"""Net worth computation engine.

Computes portfolio value, asset allocation, and growth rates from
holdings data and current market prices. Designed for the dashboard's
net worth tracker (Spec 5.2).

"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class NetWorthSnapshot:
    """Point-in-time net worth computation result.

    Attributes:
        total_value: Sum of all holdings at current market prices.
        total_cost_basis: Sum of all cost bases.
        total_unrealized_gain: total_value - total_cost_basis.
        by_account: Breakdown by account_id.
        by_asset_type: Breakdown by asset type.

    """

    total_value: float = 0.0
    total_cost_basis: float = 0.0
    total_unrealized_gain: float = 0.0
    by_account: dict[str, float] = field(default_factory=dict)
    by_asset_type: dict[str, float] = field(default_factory=dict)


def compute_net_worth(
    holdings: list[dict[str, Any]],
    prices: dict[str, float],
) -> dict[str, Any]:
    """Compute net worth from holdings and current prices.

    Args:
        holdings: List of holding dicts with keys: account_id, symbol,
            shares, cost_basis, and optionally asset_type.
        prices: Dict mapping symbol to current price per share.

    Returns:
        Dict with total_value, total_cost_basis, total_unrealized_gain,
        by_account breakdown, and by_asset_type breakdown.

    """
    snapshot = NetWorthSnapshot()
    by_account: dict[str, float] = {}
    by_asset_type: dict[str, float] = {}

    for holding in holdings:
        symbol = holding["symbol"]
        shares = float(holding.get("shares", 0))
        cost_basis = float(holding.get("cost_basis", 0))
        account_id = holding.get("account_id", "default")
        asset_type = holding.get("asset_type", "unknown")

        current_price = prices.get(symbol, 0.0)
        market_value = shares * current_price

        snapshot.total_value += market_value
        snapshot.total_cost_basis += cost_basis

        by_account[account_id] = by_account.get(account_id, 0.0) + market_value
        by_asset_type[asset_type] = (
            by_asset_type.get(asset_type, 0.0) + market_value
        )

    snapshot.total_unrealized_gain = snapshot.total_value - snapshot.total_cost_basis
    snapshot.by_account = by_account
    snapshot.by_asset_type = by_asset_type

    return {
        "total_value": snapshot.total_value,
        "total_cost_basis": snapshot.total_cost_basis,
        "total_unrealized_gain": snapshot.total_unrealized_gain,
        "by_account": snapshot.by_account,
        "by_asset_type": snapshot.by_asset_type,
    }


def compute_asset_allocation(
    holdings: list[dict[str, Any]],
    prices: dict[str, float],
) -> list[dict[str, Any]]:
    """Compute asset allocation weights.

    Args:
        holdings: List of holding dicts with keys: symbol, shares,
            and optionally asset_type.
        prices: Dict mapping symbol to current price per share.

    Returns:
        List of dicts with asset_type, symbol, value, weight_pct,
        sorted by weight descending.

    """
    allocations: list[dict[str, Any]] = []
    total_value = 0.0

    for holding in holdings:
        symbol = holding["symbol"]
        shares = float(holding.get("shares", 0))
        current_price = prices.get(symbol, 0.0)
        value = shares * current_price
        total_value += value
        allocations.append(
            {
                "asset_type": holding.get("asset_type", "unknown"),
                "symbol": symbol,
                "value": value,
            }
        )

    # Compute weights
    for alloc in allocations:
        alloc["weight_pct"] = (
            (alloc["value"] / total_value * 100.0) if total_value > 0 else 0.0
        )

    return sorted(allocations, key=lambda a: a["weight_pct"], reverse=True)


def compute_growth_rates(
    snapshots: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compute growth rates from historical portfolio snapshots.

    Calculates absolute and percentage changes across various time
    horizons. Snapshots must be sorted by date ascending.

    Args:
        snapshots: List of snapshot dicts with keys: date, total_value.
            Must be sorted by date ascending.

    Returns:
        Dict with period-based returns and velocity metrics.

    """
    if len(snapshots) < 2:
        return {
            "periods": {},
            "velocity": 0.0,
        }

    latest = float(snapshots[-1]["total_value"])
    results: dict[str, dict[str, float]] = {}

    # Compute returns for each period lookback
    period_defs = {
        "1m": 21,    # ~21 trading days
        "3m": 63,
        "6m": 126,
        "1y": 252,
        "3y": 756,
        "5y": 1260,
    }

    for period_name, lookback_days in period_defs.items():
        if len(snapshots) > lookback_days:
            prior = float(snapshots[-(lookback_days + 1)]["total_value"])
            if prior > 0:
                pct_change = (latest - prior) / prior * 100.0
                results[period_name] = {
                    "start_value": prior,
                    "end_value": latest,
                    "absolute_change": latest - prior,
                    "pct_change": pct_change,
                }

    # Velocity: recent rate of change vs earlier rate
    velocity = 0.0
    if len(snapshots) >= 42:
        recent_start = float(snapshots[-22]["total_value"])
        prior_start = float(snapshots[-42]["total_value"])
        prior_end = float(snapshots[-22]["total_value"])

        if recent_start > 0 and prior_start > 0:
            recent_rate = (latest - recent_start) / recent_start
            prior_rate = (prior_end - prior_start) / prior_start
            velocity = recent_rate - prior_rate

    return {
        "periods": results,
        "velocity": velocity,
    }
