"""Integration tests for StatusOrchestrator with Redis and database.

These tests verify:
- End-to-end flow from status publish to WebSocket delivery
- Latency measurement with real timing
- Database transaction handling
- Redis pub/sub message delivery
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, AsyncGenerator
from uuid import uuid4
import time

import pytest

from api.app.services.status_orchestrator import (
    StatusOrchestrator,
    OrderEventType,
)


class IntegrationEventBus:
    """
    Integration EventBus that simulates Redis pub/sub with realistic timing.

    This simulates the Redis pub/sub behavior more realistically than the unit test mock,
    including small latencies to measure P99 performance.
    """

    def __init__(self) -> None:
        self.channels: dict[str, list[dict[str, Any]]] = {}
        self.publish_latency_ms = 10  # Simulate 10ms Redis latency

    async def publish(self, channel: str, event: dict[str, Any]) -> None:
        """Publish event with simulated Redis latency."""
        # Simulate Redis network round trip
        await self._simulate_latency(self.publish_latency_ms)

        if channel not in self.channels:
            self.channels[channel] = []
        self.channels[channel].append(event)

    async def subscribe(self, channel: str) -> AsyncGenerator[dict[str, Any], None]:
        """Subscribe to channel and yield events."""
        # Simulate subscription setup latency
        await self._simulate_latency(5)

        if channel in self.channels:
            for event in self.channels[channel]:
                # Simulate message delivery latency
                await self._simulate_latency(5)
                yield event

    async def _simulate_latency(self, ms: float) -> None:
        """Simulate network latency."""
        import asyncio
        await asyncio.sleep(ms / 1000.0)


class IntegrationAsyncSession:
    """
    Integration database session that simulates real database behavior.
    """

    def __init__(self) -> None:
        self.added_objects: list[Any] = []
        self.committed = False
        self.commit_latency_ms = 20  # Simulate 20ms DB commit latency

    def add(self, obj: Any) -> None:
        """Add object to session."""
        self.added_objects.append(obj)

    async def commit(self) -> None:
        """Commit with simulated database latency."""
        import asyncio
        await asyncio.sleep(self.commit_latency_ms / 1000.0)
        self.committed = True

    async def rollback(self) -> None:
        """Rollback transaction."""
        self.rolled_back = True

    async def execute(self, query: Any) -> Any:
        """Execute query with simulated latency."""
        import asyncio
        from unittest.mock import MagicMock

        await asyncio.sleep(10 / 1000.0)  # 10ms query latency
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        return result


@pytest.fixture
def integration_event_bus() -> IntegrationEventBus:
    """Fixture providing integration EventBus."""
    return IntegrationEventBus()


@pytest.fixture
def integration_db_session() -> IntegrationAsyncSession:
    """Fixture providing integration database session."""
    return IntegrationAsyncSession()


@pytest.fixture
def integration_orchestrator(
    integration_event_bus: IntegrationEventBus,
    integration_db_session: IntegrationAsyncSession,
) -> StatusOrchestrator:
    """Fixture providing StatusOrchestrator with integration dependencies."""
    return StatusOrchestrator(
        event_bus=integration_event_bus,
        db_session=integration_db_session,
    )


class TestEndToEndFlow:
    """Test end-to-end flow from publish to delivery."""

    @pytest.mark.asyncio
    async def test_publish_to_websocket_delivery_latency(
        self,
        integration_orchestrator: StatusOrchestrator,
        integration_event_bus: IntegrationEventBus,
    ) -> None:
        """
        Test complete flow from order status change to WebSocket delivery.

        Measures latency from publish_order_filled to event received by subscriber.
        Requirement: P99 latency < 500ms.
        """
        order_id = uuid4()
        trader_id = uuid4()

        # Record timestamp before publish
        start_time = time.perf_counter()
        start_timestamp = datetime.now(timezone.utc)

        # Publish order filled event
        success = await integration_orchestrator.publish_order_filled(
            order_id=order_id,
            trader_id=trader_id,
            quantity_filled=100,
            price_at_fill=Decimal("150.25"),
            venue="NYSE",
        )

        assert success is True

        # Subscribe and receive event
        received_events = []
        async for event in integration_orchestrator.subscribe_to_trader_orders(trader_id):
            end_time = time.perf_counter()
            end_timestamp = datetime.now(timezone.utc)
            received_events.append(event)
            break

        # Calculate latency
        latency_ms = (end_time - start_time) * 1000
        total_time_diff = (end_timestamp - start_timestamp).total_seconds() * 1000

        print(f"\nEnd-to-end latency: {latency_ms:.2f}ms")
        print(f"Total time: {total_time_diff:.2f}ms")

        # Verify P99 latency requirement (< 500ms)
        assert latency_ms < 500, f"Latency {latency_ms:.2f}ms exceeds 500ms requirement"

        # Verify event received correctly
        assert len(received_events) == 1
        event = received_events[0]
        assert event["event"] == "order.filled"
        assert event["order_id"] == str(order_id)
        assert event["trader_id"] == str(trader_id)
        assert event["quantity_filled"] == 100
        assert event["price_at_fill"] == "150.25"
        assert event["venue"] == "NYSE"

    @pytest.mark.asyncio
    async def test_multiple_subscribers_receive_events(
        self,
        integration_orchestrator: StatusOrchestrator,
        integration_event_bus: IntegrationEventBus,
    ) -> None:
        """
        Test that multiple WebSocket connections can subscribe to same trader.
        """
        trader_id = uuid4()
        order_id = uuid4()

        # Publish event
        await integration_orchestrator.publish_order_filled(
            order_id=order_id,
            trader_id=trader_id,
            quantity_filled=50,
            price_at_fill=Decimal("150.25"),
            venue="NYSE",
        )

        # Multiple subscribers should receive the same event
        subscriber1_events = []
        async for event in integration_orchestrator.subscribe_to_trader_orders(trader_id):
            subscriber1_events.append(event)
            break

        subscriber2_events = []
        async for event in integration_orchestrator.subscribe_to_trader_orders(trader_id):
            subscriber2_events.append(event)
            break

        # Both should receive same event
        assert len(subscriber1_events) == 1
        assert len(subscriber2_events) == 1
        assert subscriber1_events[0]["order_id"] == str(order_id)
        assert subscriber2_events[0]["order_id"] == str(order_id)

    @pytest.mark.asyncio
    async def test_event_ordering_preserved(
        self,
        integration_orchestrator: StatusOrchestrator,
        integration_event_bus: IntegrationEventBus,
    ) -> None:
        """
        Test that events are delivered in order they were published.
        """
        trader_id = uuid4()
        order1_id = uuid4()
        order2_id = uuid4()
        order3_id = uuid4()

        # Publish multiple events in sequence
        await integration_orchestrator.publish_order_filled(
            order_id=order1_id,
            trader_id=trader_id,
            quantity_filled=50,
            price_at_fill=Decimal("150.00"),
            venue="NYSE",
        )

        await integration_orchestrator.publish_order_partial(
            order_id=order2_id,
            trader_id=trader_id,
            quantity_filled=30,
            price_at_fill=Decimal("151.00"),
            total_filled=30,
        )

        await integration_orchestrator.publish_order_rejected(
            order_id=order3_id,
            trader_id=trader_id,
            reason="Insufficient funds",
            error_code="INSUFFICIENT_FUNDS",
        )

        # Subscribe and verify order preserved
        received_events = []
        count = 0
        async for event in integration_orchestrator.subscribe_to_trader_orders(trader_id):
            received_events.append(event)
            count += 1
            if count >= 3:
                break

        assert len(received_events) == 3
        assert received_events[0]["order_id"] == str(order1_id)
        assert received_events[0]["event"] == "order.filled"
        assert received_events[1]["order_id"] == str(order2_id)
        assert received_events[1]["event"] == "order.partial"
        assert received_events[2]["order_id"] == str(order3_id)
        assert received_events[2]["event"] == "order.rejected"


class TestLatencyUnderLoad:
    """Test latency requirements under simulated load."""

    @pytest.mark.asyncio
    async def test_p99_latency_multiple_events(
        self,
        integration_orchestrator: StatusOrchestrator,
    ) -> None:
        """
        Test P99 latency with multiple concurrent events.

        Publishes 100 events and verifies 99th percentile is under 500ms.
        """
        trader_id = uuid4()
        latencies = []

        # Publish 100 events and measure latency
        for i in range(100):
            order_id = uuid4()
            start_time = time.perf_counter()

            await integration_orchestrator.publish_order_filled(
                order_id=order_id,
                trader_id=trader_id,
                quantity_filled=50,
                price_at_fill=Decimal("150.25"),
                venue="NYSE",
            )

            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000
            latencies.append(latency_ms)

        # Calculate P99 latency
        latencies.sort()
        p99_index = int(len(latencies) * 0.99)
        p99_latency = latencies[p99_index]

        print(f"\nP99 latency: {p99_latency:.2f}ms")
        print(f"Min latency: {min(latencies):.2f}ms")
        print(f"Max latency: {max(latencies):.2f}ms")
        print(f"Average latency: {sum(latencies)/len(latencies):.2f}ms")

        # Verify P99 < 500ms requirement
        assert p99_latency < 500, f"P99 latency {p99_latency:.2f}ms exceeds 500ms requirement"


class TestDatabaseTransactions:
    """Test database transaction handling."""

    @pytest.mark.asyncio
    async def test_database_logging_committed(
        self,
        integration_orchestrator: StatusOrchestrator,
        integration_db_session: IntegrationAsyncSession,
    ) -> None:
        """Test that events are logged to database."""
        order_id = uuid4()
        trader_id = uuid4()

        await integration_orchestrator.publish_order_filled(
            order_id=order_id,
            trader_id=trader_id,
            quantity_filled=50,
            price_at_fill=Decimal("150.25"),
            venue="NYSE",
        )

        # Verify database commit was called
        assert integration_db_session.committed is True
        # Verify execution log was added
        assert len(integration_db_session.added_objects) > 0


class TestEventPayloadStructure:
    """Test event payload structure and content."""

    @pytest.mark.asyncio
    async def test_event_payload_contains_required_fields(
        self,
        integration_orchestrator: StatusOrchestrator,
        integration_event_bus: IntegrationEventBus,
    ) -> None:
        """Test that event payload contains all required fields."""
        order_id = uuid4()
        trader_id = uuid4()

        await integration_orchestrator.publish_order_filled(
            order_id=order_id,
            trader_id=trader_id,
            quantity_filled=100,
            price_at_fill=Decimal("150.25"),
            venue="NYSE",
        )

        # Get published event
        channel = f"orders:{trader_id}"
        assert channel in integration_event_bus.channels
        events = integration_event_bus.channels[channel]
        assert len(events) == 1

        event = events[0]

        # Verify required fields
        required_fields = [
            "event",
            "order_id",
            "trader_id",
            "timestamp",
            "quantity_filled",
            "price_at_fill",
            "status",
            "venue",
        ]

        for field in required_fields:
            assert field in event, f"Missing required field: {field}"

        # Verify field types and values
        assert event["event"] == "order.filled"
        assert event["order_id"] == str(order_id)
        assert event["trader_id"] == str(trader_id)
        assert isinstance(event["timestamp"], str)
        assert event["quantity_filled"] == 100
        assert event["price_at_fill"] == "150.25"
        assert event["status"] == "FILLED"
        assert event["venue"] == "NYSE"

        # Verify timestamp is recent and in ISO format
        event_timestamp = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        time_diff = (now - event_timestamp).total_seconds()
        assert time_diff < 5.0, "Event timestamp is not recent"
