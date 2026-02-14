"""Run Sphinx documentation generation with dual output.

Writes:
    .reports/docs/html/            - HTML docs (for humans)
    .reports/docs/json/            - JSON docs (for agents)
    .reports/docs/sphinx_output.txt - Full Sphinx build output

Stdout (agent-friendly):
    [docs] PASS: generated docs (0 warnings)
    [docs] FAIL: build failed (3 warnings)
"""

from __future__ import annotations

import re
import sys
from typing import Any

from scripts._report import (
    PYTHON_ROOT,
    ensure_report_dir,
    parse_verbose_flag,
    print_summary,
    run_command,
    update_summary,
    write_json_report,
)

TOOL_NAME = "docs"


def run(verbose: bool = False) -> dict[str, Any]:
    """Run Sphinx builds (HTML + JSON), write reports, return results."""
    report_dir = ensure_report_dir(TOOL_NAME)
    docs_src = PYTHON_ROOT / "docs"
    html_out = report_dir / "html"
    json_out = report_dir / "json"

    # --- Build HTML ---
    html_result = run_command(
        [
            "uv",
            "run",
            "python",
            "-m",
            "sphinx",
            "-b",
            "html",
            str(docs_src),
            str(html_out),
            "-q",
        ],
        cwd=PYTHON_ROOT,
    )

    # --- Build JSON ---
    json_result = run_command(
        [
            "uv",
            "run",
            "python",
            "-m",
            "sphinx",
            "-b",
            "json",
            str(docs_src),
            str(json_out),
            "-q",
        ],
        cwd=PYTHON_ROOT,
    )

    full_output = (
        "=== HTML Build ===\n"
        + html_result.stdout
        + html_result.stderr
        + "\n=== JSON Build ===\n"
        + json_result.stdout
        + json_result.stderr
    )
    (report_dir / "sphinx_output.txt").write_text(full_output)

    # --- Parse warnings ---
    n_warnings = 0
    for line in full_output.splitlines():
        warning_match = re.search(r"(\d+) warnings?", line)
        if warning_match:
            n_warnings += int(warning_match.group(1))

    passed = html_result.returncode == 0 and json_result.returncode == 0

    # --- Summary ---
    details: dict[str, Any] = {
        "warnings": n_warnings,
        "html_built": html_result.returncode == 0,
        "json_built": json_result.returncode == 0,
    }
    write_json_report(TOOL_NAME, details)
    update_summary(TOOL_NAME, "pass" if passed else "fail", details)

    msg = f"generated docs ({n_warnings} warnings)"
    print_summary(TOOL_NAME, passed, msg)

    if verbose:
        print(full_output)

    return {"passed": passed, "exit_code": 0 if passed else 1, **details}


if __name__ == "__main__":
    result = run(verbose=parse_verbose_flag())
    sys.exit(result["exit_code"])
