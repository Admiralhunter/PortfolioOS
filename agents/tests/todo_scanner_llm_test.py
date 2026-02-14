"""Tests for the LLM-powered TODO Scanner agent."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from agents.agents.todo_scanner_llm import TodoScannerLLMAgent
from agents.blackboard.db import Blackboard
from agents.llm.provider import LLMProvider, LLMResponse


class FakeLLM(LLMProvider):
    """LLM that returns a canned triage response."""

    def __init__(self, response: str = "") -> None:
        self._response = response

    def complete(self, *, system: str, user: str, **kwargs: Any) -> LLMResponse:
        return LLMResponse(content=self._response, tokens_used=50, model="fake")


@pytest.fixture()
def scan_dir(tmp_path: Path) -> Path:
    """Create a small repo to scan."""
    src = tmp_path / "src"
    src.mkdir()

    (src / "calc.py").write_text(
        "# TODO: add input validation\n"
        "# FIXME: division by zero when balance is 0\n"
        "def calc(x): return 1/x\n"
    )
    (src / "ui.ts").write_text(
        "// TODO: add loading spinner\n"
        "// NOTE: this is fine as-is\n"
        "export const App = () => null;\n"
    )
    return tmp_path


class TestTodoScannerLLMWithoutLLM:
    """Tests without an LLM — verifies fallback behavior."""

    def test_scans_files_and_extracts_markers(
        self, scan_dir: Path, tmp_path: Path
    ) -> None:
        db_path = tmp_path / "test.db"
        agent = TodoScannerLLMAgent(
            repo_root=scan_dir, db_path=db_path, llm=None,
        )
        agent.llm = None  # force no LLM
        agent.gh = None
        result = agent.run()

        assert result["markers_found"] == 4  # 2 TODO + 1 FIXME + 1 NOTE
        assert result["actionable"] == 3  # excludes NOTE

    def test_fallback_creates_one_group_per_marker(
        self, scan_dir: Path, tmp_path: Path
    ) -> None:
        db_path = tmp_path / "test.db"
        agent = TodoScannerLLMAgent(
            repo_root=scan_dir, db_path=db_path, llm=None,
        )
        agent.llm = None
        agent.gh = None
        result = agent.run()

        # Without LLM, each actionable marker becomes its own group
        assert result["groups"] == 3

    def test_writes_to_blackboard(
        self, scan_dir: Path, tmp_path: Path
    ) -> None:
        db_path = tmp_path / "test.db"
        agent = TodoScannerLLMAgent(
            repo_root=scan_dir, db_path=db_path, llm=None,
        )
        agent.llm = None
        agent.gh = None
        agent.run()

        bb = Blackboard(db_path)
        findings = bb.get_findings(status="open")
        assert len(findings) == 3  # 2 TODO + 1 FIXME (no NOTE)


class TestTodoScannerLLMWithLLM:
    """Tests with a fake LLM — verifies triage behavior."""

    def test_llm_groups_markers(
        self, scan_dir: Path, tmp_path: Path
    ) -> None:
        triage_response = json.dumps({
            "groups": [
                {
                    "title": "Input validation and safety",
                    "priority": "p2",
                    "body": "Multiple markers relate to input safety.",
                    "markers": [0, 1],
                },
                {
                    "title": "UI improvements",
                    "priority": "p3",
                    "body": "Add loading spinner.",
                    "markers": [2],
                },
            ]
        })

        db_path = tmp_path / "test.db"
        agent = TodoScannerLLMAgent(
            repo_root=scan_dir,
            db_path=db_path,
            llm=FakeLLM(triage_response),
        )
        agent.gh = None
        result = agent.run()

        assert result["groups"] == 2

    def test_llm_malformed_response_falls_back(
        self, scan_dir: Path, tmp_path: Path
    ) -> None:
        db_path = tmp_path / "test.db"
        agent = TodoScannerLLMAgent(
            repo_root=scan_dir,
            db_path=db_path,
            llm=FakeLLM("this is not json"),
        )
        agent.gh = None
        result = agent.run()

        # Falls back to one-group-per-marker
        assert result["groups"] == 3

    def test_llm_response_with_code_fences(
        self, scan_dir: Path, tmp_path: Path
    ) -> None:
        inner = '{"title": "T", "priority": "p3", "body": "B", "markers": [0]}'
        response = f"```json\n{{\"groups\": [{inner}]}}\n```"

        db_path = tmp_path / "test.db"
        agent = TodoScannerLLMAgent(
            repo_root=scan_dir,
            db_path=db_path,
            llm=FakeLLM(response),
        )
        agent.gh = None
        result = agent.run()

        assert result["groups"] == 1


class TestGitHubIssueCreation:
    """Verifies that only p1/p2 findings create GitHub issues."""

    def test_no_issues_without_github(
        self, scan_dir: Path, tmp_path: Path
    ) -> None:
        db_path = tmp_path / "test.db"
        agent = TodoScannerLLMAgent(
            repo_root=scan_dir, db_path=db_path, llm=None,
        )
        agent.llm = None
        agent.gh = None
        result = agent.run()

        assert result["issues_created"] == 0
