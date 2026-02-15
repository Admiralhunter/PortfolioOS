# Backend Completion Plan

> **Date**: 2026-02-15
> **Goal**: Make the backend "essentially complete" before any frontend work begins.
> **Scope**: Python sidecar gaps + Electron main process + SQLite + IPC + LLM + services

---

## Current State Summary

### What Exists (Python Sidecar — ~2,100 SLOC, ~100 tests)

| Module | Status | Notes |
|--------|--------|-------|
| `main.py` — JSON-RPC message loop | Done | 18 method handlers, NumPy encoder |
| `simulation/monte_carlo.py` | Done | Vectorized 10K trials, <2s target |
| `simulation/withdrawal.py` | Done | Constant-dollar + Guyton-Klinger |
| `market/yahoo.py` | Done | OHLCV, dividends, splits, fundamentals |
| `market/fred.py` | Done | Single + batch series, graceful degradation |
| `market/validation.py` | Done | Gap detection, outlier flagging, OHLCV integrity |
| `analysis/returns.py` | Done | CAGR, max drawdown |
| `analysis/statistics.py` | Done | Percentile rank, bootstrap returns |
| `ingest/csv_import.py` | Done | Flexible column mapping, multi-brokerage |
| `db/schema.py` | Done | 8 DuckDB tables defined |
| `db/connection.py` | Done | File + in-memory connections, schema init |
| `db/market_store.py` | Done | Upsert + query for price/macro/dividends/splits |
| `db/portfolio_store.py` | Done | Holdings, transactions, snapshots CRUD |

### What Does NOT Exist

| Component | Status |
|-----------|--------|
| Electron main process (`electron/`) | Not started |
| SQLite app-state database | Not started |
| IPC handlers | Not started |
| Python sidecar manager (spawn/lifecycle) | Not started |
| LLM provider abstraction | Not started |
| Cost basis lot tracking (FIFO/LIFO/specific ID/avg cost) | Not started |
| Portfolio reconciliation (compute holdings from transactions) | Not started |
| Net worth calculation engine | Not started |
| Market data scheduling / incremental sync | Not started |
| Data export (CSV, JSON) | Not started |
| API key management (Electron safeStorage) | Not started |

---

## Implementation Plan — 14 Steps

Steps are ordered by dependency. Each step produces a testable, self-contained unit.

---

### Step 1: Python — Cost Basis Engine

**Why first**: The spec requires FIFO, LIFO, specific lot, and average cost methods. The current `portfolio_store.py` only tracks aggregate `cost_basis` on holdings — it cannot compute gains per lot, which is fundamental to the portfolio manager.

**Files to create**:
- `python/portfolioos/portfolio/cost_basis.py`

**What it does**:
- `TaxLot` dataclass: `date`, `quantity`, `price`, `fees`, `remaining_qty`
- `CostBasisTracker` class:
  - `add_buy(date, quantity, price, fees)` — creates a new lot
  - `sell(date, quantity, method="fifo") -> list[DisposedLot]` — disposes lots by method
  - Methods: `fifo`, `lifo`, `average_cost`, `specific_id`
  - `get_unrealized_gains(current_price) -> list[UnrealizedGain]` — per-lot unrealized
  - `get_total_cost_basis() -> float`
  - `get_total_shares() -> float`
- `DisposedLot` dataclass: lot reference, qty sold, proceeds, cost basis, gain/loss, holding period (short/long term based on 1-year threshold)

**Tests**: `python/tests/portfolio/cost_basis_test.py`
- FIFO ordering, LIFO ordering, average cost pooling
- Partial lot sales, multi-lot sales
- Short-term vs long-term classification
- Insufficient shares error

**Sidecar methods to register**:
- `portfolio.cost_basis.sell`
- `portfolio.cost_basis.unrealized`

---

### Step 2: Python — Portfolio Reconciliation

**Why**: Holdings should be computed from transaction history, not manually upserted. The current `upsert_holding` bypasses the transaction ledger entirely.

**Files to create**:
- `python/portfolioos/portfolio/reconciliation.py`

