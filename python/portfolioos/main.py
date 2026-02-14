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


def dispatch(method: str, params: dict[str, Any]) -> Any:
    """Route a method call to the appropriate handler.

    Args:
        method: The method name (e.g., "simulation.monte_carlo").
        params: The parameters for the method.

    Returns:
        The result of the method call.

    Raises:
        ValueError: If the method is not recognized.

    """
    # Wire up handlers as simulation/market/analysis modules are implemented.
    handlers: dict[str, Any] = {}
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
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        request: dict[str, Any] = {}
        try:
            request = json.loads(line)
            request_id = request.get("id", "unknown")
            method = request["method"]
            params = request.get("params", {})
            result = dispatch(method, params)
            response: dict[str, Any] = {"id": request_id, "result": result}
        except Exception as exc:
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
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
