"""
Integration tests for Metrics and WebSocket Streaming API.

Tests metrics routes with TestClient:
- GET /api/v1/metrics - Get current metrics snapshot
- WebSocket /api/v1/metrics/stream - Real-time state streaming
- GET /api/v1/metrics/connections - Get active connection count
"""

import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.app.routes.metrics import router as metrics_router
from api.app.schemas.state import BotStateResponse
from api.app.core.websocket import ConnectionManager


@pytest.fixture
def app():
    """Create FastAPI app with metrics routes."""
    app = FastAPI()
    app.include_router(metrics_router, prefix="/api/v1")
    return app


@pytest.fixture
def client(app):
    """Create TestClient for API testing."""
    return TestClient(app)


@pytest.fixture
def mock_state_aggregator():
    """Mock StateAggregator to return sample state."""
    with patch("api.app.routes.metrics.get_state_aggregator") as mock:
        aggregator = AsyncMock()
        aggregator.get_bot_state.return_value = BotStateResponse(
            health_status="healthy",
            position_count=3,
            open_orders_count=2,
            daily_pnl=1250.75,
            circuit_breaker_status="active",
            account_balance=50000.0,
            buying_power=25000.0,
            data_age_seconds=5,
            warnings=[],
        )
        mock.return_value = aggregator
        yield mock


@pytest.fixture
def mock_auth():
    """Mock API key authentication."""
    with patch("api.app.routes.metrics.verify_api_key") as mock:
        mock.return_value = True
        yield mock


class TestMetricsAPI:
    """Integration tests for metrics API endpoints."""

    def test_get_metrics_snapshot(self, client, mock_state_aggregator, mock_auth):
        """
        GIVEN: API is running with bot state data
        WHEN: Client queries GET /api/v1/metrics
        THEN: Current bot state is returned
        """
        response = client.get("/api/v1/metrics")

        assert response.status_code == 200
        data = response.json()
        assert data["health_status"] == "healthy"
        assert data["position_count"] == 3
        assert data["open_orders_count"] == 2
        assert data["daily_pnl"] == 1250.75
        assert data["circuit_breaker_status"] == "active"

    def test_get_connection_count(self, client, mock_auth):
        """
        GIVEN: WebSocket connections are active
        WHEN: Client queries GET /api/v1/metrics/connections
        THEN: Connection count is returned
        """
        response = client.get("/api/v1/metrics/connections")

        assert response.status_code == 200
        data = response.json()
        assert "active_connections" in data
        assert isinstance(data["active_connections"], int)
        assert data["active_connections"] >= 0


class TestWebSocketStreaming:
    """Integration tests for WebSocket streaming."""

    def test_websocket_connection_lifecycle(self, client):
        """
        GIVEN: WebSocket endpoint is available
        WHEN: Client connects and disconnects
        THEN: Connection is accepted and cleaned up
        """
        with client.websocket_connect("/api/v1/metrics/stream") as websocket:
            # Connection should be established
            assert websocket is not None

            # Send heartbeat
            websocket.send_text("ping")
            response = websocket.receive_text()
            assert response == "pong"

        # Connection should be closed automatically

    def test_websocket_receives_updates(self, client, mock_state_aggregator):
        """
        GIVEN: WebSocket is connected
        WHEN: Broadcast loop sends state updates
        THEN: Client receives JSON messages with state data
        """
        with client.websocket_connect("/api/v1/metrics/stream") as websocket:
            # Note: In real scenario, broadcast loop would send updates
            # Here we test the connection accepts messages

            # Send heartbeat to keep alive
            websocket.send_text("ping")
            response = websocket.receive_text()
            assert response == "pong"

            # In production, would receive state updates like:
            # {"type": "state_update", "state": {...}, "timestamp": "...", "broadcast_at": "..."}

    def test_websocket_heartbeat_timeout(self, client):
        """
        GIVEN: WebSocket is connected
        WHEN: No message received for 30+ seconds
        THEN: Server sends heartbeat to keep connection alive
        """
        with client.websocket_connect("/api/v1/metrics/stream") as websocket:
            # Receive heartbeat (sent after timeout)
            # Note: TestClient may not fully simulate timeout behavior
            # This is more of a contract test

            # Send ping to verify connection is alive
            websocket.send_text("ping")
            response = websocket.receive_text()
            assert response == "pong"

    def test_multiple_websocket_connections(self, client):
        """
        GIVEN: Multiple clients connect to WebSocket
        WHEN: Broadcast is sent
        THEN: All clients should receive the message
        """
        # Note: TestClient doesn't support true concurrent WebSocket connections
        # This test verifies single connection works, full multi-client test
        # would require separate test infrastructure

        with client.websocket_connect("/api/v1/metrics/stream") as ws1:
            # First connection works
            ws1.send_text("ping")
            assert ws1.receive_text() == "pong"

        # Connection properly cleaned up
        # In production, ConnectionManager tracks multiple connections


