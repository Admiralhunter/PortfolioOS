"""Tests for Monte Carlo simulation engine."""

from __future__ import annotations

import numpy as np
import pytest
from numpy.typing import NDArray
from portfolioos.simulation.monte_carlo import run_simulation


class TestRunSimulation:
    """Tests for the run_simulation function."""

    @pytest.mark.skip(reason="Implementation pending")
    def test_returns_correct_shape(
        self,
        sample_returns: NDArray[np.float64],
        sample_portfolio_value: float,
    ) -> None:
        result = run_simulation(
            initial_portfolio=sample_portfolio_value,
            annual_withdrawal=40_000.0,
            return_distribution=sample_returns,
            n_trials=100,
            n_years=30,
            seed=42,
        )
        assert result["portfolio_values"].shape == (100, 31)

    @pytest.mark.skip(reason="Implementation pending")
    def test_reproducible_with_seed(
        self,
        sample_returns: NDArray[np.float64],
        sample_portfolio_value: float,
    ) -> None:
        result1 = run_simulation(
            initial_portfolio=sample_portfolio_value,
            annual_withdrawal=40_000.0,
            return_distribution=sample_returns,
            seed=12345,
        )
        result2 = run_simulation(
            initial_portfolio=sample_portfolio_value,
            annual_withdrawal=40_000.0,
            return_distribution=sample_returns,
            seed=12345,
        )
        np.testing.assert_array_equal(
            result1["portfolio_values"],
            result2["portfolio_values"],
        )

    @pytest.mark.skip(reason="Implementation pending")
    def test_success_rate_bounded(
        self,
        sample_returns: NDArray[np.float64],
        sample_portfolio_value: float,
    ) -> None:
        result = run_simulation(
            initial_portfolio=sample_portfolio_value,
            annual_withdrawal=40_000.0,
            return_distribution=sample_returns,
            seed=42,
        )
        assert 0.0 <= result["success_rate"] <= 1.0
