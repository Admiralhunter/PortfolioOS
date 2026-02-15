"""DuckDB schema definitions for PortfolioOS.

Contains DDL statements for all analytical tables:
- price_history: Daily OHLCV data per symbol
- holdings: Current portfolio holdings
- transactions: Buy/sell/dividend/split records
- portfolio_snapshots: Materialized daily totals per account
- macro_indicators: FRED economic data series
- simulation_results: Monte Carlo trial data

References:
    ARCHITECTURE.md — Database Schemas section.

"""

from __future__ import annotations

# ── Price History ──

CREATE_PRICE_HISTORY = """
CREATE TABLE IF NOT EXISTS price_history (
    symbol       VARCHAR NOT NULL,
    date         DATE NOT NULL,
    open         DOUBLE NOT NULL,
    high         DOUBLE NOT NULL,
    low          DOUBLE NOT NULL,
    close        DOUBLE NOT NULL,
    adj_close    DOUBLE NOT NULL,
    volume       BIGINT NOT NULL,
    source       VARCHAR DEFAULT 'yahoo',
    fetched_at   TIMESTAMP DEFAULT current_timestamp,
    PRIMARY KEY  (symbol, date)
);
"""

# ── Holdings ──

CREATE_HOLDINGS = """
CREATE TABLE IF NOT EXISTS holdings (
    id           VARCHAR PRIMARY KEY,
    account_id   VARCHAR NOT NULL,
    symbol       VARCHAR NOT NULL,
    asset_type   VARCHAR NOT NULL,
    shares       DOUBLE NOT NULL DEFAULT 0,
    cost_basis   DOUBLE NOT NULL DEFAULT 0,
    created_at   TIMESTAMP DEFAULT current_timestamp,
    updated_at   TIMESTAMP DEFAULT current_timestamp
);
"""

# ── Transactions ──

CREATE_TRANSACTIONS = """
CREATE TABLE IF NOT EXISTS transactions (
    id           VARCHAR PRIMARY KEY,
    account_id   VARCHAR NOT NULL,
    symbol       VARCHAR NOT NULL,
    type         VARCHAR NOT NULL,
    date         DATE NOT NULL,
    quantity     DOUBLE NOT NULL,
    price        DOUBLE NOT NULL,
    fees         DOUBLE DEFAULT 0,
    notes        VARCHAR DEFAULT '',
    created_at   TIMESTAMP DEFAULT current_timestamp
);
"""

# ── Portfolio Snapshots ──

CREATE_PORTFOLIO_SNAPSHOTS = """
CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    account_id        VARCHAR NOT NULL,
    date              DATE NOT NULL,
    total_value       DOUBLE NOT NULL,
    total_cost_basis  DOUBLE NOT NULL,
    unrealized_gain   DOUBLE NOT NULL,
    PRIMARY KEY       (account_id, date)
);
"""

# ── Macro Indicators (FRED) ──

CREATE_MACRO_INDICATORS = """
CREATE TABLE IF NOT EXISTS macro_indicators (
    series_id    VARCHAR NOT NULL,
    date         DATE NOT NULL,
    value        DOUBLE NOT NULL,
    source       VARCHAR DEFAULT 'fred',
    fetched_at   TIMESTAMP DEFAULT current_timestamp,
    PRIMARY KEY  (series_id, date)
);
"""

# ── Simulation Results ──

CREATE_SIMULATION_RESULTS = """
CREATE TABLE IF NOT EXISTS simulation_results (
    simulation_id  VARCHAR NOT NULL,
    trial_num      INTEGER NOT NULL,
    year           INTEGER NOT NULL,
    portfolio_value DOUBLE NOT NULL,
    withdrawal     DOUBLE NOT NULL,
    PRIMARY KEY    (simulation_id, trial_num, year)
);
"""

# ── Dividends ──

CREATE_DIVIDENDS = """
CREATE TABLE IF NOT EXISTS dividends (
    symbol       VARCHAR NOT NULL,
    date         DATE NOT NULL,
    amount       DOUBLE NOT NULL,
    source       VARCHAR DEFAULT 'yahoo',
    fetched_at   TIMESTAMP DEFAULT current_timestamp,
    PRIMARY KEY  (symbol, date)
);
"""

# ── Splits ──

CREATE_SPLITS = """
CREATE TABLE IF NOT EXISTS splits (
    symbol       VARCHAR NOT NULL,
    date         DATE NOT NULL,
    ratio        DOUBLE NOT NULL,
    source       VARCHAR DEFAULT 'yahoo',
    fetched_at   TIMESTAMP DEFAULT current_timestamp,
    PRIMARY KEY  (symbol, date)
);
"""

# All DDL statements in creation order
ALL_TABLES: list[str] = [
    CREATE_PRICE_HISTORY,
    CREATE_HOLDINGS,
    CREATE_TRANSACTIONS,
    CREATE_PORTFOLIO_SNAPSHOTS,
    CREATE_MACRO_INDICATORS,
    CREATE_SIMULATION_RESULTS,
    CREATE_DIVIDENDS,
    CREATE_SPLITS,
]
