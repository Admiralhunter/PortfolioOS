# CLAUDE.md — AI Assistant Context for PortfolioOS

## Project Overview

PortfolioOS is a local-first, privacy-preserving desktop application for personal finance management, FIRE (Financial Independence, Retire Early) analysis, and market intelligence. All user data stays on the user's machine. No account logins, no credential storage, no cloud dependency for core functionality.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| App Shell | Electron |
| Frontend | React 19 + TypeScript + Vite |
| Styling | Tailwind CSS 4 + shadcn/ui |
| Charts | Recharts (dashboards) + Lightweight Charts (financial) + D3.js (custom) |
| Client State | Zustand |
| Async State | TanStack Query |
| Routing | TanStack Router |
| Backend | Electron main process (Node.js) |
| Analytics Engine | Python sidecar (NumPy, Pandas, SciPy) |
| Primary DB | DuckDB (analytics, time-series, portfolio data) |
| App State DB | SQLite (preferences, account metadata, UI state) |
| LLM (default) | LM Studio (local inference) |
| LLM (cloud) | OpenAI, Anthropic, OpenRouter (opt-in) |
| JS Package Manager | pnpm |
| Python Package Manager | uv |

## Project Structure (Planned)

```
PortfolioOS/
  CLAUDE.md                     # This file
  README.md
  LICENSE                       # PolyForm Noncommercial 1.0.0
  docs/
    SPEC.md                     # Product specification
    ARCHITECTURE.md             # Architecture and tech stack
  electron/                     # Electron main process
    main.ts                     # Entry point
    preload.ts                  # Preload script (context bridge)
    ipc/                        # IPC handler modules
    db/                         # Database access layer
    services/                   # Business logic services
    llm/                        # LLM provider abstraction
  src/                          # React frontend (renderer)
    main.tsx
    App.tsx
    components/
      ui/                       # shadcn/ui components
      portfolio/                # Portfolio feature components
      fire/                     # FIRE simulator components
      market/                   # Market intelligence components
      common/                   # Shared components
    hooks/                      # Custom React hooks
    stores/                     # Zustand stores
    lib/                        # Utility functions
    types/                      # TypeScript type definitions
  python/                       # Python sidecar
    portfolioos/
      __init__.py
      simulation/               # Monte Carlo engine
      market/                   # Market data fetchers
      analysis/                 # Statistical analysis
    pyproject.toml
    tests/
  tests/                        # Integration tests
  .github/
    workflows/                  # CI/CD
```

## Key Architectural Decisions

1. **Dual database (DuckDB + SQLite)**: DuckDB handles analytical queries over time-series and portfolio data (columnar storage, vectorized execution). SQLite handles transactional app state (preferences, account metadata). Do not merge these — they serve fundamentally different access patterns.

2. **Python sidecar for analytics**: Monte Carlo simulations and statistical analysis run in a Python process, not in Node.js. NumPy's vectorized operations for 10,000-trial simulations are difficult to match in JavaScript. The Python sidecar communicates with Electron via stdin/stdout JSON messages.

3. **No cloud dependency**: Core features must work fully offline. Market data fetching is the only network operation and must degrade gracefully when unavailable.

4. **Electron IPC for all backend operations**: The React renderer never accesses databases or the filesystem directly. All operations go through Electron's IPC (invoke pattern via contextBridge).

5. **LM Studio as default LLM provider**: Local inference preserves the privacy-first principle — no portfolio data leaves the machine. Cloud providers (OpenAI, Anthropic, OpenRouter) are available but opt-in only. All providers implement a unified interface.

## Pull Request Process

AI agents **must** follow the PR template and tag system defined in [`.github/pull_request_template.md`](.github/pull_request_template.md). Full tag definitions and enforcement rules are in [`.github/AGENT_PR_GUIDE.md`](.github/AGENT_PR_GUIDE.md).

**Hard limits enforced on every PR:**
- **File size**: 700 lines max per source file
- **Function length**: 100 lines max per function
- **Tags**: Every PR must declare a change type, scope(s), and risk level
- **Self-review**: Agents must verify DRY compliance, documentation, security, and testing before opening a PR

## Coding Conventions

