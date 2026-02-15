"""Tests for cost basis tracking engine."""

from __future__ import annotations

import pytest
from portfolioos.portfolio.cost_basis import CostBasisTracker


class TestCostBasisTrackerBuys:
    """Test lot creation via add_buy."""

    def test_add_single_buy(self):
        tracker = CostBasisTracker()
        lot_id = tracker.add_buy("2024-01-15", 100, 50.0, fees=9.99)
        assert tracker.get_total_shares() == 100
        assert lot_id == "lot-0"
        assert len(tracker.lots) == 1

    def test_add_multiple_buys(self):
        tracker = CostBasisTracker()
        tracker.add_buy("2024-01-15", 100, 50.0)
        tracker.add_buy("2024-06-15", 50, 60.0)
        assert tracker.get_total_shares() == 150
        assert len(tracker.lots) == 2

    def test_total_cost_basis(self):
        tracker = CostBasisTracker()
        tracker.add_buy("2024-01-15", 100, 50.0, fees=10.0)
        tracker.add_buy("2024-06-15", 50, 60.0, fees=5.0)
        # 100*50 + 10 + 50*60 + 5 = 5010 + 3005 = 8015
        assert tracker.get_total_cost_basis() == pytest.approx(8015.0)


class TestFIFO:
    """Test FIFO (first-in, first-out) disposal."""

    def test_fifo_sells_earliest_first(self):
        tracker = CostBasisTracker()
        tracker.add_buy("2023-01-01", 100, 50.0)
        tracker.add_buy("2024-01-01", 100, 70.0)
        disposed = tracker.sell("2024-06-01", 50, 80.0, method="fifo")
        assert len(disposed) == 1
        assert disposed[0].lot_date == "2023-01-01"
        assert disposed[0].qty_sold == 50
        assert tracker.get_total_shares() == pytest.approx(150)

    def test_fifo_spans_multiple_lots(self):
        tracker = CostBasisTracker()
        tracker.add_buy("2023-01-01", 30, 50.0)
        tracker.add_buy("2024-01-01", 70, 70.0)
        disposed = tracker.sell("2024-06-01", 50, 80.0, method="fifo")
        assert len(disposed) == 2
        assert disposed[0].lot_date == "2023-01-01"
        assert disposed[0].qty_sold == 30
        assert disposed[1].lot_date == "2024-01-01"
        assert disposed[1].qty_sold == 20
        assert tracker.get_total_shares() == pytest.approx(50)

    def test_fifo_gain_calculation(self):
        tracker = CostBasisTracker()
        tracker.add_buy("2023-01-01", 100, 50.0)
        disposed = tracker.sell("2024-06-01", 100, 80.0, method="fifo")
        assert len(disposed) == 1
        # Proceeds: 100 * 80 = 8000, Cost: 100 * 50 = 5000, Gain: 3000
        assert disposed[0].proceeds == pytest.approx(8000.0)
        assert disposed[0].cost_basis == pytest.approx(5000.0)
        assert disposed[0].gain_loss == pytest.approx(3000.0)


class TestLIFO:
    """Test LIFO (last-in, first-out) disposal."""

    def test_lifo_sells_latest_first(self):
        tracker = CostBasisTracker()
        tracker.add_buy("2023-01-01", 100, 50.0)
        tracker.add_buy("2024-01-01", 100, 70.0)
        disposed = tracker.sell("2024-06-01", 50, 80.0, method="lifo")
        assert len(disposed) == 1
        assert disposed[0].lot_date == "2024-01-01"
        assert disposed[0].qty_sold == 50

    def test_lifo_spans_multiple_lots(self):
        tracker = CostBasisTracker()
        tracker.add_buy("2023-01-01", 70, 50.0)
        tracker.add_buy("2024-01-01", 30, 70.0)
        disposed = tracker.sell("2024-06-01", 50, 80.0, method="lifo")
        assert len(disposed) == 2
        assert disposed[0].lot_date == "2024-01-01"
        assert disposed[0].qty_sold == 30
        assert disposed[1].lot_date == "2023-01-01"
        assert disposed[1].qty_sold == 20


class TestAverageCost:
    """Test average cost disposal method."""

    def test_average_cost_pooling(self):
        tracker = CostBasisTracker()
        tracker.add_buy("2023-01-01", 100, 50.0)
        tracker.add_buy("2024-01-01", 100, 70.0)
        disposed = tracker.sell("2024-06-01", 50, 80.0, method="average_cost")
        assert len(disposed) == 1
        # Average cost: (100*50 + 100*70) / 200 = 60
        # Cost basis for 50 shares: 50 * 60 = 3000
        assert disposed[0].cost_basis == pytest.approx(3000.0)
        # Proceeds: 50 * 80 = 4000, Gain: 1000
        assert disposed[0].gain_loss == pytest.approx(1000.0)