**What it does**:
- `reconcile_holdings(transactions: list[dict]) -> list[dict]`
  - Groups transactions by (account_id, symbol)
  - Applies buys, sells, splits, dividends chronologically
  - Uses `CostBasisTracker` from Step 1 for cost basis
  - Returns computed holdings with shares, cost_basis, realized_gain
- `detect_discrepancies(computed: list[dict], stored: list[dict]) -> list[dict]`
  - Compares reconciled holdings against stored holdings
  - Flags mismatches in shares or cost basis

**Tests**: Reconcile from a sequence of buys/sells, verify share counts and cost basis match expected values.

**Sidecar methods**: `portfolio.reconcile`, `portfolio.detect_discrepancies`

---

### Step 3: Python — Net Worth Engine

**Why**: Net worth tracking is a top-level feature (Spec 5.2). Requires combining holdings with current prices to compute total value, then tracking over time.

**Files to create**:
- `python/portfolioos/portfolio/net_worth.py`

**What it does**:
- `compute_net_worth(holdings: list[dict], prices: dict[str, float]) -> NetWorthSnapshot`
  - Maps each holding's shares * current price → market value
  - Sums to total portfolio value
  - Computes total cost basis, total unrealized gain
  - Breaks down by account, asset type, sector (if available)
- `compute_asset_allocation(holdings: list[dict], prices: dict[str, float]) -> list[dict]`
  - Returns list of `{asset_type, symbol, value, weight_pct}`
  - Sorted by weight descending
- `compute_growth_rates(snapshots: list[dict]) -> dict`
  - Monthly, quarterly, annual growth rates from historical snapshots
  - Velocity of wealth change (acceleration/deceleration)

**Tests**: Various portfolio compositions, edge cases (empty portfolio, single holding, zero-price asset).

**Sidecar methods**: `portfolio.net_worth`, `portfolio.asset_allocation`, `portfolio.growth_rates`

---

### Step 4: Python — Enhanced Simulation

**Why**: The current Monte Carlo only supports constant-dollar withdrawal. The spec requires multiple withdrawal strategies, life events, and sensitivity analysis.

**Files to create**:
- `python/portfolioos/simulation/scenarios.py`

**What it does**:
- `run_scenario(config: ScenarioConfig) -> ScenarioResult`
  - `ScenarioConfig`: initial_portfolio, withdrawal_strategy (enum), life_events list, return_distribution, inflation_model, n_trials, n_years, seed
  - Withdrawal strategies: `constant_dollar`, `constant_percentage`, `guyton_klinger`
  - Life events: `{year, type, amount}` — types: `expense`, `income_change`, `windfall`, `savings_rate_change`
  - Applies life events at specified years during simulation
- `sensitivity_analysis(base_config, vary_param, values) -> list[ScenarioResult]`
  - Runs simulation across a range of one parameter
  - Returns results for each value (e.g., vary withdrawal rate from 3% to 6%)

**Tests**: Life events affect outcomes, sensitivity produces monotonic results for withdrawal rate.

**Sidecar methods**: `simulation.scenario`, `simulation.sensitivity`

---

### Step 5: Python — Data Export

**Why**: Users need to export portfolio data, simulation results, and reports. Backend should handle serialization.

**Files to create**:
- `python/portfolioos/export/csv_export.py`
- `python/portfolioos/export/json_export.py`

**What they do**:
- `export_holdings_csv(holdings, output_path) -> str` — write holdings to CSV, return path
- `export_transactions_csv(transactions, output_path) -> str`
- `export_simulation_csv(result, output_path) -> str` — percentile paths as columns
- `export_portfolio_json(holdings, transactions, snapshots) -> str` — full portfolio dump
- All exports include metadata header (date generated, account, date range)

**Tests**: Round-trip test — export then re-import and verify data matches.

**Sidecar methods**: `export.holdings_csv`, `export.transactions_csv`, `export.simulation_csv`, `export.portfolio_json`

---

### Step 6: Python — Database Operations Layer

**Why**: The sidecar currently registers market data fetchers but not database write/read operations. The Electron process needs to call into the sidecar for db operations that involve computation (reconciliation, snapshots), while simple CRUD can go through Node.js DuckDB bindings.

