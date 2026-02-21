/**
 * Renderer-side type definitions mirroring the preload API surface.
 *
 * These types describe the `window.api` object exposed by the preload
 * script via contextBridge.
 */

import type {
  Account,
  CreateAccountParams,
  Holding,
  Transaction,
  TransactionFilters,
  Snapshot,
  PriceRecord,
  MacroRecord,
  Gap,
  SimulationConfig,
  ScenarioConfig,
  SimulationResult,
  SensitivityResult,
  LLMProvider,
  LLMOptions,
  LLMResponse,
  ImportResult,
  AppPaths,
  Preferences,
  IPCResponse,
} from "./index";

export interface PortfolioAPI {
  createAccount(params: CreateAccountParams): Promise<IPCResponse<Account>>;
  listAccounts(): Promise<IPCResponse<Account[]>>;
  updateAccount(id: string, params: Partial<CreateAccountParams>): Promise<IPCResponse<Account>>;
  deleteAccount(id: string): Promise<IPCResponse<void>>;
  importCSV(filePath: string, accountId: string): Promise<IPCResponse<ImportResult>>;
  getHoldings(accountId?: string): Promise<IPCResponse<Holding[]>>;
  getTransactions(filters?: TransactionFilters): Promise<IPCResponse<Transaction[]>>;
  getSnapshots(accountId: string, dateRange?: { start: string; end: string }): Promise<IPCResponse<Snapshot[]>>;
  reconcile(accountId: string): Promise<IPCResponse<void>>;
}

export interface MarketAPI {
  fetchPriceHistory(symbol: string, startDate: string, endDate: string): Promise<IPCResponse<PriceRecord[]>>;
  fetchMacroSeries(seriesId: string, startDate: string, endDate: string): Promise<IPCResponse<MacroRecord[]>>;
  detectGaps(symbol: string): Promise<IPCResponse<Gap[]>>;
  getCachedPrices(symbol: string, dateRange?: { start: string; end: string }): Promise<IPCResponse<PriceRecord[]>>;
}

export interface SimulationAPI {
  run(config: SimulationConfig): Promise<IPCResponse<SimulationResult>>;
  runScenario(config: ScenarioConfig): Promise<IPCResponse<SimulationResult>>;
  sensitivity(config: ScenarioConfig & { vary_param: string; values: number[] }): Promise<IPCResponse<SensitivityResult[]>>;
}

export interface LLMAPI {
  listProviders(): Promise<IPCResponse<LLMProvider[]>>;
  setDefault(providerId: string): Promise<IPCResponse<void>>;
  send(prompt: string, options?: LLMOptions): Promise<IPCResponse<LLMResponse>>;
}

export interface DataAPI {
  exportCSV(type: string, filters: Record<string, unknown>, outputPath: string): Promise<IPCResponse<string>>;
  exportJSON(filters: Record<string, unknown>, outputPath: string): Promise<IPCResponse<string>>;
}

export interface SystemAPI {
  getAppPaths(): Promise<IPCResponse<AppPaths>>;
  getPreferences(): Promise<IPCResponse<Preferences>>;
  setPreference(key: string, value: string): Promise<IPCResponse<void>>;
}

export interface PortfolioOSAPI {
  portfolio: PortfolioAPI;
  market: MarketAPI;
  simulation: SimulationAPI;
  llm: LLMAPI;
  data: DataAPI;
  system: SystemAPI;
}

declare global {
  interface Window {
    api: PortfolioOSAPI;
  }
}
