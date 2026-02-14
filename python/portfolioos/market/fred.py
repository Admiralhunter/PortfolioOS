"""FRED (Federal Reserve Economic Data) adapter.

Fetches macro economic indicators: interest rates, inflation,
unemployment, and other series from the FRED API.

Note:
    Requires a free API key from https://fred.stlouisfed.org/docs/api/api_key.html
    Rate limit: 120 requests per minute.

"""

from __future__ import annotations

from typing import Any


def fetch_series(
    series_id: str,
    start_date: str,
    end_date: str,
) -> list[dict[str, Any]]:
    """Fetch a FRED data series.

    Args:
        series_id: FRED series ID (e.g., "FEDFUNDS", "CPIAUCSL", "UNRATE").
        start_date: Start date in ISO format (YYYY-MM-DD).
        end_date: End date in ISO format (YYYY-MM-DD).

    Returns:
        List of dicts with keys: date, value, series_id.

    Raises:
        NotImplementedError: Placeholder until implementation is complete.

    """
    raise NotImplementedError("FRED adapter not yet implemented")
