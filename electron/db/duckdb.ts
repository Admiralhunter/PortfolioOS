/**
 * DuckDB access layer for read-only queries from the Electron main process.
 *
 * Write operations go through the Python sidecar to prevent two-writer
 * data corruption. This layer provides direct reads for low-latency
 * queries that don't need computation.
 *
 * Uses the official Node.js duckdb bindings.
 */

import * as duckdb from "duckdb";
import * as path from "node:path";
import type { Holding, PriceRecord, Snapshot, Transaction } from "../types";

interface DateRange {
  start?: string;
  end?: string;
}

interface TransactionFilters {
  account_id?: string;
  symbol?: string;
  start_date?: string;
  end_date?: string;
}

export class DuckDBManager {
  private marketDB: duckdb.Database | null = null;
  private portfolioDB: duckdb.Database | null = null;
  private dataDir: string;

  constructor(dataDir: string) {
    this.dataDir = dataDir;
  }

  /** Initialize the market data database. */
  initMarketDB(dbPath?: string): void {
    const p = dbPath ?? path.join(this.dataDir, "market.duckdb");
    this.marketDB = new duckdb.Database(p);
  }

  /** Initialize the portfolio database. */
  initPortfolioDB(dbPath?: string): void {
    const p = dbPath ?? path.join(this.dataDir, "portfolio.duckdb");
    this.portfolioDB = new duckdb.Database(p);
  }

  /** Close all database connections. */
  close(): void {
    if (this.marketDB) {
      this.marketDB.close();
      this.marketDB = null;
    }
    if (this.portfolioDB) {
      this.portfolioDB.close();
      this.portfolioDB = null;
    }
  }

  /** Execute a read query on a database. */
  private query(
    db: duckdb.Database,
    sql: string,
    params: unknown[] = []
  ): Promise<Record<string, unknown>[]> {
    return new Promise((resolve, reject) => {
      db.all(sql, ...params, (err: Error | null, rows: Record<string, unknown>[]) => {
        if (err) reject(err);
        else resolve(rows ?? []);
      });
    });
  }

  /** Get cached price history for a symbol. */
  async getPriceHistory(
    symbol: string,
    dateRange?: DateRange
  ): Promise<PriceRecord[]> {
    if (!this.marketDB) throw new Error("Market DB not initialized");

    let sql =
      "SELECT * FROM price_history WHERE symbol = ?";
    const params: unknown[] = [symbol];

    if (dateRange?.start) {
      sql += " AND date >= ?";
      params.push(dateRange.start);
    }
    if (dateRange?.end) {
      sql += " AND date <= ?";
      params.push(dateRange.end);
    }
    sql += " ORDER BY date ASC";

    const rows = await this.query(this.marketDB, sql, params);
    return rows as unknown as PriceRecord[];
  }

  /** Get current holdings, optionally filtered by account. */
  async getHoldings(accountId?: string): Promise<Holding[]> {
    if (!this.portfolioDB) throw new Error("Portfolio DB not initialized");

    let sql = "SELECT * FROM holdings";
    const params: unknown[] = [];

    if (accountId) {
      sql += " WHERE account_id = ?";
      params.push(accountId);
    }
    sql += " ORDER BY symbol ASC";

    const rows = await this.query(this.portfolioDB, sql, params);
    return rows as unknown as Holding[];
  }

  /** Get transactions with optional filters. */
  async getTransactions(filters?: TransactionFilters): Promise<Transaction[]> {
    if (!this.portfolioDB) throw new Error("Portfolio DB not initialized");

    let sql = "SELECT * FROM transactions WHERE 1=1";
    const params: unknown[] = [];

    if (filters?.account_id) {
      sql += " AND account_id = ?";
      params.push(filters.account_id);
    }
    if (filters?.symbol) {
      sql += " AND symbol = ?";
      params.push(filters.symbol);
    }
    if (filters?.start_date) {
      sql += " AND date >= ?";
      params.push(filters.start_date);
    }
    if (filters?.end_date) {
      sql += " AND date <= ?";
      params.push(filters.end_date);
    }
    sql += " ORDER BY date DESC";

    const rows = await this.query(this.portfolioDB, sql, params);
    return rows as unknown as Transaction[];
  }

  /** Get portfolio snapshots for an account. */
  async getSnapshots(
    accountId: string,
    dateRange?: DateRange
  ): Promise<Snapshot[]> {
    if (!this.portfolioDB) throw new Error("Portfolio DB not initialized");

    let sql =
      "SELECT * FROM portfolio_snapshots WHERE account_id = ?";
    const params: unknown[] = [accountId];

    if (dateRange?.start) {
      sql += " AND date >= ?";
      params.push(dateRange.start);
    }
    if (dateRange?.end) {
      sql += " AND date <= ?";
      params.push(dateRange.end);
    }
    sql += " ORDER BY date ASC";

    const rows = await this.query(this.portfolioDB, sql, params);
    return rows as unknown as Snapshot[];
  }

  /** Get macro indicators for a FRED series. */
  async getMacroIndicators(
    seriesId: string,
    dateRange?: DateRange
  ): Promise<Record<string, unknown>[]> {
    if (!this.marketDB) throw new Error("Market DB not initialized");

    let sql =
      "SELECT * FROM macro_indicators WHERE series_id = ?";
    const params: unknown[] = [seriesId];

    if (dateRange?.start) {
      sql += " AND date >= ?";
      params.push(dateRange.start);
    }
    if (dateRange?.end) {
      sql += " AND date <= ?";
      params.push(dateRange.end);
    }
    sql += " ORDER BY date ASC";

    return this.query(this.marketDB, sql, params);
  }
}