**Files to modify**:
- `python/portfolioos/main.py` — register new db methods

**New sidecar methods to register**:
- `db.import_transactions` — parse CSV + write to DuckDB + reconcile holdings (orchestrated pipeline)
- `db.get_holdings` — read holdings with optional price enrichment
- `db.get_transactions` — filtered query
- `db.save_snapshot` — compute net worth from holdings + prices, save snapshot
- `db.get_snapshots` — historical snapshot query
- `db.upsert_market_data` — fetch from Yahoo/FRED + validate + store (full pipeline)

This step wires together Steps 1-5 with the existing db layer into cohesive end-to-end operations.

---

### Step 7: Electron — Project Scaffolding

**Why**: The Electron main process is the backbone that connects the frontend to all backend services. Nothing works without it.

**Files to create**:
- `package.json` — Electron, Electron Forge, Vite, TypeScript, better-sqlite3, duckdb (Node.js bindings)
- `tsconfig.json` — strict mode, ES2022 target
- `forge.config.ts` — Electron Forge with Vite plugin
- `vite.main.config.ts` — Vite config for main process
- `vite.preload.config.ts` — Vite config for preload
- `vite.renderer.config.ts` — Vite config for renderer (minimal placeholder)
- `electron/main.ts` — app lifecycle, window creation, IPC registration
- `electron/preload.ts` — contextBridge with typed API surface

**Key decisions**:
- `contextIsolation: true`, `nodeIntegration: false` (security)
- Preload exposes a `window.api` object with typed async methods
- Main process registers IPC handlers from modular handler files
- App creates `~/.portfolioos/` directory structure on first run

**What the preload exposes** (typed interface):
```typescript
interface PortfolioOSAPI {
  // Portfolio
  portfolio: {
    createAccount(params): Promise<Account>
    listAccounts(): Promise<Account[]>
    importCSV(filePath: string, accountId: string): Promise<ImportResult>
    getHoldings(accountId?: string): Promise<Holding[]>
    getTransactions(filters): Promise<Transaction[]>
    getSnapshots(accountId, dateRange?): Promise<Snapshot[]>
  }
  // Market
  market: {
    fetchPriceHistory(symbol, startDate, endDate): Promise<PriceRecord[]>
    fetchMacroSeries(seriesId, startDate, endDate): Promise<MacroRecord[]>
    detectGaps(symbol): Promise<Gap[]>
    getCachedPrices(symbol, dateRange?): Promise<PriceRecord[]>
  }
  // Simulation
  simulation: {
    run(config): Promise<SimulationResult>
    runScenario(config): Promise<ScenarioResult>
    sensitivity(config): Promise<SensitivityResult>
  }
  // LLM
  llm: {
    listProviders(): Promise<LLMProvider[]>
    setDefault(providerId: string): Promise<void>
    send(prompt: string, options?): Promise<LLMResponse>
  }
  // Data
  data: {
    exportCSV(type, filters, outputPath): Promise<string>
    exportJSON(filters, outputPath): Promise<string>
  }
  // System
  system: {
    getAppPaths(): Promise<AppPaths>
    getPreferences(): Promise<Preferences>
    setPreference(key, value): Promise<void>
  }
}
```

---

### Step 8: Electron — SQLite App State Database

**Why**: App preferences, account metadata, LLM provider config, and data source config live in SQLite (not DuckDB). This is the transactional side of the dual-database architecture.

**Files to create**:
- `electron/db/sqlite.ts`
- `electron/db/sqlite-schema.ts`

**What they do**:
- Initialize `~/.portfolioos/config.sqlite` on first run
- Create tables:
  - `accounts` — id, name, type, institution, notes, created_at, updated_at
  - `preferences` — key/value store with updated_at
  - `llm_providers` — id, name, provider_type, endpoint_url, model, is_default, is_local
  - `data_sources` — id, name, source_type, api_key_ref, rate_limit_per_min, enabled
