"""FRED (Federal Reserve Economic Data) adapter.

Fetches macro economic indicators: interest rates, inflation,
unemployment, and other series from the FRED API.

Note:
    Requires a free API key from https://fred.stlouisfed.org/docs/api/api_key.html
    Rate limit: 120 requests per minute.

"""

from __future__ import annotations

import logging
import os
from typing import Any

import pandas as pd
from fredapi import Fred

logger = logging.getLogger(__name__)

# Common FRED series IDs used in PortfolioOS
SERIES_FEDERAL_FUNDS = "FEDFUNDS"
SERIES_CPI = "CPIAUCSL"
SERIES_UNEMPLOYMENT = "UNRATE"
SERIES_10Y_TREASURY = "DGS10"
SERIES_2Y_TREASURY = "DGS2"
SERIES_30Y_MORTGAGE = "MORTGAGE30US"
SERIES_M2_MONEY = "M2SL"
SERIES_GDP = "GDP"
SERIES_SP500 = "SP500"
SERIES_VIX = "VIXCLS"

# Default set for macro dashboard
DEFAULT_SERIES: list[str] = [
    SERIES_FEDERAL_FUNDS,
    SERIES_CPI,
    SERIES_UNEMPLOYMENT,
    SERIES_10Y_TREASURY,
    SERIES_SP500,
]


def _get_fred_client(api_key: str | None = None) -> Fred:
    """Create a FRED API client.

    Args:
        api_key: FRED API key. Falls back to FRED_API_KEY env var.

    Returns:
        Configured Fred client.

    Raises:
        ValueError: If no API key is provided or found in environment.

    """
    key = api_key or os.environ.get("FRED_API_KEY")
    if not key:
        msg = (
            "FRED API key required. Set FRED_API_KEY environment variable "
            "or pass api_key parameter."
        )
        raise ValueError(msg)
    return Fred(api_key=key)


def fetch_series(
    series_id: str,
    start_date: str,
    end_date: str,
    api_key: str | None = None,
) -> list[dict[str, Any]]:
    """Fetch a FRED data series.

    Args:
        series_id: FRED series ID (e.g., "FEDFUNDS", "CPIAUCSL", "UNRATE").
        start_date: Start date in ISO format (YYYY-MM-DD).
        end_date: End date in ISO format (YYYY-MM-DD).
        api_key: FRED API key. Falls back to FRED_API_KEY env var.

    Returns:
        List of dicts with keys: date, value, series_id.
        Rows with missing values (NaN) are excluded.

    Raises:
        ValueError: If series_id is empty or API key is missing.

    """
    if not series_id or not series_id.strip():
        msg = "series_id must be a non-empty string"
        raise ValueError(msg)

    client = _get_fred_client(api_key)
    data: pd.Series[float] = client.get_series(
        series_id.strip().upper(),
        observation_start=start_date,
        observation_end=end_date,
    )

    if data.empty:
        logger.warning(
            "No FRED data returned for %s (%s to %s)",
            series_id,
            start_date,
            end_date,
        )
        return []

    # Drop NaN values — FRED uses them for missing observations
    data = data.dropna()

    return [
        {
            "date": pd.Timestamp(date_idx).strftime("%Y-%m-%d"),  # type: ignore[arg-type]
            "value": round(float(value), 6),
            "series_id": series_id.strip().upper(),
        }
        for date_idx, value in data.items()
    ]


def fetch_multiple_series(
    series_ids: list[str],
    start_date: str,
    end_date: str,
    api_key: str | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Fetch multiple FRED data series.

    Args:
        series_ids: List of FRED series IDs.
        start_date: Start date in ISO format (YYYY-MM-DD).
        end_date: End date in ISO format (YYYY-MM-DD).
        api_key: FRED API key. Falls back to FRED_API_KEY env var.

    Returns:
        Dict mapping series_id to its list of observations.
        Failed series are logged and omitted from results.

    """
    results: dict[str, list[dict[str, Any]]] = {}
    for sid in series_ids:
        try:
            results[sid] = fetch_series(sid, start_date, end_date, api_key=api_key)
        except Exception:
            logger.exception("Failed to fetch FRED series %s", sid)
    return results


def fetch_series_info(
    series_id: str,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Fetch metadata about a FRED series.

    Args:
        series_id: FRED series ID.
        api_key: FRED API key. Falls back to FRED_API_KEY env var.

    Returns:
        Dict with keys: series_id, title, frequency, units,
        seasonal_adjustment, last_updated.

    Raises:
        ValueError: If series_id is empty or API key is missing.

    """
    if not series_id or not series_id.strip():
        msg = "series_id must be a non-empty string"
        raise ValueError(msg)

    client = _get_fred_client(api_key)
    info = client.get_series_info(series_id.strip().upper())

    return {
        "series_id": str(info.get("id", series_id)),
        "title": str(info.get("title", "")),
        "frequency": str(info.get("frequency", "")),
        "units": str(info.get("units", "")),
        "seasonal_adjustment": str(info.get("seasonal_adjustment", "")),
        "last_updated": str(info.get("last_updated", "")),
    }
