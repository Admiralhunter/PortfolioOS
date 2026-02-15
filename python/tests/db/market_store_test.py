"""Tests for the market data store."""

from __future__ import annotations

import pytest
from portfolioos.db.connection import init_memory_db
from portfolioos.db.market_store import (
    get_latest_date,
    query_macro_indicators,
    query_price_history,
    upsert_dividends,
    upsert_macro_indicators,
    upsert_price_history,
    upsert_splits,
)


@pytest.fixture
def db():
    conn = init_memory_db()
    yield conn
    conn.close()


class TestUpsertPriceHistory:
    """Tests for price history upsert."""

    def test_insert_records(self, db):
        records = [
            {
                "symbol": "AAPL",
                "date": "2024-01-02",
                "open": 185.0,
                "high": 186.0,
                "low": 184.0,
                "close": 185.5,
                "adj_close": 185.0,
                "volume": 1000000,
            },
            {
                "symbol": "AAPL",
                "date": "2024-01-03",
                "open": 185.5,
                "high": 187.0,
                "low": 185.0,
                "close": 186.0,
                "adj_close": 185.5,
                "volume": 1200000,
            },
        ]
        count = upsert_price_history(db, records)
        assert count == 2

    def test_upsert_overwrites(self, db):
        record = {
            "symbol": "AAPL",
            "date": "2024-01-02",
            "open": 185.0,
            "high": 186.0,
            "low": 184.0,
            "close": 185.5,
            "adj_close": 185.0,
            "volume": 1000000,
        }
        upsert_price_history(db, [record])

        # Update the close price
        record["close"] = 190.0
        upsert_price_history(db, [record])

        result = query_price_history(db, "AAPL")
        assert len(result) == 1
        assert result[0]["close"] == 190.0

    def test_empty_records(self, db):
        assert upsert_price_history(db, []) == 0

    def test_missing_symbol_skipped(self, db):
        records = [
            {
                "date": "2024-01-02",
                "open": 1,
                "high": 2,
                "low": 0.5,
                "close": 1.5,
                "volume": 100,
            },
        ]
        assert upsert_price_history(db, records) == 0


class TestQueryPriceHistory:
    """Tests for price history queries."""

    def test_filter_by_date_range(self, db):
        records = [
            {
                "symbol": "VTI",
                "date": f"2024-01-{d:02d}",
                "open": 200,
                "high": 205,
                "low": 198,
                "close": 203,
                "adj_close": 203,
                "volume": 500000,
            }
            for d in range(2, 12)
        ]
        upsert_price_history(db, records)

        result = query_price_history(
            db,
            "VTI",
            start_date="2024-01-05",
            end_date="2024-01-08",
        )
        assert len(result) == 4

    def test_no_data_returns_empty(self, db):
        result = query_price_history(db, "UNKNOWN")
        assert result == []


class TestUpsertMacroIndicators:
    """Tests for macro indicator upsert."""

    def test_insert_records(self, db):
        records = [
            {"series_id": "FEDFUNDS", "date": "2024-01-01", "value": 5.33},
            {"series_id": "FEDFUNDS", "date": "2024-02-01", "value": 5.33},
        ]
        count = upsert_macro_indicators(db, records)
        assert count == 2

    def test_query_by_series(self, db):
        records = [
            {"series_id": "FEDFUNDS", "date": "2024-01-01", "value": 5.33},
            {"series_id": "UNRATE", "date": "2024-01-01", "value": 3.7},
        ]
        upsert_macro_indicators(db, records)

        result = query_macro_indicators(db, "FEDFUNDS")
        assert len(result) == 1
        assert result[0]["value"] == 5.33


class TestUpsertDividends:
    """Tests for dividend upsert."""

    def test_insert_dividends(self, db):
        records = [
            {"date": "2024-03-15", "dividend": 0.25},
            {"date": "2024-06-15", "dividend": 0.26},
        ]
        count = upsert_dividends(db, "AAPL", records)
        assert count == 2


class TestUpsertSplits:
    """Tests for splits upsert."""

    def test_insert_splits(self, db):
        records = [{"date": "2020-08-31", "ratio": 4.0}]
        count = upsert_splits(db, "AAPL", records)
        assert count == 1


class TestGetLatestDate:
    """Tests for latest date lookup."""

    def test_returns_latest_date(self, db):
        records = [
            {
                "symbol": "AAPL",
                "date": "2024-01-02",
                "open": 1,
                "high": 2,
                "low": 0.5,
                "close": 1.5,
                "adj_close": 1.5,
                "volume": 100,
            },
            {
                "symbol": "AAPL",
                "date": "2024-01-05",
                "open": 1,
                "high": 2,
                "low": 0.5,
                "close": 1.5,
                "adj_close": 1.5,
                "volume": 100,
            },
        ]
        upsert_price_history(db, records)

        latest = get_latest_date(db, "price_history", "AAPL")
        assert latest == "2024-01-05"

    def test_no_data_returns_none(self, db):
        assert get_latest_date(db, "price_history", "UNKNOWN") is None

    def test_invalid_table_raises(self, db):
        with pytest.raises(ValueError, match="Table must be one of"):
            get_latest_date(db, "invalid_table", "AAPL")

    def test_invalid_column_raises(self, db):
        with pytest.raises(ValueError, match="id_column must be one of"):
            get_latest_date(db, "price_history", "AAPL", id_column="bad_col")
