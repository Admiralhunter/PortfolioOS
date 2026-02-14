"""Tests for FRED market data adapter."""

from __future__ import annotations

import pytest
from portfolioos.market.fred import fetch_series


class TestFetchSeries:
    """Tests for the FRED data series fetcher."""

    @pytest.mark.skip(reason="Implementation pending")
    @pytest.mark.network
    def test_returns_list_of_dicts(self) -> None:
        result = fetch_series(
            series_id="FEDFUNDS",
            start_date="2024-01-01",
            end_date="2024-06-30",
        )
        assert isinstance(result, list)
        assert all(isinstance(r, dict) for r in result)

    @pytest.mark.skip(reason="Implementation pending")
    @pytest.mark.network
    def test_contains_required_fields(self) -> None:
        result = fetch_series(
            series_id="CPIAUCSL",
            start_date="2024-01-01",
            end_date="2024-03-31",
        )
        required_keys = {"date", "value", "series_id"}
        for row in result:
            assert required_keys.issubset(row.keys())
