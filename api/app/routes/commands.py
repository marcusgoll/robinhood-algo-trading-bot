"""API routes for bot command execution."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from ..core.auth import verify_api_key
from ..schemas.commands import (
    CommandResponse,
    PauseCommand,
    ResumeCommand,
)
from ..services.command_executor import CommandExecutor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/commands", tags=["commands"])


def get_command_executor() -> CommandExecutor:
    """Dependency injection for CommandExecutor."""
    return CommandExecutor()


@router.post(
    "/pause",
    response_model=CommandResponse,
    status_code=status.HTTP_200_OK,
    summary="Pause trading operations",
    description="Pauses the trading bot. Stops accepting new signals but maintains existing positions.",
)
async def pause_bot(
    command: PauseCommand,
    _: bool = Depends(verify_api_key),
    executor: CommandExecutor = Depends(get_command_executor),
) -> CommandResponse:
    """
    Pause trading bot operations.

    Args:
        command: Pause command with optional reason

    Returns:
        CommandResponse with execution status

    Raises:
        HTTPException: If pause operation fails
    """
    try:
        response = await executor.pause(command.reason)
        return response
    except Exception as e:
        logger.error(f"Pause command failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to pause bot: {str(e)}",
        )


@router.post(
    "/resume",
    response_model=CommandResponse,
    status_code=status.HTTP_200_OK,
    summary="Resume trading operations",
    description="Resumes the trading bot. Begins accepting new signals.",
)
async def resume_bot(
    command: ResumeCommand,
    _: bool = Depends(verify_api_key),
    executor: CommandExecutor = Depends(get_command_executor),
) -> CommandResponse:
    """
    Resume trading bot operations.

    Args:
        command: Resume command (no parameters currently)

    Returns:
        CommandResponse with execution status

    Raises:
        HTTPException: If resume operation fails
    """
    try:
        response = await executor.resume()
        return response
    except Exception as e:
        logger.error(f"Resume command failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resume bot: {str(e)}",
        )
