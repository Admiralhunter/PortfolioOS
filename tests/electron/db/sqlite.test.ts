/**
 * Tests for the SQLite app state database.
 *
 * Uses a temporary database for each test to ensure isolation.
 */

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import * as fs from "node:fs";
import * as path from "node:path";
import * as os from "node:os";
import {
  initSQLite,
  closeSQLite,
  createAccount,
  getAccounts,
  getAccount,
  updateAccount,
  deleteAccount,
  getPreference,
  setPreference,
  getAllPreferences,
  addLLMProvider,
  getLLMProviders,
  setDefaultProvider,
  removeProvider,
  addDataSource,
  getDataSources,
  updateDataSource,
} from "../../../electron/db/sqlite";

let tmpDir: string;
let dbPath: string;

beforeEach(() => {
  tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "portfolioos-test-"));
  dbPath = path.join(tmpDir, "test.sqlite");
  initSQLite(dbPath);
});

afterEach(() => {
  closeSQLite();
  fs.rmSync(tmpDir, { recursive: true, force: true });
});

describe("Accounts", () => {
  it("creates an account and retrieves it", () => {
    const account = createAccount("My IRA", "ira", "Fidelity", "Notes");
    expect(account.name).toBe("My IRA");
    expect(account.type).toBe("ira");
    expect(account.institution).toBe("Fidelity");
    expect(account.id).toBeTruthy();

    const retrieved = getAccount(account.id);
    expect(retrieved?.name).toBe("My IRA");
  });

  it("lists all accounts", () => {
    createAccount("Account A", "taxable");
    createAccount("Account B", "ira");
    const accounts = getAccounts();
    expect(accounts.length).toBe(2);
  });

  it("updates an account", () => {
    const account = createAccount("Old Name", "taxable");
    const updated = updateAccount(account.id, { name: "New Name" });
    expect(updated?.name).toBe("New Name");
    expect(updated?.type).toBe("taxable"); // unchanged
  });

  it("returns undefined when updating nonexistent account", () => {
    const result = updateAccount("nonexistent", { name: "X" });
    expect(result).toBeUndefined();
  });

  it("deletes an account", () => {
    const account = createAccount("To Delete", "taxable");
    expect(deleteAccount(account.id)).toBe(true);
    expect(getAccount(account.id)).toBeUndefined();
  });

  it("returns false when deleting nonexistent account", () => {
    expect(deleteAccount("nonexistent")).toBe(false);
  });
});

describe("Preferences", () => {
  it("has default preferences after init", () => {
    const prefs = getAllPreferences();
    expect(prefs.theme).toBe("system");
    expect(prefs.currency).toBe("USD");
    expect(prefs.default_withdrawal_rate).toBe("0.04");
  });

  it("gets a preference", () => {
    expect(getPreference("theme")).toBe("system");
  });

  it("sets and gets a preference", () => {
    setPreference("theme", "dark");
    expect(getPreference("theme")).toBe("dark");
  });

  it("returns undefined for missing preference", () => {
    expect(getPreference("nonexistent")).toBeUndefined();
  });
});

describe("LLM Providers", () => {
  it("has default LM Studio provider after init", () => {
    const providers = getLLMProviders();
    expect(providers.length).toBeGreaterThanOrEqual(1);
    const lmstudio = providers.find((p) => p.id === "lmstudio-default");
    expect(lmstudio).toBeTruthy();
    expect(lmstudio?.is_default).toBe(true);
    expect(lmstudio?.is_local).toBe(true);
  });

  it("adds a new provider", () => {
    const provider = addLLMProvider(
      "OpenAI",
      "openai",
      "https://api.openai.com/v1",
      "gpt-4o",
      false
    );
    expect(provider.name).toBe("OpenAI");
    expect(provider.is_local).toBe(false);
    expect(provider.is_default).toBe(false);
  });

  it("sets a default provider", () => {
    const provider = addLLMProvider(
      "OpenAI",
      "openai",
      "https://api.openai.com/v1",
      "gpt-4o",
      false
    );
    expect(setDefaultProvider(provider.id)).toBe(true);

    const providers = getLLMProviders();
    const openai = providers.find((p) => p.id === provider.id);
    expect(openai?.is_default).toBe(true);

    // LM Studio should no longer be default
    const lmstudio = providers.find((p) => p.id === "lmstudio-default");
    expect(lmstudio?.is_default).toBe(false);
  });

  it("removes a provider", () => {
    const provider = addLLMProvider(
      "Test",
      "openai",
      "http://test",
      "test",
      false
    );
    expect(removeProvider(provider.id)).toBe(true);
    const providers = getLLMProviders();
    expect(providers.find((p) => p.id === provider.id)).toBeUndefined();
  });
});

describe("Data Sources", () => {
  it("adds a data source", () => {
    const ds = addDataSource("FRED", "fred", "fred-api-key", 120);
    expect(ds.name).toBe("FRED");
    expect(ds.source_type).toBe("fred");
    expect(ds.rate_limit_per_min).toBe(120);
    expect(ds.enabled).toBe(true);
  });

  it("lists data sources", () => {
    addDataSource("FRED", "fred");
    addDataSource("Yahoo", "yahoo");
    const sources = getDataSources();
    expect(sources.length).toBe(2);
  });

  it("updates a data source", () => {
    const ds = addDataSource("FRED", "fred");
    expect(updateDataSource(ds.id, { rate_limit_per_min: 30 })).toBe(true);
    const sources = getDataSources();
    const updated = sources.find((s) => s.id === ds.id);
    expect(updated?.rate_limit_per_min).toBe(30);
  });

  it("returns false for nonexistent data source update", () => {
    expect(updateDataSource("nonexistent", { name: "X" })).toBe(false);
  });
});
