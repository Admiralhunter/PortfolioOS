"""Build the Python package using uv build.

Writes:
    .reports/build/build_output.txt  - Full build output
    .reports/build/report.json       - Build result metadata (artifacts, sizes)

Stdout (agent-friendly):
    [build] PASS: built portfolioos-0.1.0.tar.gz + portfolioos-0.1.0-py3-none-any.whl
    [build] FAIL: build error (see .reports/build/build_output.txt)
"""

from __future__ import annotations

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

TOOL_NAME = "build"


def run(verbose: bool = False) -> dict[str, Any]:
    """Run uv build, write reports, return results."""
    result = run_command(
        ["uv", "build"],
        cwd=PYTHON_ROOT,
    )
    full_output = result.stdout + result.stderr
    write_text_report(TOOL_NAME, full_output, "build_output.txt")

    passed = result.returncode == 0

    # --- List artifacts ---
    artifacts: list[dict[str, Any]] = []
    dist_dir = PYTHON_ROOT / "dist"
    if dist_dir.exists():
        artifacts.extend(
            {"name": f.name, "size_bytes": f.stat().st_size}
            for f in sorted(dist_dir.iterdir())
            if f.is_file() and f.suffix in (".gz", ".whl", ".zip")
        )

    # --- Summary ---
    details: dict[str, Any] = {
        "artifacts": [a["name"] for a in artifacts],
        "artifact_details": artifacts,
    }
    write_json_report(TOOL_NAME, details)
    update_summary(TOOL_NAME, "pass" if passed else "fail", details)

    if passed and artifacts:
        artifact_names = " + ".join(a["name"] for a in artifacts)
        msg = f"built {artifact_names}"
    elif passed:
        msg = "built (no artifacts found in dist/)"
    else:
        msg = "build error (see .reports/build/build_output.txt)"
    print_summary(TOOL_NAME, passed, msg)

    if verbose:
        print(full_output)

    return {"passed": passed, "exit_code": result.returncode, **details}


if __name__ == "__main__":
    result = run(verbose=parse_verbose_flag())
    sys.exit(result["exit_code"])
