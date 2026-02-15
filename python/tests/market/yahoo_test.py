"""Tests for Yahoo Finance market data adapter."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from portfolioos.market.yahoo import (
    _validate_dates,
    fetch_dividends,
    fetch_info,
    fetch_price_history,
    fetch_splits,
)


def _make_mock_yf(ticker_mock: MagicMock) -> MagicMock:
    """Create a mock yfinance module that returns the given ticker."""
    yf_mock = MagicMock()
    yf_mock.Ticker.return_value = ticker_mock
    return yf_mock


def _patch_require(yf_mock: MagicMock):
    """Patch _require_yfinance to return mocked yfinance + real pandas."""
    return patch(
        "portfolioos.market.yahoo._require_yfinance",
        return_value=(yf_mock, pd),
    )


class TestValidateDates:
    """Tests for date validation helper."""

    def test_valid_dates(self):
        start, end = _validate_dates("2024-01-01", "2024-01-31")
        assert start == "2024-01-01"
        assert end == "2024-01-31"

    def test_same_date(self):
        start, end = _validate_dates("2024-06-15", "2024-06-15")
        assert start == end

    def test_invalid_format(self):
        with pytest.raises(ValueError, match="Invalid date format"):
            _validate_dates("01/01/2024", "2024-01-31")

    def test_start_after_end(self):
        with pytest.raises(ValueError, match="must be <="):
            _validate_dates("2024-12-31", "2024-01-01")


class TestFetchPriceHistory:
    """Tests for Yahoo Finance price history fetcher (mocked)."""

    def test_empty_symbol_raises(self):
        with pytest.raises(ValueError, match="non-empty"):
            fetch_price_history("", "2024-01-01", "2024-01-31")

    def test_whitespace_symbol_raises(self):
        with pytest.raises(ValueError, match="non-empty"):
            fetch_price_history("   ", "2024-01-01", "2024-01-31")

    def test_returns_list_of_dicts(self):
        mock_ticker = MagicMock()
        idx = pd.DatetimeIndex(["2024-01-02", "2024-01-03"])
        df = pd.DataFrame(
            {
                "Open": [100.0, 101.0],
                "High": [105.0, 106.0],
                "Low": [99.0, 100.0],
                "Close": [104.0, 105.0],
                "Adj Close": [103.5, 104.5],
                "Volume": [1000000, 1200000],
            },
            index=idx,
        )
        mock_ticker.history.return_value = df
        yf_mock = _make_mock_yf(mock_ticker)

        with _patch_require(yf_mock):
            result = fetch_price_history("AAPL", "2024-01-01", "2024-01-05")

        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(r, dict) for r in result)

    def test_contains_required_fields(self):
        mock_ticker = MagicMock()
        idx = pd.DatetimeIndex(["2024-01-02"])
        df = pd.DataFrame(
            {
                "Open": [150.0],
                "High": [155.0],
                "Low": [148.0],
                "Close": [153.0],
                "Adj Close": [152.5],
                "Volume": [500000],
            },
            index=idx,
        )
        mock_ticker.history.return_value = df
        yf_mock = _make_mock_yf(mock_ticker)

        with _patch_require(yf_mock):
            result = fetch_price_history("VTI", "2024-01-01", "2024-01-05")

        required = {"date", "open", "high", "low", "close", "adj_close", "volume"}
        for row in result:
            assert required.issubset(row.keys())

    def test_empty_result(self):
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame()
        yf_mock = _make_mock_yf(mock_ticker)

        with _patch_require(yf_mock):
            result = fetch_price_history("INVALID", "2024-01-01", "2024-01-31")

        assert result == []


class TestFetchDividends:
    """Tests for dividend fetcher (mocked)."""

    def test_empty_symbol_raises(self):
        with pytest.raises(ValueError, match="non-empty"):
            fetch_dividends("", "2024-01-01", "2024-12-31")

    def test_returns_dividend_records(self):
        mock_ticker = MagicMock()
        idx = pd.DatetimeIndex(["2024-03-15", "2024-06-15"])
        mock_ticker.dividends = pd.Series([0.25, 0.26], index=idx)
        yf_mock = _make_mock_yf(mock_ticker)

        with _patch_require(yf_mock):
            result = fetch_dividends("AAPL", "2024-01-01", "2024-12-31")

        assert len(result) == 2
        assert "date" in result[0]
        assert "dividend" in result[0]

    def test_empty_dividends(self):
        mock_ticker = MagicMock()
        mock_ticker.dividends = pd.Series(dtype=float)
        yf_mock = _make_mock_yf(mock_ticker)

        with _patch_require(yf_mock):
            result = fetch_dividends("BRK-A", "2024-01-01", "2024-12-31")

        assert result == []


class TestFetchSplits:
    """Tests for stock split fetcher (mocked)."""

    def test_empty_symbol_raises(self):
        with pytest.raises(ValueError, match="non-empty"):
            fetch_splits("", "2020-01-01", "2024-12-31")

    def test_returns_split_records(self):
        mock_ticker = MagicMock()
        idx = pd.DatetimeIndex(["2020-08-31"])
        mock_ticker.splits = pd.Series([4.0], index=idx)
        yf_mock = _make_mock_yf(mock_ticker)

        with _patch_require(yf_mock):
            result = fetch_splits("AAPL", "2020-01-01", "2024-12-31")

        assert len(result) == 1
        assert result[0]["ratio"] == 4.0


class TestFetchInfo:
    """Tests for fundamental info fetcher (mocked)."""

    def test_empty_symbol_raises(self):
        with pytest.raises(ValueError, match="non-empty"):
            fetch_info("")

    def test_returns_info_dict(self):
        mock_ticker = MagicMock()
        mock_ticker.info = {
            "marketCap": 3000000000000,
            "trailingPE": 28.5,
            "shortName": "Apple Inc.",
            "sector": "Technology",
            "currency": "USD",
        }
        yf_mock = _make_mock_yf(mock_ticker)

        with _patch_require(yf_mock):
            result = fetch_info("AAPL")

        assert result["symbol"] == "AAPL"
        assert result["market_cap"] == 3000000000000
        assert result["pe_ratio"] == 28.5
        assert result["name"] == "Apple Inc."

    def test_missing_fields_omitted(self):
        mock_ticker = MagicMock()
        mock_ticker.info = {"shortName": "Test ETF"}
        yf_mock = _make_mock_yf(mock_ticker)

        with _patch_require(yf_mock):
            result = fetch_info("VTI")

        assert "symbol" in result
        assert "name" in result
        assert "market_cap" not in result
        assert "pe_ratio" not in result
