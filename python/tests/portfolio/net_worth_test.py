"""Tests for net worth computation engine."""

from __future__ import annotations

import pytest
from portfolioos.portfolio.net_worth import (
    compute_asset_allocation,
    compute_growth_rates,
    compute_net_worth,
)


class TestComputeNetWorth:
    """Test net worth computation."""

    def test_basic_computation(self):
        holdings = [
            {
                "account_id": "acc1",
                "symbol": "AAPL",
                "shares": 100,
                "cost_basis": 15000.0,
            },
            {
                "account_id": "acc1",
                "symbol": "GOOGL",
                "shares": 50,
                "cost_basis": 7000.0,
            },
        ]
        prices = {"AAPL": 180.0, "GOOGL": 160.0}
        result = compute_net_worth(holdings, prices)
        # AAPL: 100 * 180 = 18000, GOOGL: 50 * 160 = 8000
        assert result["total_value"] == pytest.approx(26000.0)
        assert result["total_cost_basis"] == pytest.approx(22000.0)
        assert result["total_unrealized_gain"] == pytest.approx(4000.0)

    def test_by_account_breakdown(self):
        holdings = [
            {
                "account_id": "ira",
                "symbol": "VTI",
                "shares": 100,
                "cost_basis": 10000.0,
            },
            {
                "account_id": "taxable",
                "symbol": "VTI",
                "shares": 50,
                "cost_basis": 5000.0,
            },
        ]
        prices = {"VTI": 220.0}
        result = compute_net_worth(holdings, prices)
        assert result["by_account"]["ira"] == pytest.approx(22000.0)
        assert result["by_account"]["taxable"] == pytest.approx(11000.0)

    def test_by_asset_type_breakdown(self):
        holdings = [
            {
                "account_id": "acc1",
                "symbol": "AAPL",
                "shares": 100,
                "cost_basis": 15000.0,
                "asset_type": "stock",
            },
            {
                "account_id": "acc1",
                "symbol": "BND",
                "shares": 200,
                "cost_basis": 16000.0,
                "asset_type": "bond",
            },
        ]
        prices = {"AAPL": 180.0, "BND": 80.0}
        result = compute_net_worth(holdings, prices)
        assert result["by_asset_type"]["stock"] == pytest.approx(18000.0)
        assert result["by_asset_type"]["bond"] == pytest.approx(16000.0)

    def test_empty_portfolio(self):
        result = compute_net_worth([], {})
        assert result["total_value"] == 0.0
        assert result["total_cost_basis"] == 0.0
        assert result["total_unrealized_gain"] == 0.0

    def test_missing_price(self):
        holdings = [
            {
                "account_id": "acc1",
                "symbol": "AAPL",
                "shares": 100,
                "cost_basis": 15000.0,
            }
        ]
        # Price for AAPL not in dict
        result = compute_net_worth(holdings, {})
        assert result["total_value"] == 0.0
        assert result["total_unrealized_gain"] == pytest.approx(-15000.0)

    def test_single_holding(self):
        holdings = [
            {
                "account_id": "acc1",
                "symbol": "VTI",
                "shares": 200,
                "cost_basis": 30000.0,
            }
        ]
        prices = {"VTI": 200.0}
        result = compute_net_worth(holdings, prices)
        assert result["total_value"] == pytest.approx(40000.0)
        assert result["total_unrealized_gain"] == pytest.approx(10000.0)


class TestComputeAssetAllocation:
    """Test asset allocation computation."""

    def test_weight_calculation(self):
        holdings = [
            {"symbol": "AAPL", "shares": 100, "asset_type": "stock"},
            {"symbol": "BND", "shares": 100, "asset_type": "bond"},
        ]
        prices = {"AAPL": 150.0, "BND": 50.0}
        allocs = compute_asset_allocation(holdings, prices)
        # AAPL: 15000, BND: 5000, total: 20000
        assert allocs[0]["symbol"] == "AAPL"
        assert allocs[0]["weight_pct"] == pytest.approx(75.0)
        assert allocs[1]["symbol"] == "BND"
        assert allocs[1]["weight_pct"] == pytest.approx(25.0)

    def test_sorted_by_weight_descending(self):
        holdings = [
            {"symbol": "A", "shares": 10, "asset_type": "stock"},
            {"symbol": "B", "shares": 100, "asset_type": "stock"},
            {"symbol": "C", "shares": 50, "asset_type": "stock"},
        ]
        prices = {"A": 10.0, "B": 10.0, "C": 10.0}
        allocs = compute_asset_allocation(holdings, prices)
        weights = [a["weight_pct"] for a in allocs]
        assert weights == sorted(weights, reverse=True)

    def test_empty_portfolio(self):
        allocs = compute_asset_allocation([], {})
        assert len(allocs) == 0

    def test_zero_price_asset(self):
        holdings = [
            {"symbol": "AAPL", "shares": 100, "asset_type": "stock"},
            {"symbol": "DEAD", "shares": 50, "asset_type": "stock"},
        ]
        prices = {"AAPL": 150.0, "DEAD": 0.0}
        allocs = compute_asset_allocation(holdings, prices)
        assert len(allocs) == 2
        dead_alloc = next(a for a in allocs if a["symbol"] == "DEAD")
        assert dead_alloc["weight_pct"] == pytest.approx(0.0)


class TestComputeGrowthRates:
    """Test growth rate computation from snapshots."""

    def test_insufficient_data(self):
        result = compute_growth_rates([{"date": "2024-01-01", "total_value": 100000}])
        assert result["periods"] == {}
        assert result["velocity"] == 0.0

    def test_monthly_return(self):
        # Create 23 snapshots to test 1m lookback (needs > 21)
        snapshots = [
            {"date": f"2024-01-{i:02d}", "total_value": 100000 + i * 100}
            for i in range(1, 24)
        ]
        result = compute_growth_rates(snapshots)
        assert "1m" in result["periods"]
        period = result["periods"]["1m"]
        assert period["pct_change"] > 0

    def test_no_period_when_insufficient_history(self):
        snapshots = [
            {"date": f"2024-01-{i:02d}", "total_value": 100000} for i in range(1, 10)
        ]
        result = compute_growth_rates(snapshots)
        # Only 9 snapshots, need > 21 for 1m
        assert "1m" not in result["periods"]

    def test_velocity_calculation(self):
        # Need 42+ snapshots for velocity
        snapshots = [
            {"date": f"day-{i}", "total_value": 100000 + i * 200} for i in range(50)
        ]
        result = compute_growth_rates(snapshots)
        # Linear growth → velocity should be near 0
        assert abs(result["velocity"]) < 0.01
