.PHONY: check-python check-agents check-js check-all lint test test-js test-python test-agents lint-python lint-agents quality-gates

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

# ── Quality gates (file size + function length) ─────────────────
quality-gates:
	@echo "Checking file sizes (≤700 effective lines)..."
	@python scripts/check-file-size.py $$(find python/portfolioos python/tests python/scripts agents/blackboard agents/agents agents/tests src electron \
		-type f \( -name '*.py' -o -name '*.ts' -o -name '*.tsx' -o -name '*.js' -o -name '*.jsx' \) \
		2>/dev/null) || exit 1
	@echo "Checking function lengths (≤100 effective lines)..."
	@python scripts/check-function-length.py $$(find python/portfolioos python/tests python/scripts agents/blackboard agents/agents agents/tests src electron \
		-type f \( -name '*.py' -o -name '*.ts' -o -name '*.tsx' -o -name '*.js' -o -name '*.jsx' \) \
		2>/dev/null) || exit 1
	@echo "Quality gates passed."

# ── Agent system ───────────────────────────────────────────────
check-agents:
	cd agents && uv run ruff check .
	cd agents && uv run pytest tests/ -v

test-agents:
	cd agents && uv run pytest tests/ -v

lint-agents:
	cd agents && uv run ruff check .

# ── Electron / TypeScript ─────────────────────────────────────
check-js:
	pnpm run build
	pnpm run test

test-js:
	pnpm run test

# ── Combined ────────────────────────────────────────────────────
check-all: check-python check-agents check-js quality-gates
	@echo ""
	@echo "All checks passed."

# Default target
lint: lint-python lint-agents
test: test-python test-agents test-js
