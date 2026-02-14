"""Statistical analysis utilities.

Provides distribution fitting, percentile ranking,
and other statistical methods for portfolio analysis.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


def percentile_rank(
    values: NDArray[np.float64],
    target: float,
) -> float:
    """Calculate the percentile rank of a target value within a distribution.

    Args:
        values: Array of observed values.
        target: The value to rank.

    Returns:
        Percentile rank as a float between 0 and 100.

    Raises:
        NotImplementedError: Placeholder until implementation is complete.

    """
    raise NotImplementedError("Percentile rank not yet implemented")


def bootstrap_returns(
    historical_returns: NDArray[np.float64],
    n_samples: int,
    n_years: int,
    seed: int | None = None,
) -> NDArray[np.float64]:
    """Generate bootstrapped return sequences from historical data.

    Args:
        historical_returns: Array of historical annual returns.
        n_samples: Number of bootstrap samples to generate.
        n_years: Length of each sample sequence in years.
        seed: Random seed for reproducibility.

    Returns:
        NDArray of shape (n_samples, n_years) with bootstrapped returns.

    Raises:
        NotImplementedError: Placeholder until implementation is complete.

    """
    raise NotImplementedError("Bootstrap returns not yet implemented")
