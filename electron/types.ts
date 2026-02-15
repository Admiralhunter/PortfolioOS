/**
 * Shared TypeScript type definitions for the PortfolioOS Electron backend.
 *
 * These types define the IPC API surface between the renderer (React)
 * and the main process (Node.js).
 */

// ── Account ──

export interface Account {
  id: string;
  name: string;
  type: string;
  institution: string;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface CreateAccountParams {
  name: string;
  type: string;
  institution?: string;
  notes?: string;
}

// ── Holdings ──

export interface Holding {
  id: string;
  account_id: string;
  symbol: string;
  asset_type: string;
  shares: number;
  cost_basis: number;
  created_at: string;
  updated_at: string;
}

// ── Transactions ──

export interface Transaction {
  id: string;
  account_id: string;
  symbol: string;
  type: string;
  date: string;
  quantity: number;
  price: number;
  fees: number;
  notes: string;
  created_at: string;
}

export interface TransactionFilters {
  account_id?: string;
  symbol?: string;
  start_date?: string;
  end_date?: string;
}

// ── Portfolio Snapshots ──

export interface Snapshot {
  account_id: string;
  date: string;
  total_value: number;
  total_cost_basis: number;
  unrealized_gain: number;
}

// ── Market Data ──

export interface PriceRecord {
  symbol: string;
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  adj_close: number;
  volume: number;
}

export interface MacroRecord {
  series_id: string;
  date: string;
  value: number;
}

export interface Gap {
  expected_date: string;
  gap_type: string;
}

// ── Simulation ──

export interface SimulationConfig {
  initial_portfolio: number;
  annual_withdrawal: number;
  return_distribution: number[];
  n_trials?: number;
  n_years?: number;
  inflation_rate?: number;
  seed?: number;
}

export interface ScenarioConfig extends SimulationConfig {
  withdrawal_strategy?: string;
  life_events?: LifeEvent[];
}

export interface LifeEvent {
  year: number;
  type: string;
  amount: number;
}

export interface SimulationResult {
  success_rate: number;
  percentiles: Record<number, number[]>;
  median_final_value: number;
  strategy: string;
}

export interface SensitivityResult {
  param_name: string;
  param_value: number;
  success_rate: number;
  median_final_value: number;
}

// ── LLM ──

export interface LLMProvider {
  id: string;
  name: string;
  provider_type: string;
  endpoint_url: string;
  model: string;
  is_default: boolean;
  is_local: boolean;
}

export interface LLMOptions {
  model?: string;
  temperature?: number;
  maxTokens?: number;
  systemPrompt?: string;
}

export interface LLMResponse {
  content: string;
  model: string;
  tokensUsed: { prompt: number; completion: number };
}

// ── Data Source ──

export interface DataSource {
  id: string;
  name: string;
  source_type: string;
  api_key_ref: string;
  rate_limit_per_min: number;
  enabled: boolean;
}

// ── Import ──

export interface ImportResult {
  transactions_imported: number;
  holdings_reconciled: number;
  errors: string[];
}

// ── System ──

export interface AppPaths {
  data: string;
  config: string;
  logs: string;
}

export interface Preferences {
  [key: string]: string;
}

// ── IPC Response Wrapper ──

export interface IPCResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
}

// ── Preload API ──

export interface PortfolioOSAPI {
  portfolio: {
    createAccount(params: CreateAccountParams): Promise<IPCResponse<Account>>;
    listAccounts(): Promise<IPCResponse<Account[]>>;
    updateAccount(id: string, params: Partial<CreateAccountParams>): Promise<IPCResponse<Account>>;
    deleteAccount(id: string): Promise<IPCResponse<void>>;
    importCSV(filePath: string, accountId: string): Promise<IPCResponse<ImportResult>>;
    getHoldings(accountId?: string): Promise<IPCResponse<Holding[]>>;
    getTransactions(filters?: TransactionFilters): Promise<IPCResponse<Transaction[]>>;
    getSnapshots(accountId: string, dateRange?: { start: string; end: string }): Promise<IPCResponse<Snapshot[]>>;
    reconcile(accountId: string): Promise<IPCResponse<void>>;
  };
  market: {
    fetchPriceHistory(symbol: string, startDate: string, endDate: string): Promise<IPCResponse<PriceRecord[]>>;
    fetchMacroSeries(seriesId: string, startDate: string, endDate: string): Promise<IPCResponse<MacroRecord[]>>;
    detectGaps(symbol: string): Promise<IPCResponse<Gap[]>>;
    getCachedPrices(symbol: string, dateRange?: { start: string; end: string }): Promise<IPCResponse<PriceRecord[]>>;
  };
  simulation: {
    run(config: SimulationConfig): Promise<IPCResponse<SimulationResult>>;
    runScenario(config: ScenarioConfig): Promise<IPCResponse<SimulationResult>>;
    sensitivity(config: ScenarioConfig & { vary_param: string; values: number[] }): Promise<IPCResponse<SensitivityResult[]>>;
  };
  llm: {
    listProviders(): Promise<IPCResponse<LLMProvider[]>>;
    setDefault(providerId: string): Promise<IPCResponse<void>>;
    send(prompt: string, options?: LLMOptions): Promise<IPCResponse<LLMResponse>>;
  };
  data: {
    exportCSV(type: string, filters: Record<string, unknown>, outputPath: string): Promise<IPCResponse<string>>;
    exportJSON(filters: Record<string, unknown>, outputPath: string): Promise<IPCResponse<string>>;
  };
  system: {
    getAppPaths(): Promise<IPCResponse<AppPaths>>;
    getPreferences(): Promise<IPCResponse<Preferences>>;
    setPreference(key: string, value: string): Promise<IPCResponse<void>>;
  };
}
