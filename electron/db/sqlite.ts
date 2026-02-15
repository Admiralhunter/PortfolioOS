/**
 * SQLite app state database — manages accounts, preferences,
 * LLM providers, and data sources.
 *
 * Uses better-sqlite3 for synchronous, fast operations suitable
 * for transactional app state (not analytics).
 */

import Database from "better-sqlite3";
import { v4 as uuidv4 } from "uuid";
import {
  ALL_TABLES,
  DEFAULT_LLM_PROVIDER,
  DEFAULT_PREFERENCES,
} from "./sqlite-schema";
import type { Account, LLMProvider, DataSource } from "../types";

let db: Database.Database | null = null;

/**
 * Initialize the SQLite database at the given path.
 * Creates tables and inserts defaults on first run.
 */
export function initSQLite(dbPath: string): Database.Database {
  db = new Database(dbPath);
  db.pragma("journal_mode = WAL");
  db.pragma("foreign_keys = ON");

  for (const ddl of ALL_TABLES) {
    db.exec(ddl);
  }

  // Insert default LLM provider if not present
  const existing = db
    .prepare("SELECT id FROM llm_providers WHERE id = ?")
    .get(DEFAULT_LLM_PROVIDER.id);
  if (!existing) {
    db.prepare(
      `INSERT INTO llm_providers (id, name, provider_type, endpoint_url, model, is_default, is_local)
       VALUES (?, ?, ?, ?, ?, ?, ?)`
    ).run(
      DEFAULT_LLM_PROVIDER.id,
      DEFAULT_LLM_PROVIDER.name,
      DEFAULT_LLM_PROVIDER.provider_type,
      DEFAULT_LLM_PROVIDER.endpoint_url,
      DEFAULT_LLM_PROVIDER.model,
      DEFAULT_LLM_PROVIDER.is_default,
      DEFAULT_LLM_PROVIDER.is_local
    );
  }

  // Insert default preferences if not present
  const insertPref = db.prepare(
    `INSERT OR IGNORE INTO preferences (key, value) VALUES (?, ?)`
  );
  for (const [key, value] of Object.entries(DEFAULT_PREFERENCES)) {
    insertPref.run(key, value);
  }

  return db;
}

/** Get the active database instance. */
export function getDB(): Database.Database {
  if (!db) {
    throw new Error("SQLite not initialized. Call initSQLite() first.");
  }
  return db;
}

/** Close the database connection. */
export function closeSQLite(): void {
  if (db) {
    db.close();
    db = null;
  }
}

// ── Accounts ──

export function createAccount(
  name: string,
  type: string,
  institution = "",
  notes = ""
): Account {
  const d = getDB();
  const id = uuidv4();
  const now = new Date().toISOString();
  d.prepare(
    `INSERT INTO accounts (id, name, type, institution, notes, created_at, updated_at)
     VALUES (?, ?, ?, ?, ?, ?, ?)`
  ).run(id, name, type, institution, notes, now, now);
  return { id, name, type, institution, notes, created_at: now, updated_at: now };
}

export function getAccounts(): Account[] {
  const d = getDB();
  return d.prepare("SELECT * FROM accounts ORDER BY name").all() as Account[];
}

export function getAccount(id: string): Account | undefined {
  const d = getDB();
  return d.prepare("SELECT * FROM accounts WHERE id = ?").get(id) as
    | Account
    | undefined;
}

export function updateAccount(
  id: string,
  updates: { name?: string; type?: string; institution?: string; notes?: string }
): Account | undefined {
  const d = getDB();
  const existing = getAccount(id);
  if (!existing) return undefined;

  const name = updates.name ?? existing.name;
  const type = updates.type ?? existing.type;
  const institution = updates.institution ?? existing.institution;
  const notes = updates.notes ?? existing.notes;
  const now = new Date().toISOString();

  d.prepare(
    `UPDATE accounts SET name = ?, type = ?, institution = ?, notes = ?, updated_at = ?
     WHERE id = ?`
  ).run(name, type, institution, notes, now, id);

  return { ...existing, name, type, institution, notes, updated_at: now };
}

export function deleteAccount(id: string): boolean {
  const d = getDB();
  const result = d.prepare("DELETE FROM accounts WHERE id = ?").run(id);
  return result.changes > 0;
}

// ── Preferences ──

export function getPreference(key: string): string | undefined {
  const d = getDB();
  const row = d.prepare("SELECT value FROM preferences WHERE key = ?").get(key) as
    | { value: string }
    | undefined;
  return row?.value;
}

