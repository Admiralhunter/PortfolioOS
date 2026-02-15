/**
 * IPC handlers for simulation operations.
 *
 * Routes simulation requests to the Python sidecar for Monte Carlo,
 * scenario, and sensitivity analysis computations.
 */

import { ipcMain } from "electron";
import type { SidecarManager } from "../services/sidecar";
import type { IPCResponse } from "../types";

/** Simulation timeout — 60s for large simulations. */
const SIMULATION_TIMEOUT_MS = 60_000;

export function registerSimulationHandlers(sidecar: SidecarManager): void {
  ipcMain.handle(
    "simulation:run",
    async (_event, config): Promise<IPCResponse<unknown>> => {
      try {
        const result = await sidecar.send(
          "simulation.run",
          config,
          SIMULATION_TIMEOUT_MS
        );
        return { success: true, data: result };
      } catch (err) {
        return { success: false, error: (err as Error).message };
      }
    }
  );

  ipcMain.handle(
    "simulation:scenario",
    async (_event, config): Promise<IPCResponse<unknown>> => {
      try {
        const result = await sidecar.send(
          "simulation.scenario",
          config,
          SIMULATION_TIMEOUT_MS
        );
        return { success: true, data: result };
      } catch (err) {
        return { success: false, error: (err as Error).message };
      }
    }
  );

  ipcMain.handle(
    "simulation:sensitivity",
    async (_event, config): Promise<IPCResponse<unknown>> => {
      try {
        // Sensitivity runs multiple simulations, use extended timeout
        const result = await sidecar.send(
          "simulation.sensitivity",
          config,
          SIMULATION_TIMEOUT_MS * 3
        );
        return { success: true, data: result };
      } catch (err) {
        return { success: false, error: (err as Error).message };
      }
    }
  );
}
