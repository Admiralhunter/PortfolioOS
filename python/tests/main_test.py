"""Tests for the sidecar entry point (dispatch and message loop)."""

from __future__ import annotations

import json
from io import StringIO
from unittest.mock import patch

import pytest
from portfolioos.main import dispatch, main


class TestDispatch:
    """Tests for the dispatch function."""

    def test_unknown_method_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown method"):
            dispatch("nonexistent.method", {})

    def test_unknown_method_includes_name(self) -> None:
        with pytest.raises(ValueError, match=r"foo\.bar"):
            dispatch("foo.bar", {})


class TestMain:
    """Tests for the stdin/stdout message loop."""

    def test_valid_request_returns_response(self) -> None:
        request = json.dumps({"id": "1", "method": "ping", "params": {}})
        stdin = StringIO(request + "\n")
        stdout = StringIO()

        with (
            patch("sys.stdin", stdin),
            patch("sys.stdout", stdout),
            patch(
                "portfolioos.main.dispatch",
                return_value={"status": "ok"},
            ),
        ):
            main()

        response = json.loads(stdout.getvalue().strip())
        assert response["id"] == "1"
        assert response["result"] == {"status": "ok"}

    def test_invalid_json_returns_error(self) -> None:
        stdin = StringIO("not valid json\n")
        stdout = StringIO()

        with patch("sys.stdin", stdin), patch("sys.stdout", stdout):
            main()

        response = json.loads(stdout.getvalue().strip())
        assert response["id"] == "unknown"
        assert "error" in response

    def test_missing_method_returns_error(self) -> None:
        request = json.dumps({"id": "2"})
        stdin = StringIO(request + "\n")
        stdout = StringIO()

        with patch("sys.stdin", stdin), patch("sys.stdout", stdout):
            main()

        response = json.loads(stdout.getvalue().strip())
        assert response["id"] == "2"
        assert "error" in response

    def test_empty_lines_are_skipped(self) -> None:
        request = json.dumps({"id": "3", "method": "test", "params": {}})
        stdin = StringIO("\n\n" + request + "\n\n")
        stdout = StringIO()

        with (
            patch("sys.stdin", stdin),
            patch("sys.stdout", stdout),
            patch("portfolioos.main.dispatch", return_value="ok"),
        ):
            main()

        lines = [line for line in stdout.getvalue().strip().split("\n") if line]
        assert len(lines) == 1

    def test_dispatch_error_includes_traceback(self) -> None:
        request = json.dumps({"id": "4", "method": "bad", "params": {}})
        stdin = StringIO(request + "\n")
        stdout = StringIO()

        with patch("sys.stdin", stdin), patch("sys.stdout", stdout):
            main()

        response = json.loads(stdout.getvalue().strip())
        assert "traceback" in response["error"]