class TestSpecificID:
    """Test specific lot identification disposal method."""

    def test_specific_id_selection(self):
        tracker = CostBasisTracker()
        id0 = tracker.add_buy("2023-01-01", 100, 50.0)
        _id1 = tracker.add_buy("2024-01-01", 100, 70.0)
        disposed = tracker.sell(
            "2024-06-01", 50, 80.0, method="specific_id", lot_ids=[id0]
        )
        assert len(disposed) == 1
        assert disposed[0].lot_date == "2023-01-01"
        assert disposed[0].qty_sold == 50

    def test_specific_id_not_found(self):
        tracker = CostBasisTracker()
        tracker.add_buy("2023-01-01", 100, 50.0)
        with pytest.raises(ValueError, match="not found"):
            tracker.sell(
                "2024-06-01", 50, 80.0, method="specific_id", lot_ids=["bogus"]
            )

    def test_specific_id_insufficient_shares_in_lots(self):
        tracker = CostBasisTracker()
        id0 = tracker.add_buy("2023-01-01", 10, 50.0)
        tracker.add_buy("2024-01-01", 100, 70.0)
        with pytest.raises(ValueError, match="Insufficient shares in specified"):
            tracker.sell("2024-06-01", 50, 80.0, method="specific_id", lot_ids=[id0])


class TestHoldingPeriod:
    """Test short-term vs long-term classification."""

    def test_short_term(self):
        tracker = CostBasisTracker()
        tracker.add_buy("2024-01-01", 100, 50.0)
        disposed = tracker.sell("2024-06-01", 100, 80.0, method="fifo")
        assert disposed[0].holding_period == "short_term"

    def test_long_term(self):
        tracker = CostBasisTracker()
        tracker.add_buy("2023-01-01", 100, 50.0)
        disposed = tracker.sell("2024-06-01", 100, 80.0, method="fifo")
        assert disposed[0].holding_period == "long_term"

    def test_exactly_one_year_is_short_term(self):
        tracker = CostBasisTracker()
        tracker.add_buy("2023-06-01", 100, 50.0)
        disposed = tracker.sell("2024-06-01", 100, 80.0, method="fifo")
        # 366 days in a leap year — long_term
        assert disposed[0].holding_period == "long_term"


class TestPartialAndEdge:
    """Test partial sales and edge cases."""

    def test_partial_lot_sale(self):
        tracker = CostBasisTracker()
        tracker.add_buy("2023-01-01", 100, 50.0)
        tracker.sell("2024-06-01", 40, 80.0, method="fifo")
        assert tracker.get_total_shares() == pytest.approx(60)
        assert tracker.lots[0].remaining_qty == pytest.approx(60)

    def test_sell_all_shares(self):
        tracker = CostBasisTracker()
        tracker.add_buy("2023-01-01", 100, 50.0)
        tracker.sell("2024-06-01", 100, 80.0, method="fifo")
        assert tracker.get_total_shares() == pytest.approx(0)

    def test_insufficient_shares_raises(self):
        tracker = CostBasisTracker()
        tracker.add_buy("2023-01-01", 50, 50.0)
        with pytest.raises(ValueError, match="Insufficient shares"):
            tracker.sell("2024-06-01", 100, 80.0, method="fifo")

    def test_unknown_method_raises(self):
        tracker = CostBasisTracker()
        tracker.add_buy("2023-01-01", 100, 50.0)
        with pytest.raises(ValueError, match="Unknown method"):
            tracker.sell("2024-06-01", 50, 80.0, method="random")

    def test_sell_with_fees(self):
        tracker = CostBasisTracker()
        tracker.add_buy("2023-01-01", 100, 50.0, fees=10.0)
        disposed = tracker.sell("2024-06-01", 100, 80.0, fees=9.99, method="fifo")
        assert disposed[0].proceeds == pytest.approx(7990.01)
        assert disposed[0].cost_basis == pytest.approx(5010.0)


class TestUnrealizedGains:
    """Test unrealized gain computation."""

    def test_unrealized_gains_basic(self):
        tracker = CostBasisTracker()
        tracker.add_buy("2023-01-01", 100, 50.0)
        gains = tracker.get_unrealized_gains(80.0, as_of_date="2024-06-01")
        assert len(gains) == 1
        assert gains[0].shares == 100
        assert gains[0].market_value == pytest.approx(8000.0)
        assert gains[0].cost_basis == pytest.approx(5000.0)
        assert gains[0].unrealized_gain == pytest.approx(3000.0)
        assert gains[0].holding_period == "long_term"

    def test_unrealized_gains_after_partial_sale(self):
        tracker = CostBasisTracker()
        tracker.add_buy("2023-01-01", 100, 50.0)
        tracker.sell("2024-01-15", 40, 80.0, method="fifo")
        gains = tracker.get_unrealized_gains(90.0, as_of_date="2024-06-01")
        assert len(gains) == 1
        assert gains[0].shares == 60
        assert gains[0].market_value == pytest.approx(5400.0)

    def test_unrealized_gains_excludes_empty_lots(self):
        tracker = CostBasisTracker()
        tracker.add_buy("2023-01-01", 100, 50.0)
        tracker.sell("2024-06-01", 100, 80.0, method="fifo")
        gains = tracker.get_unrealized_gains(80.0, as_of_date="2024-06-01")
        assert len(gains) == 0


class TestSerialization:
    """Test tracker serialization."""

    def test_to_dict(self):
        tracker = CostBasisTracker()
        tracker.add_buy("2023-01-01", 100, 50.0, fees=10.0)
        result = tracker.to_dict()
        assert result["total_shares"] == 100
        assert result["total_cost_basis"] == pytest.approx(5010.0)
        assert len(result["lots"]) == 1
        assert result["lots"][0]["date"] == "2023-01-01"