- CRUD functions:
  - `createAccount`, `getAccounts`, `updateAccount`, `deleteAccount`
  - `getPreference`, `setPreference`, `getAllPreferences`
  - `addLLMProvider`, `getLLMProviders`, `setDefaultProvider`, `removeProvider`
  - `addDataSource`, `getDataSources`, `updateDataSource`
- Use `better-sqlite3` (synchronous, fast, no native async overhead for simple ops)
- Parameterized queries only (no string interpolation)

**Tests**: `tests/electron/db/sqlite.test.ts` — CRUD for each table, constraint validation.

---

### Step 9: Electron — Python Sidecar Manager

**Why**: The Electron main process needs to spawn, communicate with, and manage the lifecycle of the Python sidecar process. This is the bridge between Node.js and all Python analytics.

**Files to create**:
- `electron/services/sidecar.ts`

**What it does**:
- `SidecarManager` class:
  - `start()` — spawn `uv run python -m portfolioos.main` as child process
  - `stop()` — send SIGTERM, wait for clean exit, fallback to SIGKILL after timeout
  - `restart()` — stop then start
  - `isRunning() -> boolean`
  - `send(method: string, params: object) -> Promise<any>` — send JSON request, await JSON response
  - Request/response correlation via `id` field (UUID)
  - Timeout handling (configurable, default 30s for simulations)
  - Error handling: parse error responses, throw typed errors
  - Buffered stdout reading (handle partial JSON lines)
  - stderr logging (capture Python tracebacks)
- Auto-start on app launch, auto-stop on app quit
- Crash recovery: detect process exit, auto-restart with backoff
- Queue management: serialize concurrent requests (Python reads stdin sequentially)

**Tests**: Mock child_process.spawn, verify message correlation, timeout behavior, crash recovery.

---

### Step 10: Electron — DuckDB Access Layer

**Why**: Some queries are simple reads that don't need the Python sidecar (e.g., "list all cached price history for AAPL"). Direct DuckDB access from Node.js avoids the sidecar round-trip for these.

**Files to create**:
- `electron/db/duckdb.ts`

**What it does**:
- `DuckDBManager` class:
  - `initMarketDB(path?)` — create/open market.duckdb, run schema DDL
  - `initPortfolioDB(path?)` — create/open portfolio.duckdb, run schema DDL
  - `query(db, sql, params) -> any[]` — parameterized query
  - `execute(db, sql, params) -> void` — parameterized write
- Read-only convenience functions (write operations go through sidecar for consistency):
  - `getPriceHistory(symbol, dateRange?)` — read cached prices
  - `getHoldings(accountId?)` — read current holdings
  - `getTransactions(filters)` — filtered read
  - `getSnapshots(accountId, dateRange?)` — historical snapshots
  - `getMacroIndicators(seriesId, dateRange?)` — FRED data
- Uses Node.js `duckdb` package (official bindings)
- Connection pooling: keep connections open per database file

**Decision**: Writes that involve computation (import + reconcile, fetch + validate + store) go through the Python sidecar. Simple reads go direct. This prevents data consistency issues from two writers.

---

### Step 11: Electron — IPC Handlers

**Why**: IPC handlers are the API surface between the renderer (React) and all backend services. They orchestrate calls to SQLite, DuckDB, and the Python sidecar.

**Files to create**:
- `electron/ipc/portfolio.ts`
- `electron/ipc/market.ts`
- `electron/ipc/simulation.ts`
- `electron/ipc/llm.ts`
- `electron/ipc/data.ts`
- `electron/ipc/system.ts`
- `electron/ipc/index.ts` — registers all handlers

**Handler responsibilities**:

**portfolio.ts**:
- `portfolio:create-account` → SQLite insert
- `portfolio:list-accounts` → SQLite query
- `portfolio:update-account` → SQLite update
- `portfolio:delete-account` → SQLite delete
- `portfolio:import-csv` → sidecar `db.import_transactions`
- `portfolio:get-holdings` → DuckDB read (optionally enriched via sidecar `portfolio.net_worth`)
- `portfolio:get-transactions` → DuckDB read
- `portfolio:get-snapshots` → DuckDB read
- `portfolio:reconcile` → sidecar `portfolio.reconcile`

