"""Offset calculations and validation helpers for order management."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from ..config import OrderManagementConfig

from .exceptions import UnsupportedOrderTypeError
from .models import OrderRequest, PriceOffsetConfig


def resolve_strategy_offsets(
    config: OrderManagementConfig, strategy_name: str | None
) -> PriceOffsetConfig:
    """Return resolved offsets for the given strategy name."""

    overrides = {}
    if strategy_name:
        overrides = config.strategy_overrides.get(strategy_name, {})

    offset_mode = overrides.get("offset_mode", config.offset_mode)
    buy_offset = float(overrides.get("buy_offset", config.buy_offset))
    sell_offset = float(overrides.get("sell_offset", config.sell_offset))
    max_slippage = float(overrides.get("max_slippage_pct", config.max_slippage_pct))

    return PriceOffsetConfig(
        offset_mode=offset_mode,  # type: ignore[arg-type]
        buy_offset=buy_offset,
        sell_offset=sell_offset,
        max_slippage_pct=max_slippage,
        strategy_name=strategy_name,
    )


def validate_order_request(
    order: OrderRequest, config: OrderManagementConfig
) -> None:
    """Validate request structure prior to submission."""

    symbol = order.symbol
    if not symbol or not symbol.isalpha() or not symbol.isupper():
        raise ValueError("Order symbol must be uppercase alphabetic characters only")

    if order.quantity <= 0:
        raise ValueError("Order quantity must be greater than zero")

    if order.reference_price <= 0:
        raise ValueError("Reference price must be greater than zero")

    order_type = (order.order_type or "").lower()
    if order_type != "limit":
        raise UnsupportedOrderTypeError(order.order_type)

    config.validate()


def compute_limit_price(
    order: OrderRequest, offsets: PriceOffsetConfig
) -> Decimal:
    """Compute limit price applying offsets and guardrails."""

    reference = order.reference_price
    if reference <= 0:
        raise ValueError("Reference price must be greater than zero")

    if offsets.offset_mode == "bps":
        if order.side == "BUY":
            adjusted = reference * (
                Decimal("1") - Decimal(str(offsets.buy_offset)) / Decimal("10000")
            )
        else:
            adjusted = reference * (
                Decimal("1") + Decimal(str(offsets.sell_offset)) / Decimal("10000")
            )
    else:  # absolute offsets
        delta = Decimal(
            str(offsets.buy_offset if order.side == "BUY" else offsets.sell_offset)
        )
        adjusted = reference - delta if order.side == "BUY" else reference + delta

    if adjusted <= 0:
        raise ValueError("Computed limit price must be positive")

    limit_price = adjusted.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    if limit_price < adjusted:
        limit_price += Decimal("0.01")

    _enforce_slippage(reference, limit_price, offsets.max_slippage_pct)

    return limit_price


def _enforce_slippage(reference: Decimal, limit_price: Decimal, max_pct: float) -> None:
    if reference <= 0:
        raise ValueError("Reference price must be positive for slippage checks")

    delta = abs(reference - limit_price)
    delta_pct = (delta / reference) * Decimal("100")

    if delta_pct > Decimal(str(max_pct)):
        raise ValueError(
            "Computed limit price exceeds configured slippage guard"
        )
