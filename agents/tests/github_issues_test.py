"""Tests for the GitHub Issues API wrapper."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, ClassVar

import pytest

from agents.github.issues import GitHubIssues, _detect_repo

# -- Fake GitHub API server -------------------------------------------------

class FakeGitHubHandler(BaseHTTPRequestHandler):
    """Minimal handler that mimics the GitHub REST API."""

    # Class-level state shared across requests
    issues: ClassVar[list[dict[str, Any]]] = []
    comments: ClassVar[dict[int, list[dict[str, Any]]]] = {}
    next_id = 1

    def do_GET(self) -> None:
        # Strip query string if present, then trailing slash
        path = self.path.split("?")[0].rstrip("/")

        # GET /repos/owner/repo/issues
        if path.endswith("/issues"):
            self._respond(200, self.issues)
            return

        # GET /repos/owner/repo/issues/123
        parts = path.split("/")
        if len(parts) >= 2 and parts[-2] == "issues" and parts[-1].isdigit():
            num = int(parts[-1])
            for iss in self.issues:
                if iss["number"] == num:
                    self._respond(200, iss)
                    return
            self._respond(404, {"message": "Not Found"})
            return

        # GET /repos/owner/repo/issues/123/comments
        if "comments" in parts:
            num = int(parts[parts.index("comments") - 1])
            self._respond(200, self.comments.get(num, []))
            return

        self._respond(404, {"message": "Not Found"})

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}
        path = self.path.rstrip("/")

        # POST /repos/owner/repo/issues
        if path.endswith("/issues"):
            issue = {
                "number": self.next_id,
                "title": body.get("title", ""),
                "body": body.get("body", ""),
                "labels": [{"name": lab} for lab in body.get("labels", [])],
                "state": "open",
            }
            FakeGitHubHandler.next_id += 1
            self.issues.append(issue)
            self._respond(201, issue)
            return

        # POST /repos/owner/repo/issues/123/comments
        parts = path.split("/")
        if "comments" in parts:
            num = int(parts[parts.index("comments") - 1])
            comment = {"id": self.next_id, "body": body.get("body", "")}
            FakeGitHubHandler.next_id += 1
            self.comments.setdefault(num, []).append(comment)
            self._respond(201, comment)
            return

        # POST /repos/owner/repo/issues/123/labels
        if "labels" in parts:
            num = int(parts[parts.index("labels") - 1])
            new_labels = [{"name": lab} for lab in body.get("labels", [])]
            self._respond(200, new_labels)
            return

        # POST /repos/owner/repo/issues/123/assignees
        if "assignees" in parts:
            num = int(parts[parts.index("assignees") - 1])
            self._respond(200, {"number": num, "assignees": body.get("assignees", [])})
            return

        self._respond(404, {"message": "Not Found"})

    def do_PUT(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}
        path = self.path.rstrip("/")

        # PUT /repos/owner/repo/issues/123/labels
        if "labels" in path:
            new_labels = [{"name": lab} for lab in body.get("labels", [])]
            self._respond(200, new_labels)
            return

        self._respond(404, {"message": "Not Found"})

    def do_PATCH(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}
        path = self.path.rstrip("/")
        parts = path.split("/")

        # PATCH /repos/owner/repo/issues/123
        if len(parts) >= 2 and parts[-2] == "issues" and parts[-1].isdigit():
            num = int(parts[-1])
            for iss in self.issues:
                if iss["number"] == num:
                    iss.update(body)
                    if "labels" in body:
                        iss["labels"] = [{"name": lab} for lab in body["labels"]]
                    self._respond(200, iss)
                    return
            self._respond(404, {"message": "Not Found"})
            return

        self._respond(404, {"message": "Not Found"})

    def do_DELETE(self) -> None:
        self._respond(200, {})

    def _respond(self, code: int, body: Any) -> None:
        payload = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *_args: Any) -> None:
        pass


@pytest.fixture(autouse=True)
def _reset_fake_state():
    """Reset the fake server state between tests."""
    FakeGitHubHandler.issues = []
    FakeGitHubHandler.comments = {}
    FakeGitHubHandler.next_id = 1
    yield


@pytest.fixture()
def fake_github():
    """Start a fake GitHub API server and return a configured client."""
    server = HTTPServer(("127.0.0.1", 0), FakeGitHubHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    client = GitHubIssues(repo="test/repo", token="fake-token")
    client.api_base = f"http://127.0.0.1:{port}/repos/test/repo"
    yield client
    server.shutdown()


# -- _detect_repo tests -----------------------------------------------------

class TestDetectRepo:
    def test_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
        assert _detect_repo() == "owner/repo"

    def test_no_env_no_git_raises(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Any,
    ) -> None:
        monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
        monkeypatch.chdir(tmp_path)
        with pytest.raises(OSError):
            _detect_repo()


# -- GitHubIssues CRUD tests ------------------------------------------------

class TestCreateIssue:
    def test_basic(self, fake_github: GitHubIssues) -> None:
        issue = fake_github.create_issue(
            title="Test issue",
            body="Body text",
            labels=["agent:test", "priority:p3"],
        )
        assert issue["number"] == 1
        assert issue["title"] == "Test issue"
        assert issue["body"] == "Body text"

    def test_multiple(self, fake_github: GitHubIssues) -> None:
        fake_github.create_issue(title="First", body="")
        issue2 = fake_github.create_issue(title="Second", body="")
        assert issue2["number"] == 2


class TestListIssues:
    def test_empty(self, fake_github: GitHubIssues) -> None:
        issues = fake_github.list_issues()
        assert issues == []

    def test_with_issues(self, fake_github: GitHubIssues) -> None:
        fake_github.create_issue(title="A", body="")
        fake_github.create_issue(title="B", body="")
        issues = fake_github.list_issues()
        assert len(issues) == 2


class TestGetIssue:
    def test_existing(self, fake_github: GitHubIssues) -> None:
        fake_github.create_issue(title="Find me", body="here")
        issue = fake_github.get_issue(1)
        assert issue["title"] == "Find me"


class TestComments:
    def test_add_and_list(self, fake_github: GitHubIssues) -> None:
        fake_github.create_issue(title="I", body="")
        fake_github.add_comment(1, "Hello from agent")
        comments = fake_github.list_comments(1)
        assert len(comments) == 1
        assert comments[0]["body"] == "Hello from agent"


class TestLabels:
    def test_update_labels(self, fake_github: GitHubIssues) -> None:
        fake_github.create_issue(title="I", body="")
        result = fake_github.update_labels(1, ["status:spec-ready"])
        assert result[0]["name"] == "status:spec-ready"

    def test_add_labels(self, fake_github: GitHubIssues) -> None:
        fake_github.create_issue(title="I", body="")
        result = fake_github.add_labels(1, ["priority:p1"])
        assert result[0]["name"] == "priority:p1"

    def test_remove_label_idempotent(self, fake_github: GitHubIssues) -> None:
        fake_github.create_issue(title="I", body="")
        # Should not raise even if label doesn't exist
        fake_github.remove_label(1, "nonexistent")


# -- High-level helpers tests -----------------------------------------------

class TestFindIssueByTitle:
    def test_found(self, fake_github: GitHubIssues) -> None:
        fake_github.create_issue(title="Exact Match", body="")
        result = fake_github.find_issue_by_title("Exact Match")
        assert result is not None
        assert result["title"] == "Exact Match"

    def test_not_found(self, fake_github: GitHubIssues) -> None:
        fake_github.create_issue(title="Something Else", body="")
        result = fake_github.find_issue_by_title("Not Here")
        assert result is None


class TestCreateOrUpdateFinding:
    def test_creates_new(self, fake_github: GitHubIssues) -> None:
        result = fake_github.create_or_update_finding(
            agent_name="test-agent",
            title="New finding",
            body="Details",
            priority="p2",
        )
        assert result["title"] == "New finding"

    def test_updates_existing(self, fake_github: GitHubIssues) -> None:
        fake_github.create_or_update_finding(
            agent_name="test-agent",
            title="Dup finding",
            body="v1",
        )
        result = fake_github.create_or_update_finding(
            agent_name="test-agent",
            title="Dup finding",
            body="v2",
        )
        # Should update, not create a second issue
        assert result["body"] == "v2"


class TestCreateTaskFromFinding:
    def test_basic(self, fake_github: GitHubIssues) -> None:
        finding = fake_github.create_issue(title="Bug", body="found it")
        task = fake_github.create_task_from_finding(
            finding_issue_number=finding["number"],
            title="Fix the bug",
            spec_body="Do this...",
            priority="p2",
            target_agent="worker",
        )
        assert task["title"] == "Fix the bug"
        assert "#1" in task["body"]  # references finding
