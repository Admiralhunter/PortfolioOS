/**
 * IPC handler registry — registers all handler modules.
 *
 * Called from the main process on app startup to wire up
 * all IPC channels between the renderer and backend services.
 */

import type { SidecarManager } from "../services/sidecar";
import { DuckDBManager } from "../db/duckdb";
import { LLMManager } from "../llm/manager";
import { registerPortfolioHandlers } from "./portfolio";
import { registerMarketHandlers } from "./market";
import { registerSimulationHandlers } from "./simulation";
import { registerLLMHandlers } from "./llm";
import { registerDataHandlers } from "./data";
import { registerSystemHandlers } from "./system";

interface AppConfig {
  dataDir: string;
  configDir: string;
  logsDir: string;
}

export function registerAllHandlers(
  sidecar: SidecarManager,
  config: AppConfig
): void {
  // Initialize DuckDB for read-only queries
  const duckdb = new DuckDBManager(config.dataDir);
  duckdb.initMarketDB();
  duckdb.initPortfolioDB();

  // Initialize LLM manager
  const llmManager = new LLMManager();

  // Register all handler modules
  registerPortfolioHandlers(sidecar, duckdb);
  registerMarketHandlers(sidecar, duckdb);
  registerSimulationHandlers(sidecar);
  registerLLMHandlers(llmManager);
  registerDataHandlers(sidecar);
  registerSystemHandlers(config);
}
