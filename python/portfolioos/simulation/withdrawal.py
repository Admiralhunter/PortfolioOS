"""Withdrawal strategy implementations.

Supports:
    - Constant dollar (4% rule, Bengen 1994)
    - Constant percentage
    - Guyton-Klinger guardrails

References:
    Bengen, W. P. (1994). "Determining Withdrawal Rates Using Historical Data."
    Guyton, J. T. & Klinger, W. J. (2006).
        "Decision Rules and Maximum Initial Withdrawal Rates."
    Kitces, M. (2008+). Rising equity glidepath research.

"""

from __future__ import annotations

# Guyton-Klinger guardrail thresholds (Guyton & Klinger, 2006)
_GK_CEILING_MULTIPLIER = 1.2  # withdrawal rate 20% above initial triggers cut
_GK_FLOOR_MULTIPLIER = 0.8  # withdrawal rate 20% below initial triggers raise
_GK_ADJUSTMENT = 0.10  # 10% cut or raise when guardrail is hit


def constant_dollar_withdrawal(
    initial_withdrawal: float,
    year: int,
    inflation_rate: float,
) -> float:
    """Calculate inflation-adjusted constant dollar withdrawal.

    The "4% rule" (Bengen, 1994): withdraw a fixed real dollar amount
    each year, adjusted upward for inflation.

    Args:
        initial_withdrawal: First year withdrawal amount.
        year: Current year (0-indexed). Year 0 returns initial_withdrawal.
        inflation_rate: Annual inflation rate (e.g., 0.03 for 3%).

    Returns:
        Inflation-adjusted withdrawal amount for the given year.

    """
    return initial_withdrawal * (1.0 + inflation_rate) ** year


def guyton_klinger_withdrawal(
    initial_withdrawal: float,
    year: int,
    inflation_rate: float,
    portfolio_value: float,
    previous_portfolio_value: float,
) -> float:
    """Calculate withdrawal using Guyton-Klinger guardrail rules.

    Applies three decision rules from Guyton & Klinger (2006):

    1. **Inflation rule**: adjust for inflation unless the portfolio
       declined AND the current withdrawal rate already exceeds
       the initial rate.
    2. **Capital preservation rule**: if the current withdrawal rate
       exceeds 120% of the initial rate, cut the withdrawal by 10%.
    3. **Prosperity rule**: if the current withdrawal rate falls below
       80% of the initial rate, increase the withdrawal by 10%.

    Args:
        initial_withdrawal: First year withdrawal amount.
        year: Current year (0-indexed). Year 0 returns initial_withdrawal.
        inflation_rate: Annual inflation rate (e.g., 0.03 for 3%).
        portfolio_value: Current portfolio value.
        previous_portfolio_value: Portfolio value at start of previous year.

    Returns:
        Guardrail-adjusted withdrawal amount.

    """
    if year == 0:
        return initial_withdrawal

    # Start with inflation-adjusted base
    base_withdrawal = initial_withdrawal * (1.0 + inflation_rate) ** year
    initial_rate = initial_withdrawal / previous_portfolio_value

    # Inflation rule: skip inflation adjustment if portfolio declined
    # and withdrawal rate already exceeds initial rate
    portfolio_declined = portfolio_value < previous_portfolio_value
    current_rate = base_withdrawal / portfolio_value
    if portfolio_declined and current_rate > initial_rate:
        base_withdrawal = initial_withdrawal * (1.0 + inflation_rate) ** (year - 1)
        current_rate = base_withdrawal / portfolio_value

    # Capital preservation rule: cut 10% if rate exceeds ceiling
    ceiling = initial_rate * _GK_CEILING_MULTIPLIER
    if current_rate > ceiling:
        base_withdrawal *= 1.0 - _GK_ADJUSTMENT

    # Prosperity rule: raise 10% if rate falls below floor
    floor = initial_rate * _GK_FLOOR_MULTIPLIER
    if current_rate < floor:
        base_withdrawal *= 1.0 + _GK_ADJUSTMENT

    return base_withdrawal
