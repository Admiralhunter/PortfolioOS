"""PortfolioOS Python sidecar entry point.

Communicates with the Electron main process via stdin/stdout
using newline-delimited JSON messages.

Protocol:
    Request:  {"id": "uuid", "method": "string", "params": {}}
    Response: {"id": "uuid", "result": {}}
    Error:    {"id": "uuid", "error": {"message": "string"}}
"""

from __future__ import annotations

import json
import sys
import traceback
from typing import Any

import numpy as np

from portfolioos.analysis.returns import cagr, max_drawdown
from portfolioos.analysis.statistics import bootstrap_returns, percentile_rank
from portfolioos.simulation.monte_carlo import run_simulation
from portfolioos.simulation.withdrawal import (
    constant_dollar_withdrawal,
    guyton_klinger_withdrawal,
)


class _NumpyEncoder(json.JSONEncoder):
    """JSON encoder that handles NumPy types."""

    def default(self, o: Any) -> Any:
        """Convert NumPy types to JSON-serializable Python types."""
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return float(o)
        return super().default(o)


def dispatch(method: str, params: dict[str, Any]) -> Any:
    """Route a method call to the appropriate handler.

    Args:
        method: The method name (e.g., "simulation.run").
        params: The parameters for the method.

    Returns:
        The result of the method call.

    Raises:
        ValueError: If the method is not recognized.

    """
    handlers: dict[str, Any] = {
        "simulation.run": run_simulation,
        "analysis.cagr": cagr,
        "analysis.max_drawdown": max_drawdown,
        "analysis.percentile_rank": percentile_rank,
        "analysis.bootstrap_returns": bootstrap_returns,
        "withdrawal.constant_dollar": constant_dollar_withdrawal,
        "withdrawal.guyton_klinger": guyton_klinger_withdrawal,
    }
    if method not in handlers:
        msg = f"Unknown method: {method}"
        raise ValueError(msg)
    return handlers[method](**params)


def main() -> None:
    """Run the sidecar message loop.

    Reads newline-delimited JSON from stdin, dispatches to handlers,
    and writes JSON responses to stdout. Runs indefinitely until
    stdin is closed.
    """
    for raw_line in sys.stdin:
        stripped = raw_line.strip()
        if not stripped:
            continue

        request: dict[str, Any] = {}
        try:
            request = json.loads(stripped)
            request_id = request.get("id", "unknown")
            method = request["method"]
            params = request.get("params", {})
            result = dispatch(method, params)
            response: dict[str, Any] = {"id": request_id, "result": result}
        except Exception as exc:  # noqa: BLE001 — dispatcher must catch all errors and return them as JSON
            request_id = (
                request.get("id", "unknown") if isinstance(request, dict) else "unknown"
            )
            response = {
                "id": request_id,
                "error": {
                    "message": str(exc),
                    "traceback": traceback.format_exc(),
                },
            }
        sys.stdout.write(json.dumps(response, cls=_NumpyEncoder) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
