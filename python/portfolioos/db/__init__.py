"""PortfolioOS database layer.

Provides DuckDB-based storage for market data, portfolio holdings,
and simulation results. SQLite handles app-state (preferences,
account metadata) — see ARCHITECTURE.md for the dual-database rationale.
"""
