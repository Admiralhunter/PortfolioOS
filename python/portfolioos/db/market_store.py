"""Market data store — DuckDB CRUD for price history and macro indicators.

Handles upsert (INSERT OR REPLACE) semantics so that re-fetching
data for an existing date range safely overwrites stale records.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import duckdb

logger = logging.getLogger(__name__)


def upsert_price_history(
    conn: duckdb.DuckDBPyConnection,
    records: list[dict[str, Any]],
    source: str = "yahoo",
) -> int:
    """Insert or update daily price history records.

    Uses INSERT OR REPLACE on the (symbol, date) primary key.

    Args:
        conn: Active DuckDB connection.
        records: List of dicts with keys: date, open, high, low,
            close, adj_close, volume. Must also include "symbol"
            or it will be skipped.
        source: Data source identifier (default: "yahoo").

    Returns:
        Number of records upserted.

    """
    if not records:
        return 0

    count = 0
    for rec in records:
        symbol = rec.get("symbol")
        if not symbol:
            continue
        conn.execute(
            """
            INSERT OR REPLACE INTO price_history
                (symbol, date, open, high, low, close, adj_close, volume, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                symbol,
                rec["date"],
                rec["open"],
                rec["high"],
                rec["low"],
                rec["close"],
                rec.get("adj_close", rec["close"]),
                rec["volume"],
                source,
            ],
        )
        count += 1

    logger.info("Upserted %d price history records", count)
    return count


def upsert_macro_indicators(
    conn: duckdb.DuckDBPyConnection,
    records: list[dict[str, Any]],
    source: str = "fred",
) -> int:
    """Insert or update macro indicator records.

    Uses INSERT OR REPLACE on the (series_id, date) primary key.

    Args:
        conn: Active DuckDB connection.
        records: List of dicts with keys: series_id, date, value.
        source: Data source identifier (default: "fred").

    Returns:
        Number of records upserted.

    """
    if not records:
        return 0

    count = 0
    for rec in records:
        conn.execute(
            """
            INSERT OR REPLACE INTO macro_indicators
                (series_id, date, value, source)
            VALUES (?, ?, ?, ?)
            """,
            [rec["series_id"], rec["date"], rec["value"], source],
        )
        count += 1

    logger.info("Upserted %d macro indicator records", count)
    return count


def upsert_dividends(
    conn: duckdb.DuckDBPyConnection,
    symbol: str,
    records: list[dict[str, Any]],
    source: str = "yahoo",
) -> int:
    """Insert or update dividend records.

    Args:
        conn: Active DuckDB connection.
        symbol: Ticker symbol.
        records: List of dicts with keys: date, dividend.
        source: Data source identifier.

    Returns:
        Number of records upserted.

    """
    if not records:
        return 0

    count = 0
    for rec in records:
        conn.execute(
            """
            INSERT OR REPLACE INTO dividends
                (symbol, date, amount, source)
            VALUES (?, ?, ?, ?)
            """,
            [symbol, rec["date"], rec["dividend"], source],
        )
        count += 1

    logger.info("Upserted %d dividend records for %s", count, symbol)
    return count


def upsert_splits(
    conn: duckdb.DuckDBPyConnection,
    symbol: str,
    records: list[dict[str, Any]],
    source: str = "yahoo",
) -> int:
    """Insert or update stock split records.

    Args:
        conn: Active DuckDB connection.
        symbol: Ticker symbol.
        records: List of dicts with keys: date, ratio.
        source: Data source identifier.

    Returns:
        Number of records upserted.

    """
    if not records:
        return 0

    count = 0
    for rec in records:
        conn.execute(
            """
            INSERT OR REPLACE INTO splits
                (symbol, date, ratio, source)
            VALUES (?, ?, ?, ?)
            """,
            [symbol, rec["date"], rec["ratio"], source],
        )
        count += 1

    logger.info("Upserted %d split records for %s", count, symbol)
    return count


def query_price_history(
    conn: duckdb.DuckDBPyConnection,
    symbol: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict[str, Any]]:
    """Query price history for a symbol.

    Args:
        conn: Active DuckDB connection.
        symbol: Ticker symbol.
        start_date: Optional start date filter (YYYY-MM-DD).
        end_date: Optional end date filter (YYYY-MM-DD).

    Returns:
        List of price record dicts ordered by date ascending.

    """
    query = "SELECT * FROM price_history WHERE symbol = ?"
    params: list[Any] = [symbol]

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


def query_macro_indicators(
    conn: duckdb.DuckDBPyConnection,
    series_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict[str, Any]]:
    """Query macro indicator data for a series.

    Args:
        conn: Active DuckDB connection.
        series_id: FRED series ID.
        start_date: Optional start date filter (YYYY-MM-DD).
        end_date: Optional end date filter (YYYY-MM-DD).

    Returns:
        List of indicator record dicts ordered by date ascending.

    """
    query = "SELECT * FROM macro_indicators WHERE series_id = ?"
    params: list[Any] = [series_id]

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


def get_latest_date(
    conn: duckdb.DuckDBPyConnection,
    table: str,
    symbol_or_series: str,
    id_column: str = "symbol",
) -> str | None:
    """Get the most recent date for a symbol/series in a table.

    Useful for incremental fetching — only fetch data after
    the last known date.

    Args:
        conn: Active DuckDB connection.
        table: Table name ("price_history" or "macro_indicators").
        symbol_or_series: The symbol or series_id value.
        id_column: Column name for the identifier (default: "symbol").

    Returns:
        Most recent date as YYYY-MM-DD string, or None if no data.

    """
    allowed_tables = {"price_history", "macro_indicators", "dividends", "splits"}
    if table not in allowed_tables:
        msg = f"Table must be one of {allowed_tables}, got '{table}'"
        raise ValueError(msg)

    allowed_columns = {"symbol", "series_id"}
    if id_column not in allowed_columns:
        msg = f"id_column must be one of {allowed_columns}, got '{id_column}'"
        raise ValueError(msg)

    result = conn.execute(
        f"SELECT MAX(date) FROM {table} WHERE {id_column} = ?",  # noqa: S608
        [symbol_or_series],
    ).fetchone()

    if result and result[0]:
        return str(result[0])
    return None
