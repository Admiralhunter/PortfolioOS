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
from portfolioos.export.csv_export import (
    export_holdings_csv,
    export_simulation_csv,
    export_transactions_csv,
)
from portfolioos.export.json_export import export_portfolio_json
from portfolioos.ingest.csv_import import parse_csv
from portfolioos.market.fred import fetch_multiple_series as fred_fetch_multiple
from portfolioos.market.fred import fetch_series as fred_fetch_series
from portfolioos.market.validation import detect_gaps, detect_outliers, validate_ohlcv
from portfolioos.market.yahoo import (
    fetch_dividends,
    fetch_info,
    fetch_price_history,
    fetch_splits,
)
from portfolioos.portfolio.cost_basis import CostBasisTracker
from portfolioos.portfolio.net_worth import (
    compute_asset_allocation,
    compute_growth_rates,
    compute_net_worth,
)
from portfolioos.portfolio.reconciliation import (
    detect_discrepancies,
    reconcile_holdings,
)
from portfolioos.simulation.monte_carlo import run_simulation
from portfolioos.simulation.scenarios import run_scenario, sensitivity_analysis
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


def _handle_cost_basis_sell(
    lots: list[dict[str, Any]],
    date: str,
    quantity: float,
    price: float,
    fees: float = 0.0,
    method: str = "fifo",
    lot_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Handle cost basis sell via sidecar (stateless, lots passed in).

    Args:
        lots: List of lot dicts with keys: date, quantity, price, fees,
            remaining_qty, lot_id.
        date: Sale date.
        quantity: Shares to sell.
        price: Sale price per share.
        fees: Sale fees.
        method: Cost basis method.
        lot_ids: Lot IDs for specific_id method.

    Returns:
        Dict with disposed lots and updated tracker state.

    """
    from portfolioos.portfolio.cost_basis import TaxLot

    tracker = CostBasisTracker()
    for lot_data in lots:
        lot = TaxLot(
            date=lot_data["date"],
            quantity=lot_data["quantity"],
            price=lot_data["price"],
            fees=lot_data.get("fees", 0.0),
            remaining_qty=lot_data.get("remaining_qty", lot_data["quantity"]),
            lot_id=lot_data.get("lot_id", ""),
        )
        tracker.lots.append(lot)

    disposed = tracker.sell(date, quantity, price, fees, method=method, lot_ids=lot_ids)
    return {
        "disposed": [
            {
                "lot_date": d.lot_date,
                "qty_sold": d.qty_sold,
                "proceeds": d.proceeds,
                "cost_basis": d.cost_basis,
                "gain_loss": d.gain_loss,
                "holding_period": d.holding_period,
            }
            for d in disposed
        ],
        "tracker": tracker.to_dict(),
    }


def _handle_cost_basis_unrealized(
    lots: list[dict[str, Any]],
    current_price: float,
    as_of_date: str | None = None,
) -> dict[str, Any]:
    """Handle unrealized gains via sidecar (stateless, lots passed in).

    Args:
        lots: List of lot dicts.
        current_price: Current market price per share.
        as_of_date: Date for holding period calculation.

    Returns:
        Dict with unrealized gains per lot and totals.

    """
    from portfolioos.portfolio.cost_basis import TaxLot

    tracker = CostBasisTracker()
    for lot_data in lots:
        lot = TaxLot(
            date=lot_data["date"],
            quantity=lot_data["quantity"],
            price=lot_data["price"],
            fees=lot_data.get("fees", 0.0),
            remaining_qty=lot_data.get("remaining_qty", lot_data["quantity"]),
            lot_id=lot_data.get("lot_id", ""),
        )
        tracker.lots.append(lot)

    gains = tracker.get_unrealized_gains(current_price, as_of_date)
    return {
        "gains": [
            {
                "lot_date": g.lot_date,
                "shares": g.shares,
                "cost_basis": g.cost_basis,
                "market_value": g.market_value,
                "unrealized_gain": g.unrealized_gain,
                "holding_period": g.holding_period,
            }
            for g in gains
        ],
        "total_unrealized": sum(g.unrealized_gain for g in gains),
        "total_market_value": sum(g.market_value for g in gains),
    }


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
        # Simulation
        "simulation.run": run_simulation,
        "simulation.scenario": run_scenario,
        "simulation.sensitivity": sensitivity_analysis,
        # Analysis
        "analysis.cagr": cagr,
        "analysis.max_drawdown": max_drawdown,
        "analysis.percentile_rank": percentile_rank,
        "analysis.bootstrap_returns": bootstrap_returns,
        # Withdrawal strategies
        "withdrawal.constant_dollar": constant_dollar_withdrawal,
        "withdrawal.guyton_klinger": guyton_klinger_withdrawal,
        # Market data — Yahoo Finance
        "market.yahoo.price_history": fetch_price_history,
        "market.yahoo.dividends": fetch_dividends,
        "market.yahoo.splits": fetch_splits,
        "market.yahoo.info": fetch_info,
        # Market data — FRED
        "market.fred.series": fred_fetch_series,
        "market.fred.multiple_series": fred_fetch_multiple,
        # Validation
        "validation.detect_gaps": detect_gaps,
        "validation.detect_outliers": detect_outliers,
        "validation.ohlcv": validate_ohlcv,
        # Import
        "ingest.csv": parse_csv,
        # Portfolio
        "portfolio.reconcile": reconcile_holdings,
        "portfolio.detect_discrepancies": detect_discrepancies,
        "portfolio.cost_basis.sell": _handle_cost_basis_sell,
        "portfolio.cost_basis.unrealized": _handle_cost_basis_unrealized,
        "portfolio.net_worth": compute_net_worth,
        "portfolio.asset_allocation": compute_asset_allocation,
        "portfolio.growth_rates": compute_growth_rates,
        # Export
        "export.holdings_csv": export_holdings_csv,
        "export.transactions_csv": export_transactions_csv,
        "export.simulation_csv": export_simulation_csv,
        "export.portfolio_json": export_portfolio_json,
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
