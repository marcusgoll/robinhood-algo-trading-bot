"""API routes for bot metrics and real-time streaming."""

from __future__ import annotations

import asyncio
import logging
from typing import Dict, Any

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from ..core.auth import verify_api_key
from ..core.websocket import manager
from ..schemas.state import BotStateResponse
from ..services.state_aggregator import StateAggregator

router = APIRouter(prefix="/metrics", tags=["metrics"])
logger = logging.getLogger(__name__)


def get_state_aggregator() -> StateAggregator:
    """Dependency injection for StateAggregator."""
    return StateAggregator()


@router.get(
    "",
    response_model=BotStateResponse,
    summary="Get current bot metrics snapshot",
    description="Returns current bot state and performance metrics",
)
async def get_metrics(
    _: bool = Depends(verify_api_key),
    aggregator: StateAggregator = Depends(get_state_aggregator),
) -> BotStateResponse:
    """
    Get current bot metrics snapshot.

    Returns:
        BotStateResponse with current state and metrics
    """
    return aggregator.get_bot_state()


@router.websocket("/stream")
async def stream_metrics(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for real-time bot state streaming.

    Broadcasts bot state every 5 seconds to connected clients.
    Clients should handle reconnection on disconnect.

    Connection protocol:
    1. Client connects to ws://host/api/v1/metrics/stream
    2. Server sends state updates every 5s as JSON
    3. Client receives: {"state": {...}, "timestamp": "...", "broadcast_at": "..."}
    4. On error, server disconnects and client should retry
    """
    await manager.connect(websocket)

    try:
        # Keep connection alive and let broadcast loop handle updates
        while True:
            # Wait for client messages (heartbeat/ping)
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(), timeout=30.0
                )
                # Echo heartbeat
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # No message received in 30s, send heartbeat
                await websocket.send_json({"type": "heartbeat", "active": True})
            except WebSocketDisconnect:
                break

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await manager.disconnect(websocket)


@router.get(
    "/connections",
    response_model=Dict[str, int],
    summary="Get active WebSocket connection count",
    description="Returns number of active WebSocket connections for monitoring",
)
async def get_connection_count(
    _: bool = Depends(verify_api_key),
) -> Dict[str, int]:
    """
    Get count of active WebSocket connections.

    Returns:
        Dict with active_connections count
    """
    return {"active_connections": manager.get_active_count()}
