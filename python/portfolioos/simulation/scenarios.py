"""Enhanced simulation with scenarios, life events, and sensitivity analysis.

Extends the base Monte Carlo engine with multiple withdrawal strategies,
life event modeling, and parameter sensitivity sweeps.

References:
    Bengen, W. P. (1994). "Determining Withdrawal Rates Using Historical Data."
    Trinity Study (Cooley, Hubbard, Walz, 1998).
    Guyton, J. T. & Klinger, W. J. (2006).
        "Decision Rules and Maximum Initial Withdrawal Rates."

"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

import numpy as np

from portfolioos.analysis.statistics import bootstrap_returns
from portfolioos.simulation.withdrawal import (
    constant_dollar_withdrawal,
    guyton_klinger_withdrawal,
)

if TYPE_CHECKING:
    from numpy.typing import NDArray

_PERCENTILE_LEVELS = (5, 25, 50, 75, 95)


class WithdrawalStrategy(Enum):
    """Supported withdrawal strategies."""

    CONSTANT_DOLLAR = "constant_dollar"
    CONSTANT_PERCENTAGE = "constant_percentage"
    GUYTON_KLINGER = "guyton_klinger"


@dataclass
class LifeEvent:
    """A one-time or recurring financial event during simulation.

    Attributes:
        year: Simulation year when event occurs (0-indexed).
        event_type: One of "expense", "income_change", "windfall",
            "savings_rate_change".
        amount: Dollar amount or rate change.

    """

    year: int
    event_type: str
    amount: float


@dataclass
class ScenarioConfig:
    """Configuration for a scenario-based simulation.

    Attributes:
        initial_portfolio: Starting portfolio value.
        annual_withdrawal: Base annual withdrawal amount.
        return_distribution: Historical returns for bootstrapping.
        withdrawal_strategy: Strategy enum value.
        life_events: List of LifeEvent objects.
        inflation_rate: Annual inflation rate.
        n_trials: Number of Monte Carlo trials.
        n_years: Simulation horizon in years.
        seed: Random seed for reproducibility.

    """

    initial_portfolio: float
    annual_withdrawal: float
    return_distribution: list[float] | NDArray[np.float64]
    withdrawal_strategy: str = "constant_dollar"
    life_events: list[dict[str, Any]] = field(default_factory=list)
    inflation_rate: float = 0.03
    n_trials: int = 10_000
    n_years: int = 50
    seed: int | None = None


def run_scenario(  # noqa: PLR0913
    initial_portfolio: float,
    annual_withdrawal: float,
    return_distribution: list[float] | NDArray[np.float64],
    withdrawal_strategy: str = "constant_dollar",
    life_events: list[dict[str, Any]] | None = None,
    inflation_rate: float = 0.03,
    n_trials: int = 10_000,
    n_years: int = 50,
    seed: int | None = None,
) -> dict[str, Any]:
    """Run a scenario-based Monte Carlo simulation.

    Supports multiple withdrawal strategies and life events that
    modify the portfolio at specified years.

    Args:
        initial_portfolio: Starting portfolio value in dollars.
        annual_withdrawal: Base annual withdrawal amount.
        return_distribution: Historical returns for bootstrapping.
        withdrawal_strategy: One of "constant_dollar",
            "constant_percentage", "guyton_klinger".
        life_events: List of event dicts with keys: year, type, amount.
        inflation_rate: Annual inflation rate.
        n_trials: Number of simulation trials.
        n_years: Time horizon in years.
        seed: Random seed for reproducibility.

    Returns:
        Dict with portfolio_values, success_rate, percentiles,
        median_final_value, and strategy used.

    """
    if life_events is None:
        life_events = []

    returns_arr = np.asarray(return_distribution, dtype=np.float64)
    returns = bootstrap_returns(
        returns_arr, n_samples=n_trials, n_years=n_years, seed=seed
    )

    # Build life events index for quick lookup
    events_by_year: dict[int, list[dict[str, Any]]] = {}
    for event in life_events:
        yr = int(event["year"])
        if yr not in events_by_year:
            events_by_year[yr] = []
        events_by_year[yr].append(event)

    portfolio = np.empty((n_trials, n_years + 1), dtype=np.float64)
    portfolio[:, 0] = initial_portfolio

    for yr in range(n_years):
        withdrawal = _compute_withdrawal(
            strategy=withdrawal_strategy,
            initial_withdrawal=annual_withdrawal,
            year=yr,
            inflation_rate=inflation_rate,
            portfolio_values=portfolio[:, yr],
            initial_portfolio=initial_portfolio,
            prev_portfolio=portfolio[:, max(0, yr - 1)],
        )

        # Apply life events for this year
        event_adjustment = _compute_event_adjustment(events_by_year.get(yr, []))

        grown = portfolio[:, yr] * (1.0 + returns[:, yr])
        portfolio[:, yr + 1] = np.maximum(grown - withdrawal + event_adjustment, 0.0)

    success_rate = float(np.mean(portfolio[:, -1] > 0))

    percentiles: dict[int, list[float]] = {}
    for p in _PERCENTILE_LEVELS:
        percentiles[p] = np.percentile(portfolio, p, axis=0).tolist()

    return {
        "portfolio_values": portfolio,
        "success_rate": success_rate,
        "percentiles": percentiles,
        "median_final_value": float(np.median(portfolio[:, -1])),
        "strategy": withdrawal_strategy,
    }


def sensitivity_analysis(  # noqa: PLR0913
    initial_portfolio: float,
    annual_withdrawal: float,
    return_distribution: list[float] | NDArray[np.float64],
    vary_param: str,
    values: list[float],
    withdrawal_strategy: str = "constant_dollar",
    inflation_rate: float = 0.03,
    n_trials: int = 10_000,
    n_years: int = 50,
    seed: int | None = None,
) -> list[dict[str, Any]]:
    """Run simulation across a range of one parameter.

    Args:
        initial_portfolio: Starting portfolio value.
        annual_withdrawal: Base annual withdrawal amount.
        return_distribution: Historical returns for bootstrapping.
        vary_param: Parameter to vary. One of "withdrawal_rate",
            "inflation_rate", "n_years".
        values: List of values to test for the varied parameter.
        withdrawal_strategy: Withdrawal strategy to use.
        inflation_rate: Annual inflation rate (used when not varied).
        n_trials: Number of trials per simulation.
        n_years: Time horizon (used when not varied).
        seed: Random seed for reproducibility.

    Returns:
        List of result dicts, one per value, each including the
        varied parameter value, success_rate, and median_final_value.

    Raises:
        ValueError: If vary_param is not recognized.

    """
    valid_params = {"withdrawal_rate", "inflation_rate", "n_years"}
    if vary_param not in valid_params:
        msg = f"vary_param must be one of {valid_params}, got '{vary_param}'"
        raise ValueError(msg)

    results: list[dict[str, Any]] = []

    for val in values:
        run_withdrawal = annual_withdrawal
        run_inflation = inflation_rate
        run_years = n_years

        if vary_param == "withdrawal_rate":
            run_withdrawal = initial_portfolio * val
        elif vary_param == "inflation_rate":
            run_inflation = val
        elif vary_param == "n_years":
            run_years = int(val)

        result = run_scenario(
            initial_portfolio=initial_portfolio,
            annual_withdrawal=run_withdrawal,
            return_distribution=return_distribution,
            withdrawal_strategy=withdrawal_strategy,
            inflation_rate=run_inflation,
            n_trials=n_trials,
            n_years=run_years,
            seed=seed,
        )

        results.append(
            {
                "param_name": vary_param,
                "param_value": val,
                "success_rate": result["success_rate"],
                "median_final_value": result["median_final_value"],
            }
        )

    return results


def _compute_withdrawal(
    strategy: str,
    initial_withdrawal: float,
    year: int,
    inflation_rate: float,
    portfolio_values: NDArray[np.float64],
    initial_portfolio: float,
    prev_portfolio: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Compute withdrawal amounts for all trials at a given year.

    Args:
        strategy: Withdrawal strategy name.
        initial_withdrawal: Base withdrawal amount.
        year: Current simulation year.
        inflation_rate: Annual inflation rate.
        portfolio_values: Current portfolio values (n_trials,).
        initial_portfolio: Starting portfolio value.
        prev_portfolio: Previous year portfolio values.

    Returns:
        Array of withdrawal amounts (n_trials,).

    """
    n_trials = len(portfolio_values)

    if strategy == "constant_dollar":
        amount = constant_dollar_withdrawal(initial_withdrawal, year, inflation_rate)
        return np.full(n_trials, amount, dtype=np.float64)

    if strategy == "constant_percentage":
        rate = initial_withdrawal / initial_portfolio if initial_portfolio > 0 else 0.04
        return portfolio_values * rate

    if strategy == "guyton_klinger":
        # Vectorized approximation of Guyton-Klinger
        result = np.empty(n_trials, dtype=np.float64)
        for i in range(n_trials):
            result[i] = guyton_klinger_withdrawal(
                initial_withdrawal=initial_withdrawal,
                year=year,
                inflation_rate=inflation_rate,
                portfolio_value=max(portfolio_values[i], 1.0),
                previous_portfolio_value=max(prev_portfolio[i], 1.0),
            )
        return result

    # Default fallback
    amount = constant_dollar_withdrawal(initial_withdrawal, year, inflation_rate)
    return np.full(n_trials, amount, dtype=np.float64)


def _compute_event_adjustment(events: list[dict[str, Any]]) -> float:
    """Compute net portfolio adjustment from life events.

    Args:
        events: List of life event dicts for the current year.

    Returns:
        Net dollar adjustment (positive = inflow, negative = outflow).

    """
    adjustment = 0.0
    for event in events:
        event_type = event.get("type", "")
        amount = float(event.get("amount", 0))

        if event_type == "windfall":
            adjustment += amount
        elif event_type == "expense":
            adjustment -= amount
        elif event_type == "income_change":
            adjustment += amount
        # savings_rate_change modifies contribution but not directly
        # modeled as a one-time adjustment here

    return adjustment
