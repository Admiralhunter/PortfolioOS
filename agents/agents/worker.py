"""Worker agent — picks up spec-ready tasks and implements them.

The Worker agent is the only agent that writes production code.  It:

1. Finds issues labelled ``status:spec-ready`` + ``agent:worker``
2. Claims the highest-priority issue
3. Uses an LLM to generate an implementation plan
4. Executes the plan (create branch, write code, run checks)
5. Opens a PR and links it back to the issue
6. Relabels the issue as ``status:review``

The actual code generation is delegated to an LLM (claude-opus
recommended).  In GitHub Actions, this agent is typically invoked
via ``anthropics/claude-code-action`` which provides full tool access.

For local execution, the agent generates a plan and posts it as a
comment, then waits for a human or Claude Code session to execute.

Usage::

    # CLI — generate plan only (safe, no code writes)
    python -m agents.agents.worker --plan-only

    # CLI — full execution (creates branch, writes code, opens PR)
    python -m agents.agents.worker --execute

    # GitHub Actions — see .github/workflows/agent-worker.yml
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from agents.base import Agent  # noqa: E402

_PLANNING_SYSTEM_PROMPT = """\
You are the Worker agent for PortfolioOS, a local-first financial desktop \
application.  You implement tasks from the issue queue.

## Your Constraints
- Follow ALL conventions in CLAUDE.md (conventional commits, naming, etc.)
- Max 700 lines per file, max 100 lines per function
- TypeScript: strict mode, no `any`, prefer `interface`
- Python: type hints on all public functions, snake_case
- React: functional components only
- NEVER add telemetry, tracking, or data exfiltration
- NEVER store user credentials
- NEVER send portfolio data to cloud without explicit consent
- All financial calculations must cite methodology

## Task
Read the specification below and produce an implementation plan as JSON:

```json
{
  "branch_name": "feat/short-description",
  "commit_message": "feat: description of the change",
  "steps": [
    {
      "action": "create|modify|delete",
      "file": "path/to/file.py",
      "description": "What to do to this file",
      "code": "The actual code to write (for create) or a diff description (for modify)"
    }
  ],
  "test_files": ["path/to/test_file.py"],
  "commands_to_run": ["make check-all"]
}
```

Rules:
- Keep the plan minimal — do the least work that satisfies the spec
- Always include tests
- Always include ``make check-all`` in commands_to_run
- Respond ONLY with the JSON object"""

_EXECUTION_SYSTEM_PROMPT = """\
You are the Worker agent for PortfolioOS.  Execute the implementation \
plan provided.  For each step:

1. If action is "create": write the file
2. If action is "modify": apply the changes to the existing file
3. If action is "delete": remove the file

After all steps:
- Run ``make check-all`` and fix any failures
- Commit with the specified commit message
- Push to the specified branch

