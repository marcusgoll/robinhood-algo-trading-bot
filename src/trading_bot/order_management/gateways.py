"""Broker gateway wrappers for order submission and status tracking."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from trading_bot.error_handling.exceptions import RetriableError
from trading_bot.error_handling.retry import with_retry

from .calculator import compute_limit_price
from .exceptions import (
    OrderCancellationError,
    OrderStatusError,
    OrderSubmissionError,
)
from .models import OrderEnvelope, OrderRequest, OrderStatus, PriceOffsetConfig

logger = logging.getLogger(__name__)

try:  # pragma: no cover - import guarded for runtime only
    import robin_stocks.robinhood as _robin_stocks  # type: ignore
except ImportError:  # pragma: no cover
    _robin_stocks = None  # type: ignore


def _create_mock_order_response(
    symbol: str,
    side: str,
    quantity: int,
    limit_price: Decimal,
) -> dict[str, Any]:
    """Create a mock order response for paper trading mode.

    Returns a simulated order response that mimics Robinhood API format
    without making any actual API calls.

    Args:
        symbol: Stock ticker symbol
        side: Order side (buy/sell)
        quantity: Number of shares
        limit_price: Limit price per share

    Returns:
        Mock order response dict compatible with OrderEnvelope
    """
    order_id = f"paper-{uuid.uuid4()}"
    timestamp = datetime.now(UTC).isoformat()

    logger.info(
        f"[PAPER] Mock {side.upper()} order created: {quantity} shares of {symbol} @ ${limit_price}"
    )

    return {
        "id": order_id,
        "symbol": symbol,
        "side": side,
        "quantity": str(quantity),
        "price": str(limit_price),
        "state": "filled",  # Paper trades auto-fill immediately
        "type": "limit",
        "time_in_force": "gtc",
        "created_at": timestamp,
        "updated_at": timestamp,
        "cumulative_quantity": str(quantity),  # Instantly filled
        "average_price": str(limit_price),
        "fees": "0.00",
        "paper_trading": True,
    }


def submit_limit_buy(
    order: OrderRequest,
    offsets: PriceOffsetConfig,
    *,
    execution_mode: str,
) -> OrderEnvelope:
    """Submit a limit BUY order.

    In PAPER mode: Returns mock order without calling Robinhood API.
    In LIVE mode: Submits real order via robin_stocks.

    Args:
        order: Order request details
        offsets: Price offset configuration
        execution_mode: "PAPER" or "LIVE"

    Returns:
        OrderEnvelope with order details
    """
    limit_price = compute_limit_price(order, offsets)
    submitted_at = datetime.now(UTC)

    # PAPER MODE: Use mock order, NO Robinhood API calls
    if execution_mode.upper() == "PAPER":
        response = _create_mock_order_response(
            symbol=order.symbol,
            side="buy",
            quantity=order.quantity,
            limit_price=limit_price,
        )
        order_id = _extract_order_id(response)

        return OrderEnvelope(
            order_id=order_id,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            limit_price=limit_price,
            execution_mode="PAPER",  # type: ignore[arg-type]
            submitted_at=submitted_at,
            raw=response,
        )

    # LIVE MODE: Call Robinhood API
    broker = _require_broker()

    @with_retry()
    def _call() -> dict[str, Any]:
        try:
            return broker.orders.order_buy_limit(
                symbol=order.symbol,
                quantity=order.quantity,
                limitPrice=float(limit_price),
                timeInForce=order.time_in_force,
                extendedHours=order.extended_hours,
            )
        except Exception as exc:  # noqa: BLE001
            raise RetriableError(str(exc)) from exc

    try:
        response = _call()
    except Exception as exc:  # noqa: BLE001
        raise OrderSubmissionError(str(exc)) from exc

    order_id = _extract_order_id(response)

    return OrderEnvelope(
        order_id=order_id,
        symbol=order.symbol,
        side=order.side,
        quantity=order.quantity,
        limit_price=limit_price,
        execution_mode=execution_mode.upper(),  # type: ignore[arg-type]
        submitted_at=submitted_at,
        raw=response,
    )


def submit_limit_sell(
    order: OrderRequest,
    offsets: PriceOffsetConfig,
    *,
    execution_mode: str,
) -> OrderEnvelope:
    """Submit a limit SELL order.

    In PAPER mode: Returns mock order without calling Robinhood API.
    In LIVE mode: Submits real order via robin_stocks.

    Args:
        order: Order request details
        offsets: Price offset configuration
        execution_mode: "PAPER" or "LIVE"

    Returns:
        OrderEnvelope with order details
    """
    limit_price = compute_limit_price(order, offsets)
    submitted_at = datetime.now(UTC)

    # PAPER MODE: Use mock order, NO Robinhood API calls
    if execution_mode.upper() == "PAPER":
        response = _create_mock_order_response(
            symbol=order.symbol,
            side="sell",
            quantity=order.quantity,
            limit_price=limit_price,
        )
        order_id = _extract_order_id(response)

        return OrderEnvelope(
            order_id=order_id,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            limit_price=limit_price,
            execution_mode="PAPER",  # type: ignore[arg-type]
            submitted_at=submitted_at,
            raw=response,
        )

    # LIVE MODE: Call Robinhood API
    broker = _require_broker()

    @with_retry()
    def _call() -> dict[str, Any]:
        try:
            return broker.orders.order_sell_limit(
                symbol=order.symbol,
                quantity=order.quantity,
                limitPrice=float(limit_price),
                timeInForce=order.time_in_force,
                extendedHours=order.extended_hours,
            )
        except Exception as exc:  # noqa: BLE001
            raise RetriableError(str(exc)) from exc

    try:
        response = _call()
    except Exception as exc:  # noqa: BLE001
        raise OrderSubmissionError(str(exc)) from exc

    order_id = _extract_order_id(response)

    return OrderEnvelope(
        order_id=order_id,
        symbol=order.symbol,
        side=order.side,
        quantity=order.quantity,
        limit_price=limit_price,
        execution_mode=execution_mode.upper(),  # type: ignore[arg-type]
        submitted_at=submitted_at,
        raw=response,
    )


def cancel_all_equity_orders() -> list[str]:
    """Cancel all open equity orders and return list of cancelled IDs."""

    broker = _require_broker()

    @with_retry()
    def _fetch_open() -> list[dict[str, Any]]:
        try:
            return list(broker.orders.get_all_open_stock_orders() or [])
        except Exception as exc:  # noqa: BLE001
            raise RetriableError(str(exc)) from exc

    try:
        open_orders = _fetch_open()
    except Exception as exc:  # noqa: BLE001
        raise OrderCancellationError(str(exc)) from exc

    cancelled: list[str] = []
    failures: list[str] = []

    for order in open_orders:
        order_id = str(order.get("id", ""))
        if not order_id:
            continue

        @with_retry()
        def _cancel(current_order_id: str = order_id) -> Any:
            try:
                return broker.orders.cancel_stock_order(current_order_id)
            except Exception as exc:  # noqa: BLE001
                raise RetriableError(str(exc)) from exc

        try:
            _cancel()
            cancelled.append(order_id)
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{order_id}: {exc}")

    if failures:
        raise OrderCancellationError(
            "Failed to cancel orders: " + ", ".join(failures)
        )

    return cancelled


def fetch_order_status(order_id: str) -> OrderStatus:
    """Fetch latest broker status for the given order id."""

    broker = _require_broker()

    @with_retry()
    def _call() -> dict[str, Any] | None:
        try:
            return broker.orders.get_stock_order_info(order_id)
        except Exception as exc:  # noqa: BLE001
            raise RetriableError(str(exc)) from exc

    try:
        payload = _call()
    except Exception as exc:  # noqa: BLE001
        raise OrderStatusError(str(exc)) from exc

    if not payload:
        raise OrderStatusError(f"Order {order_id} not found")

    return _normalize_status_payload(payload)


def _normalize_status_payload(payload: dict[str, Any]) -> OrderStatus:
    state = str(payload.get("state", "unknown")).lower()
    symbol = str(payload.get("symbol", "")).upper()
    side = str(payload.get("side", "")).upper() or "BUY"

    quantity = _coerce_int(payload.get("quantity"), default=0)
    filled_quantity = _coerce_int(
        payload.get("cumulative_quantity"),
        default=_coerce_int(payload.get("filled_quantity"), default=0),
    )
    pending_quantity = max(quantity - filled_quantity, 0)

    average_price_raw = payload.get("average_price") or payload.get("average_fill_price")
    average_fill_price = (
        Decimal(str(average_price_raw)) if average_price_raw not in (None, "") else None
    )

    updated_at_raw = payload.get("last_transaction_at") or payload.get("updated_at")
    updated_at = _parse_timestamp(updated_at_raw)

    return OrderStatus(
        order_id=str(payload.get("id", "")),
        state=state,  # type: ignore[arg-type]
        symbol=symbol,
        side=side,  # type: ignore[arg-type]
        filled_quantity=filled_quantity,
        average_fill_price=average_fill_price,
        pending_quantity=pending_quantity,
        updated_at=updated_at,
        raw=payload,
    )


def _parse_timestamp(value: Any) -> datetime:
    if not value:
        return datetime.now(UTC)

    if isinstance(value, datetime):
        return value.astimezone(UTC)

    text = str(value)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    try:
        return datetime.fromisoformat(text).astimezone(UTC)
    except ValueError as exc:  # noqa: BLE001
        raise OrderStatusError(f"Invalid timestamp format: {value}") from exc


def _coerce_int(value: Any, *, default: int = 0) -> int:
    if value in (None, ""):
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):  # noqa: BLE001
        return default


def _extract_order_id(response: Any) -> str:
    if isinstance(response, dict) and response.get("id"):
        return str(response["id"])
    raise OrderSubmissionError("Broker response missing order id")


def _require_broker():
    if _robin_stocks is None:
        raise OrderSubmissionError("robin_stocks library is not available")
    return _robin_stocks
