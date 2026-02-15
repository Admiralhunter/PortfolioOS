"""Project Manager agent — triages GitHub issues and drafts specs.

Monitors GitHub Issues labelled ``status:needs-triage``, reads each one,
uses an LLM to analyse the request, posts clarifying questions or a
spec draft as a comment, and relabels the issue as ``status:spec-ready``
when done.

This agent requires a cloud LLM (claude-opus recommended) because it
needs strong reasoning about requirements, architecture, and scope.

Usage::

    # CLI
    python -m agents.agents.project_manager

    # GitHub Actions (see .github/workflows/agent-pm.yml)
    # Triggered on issues.opened or issues.labeled events
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from agents.base import Agent  # noqa: E402

# Read project context files at import time for prompt building
_SPEC_PATH = _REPO_ROOT / "docs" / "SPEC.md"
_ARCH_PATH = _REPO_ROOT / "docs" / "ARCHITECTURE.md"
_CLAUDE_MD_PATH = _REPO_ROOT / "CLAUDE.md"


def _read_context_file(path: Path, max_chars: int = 4000) -> str:
    """Read a context file, truncating if too long."""
    if not path.exists():
        return f"({path.name} not found)"
    text = path.read_text(encoding="utf-8", errors="replace")
    if len(text) > max_chars:
        return text[:max_chars] + "\n\n[... truncated ...]"
    return text


_TRIAGE_SYSTEM_PROMPT = """\
You are the Project Manager agent for PortfolioOS, a local-first, \
privacy-preserving desktop application for personal finance and FIRE \
analysis.

## Your Role
- Triage new GitHub issues from users and developers
- Identify ambiguities and ask clarifying questions
- Draft implementation specifications
- Assess priority and scope
- Recommend which agent (worker, human) should implement it

## Project Context

### Key Constraints
- Local-first: all data stays on user's machine
- No telemetry, no tracking, no data exfiltration
- Dual database: DuckDB (analytics) + SQLite (app state) — never merge
- Renderer never accesses DB directly — all through Electron IPC
- Cloud LLM is opt-in only; LM Studio is default
- API keys stored via Electron safeStorage
- All financial calcs must cite methodology (Bengen 1994, Trinity Study, etc.)

### Tech Stack
Electron + React 19 + TypeScript + Vite + Tailwind + Zustand + TanStack \
Query/Router + Python sidecar (NumPy/Pandas/SciPy) + DuckDB + SQLite

## Output Format

Respond with a JSON object:
```json
{
  "needs_clarification": true,
  "questions": ["What cost basis method should be used?", "..."],
  "priority": "p2",
  "scope": "medium",
  "assignee": "worker",
  "spec": "## Specification\\n\\n### Goal\\n...\\n..."
}
```

