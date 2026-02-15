"""Tests for the CSV import pipeline."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from portfolioos.ingest.csv_import import (
    _map_columns,
    _normalize_action,
    _parse_float,
    parse_csv,
)


class TestParseFloat:
    """Tests for currency-aware float parsing."""

    def test_plain_number(self):
        assert _parse_float("123.45") == 123.45

    def test_currency_symbol(self):
        assert _parse_float("$1,234.56") == 1234.56

    def test_parentheses_negative(self):
        assert _parse_float("($500.00)") == -500.0

    def test_empty_string(self):
        assert _parse_float("") == 0.0

    def test_whitespace(self):
        assert _parse_float("  ") == 0.0

    def test_invalid_returns_default(self):
        assert _parse_float("not-a-number", default=-1.0) == -1.0


class TestNormalizeAction:
    """Tests for transaction type normalization."""

    def test_buy_aliases(self):
        assert _normalize_action("Buy") == "buy"
        assert _normalize_action("BOUGHT") == "buy"
        assert _normalize_action("purchase") == "buy"

    def test_sell_aliases(self):
        assert _normalize_action("Sell") == "sell"
        assert _normalize_action("SOLD") == "sell"

    def test_dividend_aliases(self):
        assert _normalize_action("Dividend") == "dividend"
        assert _normalize_action("DIV") == "dividend"

    def test_unknown_action_passthrough(self):
        assert _normalize_action("custom_action") == "custom_action"


class TestMapColumns:
    """Tests for column header mapping."""

    def test_standard_headers(self):
        headers = ["Date", "Symbol", "Type", "Quantity", "Price", "Fees"]
        mapping = _map_columns(headers)
        assert mapping["date"] == 0
        assert mapping["symbol"] == 1
        assert mapping["type"] == 2

    def test_alternative_headers(self):
        headers = ["Trade Date", "Ticker", "Action", "Qty", "Unit Price", "Commission"]
        mapping = _map_columns(headers)
        assert "date" in mapping
        assert "symbol" in mapping
        assert "type" in mapping

    def test_missing_required_raises(self):
        headers = ["Price", "Quantity"]
        with pytest.raises(ValueError, match="Required columns not found"):
            _map_columns(headers)


class TestParseCsv:
    """Tests for CSV parsing."""

    def test_parse_basic_csv(self):
        csv_content = (
            "Date,Symbol,Type,Quantity,Price,Fees\n"
            "2024-01-15,AAPL,Buy,10,185.50,4.95\n"
            "2024-01-16,VTI,Buy,50,200.00,0.00\n"
        )
        result = parse_csv(csv_content=csv_content, account_id="test")
        assert len(result) == 2
        assert result[0]["symbol"] == "AAPL"
        assert result[0]["type"] == "buy"
        assert result[0]["quantity"] == 10.0
        assert result[0]["price"] == 185.50
        assert result[0]["account_id"] == "test"

    def test_parse_from_file(self):
        csv_content = "Date,Symbol,Type,Quantity,Price\n2024-01-15,GOOG,Buy,5,140.00\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            f.flush()
            result = parse_csv(file_path=f.name)

        assert len(result) == 1
        assert result[0]["symbol"] == "GOOG"
        Path(f.name).unlink()

    def test_skips_empty_rows(self):
        csv_content = (
            "Date,Symbol,Type,Quantity,Price\n"
            "2024-01-15,AAPL,Buy,10,185.50\n"
            "\n"
            "2024-01-16,VTI,Buy,50,200.00\n"
        )
        result = parse_csv(csv_content=csv_content)
        assert len(result) == 2

    def test_skips_rows_without_symbol(self):
        csv_content = (
            "Date,Symbol,Type,Quantity,Price\n"
            "2024-01-15,,Buy,10,185.50\n"
            "2024-01-16,VTI,Buy,50,200.00\n"
        )
        result = parse_csv(csv_content=csv_content)
        assert len(result) == 1

    def test_currency_values_parsed(self):
        csv_content = (
            "Date,Symbol,Type,Quantity,Price,Fees\n"
            "2024-01-15,AAPL,Buy,10,$185.50,$4.95\n"
        )
        result = parse_csv(csv_content=csv_content)
        assert result[0]["price"] == 185.50
        assert result[0]["fees"] == 4.95

    def test_negative_quantities_abs(self):
        csv_content = (
            "Date,Symbol,Type,Quantity,Price\n2024-01-15,AAPL,Sell,-10,185.50\n"
        )
        result = parse_csv(csv_content=csv_content)
        assert result[0]["quantity"] == 10.0

    def test_no_input_raises(self):
        with pytest.raises(ValueError, match="Provide either"):
            parse_csv()

    def test_default_account_id(self):
        csv_content = "Date,Symbol,Type,Quantity,Price\n2024-01-15,AAPL,Buy,10,185.50\n"
        result = parse_csv(csv_content=csv_content)
        assert result[0]["account_id"] == "default"

    def test_fidelity_format(self):
        csv_content = (
            "Run Date,Action,Symbol,Quantity,Price,Amount\n"
            "01/15/2024,Bought,AAPL,10,185.50,1855.00\n"
        )
        result = parse_csv(csv_content=csv_content)
        assert len(result) == 1
        assert result[0]["type"] == "buy"
        assert result[0]["symbol"] == "AAPL"
