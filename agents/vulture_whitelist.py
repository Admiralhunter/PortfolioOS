"""Vulture whitelist — references that appear unused but are called dynamically.

Usage:
    cd agents && uv run vulture agents tests vulture_whitelist.py
"""

# ── Base class interface methods (overridden by subclasses) ──
from base import Agent

Agent.execute  # noqa: B018
