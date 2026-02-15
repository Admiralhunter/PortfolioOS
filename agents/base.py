"""Base class for LLM-powered agents.

Every agent inherits from ``Agent`` and overrides ``execute()``.
The base class handles:

- LLM provider initialisation (local or cloud)
- GitHub Issues integration (optional, for CI-based agents)
- Blackboard logging (start / heartbeat / complete / error events)
- Timing and token tracking

Usage::

    class MyAgent(Agent):
        name = "my-agent"
        model_pref = "claude-sonnet"

        def execute(self) -> dict:
            analysis = self.reason(
                system="You are a code reviewer.",
                user="Review this function...",
            )
            self.create_finding_issue(
                title="Bug in calc.py",
                body=analysis,
                priority="p2",
            )
            return {"reviewed": 1}
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

# Allow running from repo root
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from agents.blackboard.db import Blackboard  # noqa: E402
from agents.github.issues import GitHubIssues  # noqa: E402
from agents.llm.provider import LLMProvider, LLMResponse, get_provider  # noqa: E402


class Agent:
    """Base class for all LLM-powered agents.

    Subclasses must set ``name`` and override ``execute()``.
    Optionally set ``model_pref`` to choose the LLM backend.

    Attributes:
        name: Unique agent identifier (e.g. "todo-scanner", "pm").
        model_pref: LLM backend preference.  One of "local",
            "claude-sonnet", "claude-opus", "openai".
            Defaults to "local" (LM Studio).
        use_github: Whether to initialise the GitHub Issues client.
            Defaults to True but degrades gracefully if GITHUB_TOKEN
            is not set.
    """

    name: str = "unnamed-agent"
    model_pref: str = "local"
    use_github: bool = True

    def __init__(
        self,
        *,
        db_path: Path | None = None,
        llm: LLMProvider | None = None,
        github: GitHubIssues | None = None,
    ) -> None:
        self.bb = Blackboard(db_path) if db_path else Blackboard()

        # LLM — allow injection for testing, otherwise use preference
        if llm is not None:
            self.llm: LLMProvider | None = llm
        else:
            try:
                self.llm = get_provider(self.model_pref)
            except (OSError, ValueError):
                # No API key or LM Studio not running — agent can still
                # do non-LLM work (regex scanning, etc.)
                self.llm = None

        # GitHub Issues — optional, for agents running in CI
        if github is not None:
            self.gh: GitHubIssues | None = github
        elif self.use_github:
            try:
                self.gh = GitHubIssues()
            except OSError:
                self.gh = None
        else:
            self.gh = None

        self._total_tokens = 0

    # -- lifecycle ----------------------------------------------------------

    def run(self) -> dict[str, Any]:
        """Run the agent with full lifecycle management.

        Logs start/complete/error to the blackboard, tracks duration
        and token spend.  Calls ``self.execute()`` which subclasses
        implement.

        Returns:
            The dict returned by ``execute()``.
        """
        self.bb.log_event(agent_name=self.name, event_type="start")
        start = time.monotonic()

        try:
            result = self.execute()
            elapsed_ms = int((time.monotonic() - start) * 1000)
            self.bb.log_event(
                agent_name=self.name,
                event_type="complete",
                message=str(result),
                duration_ms=elapsed_ms,
                tokens_used=self._total_tokens or None,
                model_used=self.model_pref,
            )
            self.bb.update_last_run(self.name)
            return result

        except Exception as exc:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            self.bb.log_event(
                agent_name=self.name,
                event_type="error",
                message=f"{type(exc).__name__}: {exc}",
                duration_ms=elapsed_ms,
            )
            raise

    def execute(self) -> dict[str, Any]:
        """Override in subclasses.  Do the actual agent work.

        Returns:
            A summary dict (contents are agent-specific).
        """
        raise NotImplementedError(
            f"{type(self).__name__} must implement execute()"
        )

    # -- LLM helpers --------------------------------------------------------

    def reason(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> str:
        """Call the LLM for reasoning and return the text response.

        Also logs a heartbeat with token usage to the blackboard.

        Raises:
            RuntimeError: If no LLM provider is available.
        """
        if self.llm is None:
            raise RuntimeError(
                f"Agent '{self.name}' has no LLM provider. "
                f"Set {self.model_pref} credentials or start LM Studio."
            )

        resp: LLMResponse = self.llm.complete(
            system=system,
            user=user,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        self._total_tokens += resp.tokens_used

        self.bb.log_event(
            agent_name=self.name,
            event_type="heartbeat",
            message=f"LLM call: {resp.tokens_used} tokens",
            tokens_used=resp.tokens_used,
            model_used=resp.model,
        )
        return resp.content

    def reason_or_skip(
        self,
        system: str,
        user: str,
        *,
        fallback: str = "",
        **kwargs: Any,
    ) -> str:
        """Like ``reason()`` but returns *fallback* if no LLM is available.

        Useful for agents that can do basic work without an LLM
        (e.g. regex scanning) but produce richer output with one.

        Returns the fallback when:
        - No LLM provider is configured (``self.llm is None``)
        - The LLM endpoint is unreachable (connection refused, timeout, etc.)
        """
        if self.llm is None:
            return fallback
        try:
            return self.reason(system, user, **kwargs)
        except OSError:
            # OSError covers ConnectionRefusedError, urllib.error.URLError,
            # TimeoutError, and other network-related failures that indicate
            # the LLM endpoint is not reachable.
            return fallback

    # -- GitHub Issues helpers ----------------------------------------------

    def create_finding_issue(
        self,
        title: str,
        body: str,
        priority: str = "p3",
        extra_labels: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """Create (or update) a finding issue on GitHub.

        Returns the issue dict, or None if GitHub is not available.
        """
        if self.gh is None:
            return None
        return self.gh.create_or_update_finding(
            agent_name=self.name,
            title=title,
            body=body,
            priority=priority,
            extra_labels=extra_labels,
        )

    def comment_on_issue(
        self, issue_number: int, body: str
    ) -> dict[str, Any] | None:
        """Post a comment on a GitHub issue.

        Returns the comment dict, or None if GitHub is not available.
        """
        if self.gh is None:
            return None
        return self.gh.add_comment(issue_number, body)

    def claim_issue(
        self, issue_number: int
    ) -> bool:
        """Claim an issue by labelling it in-progress.

        Returns True if successfully claimed, False if GitHub unavailable.
        """
        if self.gh is None:
            return False
        self.gh.add_labels(issue_number, ["status:in-progress"])
        self.gh.remove_label(issue_number, "status:needs-triage")
        self.gh.remove_label(issue_number, "status:spec-ready")
        return True
