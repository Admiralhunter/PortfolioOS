"""Monte Carlo simulation engine.

Implements vectorized Monte Carlo simulations for FIRE analysis.
Default: 10,000 trials over a 50-year horizon using NumPy array operations.

Performance target: 10,000 trials x 50 years < 2 seconds on modern hardware.

References:
    Bengen, W. P. (1994). "Determining Withdrawal Rates Using Historical Data."
    Trinity Study (Cooley, Hubbard, Walz, 1998).
        "Retirement Savings: Choosing a Withdrawal Rate That Is Sustainable."

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np

from portfolioos.analysis.statistics import bootstrap_returns

if TYPE_CHECKING:
    from numpy.typing import NDArray

_PERCENTILE_LEVELS = (5, 25, 50, 75, 95)


def run_simulation(
    initial_portfolio: float,
    annual_withdrawal: float,
    return_distribution: NDArray[np.float64],
    n_trials: int = 10_000,
    n_years: int = 50,
    inflation_rate: float = 0.03,
    seed: int | None = None,
) -> dict[str, Any]:
    """Run a Monte Carlo simulation for portfolio survival.

    Generates bootstrapped return sequences from historical data,
    then simulates portfolio evolution under constant-dollar withdrawals
    (Bengen, 1994) adjusted for inflation. Fully vectorized via NumPy.

    Args:
        initial_portfolio: Starting portfolio value in dollars.
        annual_withdrawal: Annual withdrawal amount in today's dollars.
        return_distribution: Array of historical annual returns to bootstrap from.
        n_trials: Number of simulation trials.
        n_years: Time horizon in years.
        inflation_rate: Annual inflation rate for withdrawal adjustment.
        seed: Random seed for reproducibility. Required for deterministic results.

    Returns:
        Dictionary containing:
            - "portfolio_values": NDArray of shape (n_trials, n_years+1)
            - "success_rate": float, fraction of trials surviving full horizon
            - "percentiles": dict mapping percentile level to path array of
              shape (n_years+1,) — keys are 5, 25, 50, 75, 95

    """
    # Bootstrap return sequences: (n_trials, n_years)
    returns = bootstrap_returns(
        return_distribution, n_samples=n_trials, n_years=n_years, seed=seed
    )

    # Pre-compute inflation-adjusted withdrawals for each year
    years = np.arange(n_years)
    withdrawals = annual_withdrawal * (1.0 + inflation_rate) ** years

    # Simulate portfolio paths: (n_trials, n_years+1)
    portfolio = np.empty((n_trials, n_years + 1), dtype=np.float64)
    portfolio[:, 0] = initial_portfolio

    for yr in range(n_years):
        grown = portfolio[:, yr] * (1.0 + returns[:, yr])
        portfolio[:, yr + 1] = np.maximum(grown - withdrawals[yr], 0.0)

    # Success = portfolio survived the full horizon (value > 0 at end)
    success_rate = float(np.mean(portfolio[:, -1] > 0))

    # Percentile paths across trials at each year
    percentiles: dict[int, NDArray[np.float64]] = {}
    for p in _PERCENTILE_LEVELS:
        percentiles[p] = np.percentile(portfolio, p, axis=0)

    return {
        "portfolio_values": portfolio,
        "success_rate": success_rate,
        "percentiles": percentiles,
    }
