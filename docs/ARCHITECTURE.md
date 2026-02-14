# PortfolioOS — Architecture Design

> **Version**: 0.1.0-draft
> **Date**: 2026-02-14
> **Status**: DRAFT

---

## 1. System Overview

PortfolioOS is a desktop application built on Electron with a React frontend, a Node.js backend (Electron main process), a Python sidecar for analytics, and a dual-database storage layer (DuckDB + SQLite).

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    Electron Shell                        │
│                                                         │
│  ┌──────────────────────┐  ┌─────────────────────────┐  │
│  │   Renderer Process   │  │     Main Process         │  │
│  │                      │  │     (Node.js)            │  │
│  │  ┌────────────────┐  │  │  ┌───────────────────┐  │  │
│  │  │  React 19 +    │  │  │  │  IPC Handlers     │  │  │
│  │  │  TypeScript     │◄─┼──┼─►│                   │  │  │
│  │  │                │  │  │  │  ┌─────────────┐  │  │  │
│  │  │  ┌──────────┐  │  │  │  │  │ DB Layer    │  │  │  │
│  │  │  │ Zustand  │  │  │  │  │  │ DuckDB +    │  │  │  │
│  │  │  │ TanStack │  │  │  │  │  │ SQLite      │  │  │  │
│  │  │  └──────────┘  │  │  │  │  └─────────────┘  │  │  │
│  │  │                │  │  │  │                   │  │  │
│  │  │  ┌──────────┐  │  │  │  │  ┌─────────────┐  │  │  │
│  │  │  │ Recharts │  │  │  │  │  │ LLM Provider│  │  │  │
│  │  │  │ LW Charts│  │  │  │  │  │ Abstraction │  │  │  │
│  │  │  │ D3.js    │  │  │  │  │  └─────────────┘  │  │  │
│  │  │  └──────────┘  │  │  │  │                   │  │  │
│  │  └────────────────┘  │  │  └───────┬───────────┘  │  │
│  └──────────────────────┘  │          │              │  │
│                            │          │ stdin/stdout │  │
│                            │  ┌───────▼───────────┐  │  │
│                            │  │  Python Sidecar   │  │  │
│                            │  │  NumPy, Pandas,   │  │  │
│                            │  │  SciPy            │  │  │
│                            │  └───────────────────┘  │  │
│                            └─────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                            │
                    ┌───────▼───────┐
                    │ External APIs │
                    │ Yahoo Finance │
                    │ FRED          │
                    │ Alpha Vantage │
                    │ LM Studio     │
                    └───────────────┘
```

### Data Flow

```
User Action
  → React Component (event handler)
    → IPC invoke via contextBridge
      → Electron Main Process handler
        ├→ DuckDB query (analytics, time-series)
        ├→ SQLite query (app state, preferences)
        ├→ Python sidecar (simulations, statistical analysis)
        ├→ LLM provider (natural language features)
        └→ External API (market data fetch)
      → IPC response
    → TanStack Query cache update
  → React re-render
