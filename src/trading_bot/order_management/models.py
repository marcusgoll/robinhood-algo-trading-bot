"""Order management domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

OrderSide = Literal["BUY", "SELL"]
ExecutionMode = Literal["PAPER", "LIVE"]
OrderType = Literal["limit"]
OrderState = Literal[
    "queued",
    "confirmed",
    "partially_filled",
    "filled",
    "cancelled",
    "rejected",
]


@dataclass(slots=True)
class OrderRequest:
    """Intent to submit an order to the broker."""

    symbol: str
    side: OrderSide
    quantity: int
    reference_price: Decimal
    order_type: OrderType = "limit"
    time_in_force: str = "gfd"
    extended_hours: bool = False


@dataclass(slots=True)
class PriceOffsetConfig:
    """Resolved offsets for a particular submission context."""

    offset_mode: Literal["bps", "absolute"]
    buy_offset: float
    sell_offset: float
    max_slippage_pct: float
    strategy_name: str | None = None


@dataclass(slots=True)
class OrderEnvelope:
    """Audit-friendly record returned after submitting an order."""

    order_id: str
    symbol: str
    side: OrderSide
    quantity: int
    limit_price: Decimal
    execution_mode: ExecutionMode
    submitted_at: datetime
    order_type: OrderType = "limit"
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class OrderStatus:
    """Normalized broker status payload."""

    order_id: str
    state: OrderState
    symbol: str
    side: OrderSide
    filled_quantity: int
    average_fill_price: Decimal | None
    pending_quantity: int
    updated_at: datetime
    raw: dict[str, Any] = field(default_factory=dict)
