"""Tests for the blackboard database wrapper."""

import sqlite3
from pathlib import Path

import pytest

from agents.blackboard.db import Blackboard


@pytest.fixture
def bb(tmp_path: Path) -> Blackboard:
    """Create a fresh blackboard database in a temp directory."""
    return Blackboard(tmp_path / "test.db")


class TestSchema:
    def test_creates_tables(self, bb: Blackboard) -> None:
        with bb._connect() as conn:
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
        assert "findings" in tables
        assert "task_queue" in tables
        assert "agent_log" in tables
        assert "file_hashes" in tables
        assert "dependency_state" in tables
        assert "agent_config" in tables

    def test_idempotent_schema_creation(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        Blackboard(db_path)
        bb2 = Blackboard(db_path)
        # Second creation should not raise
        with bb2._connect() as conn:
            tables = conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
            ).fetchone()
        assert tables[0] >= 6


class TestFindings:
    def test_add_and_retrieve(self, bb: Blackboard) -> None:
        fid = bb.add_finding(
            agent_name="test_agent",
            severity="high",
            category="test",
            title="Test finding",
            description="A test finding",
            file_path="foo.py",
            line_number=42,
        )
        assert fid
        findings = bb.get_findings(agent_name="test_agent")
        assert len(findings) == 1
        assert findings[0]["title"] == "Test finding"
        assert findings[0]["severity"] == "high"
        assert findings[0]["file_path"] == "foo.py"
        assert findings[0]["line_number"] == 42

    def test_idempotent_upsert(self, bb: Blackboard) -> None:
        fid1 = bb.add_finding(
            agent_name="test",
            severity="medium",
            category="test",
            title="Duplicate",
            description="First version",
            file_path="bar.py",
        )
        fid2 = bb.add_finding(
            agent_name="test",
            severity="high",
            category="test",
            title="Duplicate",
            description="Updated version",
            file_path="bar.py",
        )
        assert fid1 == fid2
        findings = bb.get_findings(agent_name="test")
        assert len(findings) == 1
        assert findings[0]["severity"] == "high"
        assert findings[0]["description"] == "Updated version"

    def test_resolve_finding(self, bb: Blackboard) -> None:
        fid = bb.add_finding(
            agent_name="test",
            severity="low",
            category="test",
            title="To resolve",
            description="Will be resolved",
        )
        bb.resolve_finding(fid, resolved_by="human")
        findings = bb.get_findings(status="resolved")
        assert len(findings) == 1
        assert findings[0]["resolved_by"] == "human"

    def test_filter_by_severity(self, bb: Blackboard) -> None:
        bb.add_finding(
            agent_name="a", severity="critical", category="sec",
            title="Critical", description="d",
        )
        bb.add_finding(
            agent_name="a", severity="low", category="sec",
            title="Low", description="d",
        )
        critical = bb.get_findings(severity="critical")
        assert len(critical) == 1
        assert critical[0]["title"] == "Critical"

    def test_filter_by_category(self, bb: Blackboard) -> None:
        bb.add_finding(
            agent_name="a", severity="medium", category="todo",
            title="T1", description="d",
        )
        bb.add_finding(
            agent_name="a", severity="medium", category="security",
            title="T2", description="d",
        )
        todos = bb.get_findings(category="todo")
        assert len(todos) == 1

    def test_severity_constraint(self, bb: Blackboard) -> None:
        with pytest.raises(sqlite3.IntegrityError):
            bb.add_finding(
                agent_name="a", severity="invalid", category="test",
                title="Bad", description="d",
            )


    def test_deterministic_ids_across_fresh_databases(
        self, tmp_path: Path
    ) -> None:
        """Same finding produces the same ID in two independent databases."""
        db1 = Blackboard(tmp_path / "db1.db")
        db2 = Blackboard(tmp_path / "db2.db")

        fid1 = db1.add_finding(
            agent_name="scanner",
            severity="high",
            category="todo",
            title="FIXME: broken calc",
            description="Details",
            file_path="src/calc.py",
            line_number=10,
        )
        fid2 = db2.add_finding(
            agent_name="scanner",
            severity="high",
            category="todo",
            title="FIXME: broken calc",
            description="Details",
            file_path="src/calc.py",
            line_number=10,
        )
        assert fid1 == fid2

    def test_different_findings_get_different_ids(self, bb: Blackboard) -> None:
        fid1 = bb.add_finding(
            agent_name="scanner",
            severity="high",
            category="todo",
            title="FIXME: first",
            description="d",
            file_path="a.py",
        )
        fid2 = bb.add_finding(
            agent_name="scanner",
            severity="high",
            category="todo",
            title="FIXME: second",
            description="d",
            file_path="a.py",
        )
        assert fid1 != fid2