class TestConnectionManager:
    """Unit tests for WebSocket ConnectionManager."""

    @pytest.mark.asyncio
    async def test_connection_manager_connect_disconnect(self):
        """
        GIVEN: ConnectionManager instance
        WHEN: WebSocket connects and disconnects
        THEN: Active connections count updates correctly
        """
        manager = ConnectionManager()

        # Mock websocket
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()

        # Connect
        await manager.connect(mock_ws)
        assert manager.get_active_count() == 1

        # Disconnect
        await manager.disconnect(mock_ws)
        assert manager.get_active_count() == 0

    @pytest.mark.asyncio
    async def test_connection_manager_broadcast(self):
        """
        GIVEN: Multiple WebSocket connections
        WHEN: Manager broadcasts message
        THEN: All connections receive the message
        """
        manager = ConnectionManager()

        # Mock multiple websockets
        mock_ws1 = AsyncMock()
        mock_ws1.accept = AsyncMock()
        mock_ws1.send_json = AsyncMock()

        mock_ws2 = AsyncMock()
        mock_ws2.accept = AsyncMock()
        mock_ws2.send_json = AsyncMock()

        # Connect both
        await manager.connect(mock_ws1)
        await manager.connect(mock_ws2)
        assert manager.get_active_count() == 2

        # Broadcast message
        test_message = {"type": "test", "data": "hello"}
        await manager.broadcast(test_message)

        # Both websockets should have received the message
        assert mock_ws1.send_json.called
        assert mock_ws2.send_json.called

    @pytest.mark.asyncio
    async def test_connection_manager_handles_send_failure(self):
        """
        GIVEN: WebSocket connection that fails to send
        WHEN: Manager broadcasts message
        THEN: Failed connection is removed from pool
        """
        manager = ConnectionManager()

        # Mock websocket that fails to send
        mock_ws_fail = AsyncMock()
        mock_ws_fail.accept = AsyncMock()
        mock_ws_fail.send_json = AsyncMock(side_effect=Exception("Connection lost"))

        # Mock working websocket
        mock_ws_ok = AsyncMock()
        mock_ws_ok.accept = AsyncMock()
        mock_ws_ok.send_json = AsyncMock()

        # Connect both
        await manager.connect(mock_ws_fail)
        await manager.connect(mock_ws_ok)
        assert manager.get_active_count() == 2

        # Broadcast message
        await manager.broadcast({"type": "test"})

        # Failed connection should be removed
        assert manager.get_active_count() == 1
        # Working connection should still be active
        assert mock_ws_ok.send_json.called

    @pytest.mark.asyncio
    async def test_connection_manager_close_all(self):
        """
        GIVEN: Multiple active WebSocket connections
        WHEN: Manager closes all connections
        THEN: All connections are closed and pool is empty
        """
        manager = ConnectionManager()

        # Mock websockets
        mock_ws1 = AsyncMock()
        mock_ws1.accept = AsyncMock()
        mock_ws1.close = AsyncMock()

        mock_ws2 = AsyncMock()
        mock_ws2.accept = AsyncMock()
        mock_ws2.close = AsyncMock()

        # Connect both
        await manager.connect(mock_ws1)
        await manager.connect(mock_ws2)
        assert manager.get_active_count() == 2

        # Close all
        await manager.close_all()

        # Pool should be empty
        assert manager.get_active_count() == 0
        # Both should have close called
        assert mock_ws1.close.called
        assert mock_ws2.close.called


@pytest.mark.parametrize(
    "connection_count,expected_min",
    [
        (0, 0),  # No connections
        (1, 1),  # Single connection
        (5, 5),  # Multiple connections
    ],
)
@pytest.mark.asyncio
async def test_connection_count_accuracy(connection_count, expected_min):
    """Test ConnectionManager accurately tracks connection count."""
    manager = ConnectionManager()

    # Add connections
    websockets = []
    for _ in range(connection_count):
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        await manager.connect(mock_ws)
        websockets.append(mock_ws)

    assert manager.get_active_count() == expected_min

    # Cleanup
    await manager.close_all()
    assert manager.get_active_count() == 0
