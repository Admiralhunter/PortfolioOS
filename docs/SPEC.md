# PortfolioOS — Product Specification

> **Version**: 0.1.0-draft
> **Author**: Hunter Palcich
> **Date**: 2026-02-14
> **Status**: DRAFT — NOT FOR IMPLEMENTATION

---

## 1. Executive Summary

PortfolioOS is a local-first, privacy-preserving financial operating system that combines accurate long-term wealth tracking, serious FIRE simulations, and global market intelligence into a single, explainable platform. All data is stored locally, all analysis is transparent and reproducible, and nothing requires account logins or cloud services.

## 2. Problem Statement

Existing personal finance tools force users into unacceptable trade-offs:

- **Cloud-dependent tools** (Mint, YNAB, Empower/Personal Capital) require sharing brokerage credentials with third parties and depend on services that can shut down, change pricing, or be acquired
- **Spreadsheet-based tracking** provides full control but lacks simulation capabilities, automated data ingestion, and intelligent analysis
- **Specialized tools** (cFIREsim, FICalc) handle only FIRE projections without portfolio management or market context
- **All existing tools** show artificial portfolio jumps when accounts aren't synced for extended periods, producing inaccurate growth curves and misleading FIRE projections

No single tool combines portfolio management, FIRE planning, and market intelligence in a local-first, privacy-preserving package.

## 3. Target Users

**Primary audience:**
- FIRE-path individuals who want rigorous financial modeling beyond simple calculators
- Privacy-conscious investors who refuse to share credentials with cloud services
- Data-savvy users comfortable with a desktop application and manual data entry

**Not targeting:**
- Casual budgeters who need automatic bank transaction syncing
- Institutional or professional portfolio managers
- Day traders needing real-time sub-second market data
- Users who prioritize mobile-first experiences

## 4. Core Design Principles

### Privacy & Safety
- No account logins or credential storage
- No cloud dependency for core functionality
- Local-first data persistence
- API keys encrypted at rest via OS keychain

### Accuracy Over Convenience
- Historical correctness matters more than instant sync
- Missing data must be retroactively reconstructed, not ignored
- Time series continuity is non-negotiable

### Insight, Not Just Visualization
- Go beyond charts — explain *why* numbers changed
- Quantify uncertainty and confidence in all derived metrics
- Every projection includes probability distributions, not single-point estimates

### Modular & Extensible
- Pluggable data ingestion sources
- Independent analysis engines
- Future-proof architecture with clear service boundaries

## 5. Feature Modules

### 5.1 Portfolio Manager

**Description**: Central module for recording, importing, and tracking all user assets and liabilities.

**Asset Types Supported:**
- Stocks, ETFs, mutual funds
- Bonds (individual and funds)
- Cash and money market accounts
- Cryptocurrency
- Real assets (real estate, vehicles, commodities)
- Custom/other assets (collectibles, private equity, etc.)

**Capabilities:**
- Manual asset definition and tracking (no third-party logins required)
- Bulk ingestion via CSV, XLSX, and JSON imports
- Transaction-based ingestion (buys, sells, dividends, splits, transfers)
- Support for partial and incomplete histories
- Cost basis tracking (FIFO, LIFO, specific lot, average cost)
- Asset allocation views with rebalancing suggestions

**Historical Gap Reconstruction** (key differentiator):
- Detect missing time ranges in portfolio history
- Retroactively fetch or infer historical prices for those periods
- Reconstruct asset value curves with smooth continuity
- Preserve accuracy while eliminating artificial portfolio jumps

This ensures:
- True growth curves instead of step-function artifacts
- Accurate CAGR, drawdown, and volatility metrics
- Honest FIRE projections based on real historical performance

### 5.2 Net Worth Tracker

**Description**: Longitudinal tracking of total assets, liabilities, and net worth over time.

**Capabilities:**
- Net worth history with time-series visualization
- Asset vs. liability breakdown
- Milestone tracking and alerts (e.g., "Reached $500K net worth")
- Velocity of wealth change (monthly/quarterly/annual growth rates)
- Savings efficiency metrics

### 5.3 FIRE Simulator

