"""GitHub Issues API wrapper for agent coordination.

Uses only stdlib (urllib) — no external dependencies.  All agents
use this module to create findings, claim tasks, and communicate
via GitHub Issues instead of (or in addition to) the local blackboard.

Authentication uses the ``GITHUB_TOKEN`` environment variable, which
is automatically available in GitHub Actions and Claude Code sessions.

Usage::

    from agents.github.issues import GitHubIssues

    gh = GitHubIssues()  # auto-detects repo from GITHUB_REPOSITORY or git remote

    # Create a finding
    issue = gh.create_issue(
        title="FIXME: division by zero in withdrawal calc",
        body="Found in src/calc.py:42 ...",
        labels=["agent:todo-scanner", "type:finding", "priority:p2"],
    )

    # Agent claims work by labelling + commenting
    gh.update_labels(issue["number"], ["status:in-progress", "agent:worker"])
    gh.add_comment(issue["number"], "Worker agent claiming this task.")
"""

from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.request
from typing import Any


def _detect_repo() -> str:
    """Detect the GitHub owner/repo from environment or git remote."""
    # GitHub Actions sets this automatically
    repo = os.environ.get("GITHUB_REPOSITORY")
    if repo:
        return repo

    # Fallback: parse git remote
    try:
        url = subprocess.check_output(
            ["git", "remote", "get-url", "origin"],
            text=True,
            timeout=5,
        ).strip()
    except (subprocess.SubprocessError, FileNotFoundError) as exc:
        raise OSError(
            "Cannot detect repo. Set GITHUB_REPOSITORY=owner/repo "
            "or ensure a git remote named 'origin' exists."
        ) from exc

    # Handle SSH: git@github.com:owner/repo.git
    if url.startswith("git@"):
        path = url.split(":", 1)[1]
        return path.removesuffix(".git")

    # Handle HTTPS: https://github.com/owner/repo.git
    # Also handles proxy URLs: http://proxy@host/git/owner/repo
    for prefix in ("https://github.com/", "http://github.com/"):
        if url.startswith(prefix):
            return url[len(prefix):].removesuffix(".git").removesuffix("/")

    # Proxy URL fallback: take last two path segments as owner/repo
    parts = url.rstrip("/").split("/")
    if len(parts) >= 2:
        return f"{parts[-2]}/{parts[-1]}".removesuffix(".git")

    raise OSError(f"Cannot parse repo from remote URL: {url}")


