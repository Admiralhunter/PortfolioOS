/**
 * IPC handlers for simulation operations.
 *
 * Routes simulation requests to the Python sidecar for Monte Carlo,
 * scenario, and sensitivity analysis computations.
 */

import { ipcMain, type IpcMainInvokeEvent } from "electron";
import type { SidecarManager } from "../services/sidecar";
import type { IPCResponse, SimulationConfig, ScenarioConfig } from "../types";

/** Simulation timeout — 60s for large simulations. */
const SIMULATION_TIMEOUT_MS = 60_000;

export function registerSimulationHandlers(sidecar: SidecarManager): void {
  ipcMain.handle(
    "simulation:run",
    async (_event: IpcMainInvokeEvent, config: SimulationConfig): Promise<IPCResponse<unknown>> => {
      try {
        const result = await sidecar.send(
          "simulation.run",
          config as unknown as Record<string, unknown>,
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
    async (_event: IpcMainInvokeEvent, config: ScenarioConfig): Promise<IPCResponse<unknown>> => {
      try {
        const result = await sidecar.send(
          "simulation.scenario",
          config as unknown as Record<string, unknown>,
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
    async (_event: IpcMainInvokeEvent, config: ScenarioConfig & { vary_param: string; values: number[] }): Promise<IPCResponse<unknown>> => {
      try {
        // Sensitivity runs multiple simulations, use extended timeout
        const result = await sidecar.send(
          "simulation.sensitivity",
          config as unknown as Record<string, unknown>,
          SIMULATION_TIMEOUT_MS * 3
        );
        return { success: true, data: result };
      } catch (err) {
        return { success: false, error: (err as Error).message };
      }
    }
  );
}
