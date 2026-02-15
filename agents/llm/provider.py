"""Unified LLM provider interface for local and cloud inference.

Supports three backends:
  - LM Studio (local, OpenAI-compatible API at localhost:1234)
  - Anthropic Claude (cloud, requires ANTHROPIC_API_KEY)
  - OpenAI-compatible (cloud, requires OPENAI_API_KEY)

Local inference is always the default.  Cloud providers are opt-in
and require explicit environment variables to be set.

All providers implement the same ``complete()`` contract so agents
don't need to know which backend they're using.

Usage::

    from agents.llm.provider import get_provider

    llm = get_provider("local")          # LM Studio
    llm = get_provider("claude-sonnet")  # Anthropic Sonnet
    llm = get_provider("claude-opus")    # Anthropic Opus

    response = llm.complete(
        system="You are a code reviewer.",
        user="Review this function...",
    )
    print(response.content, response.tokens_used)
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass

logger = logging.getLogger("agents.llm")


@dataclass(frozen=True)
class LLMResponse:
    """Structured response from any LLM provider."""

    content: str
    tokens_used: int
    model: str


class LLMProvider(ABC):
    """Base class for LLM providers.  All agents interact via this interface."""

    @abstractmethod
    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> LLMResponse:
        """Send a single-turn completion request and return the response."""


class LMStudioProvider(LLMProvider):
    """Local inference via LM Studio's OpenAI-compatible endpoint.

    Defaults to ``http://localhost:1234/v1`` which is LM Studio's default.
    Set ``LM_STUDIO_ENDPOINT`` to override.
    """

    def __init__(
        self,
        base_url: str | None = None,
        model: str = "local-model",
    ) -> None:
        self.base_url = (
            base_url
            or os.environ.get("LM_STUDIO_ENDPOINT", "http://localhost:1234/v1")
        ).rstrip("/")
        self.model = model

    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> LLMResponse:
        payload = json.dumps({
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }).encode()

        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=payload,
            method="POST",
        )
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", "Bearer lm-studio")

        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read())

        usage = body.get("usage", {})
        return LLMResponse(
            content=body["choices"][0]["message"]["content"],
            tokens_used=usage.get("total_tokens", 0),
            model=body.get("model", self.model),
        )


class AnthropicProvider(LLMProvider):
    """Cloud inference via the Anthropic Messages API.

    Requires ``ANTHROPIC_API_KEY`` environment variable.
    """

    API_URL = "https://api.anthropic.com/v1/messages"

    def __init__(self, model: str = "claude-sonnet-4-5-20250929") -> None:
        self.model = model
        self.api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not self.api_key:
            raise OSError(
                "ANTHROPIC_API_KEY is required for Anthropic provider"
            )

    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> LLMResponse:
        payload = json.dumps({
            "model": self.model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
            "temperature": temperature,
        }).encode()

        req = urllib.request.Request(
            self.API_URL, data=payload, method="POST",
        )
        req.add_header("Content-Type", "application/json")
        req.add_header("x-api-key", self.api_key)
        req.add_header("anthropic-version", "2023-06-01")

        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read())

        usage = body.get("usage", {})
        return LLMResponse(
            content=body["content"][0]["text"],
            tokens_used=usage.get("input_tokens", 0)
            + usage.get("output_tokens", 0),
            model=self.model,
        )


class OpenAICompatibleProvider(LLMProvider):
    """Cloud inference via any OpenAI-compatible API.

    Set ``OPENAI_API_KEY`` and optionally ``OPENAI_BASE_URL``.
    Works with OpenAI, OpenRouter, Together, etc.
    """

    def __init__(
        self,
        model: str = "gpt-4o",
        base_url: str | None = None,
    ) -> None:
        self.model = model
        self.base_url = (
            base_url
            or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        ).rstrip("/")
        self.api_key = os.environ.get("OPENAI_API_KEY", "")
        if not self.api_key:
            raise OSError(
                "OPENAI_API_KEY is required for OpenAI-compatible provider"
            )

    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> LLMResponse:
        payload = json.dumps({
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }).encode()

        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=payload,
            method="POST",
        )
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", f"Bearer {self.api_key}")

        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read())

        usage = body.get("usage", {})
        return LLMResponse(
            content=body["choices"][0]["message"]["content"],
            tokens_used=usage.get("total_tokens", 0),
            model=body.get("model", self.model),
        )


# -- Provider registry -------------------------------------------------------

_PROVIDERS: dict[str, type[LLMProvider]] = {
    "local": LMStudioProvider,
    "lm-studio": LMStudioProvider,
    "claude-haiku": AnthropicProvider,
    "claude-sonnet": AnthropicProvider,
    "claude-opus": AnthropicProvider,
    "openai": OpenAICompatibleProvider,
    "openrouter": OpenAICompatibleProvider,
}

_MODEL_DEFAULTS: dict[str, str] = {
    "claude-haiku": "claude-haiku-4-5-20251001",
    "claude-sonnet": "claude-sonnet-4-5-20250929",
    "claude-opus": "claude-opus-4-6",
    "openai": "gpt-4o",
    "openrouter": "anthropic/claude-sonnet-4-5-20250929",
}


def get_provider(preference: str = "local") -> LLMProvider:
    """Instantiate an LLM provider by name.

    Args:
        preference: One of "local", "lm-studio", "claude-haiku",
            "claude-sonnet", "claude-opus", "openai", "openrouter".

    Environment variables:
        AGENT_LLM_MODEL: Override the default model ID for the chosen
            provider.  For example, set ``AGENT_LLM_MODEL=claude-haiku-4-5-20251001``
            to use Haiku instead of the default Sonnet.

    Returns:
        An initialised LLMProvider ready for ``complete()`` calls.

    Raises:
        ValueError: If *preference* is not recognised.
    """
    cls = _PROVIDERS.get(preference)
    if cls is None:
        raise ValueError(
            f"Unknown provider '{preference}'. "
            f"Choose from: {', '.join(sorted(_PROVIDERS))}"
        )

    # Allow env var to override the model ID
    model_override = os.environ.get("AGENT_LLM_MODEL", "").strip()
    model = model_override or _MODEL_DEFAULTS.get(preference)

    if model_override:
        logger.info(
            "Model override via AGENT_LLM_MODEL=%s (provider=%s)",
            model_override, preference,
        )

    if model and cls in (AnthropicProvider, OpenAICompatibleProvider):
        provider = cls(model=model)
    elif model and cls is LMStudioProvider:
        provider = cls(model=model)
    else:
        provider = cls()

    logger.info(
        "Initialized %s (model=%s)",
        type(provider).__name__,
        getattr(provider, "model", "unknown"),
    )
    return provider
