"""Cost basis tracking for portfolio tax lot management.

Implements FIFO, LIFO, specific lot identification, and average cost
methods for computing realized and unrealized gains per tax lot.

References:
    IRS Publication 550 — "Investment Income and Expenses."
    Specific identification allows investors to designate which
    shares to sell, potentially optimizing tax outcomes.

"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

# Holding period threshold for long-term capital gains (days)
_LONG_TERM_DAYS = 365


@dataclass
class TaxLot:
    """A single tax lot representing a purchase of shares.

    Attributes:
        date: Date the lot was acquired (YYYY-MM-DD).
        quantity: Number of shares originally purchased.
        price: Price per share at acquisition.
        fees: Transaction fees paid.
        remaining_qty: Shares still held from this lot.
        lot_id: Optional identifier for specific lot selection.

    """

    date: str
    quantity: float
    price: float
    fees: float = 0.0
    remaining_qty: float = 0.0
    lot_id: str = ""

    def __post_init__(self) -> None:
        """Initialize remaining quantity to purchase quantity if not set."""
        if self.remaining_qty == 0.0:
            self.remaining_qty = self.quantity


@dataclass
class DisposedLot:
    """Result of selling shares from a specific tax lot.

    Attributes:
        lot_date: Original acquisition date.
        qty_sold: Number of shares sold from this lot.
        proceeds: Sale proceeds for these shares.
        cost_basis: Cost basis for the shares sold.
        gain_loss: Realized gain (positive) or loss (negative).
        holding_period: "short_term" (<1 year) or "long_term" (>=1 year).

    """

    lot_date: str
    qty_sold: float
    proceeds: float
    cost_basis: float
    gain_loss: float
    holding_period: str


@dataclass
class UnrealizedGain:
    """Unrealized gain/loss for shares in a single tax lot.

    Attributes:
        lot_date: Original acquisition date.
        shares: Number of shares remaining.
        cost_basis: Total cost basis for remaining shares.
        market_value: Current market value of remaining shares.
        unrealized_gain: Market value minus cost basis.
        holding_period: "short_term" or "long_term" based on current date.

    """

    lot_date: str
    shares: float
    cost_basis: float
    market_value: float
    unrealized_gain: float
    holding_period: str


@dataclass
class CostBasisTracker:
    """Track tax lots and compute cost basis using various methods.

    Supports FIFO, LIFO, average cost, and specific lot identification.
    Maintains a list of tax lots and handles partial dispositions.

    """

    lots: list[TaxLot] = field(default_factory=list)
    _next_lot_id: int = field(default=0, repr=False)

    def add_buy(
        self,
        date: str,
        quantity: float,
        price: float,
        fees: float = 0.0,
    ) -> str:
        """Record a purchase, creating a new tax lot.

        Args:
            date: Purchase date (YYYY-MM-DD).
            quantity: Number of shares purchased.
            price: Price per share.
            fees: Transaction fees.

        Returns:
            The lot_id assigned to this purchase.

        """
        lot_id = f"lot-{self._next_lot_id}"
        self._next_lot_id += 1
        self.lots.append(
            TaxLot(
                date=date,
                quantity=quantity,
                price=price,
                fees=fees,
                remaining_qty=quantity,
                lot_id=lot_id,
            )
        )
        return lot_id

    def sell(
        self,
        date: str,
        quantity: float,
        price: float,
        fees: float = 0.0,
        method: str = "fifo",
        lot_ids: list[str] | None = None,
    ) -> list[DisposedLot]:
        """Sell shares using the specified cost basis method.

        Args:
            date: Sale date (YYYY-MM-DD).
            quantity: Number of shares to sell.
            price: Sale price per share.
            fees: Transaction fees for the sale.
            method: Cost basis method — "fifo", "lifo", "average_cost",
                or "specific_id".
            lot_ids: Required when method is "specific_id". List of lot
                IDs to sell from.

        Returns:
            List of DisposedLot records showing per-lot disposition.

        Raises:
            ValueError: If insufficient shares, unknown method, or
                specific_id without lot_ids.

        """
        total_available = self.get_total_shares()
        if quantity > total_available + 1e-9:
            msg = (
                f"Insufficient shares: requested {quantity}, "
                f"available {total_available}"
            )
            raise ValueError(msg)

        if method == "fifo":
            return self._sell_fifo(date, quantity, price, fees)
        if method == "lifo":
            return self._sell_lifo(date, quantity, price, fees)
        if method == "average_cost":
            return self._sell_average_cost(date, quantity, price, fees)
        if method == "specific_id":
            if not lot_ids:
                msg = "lot_ids required for specific_id method"
                raise ValueError(msg)
            return self._sell_specific(date, quantity, price, fees, lot_ids)
        msg = f"Unknown method: {method}. Use fifo, lifo, average_cost, or specific_id"
        raise ValueError(msg)

    def _sell_fifo(
        self,
        date: str,
        quantity: float,
        price: float,
        fees: float,
    ) -> list[DisposedLot]:
        """Dispose lots in first-in, first-out order."""
        return self._dispose_ordered(date, quantity, price, fees, reverse=False)

    def _sell_lifo(
        self,
        date: str,
        quantity: float,
        price: float,
        fees: float,
    ) -> list[DisposedLot]:
        """Dispose lots in last-in, first-out order."""
        return self._dispose_ordered(date, quantity, price, fees, reverse=True)

    def _dispose_ordered(
        self,
        date: str,
        quantity: float,
        price: float,
        fees: float,
        *,
        reverse: bool,
    ) -> list[DisposedLot]:
        """Dispose lots in chronological or reverse order."""
        remaining_to_sell = quantity
        total_proceeds = quantity * price - fees
        disposed: list[DisposedLot] = []

        indices = list(range(len(self.lots)))
        if reverse:
            indices = indices[::-1]

        active = [(i, self.lots[i]) for i in indices if self.lots[i].remaining_qty > 0]

        for _idx, lot in active:
            if remaining_to_sell <= 1e-9:
                break

            sell_from_lot = min(lot.remaining_qty, remaining_to_sell)
            lot_cost = sell_from_lot * lot.price + (
                lot.fees * sell_from_lot / lot.quantity
            )
            lot_proceeds = total_proceeds * (sell_from_lot / quantity)
            gain = lot_proceeds - lot_cost
            period = _holding_period(lot.date, date)

            disposed.append(
                DisposedLot(
                    lot_date=lot.date,
                    qty_sold=sell_from_lot,
                    proceeds=lot_proceeds,
                    cost_basis=lot_cost,
                    gain_loss=gain,
                    holding_period=period,
                )
            )

            lot.remaining_qty -= sell_from_lot
            remaining_to_sell -= sell_from_lot

        return disposed

    def _sell_average_cost(
        self,
        date: str,
        quantity: float,
        price: float,
        fees: float,
    ) -> list[DisposedLot]:
        """Dispose using average cost basis across all lots."""
        total_shares = self.get_total_shares()
        total_cost = self.get_total_cost_basis()
        avg_cost_per_share = total_cost / total_shares if total_shares > 0 else 0.0

        total_proceeds = quantity * price - fees
        cost_basis = quantity * avg_cost_per_share
        gain = total_proceeds - cost_basis

        # Find earliest lot date for holding period
        active_lots = [lot for lot in self.lots if lot.remaining_qty > 0]
        earliest_date = min(lot.date for lot in active_lots) if active_lots else date
        period = _holding_period(earliest_date, date)

        # Reduce shares proportionally from all lots (FIFO order)
        remaining_to_sell = quantity
        for lot in self.lots:
            if remaining_to_sell <= 1e-9:
                break
            if lot.remaining_qty <= 0:
                continue
            sell_from_lot = min(lot.remaining_qty, remaining_to_sell)
            lot.remaining_qty -= sell_from_lot
            remaining_to_sell -= sell_from_lot

        return [
            DisposedLot(
                lot_date=earliest_date,
                qty_sold=quantity,
                proceeds=total_proceeds,
                cost_basis=cost_basis,
                gain_loss=gain,
                holding_period=period,
            )
        ]

    def _sell_specific(
        self,
        date: str,
        quantity: float,
        price: float,
        fees: float,
        lot_ids: list[str],
    ) -> list[DisposedLot]:
        """Dispose from specific identified lots."""
        lot_map = {lot.lot_id: lot for lot in self.lots}
        for lid in lot_ids:
            if lid not in lot_map:
                msg = f"Lot '{lid}' not found"
                raise ValueError(msg)

        remaining_to_sell = quantity
        total_proceeds = quantity * price - fees
        disposed: list[DisposedLot] = []

        for lid in lot_ids:
            if remaining_to_sell <= 1e-9:
                break

            lot = lot_map[lid]
            sell_from_lot = min(lot.remaining_qty, remaining_to_sell)
            lot_cost = sell_from_lot * lot.price + (
                lot.fees * sell_from_lot / lot.quantity
            )
            lot_proceeds = total_proceeds * (sell_from_lot / quantity)
            gain = lot_proceeds - lot_cost
            period = _holding_period(lot.date, date)

            disposed.append(
                DisposedLot(
                    lot_date=lot.date,
                    qty_sold=sell_from_lot,
                    proceeds=lot_proceeds,
                    cost_basis=lot_cost,
                    gain_loss=gain,
                    holding_period=period,
                )
            )

            lot.remaining_qty -= sell_from_lot
            remaining_to_sell -= sell_from_lot

        if remaining_to_sell > 1e-9:
            msg = (
                f"Insufficient shares in specified lots: "
                f"still need {remaining_to_sell}"
            )
            raise ValueError(msg)

        return disposed

    def get_unrealized_gains(
        self,
        current_price: float,
        as_of_date: str | None = None,
    ) -> list[UnrealizedGain]:
        """Compute unrealized gains per tax lot.

        Args:
            current_price: Current market price per share.
            as_of_date: Date for holding period calculation (YYYY-MM-DD).
                Defaults to today.

        Returns:
            List of UnrealizedGain records for each lot with remaining shares.

        """
        if as_of_date is None:
            as_of_date = datetime.now().strftime("%Y-%m-%d")  # noqa: DTZ005

        gains: list[UnrealizedGain] = []
        for lot in self.lots:
            if lot.remaining_qty <= 0:
                continue

            cost = lot.remaining_qty * lot.price + (
                lot.fees * lot.remaining_qty / lot.quantity
            )
            market_value = lot.remaining_qty * current_price
            unrealized = market_value - cost
            period = _holding_period(lot.date, as_of_date)

            gains.append(
                UnrealizedGain(
                    lot_date=lot.date,
                    shares=lot.remaining_qty,
                    cost_basis=cost,
                    market_value=market_value,
                    unrealized_gain=unrealized,
                    holding_period=period,
                )
            )

        return gains

    def get_total_cost_basis(self) -> float:
        """Compute total cost basis for all remaining shares.

        Returns:
            Sum of (remaining_qty * price + proportional fees) across all lots.

        """
        total = 0.0
        for lot in self.lots:
            if lot.remaining_qty <= 0:
                continue
            total += lot.remaining_qty * lot.price + (
                lot.fees * lot.remaining_qty / lot.quantity
            )
        return total

    def get_total_shares(self) -> float:
        """Get total remaining shares across all lots.

        Returns:
            Sum of remaining_qty across all lots.

        """
        return sum(lot.remaining_qty for lot in self.lots)

    def to_dict(self) -> dict[str, Any]:
        """Serialize tracker state to a dictionary.

        Returns:
            Dictionary representation of all lots.

        """
        return {
            "lots": [
                {
                    "date": lot.date,
                    "quantity": lot.quantity,
                    "price": lot.price,
                    "fees": lot.fees,
                    "remaining_qty": lot.remaining_qty,
                    "lot_id": lot.lot_id,
                }
                for lot in self.lots
            ],
            "total_shares": self.get_total_shares(),
            "total_cost_basis": self.get_total_cost_basis(),
        }


def _holding_period(acquire_date: str, sell_date: str) -> str:
    """Determine if a holding period is short-term or long-term.

    Args:
        acquire_date: Acquisition date (YYYY-MM-DD).
        sell_date: Sale/evaluation date (YYYY-MM-DD).

    Returns:
        "long_term" if held > 365 days, otherwise "short_term".

    """
    acq = datetime.strptime(acquire_date, "%Y-%m-%d")  # noqa: DTZ007
    sell = datetime.strptime(sell_date, "%Y-%m-%d")  # noqa: DTZ007
    days_held = (sell - acq).days
    return "long_term" if days_held > _LONG_TERM_DAYS else "short_term"
