"""Tests for statistical analysis utilities."""

from __future__ import annotations

import numpy as np
import pytest
from numpy.typing import NDArray
from portfolioos.analysis.statistics import bootstrap_returns, percentile_rank


class TestPercentileRank:
    """Tests for percentile rank calculation."""

    def test_median_value(self) -> None:
        values = np.arange(1.0, 101.0)
        result = percentile_rank(values, target=50.0)
        assert result == pytest.approx(50.0, abs=1.0)

    def test_extreme_value(self) -> None:
        values = np.arange(1.0, 101.0)
        result = percentile_rank(values, target=100.0)
        assert result == pytest.approx(100.0, abs=1.0)

    def test_below_minimum(self) -> None:
        values = np.arange(10.0, 21.0)
        result = percentile_rank(values, target=5.0)
        assert result == pytest.approx(0.0, abs=1.0)

    def test_at_minimum(self) -> None:
        values = np.arange(1.0, 101.0)
        result = percentile_rank(values, target=1.0)
        assert result == pytest.approx(1.0, abs=1.0)


class TestBootstrapReturns:
    """Tests for bootstrapped return generation."""

    def test_output_shape(self, sample_returns: NDArray[np.float64]) -> None:
        result = bootstrap_returns(
            historical_returns=sample_returns,
            n_samples=500,
            n_years=30,
            seed=42,
        )
        assert result.shape == (500, 30)

    def test_reproducible(self, sample_returns: NDArray[np.float64]) -> None:
        result1 = bootstrap_returns(sample_returns, 100, 30, seed=42)
        result2 = bootstrap_returns(sample_returns, 100, 30, seed=42)
        np.testing.assert_array_equal(result1, result2)

    def test_values_come_from_distribution(
        self, sample_returns: NDArray[np.float64]
    ) -> None:
        result = bootstrap_returns(sample_returns, 50, 20, seed=99)
        # Every bootstrapped value must exist in the original distribution
        for val in result.flat:
            assert val in sample_returns

    def test_empty_distribution_raises(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            bootstrap_returns(np.array([]), 10, 5, seed=1)
