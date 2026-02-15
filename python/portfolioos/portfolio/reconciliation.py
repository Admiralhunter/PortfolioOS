"""Portfolio reconciliation — compute holdings from transaction history.

Replays transactions chronologically to derive current holdings,
using the CostBasisTracker for accurate per-lot cost basis tracking.
Detects discrepancies between computed and stored holdings.

"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from portfolioos.portfolio.cost_basis import CostBasisTracker


def reconcile_holdings(
    transactions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Compute holdings from a transaction history.

    Groups transactions by (account_id, symbol), then replays buys,
    sells, splits, and dividends chronologically. Uses CostBasisTracker
    for FIFO-based cost basis by default.

    Args:
        transactions: List of transaction dicts with keys: account_id,
            symbol, type, date, quantity, price, fees. Must include
            "type" as one of: buy, sell, split, dividend, transfer.

    Returns:
        List of computed holding dicts with keys: account_id, symbol,
        shares, cost_basis, realized_gain.

    """
    # Sort transactions chronologically
    sorted_txns = sorted(transactions, key=lambda t: t["date"])

    # Group by (account_id, symbol)
    trackers: dict[tuple[str, str], CostBasisTracker] = defaultdict(CostBasisTracker)
    realized_gains: dict[tuple[str, str], float] = defaultdict(float)

    for txn in sorted_txns:
        account_id = txn["account_id"]
        symbol = txn["symbol"]
        key = (account_id, symbol)
        tracker = trackers[key]

        tx_type = txn["type"]
        quantity = float(txn.get("quantity", 0))
        price = float(txn.get("price", 0))
        fees = float(txn.get("fees", 0))
        date = txn["date"]

        if tx_type == "buy":
            tracker.add_buy(date, quantity, price, fees)
        elif tx_type == "sell":
            disposed = tracker.sell(date, quantity, price, fees, method="fifo")
            for d in disposed:
                realized_gains[key] += d.gain_loss
        elif tx_type == "split":
            _apply_split(tracker, quantity)
        elif tx_type == "dividend":
            # Reinvested dividends are treated as buys at the given price
            if price > 0 and quantity > 0:
                tracker.add_buy(date, quantity, price, fees)
        elif tx_type == "transfer":
            # Transfers in are treated as buys with the given cost basis
            if quantity > 0:
                tracker.add_buy(date, quantity, price, fees)

    # Build holdings from trackers
    holdings: list[dict[str, Any]] = []
    for (account_id, symbol), tracker in trackers.items():
        total_shares = tracker.get_total_shares()
        if total_shares <= 1e-9:
            continue
        holdings.append(
            {
                "account_id": account_id,
                "symbol": symbol,
                "shares": total_shares,
                "cost_basis": tracker.get_total_cost_basis(),
                "realized_gain": realized_gains[(account_id, symbol)],
            }
        )

    return sorted(holdings, key=lambda h: (h["account_id"], h["symbol"]))


def detect_discrepancies(
    computed: list[dict[str, Any]],
    stored: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Compare reconciled holdings against stored holdings.

    Args:
        computed: Holdings derived from reconcile_holdings().
        stored: Holdings currently stored in the database.

    Returns:
        List of discrepancy dicts with keys: account_id, symbol,
        field, computed_value, stored_value.

    """
    computed_map: dict[tuple[str, str], dict[str, Any]] = {
        (h["account_id"], h["symbol"]): h for h in computed
    }
    stored_map: dict[tuple[str, str], dict[str, Any]] = {
        (h["account_id"], h["symbol"]): h for h in stored
    }

    discrepancies: list[dict[str, Any]] = []
    all_keys = set(computed_map.keys()) | set(stored_map.keys())

    for key in sorted(all_keys):
        account_id, symbol = key
        c = computed_map.get(key)
        s = stored_map.get(key)

        if c is None:
            discrepancies.append(
                {
                    "account_id": account_id,
                    "symbol": symbol,
                    "field": "existence",
                    "computed_value": "missing",
                    "stored_value": "present",
                }
            )
            continue

        if s is None:
            discrepancies.append(
                {
                    "account_id": account_id,
                    "symbol": symbol,
                    "field": "existence",
                    "computed_value": "present",
                    "stored_value": "missing",
                }
            )
            continue

        # Compare shares
        c_shares = float(c.get("shares", 0))
        s_shares = float(s.get("shares", 0))
        if abs(c_shares - s_shares) > 1e-6:
            discrepancies.append(
                {
                    "account_id": account_id,
                    "symbol": symbol,
                    "field": "shares",
                    "computed_value": c_shares,
                    "stored_value": s_shares,
                }
            )

        # Compare cost basis
        c_basis = float(c.get("cost_basis", 0))
        s_basis = float(s.get("cost_basis", 0))
        if abs(c_basis - s_basis) > 0.01:
            discrepancies.append(
                {
                    "account_id": account_id,
                    "symbol": symbol,
                    "field": "cost_basis",
                    "computed_value": c_basis,
                    "stored_value": s_basis,
                }
            )

    return discrepancies


def _apply_split(tracker: CostBasisTracker, ratio: float) -> None:
    """Apply a stock split to all lots in a tracker.

    Adjusts quantity and price for each lot to reflect the split ratio.
    For example, a 2:1 split doubles shares and halves the price.

    Args:
        tracker: The CostBasisTracker to modify.
        ratio: Split ratio (e.g., 2.0 for a 2:1 split).

    """
    if ratio <= 0:
        return
    for lot in tracker.lots:
        lot.quantity *= ratio
        lot.remaining_qty *= ratio
        lot.price /= ratio
