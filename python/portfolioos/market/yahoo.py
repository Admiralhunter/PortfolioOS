"""Yahoo Finance market data adapter.

Fetches daily OHLCV data, fundamentals, dividends, and splits
via the yfinance library. This is the primary data source for equities.

Note:
    yfinance uses an unofficial Yahoo Finance API. Rate limiting
    and respectful request patterns are required.

    yfinance is an optional dependency (install with ``pip install
    portfolioos[market]``). Functions raise ``ImportError`` at call
    time if the library is not installed.

"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

# Minimum date range that yfinance can handle reliably
_MIN_HISTORY_DAYS = 1


def _require_yfinance() -> tuple[Any, Any]:
    """Lazy-import yfinance and pandas.

    Returns:
        Tuple of (yfinance module, pandas module).

    Raises:
        ImportError: If yfinance is not installed.

    """
    try:
        import pandas as pd
        import yfinance as yf
    except ImportError as exc:
        msg = (
            "yfinance is required for Yahoo Finance data. "
            "Install with: pip install portfolioos[market]"
        )
        raise ImportError(msg) from exc
    return yf, pd


def _validate_dates(start_date: str, end_date: str) -> tuple[str, str]:
    """Validate and normalize date strings.

    Args:
        start_date: Start date in ISO format (YYYY-MM-DD).
        end_date: End date in ISO format (YYYY-MM-DD).

    Returns:
        Tuple of validated (start_date, end_date).

    Raises:
        ValueError: If dates are invalid or start > end.

    """
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError as exc:
        msg = f"Invalid date format. Expected YYYY-MM-DD: {exc}"
        raise ValueError(msg) from exc

    if start > end:
        msg = f"start_date ({start_date}) must be <= end_date ({end_date})"
        raise ValueError(msg)

    return start_date, end_date


def fetch_price_history(
    symbol: str,
    start_date: str,
    end_date: str,
) -> list[dict[str, Any]]:
    """Fetch daily OHLCV price history for a symbol.

    Args:
        symbol: Ticker symbol (e.g., "AAPL", "VTI").
        start_date: Start date in ISO format (YYYY-MM-DD).
        end_date: End date in ISO format (YYYY-MM-DD).

    Returns:
        List of dicts with keys: date, open, high, low, close, adj_close, volume.
        Empty list if no data is available for the given range.

    Raises:
        ValueError: If dates are invalid or symbol is empty.
        ImportError: If yfinance is not installed.

    """
    if not symbol or not symbol.strip():
        msg = "symbol must be a non-empty string"
        raise ValueError(msg)

    yf, pd = _require_yfinance()
    start_date, end_date = _validate_dates(start_date, end_date)

    ticker = yf.Ticker(symbol.strip().upper())
    df = ticker.history(start=start_date, end=end_date, auto_adjust=False)

    if df.empty:
        logger.warning(
            "No price data for %s (%s to %s)",
            symbol,
            start_date,
            end_date,
        )
        return []

    records: list[dict[str, Any]] = []
    for date_idx, row in df.iterrows():
        date_str = pd.Timestamp(date_idx).strftime("%Y-%m-%d")
        records.append(
            {
                "date": date_str,
                "open": round(float(row["Open"]), 4),
                "high": round(float(row["High"]), 4),
                "low": round(float(row["Low"]), 4),
                "close": round(float(row["Close"]), 4),
                "adj_close": round(float(row.get("Adj Close", row["Close"])), 4),
                "volume": int(row["Volume"]),
            }
        )

    return records


def fetch_dividends(
    symbol: str,
    start_date: str,
    end_date: str,
) -> list[dict[str, Any]]:
    """Fetch dividend history for a symbol.

    Args:
        symbol: Ticker symbol (e.g., "AAPL", "VTI").
        start_date: Start date in ISO format (YYYY-MM-DD).
        end_date: End date in ISO format (YYYY-MM-DD).

    Returns:
        List of dicts with keys: date, dividend.
        Empty list if no dividends in the range.

    Raises:
        ValueError: If dates are invalid or symbol is empty.
        ImportError: If yfinance is not installed.

    """
    if not symbol or not symbol.strip():
        msg = "symbol must be a non-empty string"
        raise ValueError(msg)

    yf, pd = _require_yfinance()
    start_date, end_date = _validate_dates(start_date, end_date)

    ticker = yf.Ticker(symbol.strip().upper())
    divs = ticker.dividends

    if divs.empty:
        return []

    # Filter by date range
    mask = (divs.index >= start_date) & (divs.index <= end_date)
    filtered = divs[mask]

    return [
        {
            "date": pd.Timestamp(date_idx).strftime("%Y-%m-%d"),
            "dividend": round(float(amount), 6),
        }
        for date_idx, amount in filtered.items()
    ]


def fetch_splits(
    symbol: str,
    start_date: str,
    end_date: str,
) -> list[dict[str, Any]]:
    """Fetch stock split history for a symbol.

    Args:
        symbol: Ticker symbol (e.g., "AAPL", "TSLA").
        start_date: Start date in ISO format (YYYY-MM-DD).
        end_date: End date in ISO format (YYYY-MM-DD).

    Returns:
        List of dicts with keys: date, ratio (e.g., 4.0 for a 4:1 split).
        Empty list if no splits in the range.

    Raises:
        ValueError: If dates are invalid or symbol is empty.
        ImportError: If yfinance is not installed.

    """
    if not symbol or not symbol.strip():
        msg = "symbol must be a non-empty string"
        raise ValueError(msg)

    yf, pd = _require_yfinance()
    start_date, end_date = _validate_dates(start_date, end_date)

    ticker = yf.Ticker(symbol.strip().upper())
    splits = ticker.splits

    if splits.empty:
        return []

    mask = (splits.index >= start_date) & (splits.index <= end_date)
    filtered = splits[mask]

    return [
        {
            "date": pd.Timestamp(date_idx).strftime("%Y-%m-%d"),
            "ratio": float(ratio),
        }
        for date_idx, ratio in filtered.items()
    ]


def fetch_info(symbol: str) -> dict[str, Any]:
    """Fetch fundamental info for a symbol.

    Args:
        symbol: Ticker symbol (e.g., "AAPL", "VTI").

    Returns:
        Dict with available fundamentals: market_cap, pe_ratio,
        dividend_yield, sector, industry, name, currency, exchange.
        Missing fields are omitted rather than set to None.

    Raises:
        ValueError: If symbol is empty.
        ImportError: If yfinance is not installed.

    """
    if not symbol or not symbol.strip():
        msg = "symbol must be a non-empty string"
        raise ValueError(msg)

    yf, _pd = _require_yfinance()

    ticker = yf.Ticker(symbol.strip().upper())
    raw_info = ticker.info

    field_map: dict[str, str] = {
        "marketCap": "market_cap",
        "trailingPE": "pe_ratio",
        "forwardPE": "forward_pe_ratio",
        "dividendYield": "dividend_yield",
        "sector": "sector",
        "industry": "industry",
        "shortName": "name",
        "longName": "long_name",
        "currency": "currency",
        "exchange": "exchange",
        "fiftyTwoWeekHigh": "fifty_two_week_high",
        "fiftyTwoWeekLow": "fifty_two_week_low",
        "fiftyDayAverage": "fifty_day_average",
        "twoHundredDayAverage": "two_hundred_day_average",
    }

    result: dict[str, Any] = {"symbol": symbol.strip().upper()}
    for yf_key, our_key in field_map.items():
        value = raw_info.get(yf_key)
        if value is not None:
            result[our_key] = value

    return result
