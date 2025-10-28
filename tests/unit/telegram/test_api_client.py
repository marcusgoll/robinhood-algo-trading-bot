"""Unit tests for InternalAPIClient."""

from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from trading_bot.telegram.api_client import InternalAPIClient


@pytest.fixture
def mock_httpx_client():
    """Mock httpx.AsyncClient for testing."""
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock()
    client.post = AsyncMock()
    client.aclose = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_context_manager_initialization():
    """Test async context manager creates and closes client."""
    # Act & Assert
    async with InternalAPIClient() as client:
        assert client._client is not None
        assert isinstance(client._client, httpx.AsyncClient)

    # Client should be closed after exiting context
    # (Can't check directly, but aclose was called)


@pytest.mark.asyncio
async def test_get_bot_state_success(mock_httpx_client):
    """Test get_bot_state returns API response."""
    # Arrange
    expected_state = {
        "mode": "running",
        "positions": [{"symbol": "AAPL", "qty": 100}],
        "balance": 10000.00,
    }
    mock_response = Mock()
    mock_response.json.return_value = expected_state
    mock_response.raise_for_status = Mock()
    mock_httpx_client.get.return_value = mock_response

    # Act
    async with InternalAPIClient() as client:
        client._client = mock_httpx_client
        state = await client.get_bot_state()

    # Assert
    assert state == expected_state
    mock_httpx_client.get.assert_awaited_once_with("/api/v1/state")


@pytest.mark.asyncio
async def test_get_bot_summary_success(mock_httpx_client):
    """Test get_bot_summary returns API response."""
    # Arrange
    expected_summary = {"mode": "running", "positions_count": 2}
    mock_response = Mock()
    mock_response.json.return_value = expected_summary
    mock_response.raise_for_status = Mock()
    mock_httpx_client.get.return_value = mock_response

    # Act
    async with InternalAPIClient() as client:
        client._client = mock_httpx_client
        summary = await client.get_bot_summary()

    # Assert
    assert summary == expected_summary
    mock_httpx_client.get.assert_awaited_once_with("/api/v1/summary")


@pytest.mark.asyncio
async def test_pause_bot_with_reason(mock_httpx_client):
    """Test pause_bot sends reason in request."""
    # Arrange
    expected_response = {
        "success": True,
        "message": "Bot paused",
        "current_state": "paused",
    }
    mock_response = Mock()
    mock_response.json.return_value = expected_response
    mock_response.raise_for_status = Mock()
    mock_httpx_client.post.return_value = mock_response

    # Act
    async with InternalAPIClient() as client:
        client._client = mock_httpx_client
        response = await client.pause_bot(reason="High volatility")

    # Assert
    assert response == expected_response
    mock_httpx_client.post.assert_awaited_once_with(
        "/api/v1/commands/pause", json={"reason": "High volatility"}
    )


@pytest.mark.asyncio
async def test_pause_bot_without_reason(mock_httpx_client):
    """Test pause_bot works without reason."""
    # Arrange
    expected_response = {"success": True, "current_state": "paused"}
    mock_response = Mock()
    mock_response.json.return_value = expected_response
    mock_response.raise_for_status = Mock()
    mock_httpx_client.post.return_value = mock_response

    # Act
    async with InternalAPIClient() as client:
        client._client = mock_httpx_client
        response = await client.pause_bot()

    # Assert
    assert response == expected_response
    mock_httpx_client.post.assert_awaited_once_with(
        "/api/v1/commands/pause", json={}
    )


@pytest.mark.asyncio
async def test_resume_bot_success(mock_httpx_client):
    """Test resume_bot sends correct request."""
    # Arrange
    expected_response = {"success": True, "current_state": "running"}
    mock_response = Mock()
    mock_response.json.return_value = expected_response
    mock_response.raise_for_status = Mock()
    mock_httpx_client.post.return_value = mock_response

    # Act
    async with InternalAPIClient() as client:
        client._client = mock_httpx_client
        response = await client.resume_bot()

    # Assert
    assert response == expected_response
    mock_httpx_client.post.assert_awaited_once_with(
        "/api/v1/commands/resume", json={}
    )


@pytest.mark.asyncio
async def test_get_positions_extracts_from_state(mock_httpx_client):
    """Test get_positions extracts positions from bot state."""
    # Arrange
    state_response = {
        "mode": "running",
        "positions": [
            {"symbol": "AAPL", "qty": 100},
            {"symbol": "MSFT", "qty": 50},
        ],
        "balance": 10000.00,
    }
    mock_response = Mock()
    mock_response.json.return_value = state_response
    mock_response.raise_for_status = Mock()
    mock_httpx_client.get.return_value = mock_response

    # Act
    async with InternalAPIClient() as client:
        client._client = mock_httpx_client
        positions = await client.get_positions()

    # Assert
    assert positions == [
        {"symbol": "AAPL", "qty": 100},
        {"symbol": "MSFT", "qty": 50},
    ]


