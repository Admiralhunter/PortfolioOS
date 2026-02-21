/**
 * Shared type definitions for the PortfolioOS renderer.
 *
 * These mirror the types in electron/types.ts so the renderer
 * can reference them without importing from the Electron process.
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

export type WithdrawalStrategy =
  | "constant_dollar"
  | "constant_percentage"
  | "guyton_klinger";

export type LifeEventType =
  | "windfall"
  | "expense"
  | "income_change"
  | "savings_rate_change";

export type FIREType = "lean" | "normal" | "fat" | "coast" | "barista";

export interface ScenarioConfig extends SimulationConfig {
  withdrawal_strategy?: WithdrawalStrategy;
  life_events?: LifeEvent[];
}

export interface LifeEvent {
  year: number;
  type: LifeEventType;
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

export type SensitivityParam =
  | "withdrawal_rate"
  | "inflation_rate"
  | "n_years";

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

export type LLMProviderType =
  | "lmstudio"
  | "openai"
  | "anthropic"
  | "openrouter";

export interface AddProviderParams {
  name: string;
  provider_type: LLMProviderType;
  endpoint_url: string;
  model: string;
  is_local: boolean;
  api_key?: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
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
