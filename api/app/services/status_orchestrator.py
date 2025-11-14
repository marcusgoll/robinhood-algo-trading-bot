"""StatusOrchestrator service for real-time order status updates via Redis pub/sub.

This service orchestrates real-time order status updates with < 500ms P99 latency
by publishing events to Redis channels and providing async subscription for WebSocket delivery.

Key Features:
- Publishes order status events to Redis channels (orders:{trader_id})
- Logs all events to database for audit trail
- Supports async subscription for WebSocket handlers
- Handles exchange fill events and updates order status
- < 500ms P99 latency from status change to WebSocket delivery
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, AsyncGenerator, Optional, Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


class EventBusProtocol(Protocol):
    """Protocol for event bus dependency (Redis pub/sub)."""

    async def publish(self, channel: str, event: dict[str, Any]) -> None:
        """Publish event to Redis channel."""
        ...

    async def subscribe(self, channel: str) -> AsyncGenerator[dict[str, Any], None]:
        """Subscribe to Redis channel and yield events."""
        ...


class OrderEventType(str, Enum):
    """Order event types for status updates."""

    ORDER_SUBMITTED = "order.submitted"
    ORDER_FILLED = "order.filled"
    ORDER_PARTIAL = "order.partial"
    ORDER_REJECTED = "order.rejected"
    ORDER_CANCELLED = "order.cancelled"


class StatusOrchestrator:
    """
    Orchestrates real-time order status updates via Redis pub/sub + WebSocket.

    Responsibilities:
    - Publish order status events to Redis channels
    - Log events to database for audit trail
    - Provide async subscription for WebSocket handlers
    - Handle fill events from exchange
    - Ensure < 500ms P99 latency

    Usage:
        orchestrator = StatusOrchestrator(event_bus=event_bus, db_session=db)

        # Publish order filled event
        success = await orchestrator.publish_order_filled(
            order_id="uuid",
            trader_id="uuid",
            quantity_filled=50,
            price_at_fill=Decimal("150.25"),
            venue="NYSE"
        )

        # Subscribe to trader's orders (WebSocket handler)
        async for event in orchestrator.subscribe_to_trader_orders(trader_id="uuid"):
            # Send event to WebSocket client
            await websocket.send_json(event)
    """

    def __init__(
        self,
        event_bus: EventBusProtocol,
        db_session: AsyncSession,
    ) -> None:
        """
        Initialize StatusOrchestrator.

        Args:
            event_bus: EventBusProtocol implementation (Redis pub/sub)
            db_session: Async SQLAlchemy database session
        """
        self.event_bus = event_bus
        self.db = db_session

    async def publish_status(
        self,
        order_id: str | UUID,
        trader_id: str | UUID,
        event_type: str | OrderEventType,
        details: dict[str, Any],
    ) -> bool:
        """
        Main entry point for publishing order status events.

        Publishes event to Redis channel: orders:{trader_id}
        Logs event to database for audit trail.

        Args:
            order_id: Order UUID
            trader_id: Trader UUID
            event_type: Event type (order.submitted, order.filled, etc.)
            details: Event details (quantity_filled, price_at_fill, timestamp, etc.)

        Returns:
            bool: True if event published successfully, False otherwise

        Example:
            success = await orchestrator.publish_status(
                order_id="uuid",
                trader_id="uuid",
                event_type=OrderEventType.ORDER_FILLED,
                details={
                    "quantity_filled": 50,
                    "price_at_fill": "150.25",
                    "total_filled": 100,
                    "status": "FILLED",
                    "venue": "NYSE"
                }
            )
        """
        try:
            # Normalize UUIDs to strings
            order_id_str = str(order_id)
            trader_id_str = str(trader_id)

            # Normalize event type
            if isinstance(event_type, OrderEventType):
                event_type_str = event_type.value
            else:
                event_type_str = str(event_type)

            # Create event payload with timestamp
            timestamp = datetime.now(timezone.utc).isoformat()
            event_payload = {
                "event": event_type_str,
                "order_id": order_id_str,
                "trader_id": trader_id_str,
                "timestamp": timestamp,
                **details,
            }

            # Publish to Redis channel: orders:{trader_id}
            channel = f"orders:{trader_id_str}"
            await self.event_bus.publish(channel, event_payload)

            # Log event to database for audit trail
            await self._log_event_to_database(
                order_id=order_id_str,
                trader_id=trader_id_str,
                event_type=event_type_str,
                details=details,
                timestamp=timestamp,
            )

            return True

        except Exception as e:
            # Log error but don't raise (graceful degradation)
            print(f"Error publishing status event: {e}")
            return False

    async def publish_order_filled(
        self,
        order_id: str | UUID,
        trader_id: str | UUID,
        quantity_filled: int,
        price_at_fill: Decimal,
        venue: str,
    ) -> bool:
        """
        Helper method to publish order filled event.

        Args:
            order_id: Order UUID
            trader_id: Trader UUID
            quantity_filled: Quantity filled in this event
            price_at_fill: Price at which order was filled
            venue: Exchange venue (NYSE, NASDAQ, etc.)

        Returns:
            bool: True if event published successfully

        Example:
            success = await orchestrator.publish_order_filled(
                order_id="uuid",
                trader_id="uuid",
                quantity_filled=50,
                price_at_fill=Decimal("150.25"),
                venue="NYSE"
            )
        """
        details = {
            "quantity_filled": quantity_filled,
            "price_at_fill": str(price_at_fill),
            "status": "FILLED",
            "venue": venue,
            "total_filled": quantity_filled,  # Will be updated if partial
        }

        return await self.publish_status(
            order_id=order_id,
            trader_id=trader_id,
            event_type=OrderEventType.ORDER_FILLED,
            details=details,
        )

    async def publish_order_partial(
        self,
        order_id: str | UUID,
        trader_id: str | UUID,
        quantity_filled: int,
        price_at_fill: Decimal,
        total_filled: int,
    ) -> bool:
        """
        Helper method to publish order partial fill event.

        Args:
            order_id: Order UUID
            trader_id: Trader UUID
            quantity_filled: Quantity filled in this partial fill
            price_at_fill: Price at which partial fill occurred
            total_filled: Total quantity filled so far (including this fill)

        Returns:
            bool: True if event published successfully

        Example:
            success = await orchestrator.publish_order_partial(
                order_id="uuid",
                trader_id="uuid",
                quantity_filled=30,
                price_at_fill=Decimal("150.25"),
                total_filled=50  # Previous fills + this fill
            )
        """
        details = {
            "quantity_filled": quantity_filled,
            "price_at_fill": str(price_at_fill),
            "total_filled": total_filled,
            "status": "PARTIAL",
        }

        return await self.publish_status(
            order_id=order_id,
            trader_id=trader_id,
            event_type=OrderEventType.ORDER_PARTIAL,
            details=details,
        )

    async def publish_order_rejected(
        self,
        order_id: str | UUID,
        trader_id: str | UUID,
        reason: str,
        error_code: Optional[str] = None,
    ) -> bool:
        """
        Helper method to publish order rejection event.

        Args:
            order_id: Order UUID
            trader_id: Trader UUID
            reason: Human-readable rejection reason
            error_code: Optional error code (e.g., INSUFFICIENT_FUNDS)

        Returns:
            bool: True if event published successfully

        Example:
            success = await orchestrator.publish_order_rejected(
                order_id="uuid",
                trader_id="uuid",
                reason="Insufficient funds",
                error_code="INSUFFICIENT_FUNDS"
            )
        """
        details = {
            "status": "REJECTED",
            "reason": reason,
        }

        if error_code:
            details["error_code"] = error_code

        return await self.publish_status(
            order_id=order_id,
            trader_id=trader_id,
            event_type=OrderEventType.ORDER_REJECTED,
            details=details,
        )

    async def subscribe_to_trader_orders(
        self,
        trader_id: str | UUID,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Server-side subscription to trader's order events.

        Subscribes to Redis channel: orders:{trader_id}
        Yields events as they arrive (used by WebSocket handler).

        Args:
            trader_id: Trader UUID

        Yields:
            dict: Event payload with order status update

        Example:
            async for event in orchestrator.subscribe_to_trader_orders("uuid"):
                await websocket.send_json(event)
        """
        trader_id_str = str(trader_id)
        channel = f"orders:{trader_id_str}"

        async for event in self.event_bus.subscribe(channel):
            yield event

    async def handle_fill_event(
        self,
        fill_record: dict[str, Any],
    ) -> bool:
        """
        Event listener for fill events from exchange.

        Called when fill detected from exchange.
        Updates order status in database.
        Publishes order.filled or order.partial event.
        Logs to execution_logs table.

        Args:
            fill_record: Fill record from exchange containing:
                - order_id: Order UUID
                - trader_id: Trader UUID
                - quantity_filled: Quantity in this fill
                - price_at_fill: Execution price
                - venue: Exchange name
                - timestamp: Fill timestamp

        Returns:
            bool: True if fill handled successfully

        Example:
            success = await orchestrator.handle_fill_event({
                "order_id": "uuid",
                "trader_id": "uuid",
                "quantity_filled": 50,
                "price_at_fill": "150.25",
                "venue": "NYSE",
                "timestamp": "2025-10-17T12:00:05Z"
            })
        """
        try:
            from api.app.models.order import Order, OrderStatus
            from api.app.models.fill import Fill
            from api.app.models.execution_log import ExecutionLog, ExecutionAction

            order_id = fill_record["order_id"]
            trader_id = fill_record["trader_id"]
            quantity_filled = fill_record["quantity_filled"]
            price_at_fill = Decimal(str(fill_record["price_at_fill"]))
            venue = fill_record["venue"]

            # Fetch order from database
            result = await self.db.execute(
                select(Order).where(Order.id == order_id)
            )
            order = result.scalar_one_or_none()

            if not order:
                print(f"Order {order_id} not found")
                return False

            # Update order status
            previous_filled = order.filled_quantity
            new_filled = previous_filled + quantity_filled

            if new_filled >= order.quantity:
                # Fully filled
                order.status = OrderStatus.FILLED.value
                order.filled_quantity = order.quantity
                event_type = OrderEventType.ORDER_FILLED
            else:
                # Partially filled
                order.status = OrderStatus.PARTIAL.value
                order.filled_quantity = new_filled
                event_type = OrderEventType.ORDER_PARTIAL

            # Create fill record
            fill = Fill(
                order_id=order_id,
                timestamp=datetime.now(timezone.utc),
                quantity_filled=quantity_filled,
                price_at_fill=price_at_fill,
                venue=venue,
            )
            self.db.add(fill)

            # Create execution log entry
            execution_log = ExecutionLog(
                order_id=order_id,
                trader_id=trader_id,
                action=ExecutionAction.FILLED.value,
                status=order.status,
                timestamp=datetime.now(timezone.utc),
                reason=f"Filled {quantity_filled} shares at {price_at_fill} on {venue}",
            )
            self.db.add(execution_log)

            # Commit database changes
            await self.db.commit()

            # Publish event
            if event_type == OrderEventType.ORDER_FILLED:
                await self.publish_order_filled(
                    order_id=order_id,
                    trader_id=trader_id,
                    quantity_filled=quantity_filled,
                    price_at_fill=price_at_fill,
                    venue=venue,
                )
            else:
                await self.publish_order_partial(
                    order_id=order_id,
                    trader_id=trader_id,
                    quantity_filled=quantity_filled,
                    price_at_fill=price_at_fill,
                    total_filled=new_filled,
                )

            return True

        except Exception as e:
            await self.db.rollback()
            print(f"Error handling fill event: {e}")
            return False

    async def _log_event_to_database(
        self,
        order_id: str,
        trader_id: str,
        event_type: str,
        details: dict[str, Any],
        timestamp: str,
    ) -> None:
        """
        Log event to execution_logs table for audit trail.

        Args:
            order_id: Order UUID
            trader_id: Trader UUID
            event_type: Event type string
            details: Event details
            timestamp: ISO format timestamp
        """
        try:
            from api.app.models.execution_log import ExecutionLog, ExecutionAction

            # Map event type to execution action
            action_map = {
                "order.submitted": ExecutionAction.SUBMITTED,
                "order.filled": ExecutionAction.FILLED,
                "order.partial": ExecutionAction.FILLED,  # Partial is also FILLED action
                "order.rejected": ExecutionAction.REJECTED,
                "order.cancelled": ExecutionAction.CANCELLED,
            }

            action = action_map.get(event_type, ExecutionAction.EXECUTED)
            status = details.get("status")
            reason = details.get("reason")

            execution_log = ExecutionLog(
                order_id=order_id,
                trader_id=trader_id,
                action=action.value,
                status=status,
                timestamp=datetime.fromisoformat(timestamp.replace("Z", "+00:00")),
                reason=reason,
            )

            self.db.add(execution_log)
            await self.db.commit()

        except Exception as e:
            # Log error but don't raise (event already published to Redis)
            print(f"Error logging event to database: {e}")
            await self.db.rollback()