- **TypeScript**: strict mode enabled, no `any` types, prefer `interface` over `type` for object shapes
- **React**: functional components only, custom hooks for shared logic, no class components
- **Python**: type hints on all public functions, Black formatting, Ruff linting
- **Testing**: colocate test files (`*.test.ts`, `*_test.py`)
- **Commits**: conventional commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`)
- **Naming**: camelCase for JS/TS variables and functions, PascalCase for components and types, snake_case for Python

## Critical Constraints

- **NEVER** add telemetry, analytics, tracking pixels, or any form of data exfiltration
- **NEVER** store user credentials for brokerage accounts or financial institutions
- **NEVER** send portfolio data to cloud LLM providers without explicit, per-request user consent
- API keys must be encrypted at rest using the OS keychain (Electron safeStorage)
- All financial calculations must include citations to methodology (e.g., "Bengen 1994" for 4% rule, "Trinity Study 1998" for success rates)
- Monte Carlo simulations must be reproducible given a seed
- Missing data must be handled explicitly — never silently fill gaps with zeros or interpolation without flagging it
- Cloud LLM providers are opt-in only; LM Studio (local) is always the default

## GitHub API Operations

> **`gh` CLI is NOT available.** This project is primarily developed using Claude Code on the web, where the GitHub CLI (`gh`) is not installed and cannot be used. All GitHub API interactions — creating PRs, commenting on issues, checking workflow status, etc. — **must** use `curl` with the GitHub REST API.

**Authentication:** Use the `GITHUB_TOKEN` environment variable (automatically available in CI and Claude Code web sessions).

**Common operations:**

```bash
# Create a pull request
curl -s -X POST \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/OWNER/REPO/pulls \
  -d '{
    "title": "feat: add portfolio rebalancing calculator",
    "body": "## Summary\n\nDescription here.\n\n## Tags\n\n- type:feat\n- scope:frontend\n- risk:low",
    "head": "your-branch-name",
    "base": "main"
  }'

# List open pull requests
curl -s \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/OWNER/REPO/pulls

# Get a specific pull request
curl -s \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/OWNER/REPO/pulls/123

# Add a comment to a pull request
curl -s -X POST \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/OWNER/REPO/issues/123/comments \
  -d '{"body": "Your comment here"}'

# List issues
curl -s \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/OWNER/REPO/issues

# Check workflow runs
curl -s \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/OWNER/REPO/actions/runs
```

**Important:** Replace `OWNER/REPO` with the actual repository owner and name (e.g., `Admiralhunter/PortfolioOS`). Always use `$GITHUB_TOKEN` for authentication — never hardcode tokens.

## Common Commands

<!-- TODO(BUILD_TODO#2): pnpm dev/build/test/lint don't exist — no package.json
     has been created yet. These commands will fail until Phase 0 scaffolding
     is complete. -->
<!-- TODO(BUILD_TODO#6): No unified root-level command runs both Python and JS
     checks. Agents must manually cd between directories. Add a root Makefile
     or check-all script. -->
```bash
# Development
pnpm dev                    # Start Electron app in dev mode
pnpm build                  # Build for production
pnpm test                   # Run frontend tests (Vitest)
pnpm lint                   # Lint TypeScript/React code

# Python sidecar
cd python && uv run pytest  # Run Python tests
cd python && uv run ruff check .  # Lint Python code

# Database
# DuckDB and SQLite are embedded — no server to start
```

## Data Flow

```
User Input
  -> React UI (renderer process)
    -> IPC invoke (contextBridge)
      -> Electron Main Process (Node.js)
        -> DuckDB/SQLite for data operations
        -> Python sidecar for simulations/analytics
        -> LLM provider for natural language features
      -> IPC response
    -> React state update
  -> UI render
```

## LLM Integration

- **Provider interface**: all providers (LM Studio, OpenAI, Anthropic, OpenRouter) implement the same request/response contract
- **Configuration**: endpoint URL, model name, API key (optional for local LM Studio)
- **Provider config stored in**: SQLite app state database
- **API keys stored in**: OS keychain via Electron safeStorage
- **Default endpoint**: `http://localhost:1234/v1` (LM Studio default)
- **Use cases**: report generation, natural language portfolio queries, trend summarization, agent-driven insights
- **Privacy rule**: local LM Studio can access all portfolio data freely; cloud providers require explicit user consent per interaction or via a global opt-in setting

## Financial Domain Notes

- **Cost basis methods**: FIFO, LIFO, specific lot identification, average cost
- **FIRE number**: Annual expenses / safe withdrawal rate
- **FIRE types**: Lean (minimal expenses), Fat (comfortable expenses), Coast (enough invested, no more contributions needed), Barista (part-time income covers gap)
- **Monte Carlo defaults**: 10,000 trials, 50-year horizon, bootstrap from historical returns
- **Tax-advantaged accounts**: 401(k), Traditional IRA, Roth IRA, HSA, 529, taxable brokerage
- **Key research**: Bengen (1994) — 4% rule origin, Trinity Study (1998) — success rate analysis, Kitces (2008+) — rising equity glidepath, Guyton-Klinger — guardrail withdrawal rules
- **Sequence-of-returns risk**: early retirement years' returns disproportionately affect portfolio longevity

## License

PolyForm Noncommercial 1.0.0 — this software cannot be used for commercial purposes. When adding dependencies, ensure license compatibility. GPL-compatible licenses are fine. AGPL dependencies need review. Proprietary or commercially-restricted dependencies must be avoided.
