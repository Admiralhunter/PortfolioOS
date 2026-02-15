/**
 * IPC handlers for data export operations.
 *
 * Routes export requests to the Python sidecar for CSV and JSON
 * generation.
 */

import { ipcMain } from "electron";
import type { SidecarManager } from "../services/sidecar";
import type { IPCResponse } from "../types";

export function registerDataHandlers(sidecar: SidecarManager): void {
  ipcMain.handle(
    "data:export-csv",
    async (
      _event,
      type: string,
      filters: Record<string, unknown>,
      outputPath: string
    ): Promise<IPCResponse<unknown>> => {
      try {
        const methodMap: Record<string, string> = {
          holdings: "export.holdings_csv",
          transactions: "export.transactions_csv",
          simulation: "export.simulation_csv",
        };
        const method = methodMap[type];
        if (!method) {
          return { success: false, error: `Unknown export type: ${type}` };
        }
        const result = await sidecar.send(method, {
          ...filters,
          output_path: outputPath,
        });
        return { success: true, data: result };
      } catch (err) {
        return { success: false, error: (err as Error).message };
      }
    }
  );

  ipcMain.handle(
    "data:export-json",
    async (
      _event,
      filters: Record<string, unknown>,
      outputPath: string
    ): Promise<IPCResponse<unknown>> => {
      try {
        const result = await sidecar.send("export.portfolio_json", {
          ...filters,
          output_path: outputPath,
        });
        return { success: true, data: result };
      } catch (err) {
        return { success: false, error: (err as Error).message };
      }
    }
  );
}
