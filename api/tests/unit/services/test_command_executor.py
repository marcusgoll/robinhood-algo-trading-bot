"""Unit tests for CommandExecutor service."""

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from api.app.services.command_executor import CommandExecutor


@pytest.fixture
def temp_state_file(tmp_path):
    """Create temporary state file for testing."""
    state_file = tmp_path / "bot_state.json"
    return state_file


@pytest.fixture
def executor(temp_state_file):
    """Create CommandExecutor with temporary state file."""
    return CommandExecutor(state_file=temp_state_file)


@pytest.mark.asyncio
async def test_pause_creates_paused_state(executor, temp_state_file):
    """Test pause command writes paused state to file."""
    # Act
    response = await executor.pause(reason="High volatility")

    # Assert
    assert response.success is True
    assert response.current_state == "paused"
    assert response.metadata["reason"] == "High volatility"

    # Verify state file
    state = json.loads(temp_state_file.read_text())
    assert state["mode"] == "paused"
    assert state["reason"] == "High volatility"
    assert "timestamp" in state


@pytest.mark.asyncio
async def test_pause_without_reason(executor, temp_state_file):
    """Test pause command without reason."""
    # Act
    response = await executor.pause()

    # Assert
    assert response.success is True
    assert response.current_state == "paused"
    assert response.metadata is None

    # Verify state file
    state = json.loads(temp_state_file.read_text())
    assert state["mode"] == "paused"
    assert state["reason"] is None


@pytest.mark.asyncio
async def test_resume_creates_running_state(executor, temp_state_file):
    """Test resume command writes running state to file."""
    # Arrange - first pause
    await executor.pause("Test pause")

    # Act
    response = await executor.resume()

    # Assert
    assert response.success is True
    assert response.current_state == "running"
    assert response.previous_state == "paused"

    # Verify state file
    state = json.loads(temp_state_file.read_text())
    assert state["mode"] == "running"
    assert "timestamp" in state


@pytest.mark.asyncio
async def test_pause_tracks_previous_state(executor, temp_state_file):
    """Test pause command records previous state."""
    # Arrange - write initial running state
    temp_state_file.write_text(
        json.dumps({"mode": "running", "timestamp": "2025-10-27T12:00:00Z"})
    )

    # Act
    response = await executor.pause("Emergency")

    # Assert
    assert response.previous_state == "running"
    assert response.current_state == "paused"

    # Verify state file
    state = json.loads(temp_state_file.read_text())
    assert state["previous_mode"] == "running"


@pytest.mark.asyncio
async def test_resume_tracks_previous_state(executor, temp_state_file):
    """Test resume command records previous state."""
    # Arrange - write paused state
    temp_state_file.write_text(
        json.dumps({"mode": "paused", "timestamp": "2025-10-27T12:00:00Z"})
    )

    # Act
    response = await executor.resume()

    # Assert
    assert response.previous_state == "paused"
    assert response.current_state == "running"

    # Verify state file
    state = json.loads(temp_state_file.read_text())
    assert state["previous_mode"] == "paused"


@pytest.mark.asyncio
async def test_read_state_file_missing(executor):
    """Test reading state when file doesn't exist (first run)."""
    # Act
    state = await executor._read_state()

    # Assert
    assert state == {"mode": "unknown"}


@pytest.mark.asyncio
async def test_read_state_corrupt_json(executor, temp_state_file):
    """Test reading state when JSON is corrupt."""
    # Arrange - write corrupt JSON
    temp_state_file.write_text("{ invalid json")

    # Act
    state = await executor._read_state()

    # Assert
    assert state == {"mode": "unknown"}


@pytest.mark.asyncio
async def test_pause_when_state_unknown(executor, temp_state_file):
    """Test pause command when state file doesn't exist."""
    # Act
    response = await executor.pause("First run")

    # Assert
    assert response.success is True
    assert response.previous_state == "unknown"
    assert response.current_state == "paused"


@pytest.mark.asyncio
async def test_resume_when_state_unknown(executor, temp_state_file):
    """Test resume command when state file doesn't exist."""
    # Act
    response = await executor.resume()

    # Assert
    assert response.success is True
    assert response.previous_state == "unknown"
    assert response.current_state == "running"


@pytest.mark.asyncio
async def test_write_state_creates_directory(tmp_path):
    """Test that state file parent directory is created if missing."""
    # Arrange
    state_file = tmp_path / "nested" / "logs" / "bot_state.json"
    executor = CommandExecutor(state_file=state_file)

    # Act
    await executor.pause("Test")

    # Assert
    assert state_file.exists()
    assert state_file.parent.exists()


@pytest.mark.asyncio
async def test_pause_timestamp_format(executor, temp_state_file):
    """Test that pause command uses correct timestamp format."""
    # Act
    response = await executor.pause("Test")

    # Assert - verify response timestamp is timezone-aware UTC
    assert response.timestamp.tzinfo is not None
    assert response.timestamp.tzinfo.utcoffset(None).total_seconds() == 0

    # Verify state file timestamp is ISO 8601
    state = json.loads(temp_state_file.read_text())
    timestamp_str = state["timestamp"]
    # Should be parseable as ISO 8601
    parsed = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
    assert parsed is not None


@pytest.mark.asyncio
async def test_resume_timestamp_format(executor, temp_state_file):
    """Test that resume command uses correct timestamp format."""
    # Act
    response = await executor.resume()

    # Assert - verify response timestamp is timezone-aware UTC
    assert response.timestamp.tzinfo is not None
    assert response.timestamp.tzinfo.utcoffset(None).total_seconds() == 0

    # Verify state file timestamp is ISO 8601
    state = json.loads(temp_state_file.read_text())
    timestamp_str = state["timestamp"]
    # Should be parseable as ISO 8601
    parsed = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
    assert parsed is not None


@pytest.mark.asyncio
async def test_multiple_pause_resume_cycle(executor, temp_state_file):
    """Test multiple pause/resume cycles work correctly."""
    # Cycle 1: Pause
    response1 = await executor.pause("Cycle 1")
    assert response1.current_state == "paused"

    # Cycle 2: Resume
    response2 = await executor.resume()
    assert response2.current_state == "running"
    assert response2.previous_state == "paused"

    # Cycle 3: Pause again
    response3 = await executor.pause("Cycle 3")
    assert response3.current_state == "paused"
    assert response3.previous_state == "running"

    # Cycle 4: Resume again
    response4 = await executor.resume()
    assert response4.current_state == "running"
    assert response4.previous_state == "paused"


@pytest.mark.asyncio
async def test_concurrent_pause_commands(executor, temp_state_file):
    """Test concurrent pause commands are handled safely."""
    import asyncio

    # Act - execute 5 pause commands concurrently
    tasks = [executor.pause(f"Concurrent {i}") for i in range(5)]
    responses = await asyncio.gather(*tasks)

    # Assert - all succeed
    for response in responses:
        assert response.success is True
        assert response.current_state == "paused"

    # Verify final state is paused
    state = json.loads(temp_state_file.read_text())
    assert state["mode"] == "paused"


@pytest.mark.asyncio
async def test_concurrent_resume_commands(executor, temp_state_file):
    """Test concurrent resume commands are handled safely."""
    import asyncio

    # Arrange - start in paused state
    await executor.pause("Setup")

    # Act - execute 5 resume commands concurrently
    tasks = [executor.resume() for i in range(5)]
    responses = await asyncio.gather(*tasks)

    # Assert - all succeed
    for response in responses:
        assert response.success is True
        assert response.current_state == "running"

    # Verify final state is running
    state = json.loads(temp_state_file.read_text())
    assert state["mode"] == "running"
