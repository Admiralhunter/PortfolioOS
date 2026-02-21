# PortfolioOS — Next Steps

> **Date**: 2026-02-21
> **Baseline commit**: `3ffa7ab` (main)
> **Purpose**: Identify what has been built, what's broken, and what to build next.

---

## Current State Summary

### What's Done

**Python sidecar** (~1,115 SLOC, 221 tests passing, 89% coverage):
All 6 Python steps from the backend plan are complete:
- Cost basis engine (FIFO, LIFO, specific lot, average cost)
- Portfolio reconciliation (compute holdings from transactions)
- Net worth engine (compute values, asset allocation, growth rates)
- Enhanced simulation (scenarios, life events, sensitivity analysis)
- Data export (CSV, JSON)
- Database operations layer (DuckDB schema, market store, portfolio store)
- Market data fetchers (Yahoo Finance, FRED)
- Data validation (gap detection, outlier flagging)
- CSV import with flexible column mapping

**Electron main process** (~2,097 SLOC across 19 files):
All 8 Electron steps from the backend plan are scaffolded:
- App lifecycle, window creation (`electron/main.ts`)
- Preload with typed API surface (`electron/preload.ts`)
- SQLite app state database with schema (`electron/db/sqlite.ts`)
- DuckDB access layer (`electron/db/duckdb.ts`)
- Python sidecar manager with crash recovery (`electron/services/sidecar.ts`)
- IPC handlers for all 6 domains (portfolio, market, simulation, LLM, data, system)
- LLM provider abstraction with 4 providers (LM Studio, OpenAI, Anthropic, OpenRouter)
- API key security via keychain (`electron/services/keychain.ts`)
- Types definition (`electron/types.ts`)

**Infrastructure**:
- CI/CD pipeline (GitHub Actions)
- Pre-commit hooks (ruff, trailing whitespace, YAML validation)
- Quality gates (file size <= 700 lines, function length <= 100 lines)
- Dead code detection (vulture for Python, knip for TS)
- Docker support for containerized execution
- PR template and agent PR guide
- Multi-agent system (project manager, worker, todo scanner, overlord)

**Documentation**:
- Product specification (SPEC.md)
- Architecture design (ARCHITECTURE.md)
- Backend completion plan (BACKEND_PLAN.md) — all 14 steps done

### What's Broken Right Now

1. **TypeScript build fails** — `pnpm run build` produces ~80+ type errors:
   - Missing `@types/node` — `Buffer`, `process`, `setTimeout`, `console`, `__dirname` all unresolved
   - Missing module declarations for `electron`, `duckdb`, `better-sqlite3`, `uuid`
   - Missing implicit `any` type annotations on IPC handler parameters
   - `node_modules` not installed (`pnpm install` not run)

2. **Agent system lint fails** — `make check-agents` fails with 2 ruff errors:
   - `agents/llm/provider.py:288` — combinable `if` branches (SIM114)
   - `agents/vulture_whitelist.py:8` — unused `noqa` directive (RUF100)

3. **No frontend code exists** — `src/` contains only `index.html` (no React app, no components, no stores)

4. **No integration tests** — Step 14 of the backend plan (integration testing & wiring) has no actual test files beyond 2 unit tests in `tests/electron/`

5. **`tsconfig.json` misconfigured** — missing `@types/node`, no `dom` lib for console/Buffer, and `lib: ["ES2022"]` doesn't include DOM types needed by Electron code

---

## Prioritized Next Steps

### Priority 0: Fix What's Broken (prerequisite for all other work)

#### 0.1 Fix TypeScript build errors
- Run `pnpm install` to install node_modules
- Add `@types/node` to devDependencies
- Fix `tsconfig.json`: add `"types": ["node"]` or adjust `lib`
- Add explicit type annotations to all IPC handler parameters (eliminate `any`)
- Verify `pnpm run build` passes cleanly

#### 0.2 Fix agent system lint
- Fix `agents/llm/provider.py:288` — combine the two `if` branches
- Fix `agents/vulture_whitelist.py:8` — remove unused `noqa: F401`
- Verify `make check-agents` passes

#### 0.3 Verify `make check-all` passes end-to-end
- After 0.1 and 0.2, all three check targets should pass
- This establishes a green baseline for all future work

---

### Priority 1: Frontend Foundation (Phase 2 of the roadmap)

The backend is essentially complete. The next major milestone is building the React frontend. This maps to **Phase 1** and **Phase 2** of the architecture roadmap.

#### 1.1 Install frontend dependencies
- React 19, React DOM
- TanStack Router, TanStack Query
- Zustand
- Tailwind CSS 4
- shadcn/ui (via the init command)
- Recharts
- lightweight-charts (TradingView)