**Description**: Comprehensive FIRE modeling engine with Monte Carlo simulations and configurable life events.

**Supported FIRE Types:**
- **Lean FIRE**: Minimal annual expenses, maximizing savings rate
- **Normal FIRE**: Standard 25x annual expenses target
- **Fat FIRE**: Comfortable or luxury-level annual expenses
- **Coast FIRE**: Enough invested that compound growth alone reaches target by retirement age (no further contributions needed)
- **Barista FIRE**: Part-time income covers living expenses gap, investments grow untouched

**Simulation Capabilities:**
- Monte Carlo simulations (default: 10,000 trials, 50-year horizon)
- Deterministic projections with fixed return assumptions
- Variable return regimes (bull/bear/normal market phases)
- Inflation modeling (fixed rate, historical distribution, regime-based)
- Withdrawal strategies: constant dollar (4% rule), constant percentage, Guyton-Klinger guardrails, variable percentage of portfolio

**Life Events Modeling:**
Users can define temporal events applied to simulations:
- Job changes and salary adjustments
- Savings rate changes
- One-time expenses (home purchase, medical, education)
- Windfalls (inheritance, bonus, property sale)
- Retirement year shifts
- Social Security start date and benefit amount

**Insight Outputs:**
- Probability of success by FIRE type
- Time-to-FIRE distributions (median, 25th/75th percentile)
- Sensitivity analysis (what-if across return rates, inflation rates, savings rates)
- Risk of sequence-of-returns failure
- Safe withdrawal rate analysis
- Tax-aware withdrawal sequencing (Roth vs. Traditional vs. taxable)

### 5.4 Comparative & Contextual Analytics

**Description**: User's financial state compared against population-level benchmarks.

**Percentile Analysis:**
- Net worth percentile vs. entire U.S. population
- Net worth percentile vs. age-based cohorts
- Income percentile
- Savings rate percentile
- Asset allocation comparison

**Derived Metrics:**
- Velocity of wealth change (acceleration/deceleration trends)
- Savings efficiency (actual savings / potential savings)
- Risk-adjusted progress (returns relative to portfolio volatility)
- FIRE readiness score (composite metric combining multiple factors)

### 5.5 Market Intelligence

**Description**: Continuous intelligence pipeline that ingests global signals, detects trends, and produces structured reports. This is not a trading system — latency tolerance is minutes to hours.

**Data Sources (non-exhaustive):**

*Financial:*
- Stock prices, ETF data, index values
- Bond yields and yield curves
- Commodity prices
- Currency exchange rates

*Macro/Economic:*
- M1/M2 money supply
- CPI, PPI, inflation expectations
- Unemployment, labor force participation
- GDP, industrial production
- Federal funds rate, Treasury yields

*News & Events:*
- Global financial news
- Corporate filings and earnings
- Government policy announcements and disclosures

*Alternative Signals (future):*
- Energy grid capacity
- Population demographics
- Trade flows
- Transportation and logistics data

**API Philosophy:**
- Prefer free data sources (Yahoo Finance, FRED, Alpha Vantage free tier)
- Simple API keys where needed (no OAuth flows)
- No API keys included in the repository
- Graceful degradation when sources are unavailable

**Processing Pipeline:**
1. Continuous or scheduled ingestion
2. Data normalization and validation
3. Temporal indexing
4. Categorization (by geography, sector, asset class)

**Confidence Scoring:**
Every derived insight includes:
- Source reliability score
- Data freshness score
- Consensus confidence (agreement across sources)
- Explicit uncertainty indicators

### 5.6 Temporal & Categorical Reporting

**Description**: Structured report generation across time horizons and categories.

**Temporal Reports:**
- Daily summaries
- Weekly digests
- Monthly analysis
- Long-term trend reports

**Categorical Breakdown:**
- Global overview
- By continent / country
- By sector / industry
- By company
- By asset class

**Output Format:**
- Markdown (human-readable)
- Indexed for retrieval
- Stored historically for trend comparison

### 5.7 Knowledge Storage & Retrieval

**Description**: Structured storage of generated reports and insights for fast retrieval and relationship tracking.

