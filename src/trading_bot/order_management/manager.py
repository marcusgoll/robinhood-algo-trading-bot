"""Order management service utilities."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from trading_bot.config import OrderManagementConfig

from .calculator import (
    resolve_strategy_offsets,
    validate_order_request,
)
from .exceptions import (
    OrderCancellationError,
    OrderStatusError,
    OrderSubmissionError,
    UnsupportedOrderTypeError,
)
from .gateways import (
    cancel_all_equity_orders,
    fetch_order_status,
    submit_limit_buy,
    submit_limit_sell,
)
from .models import OrderEnvelope, OrderRequest, PriceOffsetConfig


def ensure_limit_order_type(order_type: str) -> None:
    """Assert that the requested order type is supported (limit-only in phase one)."""

    normalized = (order_type or "").lower()
    if normalized != "limit":
        raise UnsupportedOrderTypeError(order_type)


def append_order_log(
    *,
    log_path: Path,
    session_id: str,
    bot_version: str,
    config_hash: str,
    action: str,
    strategy_name: str | None,
    envelope: OrderEnvelope,
    extra: dict[str, Any] | None = None,
) -> None:
    """Append a structured JSONL entry for order events."""

    log_path.parent.mkdir(parents=True, exist_ok=True)

    entry: dict[str, Any] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "session_id": session_id,
        "bot_version": bot_version,
        "config_hash": config_hash,
        "action": action,
        "strategy_name": strategy_name,
        "order_id": envelope.order_id,
        "symbol": envelope.symbol,
        "side": envelope.side,
        "limit_price": str(envelope.limit_price),
        "quantity": envelope.quantity,
        "execution_mode": envelope.execution_mode,
        "submitted_at": envelope.submitted_at.isoformat(),
    }

    if extra:
        entry.update(extra)

    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")


@dataclass
class OrderManager:
    """Coordinates order submission, cancellation, and status sync."""

    config: OrderManagementConfig
    safety_checks: Any
    account_data: Any
    session_id: str
    bot_version: str
    config_hash: str
    order_log_path: Path
    execution_mode: str = "PAPER"

    def __post_init__(self) -> None:
        self._tracked_orders: dict[str, str] = {}  # order_id -> symbol

    # --- Submission -----------------------------------------------------
    def place_limit_order(
        self,
        order: OrderRequest,
        *,
        strategy_name: str | None = None,
    ) -> OrderEnvelope:
        ensure_limit_order_type(order.order_type)
        validate_order_request(order, self.config)

        offsets = resolve_strategy_offsets(self.config, strategy_name)

        envelope = self._submit(order, offsets)
        self._register_tracking(envelope)

        if self.safety_checks:
            self.safety_checks.register_pending_order(
                envelope.symbol, envelope.side, envelope.order_id
            )

        append_order_log(
            log_path=self.order_log_path,
            session_id=self.session_id,
            bot_version=self.bot_version,
            config_hash=self.config_hash,
            action="submit",
            strategy_name=strategy_name,
            envelope=envelope,
            extra={"status": envelope.raw.get("state", "submitted")},
        )

        return envelope

    # --- Cancellation ---------------------------------------------------
    def cancel_order(self, order_id: str) -> None:
        """Cancel a specific order by ID.

        Args:
            order_id: The order ID to cancel

        Raises:
            OrderCancellationError: If cancellation fails
        """
        # Import the broker module
        try:
            import robin_stocks.robinhood as rh  # type: ignore
        except ImportError:
            raise OrderCancellationError("robin_stocks library is not available")

        try:
            rh.orders.cancel_stock_order(order_id)
        except Exception as exc:
            raise OrderCancellationError(f"Failed to cancel order {order_id}: {exc}") from exc

        # Clean up tracking
        symbol = self._tracked_orders.pop(order_id, None)
        if symbol and self.safety_checks:
            self.safety_checks.clear_pending_order(symbol)

        # Log cancellation
        append_order_log(
            log_path=self.order_log_path,
            session_id=self.session_id,
            bot_version=self.bot_version,
            config_hash=self.config_hash,
            action="cancel",
            strategy_name=None,
            envelope=self._dummy_envelope(
                order_id=order_id, symbol=symbol or "UNKNOWN"
            ),
            extra={"status": "cancelled"},
        )

        # Invalidate caches
        if self.account_data:
            self.account_data.invalidate_cache("buying_power")
            self.account_data.invalidate_cache("positions")

    def cancel_all_open_orders(self) -> None:
        try:
            cancelled_ids = cancel_all_equity_orders()
        except Exception as exc:  # pragma: no cover - safety
            raise OrderCancellationError(str(exc)) from exc

        for order_id in cancelled_ids:
            symbol = self._tracked_orders.pop(order_id, None)
            if symbol and self.safety_checks:
                self.safety_checks.clear_pending_order(symbol)

            append_order_log(
                log_path=self.order_log_path,
                session_id=self.session_id,
                bot_version=self.bot_version,
                config_hash=self.config_hash,
                action="cancel",
                strategy_name=None,
                envelope=self._dummy_envelope(
                    order_id=order_id, symbol=symbol or "UNKNOWN"
                ),
                extra={"status": "cancelled"},
            )

        if cancelled_ids and self.account_data:
            self.account_data.invalidate_cache("buying_power")
            self.account_data.invalidate_cache("positions")

    def get_order_status(self, order_id: str) -> dict[str, Any]:
        """Get the current status of an order.

        Args:
            order_id: The order ID to check

        Returns:
            Dictionary with order status information including:
            - order_id: str
            - status: str (filled, open, cancelled, etc.)
            - filled_quantity: int
            - average_fill_price: Decimal | None

        Raises:
            OrderStatusError: If status check fails
        """
        try:
            status = fetch_order_status(order_id)
        except OrderStatusError:
            raise

        # Return as dictionary for compatibility
        return {
            "order_id": status.order_id,
            "status": status.state,
            "filled_quantity": status.filled_quantity,
            "average_fill_price": status.average_fill_price,
        }

    # --- Synchronization ------------------------------------------------
    def synchronize_open_orders(self) -> None:
        for order_id, symbol in list(self._tracked_orders.items()):
            try:
                status = fetch_order_status(order_id)
            except OrderStatusError as exc:
                append_order_log(
                    log_path=self.order_log_path,
                    session_id=self.session_id,
                    bot_version=self.bot_version,
                    config_hash=self.config_hash,
                    action="status_error",
                    strategy_name=None,
                    envelope=self._dummy_envelope(order_id=order_id, symbol=symbol),
                    extra={"error": str(exc)},
                )
                continue

            append_order_log(
                log_path=self.order_log_path,
                session_id=self.session_id,
                bot_version=self.bot_version,
                config_hash=self.config_hash,
                action="status",
                strategy_name=None,
                envelope=self._dummy_envelope(order_id=order_id, symbol=symbol),
                extra={
                    "status": status.state,
                    "filled_quantity": status.filled_quantity,
                },
            )

            if status.state in {"filled", "cancelled", "rejected"}:
                self._clear_tracking(order_id, symbol)

    # --- Internal helpers ----------------------------------------------
    def _submit(
        self, order: OrderRequest, offsets: PriceOffsetConfig
    ) -> OrderEnvelope:
        if order.side == "BUY":
            return submit_limit_buy(order, offsets, execution_mode=self.execution_mode)
        if order.side == "SELL":
            return submit_limit_sell(order, offsets, execution_mode=self.execution_mode)
        raise OrderSubmissionError(f"Unsupported order side: {order.side}")

    def _register_tracking(self, envelope: OrderEnvelope) -> None:
        self._tracked_orders[envelope.order_id] = envelope.symbol

    def _clear_tracking(self, order_id: str, symbol: str) -> None:
        self._tracked_orders.pop(order_id, None)
        if self.safety_checks:
            self.safety_checks.clear_pending_order(symbol)
        if self.account_data:
            self.account_data.invalidate_cache("buying_power")
            self.account_data.invalidate_cache("positions")

    def _dummy_envelope(
        self, *, order_id: str = "n/a", symbol: str = "N/A"
    ) -> OrderEnvelope:
        return OrderEnvelope(
            order_id=order_id,
            symbol=symbol,
            side="BUY",
            quantity=0,
            limit_price=Decimal("0"),
            execution_mode=self.execution_mode,
            submitted_at=datetime.now(UTC),
        )