```

---

## 2. Technology Choices

### 2.1 Application Shell: Electron

**Choice**: Electron

**Rationale**:
- Mature ecosystem with extensive documentation, tooling, and community support
- Node.js main process provides direct access to filesystem, databases, and system APIs
- Proven track record for desktop financial applications (VS Code, Slack, Discord demonstrate stability at scale)
- Electron Forge provides modern build tooling, auto-updates, and platform-specific packaging
- Large pool of existing packages for Node.js reduces development effort
- Cross-platform: macOS, Windows, Linux from a single codebase

**Trade-offs acknowledged**:
- Larger bundle size (~100-150 MB) compared to native alternatives
- Higher baseline memory usage (~200 MB idle)
- Chromium update cadence requires attention for security patches

**Mitigations**:
- Use Electron Forge with webpack/Vite for tree-shaking and bundle optimization
- Lazy-load heavy renderer modules
- Monitor memory usage in development; profile and optimize as needed

### 2.2 Frontend: React + TypeScript + Vite

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| UI Framework | React 19 | Component model, ecosystem, TypeScript support |
| Language | TypeScript (strict) | Type safety for financial calculations |
| Build Tool | Vite | Fast HMR, modern ESM defaults, Electron integration via plugins |
| Routing | TanStack Router | Type-safe, file-based routing |
| Async State | TanStack Query | Caching, background refetch for market data |
| Client State | Zustand | Lightweight, minimal boilerplate, devtools support |
| Styling | Tailwind CSS 4 | Utility-first, fast prototyping, design consistency |
| UI Components | shadcn/ui | Copy-paste components on Radix primitives, full ownership, Tailwind-native |

### 2.3 Visualization Stack

A layered approach based on chart complexity:

| Library | Use Case | Rationale |
|---------|----------|-----------|
| Recharts | Dashboard charts (line, area, bar, pie) | Native React integration, fast development, good defaults |
| Lightweight Charts | Financial charts (candlestick, OHLCV) | TradingView's open-source library, 40KB, canvas-rendered, purpose-built for financial time-series |
| D3.js | Custom visualizations (Sankey, heatmaps, correlation matrices) | Full control for complex, non-standard charts; used sparingly |

### 2.4 Backend: Electron Main Process (Node.js)

The Electron main process handles:
- **IPC handler registration** — exposes backend operations to the renderer via contextBridge
- **Database access** — DuckDB and SQLite connections, query execution, migrations
- **File system operations** — CSV/XLSX/JSON import, data export, log management
- **API orchestration** — market data fetching, rate limiting, response caching
- **Python sidecar management** — spawning, health checking, stdin/stdout communication
- **LLM provider routing** — forwarding requests to configured LLM endpoint
- **Application lifecycle** — window management, auto-updates, system tray

### 2.5 Analytics Engine: Python Sidecar

**Why Python instead of pure Node.js**:
- NumPy's vectorized operations handle 10,000-trial Monte Carlo simulations in under 2 seconds — matching this in JavaScript would require WebAssembly or native addons
- Pandas provides battle-tested time-series manipulation (resampling, rolling windows, gap filling)
- SciPy offers statistical distributions, hypothesis testing, and optimization out of the box
- The financial Python ecosystem (quantlib, yfinance, fredapi) is unmatched

**Communication protocol**:
- Electron spawns the Python process as a child process
- Communication via stdin/stdout with newline-delimited JSON messages
- Each message has: `{ "id": "uuid", "method": "string", "params": {} }`
- Responses: `{ "id": "uuid", "result": {} }` or `{ "id": "uuid", "error": { "message": "string" } }`
- Python process is long-lived (not spawned per request)

**Packaging**:
- Python sidecar bundled via PyInstaller or PyOxidizer for distribution
- During development, runs directly via `uv run`

### 2.6 Database: DuckDB + SQLite

**Dual-database architecture**:

| Database | Role | Access Pattern | Rationale |
|----------|------|---------------|-----------|
| DuckDB | Financial data, time-series, analytics | Read-heavy, analytical (OLAP) | Columnar storage is 10-100x faster for aggregations over price history and portfolio snapshots. Vectorized execution. Native Parquet support. Excellent windowing functions. |
| SQLite | App state, preferences, account metadata | Read-write, transactional (OLTP) | Row-based storage ideal for frequent small writes. Mature, battle-tested, universal. |

Both are single-file, zero-server, embeddable databases — perfect for local-first architecture.

**Why not just one?**
- SQLite struggles with analytical queries over large time-series datasets (scanning millions of rows for aggregations)
- DuckDB is not optimized for frequent small transactional writes (updating a preference, toggling a setting)
- Using both plays to each engine's strengths

### 2.7 LLM Integration Layer

**Architecture**: Provider abstraction with unified interface.

```
┌─────────────────────────────────────┐
│       LLM Provider Interface        │
│  send(prompt, options) → response   │
│  stream(prompt, options) → stream   │
│  listModels() → model[]             │
└──────────┬──────────────────────────┘
           │
     ┌─────┴─────┬──────────┬───────────┐
     ▼           ▼          ▼           ▼
