# Multi-Agent Monitoring & Development System

> **Status:** DESIGN DRAFT
> **Author:** AI-assisted design
> **Last Updated:** 2026-02-14
> **Scope:** 24/7 autonomous monitoring, analysis, and parallel development for PortfolioOS

---

## Table of Contents

1. [Overview](#1-overview)
2. [Agent Registry](#2-agent-registry)
3. [Architecture](#3-architecture)
4. [Shared State & Coordination](#4-shared-state--coordination)
5. [Implementation Path](#5-implementation-path)
6. [Agent Specifications](#6-agent-specifications)
7. [Missing Agents Identified](#7-missing-agents-identified)
8. [Scheduling & Execution Model](#8-scheduling--execution-model)
9. [LM Studio vs Cloud Provider Strategy](#9-lm-studio-vs-cloud-provider-strategy)
10. [Security & Privacy Considerations](#10-security--privacy-considerations)
11. [Rollout Phases](#11-rollout-phases)
12. [Cost Model](#12-cost-model)

---

## 1. Overview

This document defines a multi-agent system that provides continuous monitoring, quality enforcement, and parallel development for PortfolioOS. The system follows the same privacy-first principle as the main application: **local agents handle routine work, cloud agents are opt-in for complex reasoning.**

### Design Principles

- **Local-default, cloud-opt-in** — mirrors PortfolioOS's LLM architecture
- **Blackboard coordination** — agents share findings via a central SQLite database, not point-to-point messaging
- **Idempotent agents** — every agent can be re-run safely; no destructive side effects without human approval
- **Human-in-the-loop for writes** — agents can analyze freely but require approval to commit code, open PRs, or modify production state
- **Fail-open observability** — if an agent fails, it logs the failure and continues; it never blocks other agents

### What This System Does NOT Do

- Automatically merge code without human review
- Send portfolio data or user financial information anywhere
- Replace human architectural decisions
- Operate without the developer's awareness (all actions are logged)

---

## 2. Agent Registry

### Requested Agents (from specification)

| # | Agent | Role | Frequency |
|---|-------|------|-----------|
| 1 | **Documentor** | Explores codebase, detects changes via file hashes, updates RAG system | Continuous |
| 2 | **Test Analyzer** | Audits tests for quality: over-mocking, redundancy, coverage gaps | Weekly |
| 3 | **Security** | Code/dependency vulnerability analysis, CVE monitoring, triage plans | Daily |
| 4 | **Worker** | Picks up tasks from the queue and implements them | On-demand |
| 5 | **TODO Scanner** | Finds TODO/FIXME/HACK comments, sends to backlog queue | Daily |
| 6 | **Project Manager** | Scans GitHub issues, clarifies requirements, drafts specs | On issue creation |
| 7 | **Dependency Monitor** | Audits outdated/vulnerable deps, researches alternatives | Weekly |
| 8 | **Overlord** | Monitors all agents, flags coordination issues for the human | Continuous |
| 9 | **Performance** | Runs benchmarks, profiles code, identifies regressions | Weekly |
| 10 | **End-User Tester** | Simulates full install-and-run workflow | Weekly |
| 11 | **Finance Agent** | Validates financial calculations against published research | On change |
| 12 | **Legal Agent** | Monitors for problematic wording, license compliance | Weekly |

### Additional Agents Identified (Section 7)

| # | Agent | Role | Why It's Critical |
|---|-------|------|-------------------|
| 13 | **Architecture Guardian** | Enforces architectural boundaries (IPC-only, dual-DB, no telemetry) | Prevents architectural drift as codebase grows |
| 14 | **Data Integrity Agent** | Validates financial data pipelines: no silent NaN fills, gap handling, calculation accuracy | Financial data errors compound silently |
| 15 | **Changelog & Release Agent** | Generates changelogs from conventional commits, drafts release notes | Releases without notes frustrate users |
| 16 | **Accessibility Agent** | Audits UI for WCAG compliance, keyboard navigation, screen reader support | Legal requirement in many jurisdictions; easy to neglect |
| 17 | **Configuration Drift Detector** | Ensures CI config, pre-commit hooks, Makefile, and pyproject.toml stay consistent | Config rot is a silent killer |

---

## 3. Architecture

### High-Level Topology

```
┌─────────────────────────────────────────────────────────────┐
│                     HUMAN DEVELOPER                         │
│              (reviews dashboards, approves PRs)             │
└────────────────────────┬────────────────────────────────────┘
                         │ reads reports, approves actions
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    OVERLORD AGENT                            │
│         (orchestrator, conflict resolver, reporter)         │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Health   │  │ Conflict │  │ Summary  │  │ Escalate │   │
│  │ Monitor  │  │ Detector │  │ Reporter │  │ to Human │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │ reads/writes blackboard
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   BLACKBOARD (SQLite)                        │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  findings    │  │  task_queue   │  │  agent_log   │      │
│  │  (issues,    │  │  (work items  │  │  (heartbeat, │      │
│  │   alerts)    │  │   for Worker) │  │   status)    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  file_hashes │  │  dep_state   │  │  config      │      │
│  │  (Documentor │  │  (Dependency │  │  (agent      │      │
│  │   tracking)  │  │   Monitor)   │  │   settings)  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└────────────────────────┬────────────────────────────────────┘
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  READ-ONLY   │ │  ANALYZERS   │ │  ACTORS      │
│  AGENTS      │ │              │ │  (gated)     │
│              │ │              │ │              │
│ • Documentor │ │ • Test       │ │ • Worker     │
│ • TODO       │ │   Analyzer   │ │ • Project    │
│   Scanner    │ │ • Security   │ │   Manager    │
│ • Overlord   │ │ • Perf       │ │              │
│ • Config     │ │ • Finance    │ │ (requires    │
│   Drift      │ │ • Legal      │ │  human       │
│              │ │ • Arch       │ │  approval    │
│              │ │   Guardian   │ │  for writes) │
│              │ │ • Data       │ │              │
│              │ │   Integrity  │ │              │
│              │ │ • Deps       │ │              │
│              │ │ • Accessib.  │ │              │
│              │ │ • End-User   │ │              │
│              │ │   Tester     │ │              │
└──────────────┘ └──────────────┘ └──────────────┘
```

### Agent Classification

Agents fall into three permission tiers:

| Tier | Permissions | Agents |
|------|------------|--------|
| **Read-Only** | Read files, query databases, scan repos. Zero write access. | Documentor, TODO Scanner, Overlord, Config Drift Detector |
| **Analyzer** | Read-Only + can write findings to the blackboard + can create GitHub issues (draft). | Test Analyzer, Security, Performance, Finance, Legal, Architecture Guardian, Data Integrity, Dependency Monitor, Accessibility, End-User Tester |
| **Actor** | Analyzer + can create branches, write code, open PRs (all requiring human approval to merge). | Worker, Project Manager, Changelog Agent |

---

## 4. Shared State & Coordination

### Blackboard Database Schema

All agents coordinate through a single SQLite database (`agents/blackboard.db`). No agent-to-agent direct communication.

```sql
-- Core findings table: every agent writes here
CREATE TABLE findings (
    id            TEXT PRIMARY KEY,  -- UUID
    agent_name    TEXT NOT NULL,
    severity      TEXT NOT NULL CHECK (severity IN ('critical', 'high', 'medium', 'low', 'info')),
    category      TEXT NOT NULL,     -- 'security', 'test-quality', 'performance', etc.
    title         TEXT NOT NULL,
    description   TEXT NOT NULL,
    file_path     TEXT,              -- nullable, not all findings are file-specific
    line_number   INTEGER,
    metadata      TEXT,              -- JSON blob for agent-specific data
    status        TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'acknowledged', 'in_progress', 'resolved', 'wont_fix')),
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at    TEXT NOT NULL DEFAULT (datetime('now')),
    resolved_at   TEXT,
    resolved_by   TEXT               -- 'human' or agent name
);

-- Task queue: TODO Scanner and analyzers produce, Worker consumes
CREATE TABLE task_queue (
    id            TEXT PRIMARY KEY,
    source_agent  TEXT NOT NULL,      -- who created this task
    source_finding_id TEXT,           -- links back to findings table
    title         TEXT NOT NULL,
    description   TEXT NOT NULL,
    priority      INTEGER NOT NULL DEFAULT 3 CHECK (priority BETWEEN 1 AND 5),
    status        TEXT NOT NULL DEFAULT 'pending'
                  CHECK (status IN ('pending', 'claimed', 'in_progress', 'review', 'done', 'blocked')),
    assigned_to   TEXT,               -- 'worker' or null
    branch_name   TEXT,               -- git branch if work started
    pr_url        TEXT,               -- PR URL if submitted
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Agent health log: Overlord reads this
CREATE TABLE agent_log (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name    TEXT NOT NULL,
    event_type    TEXT NOT NULL CHECK (event_type IN ('start', 'heartbeat', 'complete', 'error', 'skip')),
    message       TEXT,
    duration_ms   INTEGER,
    tokens_used   INTEGER,            -- for cost tracking
    model_used    TEXT,               -- 'lm-studio/llama-3.1' or 'claude-opus-4-6'
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

-- File hash tracking: Documentor uses this
CREATE TABLE file_hashes (
    file_path     TEXT PRIMARY KEY,
    hash_sha256   TEXT NOT NULL,
    last_analyzed TEXT NOT NULL,
    agent_name    TEXT NOT NULL DEFAULT 'documentor',
    analysis      TEXT               -- JSON: summary, exports, dependencies, etc.
);

-- Dependency state: Dependency Monitor uses this
CREATE TABLE dependency_state (
    package_name     TEXT NOT NULL,
    ecosystem        TEXT NOT NULL CHECK (ecosystem IN ('npm', 'pypi', 'system')),
    current_version  TEXT NOT NULL,
    latest_version   TEXT,
    latest_check     TEXT NOT NULL DEFAULT (datetime('now')),
    cve_ids          TEXT,            -- JSON array of known CVEs
    recommendation   TEXT,            -- 'upgrade', 'replace', 'monitor', 'ok'
    notes            TEXT,
    PRIMARY KEY (package_name, ecosystem)
);

-- Agent configuration
CREATE TABLE agent_config (
    agent_name    TEXT PRIMARY KEY,
    enabled       INTEGER NOT NULL DEFAULT 1,
    schedule_cron TEXT,               -- cron expression for scheduled agents
    model_pref    TEXT DEFAULT 'local', -- 'local' or 'cloud'
    max_tokens    INTEGER DEFAULT 4096,
    last_run      TEXT,
    config_json   TEXT                -- agent-specific config as JSON
);
```

### Coordination Rules

1. **No locks.** Agents write findings with UUIDs; no two agents write the same row.
2. **Idempotent writes.** If an agent finds the same issue twice, it updates the existing finding (matched by `agent_name` + `file_path` + `title`) rather than creating a duplicate.
3. **Priority resolution.** When findings conflict (e.g., Security says "upgrade dep X" but Dependency Monitor says "X latest has breaking changes"), the Overlord flags the conflict for human review.
4. **Stale finding cleanup.** Findings older than 30 days in `open` status with no matching file are auto-closed by the Overlord.

---

## 5. Implementation Path

### Option A: Claude Agent SDK (Recommended for Cloud)

The Claude Agent SDK provides the most capable agent runtime with built-in file access, shell execution, and subagent orchestration.

```
agents/
  orchestrator.py          # Overlord: spawns and monitors all agents
  agents/
    documentor.py
    test_analyzer.py
    security.py
    worker.py
    todo_scanner.py
    project_manager.py
    dependency_monitor.py
    performance.py
    end_user_tester.py
    finance.py
    legal.py
    architecture_guardian.py
    data_integrity.py
    config_drift.py
    accessibility.py
    changelog.py
  blackboard/
    db.py                  # SQLite wrapper for blackboard operations
    schema.sql             # The schema above
    migrations/            # Schema migrations
  config/
    agents.yaml            # Per-agent configuration
    schedules.yaml         # Cron schedules
  reports/                 # Generated reports (gitignored)
```

**Orchestrator pattern using Claude Agent SDK:**

```python
# agents/orchestrator.py (conceptual)
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, SubagentDefinition

ANALYZER_AGENTS = [
    SubagentDefinition(
        name="security",
        model="claude-sonnet-4-20250514",  # cheaper model for routine scans
        system_prompt=open("agents/agents/security.py.md").read(),
        allowed_tools=["Read", "Glob", "Grep", "Bash"],
    ),
    SubagentDefinition(
        name="test_analyzer",
        model="claude-sonnet-4-20250514",
        system_prompt=open("agents/agents/test_analyzer.py.md").read(),
        allowed_tools=["Read", "Glob", "Grep", "Bash"],
    ),
    # ... more agents
]

async def run_cycle():
    """Run one monitoring cycle. Called by cron or systemd timer."""
    options = ClaudeAgentOptions(
        model="claude-opus-4-6",  # Overlord uses the strongest model
        allowed_tools=["Read", "Glob", "Grep", "Bash", "Task"],
        permission_mode="acceptEdits",
        subagents=ANALYZER_AGENTS,
    )

    async for message in query(
        prompt="Run the daily monitoring cycle. Check agent health, "
               "spawn analyzers in parallel, collect findings, "
               "write summary report.",
        options=options,
    ):
        handle_message(message)
```

### Option B: LangGraph + LM Studio (Recommended for Local)

For fully local execution with no cloud dependency.

```python
# agents/local_orchestrator.py (conceptual)
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from openai import OpenAI

# Point at LM Studio
client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")

def make_agent(system_prompt: str):
    """Create an agent function that calls LM Studio."""
    def agent(state: dict) -> dict:
        response = client.chat.completions.create(
            model="local-model",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": state["task"]},
            ],
            tools=state.get("tools", []),
        )
        return {"findings": response.choices[0].message.content}
    return agent

# Build the graph
graph = StateGraph(MonitorState)
graph.add_node("todo_scanner", make_agent(TODO_SCANNER_PROMPT))
graph.add_node("security", make_agent(SECURITY_PROMPT))
graph.add_node("test_analyzer", make_agent(TEST_ANALYZER_PROMPT))
graph.add_node("overlord", make_agent(OVERLORD_PROMPT))

# Parallel fan-out to analyzers, fan-in to overlord
graph.set_entry_point("todo_scanner")
graph.add_edge("todo_scanner", "security")
graph.add_edge("todo_scanner", "test_analyzer")
graph.add_edge("security", "overlord")
graph.add_edge("test_analyzer", "overlord")
graph.add_edge("overlord", END)

checkpointer = SqliteSaver.from_conn_string("agents/state.db")
app = graph.compile(checkpointer=checkpointer)
```

### Option C: GitHub Actions (Simplest Starting Point)

Zero infrastructure. Agents run as scheduled GitHub Actions workflows.

```yaml
# .github/workflows/agent-security.yml
name: Security Agent
on:
  schedule:
    - cron: '0 6 * * *'  # Daily at 6 AM UTC
  workflow_dispatch:

jobs:
  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run Security Agent
        uses: anthropics/claude-code-action@v1
        with:
          prompt: |
            You are the Security Agent for PortfolioOS.

            1. Check all Python dependencies for known CVEs:
               Run: uv pip list --format=json
               Then search each dependency for CVEs.

            2. Scan code for security anti-patterns:
               - Hardcoded secrets or API keys
               - SQL injection vectors (raw string formatting in queries)
               - Path traversal vulnerabilities
               - Unsafe deserialization
               - Command injection in subprocess calls

            3. Check if any new dependencies were added since last scan.

            Report findings as a GitHub issue with label "security-agent".
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          allowed_tools: "Bash,Read,Glob,Grep"
```

### Recommended Path: Phased Hybrid

Start with **Option C** (GitHub Actions) for immediate value, then migrate to **Option A** (Claude Agent SDK) for complex agents, with **Option B** (LM Studio) for privacy-sensitive local analysis.

---

## 6. Agent Specifications

### 6.1 Documentor

**Purpose:** Maintain a live knowledge base of the codebase. Detect file changes via SHA-256 hashes, re-analyze changed files, and store structured summaries for RAG retrieval.

**Inputs:** Git working tree, `file_hashes` table
**Outputs:** Updated `file_hashes` table with analysis JSON, optional markdown summaries in `agents/reports/docs/`
**Model requirement:** Low — local LM Studio sufficient for summarization
**Schedule:** On every push to `main` (GitHub Action trigger), or hourly locally

**Analysis per file:**
```json
{
  "summary": "Monte Carlo simulation engine using NumPy vectorized operations",
  "exports": ["MonteCarloEngine", "SimulationResult", "run_simulation"],
  "dependencies": ["numpy", "scipy"],
  "internal_imports": ["portfolioos.analysis.returns"],
  "complexity": "medium",
  "test_file": "tests/simulation/monte_carlo_test.py",
  "key_decisions": ["Uses bootstrap resampling from historical returns"]
}
```

**RAG storage options:**
- **Simplest:** JSON in SQLite `file_hashes.analysis` column (searchable via JSON functions)
- **Better:** ChromaDB or LanceDB embedded vector store alongside the blackboard
- **Best:** DuckDB with `vss` extension (vector similarity search) — aligns with existing tech stack

---

### 6.2 Test Analyzer

**Purpose:** Audit test suite quality. Identify tests that are over-mocked (testing mocks instead of behavior), redundant, missing edge cases, or testing implementation details.

**Inputs:** All `*_test.py` and `*.test.ts` files, coverage reports
**Outputs:** Findings in blackboard (`category: 'test-quality'`)
**Model requirement:** Medium — needs code reasoning. Cloud (Sonnet) preferred, local viable for simpler checks.
**Schedule:** Weekly, or on PR with test changes

**Detection heuristics:**
| Issue | Detection Method |
|-------|-----------------|
| Over-mocking | Count `mock.patch` / `jest.mock` per test; flag if >3 mocks per test function |
| Redundant tests | Identify tests with identical assertion patterns on different inputs (should be parametrized) |
| Missing edge cases | Compare function parameters against test inputs; flag untested boundary values |
| Brittle tests | Tests that assert on internal state, private methods, or specific call counts |
| No assertions | Test functions that call code but never assert |
| Coverage theater | High line coverage but low branch coverage (happy-path only) |

---

### 6.3 Security Agent

**Purpose:** Continuous security posture monitoring. Code analysis, dependency CVE tracking, and triage plan generation.

**Inputs:** Full codebase, `dependency_state` table, CVE databases
**Outputs:** Findings (`category: 'security'`, severity-rated), triage plans in task queue
**Model requirement:** High — needs nuanced security reasoning. Cloud (Opus/Sonnet) strongly recommended.
**Schedule:** Daily for CVE checks, on every PR for code scan

**Scanning scope:**
1. **Static analysis** — injection vectors, hardcoded secrets, unsafe deserialization, path traversal
2. **Dependency CVEs** — query OSV.dev API for Python (PyPI) and JS (npm) packages
3. **Configuration security** — Electron security headers, CSP policy, `nodeIntegration` settings
4. **Financial data handling** — ensure portfolio data is never logged, transmitted without consent, or stored unencrypted
5. **Supply chain** — verify dependency integrity (lock file hashes)

**CVE monitoring integration:**
```bash
# Query OSV.dev for a specific package
curl -s -X POST https://api.osv.dev/v1/query \
  -d '{"package": {"name": "numpy", "ecosystem": "PyPI"}}'
```

---

### 6.4 Worker Agent

**Purpose:** Pick up tasks from the queue and implement them. The only agent that writes production code.

**Inputs:** `task_queue` table (status: `pending`), codebase
**Outputs:** Git branches, code changes, PRs (all requiring human review)
**Model requirement:** High — needs strong code generation. Cloud (Opus) recommended.
**Schedule:** On-demand, triggered when queue has pending items

**Workflow:**
1. Claim a task (set `status: 'claimed'`, `assigned_to: 'worker'`)
2. Read the task description and any linked findings
3. Create a feature branch (`agent/worker/<task-id>`)
4. Implement the change following project conventions (CLAUDE.md)
5. Run `make check-all` to verify
6. Open a PR using `scripts/create-pr.sh`
7. Update task status to `review`, set `pr_url`
8. Wait for human approval

**Safety constraints:**
- Worker NEVER merges its own PRs
- Worker NEVER modifies `main` directly
- Worker NEVER touches security-critical files (`.env`, keychain code, auth modules) without human approval
- Worker runs `make check-all` before every PR; if checks fail, it fixes or abandons

---

### 6.5 TODO Scanner

**Purpose:** Extract TODO, FIXME, HACK, XXX, and NOTE comments from the codebase and feed them into the task queue.

**Inputs:** All source files
**Outputs:** `task_queue` entries, findings (`category: 'todo'`)
**Model requirement:** Minimal — regex scanning + light LLM classification for priority
**Schedule:** Daily

**Extraction patterns:**
```
# Python
# TODO: description
# FIXME: description
# HACK: description
# XXX: description

// TypeScript
// TODO: description
// FIXME: description
```

**Priority mapping:**
| Marker | Default Priority | Notes |
|--------|-----------------|-------|
| FIXME | 2 (high) | Known bugs or broken behavior |
| HACK | 2 (high) | Technical debt that should be addressed |
| XXX | 3 (medium) | Needs attention but not urgent |
| TODO | 3 (medium) | Planned work |
| NOTE | 5 (low) | Informational, no action needed (not queued) |

---

### 6.6 Project Manager

**Purpose:** Monitor GitHub issues for new requests from maintainers. Clarify requirements, ask follow-up questions, and draft specifications before handing off to the Worker.

**Inputs:** GitHub issues API, existing specs in `docs/`
**Outputs:** Issue comments (clarification questions), spec drafts in `docs/specs/`, task queue entries
**Model requirement:** High — needs to understand requirements and communicate clearly. Cloud (Opus) recommended.
**Schedule:** On new issue creation (webhook/polling), or every 6 hours

**Workflow:**
1. Poll `GET /repos/Admiralhunter/PortfolioOS/issues?state=open&sort=created`
2. For new issues without a spec:
   a. Analyze the request against existing architecture (SPEC.md, ARCHITECTURE.md)
   b. Identify ambiguities or missing requirements
   c. Post a comment with clarifying questions
   d. Once clarified, draft a spec and add tasks to the queue
3. Label issues: `needs-spec`, `spec-ready`, `in-progress`

---

### 6.7 Dependency Monitor

**Purpose:** Track dependency freshness, security, and alternatives. Proactively identify when a dependency should be upgraded, replaced, or when a better alternative exists.

**Inputs:** `pyproject.toml`, `package.json` (when it exists), PyPI/npm APIs
**Outputs:** `dependency_state` table updates, findings, task queue entries for upgrades
**Model requirement:** Medium — needs to evaluate changelogs and breaking changes. Sonnet sufficient.
**Schedule:** Weekly

**Monitoring scope:**
1. **Version freshness** — compare installed vs. latest stable
2. **Security** — CVE check via OSV.dev (overlaps with Security Agent; Dependency Monitor focuses on upgrade feasibility, Security Agent on immediate risk)
3. **Maintenance health** — check if upstream repo is archived, has stale PRs, declining commit frequency
4. **License compliance** — flag any dependency with AGPL, proprietary, or commercially-restricted license (per CLAUDE.md constraints)
5. **Better alternatives** — when a dependency is unmaintained, research active forks or replacements

---

### 6.8 Overlord

**Purpose:** Meta-agent that monitors all other agents. Detects failures, coordination conflicts, stale findings, and generates human-readable summaries.

**Inputs:** `agent_log` table, `findings` table, `task_queue` table
**Outputs:** Daily/weekly summary reports, escalation alerts, conflict resolution entries
**Model requirement:** Medium for routine summaries, High for conflict analysis. Hybrid local/cloud.
**Schedule:** Continuous (lightweight heartbeat check every 15 min), full report daily

**Monitoring responsibilities:**
| Check | Frequency | Action on Failure |
|-------|-----------|-------------------|
| Agent heartbeat | Every 15 min | Log warning if agent missed 3+ scheduled runs |
| Finding conflicts | Daily | Flag contradictory findings from different agents |
| Queue stagnation | Daily | Alert if tasks sit in `pending` for >7 days |
| Token spend | Daily | Alert if daily cloud token usage exceeds budget |
| Error rate | Per run | Alert if any agent errors on >50% of recent runs |

**Daily summary format:**
```markdown
## Agent System Daily Report — 2026-02-14

### Health
- 12/12 agents operational
- 0 errors in last 24h
- Token usage: 45,230 (budget: 100,000)

### New Findings
- [CRITICAL] Security: numpy CVE-2026-XXXX (severity 9.1)
- [HIGH] Test Analyzer: 3 tests in monte_carlo_test.py are redundant
- [MEDIUM] TODO Scanner: 5 new TODOs added in withdrawal.py

### Queue Status
- 8 tasks pending, 2 in progress, 14 completed this week
- Oldest pending: "Add input validation to FRED adapter" (3 days)

### Conflicts
- None

### Action Required
- [ ] Review CVE-2026-XXXX triage plan
- [ ] Approve PR #42 from Worker (adds FRED input validation)
```

---

### 6.9 Performance Agent

**Purpose:** Identify performance regressions and bottlenecks through benchmarking and profiling.

**Inputs:** Codebase, benchmark results, Python profiler output
**Outputs:** Findings (`category: 'performance'`), benchmark baselines
**Model requirement:** Medium — needs to interpret profiler output. Sonnet sufficient.
**Schedule:** Weekly, or on PR with changes to core computation modules

**Analysis scope:**
1. **Monte Carlo simulation benchmarks** — runtime for 10K trials should not regress
2. **Database query performance** — DuckDB analytical queries, SQLite transactional queries
3. **Memory profiling** — detect memory leaks in long-running processes (Electron, Python sidecar)
4. **Bundle size** (once frontend exists) — track JS bundle growth
5. **Startup time** — Electron cold-start and Python sidecar initialization

---

### 6.10 End-User Tester

**Purpose:** Simulate the full user experience: clone, install dependencies, build, launch, and exercise core workflows.

**Inputs:** The repository itself (treated as a black box)
**Outputs:** Findings (`category: 'ux'`), step-by-step failure reports
**Model requirement:** Medium — needs to follow instructions and report issues. Sonnet sufficient.
**Schedule:** Weekly, or on release branches

**Test script:**
1. Clone repo to a clean directory
2. Install Python dependencies (`uv sync`)
3. Install JS dependencies (`pnpm install`, when applicable)
4. Run `make check-all`
5. Build the application (`pnpm build`, when applicable)
6. Launch the application
7. Exercise core workflows (add portfolio, run simulation, view results)
8. Report any step that fails with full error output

---

### 6.11 Finance Agent

**Purpose:** Validate that all financial calculations, methodologies, and guidance adhere to published academic research and regulatory standards.

**Inputs:** Source code for financial calculations, test assertions, user-facing text
**Outputs:** Findings (`category: 'finance'`)
**Model requirement:** High — needs deep domain knowledge. Cloud (Opus) strongly recommended.
**Schedule:** On change to financial calculation modules, or monthly audit

**Validation checklist:**
| Area | Validation |
|------|-----------|
| Safe Withdrawal Rate | Matches Bengen (1994) — 4% of initial portfolio, inflation-adjusted |
| Monte Carlo | Uses bootstrap resampling (not parametric normal), configurable seed |
| Cost basis | FIFO/LIFO/SpecID/AvgCost correctly implemented per IRS Publication 550 |
| Tax-loss harvesting | Respects wash-sale rule (30-day window) |
| Inflation adjustment | Uses CPI-U or configurable index, not hardcoded rate |
| Compound interest | Correct compounding frequency (daily/monthly/annual) |
| FIRE calculations | Expense-based, not income-based; accounts for tax drag |
| Citations | Every methodology has a citation in code comments or docs |

---

### 6.12 Legal Agent

**Purpose:** Monitor for legal risks: problematic wording that could constitute financial advice, license violations, and regulatory compliance issues.

**Inputs:** User-facing text, documentation, dependency licenses
**Outputs:** Findings (`category: 'legal'`)
**Model requirement:** High — needs nuanced language analysis. Cloud (Opus) recommended.
**Schedule:** Weekly, or on changes to user-facing content

**Scanning scope:**
1. **Financial advice disclaimers** — ensure the app never states "you should invest in X" without disclaimers
2. **License compliance** — PolyForm Noncommercial 1.0.0 compatibility with all dependencies
3. **Regulatory language** — avoid triggering SEC/FINRA "investment advisor" definitions
4. **Privacy claims** — ensure "local-first" and "no cloud" claims remain true
5. **Wording patterns to flag:**
   - "guaranteed returns"
   - "you should buy/sell"
   - "this is financial advice"
   - "we recommend" (without disclaimer)
   - Claims about tax savings without "consult a tax professional" qualifier

---

## 7. Missing Agents Identified

Beyond the 12 agents originally specified, these are critical for a financial application:

### 7.1 Architecture Guardian

**Why critical:** As multiple agents and developers add code in parallel, architectural boundaries drift. For PortfolioOS, the key invariants are:
- Renderer process never directly accesses databases or filesystem (must go through IPC)
- DuckDB and SQLite are not merged (different access patterns)
- No telemetry or tracking code is introduced
- LM Studio remains the default LLM (cloud providers are opt-in)
- API keys go through Electron safeStorage, never stored in plaintext

**Detection method:** AST analysis + pattern matching for `import duckdb` in renderer code, `fetch()` calls to analytics endpoints, `navigator.sendBeacon()`, etc.

### 7.2 Data Integrity Agent

**Why critical:** Financial applications have a unique failure mode: silent data corruption. A NaN in a Monte Carlo simulation doesn't crash — it produces a wrong number that the user trusts.

**Checks:**
- No `fillna(0)` or silent interpolation without flagging
- All division operations guard against division by zero
- Date ranges are contiguous (no missing trading days without explicit handling)
- Portfolio values are non-negative (basic sanity check)
- Historical returns data matches known benchmarks (e.g., S&P 500 2024 return within expected range)

### 7.3 Changelog & Release Agent

**Why critical:** Automated releases without clear changelogs frustrate users. Since PortfolioOS uses conventional commits, this agent can auto-generate changelogs.

**Outputs:** `CHANGELOG.md` updates, draft GitHub release notes, version bump recommendations (major/minor/patch based on commit types).

### 7.4 Accessibility Agent

**Why critical:** Financial tools must be accessible. Screen readers, keyboard navigation, color contrast, and ARIA labels are frequently neglected.

**Checks (once frontend exists):**
- axe-core automated accessibility audit
- Keyboard navigation for all interactive elements
- ARIA labels on charts and data tables
- Color contrast ratios (WCAG AA minimum)
- Screen reader announcement of live data updates (portfolio values, simulation progress)

### 7.5 Configuration Drift Detector

**Why critical:** CI config, pre-commit hooks, Makefile targets, and `pyproject.toml` settings can quietly go out of sync. One developer adds a new linting rule; another agent bypasses it.

**Checks:**
- Pre-commit hooks match CI workflow steps
- Makefile targets cover all CI checks
- Coverage thresholds are consistent across `pyproject.toml`, `ci.yml`, and `.pre-commit-config.yaml`
- Python version is consistent across `pyproject.toml`, `ci.yml`, and Dockerfile (if any)
- All `scripts/*.py` referenced in hooks actually exist

---

## 8. Scheduling & Execution Model

### Execution Tiers

| Tier | Trigger | Agents | Infrastructure |
|------|---------|--------|----------------|
| **On-push** | Git push to `main` | Documentor, Config Drift | GitHub Actions |
| **On-PR** | Pull request opened/updated | Security (code scan), Test Analyzer, Architecture Guardian, Finance, Legal | GitHub Actions |
| **Daily** | Cron: `0 6 * * *` | Security (CVE scan), TODO Scanner, Overlord (full report) | GitHub Actions or local cron |
| **Weekly** | Cron: `0 6 * * 1` | Dependency Monitor, Performance, End-User Tester, Accessibility, Test Analyzer (deep), Legal (full) | GitHub Actions or local cron |
| **On-demand** | Queue has items | Worker, Project Manager | Manual trigger or watched queue |
| **Continuous** | Every 15 min | Overlord (heartbeat only) | Local systemd timer |

### Systemd Timer (Local Agents)

```ini
# /etc/systemd/user/portfolioos-agents.timer
[Unit]
Description=PortfolioOS Agent Monitoring Cycle

[Timer]
OnCalendar=*-*-* 06:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

```ini
# /etc/systemd/user/portfolioos-agents.service
[Unit]
Description=PortfolioOS Agent Monitoring Run

[Service]
Type=oneshot
WorkingDirectory=/home/user/PortfolioOS
ExecStart=/home/user/.local/bin/uv run python agents/orchestrator.py --cycle daily
Environment=LM_STUDIO_ENDPOINT=http://localhost:1234/v1
```

### GitHub Actions Cron

```yaml
# .github/workflows/agent-daily.yml
name: Daily Agent Cycle
on:
  schedule:
    - cron: '0 6 * * *'
  workflow_dispatch:

jobs:
  run-agents:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        agent: [security-cve, todo-scanner, overlord-report]
    steps:
      - uses: actions/checkout@v4
      - uses: anthropics/claude-code-action@v1
        with:
          prompt_file: agents/prompts/${{ matrix.agent }}.md
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
```

---

## 9. LM Studio vs Cloud Provider Strategy

### Decision Matrix

| Agent | LM Studio (Local) | Cloud (Sonnet) | Cloud (Opus) | Rationale |
|-------|-------------------|----------------|--------------|-----------|
| Documentor | **Primary** | Fallback | — | Summarization is well within local model capability |
| TODO Scanner | **Primary** | — | — | Regex + light classification; local is sufficient |
| Config Drift | **Primary** | — | — | Rule-based checks; LLM is optional |
| Test Analyzer | Secondary | **Primary** | — | Needs code reasoning; Sonnet is cost-effective |
| Security | — | **Primary** | Escalation | CVE triage needs strong reasoning; Opus for critical findings |
| Worker | — | — | **Primary** | Code generation requires the strongest model |
| Project Manager | — | — | **Primary** | Requirement analysis and spec writing need deep reasoning |
| Dependency Monitor | Secondary | **Primary** | — | Changelog analysis needs moderate reasoning |
| Overlord | **Primary** | Escalation | — | Routine summaries local; conflict resolution cloud |
| Performance | **Primary** | Fallback | — | Mostly benchmark comparison; local sufficient |
| End-User Tester | **Primary** | Fallback | — | Follows scripts; local sufficient |
| Finance Agent | — | — | **Primary** | Financial domain expertise; wrong answers are dangerous |
| Legal Agent | — | — | **Primary** | Legal nuance requires the strongest model |
| Architecture Guardian | Secondary | **Primary** | — | Pattern matching + reasoning about invariants |
| Data Integrity | **Primary** | Fallback | — | Mostly rule-based numerical checks |
| Accessibility | Secondary | **Primary** | — | Needs understanding of WCAG standards |
| Changelog | **Primary** | — | — | Template-based generation from conventional commits |

### Cost Estimation

Assuming current API pricing (2026):

| Category | Agents | Est. Monthly Tokens | Est. Monthly Cost |
|----------|--------|--------------------|--------------------|
| Local only | 6 agents | 0 (local) | Electricity only |
| Sonnet | 5 agents | ~2M tokens/month | ~$6-12/month |
| Opus | 4 agents (infrequent) | ~500K tokens/month | ~$15-30/month |
| **Total cloud** | | | **~$20-45/month** |

These estimates assume a moderately active solo-developer project. Costs scale with codebase size and PR frequency.

### LM Studio Model Recommendations

| Task Type | Recommended Models | Min VRAM |
|-----------|--------------------|----------|
| Code summarization | Llama 3.1 8B, CodeLlama 13B | 8 GB |
| Code reasoning | Llama 3.1 70B, DeepSeek Coder V2 | 48 GB |
| General reasoning | Llama 3.1 70B, Mixtral 8x22B | 48 GB |
| Light classification | Phi-3 Mini, Llama 3.1 8B | 6 GB |

For a home setup with a single GPU (e.g., RTX 4090 with 24 GB VRAM), the 8B models handle most local agent tasks effectively. The 70B models require either quantization (Q4) or multi-GPU setups.

---

## 10. Security & Privacy Considerations

### Agent Permissions

```yaml
# agents/config/permissions.yaml
documentor:
  filesystem: read-only
  git: read-only
  network: none
  blackboard: write (file_hashes only)

worker:
  filesystem: read-write (non-main branches only)
  git: branch, commit, push (never to main)
  network: none
  blackboard: read all, write (task_queue status only)

security:
  filesystem: read-only
  git: read-only
  network: osv.dev API only
  blackboard: write (findings, dependency_state)

# ... etc
```

### Data Boundaries

- **No agent ever accesses user financial data.** Agents operate on source code, tests, and configuration — never on portfolio databases.
- **No agent sends source code to external services** except during cloud LLM inference calls (which are opt-in per the project's existing privacy model).
- **Blackboard database is gitignored.** It contains findings and operational state, not source code.
- **Agent API keys are separate from application API keys.** Stored in a separate keychain entry.

### Threat Model for the Agent System

| Threat | Mitigation |
|--------|-----------|
| Agent writes malicious code | Worker PRs require human review; `make check-all` gates |
| Agent leaks source code | Network access restricted per agent; local agents preferred |
| Agent corrupts blackboard | Idempotent writes, UUID-based rows, no DELETE operations |
| Agent runs indefinitely | Token budgets, execution timeouts, Overlord monitoring |
| Compromised dependency in agent tooling | Separate `pyproject.toml` for agents; pinned versions |
| Agent modifies its own config | Config files are read-only to agents; only human edits |

---

## 11. Rollout Phases

### Phase 1: Foundation (Weeks 1-2)

**Goal:** Blackboard database, TODO Scanner, and Overlord running via GitHub Actions.

**Deliverables:**
- [ ] `agents/blackboard/schema.sql` — create blackboard schema
- [ ] `agents/blackboard/db.py` — Python wrapper for blackboard CRUD
- [ ] `agents/agents/todo_scanner.py` — regex-based TODO extraction + LLM priority classification
- [ ] `agents/agents/overlord.py` — basic health check and summary report
- [ ] `.github/workflows/agent-daily.yml` — cron-triggered workflow
- [ ] `agents/README.md` — setup and usage documentation

**Why start here:** These two agents are low-risk (read-only), immediately useful, and establish the coordination infrastructure all other agents depend on.

### Phase 2: Analysis Agents (Weeks 3-5)

**Goal:** Security, Test Analyzer, and Dependency Monitor operational.

**Deliverables:**
- [ ] `agents/agents/security.py` — code scanning + CVE monitoring via OSV.dev
- [ ] `agents/agents/test_analyzer.py` — test quality auditing
- [ ] `agents/agents/dependency_monitor.py` — freshness and license checks
- [ ] `agents/agents/config_drift.py` — CI/hook consistency checker
- [ ] GitHub Actions workflows for each agent
- [ ] Overlord updated to monitor new agents

### Phase 3: Actor Agents (Weeks 6-8)

**Goal:** Worker and Project Manager can process the queue.

**Deliverables:**
- [ ] `agents/agents/worker.py` — task implementation with PR creation
- [ ] `agents/agents/project_manager.py` — issue triage and spec drafting
- [ ] Human approval workflow (PR review gates)
- [ ] Queue priority system and claim/release logic

### Phase 4: Domain Agents (Weeks 9-12)

**Goal:** Finance, Legal, Performance, and End-User Tester.

**Deliverables:**
- [ ] `agents/agents/finance.py` — financial calculation validation
- [ ] `agents/agents/legal.py` — regulatory language scanning
- [ ] `agents/agents/performance.py` — benchmarking framework
- [ ] `agents/agents/end_user_tester.py` — install-and-run simulation
- [ ] `agents/agents/architecture_guardian.py` — architectural invariant enforcement

### Phase 5: Local Agent Infrastructure (Weeks 13-16)

**Goal:** LM Studio-backed local agents for privacy-sensitive and cost-sensitive operations.

**Deliverables:**
- [ ] Local orchestrator using LangGraph + SQLite checkpointer
- [ ] LM Studio integration for Documentor, TODO Scanner, Overlord, Performance
- [ ] systemd timer for scheduled local runs
- [ ] Hybrid mode: local agents write to blackboard, cloud agents read from it
- [ ] `agents/agents/documentor.py` — file hash tracking + RAG system
- [ ] `agents/agents/data_integrity.py` — financial data validation
- [ ] `agents/agents/accessibility.py` — WCAG compliance checks
- [ ] `agents/agents/changelog.py` — automated changelog generation

---

## 12. Cost Model

### GitHub Actions Minutes

| Agent | Runs/Month | Est. Minutes/Run | Monthly Minutes |
|-------|-----------|-----------------|-----------------|
| TODO Scanner | 30 | 2 | 60 |
| Security (CVE) | 30 | 5 | 150 |
| Security (code) | 20 (per PR) | 3 | 60 |
| Test Analyzer | 4 | 10 | 40 |
| Dependency Monitor | 4 | 5 | 20 |
| Overlord | 30 | 2 | 60 |
| Performance | 4 | 15 | 60 |
| End-User Tester | 4 | 10 | 40 |
| **Total** | | | **~490 min/month** |

GitHub Free tier includes 2,000 minutes/month. This system uses ~25% of the free allocation.

### Cloud API Costs

See Section 9 for token estimates. Budget ~$20-45/month for cloud LLM calls, with the option to reduce by shifting more agents to LM Studio as local model quality improves.

### Total Monthly Cost (Estimated)

| Component | Cost |
|-----------|------|
| GitHub Actions | $0 (within free tier) |
| Cloud LLM (Sonnet + Opus) | $20-45 |
| LM Studio (local) | $0 (electricity) |
| **Total** | **$20-45/month** |

---

## Appendix A: Blackboard Query Examples

```sql
-- Get all unresolved critical/high findings
SELECT agent_name, title, file_path, created_at
FROM findings
WHERE status = 'open' AND severity IN ('critical', 'high')
ORDER BY severity, created_at;

-- Get pending tasks by priority
SELECT title, source_agent, priority, created_at
FROM task_queue
WHERE status = 'pending'
ORDER BY priority, created_at;

-- Agent health: last successful run per agent
SELECT agent_name, MAX(created_at) as last_run, event_type
FROM agent_log
WHERE event_type = 'complete'
GROUP BY agent_name;

-- Token spend in last 24h
SELECT agent_name, SUM(tokens_used) as total_tokens, model_used
FROM agent_log
WHERE created_at > datetime('now', '-1 day')
GROUP BY agent_name, model_used;

-- Dependency audit summary
SELECT package_name, current_version, latest_version, recommendation,
       json_array_length(cve_ids) as cve_count
FROM dependency_state
WHERE recommendation != 'ok'
ORDER BY cve_count DESC;
```

## Appendix B: Agent Prompt Template

Each agent is defined by a markdown prompt file in `agents/prompts/`. Standard structure:

```markdown
# Agent: {name}

## Role
You are the {name} agent for PortfolioOS. {one-sentence purpose}

## Context
- Repository: PortfolioOS (local-first financial desktop app)
- Tech stack: Electron + React + Python sidecar
- Key constraints: {relevant constraints from CLAUDE.md}

## Task
{specific instructions for this run}

## Output Format
Write your findings as JSON to stdout in this format:
{json schema}

## Rules
- Never modify source code (unless you are the Worker agent)
- Never access user financial data
- Report uncertain findings as severity: 'info' with a note
- If you find nothing, report an empty findings array (not an error)
```

## Appendix C: Technology Decision Record

| Decision | Choice | Alternatives Considered | Rationale |
|----------|--------|------------------------|-----------|
| Coordination model | Blackboard (shared SQLite) | Message queue (Redis/RabbitMQ), Direct agent-to-agent | Simplest for single-developer; no infrastructure to maintain; agents are decoupled |
| Cloud orchestration | Claude Agent SDK | LangGraph Cloud, CrewAI | Native subagent support, session persistence, aligns with existing Claude Code usage |
| Local orchestration | LangGraph + LM Studio | CrewAI, smolagents | Best state persistence (SQLite checkpointer), graph-based control flow, mature |
| Scheduling | GitHub Actions cron + systemd timers | Airflow, Prefect, Temporal | Zero infrastructure for cloud; systemd is universal for local |
| Vector store (RAG) | DuckDB `vss` extension | ChromaDB, LanceDB, Pinecone | Already in tech stack; no new dependency |
| CVE database | OSV.dev API | NVD, Snyk, GitHub Advisory | Free, open, covers PyPI and npm, simple REST API |
