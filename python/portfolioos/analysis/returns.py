"""Return calculation utilities.

Provides functions for computing various return metrics:
CAGR, rolling returns, drawdown analysis, and total return.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray


def cagr(
    start_value: float,
    end_value: float,
    n_years: float,
) -> float:
    """Calculate Compound Annual Growth Rate.

    Args:
        start_value: Initial portfolio or investment value. Must be positive.
        end_value: Final portfolio or investment value. Must be non-negative.
        n_years: Number of years (can be fractional). Must be positive.

    Returns:
        CAGR as a decimal (e.g., 0.07 for 7%).

    Raises:
        ValueError: If start_value <= 0, end_value < 0, or n_years <= 0.

    """
    if start_value <= 0:
        msg = f"start_value must be positive, got {start_value}"
        raise ValueError(msg)
    if end_value < 0:
        msg = f"end_value must be non-negative, got {end_value}"
        raise ValueError(msg)
    if n_years <= 0:
        msg = f"n_years must be positive, got {n_years}"
        raise ValueError(msg)
    return float((end_value / start_value) ** (1.0 / n_years) - 1.0)


def max_drawdown(values: NDArray[np.float64]) -> float:
    """Calculate the maximum drawdown from a series of portfolio values.

    Args:
        values: Array of portfolio values over time. Must have at least 2 elements.

    Returns:
        Maximum drawdown as a negative decimal (e.g., -0.1818 for 18.18% drawdown).
        Returns 0.0 if the series is monotonically increasing.

    Raises:
        ValueError: If values has fewer than 2 elements.

    """
    if len(values) < 2:  # noqa: PLR2004
        msg = f"values must have at least 2 elements, got {len(values)}"
        raise ValueError(msg)
    running_max = np.maximum.accumulate(values)
    drawdowns = (values - running_max) / running_max
    return float(np.min(drawdowns))