@pytest.mark.asyncio
async def test_get_positions_empty_when_no_positions(mock_httpx_client):
    """Test get_positions returns empty list when no positions."""
    # Arrange
    state_response = {"mode": "running", "balance": 10000.00}
    mock_response = Mock()
    mock_response.json.return_value = state_response
    mock_response.raise_for_status = Mock()
    mock_httpx_client.get.return_value = mock_response

    # Act
    async with InternalAPIClient() as client:
        client._client = mock_httpx_client
        positions = await client.get_positions()

    # Assert
    assert positions == []


@pytest.mark.asyncio
async def test_get_performance_metrics_extracts_from_state(mock_httpx_client):
    """Test get_performance_metrics extracts metrics from bot state."""
    # Arrange
    state_response = {
        "mode": "running",
        "performance": {
            "win_rate": 0.65,
            "total_pnl": 2500.00,
            "total_trades": 50,
        },
    }
    mock_response = Mock()
    mock_response.json.return_value = state_response
    mock_response.raise_for_status = Mock()
    mock_httpx_client.get.return_value = mock_response

    # Act
    async with InternalAPIClient() as client:
        client._client = mock_httpx_client
        metrics = await client.get_performance_metrics()

    # Assert
    assert metrics == {
        "win_rate": 0.65,
        "total_pnl": 2500.00,
        "total_trades": 50,
    }


@pytest.mark.asyncio
async def test_get_performance_metrics_empty_when_missing(mock_httpx_client):
    """Test get_performance_metrics returns empty dict when missing."""
    # Arrange
    state_response = {"mode": "running", "positions": []}
    mock_response = Mock()
    mock_response.json.return_value = state_response
    mock_response.raise_for_status = Mock()
    mock_httpx_client.get.return_value = mock_response

    # Act
    async with InternalAPIClient() as client:
        client._client = mock_httpx_client
        metrics = await client.get_performance_metrics()

    # Assert
    assert metrics == {}


@pytest.mark.asyncio
async def test_api_call_without_context_raises_error():
    """Test API calls outside context manager raise error."""
    # Arrange
    client = InternalAPIClient()

    # Act & Assert
    with pytest.raises(RuntimeError, match="Client not initialized"):
        await client.get_bot_state()


@pytest.mark.asyncio
async def test_http_error_propagates(mock_httpx_client):
    """Test HTTP errors are propagated to caller."""
    # Arrange
    mock_httpx_client.get.side_effect = httpx.HTTPStatusError(
        "500 Server Error", request=Mock(), response=Mock()
    )

    # Act & Assert
    async with InternalAPIClient() as client:
        client._client = mock_httpx_client
        with pytest.raises(httpx.HTTPStatusError):
            await client.get_bot_state()


@pytest.mark.asyncio
async def test_request_error_propagates(mock_httpx_client):
    """Test request errors (timeout, connection) are propagated."""
    # Arrange
    mock_httpx_client.get.side_effect = httpx.RequestError(
        "Connection refused", request=Mock()
    )

    # Act & Assert
    async with InternalAPIClient() as client:
        client._client = mock_httpx_client
        with pytest.raises(httpx.RequestError):
            await client.get_bot_state()


@pytest.mark.asyncio
async def test_custom_base_url():
    """Test client can be initialized with custom base URL."""
    # Act
    async with InternalAPIClient(
        base_url="http://custom-api:9000"
    ) as client:
        # Assert
        assert client.base_url == "http://custom-api:9000"


@pytest.mark.asyncio
async def test_custom_timeout():
    """Test client can be initialized with custom timeout."""
    # Act
    async with InternalAPIClient(timeout=5.0) as client:
        # Assert
        assert client.timeout == 5.0


@pytest.mark.asyncio
async def test_api_key_from_env():
    """Test API key is loaded from environment variable."""
    # Arrange
    with patch.dict("os.environ", {"BOT_API_AUTH_TOKEN": "test-key-123"}):
        # Act
        async with InternalAPIClient() as client:
            # Assert
            assert client.api_key == "test-key-123"


@pytest.mark.asyncio
async def test_api_key_custom_override():
    """Test custom API key overrides environment variable."""
    # Arrange
    with patch.dict("os.environ", {"BOT_API_AUTH_TOKEN": "env-key"}):
        # Act
        async with InternalAPIClient(api_key="custom-key") as client:
            # Assert
            assert client.api_key == "custom-key"