**market.ts**:
- `market:fetch-prices` → sidecar `db.upsert_market_data` (fetch + validate + store)
- `market:fetch-macro` → sidecar (FRED fetch + store)
- `market:get-cached-prices` → DuckDB read
- `market:detect-gaps` → sidecar `validation.detect_gaps`
- `market:get-symbol-info` → sidecar `market.yahoo.info`

**simulation.ts**:
- `simulation:run` → sidecar `simulation.run`
- `simulation:scenario` → sidecar `simulation.scenario`
- `simulation:sensitivity` → sidecar `simulation.sensitivity`

**llm.ts**:
- `llm:list-providers` → SQLite query
- `llm:add-provider` → SQLite insert + safeStorage for API key
- `llm:set-default` → SQLite update
- `llm:send` → HTTP request to configured provider endpoint
- `llm:delete-provider` → SQLite delete + safeStorage cleanup

**data.ts**:
- `data:export-csv` → sidecar export methods
- `data:export-json` → sidecar export methods

**system.ts**:
- `system:get-paths` → return `~/.portfolioos/` structure
- `system:get-preference` → SQLite read
- `system:set-preference` → SQLite write
- `system:get-version` → read from package.json

**All handlers**:
- Validate input params (type + range checks)
- Return `{ success: true, data: ... }` or `{ success: false, error: "..." }`
- Log errors with context
- Never expose stack traces to renderer

**Tests**: One test file per handler module, mocking sidecar + db calls.

---

### Step 12: Electron — LLM Provider Abstraction

**Why**: LLM integration is a major feature (Spec 5.9). The backend needs a unified interface so the frontend doesn't care which provider is active.

**Files to create**:
- `electron/llm/types.ts` — interfaces
- `electron/llm/provider.ts` — base class / interface
- `electron/llm/lmstudio.ts` — LM Studio (local, default)
- `electron/llm/openai.ts` — OpenAI-compatible
- `electron/llm/anthropic.ts` — Anthropic
- `electron/llm/openrouter.ts` — OpenRouter
- `electron/llm/manager.ts` — provider registry and routing

**Interface**:
```typescript
interface LLMProvider {
  id: string
  name: string
  isLocal: boolean
  send(prompt: string, options?: LLMOptions): Promise<LLMResponse>
  stream(prompt: string, options?: LLMOptions): AsyncGenerator<string>
  listModels(): Promise<string[]>
  testConnection(): Promise<boolean>
}

interface LLMOptions {
  model?: string
  temperature?: number
  maxTokens?: number
  systemPrompt?: string
}

interface LLMResponse {
  content: string
  model: string
  tokensUsed: { prompt: number; completion: number }
}
```

**LM Studio provider**:
- Connects to `http://localhost:1234/v1` (OpenAI-compatible API)
- No API key required
- Full data access (no consent prompts — everything stays local)

**Cloud providers**:
- API keys stored/retrieved via `electron.safeStorage`
- Consent check: before sending any data, verify user has opted in
- Rate limiting: respect provider limits

**Manager**:
- `getProvider(id?) -> LLMProvider` — returns default or specific
- `setDefault(id)` — update SQLite
- `getAll() -> LLMProviderConfig[]` — list configured providers
- `addProvider(config) -> string` — register + store API key securely

**Tests**: Mock HTTP requests, verify each provider formats requests correctly, test consent enforcement for cloud providers.

---

### Step 13: Electron — API Key Security

**Why**: API keys (FRED, cloud LLMs) must be encrypted at rest per spec constraints. Electron's `safeStorage` uses the OS keychain (macOS Keychain, Windows DPAPI, Linux libsecret).

**Files to create**:
- `electron/services/keychain.ts`

**What it does**:
- `storeKey(service: string, key: string) -> void` — encrypt and store via safeStorage
- `getKey(service: string) -> string | null` — decrypt and return
- `deleteKey(service: string) -> void`
- `hasKey(service: string) -> boolean`
- Services: `fred-api-key`, `openai-api-key`, `anthropic-api-key`, `openrouter-api-key`
- Falls back gracefully if safeStorage not available (e.g., Linux without libsecret)
  - Warns user that keys are stored in plaintext
  - Still functional, just less secure