class GitHubIssues:
    """Thin wrapper around the GitHub REST API for Issues."""

    def __init__(
        self,
        repo: str | None = None,
        token: str | None = None,
    ) -> None:
        self.repo = repo or _detect_repo()
        self.token = token or os.environ.get("GITHUB_TOKEN", "")
        self.api_base = f"https://api.github.com/repos/{self.repo}"

    # -- low-level request helper -------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Make an authenticated request to the GitHub API."""
        url = f"{self.api_base}/{path}"
        data = json.dumps(body).encode() if body else None

        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Accept", "application/vnd.github+json")
        if self.token:
            req.add_header("Authorization", f"Bearer {self.token}")
        if data:
            req.add_header("Content-Type", "application/json")

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode(errors="replace")
            raise RuntimeError(
                f"GitHub API {method} {path} returned {exc.code}: {error_body}"
            ) from exc

    # -- Issues CRUD --------------------------------------------------------

    def create_issue(
        self,
        title: str,
        body: str,
        labels: list[str] | None = None,
        assignees: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a new GitHub issue.

        Returns the full issue object from the API.
        """
        payload: dict[str, Any] = {"title": title, "body": body}
        if labels:
            payload["labels"] = labels
        if assignees:
            payload["assignees"] = assignees
        result = self._request("POST", "issues", payload)
        return result  # type: ignore[return-value]

    def get_issue(self, issue_number: int) -> dict[str, Any]:
        """Fetch a single issue by number."""
        result = self._request("GET", f"issues/{issue_number}")
        return result  # type: ignore[return-value]

    def list_issues(
        self,
        labels: str | None = None,
        state: str = "open",
        per_page: int = 30,
    ) -> list[dict[str, Any]]:
        """List issues, optionally filtered by labels.

        Args:
            labels: Comma-separated label names (e.g. "status:needs-triage,type:task").
            state: "open", "closed", or "all".
            per_page: Results per page (max 100).
        """
        query = f"issues?state={state}&per_page={per_page}"
        if labels:
            query += f"&labels={labels}"
        result = self._request("GET", query)
        return result  # type: ignore[return-value]

    def close_issue(self, issue_number: int) -> dict[str, Any]:
        """Close an issue."""
        result = self._request(
            "PATCH", f"issues/{issue_number}", {"state": "closed"}
        )
        return result  # type: ignore[return-value]

    # -- Labels -------------------------------------------------------------

    def update_labels(
        self, issue_number: int, labels: list[str]
    ) -> list[dict[str, Any]]:
        """Replace all labels on an issue."""
        result = self._request(
            "PUT", f"issues/{issue_number}/labels", {"labels": labels}
        )
        return result  # type: ignore[return-value]

    def add_labels(
        self, issue_number: int, labels: list[str]
    ) -> list[dict[str, Any]]:
        """Add labels to an issue (without removing existing ones)."""
        result = self._request(
            "POST", f"issues/{issue_number}/labels", {"labels": labels}
        )
        return result  # type: ignore[return-value]

    def remove_label(self, issue_number: int, label: str) -> None:
        """Remove a single label from an issue (idempotent)."""
        import contextlib

        with contextlib.suppress(RuntimeError):
            self._request("DELETE", f"issues/{issue_number}/labels/{label}")

    # -- Comments -----------------------------------------------------------

    def add_comment(
        self, issue_number: int, body: str
    ) -> dict[str, Any]:
        """Add a comment to an issue."""
        result = self._request(
            "POST", f"issues/{issue_number}/comments", {"body": body}
        )
        return result  # type: ignore[return-value]

    def list_comments(
        self, issue_number: int, per_page: int = 30
    ) -> list[dict[str, Any]]:
        """List comments on an issue."""
        result = self._request(
            "GET", f"issues/{issue_number}/comments?per_page={per_page}"
        )
        return result  # type: ignore[return-value]

    # -- Assignees ----------------------------------------------------------

    def assign(
        self, issue_number: int, assignees: list[str]
    ) -> dict[str, Any]:
        """Add assignees to an issue."""
        result = self._request(
            "POST",
            f"issues/{issue_number}/assignees",
            {"assignees": assignees},
        )
        return result  # type: ignore[return-value]

    # -- Search (for deduplication) -----------------------------------------

    def find_issue_by_title(
        self, title: str, labels: str | None = None
    ) -> dict[str, Any] | None:
        """Find an open issue with an exact title match.

        Used for idempotent issue creation — agents check before creating.
        Returns the issue dict if found, None otherwise.
        """
        issues = self.list_issues(labels=labels, per_page=100)
        for issue in issues:
            if issue["title"] == title:
                return issue
        return None

    # -- High-level helpers for agents --------------------------------------

    def create_or_update_finding(
        self,
        *,
        agent_name: str,
        title: str,
        body: str,
        priority: str = "p3",
        extra_labels: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a finding issue, or update it if one with the same title exists.

        This is the idempotent entry point agents should use.
        """
        labels = [f"agent:{agent_name}", "type:finding", f"priority:{priority}"]
        if extra_labels:
            labels.extend(extra_labels)

        label_filter = f"agent:{agent_name},type:finding"
        existing = self.find_issue_by_title(title, labels=label_filter)

        if existing:
            # Update the body with fresh data
            result = self._request(
                "PATCH",
                f"issues/{existing['number']}",
                {"body": body, "labels": labels},
            )
            return result  # type: ignore[return-value]

        return self.create_issue(title=title, body=body, labels=labels)

    def create_task_from_finding(
        self,
        *,
        finding_issue_number: int,
        title: str,
        spec_body: str,
        priority: str = "p3",
        target_agent: str = "worker",
    ) -> dict[str, Any]:
        """Create a task issue linked to a finding.

        The task body includes a reference back to the finding issue.
        """
        body = (
            f"## Task\n\n{spec_body}\n\n"
            f"---\n"
            f"_Source: #{finding_issue_number}_"
        )
        labels = [
            f"agent:{target_agent}",
            "type:task",
            f"priority:{priority}",
            "status:needs-triage",
        ]
        return self.create_issue(title=title, body=body, labels=labels)