Report your results as JSON:
```json
{
  "status": "success|failure",
  "files_changed": ["path/to/file.py"],
  "checks_passed": true,
  "errors": []
}
```"""


class WorkerAgent(Agent):
    """Implements tasks from the GitHub issue queue."""

    name = "worker"
    model_pref = "claude-opus"

    def __init__(
        self,
        *,
        plan_only: bool = True,
        single_issue: int | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.plan_only = plan_only
        self.single_issue = single_issue

    def execute(self) -> dict[str, Any]:
        if self.gh is None:
            raise RuntimeError(
                "Worker agent requires GitHub access. "
                "Set GITHUB_TOKEN and GITHUB_REPOSITORY."
            )
        if self.llm is None:
            raise RuntimeError(
                "Worker agent requires an LLM. "
                "Set ANTHROPIC_API_KEY or start LM Studio."
            )

        # Find work
        issue = self._find_task()
        if issue is None:
            return {"status": "no_work", "message": "No spec-ready tasks found"}

        issue_number = issue["number"]

        # Claim it
        self.claim_issue(issue_number)
        self.comment_on_issue(
            issue_number,
            "**Worker agent** is picking up this task.",
        )

        # Generate implementation plan
        plan = self._generate_plan(issue)

        if self.plan_only:
            # Post plan as comment, leave for human/Claude Code to execute
            self._post_plan_comment(issue_number, plan)
            return {
                "status": "plan_posted",
                "issue": issue_number,
                "steps": len(plan.get("steps", [])),
            }

        # Full execution mode
        result = self._execute_plan(issue_number, plan)
        return result

    def _find_task(self) -> dict[str, Any] | None:
        """Find the highest-priority spec-ready task."""
        if self.gh is None:
            return None

        if self.single_issue is not None:
            return self.gh.get_issue(self.single_issue)

        issues = self.gh.list_issues(
            labels="status:spec-ready,agent:worker",
        )
        if not issues:
            return None

        # Sort by priority label (p1 > p2 > p3)
        def priority_key(iss: dict[str, Any]) -> int:
            labels = [
                lbl["name"] if isinstance(lbl, dict) else str(lbl)
                for lbl in iss.get("labels", [])
            ]
            for p, val in [("priority:p1", 1), ("priority:p2", 2), ("priority:p3", 3)]:
                if p in labels:
                    return val
            return 3

        issues.sort(key=priority_key)
        return issues[0]

    def _generate_plan(self, issue: dict[str, Any]) -> dict[str, Any]:
        """Use the LLM to generate an implementation plan."""
        user_prompt = (
            f"## Task: #{issue['number']} — {issue.get('title', '')}\n\n"
            f"{issue.get('body', '')}"
        )

        raw = self.reason(
            system=_PLANNING_SYSTEM_PROMPT,
            user=user_prompt,
            max_tokens=8192,
        )

        return self._parse_plan(raw)

    def _parse_plan(self, raw: str) -> dict[str, Any]:
        """Parse the LLM's plan JSON."""
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)

        try:
            data = json.loads(text)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

        return {
            "branch_name": "agent/worker/unknown",
            "commit_message": "feat: agent implementation",
            "steps": [],
            "raw_plan": raw,
        }

    def _post_plan_comment(
        self, issue_number: int, plan: dict[str, Any]
    ) -> None:
        """Post the implementation plan as a GitHub comment."""
        steps_md = ""
        for i, step in enumerate(plan.get("steps", []), 1):
            action = step.get("action", "?")
            filepath = step.get("file", "?")
            desc = step.get("description", "")
            steps_md += f"{i}. **{action}** `{filepath}` — {desc}\n"

        raw_plan = plan.get("raw_plan", "")
        if raw_plan and not steps_md:
            steps_md = f"```\n{raw_plan}\n```"

        comment = (
            "## Worker Agent — Implementation Plan\n\n"
            f"**Branch:** `{plan.get('branch_name', 'TBD')}`\n"
            f"**Commit:** `{plan.get('commit_message', 'TBD')}`\n\n"
            f"### Steps\n{steps_md}\n"
            f"### Validation\n"
            "```\n"
            f"{', '.join(plan.get('commands_to_run', ['make check-all']))}"
            "\n```\n\n"
            "---\n"
            "_This plan was generated by the Worker agent. "
            "A human or Claude Code session should review and execute it. "
            "To execute automatically, re-run with `--execute`._"
        )
        self.comment_on_issue(issue_number, comment)

    def _execute_plan(
        self, issue_number: int, plan: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute the plan: create branch, write files, run checks, open PR.

        This is the fully autonomous mode.  In practice, this is usually
        delegated to ``anthropics/claude-code-action`` in GitHub Actions
        rather than run directly.
        """
        branch = plan.get("branch_name", f"agent/worker/issue-{issue_number}")
        commit_msg = plan.get("commit_message", f"feat: implement #{issue_number}")

        # Create branch
        _run_git("checkout", "-b", branch)

        errors: list[str] = []
        files_changed: list[str] = []

        for step in plan.get("steps", []):
            action = step.get("action", "")
            filepath = step.get("file", "")
            code = step.get("code", "")

            if not filepath:
                continue

            full_path = _REPO_ROOT / filepath
            try:
                if action == "create":
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    full_path.write_text(code, encoding="utf-8")
                    files_changed.append(filepath)
                elif action == "delete" and full_path.exists():
                    full_path.unlink()
                    files_changed.append(filepath)
                elif action == "modify":
                    # For modify, we'd need the LLM to provide a diff or
                    # full replacement.  This is a simplified version.
                    if code and full_path.exists():
                        full_path.write_text(code, encoding="utf-8")
                        files_changed.append(filepath)
            except OSError as exc:
                errors.append(f"Failed to {action} {filepath}: {exc}")

        # Run checks
        checks_passed = False
        try:
            subprocess.run(
                ["make", "check-all"],
                cwd=str(_REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=300,
                check=True,
            )
            checks_passed = True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            errors.append(f"Check failed: {exc}")

        # Commit and push
        if files_changed and checks_passed:
            for f in files_changed:
                _run_git("add", f)
            _run_git("commit", "-m", commit_msg)
            _run_git("push", "-u", "origin", branch)

            # Open PR
            if self.gh is not None:
                pr_body = (
                    f"## Summary\n\nImplements #{issue_number}.\n\n"
                    f"## Changes\n"
                    + "\n".join(f"- `{f}`" for f in files_changed)
                    + f"\n\n## Tags\n- type:feat\n- risk:low\n\n"
                    f"Closes #{issue_number}"
                )
                pr = self.gh._request("POST", "pulls", {
                    "title": commit_msg,
                    "body": pr_body,
                    "head": branch,
                    "base": "main",
                })
                pr_url = pr.get("html_url", "") if isinstance(pr, dict) else ""

                # Update issue
                self.gh.add_labels(
                    issue_number, ["status:review"]
                )
                self.comment_on_issue(
                    issue_number,
                    f"**Worker agent** opened PR: {pr_url}",
                )

        status = "success" if checks_passed and not errors else "failure"
        return {
            "status": status,
            "issue": issue_number,
            "branch": branch,
            "files_changed": files_changed,
            "checks_passed": checks_passed,
            "errors": errors,
        }


def _run_git(*args: str) -> str:
    """Run a git command and return stdout."""
    result = subprocess.run(
        ["git", *args],
        cwd=str(_REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.stdout.strip()


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="PortfolioOS Worker Agent"
    )
    parser.add_argument(
        "--issue", type=int, default=None,
        help="Work on a specific issue number",
    )
    parser.add_argument(
        "--plan-only", action="store_true", default=True,
        help="Only generate and post the plan (default)",
    )
    parser.add_argument(
        "--execute", action="store_true", default=False,
        help="Execute the plan (create branch, write code, open PR)",
    )
    parser.add_argument(
        "--db-path", type=Path, default=None,
        help="Path to the blackboard database",
    )
    args = parser.parse_args()
    agent = WorkerAgent(
        plan_only=not args.execute,
        single_issue=args.issue,
        db_path=args.db_path,
    )
    agent.run()


if __name__ == "__main__":
    main()
