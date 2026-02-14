# Multi-Agent System — Developer Tooling

This directory contains the Phase 1 implementation of the PortfolioOS multi-agent monitoring system. See [`docs/MULTI_AGENT_SYSTEM.md`](../docs/MULTI_AGENT_SYSTEM.md) for the full design.

## Quick Start

```bash
# Run the TODO Scanner against the repo
cd PortfolioOS
uv run --project agents python -m agents.agents.todo_scanner

# Run the Overlord report
uv run --project agents python -m agents.agents.overlord

# Run agent tests
cd agents && uv run pytest tests/ -v
```

## What's Implemented (Phase 1)

| Component | Description |
|-----------|-------------|
| `blackboard/schema.sql` | SQLite schema for cross-agent coordination |
| `blackboard/db.py` | Typed Python wrapper for all blackboard CRUD operations |
| `agents/todo_scanner.py` | Scans codebase for TODO/FIXME/HACK/XXX markers, writes findings + tasks |
| `agents/overlord.py` | Reads blackboard state, generates markdown health reports |
| `prompts/` | Markdown prompt templates for GitHub Actions agent runs |

## Directory Structure

```
agents/
  __init__.py
  pyproject.toml          # Separate from main python/ project (isolated deps)
  README.md               # This file
  blackboard/
    __init__.py
    schema.sql            # SQLite schema (6 tables)
    db.py                 # Python wrapper
    blackboard.db         # (gitignored) Runtime database
  agents/
    __init__.py
    todo_scanner.py       # Phase 1 agent
    overlord.py           # Phase 1 agent
  prompts/
    todo-scanner.md       # Prompt template for CI
    overlord-report.md    # Prompt template for CI
  config/                 # (future) Agent YAML configs
  reports/                # (gitignored) Generated reports
  tests/
    blackboard_test.py
    todo_scanner_test.py
```

## Blackboard Database

All agents coordinate through a shared SQLite database (`blackboard/blackboard.db`). No agent-to-agent messaging — agents write findings and read each other's output from the blackboard.

**Core tables:**
- `findings` — issues, alerts, and observations from any agent
- `task_queue` — work items for the Worker agent (Phase 3)
- `agent_log` — heartbeat/status events for health monitoring
- `file_hashes` — Documentor's file change tracking (Phase 5)
- `dependency_state` — Dependency Monitor's package tracking (Phase 2)
- `agent_config` — per-agent settings and scheduling

## GitHub Actions

The daily agent cycle runs via `.github/workflows/agent-daily.yml`:

1. **TODO Scanner** runs first, populates the blackboard
2. **Overlord** runs second, reads the blackboard, generates a report
3. Reports are uploaded as GitHub Actions artifacts (retained 30 days)

Trigger manually: Actions tab → "Daily Agent Cycle" → "Run workflow"

## Development

```bash
# Lint agent code
cd agents && uv run ruff check .

# Run tests
cd agents && uv run pytest tests/ -v

# Test a single agent locally
uv run --project agents python -m agents.agents.todo_scanner --repo-root /path/to/repo
```

The agents use only the Python standard library at runtime (sqlite3, re, json, pathlib). Dev dependencies (pytest, ruff) are in `agents/pyproject.toml`.
