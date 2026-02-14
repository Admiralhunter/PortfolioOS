"""Tests for withdrawal strategy implementations."""

from __future__ import annotations

import pytest
from portfolioos.simulation.withdrawal import (
    constant_dollar_withdrawal,
    guyton_klinger_withdrawal,
)


class TestConstantDollarWithdrawal:
    """Tests for the constant dollar withdrawal strategy."""

    @pytest.mark.skip(reason="Implementation pending")
    def test_year_zero_returns_initial(self) -> None:
        result = constant_dollar_withdrawal(
            initial_withdrawal=40_000.0,
            year=0,
            inflation_rate=0.03,
        )
        assert result == 40_000.0

    @pytest.mark.skip(reason="Implementation pending")
    def test_inflation_adjustment(self) -> None:
        result = constant_dollar_withdrawal(
            initial_withdrawal=40_000.0,
            year=1,
            inflation_rate=0.03,
        )
        assert result == pytest.approx(41_200.0)


class TestGuytonKlingerWithdrawal:
    """Tests for the Guyton-Klinger guardrail strategy."""

    @pytest.mark.skip(reason="Implementation pending")
    def test_basic_guardrail(self) -> None:
        result = guyton_klinger_withdrawal(
            initial_withdrawal=40_000.0,
            year=1,
            inflation_rate=0.03,
            portfolio_value=1_100_000.0,
            previous_portfolio_value=1_000_000.0,
        )
        assert result > 0
