"""Unit tests for TelegramCommandHandler."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from trading_bot.telegram.command_handler import TelegramCommandHandler
from trading_bot.telegram.middleware import CommandAuthMiddleware, CommandRateLimiter
from trading_bot.telegram.response_formatter import ResponseFormatter


@pytest.fixture
def mock_application():
    """Mock telegram.ext.Application."""
    app = Mock()
    app.add_handler = Mock()
    return app


@pytest.fixture
def mock_auth_middleware():
    """Mock CommandAuthMiddleware."""
    auth = Mock(spec=CommandAuthMiddleware)
    auth.is_authorized = Mock(return_value=True)
    return auth


@pytest.fixture
def mock_rate_limiter():
    """Mock CommandRateLimiter."""
    limiter = Mock(spec=CommandRateLimiter)
    limiter.is_allowed = Mock(return_value=True)
    limiter.record_command = Mock()
    limiter.get_remaining_cooldown = Mock(return_value=5.0)
    return limiter


@pytest.fixture
def mock_formatter():
    """Mock ResponseFormatter."""
    formatter = Mock(spec=ResponseFormatter)
    formatter.format_welcome = Mock(return_value="Welcome!")
    formatter.format_help = Mock(return_value="Help")
    formatter.format_status = Mock(return_value="Status")
    formatter.format_positions = Mock(return_value="Positions")
    formatter.format_performance = Mock(return_value="Performance")
    formatter.format_error = Mock(return_value="Error")
    return formatter


@pytest.fixture
def mock_api_client():
    """Mock InternalAPIClient."""
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.get_bot_state = AsyncMock(
        return_value={"mode": "running", "positions": []}
    )
    client.get_positions = AsyncMock(return_value=[])
    client.get_performance_metrics = AsyncMock(return_value={})
    client.pause_bot = AsyncMock(return_value={"message": "Paused"})
    client.resume_bot = AsyncMock(return_value={"message": "Resumed"})
    return client


@pytest.fixture
def command_handler(
    mock_application,
    mock_auth_middleware,
    mock_rate_limiter,
    mock_formatter,
    mock_api_client,
):
    """Create TelegramCommandHandler with mocked dependencies."""
    # Create factory that returns the mock client
    def api_client_factory():
        return mock_api_client

    handler = TelegramCommandHandler(
        application=mock_application,
        auth_middleware=mock_auth_middleware,
        rate_limiter=mock_rate_limiter,
        formatter=mock_formatter,
        api_client_factory=api_client_factory,
    )
    return handler


def test_initialization(command_handler):
    """Test command handler initializes correctly."""
    assert command_handler.application is not None
    assert command_handler.auth_middleware is not None
    assert command_handler.rate_limiter is not None
    assert command_handler.formatter is not None


def test_register_commands(command_handler, mock_application):
    """Test register_commands adds all command handlers."""
    # Act
    command_handler.register_commands()

    # Assert - verify 7 command handlers were registered
    assert mock_application.add_handler.call_count == 7

    # Verify all calls were CommandHandler instances
    calls = mock_application.add_handler.call_args_list
    for call in calls:
        handler = call[0][0]
        assert handler.__class__.__name__ == "CommandHandler"


@pytest.mark.asyncio
async def test_handle_start_authorized(command_handler, mock_formatter):
    """Test /start command for authorized user."""
    # Arrange
    update = Mock()
    update.effective_user.id = 123456
    update.message.reply_text = AsyncMock()
    context = Mock()

    # Act
    await command_handler._handle_start(update, context)

    # Assert
    mock_formatter.format_welcome.assert_called_once_with(authorized=True)
    update.message.reply_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_start_unauthorized(command_handler, mock_auth_middleware, mock_formatter):
    """Test /start command for unauthorized user."""
    # Arrange
    mock_auth_middleware.is_authorized.return_value = False
    update = Mock()
    update.effective_user.id = 999999
    update.message.reply_text = AsyncMock()
    context = Mock()

    # Act
    await command_handler._handle_start(update, context)

    # Assert
    mock_formatter.format_welcome.assert_called_once_with(authorized=False)


@pytest.mark.asyncio
async def test_handle_help_success(command_handler, mock_formatter, mock_rate_limiter):
    """Test /help command returns help message."""
    # Arrange
    update = Mock()
    update.effective_user.id = 123456
    update.message.reply_text = AsyncMock()
    context = Mock()

    # Act
    await command_handler._handle_help(update, context)

    # Assert
    mock_formatter.format_help.assert_called_once()
    mock_rate_limiter.record_command.assert_called_once_with(123456)
    update.message.reply_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_help_unauthorized(command_handler, mock_auth_middleware, mock_formatter):
    """Test /help command rejects unauthorized user."""
    # Arrange
    mock_auth_middleware.is_authorized.return_value = False
    update = Mock()
    update.effective_user.id = 999999
    update.message.reply_text = AsyncMock()
    context = Mock()

    # Act
    await command_handler._handle_help(update, context)

    # Assert
    mock_formatter.format_error.assert_called_once_with("unauthorized")
    update.message.reply_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_help_rate_limited(command_handler, mock_rate_limiter, mock_formatter):
    """Test /help command blocks rate limited user."""
    # Arrange
    mock_rate_limiter.is_allowed.return_value = False
    mock_rate_limiter.get_remaining_cooldown.return_value = 3.5
    update = Mock()
    update.effective_user.id = 123456
    update.message.reply_text = AsyncMock()
    context = Mock()

    # Act
    await command_handler._handle_help(update, context)

    # Assert
    mock_formatter.format_error.assert_called_once_with("rate_limit", "4 seconds")
    update.message.reply_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_status_success(command_handler, mock_api_client, mock_formatter):
    """Test /status command returns bot status."""
    # Arrange
    update = Mock()
    update.effective_user.id = 123456
    update.message.reply_text = AsyncMock()
    context = Mock()

    # Act
    await command_handler._handle_status(update, context)

    # Assert
    mock_api_client.get_bot_state.assert_awaited_once()
    mock_formatter.format_status.assert_called_once()
    update.message.reply_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_status_api_error(command_handler, mock_api_client, mock_formatter):
    """Test /status command handles API errors gracefully."""
    # Arrange
    mock_api_client.get_bot_state.side_effect = Exception("Connection failed")
    update = Mock()
    update.effective_user.id = 123456
    update.message.reply_text = AsyncMock()
    context = Mock()

    # Act
    await command_handler._handle_status(update, context)

    # Assert
    mock_formatter.format_error.assert_called_once_with(
        "api_error", "Connection failed"
    )
    update.message.reply_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_pause_success(command_handler, mock_api_client):
    """Test /pause command pauses bot."""
    # Arrange
    update = Mock()
    update.effective_user.id = 123456
    update.message.reply_text = AsyncMock()
    context = Mock()

    # Act
    await command_handler._handle_pause(update, context)

    # Assert
    mock_api_client.pause_bot.assert_awaited_once_with(
        reason="Manual pause via Telegram"
    )
    update.message.reply_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_resume_success(command_handler, mock_api_client):
    """Test /resume command resumes bot."""
    # Arrange
    update = Mock()
    update.effective_user.id = 123456
    update.message.reply_text = AsyncMock()
    context = Mock()

    # Act
    await command_handler._handle_resume(update, context)

    # Assert
    mock_api_client.resume_bot.assert_awaited_once()
    update.message.reply_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_positions_success(command_handler, mock_api_client, mock_formatter):
    """Test /positions command returns positions."""
    # Arrange
    update = Mock()
    update.effective_user.id = 123456
    update.message.reply_text = AsyncMock()
    context = Mock()

    # Act
    await command_handler._handle_positions(update, context)

    # Assert
    mock_api_client.get_positions.assert_awaited_once()
    mock_formatter.format_positions.assert_called_once()
    update.message.reply_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_performance_success(command_handler, mock_api_client, mock_formatter):
    """Test /performance command returns metrics."""
    # Arrange
    update = Mock()
    update.effective_user.id = 123456
    update.message.reply_text = AsyncMock()
    context = Mock()

    # Act
    await command_handler._handle_performance(update, context)

    # Assert
    mock_api_client.get_performance_metrics.assert_awaited_once()
    mock_formatter.format_performance.assert_called_once()
    update.message.reply_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_check_rate_limit_allowed(command_handler, mock_rate_limiter):
    """Test rate limit check allows command."""
    # Arrange
    mock_rate_limiter.is_allowed.return_value = True
    update = Mock()

    # Act
    result = await command_handler._check_rate_limit(update, 123456)

    # Assert
    assert result is True


@pytest.mark.asyncio
async def test_check_rate_limit_blocked(command_handler, mock_rate_limiter, mock_formatter):
    """Test rate limit check blocks command."""
    # Arrange
    mock_rate_limiter.is_allowed.return_value = False
    mock_rate_limiter.get_remaining_cooldown.return_value = 3.7
    update = Mock()
    update.message.reply_text = AsyncMock()

    # Act
    result = await command_handler._check_rate_limit(update, 123456)

    # Assert
    assert result is False
    mock_formatter.format_error.assert_called_once_with("rate_limit", "4 seconds")
    update.message.reply_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_send_unauthorized_error(command_handler, mock_formatter):
    """Test unauthorized error is sent to user."""
    # Arrange
    update = Mock()
    update.message.reply_text = AsyncMock()

    # Act
    await command_handler._send_unauthorized_error(update)

    # Assert
    mock_formatter.format_error.assert_called_once_with("unauthorized")
    update.message.reply_text.assert_awaited_once()