**Tests**: Verify encrypt/decrypt round-trip, missing key returns null, delete removes key.

---

### Step 14: Integration Testing & Wiring

**Why**: Each step above produces isolated units. This step wires them together and verifies end-to-end flows.

**Files to create**:
- `tests/integration/import-flow.test.ts` — CSV → sidecar → DuckDB → read back
- `tests/integration/simulation-flow.test.ts` — config → sidecar → results
- `tests/integration/market-data-flow.test.ts` — fetch → validate → store → read
- Update `Makefile` to include Electron tests in `check-all`
- Update `.github/workflows/ci.yml` to run TypeScript tests

**End-to-end flows tested**:
1. Import CSV → transactions appear in DuckDB → holdings reconciled → snapshot computed
2. Fetch market data → validation → stored in DuckDB → queried back with date range
3. Run simulation with scenario config → results include percentiles and success rate
4. Configure LLM provider → test connection → send prompt → receive response
5. Store API key → retrieve → delete → confirm gone

---

## Dependency Graph

```
Step 1 (Cost Basis)
  └→ Step 2 (Reconciliation) — uses CostBasisTracker
       └→ Step 3 (Net Worth) — uses reconciled holdings
            └→ Step 6 (DB Operations) — orchestrates 1-5 into sidecar methods

Step 4 (Enhanced Simulation) — independent of 1-3
Step 5 (Data Export) — independent of 1-4

Step 7 (Electron Scaffolding) — independent of Python steps
  └→ Step 8 (SQLite) — needs Electron app structure
  └→ Step 9 (Sidecar Manager) — needs Electron app structure
  └→ Step 10 (DuckDB Access) — needs Electron app structure
       └→ Step 11 (IPC Handlers) — needs 8, 9, 10
            └→ Step 12 (LLM Providers) — needs 11 for IPC integration
            └→ Step 13 (Keychain) — needs 11 for IPC integration
                 └→ Step 14 (Integration Tests) — needs everything
```

**Parallelizable**:
- Steps 1-6 (Python) can run in parallel with Steps 7-10 (Electron scaffolding)
- Steps 4, 5 are independent of Steps 1-3
- Step 12 and Step 13 are independent of each other

---

## What "Backend Complete" Means

When all 14 steps are done, the backend can:

- Import portfolio data from CSV files (multi-brokerage)
- Track cost basis per tax lot (FIFO, LIFO, specific ID, average cost)
- Reconcile holdings from transaction history
- Compute net worth with real-time prices
- Detect and flag data gaps and outliers
- Run Monte Carlo simulations with multiple withdrawal strategies and life events
- Run sensitivity analysis across parameter ranges
- Fetch and cache market data (Yahoo Finance, FRED)
- Store/query all data in DuckDB (analytics) and SQLite (app state)
- Manage LLM providers (local LM Studio + cloud opt-in)
- Encrypt API keys via OS keychain
- Export data to CSV and JSON
- Respond to any IPC call from a future React frontend

The frontend becomes purely a presentation layer — every data operation, computation, and external call is already handled by the backend.

---

## Files Not Changed

This plan does **not** modify:
- Existing Python sidecar code (only extends with new modules)
- Agent system (`agents/`)
- CI workflows (only adds TypeScript jobs)
- Documentation (SPEC.md, ARCHITECTURE.md unchanged)

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| DuckDB Node.js bindings compatibility | Could block Step 10 | Test early; fallback to routing all reads through sidecar |
| Electron Forge + Vite config complexity | Could delay Step 7 | Use official Electron Forge Vite template |
| safeStorage unavailable on Linux CI | Blocks Step 13 tests | Mock safeStorage in tests; only test real keychain on local dev |
| Python sidecar startup time | Cold start could be slow | Measure; consider `--preload` flag or keeping process warm |
| Two concurrent DuckDB writers (Node + Python) | Data corruption risk | Enforce: Python sidecar owns all writes; Node.js reads only |
