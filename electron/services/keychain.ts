/**
 * API key security — encrypts keys at rest using Electron's safeStorage.
 *
 * Electron safeStorage uses the OS keychain:
 * - macOS: Keychain Services
 * - Windows: DPAPI
 * - Linux: libsecret (GNOME Keyring / KWallet)
 *
 * Falls back to plaintext storage with a warning if safeStorage
 * is unavailable (e.g., Linux without libsecret).
 */

import * as fs from "node:fs";
import * as path from "node:path";
import { app } from "electron";

/** In-memory cache for decrypted keys during the session. */
const keyCache: Map<string, string> = new Map();

/** Path to the encrypted key store file. */
function getKeyStorePath(): string {
  const configDir = path.join(app.getPath("home"), ".portfolioos", "config");
  if (!fs.existsSync(configDir)) {
    fs.mkdirSync(configDir, { recursive: true });
  }
  return path.join(configDir, "keys.json");
}

/**
 * Check if safeStorage is available and ready.
 *
 * safeStorage may not be available on Linux without libsecret,
 * or before the app is ready.
 */
function isSafeStorageAvailable(): boolean {
  try {
    // Dynamic import to avoid errors in test environments
    const { safeStorage } = require("electron");
    return safeStorage.isEncryptionAvailable();
  } catch {
    return false;
  }
}

/**
 * Store an API key securely.
 *
 * Encrypts the key using safeStorage if available, otherwise
 * stores as base64-encoded plaintext (with console warning).
 */
export function storeKey(service: string, key: string): void {
  keyCache.set(service, key);

  const storePath = getKeyStorePath();
  const store = loadStore(storePath);

  if (isSafeStorageAvailable()) {
    const { safeStorage } = require("electron");
    const encrypted = safeStorage.encryptString(key);
    store[service] = {
      data: encrypted.toString("base64"),
      encrypted: true,
    };
  } else {
    console.warn(
      `[keychain] safeStorage not available. Storing key for '${service}' ` +
        "in plaintext. Install libsecret for encrypted storage on Linux."
    );
    store[service] = {
      data: Buffer.from(key).toString("base64"),
      encrypted: false,
    };
  }

  fs.writeFileSync(storePath, JSON.stringify(store, null, 2));
}

/**
 * Retrieve an API key.
 *
 * Returns null if the key doesn't exist.
 */
export function getKey(service: string): string | null {
  // Check cache first
  const cached = keyCache.get(service);
  if (cached !== undefined) return cached;

  const storePath = getKeyStorePath();
  const store = loadStore(storePath);
  const entry = store[service];
  if (!entry) return null;

  let key: string;
  if (entry.encrypted && isSafeStorageAvailable()) {
    const { safeStorage } = require("electron");
    const buffer = Buffer.from(entry.data, "base64");
    key = safeStorage.decryptString(buffer);
  } else {
    key = Buffer.from(entry.data, "base64").toString("utf-8");
  }

  keyCache.set(service, key);
  return key;
}

/** Delete an API key. */
export function deleteKey(service: string): void {
  keyCache.delete(service);

  const storePath = getKeyStorePath();
  const store = loadStore(storePath);
  delete store[service];
  fs.writeFileSync(storePath, JSON.stringify(store, null, 2));
}

/** Check if a key exists. */
export function hasKey(service: string): boolean {
  if (keyCache.has(service)) return true;

  const storePath = getKeyStorePath();
  const store = loadStore(storePath);
  return service in store;
}

interface KeyEntry {
  data: string;
  encrypted: boolean;
}

function loadStore(storePath: string): Record<string, KeyEntry> {
  if (!fs.existsSync(storePath)) return {};
  try {
    const content = fs.readFileSync(storePath, "utf-8");
    return JSON.parse(content) as Record<string, KeyEntry>;
  } catch {
    return {};
  }
}