class TestTaskQueue:
    def test_add_and_list(self, bb: Blackboard) -> None:
        tid = bb.add_task(
            source_agent="scanner",
            title="Fix something",
            description="Details here",
            priority=2,
        )
        assert tid
        tasks = bb.get_tasks(status="pending")
        assert len(tasks) == 1
        assert tasks[0]["title"] == "Fix something"
        assert tasks[0]["priority"] == 2

    def test_claim_task(self, bb: Blackboard) -> None:
        tid = bb.add_task(
            source_agent="scanner",
            title="Claim me",
            description="d",
        )
        assert bb.claim_task(tid, assigned_to="worker")
        tasks = bb.get_tasks(status="claimed")
        assert len(tasks) == 1
        assert tasks[0]["assigned_to"] == "worker"

    def test_claim_already_claimed(self, bb: Blackboard) -> None:
        tid = bb.add_task(
            source_agent="scanner",
            title="Double claim",
            description="d",
        )
        assert bb.claim_task(tid)
        assert not bb.claim_task(tid)  # second claim fails

    def test_priority_ordering(self, bb: Blackboard) -> None:
        bb.add_task(source_agent="a", title="Low", description="d", priority=5)
        bb.add_task(source_agent="a", title="High", description="d", priority=1)
        bb.add_task(source_agent="a", title="Med", description="d", priority=3)
        tasks = bb.get_tasks()
        titles = [t["title"] for t in tasks]
        assert titles == ["High", "Med", "Low"]

    def test_idempotent_task_add(self, bb: Blackboard) -> None:
        """Adding the same task twice should update, not duplicate."""
        tid1 = bb.add_task(
            source_agent="scanner",
            title="Fix it",
            description="v1",
            priority=3,
        )
        tid2 = bb.add_task(
            source_agent="scanner",
            title="Fix it",
            description="v2",
            priority=2,
        )
        assert tid1 == tid2
        tasks = bb.get_tasks()
        assert len(tasks) == 1
        assert tasks[0]["description"] == "v2"
        assert tasks[0]["priority"] == 2

    def test_deterministic_task_ids_across_databases(
        self, tmp_path: Path
    ) -> None:
        """Same task produces the same ID in independent databases."""
        db1 = Blackboard(tmp_path / "db1.db")
        db2 = Blackboard(tmp_path / "db2.db")

        tid1 = db1.add_task(
            source_agent="scanner", title="Fix it", description="d",
        )
        tid2 = db2.add_task(
            source_agent="scanner", title="Fix it", description="d",
        )
        assert tid1 == tid2


class TestAgentLog:
    def test_log_and_health(self, bb: Blackboard) -> None:
        bb.log_event(agent_name="scanner", event_type="start")
        bb.log_event(agent_name="scanner", event_type="complete", message="ok")
        bb.log_event(agent_name="overlord", event_type="start")
        health = bb.get_agent_health()
        assert len(health) == 2
        names = {h["agent_name"] for h in health}
        assert names == {"scanner", "overlord"}

    def test_recent_errors(self, bb: Blackboard) -> None:
        bb.log_event(agent_name="bad_agent", event_type="error", message="boom")
        errors = bb.get_recent_errors(hours=1)
        assert len(errors) == 1
        assert errors[0]["message"] == "boom"


class TestAgentConfig:
    def test_set_and_get(self, bb: Blackboard) -> None:
        bb.set_agent_config("scanner", schedule_cron="0 6 * * *")
        cfg = bb.get_agent_config("scanner")
        assert cfg is not None
        assert cfg["schedule_cron"] == "0 6 * * *"
        assert cfg["enabled"] == 1

    def test_upsert(self, bb: Blackboard) -> None:
        bb.set_agent_config("scanner", enabled=True)
        bb.set_agent_config("scanner", enabled=False)
        cfg = bb.get_agent_config("scanner")
        assert cfg is not None
        assert cfg["enabled"] == 0

    def test_missing_agent(self, bb: Blackboard) -> None:
        assert bb.get_agent_config("nonexistent") is None


class TestSummaryStats:
    def test_empty_db(self, bb: Blackboard) -> None:
        stats = bb.summary_stats()
        assert stats["open_findings"] == {}
        assert stats["tasks"] == {}
        assert stats["agent_count"] == 0
        assert stats["errors_24h"] == 0

    def test_with_data(self, bb: Blackboard) -> None:
        bb.add_finding(
            agent_name="a", severity="high", category="test",
            title="F1", description="d",
        )
        bb.add_finding(
            agent_name="a", severity="high", category="test",
            title="F2", description="d",
        )
        bb.add_task(source_agent="a", title="T1", description="d")
        bb.log_event(agent_name="a", event_type="complete")
        stats = bb.summary_stats()
        assert stats["open_findings"]["high"] == 2
        assert stats["tasks"]["pending"] == 1
        assert stats["agent_count"] == 1
