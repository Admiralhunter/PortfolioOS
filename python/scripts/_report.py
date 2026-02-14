"""Shared reporting infrastructure for PortfolioOS build scripts.

Handles:
    - Creating and managing the .reports/ directory structure
    - Writing JSON and plain-text report files
    - Aggregating results into summary.json
    - Formatting minimal CLI output
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PYTHON_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PYTHON_ROOT / ".reports"


def ensure_report_dir(tool_name: str) -> Path:
    """Create and return the report directory for a specific tool."""
    tool_dir = REPORTS_DIR / tool_name
    tool_dir.mkdir(parents=True, exist_ok=True)
    return tool_dir


def write_json_report(
    tool_name: str,
    data: dict[str, Any],
    filename: str = "report.json",
) -> Path:
    """Write a JSON report file for a tool."""
    report_dir = ensure_report_dir(tool_name)
    path = report_dir / filename
    path.write_text(json.dumps(data, indent=2, default=str) + "\n")
    return path


def write_text_report(
    tool_name: str,
    content: str,
    filename: str = "output.txt",
) -> Path:
    """Write a plain text report file."""
    report_dir = ensure_report_dir(tool_name)
    path = report_dir / filename
    path.write_text(content)
    return path


def run_command(
    cmd: list[str],
    cwd: Path | None = None,
    timeout: int = 120,
) -> subprocess.CompletedProcess[str]:
    """Run a subprocess and capture all output.

    Args:
        cmd: Command and arguments to run.
        cwd: Working directory. Defaults to PYTHON_ROOT.
        timeout: Maximum seconds before killing the process. Defaults to 120.

    Returns:
        CompletedProcess with captured stdout/stderr. On timeout, returncode
        is set to 1 and stderr contains the timeout message.
    """
    try:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd or PYTHON_ROOT,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=1,
            stdout="",
            stderr=f"TIMEOUT: command exceeded {timeout}s limit: {' '.join(cmd)}\n",
        )


def update_summary(
    tool_name: str,
    status: str,
    details: dict[str, Any],
) -> None:
    """Update the aggregate summary.json with results from a tool."""
    summary_path = REPORTS_DIR / "summary.json"
    if summary_path.exists():
        summary = json.loads(summary_path.read_text())
    else:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        summary = {"generated_at": "", "tools": {}}

    summary["generated_at"] = datetime.now(UTC).isoformat()
    summary["tools"][tool_name] = {
        "status": status,
        "timestamp": datetime.now(UTC).isoformat(),
        **details,
    }

    statuses = [t["status"] for t in summary["tools"].values()]
    summary["overall_status"] = "pass" if all(s == "pass" for s in statuses) else "fail"

    summary_path.write_text(json.dumps(summary, indent=2) + "\n")


def print_summary(tool_name: str, passed: bool, message: str) -> None:
    """Print a minimal one-line summary to stdout."""
    status = "PASS" if passed else "FAIL"
    print(f"[{tool_name}] {status}: {message}")


def parse_verbose_flag() -> bool:
    """Check if --verbose was passed on the command line."""
    return "--verbose" in sys.argv or "-v" in sys.argv
