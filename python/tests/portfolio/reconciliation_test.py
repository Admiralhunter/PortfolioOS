"""Tests for portfolio reconciliation engine."""

from __future__ import annotations

import pytest

from portfolioos.portfolio.reconciliation import (
    detect_discrepancies,
    reconcile_holdings,
)


class TestReconcileHoldings:
    """Test holdings computation from transactions."""

    def test_single_buy(self):
        txns = [
            {
                "account_id": "acc1",
                "symbol": "AAPL",
                "type": "buy",
                "date": "2024-01-15",
                "quantity": 100,
                "price": 150.0,
                "fees": 0,
            }
        ]
        holdings = reconcile_holdings(txns)
        assert len(holdings) == 1
        assert holdings[0]["symbol"] == "AAPL"
        assert holdings[0]["shares"] == pytest.approx(100)
        assert holdings[0]["cost_basis"] == pytest.approx(15000.0)

    def test_buy_then_sell(self):
        txns = [
            {
                "account_id": "acc1",
                "symbol": "AAPL",
                "type": "buy",
                "date": "2024-01-15",
                "quantity": 100,
                "price": 150.0,
                "fees": 0,
            },
            {
                "account_id": "acc1",
                "symbol": "AAPL",
                "type": "sell",
                "date": "2024-06-15",
                "quantity": 50,
                "price": 180.0,
                "fees": 0,
            },
        ]
        holdings = reconcile_holdings(txns)
        assert len(holdings) == 1
        assert holdings[0]["shares"] == pytest.approx(50)
        assert holdings[0]["realized_gain"] == pytest.approx(1500.0)

    def test_sell_all_removes_holding(self):
        txns = [
            {
                "account_id": "acc1",
                "symbol": "AAPL",
                "type": "buy",
                "date": "2024-01-15",
                "quantity": 100,
                "price": 150.0,
                "fees": 0,
            },
            {
                "account_id": "acc1",
                "symbol": "AAPL",
                "type": "sell",
                "date": "2024-06-15",
                "quantity": 100,
                "price": 180.0,
                "fees": 0,
            },
        ]
        holdings = reconcile_holdings(txns)
        assert len(holdings) == 0

    def test_multiple_symbols(self):
        txns = [
            {
                "account_id": "acc1",
                "symbol": "AAPL",
                "type": "buy",
                "date": "2024-01-15",
                "quantity": 50,
                "price": 150.0,
                "fees": 0,
            },
            {
                "account_id": "acc1",
                "symbol": "GOOGL",
                "type": "buy",
                "date": "2024-01-15",
                "quantity": 30,
                "price": 140.0,
                "fees": 0,
            },
        ]
        holdings = reconcile_holdings(txns)
        assert len(holdings) == 2
        symbols = {h["symbol"] for h in holdings}
        assert symbols == {"AAPL", "GOOGL"}

    def test_multiple_accounts(self):
        txns = [
            {
                "account_id": "ira",
                "symbol": "VTI",
                "type": "buy",
                "date": "2024-01-15",
                "quantity": 100,
                "price": 200.0,
                "fees": 0,
            },
            {
                "account_id": "taxable",
                "symbol": "VTI",
                "type": "buy",
                "date": "2024-01-15",
                "quantity": 50,
                "price": 200.0,
                "fees": 0,
            },
        ]
        holdings = reconcile_holdings(txns)
        assert len(holdings) == 2
        ira_holding = next(h for h in holdings if h["account_id"] == "ira")
        tax_holding = next(h for h in holdings if h["account_id"] == "taxable")
        assert ira_holding["shares"] == pytest.approx(100)
        assert tax_holding["shares"] == pytest.approx(50)

    def test_chronological_ordering(self):
        # Transactions out of order should be sorted before processing
        txns = [
            {
                "account_id": "acc1",
                "symbol": "AAPL",
                "type": "sell",
                "date": "2024-06-15",
                "quantity": 50,
                "price": 180.0,
                "fees": 0,
            },
            {
                "account_id": "acc1",
                "symbol": "AAPL",
                "type": "buy",
                "date": "2024-01-15",
                "quantity": 100,
                "price": 150.0,
                "fees": 0,
            },
        ]
        holdings = reconcile_holdings(txns)
        assert len(holdings) == 1
        assert holdings[0]["shares"] == pytest.approx(50)

    def test_stock_split(self):
        txns = [
            {
                "account_id": "acc1",
                "symbol": "AAPL",
                "type": "buy",
                "date": "2024-01-15",
                "quantity": 100,
                "price": 300.0,
                "fees": 0,
            },
            {
                "account_id": "acc1",
                "symbol": "AAPL",
                "type": "split",
                "date": "2024-06-15",
                "quantity": 2,
                "price": 0,
                "fees": 0,
            },
        ]
        holdings = reconcile_holdings(txns)
        assert len(holdings) == 1
        # After 2:1 split: 200 shares at $150 each
        assert holdings[0]["shares"] == pytest.approx(200)
        # Cost basis unchanged
        assert holdings[0]["cost_basis"] == pytest.approx(30000.0)

    def test_dividend_reinvestment(self):
        txns = [
            {
                "account_id": "acc1",
                "symbol": "VTI",
                "type": "buy",
                "date": "2024-01-15",
                "quantity": 100,
                "price": 200.0,
                "fees": 0,
            },
            {
                "account_id": "acc1",
                "symbol": "VTI",
                "type": "dividend",
                "date": "2024-03-15",
                "quantity": 2,
                "price": 205.0,
                "fees": 0,
            },
        ]
        holdings = reconcile_holdings(txns)
        assert len(holdings) == 1
        assert holdings[0]["shares"] == pytest.approx(102)

    def test_empty_transactions(self):
        holdings = reconcile_holdings([])
        assert len(holdings) == 0

    def test_transfer_in(self):
        txns = [
            {
                "account_id": "acc1",
                "symbol": "MSFT",
                "type": "transfer",
                "date": "2024-01-15",
                "quantity": 50,
                "price": 400.0,
                "fees": 0,
            },
        ]
        holdings = reconcile_holdings(txns)
        assert len(holdings) == 1
        assert holdings[0]["shares"] == pytest.approx(50)
        assert holdings[0]["cost_basis"] == pytest.approx(20000.0)


