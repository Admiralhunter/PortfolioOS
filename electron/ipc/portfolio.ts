/**
 * IPC handlers for portfolio operations.
 *
 * Routes renderer requests to SQLite (accounts), DuckDB (holdings,
 * transactions, snapshots), and the Python sidecar (import, reconcile).
 */

import { ipcMain, type IpcMainInvokeEvent } from "electron";
import type { SidecarManager } from "../services/sidecar";
import type { DuckDBManager } from "../db/duckdb";
import type { IPCResponse, CreateAccountParams, TransactionFilters } from "../types";
import {
  createAccount,
  getAccounts,
  updateAccount,
  deleteAccount,
} from "../db/sqlite";

export function registerPortfolioHandlers(
  sidecar: SidecarManager,
  duckdb: DuckDBManager
): void {
  ipcMain.handle(
    "portfolio:create-account",
    async (_event: IpcMainInvokeEvent, params: CreateAccountParams): Promise<IPCResponse<unknown>> => {
      try {
        const account = createAccount(
          params.name,
          params.type,
          params.institution ?? "",
          params.notes ?? ""
        );
        return { success: true, data: account };
      } catch (err) {
        return { success: false, error: (err as Error).message };
      }
    }
  );

  ipcMain.handle(
    "portfolio:list-accounts",
    async (): Promise<IPCResponse<unknown>> => {
      try {
        return { success: true, data: getAccounts() };
      } catch (err) {
        return { success: false, error: (err as Error).message };
      }
    }
  );

  ipcMain.handle(
    "portfolio:update-account",
    async (_event: IpcMainInvokeEvent, id: string, params: Partial<CreateAccountParams>): Promise<IPCResponse<unknown>> => {
      try {
        const account = updateAccount(id, params);
        if (!account) {
          return { success: false, error: `Account ${id} not found` };
        }
        return { success: true, data: account };
      } catch (err) {
        return { success: false, error: (err as Error).message };
      }
    }
  );

  ipcMain.handle(
    "portfolio:delete-account",
    async (_event: IpcMainInvokeEvent, id: string): Promise<IPCResponse<unknown>> => {
      try {
        const deleted = deleteAccount(id);
        if (!deleted) {
          return { success: false, error: `Account ${id} not found` };
        }
        return { success: true };
      } catch (err) {
        return { success: false, error: (err as Error).message };
      }
    }
  );

  ipcMain.handle(
    "portfolio:import-csv",
    async (_event: IpcMainInvokeEvent, filePath: string, accountId: string): Promise<IPCResponse<unknown>> => {
      try {
        const result = await sidecar.send("ingest.csv", {
          file_path: filePath,
          account_id: accountId,
        });
        return { success: true, data: result };
      } catch (err) {
        return { success: false, error: (err as Error).message };
      }
    }
  );

  ipcMain.handle(
    "portfolio:get-holdings",
    async (_event: IpcMainInvokeEvent, accountId?: string): Promise<IPCResponse<unknown>> => {
      try {
        const holdings = await duckdb.getHoldings(accountId);
        return { success: true, data: holdings };
      } catch (err) {
        return { success: false, error: (err as Error).message };
      }
    }
  );

  ipcMain.handle(
    "portfolio:get-transactions",
    async (_event: IpcMainInvokeEvent, filters?: TransactionFilters): Promise<IPCResponse<unknown>> => {
      try {
        const transactions = await duckdb.getTransactions(filters);
        return { success: true, data: transactions };
      } catch (err) {
        return { success: false, error: (err as Error).message };
      }
    }
  );

  ipcMain.handle(
    "portfolio:get-snapshots",
    async (_event: IpcMainInvokeEvent, accountId: string, dateRange?: { start: string; end: string }): Promise<IPCResponse<unknown>> => {
      try {
        const snapshots = await duckdb.getSnapshots(accountId, dateRange);
        return { success: true, data: snapshots };
      } catch (err) {
        return { success: false, error: (err as Error).message };
      }
    }
  );

  ipcMain.handle(
    "portfolio:reconcile",
    async (_event: IpcMainInvokeEvent, accountId: string): Promise<IPCResponse<unknown>> => {
      try {
        const transactions = await duckdb.getTransactions({
          account_id: accountId,
        });
        const result = await sidecar.send("portfolio.reconcile", {
          transactions,
        });
        return { success: true, data: result };
      } catch (err) {
        return { success: false, error: (err as Error).message };
      }
    }
  );
}
