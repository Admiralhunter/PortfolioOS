"""Tests for Yahoo Finance market data adapter."""

from __future__ import annotations

import pytest
from portfolioos.market.yahoo import fetch_price_history


class TestFetchPriceHistory:
    """Tests for the Yahoo Finance price history fetcher."""

    @pytest.mark.skip(reason="Implementation pending")
    @pytest.mark.network
    def test_returns_list_of_dicts(self) -> None:
        result = fetch_price_history(
            symbol="AAPL",
            start_date="2024-01-01",
            end_date="2024-01-31",
        )
        assert isinstance(result, list)
        assert all(isinstance(r, dict) for r in result)

    @pytest.mark.skip(reason="Implementation pending")
    @pytest.mark.network
    def test_contains_required_fields(self) -> None:
        result = fetch_price_history(
            symbol="VTI",
            start_date="2024-01-01",
            end_date="2024-01-05",
        )
        required_keys = {"date", "open", "high", "low", "close", "volume"}
        for row in result:
            assert required_keys.issubset(row.keys())