#### 1.2 Create React app entry point
- `src/main.tsx` — React root with providers (QueryClient, Router)
- `src/App.tsx` — Root layout with sidebar navigation
- Configure Vite renderer for React (JSX transform, HMR)
- Verify the Electron app boots and renders the React shell

#### 1.3 Define TypeScript types for the renderer
- `src/types/api.ts` — mirror the `window.api` types from preload
- `src/types/portfolio.ts` — Account, Holding, Transaction, Snapshot
- `src/types/simulation.ts` — SimulationConfig, SimulationResult
- `src/types/market.ts` — PriceRecord, MacroRecord

#### 1.4 Set up Zustand stores
- `src/stores/portfolio.ts` — selected account, holdings cache
- `src/stores/ui.ts` — sidebar state, active view, theme
- `src/stores/simulation.ts` — current simulation config

#### 1.5 Set up TanStack Query hooks
- `src/hooks/useAccounts.ts` — CRUD for accounts via IPC
- `src/hooks/useHoldings.ts` — fetch holdings for selected account
- `src/hooks/useTransactions.ts` — paginated transaction list
- `src/hooks/useMarketData.ts` — price history queries
- `src/hooks/useSimulation.ts` — run simulation, cache results

---

### Priority 2: Core UI Pages (Phase 2 continued)

#### 2.1 App shell and navigation
- Sidebar with sections: Portfolio, FIRE Simulator, Market, Settings
- Header bar with app title and global actions
- Dark/light theme support via Tailwind

#### 2.2 Portfolio dashboard
- Accounts list (create, edit, delete)
- Holdings table for selected account (symbol, shares, current value, gain/loss)
- Asset allocation pie chart (Recharts)
- Net worth summary card

#### 2.3 CSV import flow
- File picker dialog (via Electron dialog API)
- Column mapping preview
- Import progress and results

#### 2.4 Net worth tracker
- Historical net worth line chart
- Growth rate metrics (monthly, quarterly, annual)
- Milestone markers

---

### Priority 3: FIRE Simulator UI (Phase 3)

#### 3.1 Simulation configuration panel
- Input fields: initial portfolio, annual expenses, savings rate, retirement age
- Withdrawal strategy selector (constant dollar, constant percentage, Guyton-Klinger)
- FIRE type presets (Lean, Normal, Fat, Coast, Barista)
- Life events editor (add temporal events with year, type, amount)

#### 3.2 Results visualization
- Probability fan chart (5th/25th/50th/75th/95th percentile paths)
- Success rate gauge
- Time-to-FIRE distribution

#### 3.3 Sensitivity analysis
- Parameter slider (vary one input)
- Multi-line chart showing outcomes across parameter range

---

### Priority 4: Market Intelligence & LLM UI (Phase 4)

#### 4.1 LLM provider settings page
- List configured providers
- Add/remove providers (endpoint, model, API key)
- Test connection button
- Set default provider

#### 4.2 Market data dashboard
- Price chart for individual symbols (lightweight-charts candlestick)
- Macro indicators dashboard (FRED data — fed funds rate, CPI, unemployment)
- Data gap detection and fetch controls

#### 4.3 Natural language query interface
- Chat-style interface for portfolio queries via LLM
- Context-aware prompts with portfolio data

---

### Priority 5: Integration Tests & Polish (Phase 5)

#### 5.1 Integration tests
- End-to-end: CSV import -> DuckDB -> holdings read-back
- End-to-end: simulation config -> sidecar -> results
- End-to-end: market data fetch -> validate -> store -> query
- LLM provider connection test flow

#### 5.2 Application packaging
- Electron Forge makers for macOS, Windows, Linux
- Python sidecar bundling (PyInstaller/PyOxidizer)
- Auto-update mechanism

#### 5.3 First-run experience
- Onboarding wizard (create first account, import data, set LLM provider)
- Sample data for demo/exploration

---

## Dependency Graph

```
Priority 0 (Fix broken build)
  └─> Priority 1 (Frontend foundation)
        └─> Priority 2 (Core UI pages)
              ├─> Priority 3 (FIRE simulator UI)
              └─> Priority 4 (Market & LLM UI)
                    └─> Priority 5 (Integration tests & packaging)
```

Priorities 3 and 4 are independent of each other and can be parallelized.

---

## Recommended Immediate Action

**Start with Priority 0** — fix the TypeScript build and agent lint errors. Without a green `make check-all`, no PR can be merged and no progress can be validated. This is a prerequisite for everything else.

Once the build is green, **move to Priority 1** — standing up the React frontend shell. The backend APIs are ready and waiting; the project needs its UI layer to become a usable application.
