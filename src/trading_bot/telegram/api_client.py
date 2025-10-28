"""Internal API client for Telegram command handlers.

Provides async HTTP client for calling the trading bot's REST API
from Telegram command handlers.

Constitution v1.0.0:
- §Non_Blocking: All API calls are async (httpx.AsyncClient)
- §Security: Uses API key authentication from environment
- §Error_Handling: Graceful degradation on API failures
"""

import logging
import os
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class InternalAPIClient:
    """
    Async HTTP client for calling trading bot REST API.

    Used by Telegram command handlers to query bot state and execute
    control commands (pause/resume).

    Pattern: Async context manager (use with `async with`)
    Architecture: Singleton per command handler (dependency injection)
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 2.0,
    ) -> None:
        """
        Initialize API client.

        Args:
            base_url: API base URL (default: http://localhost:8000)
            api_key: API authentication token (default: from BOT_API_AUTH_TOKEN env)
            timeout: Request timeout in seconds (default: 2.0)
        """
        self.base_url = base_url or os.getenv(
            "BOT_API_BASE_URL", "http://localhost:8000"
        )
        self.api_key = api_key or os.getenv("BOT_API_AUTH_TOKEN", "")
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "InternalAPIClient":
        """Enter async context manager - create HTTP client."""
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={"X-API-Key": self.api_key},
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context manager - close HTTP client."""
        if self._client:
            await self._client.aclose()

    async def get_bot_state(self) -> Dict[str, Any]:
        """
        Get current bot state (positions, balance, mode).

        Returns:
            dict: Bot state from GET /api/v1/state

        Raises:
            httpx.HTTPStatusError: If API returns error status
            httpx.RequestError: If request fails (connection, timeout)
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use 'async with' context.")

        response = await self._client.get("/api/v1/state")
        response.raise_for_status()
        return response.json()

    async def get_bot_summary(self) -> Dict[str, Any]:
        """
        Get bot status summary (lightweight version).

        Returns:
            dict: Bot summary from GET /api/v1/summary

        Raises:
            httpx.HTTPStatusError: If API returns error status
            httpx.RequestError: If request fails (connection, timeout)
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use 'async with' context.")

        response = await self._client.get("/api/v1/summary")
        response.raise_for_status()
        return response.json()

    async def pause_bot(self, reason: Optional[str] = None) -> Dict[str, Any]:
        """
        Pause trading bot operations.

        Args:
            reason: Optional reason for pausing (logged for audit)

        Returns:
            dict: Command response from POST /api/v1/commands/pause

        Raises:
            httpx.HTTPStatusError: If API returns error status
            httpx.RequestError: If request fails (connection, timeout)
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use 'async with' context.")

        payload = {"reason": reason} if reason else {}
        response = await self._client.post("/api/v1/commands/pause", json=payload)
        response.raise_for_status()
        return response.json()

    async def resume_bot(self) -> Dict[str, Any]:
        """
        Resume trading bot operations.

        Returns:
            dict: Command response from POST /api/v1/commands/resume

        Raises:
            httpx.HTTPStatusError: If API returns error status
            httpx.RequestError: If request fails (connection, timeout)
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use 'async with' context.")

        response = await self._client.post("/api/v1/commands/resume", json={})
        response.raise_for_status()
        return response.json()

    async def get_positions(self) -> list[Dict[str, Any]]:
        """
        Get all open positions.

        Returns:
            list: Open positions from bot state

        Raises:
            httpx.HTTPStatusError: If API returns error status
            httpx.RequestError: If request fails (connection, timeout)
        """
        state = await self.get_bot_state()
        return state.get("positions", [])

    async def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics (win rate, P/L, etc.).

        Returns:
            dict: Performance metrics from bot state

        Raises:
            httpx.HTTPStatusError: If API returns error status
            httpx.RequestError: If request fails (connection, timeout)
        """
        state = await self.get_bot_state()
        return state.get("performance", {})
