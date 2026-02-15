"""Tests for Monte Carlo simulation engine."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from portfolioos.simulation.monte_carlo import run_simulation


class TestRunSimulation:
    """Tests for the run_simulation function."""

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

    def test_initial_values_match(
        self,
        sample_returns: NDArray[np.float64],
        sample_portfolio_value: float,
    ) -> None:
        result = run_simulation(
            initial_portfolio=sample_portfolio_value,
            annual_withdrawal=40_000.0,
            return_distribution=sample_returns,
            n_trials=50,
            n_years=10,
            seed=42,
        )
        # All trials start at initial_portfolio
        np.testing.assert_array_equal(
            result["portfolio_values"][:, 0],
            np.full(50, sample_portfolio_value),
        )

    def test_portfolio_never_negative(
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
        assert np.all(result["portfolio_values"] >= 0.0)

    def test_percentile_keys(
        self,
        sample_returns: NDArray[np.float64],
        sample_portfolio_value: float,
    ) -> None:
        result = run_simulation(
            initial_portfolio=sample_portfolio_value,
            annual_withdrawal=40_000.0,
            return_distribution=sample_returns,
            n_trials=100,
            n_years=10,
            seed=42,
        )
        assert set(result["percentiles"].keys()) == {5, 25, 50, 75, 95}
        for path in result["percentiles"].values():
            assert path.shape == (11,)  # n_years + 1

    def test_zero_withdrawal_always_succeeds(
        self,
        sample_returns: NDArray[np.float64],
        sample_portfolio_value: float,
    ) -> None:
        result = run_simulation(
            initial_portfolio=sample_portfolio_value,
            annual_withdrawal=0.0,
            return_distribution=sample_returns,
            n_trials=100,
            n_years=30,
            seed=42,
        )
        assert result["success_rate"] == 1.0
