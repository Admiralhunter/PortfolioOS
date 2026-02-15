"""Tests for enhanced scenario simulation."""

from __future__ import annotations

import numpy as np
import pytest

from portfolioos.simulation.scenarios import run_scenario, sensitivity_analysis


@pytest.fixture
def sample_returns():
    return np.array(
        [0.04, 0.14, 0.19, -0.15, -0.26, 0.37, 0.24, -0.07, 0.07, 0.18,
         0.32, -0.05, 0.21, 0.23, 0.06, 0.31, 0.19, 0.05, 0.16, 0.31],
        dtype=np.float64,
    )


class TestRunScenario:
    """Test scenario-based simulation."""

    def test_constant_dollar_basic(self, sample_returns):
        result = run_scenario(
            initial_portfolio=1_000_000,
            annual_withdrawal=40_000,
            return_distribution=sample_returns,
            withdrawal_strategy="constant_dollar",
            n_trials=100,
            n_years=30,
            seed=42,
        )
        assert 0.0 <= result["success_rate"] <= 1.0
        assert result["strategy"] == "constant_dollar"
        assert result["portfolio_values"].shape == (100, 31)
        assert 5 in result["percentiles"]
        assert 50 in result["percentiles"]
        assert 95 in result["percentiles"]

    def test_constant_percentage(self, sample_returns):
        result = run_scenario(
            initial_portfolio=1_000_000,
            annual_withdrawal=40_000,
            return_distribution=sample_returns,
            withdrawal_strategy="constant_percentage",
            n_trials=100,
            n_years=30,
            seed=42,
        )
        # Constant percentage never depletes the portfolio
        assert result["success_rate"] == 1.0

    def test_guyton_klinger(self, sample_returns):
        result = run_scenario(
            initial_portfolio=1_000_000,
            annual_withdrawal=40_000,
            return_distribution=sample_returns,
            withdrawal_strategy="guyton_klinger",
            n_trials=100,
            n_years=30,
            seed=42,
        )
        assert 0.0 <= result["success_rate"] <= 1.0
        assert result["strategy"] == "guyton_klinger"

    def test_reproducibility(self, sample_returns):
        kwargs = {
            "initial_portfolio": 1_000_000,
            "annual_withdrawal": 40_000,
            "return_distribution": sample_returns,
            "n_trials": 50,
            "n_years": 20,
            "seed": 123,
        }
        r1 = run_scenario(**kwargs)
        r2 = run_scenario(**kwargs)
        assert r1["success_rate"] == r2["success_rate"]
        assert r1["median_final_value"] == r2["median_final_value"]

    def test_life_event_windfall(self, sample_returns):
        # A windfall should increase success rate
        result_no_event = run_scenario(
            initial_portfolio=500_000,
            annual_withdrawal=40_000,
            return_distribution=sample_returns,
            n_trials=500,
            n_years=30,
            seed=42,
        )
        result_windfall = run_scenario(
            initial_portfolio=500_000,
            annual_withdrawal=40_000,
            return_distribution=sample_returns,
            life_events=[{"year": 5, "type": "windfall", "amount": 200_000}],
            n_trials=500,
            n_years=30,
            seed=42,
        )
        assert result_windfall["success_rate"] >= result_no_event["success_rate"]

    def test_life_event_expense(self, sample_returns):
        # A large expense should decrease success rate
        result_no_event = run_scenario(
            initial_portfolio=500_000,
            annual_withdrawal=40_000,
            return_distribution=sample_returns,
            n_trials=500,
            n_years=30,
            seed=42,
        )
        result_expense = run_scenario(
            initial_portfolio=500_000,
            annual_withdrawal=40_000,
            return_distribution=sample_returns,
            life_events=[{"year": 5, "type": "expense", "amount": 200_000}],
            n_trials=500,
            n_years=30,
            seed=42,
        )
        assert result_expense["success_rate"] <= result_no_event["success_rate"]

    def test_median_final_value(self, sample_returns):
        result = run_scenario(
            initial_portfolio=1_000_000,
            annual_withdrawal=40_000,
            return_distribution=sample_returns,
            n_trials=100,
            n_years=30,
            seed=42,
        )
        assert isinstance(result["median_final_value"], float)


class TestSensitivityAnalysis:
    """Test sensitivity sweep across parameter ranges."""

    def test_withdrawal_rate_sensitivity(self, sample_returns):
        results = sensitivity_analysis(
            initial_portfolio=1_000_000,
            annual_withdrawal=40_000,
            return_distribution=sample_returns,
            vary_param="withdrawal_rate",
            values=[0.03, 0.04, 0.05, 0.06],
            n_trials=100,
            n_years=30,
            seed=42,
        )
        assert len(results) == 4
        # Higher withdrawal rate → lower success rate (monotonic)
        success_rates = [r["success_rate"] for r in results]
        for i in range(len(success_rates) - 1):
            assert success_rates[i] >= success_rates[i + 1]

    def test_inflation_rate_sensitivity(self, sample_returns):
        results = sensitivity_analysis(
            initial_portfolio=1_000_000,
            annual_withdrawal=40_000,
            return_distribution=sample_returns,
            vary_param="inflation_rate",
            values=[0.02, 0.03, 0.04],
            n_trials=100,
            n_years=30,
            seed=42,
        )
        assert len(results) == 3
        for r in results:
            assert r["param_name"] == "inflation_rate"

    def test_n_years_sensitivity(self, sample_returns):
        results = sensitivity_analysis(
            initial_portfolio=1_000_000,
            annual_withdrawal=40_000,
            return_distribution=sample_returns,
            vary_param="n_years",
            values=[20, 30, 40],
            n_trials=100,
            seed=42,
        )
        assert len(results) == 3

    def test_invalid_param_raises(self, sample_returns):
        with pytest.raises(ValueError, match="vary_param must be one of"):
            sensitivity_analysis(
                initial_portfolio=1_000_000,
                annual_withdrawal=40_000,
                return_distribution=sample_returns,
                vary_param="bogus",
                values=[1, 2, 3],
            )
