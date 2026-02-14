"""Tests for the Agent base class."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from agents.base import Agent
from agents.blackboard.db import Blackboard
from agents.llm.provider import LLMProvider, LLMResponse

# -- Fake LLM provider for testing -----------------------------------------

class FakeLLM(LLMProvider):
    """LLM provider that returns canned responses."""

    def __init__(self, response: str = "fake response") -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []

    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> LLMResponse:
        self.calls.append({
            "system": system,
            "user": user,
            "max_tokens": max_tokens,
        })
        return LLMResponse(
            content=self.response,
            tokens_used=100,
            model="fake-model",
        )


# -- Concrete test agent ----------------------------------------------------

class SuccessAgent(Agent):
    name = "test-success"
    use_github = False

    def execute(self) -> dict[str, Any]:
        return {"status": "ok"}


class LLMAgent(Agent):
    name = "test-llm"
    use_github = False

    def execute(self) -> dict[str, Any]:
        result = self.reason(system="sys", user="question")
        return {"answer": result}


class FailAgent(Agent):
    name = "test-fail"
    use_github = False

    def execute(self) -> dict[str, Any]:
        raise ValueError("intentional failure")


# -- Tests ------------------------------------------------------------------

class TestAgentLifecycle:
    def test_run_logs_start_and_complete(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        agent = SuccessAgent(db_path=db_path)
        result = agent.run()

        assert result == {"status": "ok"}

        # Verify blackboard has start + complete events
        bb = Blackboard(db_path)
        health = bb.get_agent_health()
        names = [h["agent_name"] for h in health]
        assert "test-success" in names

    def test_run_logs_error_on_failure(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        agent = FailAgent(db_path=db_path)

        with pytest.raises(ValueError, match="intentional failure"):
            agent.run()

        # Error should be logged
        bb = Blackboard(db_path)
        errors = bb.get_recent_errors(hours=1)
        assert len(errors) >= 1
        assert "intentional failure" in errors[0]["message"]

    def test_run_tracks_duration(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        agent = SuccessAgent(db_path=db_path)
        agent.run()

        bb = Blackboard(db_path)
        with bb._connect() as conn:
            row = conn.execute(
                "SELECT duration_ms FROM agent_log "
                "WHERE agent_name = 'test-success' AND event_type = 'complete'"
            ).fetchone()
        assert row is not None
        assert row["duration_ms"] >= 0


class TestAgentReason:
    def test_reason_calls_llm(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        fake_llm = FakeLLM(response="42")
        agent = LLMAgent(db_path=db_path, llm=fake_llm)
        result = agent.run()

        assert result == {"answer": "42"}
        assert len(fake_llm.calls) == 1
        assert fake_llm.calls[0]["system"] == "sys"
        assert fake_llm.calls[0]["user"] == "question"

    def test_reason_tracks_tokens(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        fake_llm = FakeLLM()
        agent = LLMAgent(db_path=db_path, llm=fake_llm)
        agent.run()

        assert agent._total_tokens == 100

    def test_reason_without_llm_raises(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        agent = LLMAgent(db_path=db_path, llm=None)
        agent.llm = None  # explicitly disable

        with pytest.raises(RuntimeError, match="no LLM provider"):
            agent.run()


class TestAgentReasonOrSkip:
    def test_with_llm(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        fake_llm = FakeLLM(response="from-llm")
        agent = SuccessAgent(db_path=db_path, llm=fake_llm)
        result = agent.reason_or_skip("sys", "user", fallback="default")
        assert result == "from-llm"

    def test_without_llm_returns_fallback(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        agent = SuccessAgent(db_path=db_path, llm=None)
        agent.llm = None
        result = agent.reason_or_skip("sys", "user", fallback="default")
        assert result == "default"


class TestAgentGitHubIntegration:
    def test_no_github_returns_none(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        agent = SuccessAgent(db_path=db_path)
        agent.gh = None

        result = agent.create_finding_issue("title", "body")
        assert result is None

    def test_claim_issue_without_github(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        agent = SuccessAgent(db_path=db_path)
        agent.gh = None

        assert agent.claim_issue(1) is False