class TestDetectDiscrepancies:
    """Test discrepancy detection between computed and stored holdings."""

    def test_no_discrepancies(self):
        computed = [
            {"account_id": "acc1", "symbol": "AAPL", "shares": 100, "cost_basis": 15000.0}
        ]
        stored = [
            {"account_id": "acc1", "symbol": "AAPL", "shares": 100, "cost_basis": 15000.0}
        ]
        result = detect_discrepancies(computed, stored)
        assert len(result) == 0

    def test_shares_mismatch(self):
        computed = [
            {"account_id": "acc1", "symbol": "AAPL", "shares": 100, "cost_basis": 15000.0}
        ]
        stored = [
            {"account_id": "acc1", "symbol": "AAPL", "shares": 90, "cost_basis": 15000.0}
        ]
        result = detect_discrepancies(computed, stored)
        assert len(result) == 1
        assert result[0]["field"] == "shares"
        assert result[0]["computed_value"] == 100
        assert result[0]["stored_value"] == 90

    def test_cost_basis_mismatch(self):
        computed = [
            {"account_id": "acc1", "symbol": "AAPL", "shares": 100, "cost_basis": 15000.0}
        ]
        stored = [
            {"account_id": "acc1", "symbol": "AAPL", "shares": 100, "cost_basis": 14000.0}
        ]
        result = detect_discrepancies(computed, stored)
        assert len(result) == 1
        assert result[0]["field"] == "cost_basis"

    def test_missing_in_stored(self):
        computed = [
            {"account_id": "acc1", "symbol": "AAPL", "shares": 100, "cost_basis": 15000.0}
        ]
        stored: list[dict] = []
        result = detect_discrepancies(computed, stored)
        assert len(result) == 1
        assert result[0]["field"] == "existence"
        assert result[0]["stored_value"] == "missing"

    def test_extra_in_stored(self):
        computed: list[dict] = []
        stored = [
            {"account_id": "acc1", "symbol": "AAPL", "shares": 100, "cost_basis": 15000.0}
        ]
        result = detect_discrepancies(computed, stored)
        assert len(result) == 1
        assert result[0]["field"] == "existence"
        assert result[0]["computed_value"] == "missing"

    def test_multiple_discrepancies(self):
        computed = [
            {"account_id": "acc1", "symbol": "AAPL", "shares": 100, "cost_basis": 15000.0},
            {"account_id": "acc1", "symbol": "GOOGL", "shares": 50, "cost_basis": 7000.0},
        ]
        stored = [
            {"account_id": "acc1", "symbol": "AAPL", "shares": 90, "cost_basis": 14000.0},
            {"account_id": "acc1", "symbol": "GOOGL", "shares": 50, "cost_basis": 7000.0},
        ]
        result = detect_discrepancies(computed, stored)
        # AAPL has both shares and cost_basis mismatch
        assert len(result) == 2
