"""SQLite wrapper for the blackboard coordination database.

Provides typed CRUD operations for all blackboard tables so agents
don't construct raw SQL themselves.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA_PATH = Path(__file__).parent / "schema.sql"
DEFAULT_DB_PATH = Path(__file__).parent / "blackboard.db"


def _utcnow() -> str:
    """Return current UTC time as an ISO-8601 string (no TZ suffix)."""
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def _deterministic_id(*parts: str | None) -> str:
    """Generate a deterministic 32-char hex ID by hashing the given parts.

    This ensures the same logical entity (e.g. a TODO marker at a
    specific location with a specific title) always receives the same
    ID across independent runs, even when the database is recreated
    from scratch between runs (as happens in CI).
    """
    key = "\x00".join(p or "" for p in parts)
    return hashlib.sha256(key.encode()).hexdigest()[:32]


class Blackboard:
    """Thin wrapper around the blackboard SQLite database."""

    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)
        self._ensure_schema()

    # ── connection helpers ────────────────────────────────────────

    @contextmanager
    def _connect(self) -> Any:
        """Yield a connection with WAL mode and row_factory set."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _ensure_schema(self) -> None:
        """Create tables if they don't exist."""
        schema_sql = SCHEMA_PATH.read_text()
        with self._connect() as conn:
            conn.executescript(schema_sql)

    # ── findings ──────────────────────────────────────────────────

    def add_finding(
        self,
        *,
        agent_name: str,
        severity: str,
        category: str,
        title: str,
        description: str,
        file_path: str | None = None,
        line_number: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Insert a finding. Returns the new finding ID.

        If a finding with the same (agent_name, file_path, title) already
        exists and is still open, updates it instead (idempotent writes).
        """
        now = _utcnow()
        meta_json = json.dumps(metadata) if metadata else None

        with self._connect() as conn:
            # Check for existing open finding with same dedup key
            existing = conn.execute(
                "SELECT id FROM findings "
                "WHERE agent_name = ? AND file_path IS ? AND title = ? "
                "AND status = 'open'",
                (agent_name, file_path, title),
            ).fetchone()

            if existing:
                finding_id = existing["id"]
                conn.execute(
                    "UPDATE findings SET severity = ?, description = ?, "
                    "line_number = ?, metadata = ?, updated_at = ? "
                    "WHERE id = ?",
                    (severity, description, line_number, meta_json, now, finding_id),
                )
                return str(finding_id)

            finding_id = _deterministic_id(agent_name, file_path, title)
            conn.execute(
                "INSERT INTO findings "
                "(id, agent_name, severity, category, title, description, "
                "file_path, line_number, metadata, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    finding_id,
                    agent_name,
                    severity,
                    category,
                    title,
                    description,
                    file_path,
                    line_number,
                    meta_json,
                    now,
                    now,
                ),
            )
            return finding_id

    def get_findings(
        self,
        *,
        status: str | None = None,
        severity: str | None = None,
        agent_name: str | None = None,
        category: str | None = None,
    ) -> list[dict[str, Any]]:
        """Query findings with optional filters."""
        clauses: list[str] = []
        params: list[Any] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        if severity:
            clauses.append("severity = ?")
            params.append(severity)
        if agent_name:
            clauses.append("agent_name = ?")
            params.append(agent_name)
        if category:
            clauses.append("category = ?")
            params.append(category)

        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"SELECT * FROM findings{where} ORDER BY created_at DESC"  # noqa: S608

        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]

    def resolve_finding(
        self, finding_id: str, *, resolved_by: str = "human"
    ) -> None:
        """Mark a finding as resolved."""
        now = _utcnow()
        with self._connect() as conn:
            conn.execute(
                "UPDATE findings SET status = 'resolved', "
                "resolved_at = ?, resolved_by = ?, updated_at = ? "
                "WHERE id = ?",
                (now, resolved_by, now, finding_id),
            )

    # ── task queue ────────────────────────────────────────────────

    def add_task(
        self,
        *,
        source_agent: str,
        title: str,
        description: str,
        priority: int = 3,
        source_finding_id: str | None = None,
    ) -> str:
        """Add a task to the queue. Returns the task ID.

        Uses a deterministic ID derived from (source_agent, title) so
        the same logical task always gets the same ID across runs.
        If a task with the same ID already exists, it is updated
        instead of duplicated (idempotent writes).
        """
        task_id = _deterministic_id(source_agent, title)
        now = _utcnow()
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT id FROM task_queue WHERE id = ?",
                (task_id,),
            ).fetchone()

            if existing:
                conn.execute(
                    "UPDATE task_queue SET description = ?, priority = ?, "
                    "source_finding_id = ?, updated_at = ? "
                    "WHERE id = ?",
                    (description, priority, source_finding_id, now, task_id),
                )
                return task_id

            conn.execute(
                "INSERT INTO task_queue "
                "(id, source_agent, source_finding_id, title, description, "
                "priority, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    task_id,
                    source_agent,
                    source_finding_id,
                    title,
                    description,
                    priority,
                    now,
                    now,
                ),
            )
            return task_id

    def get_tasks(
        self, *, status: str | None = None
    ) -> list[dict[str, Any]]:
        """Query tasks, optionally filtered by status."""
        if status:
            sql = (
                "SELECT * FROM task_queue WHERE status = ? "
                "ORDER BY priority, created_at"
            )
            params: tuple[Any, ...] = (status,)
        else:
            sql = "SELECT * FROM task_queue ORDER BY priority, created_at"
            params = ()

        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]

    def claim_task(self, task_id: str, *, assigned_to: str = "worker") -> bool:
        """Attempt to claim a pending task. Returns True if claimed."""
        now = _utcnow()
        with self._connect() as conn:
            cursor = conn.execute(
                "UPDATE task_queue SET status = 'claimed', "
                "assigned_to = ?, updated_at = ? "
                "WHERE id = ? AND status = 'pending'",
                (assigned_to, now, task_id),
            )
            return cursor.rowcount > 0

    # ── agent log ─────────────────────────────────────────────────

    def log_event(
        self,
        *,
        agent_name: str,
        event_type: str,
        message: str | None = None,
        duration_ms: int | None = None,
        tokens_used: int | None = None,
        model_used: str | None = None,
    ) -> None:
        """Write an event to the agent log."""
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO agent_log "
                "(agent_name, event_type, message, duration_ms, "
                "tokens_used, model_used, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    agent_name,
                    event_type,
                    message,
                    duration_ms,
                    tokens_used,
                    model_used,
                    _utcnow(),
                ),
            )

    def get_agent_health(self) -> list[dict[str, Any]]:
        """Get the last event for each agent."""
        sql = (
            "SELECT agent_name, event_type, message, created_at "
            "FROM agent_log "
            "WHERE id IN ("
            "  SELECT MAX(id) FROM agent_log GROUP BY agent_name"
            ") ORDER BY agent_name"
        )
        with self._connect() as conn:
            rows = conn.execute(sql).fetchall()
            return [dict(r) for r in rows]

    def get_recent_errors(self, *, hours: int = 24) -> list[dict[str, Any]]:
        """Get error events from the last N hours."""
        sql = (
            "SELECT * FROM agent_log "
            "WHERE event_type = 'error' "
            "AND created_at > datetime('now', ?)"
        )
        with self._connect() as conn:
            rows = conn.execute(sql, (f"-{hours} hours",)).fetchall()
            return [dict(r) for r in rows]

    # ── agent config ──────────────────────────────────────────────

    def get_agent_config(self, agent_name: str) -> dict[str, Any] | None:
        """Get config for a specific agent."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM agent_config WHERE agent_name = ?",
                (agent_name,),
            ).fetchone()
            return dict(row) if row else None

    def set_agent_config(
        self,
        agent_name: str,
        *,
        enabled: bool = True,
        schedule_cron: str | None = None,
        model_pref: str = "local",
        max_tokens: int = 4096,
        config_json: dict[str, Any] | None = None,
    ) -> None:
        """Upsert agent configuration."""
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO agent_config "
                "(agent_name, enabled, schedule_cron, model_pref, "
                "max_tokens, config_json) "
                "VALUES (?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(agent_name) DO UPDATE SET "
                "enabled = excluded.enabled, "
                "schedule_cron = excluded.schedule_cron, "
                "model_pref = excluded.model_pref, "
                "max_tokens = excluded.max_tokens, "
                "config_json = excluded.config_json",
                (
                    agent_name,
                    int(enabled),
                    schedule_cron,
                    model_pref,
                    max_tokens,
                    json.dumps(config_json) if config_json else None,
                ),
            )

    def update_last_run(self, agent_name: str) -> None:
        """Record that an agent just ran."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE agent_config SET last_run = ? WHERE agent_name = ?",
                (_utcnow(), agent_name),
            )

    # ── summary helpers (used by Overlord) ────────────────────────

    def summary_stats(self) -> dict[str, Any]:
        """Return high-level stats for the Overlord daily report."""
        with self._connect() as conn:
            findings_by_severity = {}
            for row in conn.execute(
                "SELECT severity, COUNT(*) as cnt FROM findings "
                "WHERE status = 'open' GROUP BY severity"
            ):
                findings_by_severity[row["severity"]] = row["cnt"]

            tasks_by_status = {}
            for row in conn.execute(
                "SELECT status, COUNT(*) as cnt FROM task_queue "
                "GROUP BY status"
            ):
                tasks_by_status[row["status"]] = row["cnt"]

            agent_health = self.get_agent_health()
            recent_errors = self.get_recent_errors(hours=24)

            return {
                "open_findings": findings_by_severity,
                "tasks": tasks_by_status,
                "agent_count": len(agent_health),
                "agents": agent_health,
                "errors_24h": len(recent_errors),
            }
