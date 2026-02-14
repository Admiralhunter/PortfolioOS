#!/usr/bin/env bash
# Pre-commit hook: enforce minimum test coverage on commit.
#
# Runs pytest with coverage in the Python sidecar and fails if coverage
# drops below the threshold configured in pyproject.toml (fail_under).
#
# This hook runs on ALL commits, not just when Python files change,
# because any change can indirectly affect coverage (e.g., removing tests).
#
# To skip this check for a single commit:
#   SKIP=coverage-check git commit -m "..."

set -euo pipefail

PYTHON_DIR="$(git rev-parse --show-toplevel)/python"

if [ ! -d "$PYTHON_DIR" ]; then
    echo "[coverage-check] python/ directory not found, skipping"
    exit 0
fi

echo "[coverage-check] Running pytest with coverage..."
cd "$PYTHON_DIR"

# Run pytest with coverage; fail_under in pyproject.toml enforces the threshold
if uv run python -m pytest --cov=portfolioos --cov-report=term-missing:skip-covered -q 2>&1; then
    echo "[coverage-check] PASS"
    exit 0
else
    EXIT_CODE=$?
    echo ""
    echo "[coverage-check] FAIL — coverage below threshold or tests failed"
    echo "Check [tool.coverage.report] fail_under in python/pyproject.toml"
    exit $EXIT_CODE
fi
