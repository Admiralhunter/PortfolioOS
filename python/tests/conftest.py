"""Shared pytest fixtures for PortfolioOS analytics tests.

TODO(BUILD_TODO#7): Fixtures are defined here but NO actual test files exist.
The CI pipeline will report PASS with 0 tests. Add tests for at minimum:
  - portfolioos/main.py (dispatch, message loop, error handling)
  - scripts/_report.py (report generation, summary aggregation)
"""

from __future__ import annotations

import numpy as np
import pytest
from numpy.typing import NDArray


@pytest.fixture
def reproducible_rng() -> np.random.Generator:
    """Provide a seeded random number generator for deterministic tests."""
    return np.random.default_rng(seed=42)


@pytest.fixture
def sample_returns() -> NDArray[np.float64]:
    """Provide sample historical annual returns for testing.

    Based on simplified S&P 500 annual returns (representative sample).
    """
    return np.array(
        [
            0.04,
            0.14,
            0.19,
            -0.15,
            -0.26,
            0.37,
            0.24,
            -0.07,
            0.07,
            0.18,
            0.32,
            -0.05,
            0.21,
            0.23,
            0.06,
            0.31,
            0.19,
            0.05,
            0.16,
            0.31,
            -0.03,
            0.30,
            0.08,
            0.10,
            0.01,
            -0.10,
            -0.12,
            -0.22,
            0.28,
            0.11,
            0.05,
            0.16,
        ],
        dtype=np.float64,
    )


@pytest.fixture
def sample_portfolio_value() -> float:
    """Provide a standard portfolio value for testing."""
    return 1_000_000.0
