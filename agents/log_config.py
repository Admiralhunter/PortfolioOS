"""Shared logging configuration for all agents.

Call ``setup()`` once at the top of each agent's ``main()`` to get
ISO-8601 timestamps on every log line.
"""

from __future__ import annotations

import logging

_LOG_FORMAT = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S%z"


def setup(*, verbose: bool = False) -> None:
    """Configure the root logger with timestamped output.

    Args:
        verbose: If True, set level to DEBUG; otherwise INFO.
    """
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format=_LOG_FORMAT,
        datefmt=_DATE_FORMAT,
    )