┌─────────┐ ┌────────┐ ┌─────────┐ ┌──────────┐
│LM Studio│ │ OpenAI │ │Anthropic│ │OpenRouter│
│ (local) │ │ compat │ │ compat  │ │          │
│ DEFAULT │ │        │ │         │ │          │
└─────────┘ └────────┘ └─────────┘ └──────────┘
```

**Default**: LM Studio at `http://localhost:1234/v1` (OpenAI-compatible format)

**Configuration** (stored in SQLite):
- Provider name
- Endpoint URL
- Model identifier
- API key reference (actual key in OS keychain)
- Max tokens, temperature defaults

**Privacy controls**:
- Local providers (LM Studio): full access to all data, no consent prompts
- Cloud providers: require explicit user consent before sending any portfolio data
- Per-provider data access settings configurable by user

---

## 3. Data Architecture

### 3.1 SQLite Schema (App State)

```sql
-- User accounts and asset containers
CREATE TABLE accounts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,  -- '401k', 'ira', 'roth_ira', 'taxable', 'crypto', 'real_asset', 'cash'
    institution TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- User preferences
CREATE TABLE preferences (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- LLM provider configuration
CREATE TABLE llm_providers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    provider_type TEXT NOT NULL,  -- 'lmstudio', 'openai', 'anthropic', 'openrouter'
    endpoint_url TEXT NOT NULL,
    model TEXT,
    is_default INTEGER NOT NULL DEFAULT 0,
    is_local INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

-- Data source configuration
CREATE TABLE data_sources (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    source_type TEXT NOT NULL,  -- 'yahoo_finance', 'fred', 'alpha_vantage', 'csv_import'
    api_key_ref TEXT,           -- Reference to OS keychain entry
    rate_limit_per_min INTEGER,
    enabled INTEGER NOT NULL DEFAULT 1
);
```

### 3.2 DuckDB Schema (Portfolio Data)

```sql
-- Individual holdings
CREATE TABLE holdings (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    asset_type TEXT NOT NULL,  -- 'stock', 'etf', 'bond', 'crypto', 'real_asset', 'cash', 'custom'
    name TEXT,
    currency TEXT DEFAULT 'USD'
);

-- Transaction history
CREATE TABLE transactions (
    id TEXT PRIMARY KEY,
    holding_id TEXT NOT NULL,
    type TEXT NOT NULL,        -- 'buy', 'sell', 'dividend', 'split', 'transfer_in', 'transfer_out'
    date DATE NOT NULL,
    quantity DOUBLE,
    price DOUBLE,
    total_amount DOUBLE NOT NULL,
    fees DOUBLE DEFAULT 0,
    notes TEXT
);

-- Daily price history
CREATE TABLE price_history (
    symbol TEXT NOT NULL,
    date DATE NOT NULL,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE NOT NULL,
    adj_close DOUBLE,
    volume BIGINT,
    source TEXT NOT NULL,
    PRIMARY KEY (symbol, date)
);

-- Portfolio snapshots (materialized daily)
CREATE TABLE portfolio_snapshots (
    date DATE NOT NULL,
    account_id TEXT,          -- NULL = total portfolio
    total_value DOUBLE NOT NULL,
    cost_basis DOUBLE,
    unrealized_gain DOUBLE,
    PRIMARY KEY (date, account_id)
);

-- Macro economic indicators
CREATE TABLE macro_indicators (
    series_id TEXT NOT NULL,   -- e.g., 'FEDFUNDS', 'CPIAUCSL', 'UNRATE'
    date DATE NOT NULL,
    value DOUBLE NOT NULL,
    source TEXT NOT NULL,
    PRIMARY KEY (series_id, date)
);

-- Monte Carlo simulation results
CREATE TABLE simulation_results (
    simulation_id TEXT NOT NULL,
    trial_num INTEGER NOT NULL,
    year INTEGER NOT NULL,
    portfolio_value DOUBLE NOT NULL,
    withdrawal DOUBLE,
    PRIMARY KEY (simulation_id, trial_num, year)
);
```

### 3.3 Local Storage Layout

