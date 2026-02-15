"""Tests for the portfolio data store."""

from __future__ import annotations

import pytest
from portfolioos.db.connection import init_memory_db
from portfolioos.db.portfolio_store import (
    add_transaction,
    get_holdings,
    get_portfolio_snapshots,
    get_transactions,
    save_portfolio_snapshot,
    upsert_holding,
)


@pytest.fixture
def db():
    conn = init_memory_db()
    yield conn
    conn.close()


class TestAddTransaction:
    """Tests for recording transactions."""

    def test_add_buy_transaction(self, db):
        tx_id = add_transaction(
            db,
            account_id="acc1",
            symbol="AAPL",
            tx_type="buy",
            date="2024-01-15",
            quantity=10,
            price=185.0,
            fees=4.95,
        )
        assert isinstance(tx_id, str)
        assert len(tx_id) == 16

    def test_invalid_type_raises(self, db):
        with pytest.raises(ValueError, match="tx_type must be one of"):
            add_transaction(
                db,
                account_id="acc1",
                symbol="AAPL",
                tx_type="invalid",
                date="2024-01-15",
                quantity=10,
                price=185.0,
            )

    def test_all_valid_types(self, db):
        for tx_type in ("buy", "sell", "dividend", "split", "transfer"):
            tx_id = add_transaction(
                db,
                account_id="acc1",
                symbol="VTI",
                tx_type=tx_type,
                date="2024-01-15",
                quantity=1,
                price=200.0,
            )
            assert len(tx_id) == 16


class TestUpsertHolding:
    """Tests for holding management."""

    def test_create_holding(self, db):
        holding_id = upsert_holding(
            db,
            account_id="acc1",
            symbol="VTI",
            asset_type="etf",
            shares=50.0,
            cost_basis=10000.0,
        )
        assert isinstance(holding_id, str)

    def test_update_holding(self, db):
        upsert_holding(
            db,
            account_id="acc1",
            symbol="VTI",
            asset_type="etf",
            shares=50.0,
            cost_basis=10000.0,
        )
        upsert_holding(
            db,
            account_id="acc1",
            symbol="VTI",
            asset_type="etf",
            shares=75.0,
            cost_basis=15000.0,
        )

        holdings = get_holdings(db, account_id="acc1")
        assert len(holdings) == 1
        assert holdings[0]["shares"] == 75.0


class TestGetHoldings:
    """Tests for querying holdings."""

    def test_filter_by_account(self, db):
        upsert_holding(db, "acc1", "AAPL", "stock", 10, 1850)
        upsert_holding(db, "acc2", "VTI", "etf", 50, 10000)

        holdings = get_holdings(db, account_id="acc1")
        assert len(holdings) == 1
        assert holdings[0]["symbol"] == "AAPL"

    def test_get_all_holdings(self, db):
        upsert_holding(db, "acc1", "AAPL", "stock", 10, 1850)
        upsert_holding(db, "acc2", "VTI", "etf", 50, 10000)

        holdings = get_holdings(db)
        assert len(holdings) == 2


class TestGetTransactions:
    """Tests for querying transactions."""

    def test_filter_by_symbol(self, db):
        add_transaction(db, "acc1", "AAPL", "buy", "2024-01-15", 10, 185)
        add_transaction(db, "acc1", "VTI", "buy", "2024-01-16", 50, 200)

        txs = get_transactions(db, symbol="AAPL")
        assert len(txs) == 1
        assert txs[0]["symbol"] == "AAPL"

    def test_filter_by_date_range(self, db):
        add_transaction(db, "acc1", "AAPL", "buy", "2024-01-15", 10, 185)
        add_transaction(db, "acc1", "AAPL", "buy", "2024-06-15", 5, 195)

        txs = get_transactions(
            db, symbol="AAPL", start_date="2024-03-01", end_date="2024-12-31"
        )
        assert len(txs) == 1


class TestPortfolioSnapshots:
    """Tests for portfolio snapshot storage."""

    def test_save_and_retrieve(self, db):
        save_portfolio_snapshot(db, "acc1", "2024-01-15", 100000, 90000)
        save_portfolio_snapshot(db, "acc1", "2024-01-16", 101000, 90000)

        snapshots = get_portfolio_snapshots(db, "acc1")
        assert len(snapshots) == 2
        assert snapshots[0]["unrealized_gain"] == 10000
        assert snapshots[1]["total_value"] == 101000

    def test_filter_by_date(self, db):
        save_portfolio_snapshot(db, "acc1", "2024-01-15", 100000, 90000)
        save_portfolio_snapshot(db, "acc1", "2024-06-15", 110000, 90000)

        snapshots = get_portfolio_snapshots(db, "acc1", start_date="2024-03-01")
        assert len(snapshots) == 1
        assert snapshots[0]["date"].strftime("%Y-%m-%d") == "2024-06-15"
