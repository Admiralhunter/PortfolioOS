"""Return calculation utilities.

Provides functions for computing various return metrics:
CAGR, rolling returns, drawdown analysis, and total return.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


def cagr(
    start_value: float,
    end_value: float,
    n_years: float,
) -> float:
    """Calculate Compound Annual Growth Rate.

    Args:
        start_value: Initial portfolio or investment value.
        end_value: Final portfolio or investment value.
        n_years: Number of years (can be fractional).

    Returns:
        CAGR as a decimal (e.g., 0.07 for 7%).

    Raises:
        NotImplementedError: Placeholder until implementation is complete.

    """
    raise NotImplementedError("CAGR calculation not yet implemented")


def max_drawdown(values: NDArray[np.float64]) -> float:
    """Calculate the maximum drawdown from a series of portfolio values.

    Args:
        values: Array of portfolio values over time.

    Returns:
        Maximum drawdown as a negative decimal (e.g., -0.35 for 35% drawdown).

    Raises:
        NotImplementedError: Placeholder until implementation is complete.

    """
    raise NotImplementedError("Max drawdown calculation not yet implemented")