```
~/.portfolioos/
  config.sqlite              # App preferences, account metadata, LLM provider config
  data/
    portfolio.duckdb         # Holdings, transactions, cost basis
    market.duckdb            # Price history, fundamentals, macro indicators
    simulations.duckdb       # Monte Carlo results, projection cache
  exports/                   # User-exported CSVs, reports
  logs/                      # Application logs (rotated, max 50MB)
  cache/                     # API response cache (TTL-based, auto-cleaned)
```

---

## 4. Market Data Pipeline

### 4.1 Data Sources

| Source | Data | API Key Required | Rate Limit | Priority |
|--------|------|-----------------|------------|----------|
| Yahoo Finance (yfinance) | Daily OHLCV, fundamentals, dividends, splits | No | Unofficial, be respectful | Primary for equities |
| FRED | Macro indicators, interest rates, inflation, unemployment | Yes (free) | 120 req/min | Primary for macro |
| Alpha Vantage | Intraday data, technical indicators, forex | Yes (free tier) | 25 req/day (free) | Secondary |

### 4.2 Pipeline Architecture

```
Scheduler (Electron main process, configurable intervals)
  → Fetcher (Python sidecar, per-source adapters)
    → Validator (gap detection, outlier detection, corporate action adjustment)
      → Loader (upsert into DuckDB with conflict resolution)
        → Cache (HTTP response cache with TTL to minimize API calls)
```

**Key design decisions**:
- Fetching is always user-initiated or explicitly scheduled (no background polling without consent)
- Each data source has an independent adapter with its own rate limiter and retry logic
- Failed fetches never corrupt existing data (write-ahead pattern)
- Data quality checks run on every ingest: detect gaps, flag outliers, adjust for splits/dividends

---

## 5. Simulation Engine

### 5.1 Monte Carlo Implementation

**Runtime**: Python sidecar (NumPy-based vectorized computation)

**Approach**:
1. Generate all 10,000 trial paths simultaneously using NumPy array operations
2. Each trial: random sequence of annual returns drawn from configured distribution
3. Apply withdrawal strategy, inflation adjustment, and tax rules at each time step
4. Collect terminal portfolio values and per-year distributions

