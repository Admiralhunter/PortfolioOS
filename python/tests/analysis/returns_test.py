"""Tests for return calculation utilities."""

from __future__ import annotations

import numpy as np
import pytest
from portfolioos.analysis.returns import cagr, max_drawdown


class TestCAGR:
    """Tests for CAGR calculation."""

    @pytest.mark.skip(reason="Implementation pending")
    def test_positive_growth(self) -> None:
        result = cagr(start_value=100.0, end_value=200.0, n_years=10.0)
        assert result == pytest.approx(0.07177, rel=1e-3)

    @pytest.mark.skip(reason="Implementation pending")
    def test_no_growth(self) -> None:
        result = cagr(start_value=100.0, end_value=100.0, n_years=5.0)
        assert result == pytest.approx(0.0)


class TestMaxDrawdown:
    """Tests for max drawdown calculation."""

    @pytest.mark.skip(reason="Implementation pending")
    def test_simple_drawdown(self) -> None:
        values = np.array([100.0, 110.0, 90.0, 95.0, 120.0])
        result = max_drawdown(values)
        assert result == pytest.approx(-0.1818, rel=1e-3)

    @pytest.mark.skip(reason="Implementation pending")
    def test_no_drawdown(self) -> None:
        values = np.array([100.0, 110.0, 120.0, 130.0])
        result = max_drawdown(values)
        assert result == pytest.approx(0.0)
