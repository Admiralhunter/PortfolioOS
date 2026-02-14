"""Overlord agent — monitors all agents and generates summary reports.

Checks agent health, detects stale findings, flags coordination
conflicts, and writes human-readable markdown reports.

Usage:
    python -m agents.agents.overlord [--report-dir agents/reports]
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from agents.blackboard.db import Blackboard  # noqa: E402

AGENT_NAME = "overlord"

# Thresholds
STALE_FINDING_DAYS = 30
QUEUE_STAGNATION_DAYS = 7


def _check_agent_health(bb: Blackboard) -> list[dict[str, Any]]:
    """Return health status for each registered agent."""
    return bb.get_agent_health()


def _check_stale_findings(bb: Blackboard) -> list[dict[str, Any]]:
    """Find open findings older than STALE_FINDING_DAYS."""
    all_open = bb.get_findings(status="open")
    stale: list[dict[str, Any]] = []
    now = datetime.now(UTC)
    for f in all_open:
        created = datetime.fromisoformat(f["created_at"]).replace(
            tzinfo=UTC
        )
        age_days = (now - created).days
        if age_days >= STALE_FINDING_DAYS:
            stale.append({**f, "age_days": age_days})
    return stale


def _check_stagnant_tasks(bb: Blackboard) -> list[dict[str, Any]]:
    """Find pending tasks older than QUEUE_STAGNATION_DAYS."""
    pending = bb.get_tasks(status="pending")
    stagnant: list[dict[str, Any]] = []
    now = datetime.now(UTC)
    for t in pending:
        created = datetime.fromisoformat(t["created_at"]).replace(
            tzinfo=UTC
        )
        age_days = (now - created).days
        if age_days >= QUEUE_STAGNATION_DAYS:
            stagnant.append({**t, "age_days": age_days})
    return stagnant


def _generate_report(
    bb: Blackboard,
    agents: list[dict[str, Any]],
    stale: list[dict[str, Any]],
    stagnant: list[dict[str, Any]],
) -> str:
    """Generate a markdown summary report."""
    stats = bb.summary_stats()
    now_str = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    errors_24h = stats["errors_24h"]

    lines: list[str] = []
    lines.append(f"## Agent System Report — {now_str}")
    lines.append("")

    # Health
    lines.append("### Health")
    agent_count = stats["agent_count"]
    if agent_count == 0:
        lines.append("- No agents have reported yet.")
    else:
        error_agents = [
            a["agent_name"] for a in agents if a["event_type"] == "error"
        ]
        ok_count = agent_count - len(error_agents)
        lines.append(f"- {ok_count}/{agent_count} agents operational")
        lines.append(f"- {errors_24h} errors in last 24h")
        if error_agents:
            lines.append(f"- Agents with errors: {', '.join(error_agents)}")
    lines.append("")

    # Open findings
    lines.append("### Open Findings")
    open_findings = stats["open_findings"]
    if not open_findings:
        lines.append("- No open findings.")
    else:
        for sev in ("critical", "high", "medium", "low", "info"):
            count = open_findings.get(sev, 0)
            if count > 0:
                lines.append(f"- **{sev.upper()}**: {count}")

    # List recent critical/high findings
    critical_high = bb.get_findings(status="open", severity="critical")
    critical_high += bb.get_findings(status="open", severity="high")
    if critical_high:
        lines.append("")
        lines.append("**Critical/High findings:**")
        for f in critical_high[:10]:
            loc = ""
            if f.get("file_path"):
                loc = f" (`{f['file_path']}"
                if f.get("line_number"):
                    loc += f":{f['line_number']}"
                loc += "`)"
            lines.append(
                f"- [{f['severity'].upper()}] {f['agent_name']}: "
                f"{f['title']}{loc}"
            )
    lines.append("")

    # Queue status
    lines.append("### Queue Status")
    tasks = stats["tasks"]
    if not tasks:
        lines.append("- Task queue is empty.")
    else:
        statuses = ("pending", "claimed", "in_progress", "review", "done", "blocked")
        for status_name in statuses:
            count = tasks.get(status_name, 0)
            if count > 0:
                lines.append(f"- **{status_name}**: {count}")
    lines.append("")

    # Stale findings
    if stale:
        lines.append("### Stale Findings (>30 days)")
        for f in stale:
            lines.append(
                f"- {f['title']} ({f['agent_name']}, {f['age_days']} days old)"
            )
        lines.append("")

    # Stagnant tasks
    if stagnant:
        lines.append("### Stagnant Tasks (>7 days pending)")
        for t in stagnant:
            lines.append(
                f"- {t['title']} ({t['source_agent']}, {t['age_days']} days old)"
            )
        lines.append("")

    # Action items
    actions: list[str] = []
    if critical_high:
        actions.append("- [ ] Review critical/high findings above")
    if stale:
        actions.append(
            f"- [ ] Triage {len(stale)} stale findings (resolve or acknowledge)"
        )
    if stagnant:
        actions.append(
            f"- [ ] Address {len(stagnant)} stagnant tasks in the queue"
        )
    if errors_24h > 0:
        actions.append(f"- [ ] Investigate {errors_24h} agent errors in last 24h")

    if actions:
        lines.append("### Action Required")
        lines.extend(actions)
        lines.append("")
    else:
        lines.append("### Action Required")
        lines.append("- None — all clear.")
        lines.append("")

    return "\n".join(lines)


def run(
    report_dir: Path | None = None,
    db_path: Path | None = None,
) -> str:
    """Run the Overlord health check and generate a report.

    Returns the report as a string.
    """
    bb = Blackboard(db_path) if db_path else Blackboard()
    start_ms = time.monotonic_ns() // 1_000_000

    bb.log_event(agent_name=AGENT_NAME, event_type="start")

    agents = _check_agent_health(bb)
    stale = _check_stale_findings(bb)
    stagnant = _check_stagnant_tasks(bb)
    report = _generate_report(bb, agents, stale, stagnant)

    # Write report to file
    if report_dir is None:
        report_dir = _REPO_ROOT / "agents" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now(UTC).strftime("%Y-%m-%d")
    report_path = report_dir / f"report-{date_str}.md"
    report_path.write_text(report, encoding="utf-8")

    elapsed = (time.monotonic_ns() // 1_000_000) - start_ms
    bb.log_event(
        agent_name=AGENT_NAME,
        event_type="complete",
        message=f"Report written to {report_path}",
        duration_ms=elapsed,
    )
    bb.update_last_run(AGENT_NAME)

    print(report)
    print(f"\nReport saved to: {report_path}")
    return report


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="PortfolioOS Overlord Agent")
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=None,
        help="Directory for report output (default: agents/reports/)",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=None,
        help="Path to blackboard database",
    )
    args = parser.parse_args()
    run(args.report_dir, args.db_path)


if __name__ == "__main__":
    main()
