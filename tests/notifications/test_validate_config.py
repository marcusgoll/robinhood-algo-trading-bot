"""
Unit tests for validate_config CLI tool.

Tests:
- TELEGRAM_ENABLED=false (returns 1)
- Missing TELEGRAM_BOT_TOKEN (returns 1)
- Missing TELEGRAM_CHAT_ID (returns 1)
- Bot API validation failure (returns 1)
- Test message send failure (returns 1)
- Full validation success (returns 0)

Coverage target: >90%
Task: T056 [GREEN]
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal

from src.trading_bot.notifications.validate_config import validate_telegram_config


class TestValidateConfig:
    """Unit tests for validate_config async function."""

    @pytest.mark.asyncio
    async def test_disabled_telegram(self):
        """Test when TELEGRAM_ENABLED=false."""
        with patch.dict('os.environ', {'TELEGRAM_ENABLED': 'false'}):
            result = await validate_telegram_config()
            assert result == 1  # Should fail

    @pytest.mark.asyncio
    async def test_missing_bot_token(self):
        """Test when TELEGRAM_BOT_TOKEN is missing."""
        with patch.dict('os.environ', {
            'TELEGRAM_ENABLED': 'true',
            'TELEGRAM_BOT_TOKEN': '',
            'TELEGRAM_CHAT_ID': '123456789'
        }):
            result = await validate_telegram_config()
            assert result == 1  # Should fail

    @pytest.mark.asyncio
    async def test_missing_chat_id(self):
        """Test when TELEGRAM_CHAT_ID is missing."""
        with patch.dict('os.environ', {
            'TELEGRAM_ENABLED': 'true',
            'TELEGRAM_BOT_TOKEN': 'test_token',
            'TELEGRAM_CHAT_ID': ''
        }):
            result = await validate_telegram_config()
            assert result == 1  # Should fail

    @pytest.mark.asyncio
    async def test_bot_api_validation_failure(self):
        """Test when Bot API validation fails."""
        with patch.dict('os.environ', {
            'TELEGRAM_ENABLED': 'true',
            'TELEGRAM_BOT_TOKEN': 'invalid_token',
            'TELEGRAM_CHAT_ID': '123456789'
        }):
            with patch('src.trading_bot.notifications.validate_config.TelegramClient') as mock_client_class:
                # Mock client instance
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client

                # Mock failed validation
                mock_client.validate_credentials = AsyncMock(
                    return_value=MagicMock(
                        success=False,
                        error_message="Invalid bot token"
                    )
                )

                result = await validate_telegram_config()
                assert result == 1  # Should fail

    @pytest.mark.asyncio
    async def test_test_message_send_failure(self):
        """Test when test message send fails."""
        with patch.dict('os.environ', {
            'TELEGRAM_ENABLED': 'true',
            'TELEGRAM_BOT_TOKEN': 'test_token',
            'TELEGRAM_CHAT_ID': 'invalid_chat_id'
        }):
            with patch('src.trading_bot.notifications.validate_config.TelegramClient') as mock_client_class:
                # Mock client instance
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client

                # Mock successful validation but failed send
                mock_client.validate_credentials = AsyncMock(
                    return_value=MagicMock(success=True)
                )

                mock_client.send_message = AsyncMock(
                    return_value=MagicMock(
                        success=False,
                        error_message="Chat ID not found"
                    )
                )

                result = await validate_telegram_config()
                assert result == 1  # Should fail

    @pytest.mark.asyncio
    async def test_full_validation_success(self):
        """Test successful full validation."""
        with patch.dict('os.environ', {
            'TELEGRAM_ENABLED': 'true',
            'TELEGRAM_BOT_TOKEN': 'valid_token',
            'TELEGRAM_CHAT_ID': '123456789'
        }):
            with patch('src.trading_bot.notifications.validate_config.TelegramClient') as mock_client_class:
                # Mock client instance
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client

                # Mock successful validation
                mock_client.validate_credentials = AsyncMock(
                    return_value=MagicMock(success=True)
                )

                # Mock successful message send
                mock_client.send_message = AsyncMock(
                    return_value=MagicMock(
                        success=True,
                        message_id=12345,
                        delivery_time_ms=45.5
                    )
                )

                result = await validate_telegram_config()
                assert result == 0  # Should succeed

    @pytest.mark.asyncio
    async def test_unexpected_exception_handling(self):
        """Test handling of unexpected exceptions."""
        with patch.dict('os.environ', {
            'TELEGRAM_ENABLED': 'true',
            'TELEGRAM_BOT_TOKEN': 'test_token',
            'TELEGRAM_CHAT_ID': '123456789'
        }):
            with patch('src.trading_bot.notifications.validate_config.TelegramClient') as mock_client_class:
                # Mock client that raises exception
                mock_client_class.side_effect = Exception("Connection error")

                result = await validate_telegram_config()
                assert result == 1  # Should fail gracefully

    def test_main_entry_point_success(self):
        """Test main() CLI entry point with successful validation."""
        with patch('asyncio.run') as mock_asyncio_run:
            mock_asyncio_run.return_value = 0
            with patch('sys.exit') as mock_exit:
                from src.trading_bot.notifications.validate_config import main
                main()
                mock_exit.assert_called_once_with(0)

    def test_main_entry_point_failure(self):
        """Test main() CLI entry point with validation failure."""
        with patch('asyncio.run') as mock_asyncio_run:
            mock_asyncio_run.return_value = 1
            with patch('sys.exit') as mock_exit:
                from src.trading_bot.notifications.validate_config import main
                main()
                mock_exit.assert_called_once_with(1)
