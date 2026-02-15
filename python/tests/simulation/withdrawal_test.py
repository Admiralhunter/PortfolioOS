"""Tests for withdrawal strategy implementations."""

from __future__ import annotations

import pytest
from portfolioos.simulation.withdrawal import (
    constant_dollar_withdrawal,
    guyton_klinger_withdrawal,
)


class TestConstantDollarWithdrawal:
    """Tests for the constant dollar withdrawal strategy."""

    def test_year_zero_returns_initial(self) -> None:
        result = constant_dollar_withdrawal(
            initial_withdrawal=40_000.0,
            year=0,
            inflation_rate=0.03,
        )
        assert result == 40_000.0

    def test_inflation_adjustment(self) -> None:
        result = constant_dollar_withdrawal(
            initial_withdrawal=40_000.0,
            year=1,
            inflation_rate=0.03,
        )
        assert result == pytest.approx(41_200.0)

    def test_multi_year_compounding(self) -> None:
        result = constant_dollar_withdrawal(
            initial_withdrawal=40_000.0,
            year=10,
            inflation_rate=0.03,
        )
        expected = 40_000.0 * (1.03**10)
        assert result == pytest.approx(expected)

    def test_zero_inflation(self) -> None:
        result = constant_dollar_withdrawal(
            initial_withdrawal=50_000.0,
            year=5,
            inflation_rate=0.0,
        )
        assert result == 50_000.0


class TestGuytonKlingerWithdrawal:
    """Tests for the Guyton-Klinger guardrail strategy."""

    def test_year_zero_returns_initial(self) -> None:
        result = guyton_klinger_withdrawal(
            initial_withdrawal=40_000.0,
            year=0,
            inflation_rate=0.03,
            portfolio_value=1_000_000.0,
            previous_portfolio_value=1_000_000.0,
        )
        assert result == 40_000.0

    def test_basic_guardrail(self) -> None:
        result = guyton_klinger_withdrawal(
            initial_withdrawal=40_000.0,
            year=1,
            inflation_rate=0.03,
            portfolio_value=1_100_000.0,
            previous_portfolio_value=1_000_000.0,
        )
        assert result > 0

    def test_prosperity_rule_increases_withdrawal(self) -> None:
        # Portfolio grew significantly -> withdrawal rate far below initial
        # -> prosperity rule should increase withdrawal
        result = guyton_klinger_withdrawal(
            initial_withdrawal=40_000.0,
            year=1,
            inflation_rate=0.03,
            portfolio_value=2_000_000.0,  # doubled
            previous_portfolio_value=1_000_000.0,
        )
        base = 40_000.0 * 1.03
        # With prosperity rule active, result should exceed base
        assert result > base

    def test_capital_preservation_cuts_withdrawal(self) -> None:
        # Portfolio crashed -> withdrawal rate far above initial
        # -> capital preservation rule should cut withdrawal
        result = guyton_klinger_withdrawal(
            initial_withdrawal=40_000.0,
            year=1,
            inflation_rate=0.03,
            portfolio_value=500_000.0,  # halved
            previous_portfolio_value=1_000_000.0,
        )
        base = 40_000.0 * 1.03
        # With capital preservation active, result should be below base
        assert result < base