**Capabilities:**
- Reports indexed into vector store for semantic search
- Relationships stored in graph form (entity connections)
- Fast retrieval for agent queries and user searches
- Supports natural language queries:
  - "What changed this week?"
  - "What trends are emerging in tech?"
  - "Why did my portfolio drop on Tuesday?"

### 5.8 Agent & UI Layer

**Description**: Intelligent agents and a modern desktop interface.

**Agents:**
- Query historical reports and intelligence
- Detect trend acceleration and regime changes
- Synthesize cross-domain insights (e.g., macro trends affecting portfolio)
- Generate natural language summaries and explanations

**UI:**
- Runs locally as a desktop application
- Clean, modern, data-dense interface
- Time-series visualization with interactive drill-down
- Scenario sliders for FIRE simulations (adjust inputs, see results live)
- Drill-down from macro (global trends) to micro (individual holdings)

### 5.9 LLM Integration

**Description**: Pluggable LLM provider system with local-first defaults.

**Default Provider**: LM Studio (local inference)
- No data leaves the user's machine
- Connects to LM Studio's OpenAI-compatible endpoint at `localhost:1234`
- Full access to all portfolio data without privacy concerns

**Supported Cloud Providers (opt-in only):**
- OpenAI-compatible endpoints (OpenAI API, any compatible server)
- Anthropic-compatible endpoints
- OpenRouter (multi-model gateway)

**Provider Architecture:**
- Unified interface — all providers implement the same request/response contract
- Provider configuration: endpoint URL, model name, API key
- API keys stored in OS keychain (never in config files)
- Cloud providers require explicit user consent before any data is sent

**Use Cases:**
- Natural language queries over portfolio data
- Report generation and summarization
- Trend explanation and synthesis
- Agent-driven analysis and insights

## 6. Non-Functional Requirements

| Requirement | Target |
|-------------|--------|
| Monte Carlo performance | 10,000 trials x 50 years < 5 seconds |
| Application startup | < 3 seconds to interactive |
| Data storage | All user data in local files, no cloud writes |
| API key security | Encrypted at rest via OS keychain |
| Data freshness | User-initiated refresh or configurable schedule |
| Platform support | macOS, Windows, Linux |
| Offline capability | Full functionality except market data fetch |
| Reproducibility | Same inputs + seed = same simulation results |

## 7. Data Architecture (High Level)

| Store | Technology | Purpose |
|-------|-----------|---------|
| Relational / app state | SQLite | User preferences, account metadata, provider config, UI state |
| Analytical / time-series | DuckDB | Price history, portfolio snapshots, net worth history, macro indicators, simulation results |
| Intelligence layer | Vector store (TBD) | Report indexing, semantic search, RAG retrieval |
| Graph layer | Graph DB (TBD) | Entity relationships, knowledge graph |

**Local storage layout:**
```
~/.portfolioos/
  config.sqlite          # App preferences, account metadata, LLM provider config
  data/
    portfolio.duckdb     # Holdings, transactions, cost basis
    market.duckdb        # Price history, fundamentals, macro indicators
    simulations.duckdb   # Monte Carlo results, projection cache
  exports/               # User-exported CSVs, reports
  logs/                  # Application logs
  cache/                 # API response cache (TTL-based)
```

## 8. Out of Scope (v1)

- Real-time streaming market data (sub-second latency)
- Automated brokerage connections (Plaid/Yodlee integration)
- Mobile applications (iOS/Android)
- Multi-user or family sharing
- Tax filing integration (TurboTax, etc.)
- Cryptocurrency on-chain analysis
- High-frequency trading signals
- Social features or community sharing

## 9. Success Metrics

- User can import a portfolio and see a net worth dashboard within 10 minutes of first launch
- FIRE simulation produces actionable probability analysis with configurable scenarios
- Application launches and is fully usable offline after initial market data fetch
- Historical gap reconstruction produces smooth, accurate growth curves from incomplete data

## 10. Open Questions

- Should the application support a plugin/extension architecture for community-built data sources?
- What is the minimum viable set of market data APIs for the initial release?
- Should there be optional encrypted local backup or export functionality?
- What vector store and graph database should be used for the intelligence layer?
- Should report generation be purely LLM-driven or hybrid (template + LLM)?
