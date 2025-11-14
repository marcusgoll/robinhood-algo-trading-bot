"""Event bus for publishing domain events."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

logger = logging.getLogger(__name__)


class EventBus:
    """
    Simple event bus for publishing domain events.

    In production, this would integrate with a message broker (RabbitMQ, Redis, etc.).
    For MVP, this logs events for audit and can be extended later.
    """

    def __init__(self) -> None:
        """Initialize EventBus."""
        self.logger = logger

    def publish(
        self,
        event_type: str,
        payload: dict[str, Any],
        trader_id: Optional[UUID] = None,
    ) -> None:
        """
        Publish an event to the event bus.

        Args:
            event_type: Type of event (e.g., "order.submitted", "order.filled")
            payload: Event data
            trader_id: Optional trader ID for filtering/routing
        """
        event = {
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trader_id": str(trader_id) if trader_id else None,
            "payload": payload,
        }

        # Log event (in production, send to message broker)
        self.logger.info(f"Event published: {json.dumps(event)}")

    def publish_order_submitted(
        self,
        order_id: UUID,
        trader_id: UUID,
        symbol: str,
        quantity: int,
        order_type: str,
    ) -> None:
        """
        Publish order.submitted event.

        Args:
            order_id: Order UUID
            trader_id: Trader UUID
            symbol: Stock symbol
            quantity: Number of shares
            order_type: Type of order
        """
        self.publish(
            event_type="order.submitted",
            payload={
                "order_id": str(order_id),
                "symbol": symbol,
                "quantity": quantity,
                "order_type": order_type,
            },
            trader_id=trader_id,
        )

    def publish_order_cancelled(
        self,
        order_id: UUID,
        trader_id: UUID,
        symbol: str,
    ) -> None:
        """
        Publish order.cancelled event.

        Args:
            order_id: Order UUID
            trader_id: Trader UUID
            symbol: Stock symbol
        """
        self.publish(
            event_type="order.cancelled",
            payload={
                "order_id": str(order_id),
                "symbol": symbol,
                "status": "CANCELLED",
            },
            trader_id=trader_id,
        )


# Global EventBus instance
event_bus = EventBus()
