"""
Unit tests for TelegramClient.

Tests:
- send_message success (mock 200 response)
- send_message timeout
- send_message error handling
- validate_credentials

Coverage target: >90%
Task: T054 [GREEN]
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from src.trading_bot.notifications.telegram_client import TelegramClient, TelegramResponse


class TestTelegramClient:
    """Unit tests for TelegramClient class."""

    @pytest.mark.asyncio
    async def test_send_message_success(self):
        """Test successful message sending."""
        client = TelegramClient(bot_token="test_token", timeout=5.0)

        # Mock the bot's send_message method
        with patch.object(client.bot, 'send_message', new_callable=AsyncMock) as mock_send:
            mock_message = MagicMock()
            mock_message.message_id = 12345
            mock_send.return_value = mock_message

            response = await client.send_message(
                chat_id="123456789",
                text="Test message",
                parse_mode="Markdown"
            )

            assert response.success is True
            assert response.message_id == 12345
            assert response.error_message is None
            assert response.delivery_time_ms is not None
            assert response.delivery_time_ms < 1000  # Should be fast

    @pytest.mark.asyncio
    async def test_send_message_timeout(self):
        """Test message sending timeout."""
        client = TelegramClient(bot_token="test_token", timeout=0.1)

        # Mock slow API response
        with patch.object(client.bot, 'send_message', new_callable=AsyncMock) as mock_send:
            async def slow_send(*args, **kwargs):
                await asyncio.sleep(1)  # Longer than timeout
                return MagicMock()

            mock_send.side_effect = slow_send

            response = await client.send_message(
                chat_id="123456789",
                text="Test message"
            )

            assert response.success is False
            assert "timeout" in response.error_message.lower()

    @pytest.mark.asyncio
    async def test_send_message_telegram_error(self):
        """Test Telegram API error handling."""
        from telegram.error import TelegramError

        client = TelegramClient(bot_token="test_token", timeout=5.0)

        # Mock Telegram error
        with patch.object(client.bot, 'send_message', new_callable=AsyncMock) as mock_send:
            mock_send.side_effect = TelegramError("API error")

            response = await client.send_message(
                chat_id="123456789",
                text="Test message"
            )

            assert response.success is False
            assert "API error" in response.error_message

    @pytest.mark.asyncio
    async def test_validate_credentials_success(self):
        """Test successful credential validation."""
        client = TelegramClient(bot_token="valid_token", timeout=5.0)

        with patch.object(client.bot, 'get_me', new_callable=AsyncMock) as mock_get_me:
            mock_bot_info = MagicMock()
            mock_bot_info.username = "test_bot"
            mock_bot_info.id = 123456
            mock_get_me.return_value = mock_bot_info

            response = await client.validate_credentials()

            assert response.success is True
            assert response.error_message is None

    @pytest.mark.asyncio
    async def test_validate_credentials_failure(self):
        """Test credential validation failure."""
        client = TelegramClient(bot_token="invalid_token", timeout=5.0)

        with patch.object(client.bot, 'get_me', new_callable=AsyncMock) as mock_get_me:
            mock_get_me.side_effect = Exception("Invalid token")

            response = await client.validate_credentials()

            assert response.success is False
            assert "Invalid token" in response.error_message
