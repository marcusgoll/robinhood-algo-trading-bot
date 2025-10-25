"""WebSocket connection manager for real-time bot state streaming."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List

from fastapi import WebSocket


logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections for real-time state streaming.

    Provides:
    - Connection lifecycle management (connect/disconnect)
    - Broadcast messages to all connected clients
    - Heartbeat monitoring
    - Error handling and recovery
    """

    def __init__(self):
        """Initialize connection manager with empty connections list."""
        self.active_connections: List[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        """
        Accept WebSocket connection and add to active pool.

        Args:
            websocket: WebSocket connection to accept
        """
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
        logger.info(
            f"WebSocket connected. Active connections: {len(self.active_connections)}"
        )

    async def disconnect(self, websocket: WebSocket) -> None:
        """
        Remove WebSocket connection from active pool.

        Args:
            websocket: WebSocket connection to disconnect
        """
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.info(
            f"WebSocket disconnected. Active connections: {len(self.active_connections)}"
        )

    async def send_personal_message(
        self, message: str | Dict[str, Any], websocket: WebSocket
    ) -> None:
        """
        Send message to specific WebSocket connection.

        Args:
            message: Message to send (string or dict to JSON-ify)
            websocket: Target WebSocket connection
        """
        try:
            if isinstance(message, dict):
                await websocket.send_json(message)
            else:
                await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            await self.disconnect(websocket)

    async def broadcast(self, message: Dict[str, Any]) -> None:
        """
        Broadcast message to all active WebSocket connections.

        Automatically removes stale connections on send failure.

        Args:
            message: Message dict to broadcast as JSON
        """
        # Add timestamp to message
        message["broadcast_at"] = datetime.utcnow().isoformat()

        disconnected = []
        async with self._lock:
            for connection in self.active_connections:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.warning(
                        f"Failed to send to connection, marking for removal: {e}"
                    )
                    disconnected.append(connection)

        # Remove disconnected clients
        if disconnected:
            async with self._lock:
                for connection in disconnected:
                    if connection in self.active_connections:
                        self.active_connections.remove(connection)
            logger.info(
                f"Removed {len(disconnected)} stale connections. "
                f"Active: {len(self.active_connections)}"
            )

    async def broadcast_text(self, message: str) -> None:
        """
        Broadcast text message to all active connections.

        Args:
            message: Text message to broadcast
        """
        disconnected = []
        async with self._lock:
            for connection in self.active_connections:
                try:
                    await connection.send_text(message)
                except Exception as e:
                    logger.warning(
                        f"Failed to send text to connection: {e}"
                    )
                    disconnected.append(connection)

        # Remove disconnected clients
        if disconnected:
            async with self._lock:
                for connection in disconnected:
                    if connection in self.active_connections:
                        self.active_connections.remove(connection)

    def get_active_count(self) -> int:
        """
        Get count of active WebSocket connections.

        Returns:
            Number of active connections
        """
        return len(self.active_connections)

    async def close_all(self) -> None:
        """Close all active WebSocket connections gracefully."""
        async with self._lock:
            for connection in self.active_connections:
                try:
                    await connection.close()
                except Exception as e:
                    logger.warning(f"Error closing connection: {e}")
            self.active_connections.clear()
        logger.info("All WebSocket connections closed")


# Global instance
manager = ConnectionManager()
