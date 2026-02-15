"""Portfolio data store — DuckDB CRUD for holdings and transactions.

Handles portfolio-level data operations: managing holdings,
recording transactions, and computing snapshots.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import duckdb

logger = logging.getLogger(__name__)


def _generate_id(*parts: str) -> str:
    """Generate a deterministic ID from parts using SHA-256.

    Args:
        *parts: String components to hash.

    Returns:
        First 16 hex characters of the SHA-256 digest.

    """
    content = "|".join(parts)
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def add_transaction(  # noqa: PLR0913
    conn: duckdb.DuckDBPyConnection,
    account_id: str,
    symbol: str,
    tx_type: str,
    date: str,
    quantity: float,
    price: float,
    fees: float = 0.0,
    notes: str = "",
) -> str:
    """Record a new transaction.

    Args:
        conn: Active DuckDB connection.
        account_id: Account identifier.
        symbol: Ticker symbol.
        tx_type: Transaction type — "buy", "sell", "dividend",
            "split", or "transfer".
        date: Transaction date (YYYY-MM-DD).
        quantity: Number of shares/units.
        price: Price per share/unit.
        fees: Transaction fees.
        notes: Optional notes.

    Returns:
        The generated transaction ID.

    Raises:
        ValueError: If tx_type is not valid.

    """
    valid_types = {"buy", "sell", "dividend", "split", "transfer"}
    if tx_type not in valid_types:
        msg = f"tx_type must be one of {valid_types}, got '{tx_type}'"
        raise ValueError(msg)

    tx_id = _generate_id(account_id, symbol, tx_type, date, str(quantity), str(price))

    conn.execute(
        """
        INSERT INTO transactions
            (id, account_id, symbol, type, date, quantity, price, fees, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [tx_id, account_id, symbol, tx_type, date, quantity, price, fees, notes],
    )

    logger.info("Added %s transaction: %s %s @ %s", tx_type, quantity, symbol, price)
    return tx_id


def upsert_holding(
    conn: duckdb.DuckDBPyConnection,
    account_id: str,
    symbol: str,
    asset_type: str,
    shares: float,
    cost_basis: float,
) -> str:
    """Insert or update a holding record.

    Args:
        conn: Active DuckDB connection.
        account_id: Account identifier.
        symbol: Ticker symbol.
        asset_type: Asset type — "stock", "etf", "bond", "crypto",
            "real_asset", "cash".
        shares: Number of shares held.
        cost_basis: Total cost basis.

    Returns:
        The holding ID.

    """
    holding_id = _generate_id(account_id, symbol)
    now = datetime.now(tz=UTC).isoformat()

    conn.execute(
        """
        INSERT OR REPLACE INTO holdings
            (id, account_id, symbol, asset_type, shares, cost_basis,
             created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [holding_id, account_id, symbol, asset_type, shares, cost_basis, now, now],
    )

    return holding_id


def get_holdings(
    conn: duckdb.DuckDBPyConnection,
    account_id: str | None = None,
) -> list[dict[str, Any]]:
    """Get holdings, optionally filtered by account.

    Args:
        conn: Active DuckDB connection.
        account_id: Optional account filter.

    Returns:
        List of holding dicts.

    """
    if account_id:
        query = "SELECT * FROM holdings WHERE account_id = ? ORDER BY symbol"
        result = conn.execute(query, [account_id]).fetchall()
    else:
        query = "SELECT * FROM holdings ORDER BY account_id, symbol"
        result = conn.execute(query).fetchall()

    columns = [desc[0] for desc in conn.description]
    return [dict(zip(columns, row, strict=True)) for row in result]


def get_transactions(
    conn: duckdb.DuckDBPyConnection,
    account_id: str | None = None,
    symbol: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict[str, Any]]:
    """Query transactions with optional filters.

    Args:
        conn: Active DuckDB connection.
        account_id: Optional account filter.
        symbol: Optional symbol filter.
        start_date: Optional start date filter (YYYY-MM-DD).
        end_date: Optional end date filter (YYYY-MM-DD).

    Returns:
        List of transaction dicts ordered by date descending.

    """
    query = "SELECT * FROM transactions WHERE 1=1"
    params: list[Any] = []

    if account_id:
        query += " AND account_id = ?"
        params.append(account_id)
    if symbol:
        query += " AND symbol = ?"
        params.append(symbol)
    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)

    query += " ORDER BY date DESC"

    result = conn.execute(query, params).fetchall()
    columns = [desc[0] for desc in conn.description]
    return [dict(zip(columns, row, strict=True)) for row in result]


def save_portfolio_snapshot(
    conn: duckdb.DuckDBPyConnection,
    account_id: str,
    date: str,
    total_value: float,
    total_cost_basis: float,
) -> None:
    """Save a daily portfolio snapshot.

    Args:
        conn: Active DuckDB connection.
        account_id: Account identifier.
        date: Snapshot date (YYYY-MM-DD).
        total_value: Total portfolio value.
        total_cost_basis: Total cost basis.

    """
    unrealized_gain = total_value - total_cost_basis
    conn.execute(
        """
        INSERT OR REPLACE INTO portfolio_snapshots
            (account_id, date, total_value, total_cost_basis, unrealized_gain)
        VALUES (?, ?, ?, ?, ?)
        """,
        [account_id, date, total_value, total_cost_basis, unrealized_gain],
    )


def get_portfolio_snapshots(
    conn: duckdb.DuckDBPyConnection,
    account_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict[str, Any]]:
    """Query portfolio snapshots for an account.

    Args:
        conn: Active DuckDB connection.
        account_id: Account identifier.
        start_date: Optional start date filter.
        end_date: Optional end date filter.

    Returns:
        List of snapshot dicts ordered by date ascending.

    """
    query = "SELECT * FROM portfolio_snapshots WHERE account_id = ?"
    params: list[Any] = [account_id]

    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)

    query += " ORDER BY date ASC"

    result = conn.execute(query, params).fetchall()
    columns = [desc[0] for desc in conn.description]
    return [dict(zip(columns, row, strict=True)) for row in result]
