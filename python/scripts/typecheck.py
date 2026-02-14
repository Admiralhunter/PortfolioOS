"""Run mypy type checking with dual output.

Writes:
    .reports/typecheck/mypy_output.txt  - Full mypy output
    .reports/typecheck/report.json      - Parsed error count + summary

Stdout (agent-friendly):
    [typecheck] PASS: 0 errors across 12 files
    [typecheck] FAIL: 5 errors across 12 files
"""

from __future__ import annotations

import re
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

TOOL_NAME = "typecheck"


def run(verbose: bool = False) -> dict[str, Any]:
    """Run mypy, write reports, return results."""
    result = run_command(
        ["uv", "run", "mypy", "portfolioos"],
        cwd=PYTHON_ROOT,
    )
    full_output = result.stdout + result.stderr
    write_text_report(TOOL_NAME, full_output, "mypy_output.txt")

    # --- Parse mypy output ---
    n_errors = 0
    n_files = 0

    # mypy summary line: "Found N errors in M files (checked N source files)"
    # or: "Success: no issues found in N source files"
    for line in full_output.splitlines():
        error_match = re.search(
            r"Found (\d+) errors? in (\d+) files?",
            line,
        )
        if error_match:
            n_errors = int(error_match.group(1))
            n_files = int(error_match.group(2))
            break

        success_match = re.search(
            r"no issues found in (\d+) source files?",
            line,
        )
        if success_match:
            n_files = int(success_match.group(1))
            break

    passed = result.returncode == 0

    # --- Summary ---
    details: dict[str, Any] = {
        "errors": n_errors,
        "files_checked": n_files,
    }
    write_json_report(TOOL_NAME, details)
    update_summary(TOOL_NAME, "pass" if passed else "fail", details)

    msg = f"{n_errors} errors across {n_files} files"
    print_summary(TOOL_NAME, passed, msg)

    if verbose:
        print(full_output)

    return {"passed": passed, "exit_code": result.returncode, **details}


if __name__ == "__main__":
    result = run(verbose=parse_verbose_flag())
    sys.exit(result["exit_code"])
