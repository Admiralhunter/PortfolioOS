/**
 * IPC handlers for system operations.
 *
 * Returns app paths, manages preferences, and provides version info.
 */

import { ipcMain } from "electron";
import * as fs from "node:fs";
import * as path from "node:path";
import type { IPCResponse } from "../types";
import { getPreference, setPreference, getAllPreferences } from "../db/sqlite";

interface AppConfig {
  dataDir: string;
  configDir: string;
  logsDir: string;
}

export function registerSystemHandlers(config: AppConfig): void {
  ipcMain.handle(
    "system:get-paths",
    async (): Promise<IPCResponse<unknown>> => {
      try {
        return {
          success: true,
          data: {
            data: config.dataDir,
            config: config.configDir,
            logs: config.logsDir,
          },
        };
      } catch (err) {
        return { success: false, error: (err as Error).message };
      }
    }
  );

  ipcMain.handle(
    "system:get-preferences",
    async (): Promise<IPCResponse<unknown>> => {
      try {
        return { success: true, data: getAllPreferences() };
      } catch (err) {
        return { success: false, error: (err as Error).message };
      }
    }
  );

  ipcMain.handle(
    "system:get-preference",
    async (_event, key: string): Promise<IPCResponse<unknown>> => {
      try {
        const value = getPreference(key);
        return { success: true, data: value };
      } catch (err) {
        return { success: false, error: (err as Error).message };
      }
    }
  );

  ipcMain.handle(
    "system:set-preference",
    async (_event, key: string, value: string): Promise<IPCResponse<unknown>> => {
      try {
        setPreference(key, value);
        return { success: true };
      } catch (err) {
        return { success: false, error: (err as Error).message };
      }
    }
  );

  ipcMain.handle(
    "system:get-version",
    async (): Promise<IPCResponse<unknown>> => {
      try {
        const pkgPath = path.join(process.cwd(), "package.json");
        const pkg = JSON.parse(fs.readFileSync(pkgPath, "utf-8")) as {
          version: string;
        };
        return { success: true, data: { version: pkg.version } };
      } catch (err) {
        return { success: false, error: (err as Error).message };
      }
    }
  );
}
