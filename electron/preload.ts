/**
 * Preload script — exposes a typed API surface to the renderer process
 * via contextBridge. The renderer accesses backend operations through
 * window.api without direct access to Node.js or Electron internals.
 *
 * Security: contextIsolation is enabled, nodeIntegration is disabled.
 */

import { contextBridge, ipcRenderer } from "electron";
import type {
  CreateAccountParams,
  LLMOptions,
  ScenarioConfig,
  SimulationConfig,
  TransactionFilters,
} from "./types";

const api = {
  portfolio: {
    createAccount: (params: CreateAccountParams) =>
      ipcRenderer.invoke("portfolio:create-account", params),
    listAccounts: () => ipcRenderer.invoke("portfolio:list-accounts"),
    updateAccount: (id: string, params: Partial<CreateAccountParams>) =>
      ipcRenderer.invoke("portfolio:update-account", id, params),
    deleteAccount: (id: string) =>
      ipcRenderer.invoke("portfolio:delete-account", id),
    importCSV: (filePath: string, accountId: string) =>
      ipcRenderer.invoke("portfolio:import-csv", filePath, accountId),
    getHoldings: (accountId?: string) =>
      ipcRenderer.invoke("portfolio:get-holdings", accountId),
    getTransactions: (filters?: TransactionFilters) =>
      ipcRenderer.invoke("portfolio:get-transactions", filters),
    getSnapshots: (
      accountId: string,
      dateRange?: { start: string; end: string }
    ) => ipcRenderer.invoke("portfolio:get-snapshots", accountId, dateRange),
    reconcile: (accountId: string) =>
      ipcRenderer.invoke("portfolio:reconcile", accountId),
  },
  market: {
    fetchPriceHistory: (symbol: string, startDate: string, endDate: string) =>
      ipcRenderer.invoke("market:fetch-prices", symbol, startDate, endDate),
    fetchMacroSeries: (seriesId: string, startDate: string, endDate: string) =>
      ipcRenderer.invoke("market:fetch-macro", seriesId, startDate, endDate),
    detectGaps: (symbol: string) =>
      ipcRenderer.invoke("market:detect-gaps", symbol),
    getCachedPrices: (
      symbol: string,
      dateRange?: { start: string; end: string }
    ) => ipcRenderer.invoke("market:get-cached-prices", symbol, dateRange),
  },
  simulation: {
    run: (config: SimulationConfig) =>
      ipcRenderer.invoke("simulation:run", config),
    runScenario: (config: ScenarioConfig) =>
      ipcRenderer.invoke("simulation:scenario", config),
    sensitivity: (
      config: ScenarioConfig & { vary_param: string; values: number[] }
    ) => ipcRenderer.invoke("simulation:sensitivity", config),
  },
  llm: {
    listProviders: () => ipcRenderer.invoke("llm:list-providers"),
    setDefault: (providerId: string) =>
      ipcRenderer.invoke("llm:set-default", providerId),
    send: (prompt: string, options?: LLMOptions) =>
      ipcRenderer.invoke("llm:send", prompt, options),
  },
  data: {
    exportCSV: (
      type: string,
      filters: Record<string, unknown>,
      outputPath: string
    ) => ipcRenderer.invoke("data:export-csv", type, filters, outputPath),
    exportJSON: (filters: Record<string, unknown>, outputPath: string) =>
      ipcRenderer.invoke("data:export-json", filters, outputPath),
  },
  system: {
    getAppPaths: () => ipcRenderer.invoke("system:get-paths"),
    getPreferences: () => ipcRenderer.invoke("system:get-preferences"),
    setPreference: (key: string, value: string) =>
      ipcRenderer.invoke("system:set-preference", key, value),
  },
};

contextBridge.exposeInMainWorld("api", api);
