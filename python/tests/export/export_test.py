"""Tests for CSV and JSON export modules."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from portfolioos.export.csv_export import (
    export_holdings_csv,
    export_simulation_csv,
    export_transactions_csv,
)
from portfolioos.export.json_export import export_portfolio_json
from portfolioos.ingest.csv_import import parse_csv


class TestExportHoldingsCSV:
    """Test holdings CSV export."""

    def test_basic_export(self):
        holdings = [
            {
                "account_id": "acc1",
                "symbol": "AAPL",
                "asset_type": "stock",
                "shares": 100,
                "cost_basis": 15000.0,
            },
        ]
        csv_str = export_holdings_csv(holdings)
        assert "AAPL" in csv_str
        assert "100" in csv_str
        assert "# Holdings Export" in csv_str

    def test_export_to_file(self, tmp_path):
        holdings = [
            {
                "account_id": "acc1",
                "symbol": "AAPL",
                "asset_type": "stock",
                "shares": 100,
                "cost_basis": 15000.0,
            },
        ]
        out_path = str(tmp_path / "holdings.csv")
        result = export_holdings_csv(holdings, output_path=out_path)
        assert result == out_path
        content = Path(out_path).read_text()
        assert "AAPL" in content

    def test_empty_holdings(self):
        csv_str = export_holdings_csv([])
        assert "# Holdings Export" in csv_str
        # Only metadata + header, no data rows
        lines = [
            line for line in csv_str.strip().split("\n") if not line.startswith("#")
        ]
        assert len(lines) == 1  # Just the header

    def test_multiple_holdings(self):
        holdings = [
            {
                "account_id": "acc1",
                "symbol": "AAPL",
                "asset_type": "stock",
                "shares": 100,
                "cost_basis": 15000.0,
            },
            {
                "account_id": "acc1",
                "symbol": "GOOGL",
                "asset_type": "stock",
                "shares": 50,
                "cost_basis": 7000.0,
            },
        ]
        csv_str = export_holdings_csv(holdings)
        assert "AAPL" in csv_str
        assert "GOOGL" in csv_str


class TestExportTransactionsCSV:
    """Test transactions CSV export."""

    def test_basic_export(self):
        transactions = [
            {
                "account_id": "acc1",
                "symbol": "AAPL",
                "type": "buy",
                "date": "2024-01-15",
                "quantity": 100,
                "price": 150.0,
                "fees": 9.99,
                "notes": "",
            },
        ]
        csv_str = export_transactions_csv(transactions)
        assert "AAPL" in csv_str
        assert "buy" in csv_str
        assert "# Transactions Export" in csv_str

    def test_round_trip(self):
        """Export then reimport and verify data matches."""
        original = [
            {
                "account_id": "acc1",
                "symbol": "AAPL",
                "type": "buy",
                "date": "2024-01-15",
                "quantity": 100,
                "price": 150.0,
                "fees": 9.99,
                "notes": "test trade",
            },
        ]
        csv_str = export_transactions_csv(original)
        # Remove metadata comment lines for reimport
        data_lines = [line for line in csv_str.split("\n") if not line.startswith("#")]
        clean_csv = "\n".join(data_lines)
        reimported = parse_csv(csv_content=clean_csv, account_id="acc1")
        assert len(reimported) == 1
        assert reimported[0]["symbol"] == "AAPL"
        assert reimported[0]["type"] == "buy"
        assert reimported[0]["quantity"] == pytest.approx(100.0)


class TestExportSimulationCSV:
    """Test simulation results CSV export."""

    def test_basic_export(self):
        result = {
            "success_rate": 0.85,
            "percentiles": {
                5: np.array([1000000, 900000, 800000]),
                50: np.array([1000000, 1100000, 1200000]),
                95: np.array([1000000, 1300000, 1600000]),
            },
        }
        csv_str = export_simulation_csv(result)
        assert "# Simulation Results Export" in csv_str
        assert "Success Rate: 0.85" in csv_str
        assert "p5" in csv_str
        assert "p50" in csv_str
        assert "p95" in csv_str

    def test_empty_percentiles(self):
        result = {"percentiles": {}}
        csv_str = export_simulation_csv(result)
        assert csv_str == ""


class TestExportPortfolioJSON:
    """Test portfolio JSON export."""

    def test_full_export(self):
        holdings = [{"symbol": "AAPL", "shares": 100}]
        transactions = [{"symbol": "AAPL", "type": "buy", "date": "2024-01-15"}]
        snapshots = [{"date": "2024-01-15", "total_value": 15000}]
        json_str = export_portfolio_json(holdings, transactions, snapshots)
        data = json.loads(json_str)
        assert data["metadata"]["source"] == "PortfolioOS"
        assert data["metadata"]["holdings_count"] == 1
        assert data["metadata"]["transactions_count"] == 1
        assert data["metadata"]["snapshots_count"] == 1
        assert len(data["holdings"]) == 1
        assert len(data["transactions"]) == 1

    def test_holdings_only(self):
        json_str = export_portfolio_json(holdings=[{"symbol": "VTI"}])
        data = json.loads(json_str)
        assert "holdings" in data
        assert "transactions" not in data

    def test_export_to_file(self, tmp_path):
        out_path = str(tmp_path / "portfolio.json")
        result = export_portfolio_json(
            holdings=[{"symbol": "AAPL"}], output_path=out_path
        )
        assert result == out_path
        content = json.loads(Path(out_path).read_text())
        assert content["holdings"][0]["symbol"] == "AAPL"

    def test_numpy_serialization(self):
        holdings = [{"symbol": "AAPL", "value": np.float64(150.5)}]
        json_str = export_portfolio_json(holdings=holdings)
        data = json.loads(json_str)
        assert data["holdings"][0]["value"] == pytest.approx(150.5)
