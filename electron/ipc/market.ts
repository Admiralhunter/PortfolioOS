/**
 * IPC handlers for market data operations.
 *
 * Routes market data requests to the Python sidecar (fetch + validate)
 * and DuckDB (cached reads).
 */

import { ipcMain, type IpcMainInvokeEvent } from "electron";
import type { SidecarManager } from "../services/sidecar";
import type { DuckDBManager } from "../db/duckdb";
import type { IPCResponse } from "../types";

export function registerMarketHandlers(
  sidecar: SidecarManager,
  duckdb: DuckDBManager
): void {
  ipcMain.handle(
    "market:fetch-prices",
    async (
      _event,
      symbol: string,
      startDate: string,
      endDate: string
    ): Promise<IPCResponse<unknown>> => {
      try {
        const result = await sidecar.send("market.yahoo.price_history", {
          symbol,
          start_date: startDate,
          end_date: endDate,
        });
        return { success: true, data: result };
      } catch (err) {
        return { success: false, error: (err as Error).message };
      }
    }
  );

  ipcMain.handle(
    "market:fetch-macro",
    async (
      _event,
      seriesId: string,
      startDate: string,
      endDate: string
    ): Promise<IPCResponse<unknown>> => {
      try {
        const result = await sidecar.send("market.fred.series", {
          series_id: seriesId,
          start_date: startDate,
          end_date: endDate,
        });
        return { success: true, data: result };
      } catch (err) {
        return { success: false, error: (err as Error).message };
      }
    }
  );

  ipcMain.handle(
    "market:get-cached-prices",
    async (_event: IpcMainInvokeEvent, symbol: string, dateRange?: { start: string; end: string }): Promise<IPCResponse<unknown>> => {
      try {
        const prices = await duckdb.getPriceHistory(symbol, dateRange);
        return { success: true, data: prices };
      } catch (err) {
        return { success: false, error: (err as Error).message };
      }
    }
  );

  ipcMain.handle(
    "market:detect-gaps",
    async (_event, symbol: string): Promise<IPCResponse<unknown>> => {
      try {
        // First get cached prices from DuckDB
        const prices = await duckdb.getPriceHistory(symbol);
        // Then run gap detection through sidecar
        const result = await sidecar.send("validation.detect_gaps", {
          records: prices,
        });
        return { success: true, data: result };
      } catch (err) {
        return { success: false, error: (err as Error).message };
      }
    }
  );

  ipcMain.handle(
    "market:get-symbol-info",
    async (_event, symbol: string): Promise<IPCResponse<unknown>> => {
      try {
        const result = await sidecar.send("market.yahoo.info", { symbol });
        return { success: true, data: result };
      } catch (err) {
        return { success: false, error: (err as Error).message };
      }
    }
  );
}
