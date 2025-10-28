"""Service for executing bot control commands (pause, resume)."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..schemas.commands import CommandResponse

logger = logging.getLogger(__name__)

# Bot state file location (shared with main bot process)
BOT_STATE_FILE = Path("logs/bot_state.json")


class CommandExecutor:
    """
    Executes bot control commands via shared state file.

    The trading bot reads bot_state.json to determine operating mode.
    This service writes to that file to control the bot (pause/resume).

    Pattern: File-based IPC (simple, reliable, no complex async coordination)
    Constitution: §Non_Blocking - all operations async, never block trading
    """

    def __init__(self, state_file: Optional[Path] = None) -> None:
        """
        Initialize command executor.

        Args:
            state_file: Path to bot state file (default: logs/bot_state.json)
        """
        self.state_file = state_file or BOT_STATE_FILE
        # Ensure logs directory exists
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

    async def pause(self, reason: Optional[str] = None) -> CommandResponse:
        """
        Pause trading bot operations.

        Writes "paused" state to bot_state.json. The bot's main loop reads
        this file and stops accepting new signals.

        Args:
            reason: Optional reason for pausing (logged for audit)

        Returns:
            CommandResponse with confirmation

        Raises:
            Exception: If state file write fails
        """
        # Get current state
        previous_state = await self._read_state()

        # Write new state
        new_state = {
            "mode": "paused",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
            "previous_mode": previous_state.get("mode", "unknown"),
        }

        await self._write_state(new_state)

        logger.info(
            f"Bot paused via API command. Reason: {reason or 'Not specified'}"
        )

        return CommandResponse(
            success=True,
            message="Bot paused successfully. Existing positions remain open.",
            timestamp=datetime.now(timezone.utc),
            previous_state=previous_state.get("mode", "unknown"),
            current_state="paused",
            metadata={"reason": reason} if reason else None,
        )

    async def resume(self) -> CommandResponse:
        """
        Resume trading bot operations.

        Writes "running" state to bot_state.json. The bot's main loop reads
        this file and begins accepting new signals.

        Returns:
            CommandResponse with confirmation

        Raises:
            Exception: If state file write fails
        """
        # Get current state
        previous_state = await self._read_state()

        # Write new state
        new_state = {
            "mode": "running",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "previous_mode": previous_state.get("mode", "unknown"),
        }

        await self._write_state(new_state)

        logger.info("Bot resumed via API command")

        return CommandResponse(
            success=True,
            message="Bot resumed successfully. Now accepting new signals.",
            timestamp=datetime.now(timezone.utc),
            previous_state=previous_state.get("mode", "unknown"),
            current_state="running",
            metadata=None,
        )

    async def _read_state(self) -> dict:
        """
        Read current bot state from file.

        Returns:
            dict: Current bot state (or {"mode": "unknown"} if file missing)
        """
        try:
            # Use asyncio to avoid blocking
            content = await asyncio.to_thread(self.state_file.read_text)
            return json.loads(content)
        except FileNotFoundError:
            # File doesn't exist yet (first run)
            return {"mode": "unknown"}
        except json.JSONDecodeError:
            logger.warning(f"Corrupt bot state file: {self.state_file}")
            return {"mode": "unknown"}

    async def _write_state(self, state: dict) -> None:
        """
        Write bot state to file.

        Args:
            state: State dict to write

        Raises:
            Exception: If write fails
        """
        try:
            # Use asyncio to avoid blocking
            await asyncio.to_thread(
                self.state_file.write_text, json.dumps(state, indent=2)
            )
        except Exception as e:
            logger.error(f"Failed to write bot state: {e}")
            raise
