"""Run pytest with coverage and JSON reporting.

Writes:
    .reports/test/pytest.json        - pytest-json-report output
    .reports/test/coverage.json      - coverage.py JSON output
    .reports/test/htmlcov/           - HTML coverage report (for humans)
    .reports/test/pytest_output.txt  - Full pytest console output

Stdout (agent-friendly):
    [test] PASS: 42 passed, 0 failed, 3 skipped | coverage: 85.2%
    [test] FAIL: 40 passed, 2 failed, 3 skipped | coverage: 83.1%
"""

from __future__ import annotations

import json
import sys
from typing import Any

from scripts._report import (
    PYTHON_ROOT,
    ensure_report_dir,
    parse_verbose_flag,
    print_summary,
    run_command,
    update_summary,
    write_text_report,
)

TOOL_NAME = "test"


def run(verbose: bool = False) -> dict[str, Any]:
    """Run pytest with coverage, write reports, return results."""
    report_dir = ensure_report_dir(TOOL_NAME)
    pytest_json_path = report_dir / "pytest.json"
    coverage_json_path = report_dir / "coverage.json"
    htmlcov_path = report_dir / "htmlcov"

    # --- Run pytest with coverage ---
    result = run_command(
        [
            "uv",
            "run",
            "python",
            "-m",
            "pytest",
            "--json-report",
            f"--json-report-file={pytest_json_path}",
            "--json-report-omit=keywords,streams,log",
            "--cov=portfolioos",
            f"--cov-report=json:{coverage_json_path}",
            f"--cov-report=html:{htmlcov_path}",
            "--cov-report=term",
            "-q",
        ],
        cwd=PYTHON_ROOT,
    )
    full_output = result.stdout + result.stderr
    write_text_report(TOOL_NAME, full_output, "pytest_output.txt")

    # --- Parse pytest JSON report ---
    n_passed = 0
    n_failed = 0
    n_skipped = 0
    n_errors = 0

    if pytest_json_path.exists():
        try:
            pytest_data = json.loads(pytest_json_path.read_text())
            summary = pytest_data.get("summary", {})
            n_passed = summary.get("passed", 0)
            n_failed = summary.get("failed", 0)
            n_skipped = summary.get("skipped", 0)
            n_errors = summary.get("error", 0)
        except json.JSONDecodeError:
            pass

    # --- Parse coverage JSON ---
    coverage_pct = 0.0
    if coverage_json_path.exists():
        try:
            cov_data = json.loads(coverage_json_path.read_text())
            coverage_pct = cov_data.get("totals", {}).get("percent_covered", 0.0)
        except json.JSONDecodeError:
            pass

    passed = result.returncode == 0

    # --- Summary ---
    details: dict[str, Any] = {
        "tests_passed": n_passed,
        "tests_failed": n_failed,
        "tests_skipped": n_skipped,
        "tests_errors": n_errors,
        "coverage_percent": round(coverage_pct, 1),
    }
    update_summary(TOOL_NAME, "pass" if passed else "fail", details)

    msg = (
        f"{n_passed} passed, {n_failed} failed, {n_skipped} skipped"
        f" | coverage: {coverage_pct:.1f}%"
    )
    print_summary(TOOL_NAME, passed, msg)

    if verbose:
        print(full_output)

    return {"passed": passed, "exit_code": result.returncode, **details}


if __name__ == "__main__":
    result = run(verbose=parse_verbose_flag())
    sys.exit(result["exit_code"])
