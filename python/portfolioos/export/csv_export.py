"""CSV export for portfolio data, transactions, and simulation results.

Generates CSV files with metadata headers including export date,
account, and date range information.

"""

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np


def export_holdings_csv(
    holdings: list[dict[str, Any]],
    output_path: str | None = None,
) -> str:
    """Export holdings to CSV format.

    Args:
        holdings: List of holding dicts with keys: account_id, symbol,
            shares, cost_basis, and optionally asset_type.
        output_path: File path to write. If None, returns CSV string.

    Returns:
        The CSV content as a string, or file path if output_path given.

    """
    fieldnames = ["account_id", "symbol", "asset_type", "shares", "cost_basis"]
    output = io.StringIO()

    _write_metadata_header(output, "Holdings Export")

    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for holding in holdings:
        row = {k: holding.get(k, "") for k in fieldnames}
        writer.writerow(row)

    content = output.getvalue()
    if output_path:
        Path(output_path).write_text(content, encoding="utf-8")
        return output_path
    return content


def export_transactions_csv(
    transactions: list[dict[str, Any]],
    output_path: str | None = None,
) -> str:
    """Export transactions to CSV format.

    Args:
        transactions: List of transaction dicts with keys: account_id,
            symbol, type, date, quantity, price, fees, notes.
        output_path: File path to write. If None, returns CSV string.

    Returns:
        The CSV content as a string, or file path if output_path given.

    """
    fieldnames = [
        "account_id", "symbol", "type", "date",
        "quantity", "price", "fees", "notes",
    ]
    output = io.StringIO()

    _write_metadata_header(output, "Transactions Export")

    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for txn in transactions:
        row = {k: txn.get(k, "") for k in fieldnames}
        writer.writerow(row)

    content = output.getvalue()
    if output_path:
        Path(output_path).write_text(content, encoding="utf-8")
        return output_path
    return content


def export_simulation_csv(
    result: dict[str, Any],
    output_path: str | None = None,
) -> str:
    """Export simulation percentile paths to CSV.

    Writes columns for year and each percentile level (5, 25, 50, 75, 95).

    Args:
        result: Simulation result dict with "percentiles" key mapping
            percentile levels to value arrays.
        output_path: File path to write. If None, returns CSV string.

    Returns:
        The CSV content as a string, or file path if output_path given.

    """
    percentiles = result.get("percentiles", {})
    if not percentiles:
        return ""

    output = io.StringIO()
    _write_metadata_header(
        output,
        "Simulation Results Export",
        extra=f"Success Rate: {result.get('success_rate', 'N/A')}",
    )

    # Determine number of years from first percentile array
    first_key = next(iter(percentiles))
    values = percentiles[first_key]
    if isinstance(values, np.ndarray):
        n_points = len(values)
    else:
        n_points = len(values)

    fieldnames = ["year"] + [f"p{p}" for p in sorted(percentiles.keys())]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for yr in range(n_points):
        row: dict[str, Any] = {"year": yr}
        for p_level in sorted(percentiles.keys()):
            vals = percentiles[p_level]
            val = vals[yr] if isinstance(vals, np.ndarray) else vals[yr]
            row[f"p{p_level}"] = f"{float(val):.2f}"
        writer.writerow(row)

    content = output.getvalue()
    if output_path:
        Path(output_path).write_text(content, encoding="utf-8")
        return output_path
    return content


def _write_metadata_header(
    output: io.StringIO,
    title: str,
    extra: str = "",
) -> None:
    """Write metadata comment lines at the top of a CSV export.

    Args:
        output: StringIO buffer to write to.
        title: Export title.
        extra: Optional additional metadata line.

    """
    now = datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    output.write(f"# {title}\n")
    output.write(f"# Generated: {now}\n")
    if extra:
        output.write(f"# {extra}\n")
