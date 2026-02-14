"""Withdrawal strategy implementations.

Supports:
    - Constant dollar (4% rule, Bengen 1994)
    - Constant percentage
    - Guyton-Klinger guardrails

References:
    Guyton, J. T. & Klinger, W. J. (2006).
        "Decision Rules and Maximum Initial Withdrawal Rates."
    Kitces, M. (2008+). Rising equity glidepath research.

"""

from __future__ import annotations


def constant_dollar_withdrawal(
    initial_withdrawal: float,
    year: int,
    inflation_rate: float,
) -> float:
    """Calculate inflation-adjusted constant dollar withdrawal.

    Args:
        initial_withdrawal: First year withdrawal amount.
        year: Current year (0-indexed).
        inflation_rate: Annual inflation rate.

    Returns:
        Inflation-adjusted withdrawal amount for the given year.

    Raises:
        NotImplementedError: Placeholder until implementation is complete.

    """
    raise NotImplementedError("Withdrawal strategies not yet implemented")


def guyton_klinger_withdrawal(
    initial_withdrawal: float,
    year: int,
    inflation_rate: float,
    portfolio_value: float,
    previous_portfolio_value: float,
) -> float:
    """Calculate withdrawal using Guyton-Klinger guardrail rules.

    Args:
        initial_withdrawal: First year withdrawal amount.
        year: Current year (0-indexed).
        inflation_rate: Annual inflation rate.
        portfolio_value: Current portfolio value.
        previous_portfolio_value: Portfolio value at start of previous year.

    Returns:
        Guardrail-adjusted withdrawal amount.

    Raises:
        NotImplementedError: Placeholder until implementation is complete.

    """
    raise NotImplementedError("Guyton-Klinger withdrawal not yet implemented")
