"""Unit tests for command routes (pause/resume)."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import status
from httpx import AsyncClient

from api.app.main import app
from api.app.schemas.commands import CommandResponse, PauseCommand, ResumeCommand


@pytest.fixture
async def client():
    """Create async test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_command_executor():
    """Mock CommandExecutor for dependency injection."""
    executor = Mock()
    executor.pause = AsyncMock()
    executor.resume = AsyncMock()
    return executor


@pytest.mark.asyncio
async def test_pause_bot_success(client, mock_command_executor):
    """Test pause command returns success response."""
    # Arrange
    command = PauseCommand(reason="High volatility")
    expected_response = CommandResponse(
        success=True,
        message="Bot paused successfully. Existing positions remain open.",
        timestamp=datetime.now(timezone.utc),
        previous_state="running",
        current_state="paused",
        metadata={"reason": "High volatility"},
    )
    mock_command_executor.pause.return_value = expected_response

    # Mock the dependency injection
    with patch(
        "api.app.routes.commands.get_command_executor",
        return_value=mock_command_executor,
    ):
        # Act
        response = await client.post(
            "/api/v1/commands/pause",
            json=command.model_dump(),
            headers={"X-API-Key": "test-api-key"},
        )

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["success"] is True
    assert data["current_state"] == "paused"
    assert data["previous_state"] == "running"
    assert data["metadata"]["reason"] == "High volatility"
    mock_command_executor.pause.assert_awaited_once_with("High volatility")


@pytest.mark.asyncio
async def test_pause_bot_no_reason(client, mock_command_executor):
    """Test pause command without reason."""
    # Arrange
    command = PauseCommand()
    expected_response = CommandResponse(
        success=True,
        message="Bot paused successfully. Existing positions remain open.",
        timestamp=datetime.now(timezone.utc),
        previous_state="running",
        current_state="paused",
        metadata=None,
    )
    mock_command_executor.pause.return_value = expected_response

    # Mock the dependency injection
    with patch(
        "api.app.routes.commands.get_command_executor",
        return_value=mock_command_executor,
    ):
        # Act
        response = await client.post(
            "/api/v1/commands/pause",
            json=command.model_dump(),
            headers={"X-API-Key": "test-api-key"},
        )

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["success"] is True
    assert data["current_state"] == "paused"
    assert data["metadata"] is None
    mock_command_executor.pause.assert_awaited_once_with(None)


@pytest.mark.asyncio
async def test_pause_bot_unauthorized(client):
    """Test pause command rejects unauthorized requests."""
    # Arrange
    command = PauseCommand(reason="Test")

    # Act
    response = await client.post(
        "/api/v1/commands/pause",
        json=command.model_dump(),
        # No X-API-Key header
    )

    # Assert
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_pause_bot_executor_error(client, mock_command_executor):
    """Test pause command handles executor errors gracefully."""
    # Arrange
    command = PauseCommand(reason="Test")
    mock_command_executor.pause.side_effect = Exception("State file write failed")

    # Mock the dependency injection
    with patch(
        "api.app.routes.commands.get_command_executor",
        return_value=mock_command_executor,
    ):
        # Act
        response = await client.post(
            "/api/v1/commands/pause",
            json=command.model_dump(),
            headers={"X-API-Key": "test-api-key"},
        )

    # Assert
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    data = response.json()
    assert "Failed to pause bot" in data["detail"]


@pytest.mark.asyncio
async def test_resume_bot_success(client, mock_command_executor):
    """Test resume command returns success response."""
    # Arrange
    command = ResumeCommand()
    expected_response = CommandResponse(
        success=True,
        message="Bot resumed successfully. Now accepting new signals.",
        timestamp=datetime.now(timezone.utc),
        previous_state="paused",
        current_state="running",
        metadata=None,
    )
    mock_command_executor.resume.return_value = expected_response

    # Mock the dependency injection
    with patch(
        "api.app.routes.commands.get_command_executor",
        return_value=mock_command_executor,
    ):
        # Act
        response = await client.post(
            "/api/v1/commands/resume",
            json=command.model_dump(),
            headers={"X-API-Key": "test-api-key"},
        )

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["success"] is True
    assert data["current_state"] == "running"
    assert data["previous_state"] == "paused"
    assert data["metadata"] is None
    mock_command_executor.resume.assert_awaited_once()


@pytest.mark.asyncio
async def test_resume_bot_unauthorized(client):
    """Test resume command rejects unauthorized requests."""
    # Arrange
    command = ResumeCommand()

    # Act
    response = await client.post(
        "/api/v1/commands/resume",
        json=command.model_dump(),
        # No X-API-Key header
    )

    # Assert
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_resume_bot_executor_error(client, mock_command_executor):
    """Test resume command handles executor errors gracefully."""
    # Arrange
    command = ResumeCommand()
    mock_command_executor.resume.side_effect = Exception("State file write failed")

    # Mock the dependency injection
    with patch(
        "api.app.routes.commands.get_command_executor",
        return_value=mock_command_executor,
    ):
        # Act
        response = await client.post(
            "/api/v1/commands/resume",
            json=command.model_dump(),
            headers={"X-API-Key": "test-api-key"},
        )

    # Assert
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    data = response.json()
    assert "Failed to resume bot" in data["detail"]


@pytest.mark.asyncio
async def test_pause_from_unknown_state(client, mock_command_executor):
    """Test pause command when bot state is unknown (first run)."""
    # Arrange
    command = PauseCommand(reason="Emergency stop")
    expected_response = CommandResponse(
        success=True,
        message="Bot paused successfully. Existing positions remain open.",
        timestamp=datetime.now(timezone.utc),
        previous_state="unknown",
        current_state="paused",
        metadata={"reason": "Emergency stop"},
    )
    mock_command_executor.pause.return_value = expected_response

    # Mock the dependency injection
    with patch(
        "api.app.routes.commands.get_command_executor",
        return_value=mock_command_executor,
    ):
        # Act
        response = await client.post(
            "/api/v1/commands/pause",
            json=command.model_dump(),
            headers={"X-API-Key": "test-api-key"},
        )

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["success"] is True
    assert data["previous_state"] == "unknown"
    assert data["current_state"] == "paused"


@pytest.mark.asyncio
async def test_resume_from_unknown_state(client, mock_command_executor):
    """Test resume command when bot state is unknown (first run)."""
    # Arrange
    command = ResumeCommand()
    expected_response = CommandResponse(
        success=True,
        message="Bot resumed successfully. Now accepting new signals.",
        timestamp=datetime.now(timezone.utc),
        previous_state="unknown",
        current_state="running",
        metadata=None,
    )
    mock_command_executor.resume.return_value = expected_response

    # Mock the dependency injection
    with patch(
        "api.app.routes.commands.get_command_executor",
        return_value=mock_command_executor,
    ):
        # Act
        response = await client.post(
            "/api/v1/commands/resume",
            json=command.model_dump(),
            headers={"X-API-Key": "test-api-key"},
        )

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["success"] is True
    assert data["previous_state"] == "unknown"
    assert data["current_state"] == "running"
