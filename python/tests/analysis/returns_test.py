"""Tests for return calculation utilities."""

from __future__ import annotations

import numpy as np
import pytest
from portfolioos.analysis.returns import cagr, max_drawdown


class TestCAGR:
    """Tests for CAGR calculation."""

    def test_positive_growth(self) -> None:
        result = cagr(start_value=100.0, end_value=200.0, n_years=10.0)
        assert result == pytest.approx(0.07177, rel=1e-3)

    def test_no_growth(self) -> None:
        result = cagr(start_value=100.0, end_value=100.0, n_years=5.0)
        assert result == pytest.approx(0.0)

    def test_negative_growth(self) -> None:
        result = cagr(start_value=100.0, end_value=50.0, n_years=5.0)
        assert result < 0

    def test_fractional_years(self) -> None:
        result = cagr(start_value=100.0, end_value=110.0, n_years=0.5)
        assert result > 0

    def test_invalid_start_value(self) -> None:
        with pytest.raises(ValueError, match="start_value must be positive"):
            cagr(start_value=0.0, end_value=100.0, n_years=5.0)

    def test_invalid_n_years(self) -> None:
        with pytest.raises(ValueError, match="n_years must be positive"):
            cagr(start_value=100.0, end_value=200.0, n_years=0.0)

    def test_negative_end_value(self) -> None:
        with pytest.raises(ValueError, match="end_value must be non-negative"):
            cagr(start_value=100.0, end_value=-50.0, n_years=5.0)


class TestMaxDrawdown:
    """Tests for max drawdown calculation."""

    def test_simple_drawdown(self) -> None:
        values = np.array([100.0, 110.0, 90.0, 95.0, 120.0])
        result = max_drawdown(values)
        assert result == pytest.approx(-0.1818, rel=1e-3)

    def test_no_drawdown(self) -> None:
        values = np.array([100.0, 110.0, 120.0, 130.0])
        result = max_drawdown(values)
        assert result == pytest.approx(0.0)

    def test_full_loss(self) -> None:
        values = np.array([100.0, 50.0, 0.1])
        result = max_drawdown(values)
        assert result == pytest.approx(-0.999, rel=1e-2)

    def test_too_few_values(self) -> None:
        with pytest.raises(ValueError, match="at least 2 elements"):
            max_drawdown(np.array([100.0]))
