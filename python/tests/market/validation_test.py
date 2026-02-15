"""Tests for market data validation utilities."""

from __future__ import annotations

import pytest
from portfolioos.market.validation import detect_gaps, detect_outliers, validate_ohlcv


class TestDetectGaps:
    """Tests for time-series gap detection."""

    def test_no_gaps(self):
        # Mon-Fri consecutive trading days
        records = [
            {"date": "2024-01-08"},  # Monday
            {"date": "2024-01-09"},  # Tuesday
            {"date": "2024-01-10"},  # Wednesday
            {"date": "2024-01-11"},  # Thursday
            {"date": "2024-01-12"},  # Friday
        ]
        gaps = detect_gaps(records, frequency="daily")
        assert gaps == []

    def test_weekend_not_flagged(self):
        # Friday to Monday should not be a gap
        records = [
            {"date": "2024-01-12"},  # Friday
            {"date": "2024-01-15"},  # Monday
        ]
        gaps = detect_gaps(records, frequency="daily")
        assert gaps == []

    def test_gap_detected(self):
        # Missing Wednesday
        records = [
            {"date": "2024-01-08"},  # Monday
            {"date": "2024-01-09"},  # Tuesday
            {"date": "2024-01-11"},  # Thursday (Wed missing)
        ]
        gaps = detect_gaps(records, frequency="daily")
        assert len(gaps) == 1
        assert gaps[0]["gap_start"] == "2024-01-10"

    def test_single_record_no_gaps(self):
        records = [{"date": "2024-01-08"}]
        gaps = detect_gaps(records, frequency="daily")
        assert gaps == []

    def test_empty_records(self):
        gaps = detect_gaps([], frequency="daily")
        assert gaps == []

    def test_monthly_gap(self):
        records = [
            {"date": "2024-01-01"},
            {"date": "2024-02-01"},
            {"date": "2024-05-01"},  # Mar and Apr missing
        ]
        gaps = detect_gaps(records, frequency="monthly")
        assert len(gaps) == 1
        assert gaps[0]["missing_days"] == "2"

    def test_unsupported_frequency_raises(self):
        with pytest.raises(ValueError, match="Unsupported frequency"):
            detect_gaps([{"date": "2024-01-01"}], frequency="weekly")

    def test_out_of_order_dates_sorted(self):
        records = [
            {"date": "2024-01-10"},
            {"date": "2024-01-08"},
            {"date": "2024-01-09"},
        ]
        gaps = detect_gaps(records, frequency="daily")
        assert gaps == []


class TestDetectOutliers:
    """Tests for statistical outlier detection."""

    def test_no_outliers_in_smooth_data(self):
        records = [
            {"date": f"2024-01-{i:02d}", "close": 100.0 + i * 0.5} for i in range(1, 21)
        ]
        outliers = detect_outliers(records, value_key="close")
        assert outliers == []

    def test_detects_large_spike(self):
        records = [
            {"date": "2024-01-01", "close": 100.0},
            {"date": "2024-01-02", "close": 101.0},
            {"date": "2024-01-03", "close": 100.5},
            {"date": "2024-01-04", "close": 101.5},
            {"date": "2024-01-05", "close": 200.0},  # 100% spike
            {"date": "2024-01-06", "close": 100.0},
            {"date": "2024-01-07", "close": 101.0},
            {"date": "2024-01-08", "close": 100.5},
            {"date": "2024-01-09", "close": 101.0},
            {"date": "2024-01-10", "close": 100.5},
        ]
        outliers = detect_outliers(records, value_key="close", z_threshold=2.0)
        assert len(outliers) > 0
        # The spike or its aftermath should be flagged
        flagged_dates = [o["date"] for o in outliers]
        assert "2024-01-05" in flagged_dates or "2024-01-06" in flagged_dates

    def test_too_few_records(self):
        records = [
            {"date": "2024-01-01", "close": 100.0},
            {"date": "2024-01-02", "close": 200.0},
        ]
        assert detect_outliers(records) == []

    def test_custom_value_key(self):
        records = [
            {"date": f"2024-01-{i:02d}", "price": 50.0 + i * 0.1} for i in range(1, 21)
        ]
        outliers = detect_outliers(records, value_key="price")
        assert outliers == []


class TestValidateOhlcv:
    """Tests for OHLCV data integrity validation."""

    def test_valid_records(self):
        records = [
            {
                "date": "2024-01-02",
                "open": 100.0,
                "high": 105.0,
                "low": 99.0,
                "close": 104.0,
                "volume": 1000000,
            }
        ]
        errors = validate_ohlcv(records)
        assert errors == []

    def test_high_less_than_low(self):
        records = [
            {
                "date": "2024-01-02",
                "open": 100.0,
                "high": 95.0,
                "low": 99.0,
                "close": 96.0,
                "volume": 1000000,
            }
        ]
        errors = validate_ohlcv(records)
        assert any(e["field"] == "high/low" for e in errors)

    def test_missing_fields(self):
        records = [{"date": "2024-01-02", "open": 100.0}]
        errors = validate_ohlcv(records)
        assert any(e["field"] == "missing_keys" for e in errors)

    def test_negative_volume(self):
        records = [
            {
                "date": "2024-01-02",
                "open": 100.0,
                "high": 105.0,
                "low": 99.0,
                "close": 104.0,
                "volume": -100,
            }
        ]
        errors = validate_ohlcv(records)
        assert any(e["field"] == "volume" for e in errors)

    def test_zero_price(self):
        records = [
            {
                "date": "2024-01-02",
                "open": 0.0,
                "high": 105.0,
                "low": 0.0,
                "close": 104.0,
                "volume": 1000000,
            }
        ]
        errors = validate_ohlcv(records)
        assert any(e["issue"] == "Non-positive price" for e in errors)

    def test_open_outside_range(self):
        records = [
            {
                "date": "2024-01-02",
                "open": 110.0,
                "high": 105.0,
                "low": 99.0,
                "close": 104.0,
                "volume": 1000000,
            }
        ]
        errors = validate_ohlcv(records)
        assert any(e["field"] == "open" for e in errors)

    def test_empty_records(self):
        assert validate_ohlcv([]) == []

    def test_multiple_errors_in_one_record(self):
        records = [
            {
                "date": "2024-01-02",
                "open": 0.0,
                "high": 5.0,
                "low": 10.0,
                "close": 0.0,
                "volume": -1,
            }
        ]
        errors = validate_ohlcv(records)
        # Multiple issues: high < low, zero prices, negative volume
        assert len(errors) >= 2
