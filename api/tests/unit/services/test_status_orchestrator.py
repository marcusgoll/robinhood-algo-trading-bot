"""Unit tests for StatusOrchestrator service.

Tests cover:
- publish_status (event published to correct Redis channel)
- publish_order_filled helper (correct payload structure)
- publish_order_partial helper
- publish_order_rejected helper
- subscribe_to_trader_orders (receives published events)
- handle_fill_event (updates order status and publishes event)
- Latency < 500ms (timestamp comparison)
- Error handling (Redis unavailable, database error)
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.services.status_orchestrator import (
    StatusOrchestrator,
    OrderEventType,
)


class MockEventBus:
    """Mock EventBus for testing."""

    def __init__(self) -> None:
        self.published_events: list[tuple[str, dict[str, Any]]] = []
        self._subscriptions: dict[str, list[dict[str, Any]]] = {}

    async def publish(self, channel: str, event: dict[str, Any]) -> None:
        """Mock publish - stores events for verification."""
        self.published_events.append((channel, event))
        # Also add to subscriptions for testing
        if channel not in self._subscriptions:
            self._subscriptions[channel] = []
        self._subscriptions[channel].append(event)

    async def subscribe(self, channel: str) -> AsyncGenerator[dict[str, Any], None]:
        """Mock subscribe - yields stored events."""
        if channel in self._subscriptions:
            for event in self._subscriptions[channel]:
                yield event


class MockAsyncSession:
    """Mock AsyncSession for testing."""

    def __init__(self) -> None:
        self.added_objects: list[Any] = []
        self.committed = False
        self.rolled_back = False

    def add(self, obj: Any) -> None:
        """Mock add - stores objects for verification."""
        self.added_objects.append(obj)

    async def commit(self) -> None:
        """Mock commit."""
        self.committed = True

    async def rollback(self) -> None:
        """Mock rollback."""
        self.rolled_back = True

    async def execute(self, query: Any) -> Any:
        """Mock execute - returns mock result."""
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        return result


@pytest.fixture
def mock_event_bus() -> MockEventBus:
    """Fixture providing mock EventBus."""
    return MockEventBus()


@pytest.fixture
def mock_db_session() -> MockAsyncSession:
    """Fixture providing mock database session."""
    return MockAsyncSession()


@pytest.fixture
def orchestrator(
    mock_event_bus: MockEventBus,
    mock_db_session: MockAsyncSession,
) -> StatusOrchestrator:
    """Fixture providing StatusOrchestrator instance."""
    return StatusOrchestrator(
        event_bus=mock_event_bus,
        db_session=mock_db_session,
    )


class TestPublishStatus:
    """Test publish_status method."""

    @pytest.mark.asyncio
    async def test_publish_status_success(
        self,
        orchestrator: StatusOrchestrator,
        mock_event_bus: MockEventBus,
    ) -> None:
        """Test publish_status publishes event to correct Redis channel."""
        order_id = uuid4()
        trader_id = uuid4()
        event_type = OrderEventType.ORDER_FILLED
        details = {
            "quantity_filled": 50,
            "price_at_fill": "150.25",
            "status": "FILLED",
            "venue": "NYSE",
        }

        success = await orchestrator.publish_status(
            order_id=order_id,
            trader_id=trader_id,
            event_type=event_type,
            details=details,
        )

        assert success is True
        assert len(mock_event_bus.published_events) == 1

        channel, event = mock_event_bus.published_events[0]
        assert channel == f"orders:{trader_id}"
        assert event["event"] == "order.filled"
        assert event["order_id"] == str(order_id)
        assert event["trader_id"] == str(trader_id)
        assert event["quantity_filled"] == 50
        assert event["price_at_fill"] == "150.25"
        assert event["status"] == "FILLED"
        assert event["venue"] == "NYSE"
        assert "timestamp" in event

    @pytest.mark.asyncio
    async def test_publish_status_with_string_event_type(
        self,
        orchestrator: StatusOrchestrator,
        mock_event_bus: MockEventBus,
    ) -> None:
        """Test publish_status accepts string event type."""
        order_id = uuid4()
        trader_id = uuid4()
        event_type = "order.filled"
        details = {"status": "FILLED"}

        success = await orchestrator.publish_status(
            order_id=order_id,
            trader_id=trader_id,
            event_type=event_type,
            details=details,
        )

        assert success is True
        channel, event = mock_event_bus.published_events[0]
        assert event["event"] == "order.filled"

    @pytest.mark.asyncio
    async def test_publish_status_error_handling(
        self,
        orchestrator: StatusOrchestrator,
        mock_event_bus: MockEventBus,
    ) -> None:
        """Test publish_status handles errors gracefully."""
        # Make event bus raise error
        mock_event_bus.publish = AsyncMock(side_effect=Exception("Redis down"))

        order_id = uuid4()
        trader_id = uuid4()

        success = await orchestrator.publish_status(
            order_id=order_id,
            trader_id=trader_id,
            event_type=OrderEventType.ORDER_FILLED,
            details={},
        )

        assert success is False


class TestPublishOrderFilled:
    """Test publish_order_filled helper method."""

    @pytest.mark.asyncio
    async def test_publish_order_filled_correct_payload(
        self,
        orchestrator: StatusOrchestrator,
        mock_event_bus: MockEventBus,
    ) -> None:
        """Test publish_order_filled creates correct payload structure."""
        order_id = uuid4()
        trader_id = uuid4()
        quantity_filled = 50
        price_at_fill = Decimal("150.25")
        venue = "NYSE"

        success = await orchestrator.publish_order_filled(
            order_id=order_id,
            trader_id=trader_id,
            quantity_filled=quantity_filled,
            price_at_fill=price_at_fill,
            venue=venue,
        )

        assert success is True
        channel, event = mock_event_bus.published_events[0]
        assert channel == f"orders:{trader_id}"
        assert event["event"] == "order.filled"
        assert event["quantity_filled"] == 50
        assert event["price_at_fill"] == "150.25"
        assert event["status"] == "FILLED"
        assert event["venue"] == "NYSE"
        assert event["total_filled"] == 50

    @pytest.mark.asyncio
    async def test_publish_order_filled_with_uuid_strings(
        self,
        orchestrator: StatusOrchestrator,
        mock_event_bus: MockEventBus,
    ) -> None:
        """Test publish_order_filled accepts UUID strings."""
        order_id = str(uuid4())
        trader_id = str(uuid4())

        success = await orchestrator.publish_order_filled(
            order_id=order_id,
            trader_id=trader_id,
            quantity_filled=100,
            price_at_fill=Decimal("200.00"),
            venue="NASDAQ",
        )

        assert success is True
        _, event = mock_event_bus.published_events[0]
        assert event["order_id"] == order_id
        assert event["trader_id"] == trader_id


class TestPublishOrderPartial:
    """Test publish_order_partial helper method."""

    @pytest.mark.asyncio
    async def test_publish_order_partial_correct_payload(
        self,
        orchestrator: StatusOrchestrator,
        mock_event_bus: MockEventBus,
    ) -> None:
        """Test publish_order_partial creates correct payload structure."""
        order_id = uuid4()
        trader_id = uuid4()
        quantity_filled = 30
        price_at_fill = Decimal("150.25")
        total_filled = 50

        success = await orchestrator.publish_order_partial(
            order_id=order_id,
            trader_id=trader_id,
            quantity_filled=quantity_filled,
            price_at_fill=price_at_fill,
            total_filled=total_filled,
        )

        assert success is True
        channel, event = mock_event_bus.published_events[0]
        assert event["event"] == "order.partial"
        assert event["quantity_filled"] == 30
        assert event["price_at_fill"] == "150.25"
        assert event["total_filled"] == 50
        assert event["status"] == "PARTIAL"


class TestPublishOrderRejected:
    """Test publish_order_rejected helper method."""

    @pytest.mark.asyncio
    async def test_publish_order_rejected_with_error_code(
        self,
        orchestrator: StatusOrchestrator,
        mock_event_bus: MockEventBus,
    ) -> None:
        """Test publish_order_rejected includes error code."""
        order_id = uuid4()
        trader_id = uuid4()
        reason = "Insufficient funds"
        error_code = "INSUFFICIENT_FUNDS"

        success = await orchestrator.publish_order_rejected(
            order_id=order_id,
            trader_id=trader_id,
            reason=reason,
            error_code=error_code,
        )

        assert success is True
        channel, event = mock_event_bus.published_events[0]
        assert event["event"] == "order.rejected"
        assert event["status"] == "REJECTED"
        assert event["reason"] == "Insufficient funds"
        assert event["error_code"] == "INSUFFICIENT_FUNDS"

    @pytest.mark.asyncio
    async def test_publish_order_rejected_without_error_code(
        self,
        orchestrator: StatusOrchestrator,
        mock_event_bus: MockEventBus,
    ) -> None:
        """Test publish_order_rejected works without error code."""
        order_id = uuid4()
        trader_id = uuid4()

        success = await orchestrator.publish_order_rejected(
            order_id=order_id,
            trader_id=trader_id,
            reason="Market closed",
        )

        assert success is True
        _, event = mock_event_bus.published_events[0]
        assert "error_code" not in event
        assert event["reason"] == "Market closed"


class TestSubscribeToTraderOrders:
    """Test subscribe_to_trader_orders method."""

    @pytest.mark.asyncio
    async def test_subscribe_receives_published_events(
        self,
        orchestrator: StatusOrchestrator,
        mock_event_bus: MockEventBus,
    ) -> None:
        """Test subscription receives events published to trader channel."""
        trader_id = uuid4()
        order_id = uuid4()

        # Publish event first
        await orchestrator.publish_order_filled(
            order_id=order_id,
            trader_id=trader_id,
            quantity_filled=50,
            price_at_fill=Decimal("150.25"),
            venue="NYSE",
        )

        # Subscribe and verify event received
        received_events = []
        async for event in orchestrator.subscribe_to_trader_orders(trader_id):
            received_events.append(event)
            break  # Only get first event

        assert len(received_events) == 1
        event = received_events[0]
        assert event["event"] == "order.filled"
        assert event["order_id"] == str(order_id)
        assert event["trader_id"] == str(trader_id)

    @pytest.mark.asyncio
    async def test_subscribe_filters_by_trader_id(
        self,
        orchestrator: StatusOrchestrator,
        mock_event_bus: MockEventBus,
    ) -> None:
        """Test subscription only receives events for specific trader."""
        trader1_id = uuid4()
        trader2_id = uuid4()
        order1_id = uuid4()
        order2_id = uuid4()

        # Publish events for different traders
        await orchestrator.publish_order_filled(
            order_id=order1_id,
            trader_id=trader1_id,
            quantity_filled=50,
            price_at_fill=Decimal("150.25"),
            venue="NYSE",
        )

        await orchestrator.publish_order_filled(
            order_id=order2_id,
            trader_id=trader2_id,
            quantity_filled=100,
            price_at_fill=Decimal("200.00"),
            venue="NASDAQ",
        )

        # Subscribe to trader1 only
        received_events = []
        async for event in orchestrator.subscribe_to_trader_orders(trader1_id):
            received_events.append(event)
            break

        # Should only receive trader1's event
        assert len(received_events) == 1
        assert received_events[0]["trader_id"] == str(trader1_id)
        assert received_events[0]["order_id"] == str(order1_id)


class TestHandleFillEvent:
    """Test handle_fill_event method."""

    @pytest.mark.asyncio
    async def test_handle_fill_event_full_fill(
        self,
        orchestrator: StatusOrchestrator,
        mock_event_bus: MockEventBus,
        mock_db_session: MockAsyncSession,
    ) -> None:
        """Test handle_fill_event processes full fill correctly."""
        from api.app.models.order import Order, OrderStatus

        order_id = uuid4()
        trader_id = uuid4()

        # Create mock order
        mock_order = Order(
            id=order_id,
            trader_id=trader_id,
            symbol="AAPL",
            quantity=100,
            order_type="MARKET",
            status=OrderStatus.PENDING.value,
            filled_quantity=0,
        )

        # Mock database query to return order
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_order
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        fill_record = {
            "order_id": str(order_id),
            "trader_id": str(trader_id),
            "quantity_filled": 100,
            "price_at_fill": "150.25",
            "venue": "NYSE",
            "timestamp": "2025-10-17T12:00:05Z",
        }

        success = await orchestrator.handle_fill_event(fill_record)

        assert success is True
        # Verify order status updated
        assert mock_order.status == OrderStatus.FILLED.value
        assert mock_order.filled_quantity == 100
        # Verify fill and execution log created
        assert len(mock_db_session.added_objects) >= 2
        # Verify event published
        assert len(mock_event_bus.published_events) == 1
        _, event = mock_event_bus.published_events[0]
        assert event["event"] == "order.filled"

    @pytest.mark.asyncio
    async def test_handle_fill_event_partial_fill(
        self,
        orchestrator: StatusOrchestrator,
        mock_event_bus: MockEventBus,
        mock_db_session: MockAsyncSession,
    ) -> None:
        """Test handle_fill_event processes partial fill correctly."""
        from api.app.models.order import Order, OrderStatus

        order_id = uuid4()
        trader_id = uuid4()

        # Create mock order with partial fill
        mock_order = Order(
            id=order_id,
            trader_id=trader_id,
            symbol="AAPL",
            quantity=100,
            order_type="MARKET",
            status=OrderStatus.PARTIAL.value,
            filled_quantity=50,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_order
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        fill_record = {
            "order_id": str(order_id),
            "trader_id": str(trader_id),
            "quantity_filled": 30,
            "price_at_fill": "150.30",
            "venue": "NYSE",
            "timestamp": "2025-10-17T12:00:10Z",
        }

        success = await orchestrator.handle_fill_event(fill_record)

        assert success is True
        # Verify order status still PARTIAL
        assert mock_order.status == OrderStatus.PARTIAL.value
        assert mock_order.filled_quantity == 80
        # Verify partial event published
        _, event = mock_event_bus.published_events[0]
        assert event["event"] == "order.partial"
        assert event["total_filled"] == 80

    @pytest.mark.asyncio
    async def test_handle_fill_event_order_not_found(
        self,
        orchestrator: StatusOrchestrator,
        mock_db_session: MockAsyncSession,
    ) -> None:
        """Test handle_fill_event handles missing order gracefully."""
        # Mock returns None (order not found)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        fill_record = {
            "order_id": str(uuid4()),
            "trader_id": str(uuid4()),
            "quantity_filled": 50,
            "price_at_fill": "150.25",
            "venue": "NYSE",
            "timestamp": "2025-10-17T12:00:05Z",
        }

        success = await orchestrator.handle_fill_event(fill_record)

        assert success is False

    @pytest.mark.asyncio
    async def test_handle_fill_event_database_error(
        self,
        orchestrator: StatusOrchestrator,
        mock_db_session: MockAsyncSession,
    ) -> None:
        """Test handle_fill_event handles database errors gracefully."""
        # Mock database error
        mock_db_session.execute = AsyncMock(side_effect=Exception("DB error"))

        fill_record = {
            "order_id": str(uuid4()),
            "trader_id": str(uuid4()),
            "quantity_filled": 50,
            "price_at_fill": "150.25",
            "venue": "NYSE",
            "timestamp": "2025-10-17T12:00:05Z",
        }

        success = await orchestrator.handle_fill_event(fill_record)

        assert success is False
        assert mock_db_session.rolled_back is True


class TestLatencyRequirements:
    """Test latency requirements < 500ms."""

    @pytest.mark.asyncio
    async def test_publish_latency_under_500ms(
        self,
        orchestrator: StatusOrchestrator,
        mock_event_bus: MockEventBus,
    ) -> None:
        """Test publish_status latency is under 500ms via timestamp comparison."""
        import time

        order_id = uuid4()
        trader_id = uuid4()

        # Measure time before publish
        start_time = time.time()

        await orchestrator.publish_order_filled(
            order_id=order_id,
            trader_id=trader_id,
            quantity_filled=50,
            price_at_fill=Decimal("150.25"),
            venue="NYSE",
        )

        # Measure time after publish
        end_time = time.time()
        latency_ms = (end_time - start_time) * 1000

        # Verify latency < 500ms (should be << 500ms for mock)
        assert latency_ms < 500

        # Also verify timestamp in event is recent
        _, event = mock_event_bus.published_events[0]
        event_timestamp = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        time_diff = (now - event_timestamp).total_seconds()

        # Event timestamp should be within 1 second
        assert time_diff < 1.0


class TestErrorHandling:
    """Test error handling scenarios."""

    @pytest.mark.asyncio
    async def test_redis_unavailable_graceful_degradation(
        self,
        orchestrator: StatusOrchestrator,
        mock_event_bus: MockEventBus,
    ) -> None:
        """Test graceful handling when Redis is unavailable."""
        # Make publish fail
        mock_event_bus.publish = AsyncMock(side_effect=ConnectionError("Redis unavailable"))

        order_id = uuid4()
        trader_id = uuid4()

        success = await orchestrator.publish_order_filled(
            order_id=order_id,
            trader_id=trader_id,
            quantity_filled=50,
            price_at_fill=Decimal("150.25"),
            venue="NYSE",
        )

        # Should return False but not raise exception
        assert success is False

    @pytest.mark.asyncio
    async def test_database_unavailable_graceful_degradation(
        self,
        orchestrator: StatusOrchestrator,
        mock_db_session: MockAsyncSession,
        mock_event_bus: MockEventBus,
    ) -> None:
        """Test graceful handling when database is unavailable."""
        # Make commit fail
        mock_db_session.commit = AsyncMock(side_effect=Exception("DB unavailable"))

        order_id = uuid4()
        trader_id = uuid4()

        # Should still publish event even if DB logging fails
        success = await orchestrator.publish_order_filled(
            order_id=order_id,
            trader_id=trader_id,
            quantity_filled=50,
            price_at_fill=Decimal("150.25"),
            venue="NYSE",
        )

        # Event still published (DB logging is secondary)
        assert len(mock_event_bus.published_events) == 1
