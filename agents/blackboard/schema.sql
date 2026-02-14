-- Blackboard database schema for the PortfolioOS multi-agent system.
-- All agents coordinate through this single SQLite database.
-- See docs/MULTI_AGENT_SYSTEM.md for full design context.

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- Core findings table: every agent writes here
CREATE TABLE IF NOT EXISTS findings (
    id            TEXT PRIMARY KEY,
    agent_name    TEXT NOT NULL,
    severity      TEXT NOT NULL CHECK (severity IN ('critical', 'high', 'medium', 'low', 'info')),
    category      TEXT NOT NULL,
    title         TEXT NOT NULL,
    description   TEXT NOT NULL,
    file_path     TEXT,
    line_number   INTEGER,
    metadata      TEXT,
    status        TEXT NOT NULL DEFAULT 'open'
                  CHECK (status IN ('open', 'acknowledged', 'in_progress', 'resolved', 'wont_fix')),
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at    TEXT NOT NULL DEFAULT (datetime('now')),
    resolved_at   TEXT,
    resolved_by   TEXT
);

-- Task queue: TODO Scanner and analyzers produce, Worker consumes
CREATE TABLE IF NOT EXISTS task_queue (
    id            TEXT PRIMARY KEY,
    source_agent  TEXT NOT NULL,
    source_finding_id TEXT REFERENCES findings(id),
    title         TEXT NOT NULL,
    description   TEXT NOT NULL,
    priority      INTEGER NOT NULL DEFAULT 3 CHECK (priority BETWEEN 1 AND 5),
    status        TEXT NOT NULL DEFAULT 'pending'
                  CHECK (status IN ('pending', 'claimed', 'in_progress', 'review', 'done', 'blocked')),
    assigned_to   TEXT,
    branch_name   TEXT,
    pr_url        TEXT,
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Agent health log: Overlord reads this
CREATE TABLE IF NOT EXISTS agent_log (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name    TEXT NOT NULL,
    event_type    TEXT NOT NULL CHECK (event_type IN ('start', 'heartbeat', 'complete', 'error', 'skip')),
    message       TEXT,
    duration_ms   INTEGER,
    tokens_used   INTEGER,
    model_used    TEXT,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

-- File hash tracking: Documentor uses this
CREATE TABLE IF NOT EXISTS file_hashes (
    file_path     TEXT PRIMARY KEY,
    hash_sha256   TEXT NOT NULL,
    last_analyzed TEXT NOT NULL,
    agent_name    TEXT NOT NULL DEFAULT 'documentor',
    analysis      TEXT
);

-- Dependency state: Dependency Monitor uses this
CREATE TABLE IF NOT EXISTS dependency_state (
    package_name     TEXT NOT NULL,
    ecosystem        TEXT NOT NULL CHECK (ecosystem IN ('npm', 'pypi', 'system')),
    current_version  TEXT NOT NULL,
    latest_version   TEXT,
    latest_check     TEXT NOT NULL DEFAULT (datetime('now')),
    cve_ids          TEXT,
    recommendation   TEXT,
    notes            TEXT,
    PRIMARY KEY (package_name, ecosystem)
);

-- Agent configuration
CREATE TABLE IF NOT EXISTS agent_config (
    agent_name    TEXT PRIMARY KEY,
    enabled       INTEGER NOT NULL DEFAULT 1,
    schedule_cron TEXT,
    model_pref    TEXT DEFAULT 'local',
    max_tokens    INTEGER DEFAULT 4096,
    last_run      TEXT,
    config_json   TEXT
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_findings_status ON findings(status);
CREATE INDEX IF NOT EXISTS idx_findings_severity ON findings(severity);
CREATE INDEX IF NOT EXISTS idx_findings_agent ON findings(agent_name);
CREATE INDEX IF NOT EXISTS idx_findings_category ON findings(category);
CREATE INDEX IF NOT EXISTS idx_findings_dedup ON findings(agent_name, file_path, title);
CREATE INDEX IF NOT EXISTS idx_task_queue_status ON task_queue(status);
CREATE INDEX IF NOT EXISTS idx_task_queue_priority ON task_queue(priority);
CREATE INDEX IF NOT EXISTS idx_agent_log_agent ON agent_log(agent_name);
CREATE INDEX IF NOT EXISTS idx_agent_log_created ON agent_log(created_at);
