"""Pydantic schemas for bot command execution."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class PauseCommand(BaseModel):
    """
    Request to pause trading bot.

    Attributes:
        reason: Optional reason for pausing (for audit logs)
    """

    reason: Optional[str] = Field(
        None, description="Reason for pausing (logged for audit trail)"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"reason": "High market volatility detected"},
                {"reason": "Manual intervention required"},
                {},  # No reason provided
            ]
        }
    }


class ResumeCommand(BaseModel):
    """
    Request to resume trading bot.

    Currently has no parameters, but defined as schema for API consistency
    and future extensibility.
    """

    model_config = {
        "json_schema_extra": {
            "examples": [
                {},  # No parameters currently
            ]
        }
    }


class CommandResponse(BaseModel):
    """
    Response from command execution.

    Attributes:
        success: Whether command executed successfully
        message: Human-readable confirmation message
        timestamp: ISO 8601 timestamp of command execution
        previous_state: Bot state before command (e.g., "running", "paused")
        current_state: Bot state after command
        metadata: Optional additional context
    """

    success: bool = Field(..., description="Command execution success")
    message: str = Field(..., description="Confirmation message")
    timestamp: datetime = Field(..., description="Execution timestamp (UTC)")
    previous_state: str = Field(..., description="Bot state before command")
    current_state: str = Field(..., description="Bot state after command")
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Additional context"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "success": True,
                    "message": "Bot paused successfully. Existing positions remain open.",
                    "timestamp": "2025-10-27T14:30:00Z",
                    "previous_state": "running",
                    "current_state": "paused",
                    "metadata": {"reason": "High volatility detected"},
                },
                {
                    "success": True,
                    "message": "Bot resumed successfully. Now accepting new signals.",
                    "timestamp": "2025-10-27T15:00:00Z",
                    "previous_state": "paused",
                    "current_state": "running",
                    "metadata": None,
                },
            ]
        }
    }
