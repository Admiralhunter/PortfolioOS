"""JSON export for portfolio data.

Produces a comprehensive JSON dump of portfolio holdings, transactions,
and snapshots with metadata.

"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np


class _PortfolioEncoder(json.JSONEncoder):
    """JSON encoder that handles NumPy types and datetimes."""

    def default(self, o: Any) -> Any:
        """Convert non-serializable types to JSON-safe values."""
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return float(o)
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)


def export_portfolio_json(
    holdings: list[dict[str, Any]] | None = None,
    transactions: list[dict[str, Any]] | None = None,
    snapshots: list[dict[str, Any]] | None = None,
    output_path: str | None = None,
) -> str:
    """Export portfolio data to JSON format.

    Args:
        holdings: List of holding dicts.
        transactions: List of transaction dicts.
        snapshots: List of portfolio snapshot dicts.
        output_path: File path to write. If None, returns JSON string.

    Returns:
        JSON string, or file path if output_path given.

    """
    now = datetime.now(tz=UTC).isoformat()

    export_data: dict[str, Any] = {
        "metadata": {
            "export_date": now,
            "format_version": "1.0",
            "source": "PortfolioOS",
        },
    }

    if holdings is not None:
        export_data["holdings"] = holdings
        export_data["metadata"]["holdings_count"] = len(holdings)

    if transactions is not None:
        export_data["transactions"] = transactions
        export_data["metadata"]["transactions_count"] = len(transactions)

    if snapshots is not None:
        export_data["snapshots"] = snapshots
        export_data["metadata"]["snapshots_count"] = len(snapshots)

    content = json.dumps(export_data, cls=_PortfolioEncoder, indent=2)

    if output_path:
        Path(output_path).write_text(content, encoding="utf-8")
        return output_path
    return content
