"""Tests for DuckDB connection management."""

from __future__ import annotations

import tempfile
from pathlib import Path

from portfolioos.db.connection import get_connection, init_memory_db


class TestGetConnection:
    """Tests for database connection factory."""

    def test_in_memory_connection(self):
        conn = get_connection(None)
        assert conn is not None
        conn.execute("SELECT 1").fetchone()
        conn.close()

    def test_file_connection(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"
            conn = get_connection(db_path)
            conn.execute("CREATE TABLE test_tbl (id INT)")
            conn.execute("INSERT INTO test_tbl VALUES (1)")
            result = conn.execute("SELECT * FROM test_tbl").fetchone()
            assert result == (1,)
            conn.close()

    def test_creates_parent_directories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "nested" / "deep" / "test.duckdb"
            conn = get_connection(db_path)
            conn.execute("SELECT 1").fetchone()
            conn.close()
            assert db_path.parent.exists()


class TestInitMemoryDb:
    """Tests for in-memory database initialization."""

    def test_creates_all_tables(self):
        conn = init_memory_db()
        tables = conn.execute("SHOW TABLES").fetchall()
        table_names = {t[0] for t in tables}

        expected = {
            "price_history",
            "holdings",
            "transactions",
            "portfolio_snapshots",
            "macro_indicators",
            "simulation_results",
            "dividends",
            "splits",
        }
        assert expected.issubset(table_names)
        conn.close()

    def test_tables_are_empty(self):
        conn = init_memory_db()
        for table in ["price_history", "holdings", "transactions"]:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()  # noqa: S608
            assert count[0] == 0
        conn.close()

    def test_idempotent_init(self):
        # Calling init twice should not raise (IF NOT EXISTS)
        conn = init_memory_db()
        # Re-run all DDL
        from portfolioos.db.schema import ALL_TABLES

        for ddl in ALL_TABLES:
            conn.execute(ddl)
        conn.close()
