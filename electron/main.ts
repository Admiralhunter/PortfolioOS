/**
 * Electron main process entry point.
 *
 * Manages application lifecycle, creates the main window, initializes
 * databases, starts the Python sidecar, and registers IPC handlers.
 *
 * Security: contextIsolation enabled, nodeIntegration disabled.
 */

import { app, BrowserWindow } from "electron";
import * as path from "node:path";
import * as fs from "node:fs";
import { registerAllHandlers } from "./ipc/index";
import { initSQLite, closeSQLite } from "./db/sqlite";
import { SidecarManager } from "./services/sidecar";

// App data directory: ~/.portfolioos/
const APP_DIR = path.join(app.getPath("home"), ".portfolioos");
const DATA_DIR = path.join(APP_DIR, "data");
const CONFIG_DIR = path.join(APP_DIR, "config");
const LOGS_DIR = path.join(APP_DIR, "logs");

let mainWindow: BrowserWindow | null = null;
let sidecar: SidecarManager | null = null;

function ensureDirectories(): void {
  for (const dir of [APP_DIR, DATA_DIR, CONFIG_DIR, LOGS_DIR]) {
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
  }
}

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });

  // In development, load from Vite dev server
  if (MAIN_WINDOW_VITE_DEV_SERVER_URL) {
    mainWindow.loadURL(MAIN_WINDOW_VITE_DEV_SERVER_URL);
  } else {
    mainWindow.loadFile(
      path.join(__dirname, `../renderer/${MAIN_WINDOW_VITE_NAME}/index.html`)
    );
  }

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

app.whenReady().then(() => {
  ensureDirectories();

  // Initialize SQLite for app state
  const sqlitePath = path.join(CONFIG_DIR, "config.sqlite");
  initSQLite(sqlitePath);

  // Start Python sidecar
  sidecar = new SidecarManager();
  sidecar.start();

  // Register IPC handlers
  registerAllHandlers(sidecar, {
    dataDir: DATA_DIR,
    configDir: CONFIG_DIR,
    logsDir: LOGS_DIR,
  });

  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("will-quit", () => {
  sidecar?.stop();
  closeSQLite();
});

// Vite dev server URL declarations (injected by Electron Forge)
declare const MAIN_WINDOW_VITE_DEV_SERVER_URL: string | undefined;
declare const MAIN_WINDOW_VITE_NAME: string;

export { APP_DIR, DATA_DIR, CONFIG_DIR, LOGS_DIR };
