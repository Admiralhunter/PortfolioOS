"""Tests for FRED market data adapter."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from portfolioos.market.fred import (
    _get_fred_client,
    fetch_multiple_series,
    fetch_series,
    fetch_series_info,
)


def _patch_require():
    """Patch _require_fredapi to return a mock Fred class + real pandas."""
    return patch(
        "portfolioos.market.fred._require_fredapi",
        return_value=(MagicMock(), pd),
    )


class TestGetFredClient:
    """Tests for FRED client creation."""

    def test_missing_api_key_raises(self):
        mock_fred_cls = MagicMock()
        with (
            patch(
                "portfolioos.market.fred._require_fredapi",
                return_value=(mock_fred_cls, pd),
            ),
            patch.dict("os.environ", {}, clear=True),
            pytest.raises(ValueError, match="FRED API key required"),
        ):
            _get_fred_client(api_key=None)

    def test_explicit_api_key(self):
        mock_fred_cls = MagicMock()
        with patch(
            "portfolioos.market.fred._require_fredapi",
            return_value=(mock_fred_cls, pd),
        ):
            _get_fred_client(api_key="test-key-123")
            mock_fred_cls.assert_called_once_with(api_key="test-key-123")

    def test_env_var_api_key(self):
        mock_fred_cls = MagicMock()
        with (
            patch(
                "portfolioos.market.fred._require_fredapi",
                return_value=(mock_fred_cls, pd),
            ),
            patch.dict("os.environ", {"FRED_API_KEY": "env-key-456"}),
        ):
            _get_fred_client(api_key=None)
            mock_fred_cls.assert_called_once_with(api_key="env-key-456")


class TestFetchSeries:
    """Tests for FRED series fetcher (mocked)."""

    def test_empty_series_id_raises(self):
        with pytest.raises(ValueError, match="non-empty"):
            fetch_series("", "2024-01-01", "2024-06-30", api_key="test")

    def test_returns_list_of_dicts(self):
        mock_client = MagicMock()
        idx = pd.DatetimeIndex(["2024-01-01", "2024-02-01", "2024-03-01"])
        mock_client.get_series.return_value = pd.Series([5.33, 5.33, 5.33], index=idx)

        with (
            _patch_require(),
            patch(
                "portfolioos.market.fred._get_fred_client",
                return_value=mock_client,
            ),
        ):
            result = fetch_series(
                "FEDFUNDS", "2024-01-01", "2024-06-30", api_key="test"
            )

        assert isinstance(result, list)
        assert len(result) == 3
        assert all(isinstance(r, dict) for r in result)

    def test_contains_required_fields(self):
        mock_client = MagicMock()
        idx = pd.DatetimeIndex(["2024-01-01"])
        mock_client.get_series.return_value = pd.Series([308.417], index=idx)

        with (
            _patch_require(),
            patch(
                "portfolioos.market.fred._get_fred_client",
                return_value=mock_client,
            ),
        ):
            result = fetch_series(
                "CPIAUCSL", "2024-01-01", "2024-03-31", api_key="test"
            )

        required_keys = {"date", "value", "series_id"}
        for row in result:
            assert required_keys.issubset(row.keys())

    def test_empty_result(self):
        mock_client = MagicMock()
        mock_client.get_series.return_value = pd.Series(dtype=float)

        with (
            _patch_require(),
            patch(
                "portfolioos.market.fred._get_fred_client",
                return_value=mock_client,
            ),
        ):
            result = fetch_series("UNKNOWN", "2024-01-01", "2024-06-30", api_key="test")

        assert result == []

    def test_nan_values_dropped(self):
        mock_client = MagicMock()
        idx = pd.DatetimeIndex(["2024-01-01", "2024-02-01", "2024-03-01"])
        mock_client.get_series.return_value = pd.Series(
            [5.33, float("nan"), 5.25], index=idx
        )

        with (
            _patch_require(),
            patch(
                "portfolioos.market.fred._get_fred_client",
                return_value=mock_client,
            ),
        ):
            result = fetch_series(
                "FEDFUNDS", "2024-01-01", "2024-06-30", api_key="test"
            )

        assert len(result) == 2
        assert all(r["value"] == r["value"] for r in result)  # no NaN

    def test_series_id_uppercased(self):
        mock_client = MagicMock()
        idx = pd.DatetimeIndex(["2024-01-01"])
        mock_client.get_series.return_value = pd.Series([3.5], index=idx)

        with (
            _patch_require(),
            patch(
                "portfolioos.market.fred._get_fred_client",
                return_value=mock_client,
            ),
        ):
            result = fetch_series(
                "fedfunds", "2024-01-01", "2024-06-30", api_key="test"
            )

        assert result[0]["series_id"] == "FEDFUNDS"


class TestFetchMultipleSeries:
    """Tests for batch FRED series fetcher."""

    @patch("portfolioos.market.fred.fetch_series")
    def test_fetches_all_series(self, mock_fetch):
        mock_fetch.return_value = [
            {"date": "2024-01-01", "value": 1.0, "series_id": "A"},
        ]

        result = fetch_multiple_series(
            ["FEDFUNDS", "UNRATE"],
            "2024-01-01",
            "2024-06-30",
            api_key="test",
        )
        assert len(result) == 2
        assert "FEDFUNDS" in result
        assert "UNRATE" in result

    @patch("portfolioos.market.fred.fetch_series")
    def test_failed_series_omitted(self, mock_fetch):
        def side_effect(series_id, *args, **kwargs):
            if series_id == "BAD":
                raise RuntimeError("API error")
            return [
                {"date": "2024-01-01", "value": 1.0, "series_id": series_id},
            ]

        mock_fetch.side_effect = side_effect

        result = fetch_multiple_series(
            ["FEDFUNDS", "BAD", "UNRATE"],
            "2024-01-01",
            "2024-06-30",
            api_key="test",
        )
        assert len(result) == 2
        assert "BAD" not in result


class TestFetchSeriesInfo:
    """Tests for FRED series metadata."""

    def test_empty_series_id_raises(self):
        with pytest.raises(ValueError, match="non-empty"):
            fetch_series_info("", api_key="test")

    @patch("portfolioos.market.fred._get_fred_client")
    def test_returns_metadata(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get_series_info.return_value = {
            "id": "FEDFUNDS",
            "title": "Federal Funds Effective Rate",
            "frequency": "Monthly",
            "units": "Percent",
            "seasonal_adjustment": "Not Seasonally Adjusted",
            "last_updated": "2024-07-01",
        }

        result = fetch_series_info("FEDFUNDS", api_key="test")
        assert result["series_id"] == "FEDFUNDS"
        assert result["title"] == "Federal Funds Effective Rate"
        assert result["frequency"] == "Monthly"
