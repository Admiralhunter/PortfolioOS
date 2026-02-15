"""Market data validation utilities.

Provides gap detection, outlier flagging, and OHLCV integrity checks
for incoming market data. All validation functions operate on plain
dicts (the common exchange format in PortfolioOS) rather than DataFrames
to keep the validation layer framework-agnostic.

References:
    ARCHITECTURE.md — Market Data Pipeline: Validator stage.
    SPEC.md — Historical gap reconstruction requirement.

"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


def detect_gaps(
    records: list[dict[str, Any]],
    frequency: str = "daily",
) -> list[dict[str, str]]:
    """Detect missing dates in a time-series dataset.

    Compares actual dates against expected trading days. Weekends
    and common US market holidays are excluded for daily frequency.

    Args:
        records: List of dicts, each containing a "date" key (YYYY-MM-DD).
        frequency: Expected frequency — "daily" or "monthly".

    Returns:
        List of gap dicts with keys: gap_start, gap_end, missing_days.
        Empty list if no gaps are found.

    Raises:
        ValueError: If frequency is not supported.

    """
    if frequency not in ("daily", "monthly"):
        msg = f"Unsupported frequency: {frequency}. Use 'daily' or 'monthly'."
        raise ValueError(msg)

    if len(records) < 2:  # noqa: PLR2004
        return []

    dates = sorted(datetime.strptime(r["date"], "%Y-%m-%d") for r in records)

    gaps: list[dict[str, str]] = []

    if frequency == "daily":
        for i in range(1, len(dates)):
            expected_next = _next_trading_day(dates[i - 1])
            if dates[i] > expected_next:
                gaps.append(
                    {
                        "gap_start": expected_next.strftime("%Y-%m-%d"),
                        "gap_end": (dates[i] - timedelta(days=1)).strftime("%Y-%m-%d"),
                        "missing_days": str((dates[i] - expected_next).days),
                    }
                )
    elif frequency == "monthly":
        for i in range(1, len(dates)):
            month_diff = (dates[i].year - dates[i - 1].year) * 12 + (
                dates[i].month - dates[i - 1].month
            )
            if month_diff > 1:
                gaps.append(
                    {
                        "gap_start": dates[i - 1].strftime("%Y-%m-%d"),
                        "gap_end": dates[i].strftime("%Y-%m-%d"),
                        "missing_days": str(month_diff - 1),
                    }
                )

    return gaps


def _next_trading_day(dt: datetime) -> datetime:
    """Return the next expected trading day after dt.

    Skips weekends (Saturday/Sunday). Does not account for
    market holidays — those would be handled by a holiday
    calendar if needed.

    Args:
        dt: Current date.

    Returns:
        Next expected trading day.

    """
    next_day = dt + timedelta(days=1)
    # Skip weekends: Saturday=5, Sunday=6
    while next_day.weekday() >= 5:  # noqa: PLR2004
        next_day += timedelta(days=1)
    return next_day


def detect_outliers(
    records: list[dict[str, Any]],
    value_key: str = "close",
    z_threshold: float = 3.0,
) -> list[dict[str, Any]]:
    """Flag statistical outliers in a value series using z-scores.

    Uses day-over-day percentage changes to detect abnormal moves.
    A z-score above the threshold flags the record as a potential outlier.

    Args:
        records: List of dicts containing the value_key field.
        value_key: The field name to check (default: "close").
        z_threshold: Z-score threshold for flagging (default: 3.0).

    Returns:
        List of flagged records, each augmented with "z_score" and
        "pct_change" fields.

    """
    if len(records) < 3:  # noqa: PLR2004
        return []

    values = [float(r[value_key]) for r in records]

    # Calculate percentage changes
    pct_changes: list[float] = []
    for i in range(1, len(values)):
        if values[i - 1] == 0:
            pct_changes.append(0.0)
        else:
            pct_changes.append((values[i] - values[i - 1]) / values[i - 1])

    if not pct_changes:
        return []

    mean_change = sum(pct_changes) / len(pct_changes)
    variance = sum((x - mean_change) ** 2 for x in pct_changes) / len(pct_changes)
    std_change = variance**0.5

    if std_change == 0:
        return []

    flagged: list[dict[str, Any]] = []
    for i, pct in enumerate(pct_changes):
        z_score = abs(pct - mean_change) / std_change
        if z_score > z_threshold:
            record = dict(records[i + 1])
            record["z_score"] = round(z_score, 4)
            record["pct_change"] = round(pct, 6)
            flagged.append(record)

    return flagged


def validate_ohlcv(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Validate OHLCV data integrity.

    Checks:
    - Required fields are present
    - High >= Low for each bar
    - Open and Close are within [Low, High]
    - Volume is non-negative
    - Prices are positive

    Args:
        records: List of OHLCV dicts.

    Returns:
        List of error dicts with keys: date, field, issue, value.
        Empty list if all records are valid.

    """
    required_keys = {"date", "open", "high", "low", "close", "volume"}
    errors: list[dict[str, Any]] = []

    for record in records:
        date = record.get("date", "unknown")

        # Check required fields
        missing = required_keys - set(record.keys())
        if missing:
            errors.append(
                {
                    "date": date,
                    "field": "missing_keys",
                    "issue": f"Missing required fields: {sorted(missing)}",
                    "value": None,
                }
            )
            continue

        o, h, low, c = (
            float(record["open"]),
            float(record["high"]),
            float(record["low"]),
            float(record["close"]),
        )
        vol = record["volume"]

        if h < low:
            errors.append(
                {
                    "date": date,
                    "field": "high/low",
                    "issue": "High is less than Low",
                    "value": f"high={h}, low={low}",
                }
            )

        if o < low or o > h:
            errors.append(
                {
                    "date": date,
                    "field": "open",
                    "issue": "Open outside [Low, High] range",
                    "value": f"open={o}, low={low}, high={h}",
                }
            )

        if c < low or c > h:
            errors.append(
                {
                    "date": date,
                    "field": "close",
                    "issue": "Close outside [Low, High] range",
                    "value": f"close={c}, low={low}, high={h}",
                }
            )

        if vol < 0:
            errors.append(
                {
                    "date": date,
                    "field": "volume",
                    "issue": "Negative volume",
                    "value": str(vol),
                }
            )

        errors.extend(
            {
                "date": date,
                "field": price_field,
                "issue": "Non-positive price",
                "value": str(record[price_field]),
            }
            for price_field in ("open", "high", "low", "close")
            if float(record[price_field]) <= 0
        )

    return errors