**Configurable parameters**:
- Return distribution: historical bootstrap, normal, log-normal, fat-tailed (Student's t)
- Number of trials (default: 10,000)
- Time horizon (default: 50 years)
- Withdrawal strategy: constant dollar, constant percentage, Guyton-Klinger guardrails
- Inflation model: fixed rate, historical distribution, or regime-based
- Tax modeling: Roth vs. Traditional withdrawal ordering, capital gains, RMDs
- Random seed for reproducibility

**Output**:
- Success rate (% of trials where portfolio survives full horizon)
- Percentile paths (5th, 25th, 50th, 75th, 95th)
- Portfolio value distribution at each year
- Safe withdrawal rate at target success probability
- Sequence-of-returns risk metric

**Performance target**: 10,000 trials x 50 years < 2 seconds on modern hardware.

---

## 6. Security Model

| Concern | Approach |
|---------|----------|
| API keys | Encrypted in OS keychain via Electron safeStorage; never written to config files or logs |
| Brokerage credentials | Never stored — by design, not by limitation |
| Data at rest | Local filesystem; future: optional encryption via OS-level disk encryption |
| Data in transit | HTTPS for all API calls; local IPC is process-internal |
| Telemetry | None. Zero analytics, zero tracking, zero phone-home |
| LLM data privacy | Local LLM (LM Studio) by default; cloud LLMs require explicit user consent |
| Renderer isolation | contextIsolation: true, nodeIntegration: false, strict CSP |

---

## 7. Development Roadmap

### Phase 0 — Project Scaffolding

- Electron + React + Vite project setup (Electron Forge)
- DuckDB and SQLite integration in main process
- Python sidecar proof of concept (spawn, communicate, shutdown)
- CI/CD pipeline (GitHub Actions: lint, test, build)
- Linting (ESLint, Ruff), formatting (Prettier, Black), pre-commit hooks
- Basic window with "hello world" React app rendering

### Phase 1 — Data Foundation

- Database schema design and migration system
- CSV / XLSX / JSON import pipeline
- Manual account and holding entry UI
- Basic CRUD operations for accounts, holdings, transactions
- Market data fetcher: Yahoo Finance adapter + FRED adapter
- Price history storage and retrieval
- Historical gap detection (identify missing date ranges)

### Phase 2 — Portfolio Dashboard

- Portfolio overview page (holdings table, current values)
- Asset allocation visualization (pie/donut chart)
- Historical performance chart (line chart with benchmark overlay)
- Net worth tracker (assets, liabilities, net worth over time)
- Basic return calculations (total return, annualized, by holding)
- Gain/loss tracking with cost basis methods

### Phase 3 — FIRE Simulator

- Monte Carlo engine in Python sidecar
- Simulation configuration UI (inputs panel with sliders and fields)
- Results visualization (probability fan chart, success rate gauge)
- Multiple FIRE type presets (Lean, Normal, Fat, Coast, Barista)
- Life events editor (add/remove/modify temporal events)
- Withdrawal strategy comparison tool
- Sensitivity analysis charts

### Phase 4 — Market Intelligence & LLM Integration

- LLM provider abstraction and configuration UI
- LM Studio integration (default local provider)
- Cloud provider support (OpenAI, Anthropic, OpenRouter)
- Macro dashboard (FRED data visualization)
- Equity analysis page (fundamentals, valuation metrics)
- Sector and asset class performance comparison
- Natural language portfolio queries via LLM
- Report generation (daily/weekly summaries)

### Phase 5 — Polish & Release

- Application packaging for macOS, Windows, Linux (Electron Forge)
- Auto-update mechanism
- Onboarding flow / first-run experience
- Data export (CSV, JSON, PDF reports)
- User documentation
- Performance profiling and optimization
- Beta release

---

## 8. Project Structure

```
PortfolioOS/
├── CLAUDE.md
├── README.md
├── LICENSE
├── package.json
├── pnpm-lock.yaml
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.ts
├── forge.config.ts                  # Electron Forge configuration
├── docs/
│   ├── SPEC.md
│   └── ARCHITECTURE.md
├── electron/                        # Electron main process
│   ├── main.ts                      # Entry point
│   ├── preload.ts                   # Preload script (contextBridge)
│   ├── ipc/                         # IPC handler modules
│   │   ├── portfolio.ts
│   │   ├── market.ts
│   │   ├── simulation.ts
│   │   └── llm.ts
│   ├── db/                          # Database access layer
│   │   ├── duckdb.ts
│   │   ├── sqlite.ts
│   │   └── migrations/
│   ├── services/                    # Business logic
│   │   ├── import.ts
│   │   ├── market-data.ts
│   │   └── sidecar.ts
│   └── llm/                         # LLM provider implementations
│       ├── provider.ts              # Interface definition
│       ├── lmstudio.ts
│       ├── openai.ts
│       ├── anthropic.ts
│       └── openrouter.ts
├── src/                             # React frontend (renderer)
│   ├── main.tsx
│   ├── App.tsx
│   ├── components/
│   │   ├── ui/                      # shadcn/ui components
│   │   ├── portfolio/
│   │   ├── fire/
│   │   ├── market/
│   │   └── common/
│   ├── hooks/
│   ├── stores/                      # Zustand stores
│   ├── lib/                         # Utility functions
│   └── types/                       # TypeScript type definitions
├── python/                          # Python sidecar
│   ├── pyproject.toml
│   ├── portfolioos/
│   │   ├── __init__.py
│   │   ├── main.py                  # Sidecar entry point (stdin/stdout loop)
│   │   ├── simulation/
│   │   │   ├── monte_carlo.py
│   │   │   └── withdrawal.py
│   │   ├── market/
│   │   │   ├── yahoo.py
│   │   │   └── fred.py
│   │   └── analysis/
│   │       ├── returns.py
│   │       └── statistics.py
│   └── tests/
├── tests/                           # Integration / E2E tests
└── .github/
    └── workflows/
        ├── ci.yml
        └── release.yml
```
