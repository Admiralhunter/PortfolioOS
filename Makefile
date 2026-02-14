.PHONY: check-python check-js check-all lint test

# ── Python sidecar ──────────────────────────────────────────────
check-python:
	cd python && uv run ruff check .
	cd python && uv run ruff format --check .
	cd python && uv run mypy portfolioos
	cd python && uv run pytest --cov --cov-report=term-missing

lint-python:
	cd python && uv run ruff check .
	cd python && uv run ruff format --check .

test-python:
	cd python && uv run pytest --cov --cov-report=term-missing

# ── Frontend (uncomment once package.json exists) ───────────────
# check-js:
# 	pnpm lint
# 	pnpm test
# 	pnpm build

# ── Combined ────────────────────────────────────────────────────
check-all: check-python
	@echo ""
	@echo "All checks passed."

# Default target
lint: lint-python
test: test-python
