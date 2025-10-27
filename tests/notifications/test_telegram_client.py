"""
Unit tests for TelegramClient.

Tests:
- send_message success (mock 200 response)
- send_message timeout
- send_message error handling
- send_message validation (chat_id, message length)
- validate_credentials

Coverage target: >90%
Task: T054 [GREEN]
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from src.trading_bot.notifications.telegram_client import TelegramClient, TelegramResponse


@pytest.fixture
def mock_telegram_bot():
    """Fixture to mock telegram.Bot class."""
    with patch('src.trading_bot.notifications.telegram_client.Bot') as mock_bot_class:
        mock_bot_instance = MagicMock()
        mock_bot_class.return_value = mock_bot_instance
        yield mock_bot_instance


class TestTelegramClient:
    """Unit tests for TelegramClient class."""

    @pytest.mark.asyncio
    async def test_send_message_success(self, mock_telegram_bot):
        """Test successful message sending."""
        # Setup
        mock_message = MagicMock()
        mock_message.message_id = 12345
        mock_telegram_bot.send_message = AsyncMock(return_value=mock_message)

        client = TelegramClient(bot_token="test_token", timeout=5.0)

        # Execute
        response = await client.send_message(
            chat_id="123456789",
            text="Test message",
            parse_mode="Markdown"
        )

        # Verify
        assert response.success is True
        assert response.message_id == 12345
        assert response.error_message is None
        assert response.delivery_time_ms is not None
        assert response.delivery_time_ms < 1000  # Should be fast
        mock_telegram_bot.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_timeout(self, mock_telegram_bot):
        """Test message sending timeout."""
        # Setup: Mock slow API response
        async def slow_send(*args, **kwargs):
            await asyncio.sleep(1)  # Longer than timeout
            return MagicMock()

        mock_telegram_bot.send_message = AsyncMock(side_effect=slow_send)

        client = TelegramClient(bot_token="test_token", timeout=0.1)

        # Execute
        response = await client.send_message(
            chat_id="123456789",
            text="Test message"
        )

        # Verify
        assert response.success is False
        assert "timeout" in response.error_message.lower()

    @pytest.mark.asyncio
    async def test_send_message_telegram_error(self, mock_telegram_bot):
        """Test Telegram API error handling."""
        from telegram.error import TelegramError

        # Setup
        mock_telegram_bot.send_message = AsyncMock(side_effect=TelegramError("API error"))
        client = TelegramClient(bot_token="test_token", timeout=5.0)

        # Execute
        response = await client.send_message(
            chat_id="123456789",
            text="Test message"
        )

        # Verify
        assert response.success is False
        assert "API error" in response.error_message

    @pytest.mark.asyncio
    async def test_send_message_invalid_chat_id(self, mock_telegram_bot):
        """Test invalid chat_id format validation."""
        client = TelegramClient(bot_token="test_token", timeout=5.0)

        # Execute - invalid chat_id (not numeric)
        response = await client.send_message(
            chat_id="invalid-chat-id",
            text="Test message"
        )

        # Verify - should fail validation without calling API
        assert response.success is False
        assert "Invalid chat_id format" in response.error_message
        mock_telegram_bot.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_message_exceeds_length_limit(self, mock_telegram_bot):
        """Test message length validation."""
        client = TelegramClient(bot_token="test_token", timeout=5.0)

        # Create message that exceeds 4096 character limit
        long_message = "x" * 4097

        # Execute
        response = await client.send_message(
            chat_id="123456789",
            text=long_message
        )

        # Verify - should fail validation without calling API
        assert response.success is False
        assert "exceeds Telegram limit" in response.error_message
        mock_telegram_bot.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_validate_credentials_success(self, mock_telegram_bot):
        """Test successful credential validation."""
        # Setup
        mock_bot_info = MagicMock()
        mock_bot_info.username = "test_bot"
        mock_bot_info.id = 123456
        mock_telegram_bot.get_me = AsyncMock(return_value=mock_bot_info)

        client = TelegramClient(bot_token="valid_token", timeout=5.0)

        # Execute
        response = await client.validate_credentials()

        # Verify
        assert response.success is True
        assert response.error_message is None

    @pytest.mark.asyncio
    async def test_validate_credentials_failure(self, mock_telegram_bot):
        """Test credential validation failure."""
        # Setup
        mock_telegram_bot.get_me = AsyncMock(side_effect=Exception("Invalid token"))

        client = TelegramClient(bot_token="invalid_token", timeout=5.0)

        # Execute
        response = await client.validate_credentials()

        # Verify
        assert response.success is False
        assert "Invalid token" in response.error_message

    @pytest.mark.asyncio
    async def test_send_message_unexpected_error(self, mock_telegram_bot):
        """Test unexpected error handling in send_message."""
        # Setup - Mock general exception (not TelegramError or TimeoutError)
        mock_telegram_bot.send_message = AsyncMock(
            side_effect=RuntimeError("Network connection failed")
        )

        client = TelegramClient(bot_token="test_token", timeout=5.0)

        # Execute
        response = await client.send_message(
            chat_id="123456789",
            text="Test message"
        )

        # Verify
        assert response.success is False
        assert "RuntimeError" in response.error_message
        assert "Network connection failed" in response.error_message
        assert response.delivery_time_ms is not None
