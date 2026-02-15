"""DuckDB connection management for PortfolioOS.

Handles database initialization, schema creation, and connection
lifecycle. Supports separate databases for market data, portfolio
data, and simulation results per the ARCHITECTURE.md layout::

    ~/.portfolioos/
      data/
        portfolio.duckdb
        market.duckdb
        simulations.duckdb

"""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb

from portfolioos.db.schema import ALL_TABLES

logger = logging.getLogger(__name__)

# Default data directory (can be overridden for testing)
_DEFAULT_DATA_DIR = Path.home() / ".portfolioos" / "data"


def get_connection(
    db_path: str | Path | None = None,
    read_only: bool = False,
) -> duckdb.DuckDBPyConnection:
    """Open a DuckDB connection.

    Args:
        db_path: Path to the .duckdb file. If None, uses in-memory database.
        read_only: Open in read-only mode.

    Returns:
        Active DuckDB connection.

    """
    if db_path is None:
        return duckdb.connect(":memory:")

    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(path), read_only=read_only)


def init_market_db(
    db_path: str | Path | None = None,
) -> duckdb.DuckDBPyConnection:
    """Initialize the market data database with schema.

    Creates tables: price_history, macro_indicators, dividends, splits.

    Args:
        db_path: Path to the market.duckdb file.
            Defaults to ~/.portfolioos/data/market.duckdb.

    Returns:
        Initialized DuckDB connection.

    """
    if db_path is None:
        db_path = _DEFAULT_DATA_DIR / "market.duckdb"

    conn = get_connection(db_path)
    for ddl in ALL_TABLES:
        conn.execute(ddl)
    logger.info("Market database initialized at %s", db_path)
    return conn


def init_portfolio_db(
    db_path: str | Path | None = None,
) -> duckdb.DuckDBPyConnection:
    """Initialize the portfolio database with schema.

    Creates tables: holdings, transactions, portfolio_snapshots.

    Args:
        db_path: Path to the portfolio.duckdb file.
            Defaults to ~/.portfolioos/data/portfolio.duckdb.

    Returns:
        Initialized DuckDB connection.

    """
    if db_path is None:
        db_path = _DEFAULT_DATA_DIR / "portfolio.duckdb"

    conn = get_connection(db_path)
    for ddl in ALL_TABLES:
        conn.execute(ddl)
    logger.info("Portfolio database initialized at %s", db_path)
    return conn


def init_memory_db() -> duckdb.DuckDBPyConnection:
    """Create an in-memory database with full schema.

    Useful for testing and ephemeral operations.

    Returns:
        In-memory DuckDB connection with all tables created.

    """
    conn = get_connection(None)
    for ddl in ALL_TABLES:
        conn.execute(ddl)
    return conn
