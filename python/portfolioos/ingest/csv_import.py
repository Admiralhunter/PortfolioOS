"""CSV import pipeline for portfolio transactions.

Parses CSV files into normalized transaction records compatible
with the DuckDB transactions table. Supports flexible column
mapping to handle exports from different brokerages.

Supported brokerage formats (auto-detected):
- Generic: date, symbol, type, quantity, price, fees
- Fidelity: Run Date, Action, Symbol, Quantity, Price, Amount
- Schwab: Date, Action, Symbol, Quantity, Price, Fees & Comm

"""

from __future__ import annotations

import csv
import io
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Known column name mappings from popular brokerages to our canonical format
_COLUMN_ALIASES: dict[str, list[str]] = {
    "date": ["date", "run date", "trade date", "settlement date", "transaction date"],
    "symbol": ["symbol", "ticker", "security", "instrument"],
    "type": ["type", "action", "transaction type", "trans type", "activity"],
    "quantity": ["quantity", "qty", "shares", "units", "amount"],
    "price": ["price", "unit price", "price per share", "cost per share"],
    "fees": ["fees", "commission", "fees & comm", "fee", "commissions"],
    "notes": ["notes", "description", "memo", "details"],
}

# Map brokerage-specific action names to our canonical types
_ACTION_ALIASES: dict[str, str] = {
    "buy": "buy",
    "bought": "buy",
    "purchase": "buy",
    "sell": "sell",
    "sold": "sell",
    "dividend": "dividend",
    "div": "dividend",
    "reinvest dividend": "dividend",
    "split": "split",
    "stock split": "split",
    "transfer": "transfer",
    "transfer in": "transfer",
    "transfer out": "transfer",
    "journal": "transfer",
}


def _normalize_header(header: str) -> str:
    """Normalize a CSV header to lowercase, stripped.

    Args:
        header: Raw column header string.

    Returns:
        Lowercased, stripped header.

    """
    return header.strip().lower()


def _map_columns(raw_headers: list[str]) -> dict[str, int]:
    """Map raw CSV headers to canonical field names.

    Args:
        raw_headers: List of raw header strings from the CSV.

    Returns:
        Dict mapping canonical field name to column index.

    Raises:
        ValueError: If required columns (date, symbol, type) cannot be found.

    """
    normalized = [_normalize_header(h) for h in raw_headers]
    mapping: dict[str, int] = {}

    for canonical, aliases in _COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in normalized:
                mapping[canonical] = normalized.index(alias)
                break

    required = {"date", "symbol"}
    missing = required - set(mapping.keys())
    if missing:
        msg = f"Required columns not found: {sorted(missing)}. Available: {raw_headers}"
        raise ValueError(msg)

    return mapping


def _normalize_action(raw_action: str) -> str:
    """Normalize a transaction action/type string.

    Args:
        raw_action: Raw action string from CSV.

    Returns:
        Canonical transaction type.

    """
    cleaned = raw_action.strip().lower()
    return _ACTION_ALIASES.get(cleaned, cleaned)


def _parse_float(value: str, default: float = 0.0) -> float:
    """Parse a string to float, handling currency symbols and commas.

    Args:
        value: Raw string value.
        default: Default if parsing fails.

    Returns:
        Parsed float value.

    """
    if not value or not value.strip():
        return default
    cleaned = (
        value.strip()
        .replace("$", "")
        .replace(",", "")
        .replace("(", "-")
        .replace(")", "")
    )
    try:
        return float(cleaned)
    except ValueError:
        return default


def parse_csv(
    file_path: str | Path | None = None,
    csv_content: str | None = None,
    account_id: str = "default",
) -> list[dict[str, Any]]:
    """Parse a CSV file or string into normalized transaction records.

    Provide either file_path or csv_content, not both.

    Args:
        file_path: Path to the CSV file.
        csv_content: Raw CSV content as a string.
        account_id: Account to associate transactions with.

    Returns:
        List of transaction dicts with keys: account_id, symbol, type,
        date, quantity, price, fees, notes.

    Raises:
        ValueError: If neither file_path nor csv_content is provided,
            or if required columns are missing.

    """
    if file_path is None and csv_content is None:
        msg = "Provide either file_path or csv_content"
        raise ValueError(msg)

    if file_path is not None:
        path = Path(file_path)
        text = path.read_text(encoding="utf-8")
    else:
        text = csv_content  # type: ignore[assignment]

    reader = csv.reader(io.StringIO(text))
    raw_headers = next(reader)
    col_map = _map_columns(raw_headers)

    transactions: list[dict[str, Any]] = []
    skipped = 0

    for _row_num, row in enumerate(reader, start=2):
        if not any(cell.strip() for cell in row):
            continue

        symbol = row[col_map["symbol"]].strip().upper() if "symbol" in col_map else ""
        if not symbol:
            skipped += 1
            continue

        date_str = row[col_map["date"]].strip() if "date" in col_map else ""
        if not date_str:
            skipped += 1
            continue

        tx_type = "buy"
        if "type" in col_map:
            tx_type = _normalize_action(row[col_map["type"]])

        quantity = (
            _parse_float(row[col_map["quantity"]]) if "quantity" in col_map else 0.0
        )
        price = _parse_float(row[col_map["price"]]) if "price" in col_map else 0.0
        fees = _parse_float(row[col_map["fees"]]) if "fees" in col_map else 0.0
        notes = row[col_map["notes"]].strip() if "notes" in col_map else ""

        transactions.append(
            {
                "account_id": account_id,
                "symbol": symbol,
                "type": tx_type,
                "date": date_str,
                "quantity": abs(quantity),
                "price": abs(price),
                "fees": abs(fees),
                "notes": notes,
            }
        )

    if skipped:
        logger.warning("Skipped %d rows (row numbers starting at line 2)", skipped)

    logger.info("Parsed %d transactions from CSV", len(transactions))
    return transactions
