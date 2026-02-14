"""Run all checks sequentially and produce an aggregate summary.

Runs: lint -> typecheck -> test -> build (docs is optional via --with-docs).
Stops at first failure unless --continue-on-error is passed.

On failure, full verbose output is printed automatically so agents don't need
to re-run with --verbose to diagnose problems.

Writes:
    .reports/summary.json  - Aggregate results from all tools

Stdout (agent-friendly):
    [ci] lint:      PASS (0 issues)
    [ci] typecheck: PASS (0 errors)
    [ci] test:      PASS (18 passed | 85.2% coverage)
    [ci] build:     PASS (2 artifacts)
    [ci] OVERALL:   PASS
"""

from __future__ import annotations

import sys
from typing import Any

from scripts._report import parse_verbose_flag

# Core steps that always run (docs removed from critical path — use --with-docs)
STEPS: list[tuple[str, str]] = [
    ("lint", "scripts.lint"),
    ("typecheck", "scripts.typecheck"),
    ("test", "scripts.test"),
    ("build", "scripts.build"),
]

OPTIONAL_STEPS: list[tuple[str, str]] = [
    ("docs", "scripts.docs"),
]


def _format_result(name: str, result: dict[str, Any]) -> str:
    """Format a single step result into a compact line."""
    status = "PASS" if result["passed"] else "FAIL"

    if name == "lint":
        detail = f"{result.get('total_issues', 0)} issues"
    elif name == "typecheck":
        detail = f"{result.get('errors', 0)} errors"
    elif name == "test":
        detail = (
            f"{result.get('tests_passed', 0)} passed"
            f" | {result.get('coverage_percent', 0):.1f}% coverage"
        )
    elif name == "docs":
        detail = f"{result.get('warnings', 0)} warnings"
    elif name == "build":
        n_artifacts = len(result.get("artifacts", []))
        detail = f"{n_artifacts} artifacts"
    else:
        detail = ""

    return f"[ci] {name + ':':12s} {status} ({detail})"


def run(
    verbose: bool = False,
    continue_on_error: bool = False,
    with_docs: bool = False,
) -> dict[str, Any]:
    """Run all checks, return aggregate results."""
    import importlib

    steps = list(STEPS)
    if with_docs:
        steps.extend(OPTIONAL_STEPS)

    results: dict[str, dict[str, Any]] = {}
    all_passed = True

    for name, module_path in steps:
        module = importlib.import_module(module_path)
        # Auto-escalate to verbose on failure so agents don't need a second run
        result = module.run(verbose=verbose)
        results[name] = result
        print(_format_result(name, result))

        if not result["passed"]:
            all_passed = False
            if not verbose:
                # Re-run with verbose to show full output for diagnosis
                print(f"\n--- {name} failed, showing full output ---")
                module.run(verbose=True)
                print(f"--- end {name} output ---\n")
            if not continue_on_error:
                break

    overall = "PASS" if all_passed else "FAIL"
    print(f"[ci] {'OVERALL:':12s} {overall}")

    return {"passed": all_passed, "exit_code": 0 if all_passed else 1, "steps": results}


if __name__ == "__main__":
    verbose = parse_verbose_flag()
    continue_on_error = "--continue-on-error" in sys.argv
    with_docs = "--with-docs" in sys.argv
    result = run(
        verbose=verbose,
        continue_on_error=continue_on_error,
        with_docs=with_docs,
    )
    sys.exit(result["exit_code"])
