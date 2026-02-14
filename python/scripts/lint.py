"""Run ruff linting and format checking with dual output.

Writes:
    .reports/lint/check.json       - Ruff check results (JSON)
    .reports/lint/check_output.txt - Ruff check full text output
    .reports/lint/format_diff.txt  - Ruff format diff (if any)

Stdout (agent-friendly):
    [lint] PASS: 0 errors, 0 warnings, format OK
    [lint] FAIL: 3 errors, 1 warning | format: 2 files need reformatting
"""

from __future__ import annotations

import json
import sys
from typing import Any

from scripts._report import (
    PYTHON_ROOT,
    parse_verbose_flag,
    print_summary,
    run_command,
    update_summary,
    write_json_report,
    write_text_report,
)

TOOL_NAME = "lint"


def run(verbose: bool = False) -> dict[str, Any]:
    """Run ruff check and ruff format check, write reports, return results."""
    # --- Ruff check (JSON) ---
    check_json_result = run_command(
        ["uv", "run", "ruff", "check", "--output-format=json", "."],
        cwd=PYTHON_ROOT,
    )
    check_json_text = check_json_result.stdout or "[]"
    try:
        check_data = json.loads(check_json_text)
    except json.JSONDecodeError:
        check_data = []
    write_json_report(TOOL_NAME, check_data, "check.json")

    # --- Ruff check (text) ---
    check_text_result = run_command(
        ["uv", "run", "ruff", "check", "."],
        cwd=PYTHON_ROOT,
    )
    check_text_output = check_text_result.stdout + check_text_result.stderr
    write_text_report(TOOL_NAME, check_text_output, "check_output.txt")

    # --- Ruff format check ---
    format_result = run_command(
        ["uv", "run", "ruff", "format", "--check", "--diff", "."],
        cwd=PYTHON_ROOT,
    )
    format_diff = format_result.stdout + format_result.stderr
    write_text_report(TOOL_NAME, format_diff, "format_diff.txt")

    # --- Parse results ---
    n_errors = sum(1 for d in check_data if d.get("code", "").startswith("E"))
    n_warnings = sum(1 for d in check_data if d.get("code", "").startswith("W"))
    n_total = len(check_data)
    format_clean = format_result.returncode == 0

    # Count files needing reformatting from diff output
    format_files = 0
    if not format_clean:
        for line in format_result.stdout.splitlines():
            if line.startswith("--- ") or line.startswith("would reformat"):
                format_files += 1

    passed = check_json_result.returncode == 0 and format_clean

    # --- Summary ---
    details: dict[str, Any] = {
        "errors": n_errors,
        "warnings": n_warnings,
        "total_issues": n_total,
        "format_clean": format_clean,
        "format_files_changed": format_files,
    }
    update_summary(TOOL_NAME, "pass" if passed else "fail", details)

    # --- Output ---
    format_msg = "format OK" if format_clean else f"format: {format_files} files"
    msg = f"{n_total} issues ({n_errors} errors, {n_warnings} warnings), {format_msg}"
    print_summary(TOOL_NAME, passed, msg)

    if verbose:
        if check_text_output.strip():
            print(check_text_output)
        if not format_clean:
            print(format_diff)

    return {"passed": passed, "exit_code": 0 if passed else 1, **details}


if __name__ == "__main__":
    result = run(verbose=parse_verbose_flag())
    sys.exit(result["exit_code"])
