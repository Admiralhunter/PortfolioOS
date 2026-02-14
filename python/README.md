# PortfolioOS Analytics Engine

Python sidecar for PortfolioOS — Monte Carlo simulations, market data fetching, and statistical analysis.

## Development

```bash
uv sync                              # Install all dependencies
uv run python -m scripts.ci          # Run all checks (agent-friendly, minimal output)
uv run python -m scripts.ci --verbose # Run all checks (human-friendly, full output)
```

### Individual Commands

```bash
uv run python -m scripts.lint        # Ruff lint + format check
uv run python -m scripts.test        # Pytest + coverage
uv run python -m scripts.typecheck   # Mypy type checking
uv run python -m scripts.docs        # Sphinx documentation
uv run python -m scripts.build       # Build sdist + wheel
```

### Reports

All commands write detailed reports to `.reports/`:

- `.reports/summary.json` — Aggregate pass/fail for all tools
- `.reports/lint/check.json` — Ruff lint results (JSON)
- `.reports/test/pytest.json` — Test results (JSON)
- `.reports/test/coverage.json` — Coverage data (JSON)
- `.reports/test/htmlcov/` — HTML coverage report
- `.reports/docs/html/` — HTML documentation
- `.reports/docs/json/` — JSON documentation (agent-friendly)
