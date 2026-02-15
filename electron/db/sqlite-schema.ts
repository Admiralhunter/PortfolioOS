/**
 * SQLite schema definitions for app state.
 *
 * Manages transactional data: accounts, preferences, LLM providers,
 * and data sources. Separate from DuckDB analytical databases.
 */

export const CREATE_ACCOUNTS = `
CREATE TABLE IF NOT EXISTS accounts (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  type TEXT NOT NULL,
  institution TEXT DEFAULT '',
  notes TEXT DEFAULT '',
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now'))
)`;

export const CREATE_PREFERENCES = `
CREATE TABLE IF NOT EXISTS preferences (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TEXT DEFAULT (datetime('now'))
)`;

export const CREATE_LLM_PROVIDERS = `
CREATE TABLE IF NOT EXISTS llm_providers (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  provider_type TEXT NOT NULL,
  endpoint_url TEXT NOT NULL,
  model TEXT DEFAULT '',
  is_default INTEGER DEFAULT 0,
  is_local INTEGER DEFAULT 0,
  created_at TEXT DEFAULT (datetime('now'))
)`;

export const CREATE_DATA_SOURCES = `
CREATE TABLE IF NOT EXISTS data_sources (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  source_type TEXT NOT NULL,
  api_key_ref TEXT DEFAULT '',
  rate_limit_per_min INTEGER DEFAULT 60,
  enabled INTEGER DEFAULT 1,
  created_at TEXT DEFAULT (datetime('now'))
)`;

export const ALL_TABLES = [
  CREATE_ACCOUNTS,
  CREATE_PREFERENCES,
  CREATE_LLM_PROVIDERS,
  CREATE_DATA_SOURCES,
];

/** Default LM Studio provider — always available locally. */
export const DEFAULT_LLM_PROVIDER = {
  id: "lmstudio-default",
  name: "LM Studio (Local)",
  provider_type: "lmstudio",
  endpoint_url: "http://localhost:1234/v1",
  model: "",
  is_default: 1,
  is_local: 1,
};

/** Default preferences. */
export const DEFAULT_PREFERENCES: Record<string, string> = {
  theme: "system",
  currency: "USD",
  date_format: "YYYY-MM-DD",
  default_withdrawal_rate: "0.04",
  simulation_trials: "10000",
  simulation_years: "50",
};
