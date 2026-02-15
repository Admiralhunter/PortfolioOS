"""Statistical analysis utilities.

Provides distribution fitting, percentile ranking,
and other statistical methods for portfolio analysis.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from scipy import stats

if TYPE_CHECKING:
    from numpy.typing import NDArray


def percentile_rank(
    values: NDArray[np.float64],
    target: float,
) -> float:
    """Calculate the percentile rank of a target value within a distribution.

    Uses scipy.stats.percentileofscore with "rank" interpolation.

    Args:
        values: Array of observed values.
        target: The value to rank.

    Returns:
        Percentile rank as a float between 0 and 100.

    """
    return float(stats.percentileofscore(values, target, kind="rank"))


def bootstrap_returns(
    historical_returns: NDArray[np.float64],
    n_samples: int,
    n_years: int,
    seed: int | None = None,
) -> NDArray[np.float64]:
    """Generate bootstrapped return sequences from historical data.

    Draws with replacement from the historical return distribution
    to create synthetic multi-year return paths.

    Args:
        historical_returns: Array of historical annual returns.
        n_samples: Number of bootstrap samples to generate.
        n_years: Length of each sample sequence in years.
        seed: Random seed for reproducibility.

    Returns:
        NDArray of shape (n_samples, n_years) with bootstrapped returns.

    Raises:
        ValueError: If historical_returns is empty.

    """
    if len(historical_returns) == 0:
        msg = "historical_returns must not be empty"
        raise ValueError(msg)
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(historical_returns), size=(n_samples, n_years))
    return historical_returns[indices]