Rules:
- If the issue is clear enough to implement, set ``needs_clarification`` to false \
and write a full spec.
- If ambiguous, set ``needs_clarification`` to true and list your questions. \
Still draft a preliminary spec based on your best interpretation.
- ``assignee`` is one of: "worker" (agent can implement), "human" (needs human \
judgment), "skip" (not actionable or duplicate).
- ``priority``: "p1" (critical/security/data), "p2" (important feature/bug), \
"p3" (nice-to-have).
- ``scope``: "small" (<50 lines changed), "medium" (50-200), "large" (200+).
- Always include a "Files to Change" section in the spec listing likely files.
- Respond ONLY with the JSON object, no other text."""


class ProjectManagerAgent(Agent):
    """Triages GitHub issues and drafts implementation specs."""

    name = "pm"
    model_pref = "claude-opus"

    def __init__(
        self,
        *,
        single_issue: int | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.single_issue = single_issue
        self._context_loaded = False
        self._project_context = ""

    def _load_project_context(self) -> str:
        """Load project docs for inclusion in the LLM prompt."""
        if self._context_loaded:
            return self._project_context
        parts = []
        for label, path in [
            ("SPEC.md", _SPEC_PATH),
            ("ARCHITECTURE.md", _ARCH_PATH),
        ]:
            parts.append(f"### {label}\n{_read_context_file(path)}")
        self._project_context = "\n\n".join(parts)
        self._context_loaded = True
        return self._project_context

    def execute(self) -> dict[str, Any]:
        if self.gh is None:
            raise RuntimeError(
                "PM agent requires GitHub access. "
                "Set GITHUB_TOKEN and GITHUB_REPOSITORY."
            )
        if self.llm is None:
            raise RuntimeError(
                "PM agent requires an LLM. "
                "Set ANTHROPIC_API_KEY or start LM Studio."
            )

        # Get issues to triage
        if self.single_issue is not None:
            issues = [self.gh.get_issue(self.single_issue)]
        else:
            issues = self.gh.list_issues(labels="status:needs-triage")

        triaged = 0
        for issue in issues:
            self._triage_issue(issue)
            triaged += 1

        return {"triaged": triaged}

    def _triage_issue(self, issue: dict[str, Any]) -> None:
        """Triage a single issue using the LLM."""
        issue_number = issue["number"]
        issue_title = issue.get("title", "")
        issue_body = issue.get("body", "") or ""

        # Build the user prompt with project context
        context = self._load_project_context()
        user_prompt = (
            f"## Issue #{issue_number}: {issue_title}\n\n"
            f"{issue_body}\n\n"
            f"---\n\n"
            f"## Project Context\n\n{context}"
        )

        raw = self.reason(
            system=_TRIAGE_SYSTEM_PROMPT,
            user=user_prompt,
            max_tokens=4096,
        )

        analysis = self._parse_analysis(raw)
        comment = self._format_comment(analysis)
        self.gh.add_comment(issue_number, comment)

        # Update labels based on analysis
        new_labels = self._build_labels(issue, analysis)
        self.gh.update_labels(issue_number, new_labels)

    def _parse_analysis(self, raw: str) -> dict[str, Any]:
        """Parse the LLM response, with fallback on malformed output."""
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

        # Fallback: treat raw response as the spec text
        return {
            "needs_clarification": False,
            "questions": [],
            "priority": "p3",
            "scope": "medium",
            "assignee": "human",
            "spec": raw,
        }

    def _format_comment(self, analysis: dict[str, Any]) -> str:
        """Format the analysis as a GitHub issue comment."""
        parts = ["## PM Agent Analysis\n"]

        if analysis.get("needs_clarification"):
            parts.append("### Clarifying Questions\n")
            for q in analysis.get("questions", []):
                parts.append(f"- {q}")
            parts.append("")

        parts.append(
            f"**Priority:** `{analysis.get('priority', 'p3')}` | "
            f"**Scope:** `{analysis.get('scope', 'medium')}` | "
            f"**Suggested assignee:** `{analysis.get('assignee', 'human')}`\n"
        )

        spec = analysis.get("spec", "")
        if spec:
            parts.append("### Draft Specification\n")
            parts.append(spec)

        parts.append(
            "\n---\n_This analysis was generated by the PM agent. "
            "Edit the issue or reply to refine._"
        )
        return "\n".join(parts)

    def _build_labels(
        self,
        issue: dict[str, Any],
        analysis: dict[str, Any],
    ) -> list[str]:
        """Build the label set for the triaged issue."""
        priority = analysis.get("priority", "p3")
        assignee = analysis.get("assignee", "human")
        needs_clarification = analysis.get("needs_clarification", False)

        labels = ["agent:pm", "type:task", f"priority:{priority}"]

        if needs_clarification:
            labels.append("status:blocked")
        else:
            labels.append("status:spec-ready")

        if assignee == "worker":
            labels.append("agent:worker")

        # Preserve any existing labels that aren't in our managed set
        managed_prefixes = ("agent:", "status:", "priority:", "type:")
        for existing in issue.get("labels", []):
            if isinstance(existing, dict):
                name = existing.get("name", "")
            else:
                name = str(existing)
            if not any(name.startswith(p) for p in managed_prefixes):
                labels.append(name)

        return labels


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="PortfolioOS Project Manager Agent"
    )
    parser.add_argument(
        "--issue", type=int, default=None,
        help="Triage a specific issue number (default: all needs-triage)",
    )
    parser.add_argument(
        "--db-path", type=Path, default=None,
        help="Path to the blackboard database",
    )
    args = parser.parse_args()

    from agents.log_config import setup as setup_logging

    setup_logging()
    agent = ProjectManagerAgent(single_issue=args.issue, db_path=args.db_path)
    agent.run()


if __name__ == "__main__":
    main()
