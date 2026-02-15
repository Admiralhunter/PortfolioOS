"""Vulture whitelist — references that appear unused but are called dynamically.

Vulture scans for unreachable code.  Items listed here are known false
positives: entry points invoked by setuptools, pytest fixtures consumed
via dependency injection, dataclass lifecycle hooks, etc.

Usage:
    cd python && uv run vulture portfolioos tests vulture_whitelist.py
"""

# ── Entry points (called by setuptools console_scripts, not imported) ──
from portfolioos.main import main  # noqa: F401

# ── Pytest fixtures (injected by pytest, never called directly) ──
from tests.conftest import reproducible_rng  # noqa: F401
from tests.conftest import sample_portfolio_value  # noqa: F401
from tests.conftest import sample_returns  # noqa: F401

# ── Dataclass lifecycle hooks (called by @dataclass, not user code) ──
from portfolioos.portfolio.cost_basis import TaxLot  # noqa: F401

TaxLot.__post_init__  # noqa: B018
