"""LLM-powered TODO Scanner agent.

Extends the original regex-based scanner with:
  - LLM triage: prioritises and groups related TODOs
  - GitHub Issues output: creates issues for high-priority findings
  - Backward-compatible: still writes to the local blackboard

The regex extraction phase is unchanged (fast, free, deterministic).
The LLM triage phase is optional — if no LLM is available, the agent
falls back to the static priority mapping from the original scanner.

Usage::

    # CLI
    python -m agents.agents.todo_scanner_llm [--repo-root /path] [--db-path /path]

    # From code
    from agents.agents.todo_scanner_llm import TodoScannerLLMAgent
    agent = TodoScannerLLMAgent()
    result = agent.run()
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from agents.agents.todo_scanner import (  # noqa: E402
    PRIORITY_MAP,
    SEVERITY_MAP,
    _collect_source_files,
    _extract_todos,
)
from agents.base import Agent  # noqa: E402

_TRIAGE_SYSTEM_PROMPT = """\
You are a code quality analyst for PortfolioOS, a local-first financial \
desktop application (Electron + React + Python).

You will receive a JSON list of TODO/FIXME/HACK/XXX markers extracted from \
the codebase.  For each marker, assess:

1. **Priority** (p1 = critical, p2 = high, p3 = medium):
   - Financial calculation bugs or data integrity → p1
   - Security issues or credential handling → p1
   - Broken functionality or known bugs → p2
   - Technical debt that affects maintainability → p2
   - Nice-to-have improvements → p3

2. **Group**: Identify markers that relate to the same logical issue and \
should be addressed together.

3. **Issue title**: Write a concise, actionable issue title for each group.

4. **Issue body**: Write a brief description suitable for a GitHub issue body.

Respond with a JSON object:
```json
{
  "groups": [
    {
      "title": "Fix division-by-zero in withdrawal calculator",
      "priority": "p2",
      "body": "Multiple TODOs in withdrawal.py relate to ...",
      "markers": [0, 3, 7]
    }
  ]
}
```

Where ``markers`` is a list of indices into the input array.
Only include markers that are NOT of type NOTE.
Respond ONLY with the JSON object, no other text."""


class TodoScannerLLMAgent(Agent):
    """LLM-enhanced TODO scanner.

    Phase 1 (regex): Extract markers from source files.
    Phase 2 (LLM):   Triage, group, and prioritise.
    Phase 3 (output): Write to blackboard + create GitHub issues.
    """

    name = "todo-scanner"
    model_pref = "local"

    def __init__(
        self,
        *,
        repo_root: Path | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.repo_root = repo_root or _REPO_ROOT

    def execute(self) -> dict[str, Any]:
        # -- Phase 1: regex extraction (fast, deterministic) ----------------
        source_files = _collect_source_files(self.repo_root)
        all_markers: list[dict[str, Any]] = []

        for fpath in source_files:
            todos = _extract_todos(fpath)
            rel_path = str(fpath.relative_to(self.repo_root))
            for item in todos:
                item["file_path"] = rel_path
                all_markers.append(item)

        actionable = [m for m in all_markers if m["marker"] != "NOTE"]

        # -- Phase 2: LLM triage (optional) --------------------------------
        groups = self._triage_with_llm(actionable)

        # -- Phase 3: output ------------------------------------------------
        self._write_to_blackboard(all_markers)
        issues_created = self._create_github_issues(groups)

        summary = {
            "files_scanned": len(source_files),
            "markers_found": len(all_markers),
            "actionable": len(actionable),
            "groups": len(groups),
            "issues_created": issues_created,
        }
        print(json.dumps(summary, indent=2))
        return summary

    def _triage_with_llm(
        self, markers: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Use the LLM to group and prioritise markers.

        Falls back to one-group-per-marker with static priorities if
        no LLM is available.
        """
        if not markers:
            return []

        # Prepare compact input for the LLM
        compact = [
            {
                "idx": i,
                "marker": m["marker"],
                "file": m["file_path"],
                "line": m["line_number"],
                "desc": m["description"][:200],
            }
            for i, m in enumerate(markers)
        ]

        raw = self.reason_or_skip(
            system=_TRIAGE_SYSTEM_PROMPT,
            user=json.dumps(compact, indent=2),
            fallback="",
        )

        if raw:
            groups = self._parse_triage_response(raw, markers)
            if groups:
                return groups

        # Fallback: one group per marker, static priorities
        return [
            {
                "title": f"{m['marker']}: {m['description'][:100]}",
                "priority": _static_priority(m["marker"]),
                "body": (
                    f"**{m['marker']}** in `{m['file_path']}:{m['line_number']}`\n\n"
                    f"{m['description']}"
                ),
                "markers": [i],
            }
            for i, m in enumerate(markers)
        ]

    def _parse_triage_response(
        self, raw: str, markers: list[dict[str, Any]]
    ) -> list[dict[str, Any]] | None:
        """Parse the LLM's JSON response, with fallback on malformed output."""
        # Strip markdown code fences if present
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = lines[1:]  # remove opening fence
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return None

        groups = data.get("groups", [])
        if not isinstance(groups, list):
            return None

        # Validate each group has required fields
        valid_groups: list[dict[str, Any]] = []
        for g in groups:
            if not isinstance(g, dict):
                continue
            if "title" not in g or "priority" not in g:
                continue
            # Ensure marker indices are valid
            idxs = g.get("markers", [])
            if not isinstance(idxs, list):
                continue
            idxs = [i for i in idxs if isinstance(i, int) and 0 <= i < len(markers)]
            if not idxs:
                continue
            valid_groups.append({
                "title": str(g["title"])[:200],
                "priority": str(g.get("priority", "p3")),
                "body": str(g.get("body", g["title"])),
                "markers": idxs,
            })

        return valid_groups if valid_groups else None

    def _write_to_blackboard(self, markers: list[dict[str, Any]]) -> None:
        """Write findings to the local blackboard (backward compat)."""
        for m in markers:
            if m["marker"] == "NOTE":
                continue
            title = f"{m['marker']}: {m['description'][:120]}"
            self.bb.add_finding(
                agent_name=self.name,
                severity=SEVERITY_MAP[m["marker"]],
                category="todo",
                title=title,
                description=m["description"],
                file_path=m["file_path"],
                line_number=m["line_number"],
                metadata={"marker": m["marker"]},
            )

    def _create_github_issues(
        self, groups: list[dict[str, Any]]
    ) -> int:
        """Create GitHub issues for triage groups.

        Only creates issues for p1 and p2 groups to avoid noise.
        """
        if self.gh is None:
            return 0

        created = 0
        for g in groups:
            if g["priority"] not in ("p1", "p2"):
                continue
            self.create_finding_issue(
                title=g["title"],
                body=g["body"],
                priority=g["priority"],
            )
            created += 1
        return created


def _static_priority(marker: str) -> str:
    """Map marker type to priority label."""
    p = PRIORITY_MAP.get(marker, 3)
    if p <= 2:
        return "p2"
    return "p3"


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="PortfolioOS LLM-powered TODO Scanner"
    )
    parser.add_argument(
        "--repo-root", type=Path, default=_REPO_ROOT,
        help="Root of the repository to scan",
    )
    parser.add_argument(
        "--db-path", type=Path, default=None,
        help="Path to the blackboard database",
    )
    args = parser.parse_args()
    agent = TodoScannerLLMAgent(repo_root=args.repo_root, db_path=args.db_path)
    agent.run()


if __name__ == "__main__":
    main()
