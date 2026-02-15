#!/usr/bin/env bash
set -euo pipefail

# PortfolioOS Docker entrypoint
# Handles both running the app and executing tests/dev commands.

COMMAND="${1:-start}"
shift 2>/dev/null || true

case "$COMMAND" in
  start)
    echo "[portfolioos] Starting Electron app..."
    # --no-sandbox is required when running Electron as non-root in Docker.
    # The container itself provides the isolation boundary.
    exec pnpm start -- --no-sandbox "$@"
    ;;
  test)
    echo "[portfolioos] Running tests..."
    cd /app/python && uv run pytest "$@"
    cd /app && pnpm run test "$@"
    ;;
  test:python)
    echo "[portfolioos] Running Python tests..."
    cd /app/python && exec uv run pytest "$@"
    ;;
  test:js)
    echo "[portfolioos] Running JS/TS tests..."
    exec pnpm run test "$@"
    ;;
  lint)
    echo "[portfolioos] Running linters..."
    cd /app/python && uv run ruff check .
    cd /app && pnpm run lint "$@"
    ;;
  shell)
    echo "[portfolioos] Opening shell..."
    exec /bin/bash "$@"
    ;;
  *)
    # Pass through any other command
    exec "$@"
    ;;
esac