export function setPreference(key: string, value: string): void {
  const d = getDB();
  d.prepare(
    `INSERT OR REPLACE INTO preferences (key, value, updated_at)
     VALUES (?, ?, datetime('now'))`
  ).run(key, value);
}

export function getAllPreferences(): Record<string, string> {
  const d = getDB();
  const rows = d.prepare("SELECT key, value FROM preferences").all() as {
    key: string;
    value: string;
  }[];
  const prefs: Record<string, string> = {};
  for (const row of rows) {
    prefs[row.key] = row.value;
  }
  return prefs;
}

// ── LLM Providers ──

export function addLLMProvider(
  name: string,
  providerType: string,
  endpointUrl: string,
  model: string,
  isLocal: boolean
): LLMProvider {
  const d = getDB();
  const id = uuidv4();
  d.prepare(
    `INSERT INTO llm_providers (id, name, provider_type, endpoint_url, model, is_default, is_local)
     VALUES (?, ?, ?, ?, ?, 0, ?)`
  ).run(id, name, providerType, endpointUrl, model, isLocal ? 1 : 0);
  return {
    id,
    name,
    provider_type: providerType,
    endpoint_url: endpointUrl,
    model,
    is_default: false,
    is_local: isLocal,
  };
}

export function getLLMProviders(): LLMProvider[] {
  const d = getDB();
  const rows = d.prepare("SELECT * FROM llm_providers ORDER BY name").all() as Array<{
    id: string;
    name: string;
    provider_type: string;
    endpoint_url: string;
    model: string;
    is_default: number;
    is_local: number;
  }>;
  return rows.map((r) => ({
    ...r,
    is_default: r.is_default === 1,
    is_local: r.is_local === 1,
  }));
}

export function setDefaultProvider(id: string): boolean {
  const d = getDB();
  // Unset all defaults, then set the specified one
  const txn = d.transaction(() => {
    d.prepare("UPDATE llm_providers SET is_default = 0").run();
    const result = d.prepare(
      "UPDATE llm_providers SET is_default = 1 WHERE id = ?"
    ).run(id);
    return result.changes > 0;
  });
  return txn();
}

export function removeProvider(id: string): boolean {
  const d = getDB();
  const result = d.prepare("DELETE FROM llm_providers WHERE id = ?").run(id);
  return result.changes > 0;
}

// ── Data Sources ──

export function addDataSource(
  name: string,
  sourceType: string,
  apiKeyRef = "",
  rateLimitPerMin = 60
): DataSource {
  const d = getDB();
  const id = uuidv4();
  d.prepare(
    `INSERT INTO data_sources (id, name, source_type, api_key_ref, rate_limit_per_min)
     VALUES (?, ?, ?, ?, ?)`
  ).run(id, name, sourceType, apiKeyRef, rateLimitPerMin);
  return {
    id,
    name,
    source_type: sourceType,
    api_key_ref: apiKeyRef,
    rate_limit_per_min: rateLimitPerMin,
    enabled: true,
  };
}

export function getDataSources(): DataSource[] {
  const d = getDB();
  const rows = d.prepare("SELECT * FROM data_sources ORDER BY name").all() as Array<{
    id: string;
    name: string;
    source_type: string;
    api_key_ref: string;
    rate_limit_per_min: number;
    enabled: number;
  }>;
  return rows.map((r) => ({
    ...r,
    enabled: r.enabled === 1,
  }));
}

export function updateDataSource(
  id: string,
  updates: {
    name?: string;
    api_key_ref?: string;
    rate_limit_per_min?: number;
    enabled?: boolean;
  }
): boolean {
  const d = getDB();
  const existing = d
    .prepare("SELECT * FROM data_sources WHERE id = ?")
    .get(id) as Record<string, unknown> | undefined;
  if (!existing) return false;

  const name = updates.name ?? (existing.name as string);
  const apiKeyRef = updates.api_key_ref ?? (existing.api_key_ref as string);
  const rateLimit =
    updates.rate_limit_per_min ?? (existing.rate_limit_per_min as number);
  const enabled =
    updates.enabled !== undefined
      ? updates.enabled
        ? 1
        : 0
      : (existing.enabled as number);

  d.prepare(
    `UPDATE data_sources SET name = ?, api_key_ref = ?, rate_limit_per_min = ?, enabled = ?
     WHERE id = ?`
  ).run(name, apiKeyRef, rateLimit, enabled, id);
  return true;
}
