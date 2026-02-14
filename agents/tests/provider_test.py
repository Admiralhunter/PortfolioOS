"""Tests for the LLM provider abstraction."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

import pytest

from agents.llm.provider import (
    AnthropicProvider,
    LLMResponse,
    LMStudioProvider,
    OpenAICompatibleProvider,
    get_provider,
)

# -- Fake HTTP server for testing OpenAI-compatible APIs --------------------

class FakeOpenAIHandler(BaseHTTPRequestHandler):
    """Minimal handler that returns a canned OpenAI-format response."""

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}

        msgs = body.get("messages", [{}])
        echo_text = msgs[-1].get("content", "")
        response = {
            "choices": [{"message": {"content": f"echo:{echo_text}"}}],
            "model": body.get("model", "test-model"),
            "usage": {"total_tokens": 42},
        }
        payload = json.dumps(response).encode()

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *_args: Any) -> None:
        pass  # silence request logging


@pytest.fixture()
def fake_openai_server():
    """Start a local HTTP server that mimics OpenAI's chat completions."""
    server = HTTPServer(("127.0.0.1", 0), FakeOpenAIHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}/v1"
    server.shutdown()


# -- LMStudioProvider tests -------------------------------------------------

class TestLMStudioProvider:
    def test_complete_against_fake_server(self, fake_openai_server: str) -> None:
        provider = LMStudioProvider(base_url=fake_openai_server, model="test")
        resp = provider.complete(system="sys", user="hello")
        assert isinstance(resp, LLMResponse)
        assert "echo:hello" in resp.content
        assert resp.tokens_used == 42
        assert resp.model == "test"

    def test_default_endpoint(self) -> None:
        provider = LMStudioProvider()
        assert "localhost:1234" in provider.base_url

    def test_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LM_STUDIO_ENDPOINT", "http://custom:9999/v1")
        provider = LMStudioProvider()
        assert "custom:9999" in provider.base_url


# -- AnthropicProvider tests ------------------------------------------------

class TestAnthropicProvider:
    def test_requires_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(EnvironmentError, match="ANTHROPIC_API_KEY"):
            AnthropicProvider()

    def test_init_with_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        provider = AnthropicProvider(model="claude-sonnet-4-20250514")
        assert provider.model == "claude-sonnet-4-20250514"
        assert provider.api_key == "test-key"


# -- OpenAICompatibleProvider tests -----------------------------------------

class TestOpenAICompatibleProvider:
    def test_requires_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with pytest.raises(EnvironmentError, match="OPENAI_API_KEY"):
            OpenAICompatibleProvider()

    def test_complete_against_fake_server(
        self, fake_openai_server: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "fake-key")
        provider = OpenAICompatibleProvider(
            model="gpt-4o", base_url=fake_openai_server,
        )
        resp = provider.complete(system="sys", user="test-input")
        assert "echo:test-input" in resp.content
        assert resp.tokens_used == 42


# -- get_provider tests -----------------------------------------------------

class TestGetProvider:
    def test_local_provider(self) -> None:
        provider = get_provider("local")
        assert isinstance(provider, LMStudioProvider)

    def test_lm_studio_alias(self) -> None:
        provider = get_provider("lm-studio")
        assert isinstance(provider, LMStudioProvider)

    def test_claude_sonnet(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
        provider = get_provider("claude-sonnet")
        assert isinstance(provider, AnthropicProvider)
        assert "sonnet" in provider.model

    def test_claude_opus(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
        provider = get_provider("claude-opus")
        assert isinstance(provider, AnthropicProvider)
        assert "opus" in provider.model

    def test_openai(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "test")
        provider = get_provider("openai")
        assert isinstance(provider, OpenAICompatibleProvider)

    def test_unknown_provider(self) -> None:
        with pytest.raises(ValueError, match="Unknown provider"):
            get_provider("does-not-exist")


# -- LLMResponse tests -----------------------------------------------------

class TestLLMResponse:
    def test_frozen(self) -> None:
        resp = LLMResponse(content="hi", tokens_used=10, model="m")
        with pytest.raises(AttributeError):
            resp.content = "bye"  # type: ignore[misc]
