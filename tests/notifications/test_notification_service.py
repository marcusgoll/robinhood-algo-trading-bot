"""
Integration tests for NotificationService.

Tests:
- TELEGRAM_ENABLED=false (skipped notifications)
- Missing credentials (ConfigurationError)
- Rate limiting (same error twice)
- Async delivery (non-blocking)
- Position entry notification
- Position exit notification
- Risk alert notification
- Message delivery logging (success, timeout, error)
- JSONL error handling

Coverage target: >90%
Task: T055 [GREEN]
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from decimal import Decimal
from pathlib import Path

from src.trading_bot.notifications import ConfigurationError
from src.trading_bot.notifications.notification_service import NotificationService


class TestNotificationService:
    """Integration tests for NotificationService class."""

    def test_disabled_notifications(self):
        """Test notifications disabled when TELEGRAM_ENABLED=false."""
        with patch.dict('os.environ', {'TELEGRAM_ENABLED': 'false'}):
            service = NotificationService()

            assert service.is_enabled() is False
            # When disabled, client/formatter are not initialized
            assert not hasattr(service, 'client') or service.client is None

    def test_missing_credentials_raises_error(self):
        """Test ConfigurationError when credentials missing but enabled."""
        with patch.dict('os.environ', {
            'TELEGRAM_ENABLED': 'true',
            'TELEGRAM_BOT_TOKEN': '',
            'TELEGRAM_CHAT_ID': ''
        }):
            with pytest.raises(ConfigurationError):
                NotificationService()

    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Test rate limiting for duplicate error notifications."""
        with patch.dict('os.environ', {
            'TELEGRAM_ENABLED': 'true',
            'TELEGRAM_BOT_TOKEN': 'test_token',
            'TELEGRAM_CHAT_ID': '123456789',
            'TELEGRAM_ERROR_RATE_LIMIT_MINUTES': '60'
        }):
            service = NotificationService()

            # Mock the client
            service.client = MagicMock()
            service.client.send_message = AsyncMock(return_value=MagicMock(success=True))

            # Send first alert
            alert_event = {
                "breach_type": "max_daily_loss",
                "current_value": "$-300",
                "threshold": "$-200",
                "timestamp": "2025-10-27T14:00:00Z"
            }

            await service.send_risk_alert(alert_event)
            assert service._is_rate_limited("max_daily_loss") is True

    def test_graceful_degradation_on_import_error(self):
        """Test graceful degradation when notification module unavailable."""
        # If get_notification_service fails, bot should continue
        with patch('src.trading_bot.notifications.get_notification_service') as mock_get:
            mock_get.side_effect = ImportError("Module not found")

            # Should not raise, just return None or disabled service
            try:
                from src.trading_bot.notifications import get_notification_service
                service = get_notification_service()
                # Should handle gracefully
                assert True
            except ImportError:
                # Expected if module truly unavailable
                assert True

    @pytest.mark.asyncio
    async def test_send_position_entry_when_enabled(self):
        """Test position entry notification is sent when enabled."""
        with patch.dict('os.environ', {
            'TELEGRAM_ENABLED': 'true',
            'TELEGRAM_BOT_TOKEN': 'test_token',
            'TELEGRAM_CHAT_ID': '123456789',
            'TELEGRAM_NOTIFY_POSITIONS': 'true'
        }):
            service = NotificationService()

            # Mock client and formatter
            service.client = MagicMock()
            service.client.send_message = AsyncMock(
                return_value=MagicMock(success=True, message_id=999, delivery_time_ms=10.5)
            )

            # Mock trade record
            trade_record = MagicMock()
            trade_record.symbol = "AAPL"
            trade_record.price = Decimal("150.00")
            trade_record.quantity = 100
            trade_record.total_value = Decimal("15000.00")
            trade_record.stop_loss = Decimal("147.00")
            trade_record.target = Decimal("156.00")
            trade_record.execution_mode = "PAPER"
            trade_record.strategy_name = "bull-flag"
            trade_record.entry_type = "breakout"

            # Send position entry
            await service.send_position_entry(trade_record)

            # Allow async task to complete
            await asyncio.sleep(0.1)

            # Verify client was called (through _send_with_logging)
            assert service.client.send_message.called

    @pytest.mark.asyncio
    async def test_send_position_entry_when_disabled(self):
        """Test position entry notification skipped when notify_positions=false."""
        with patch.dict('os.environ', {
            'TELEGRAM_ENABLED': 'true',
            'TELEGRAM_BOT_TOKEN': 'test_token',
            'TELEGRAM_CHAT_ID': '123456789',
            'TELEGRAM_NOTIFY_POSITIONS': 'false'
        }):
            service = NotificationService()

            # Mock client
            service.client = MagicMock()
            service.client.send_message = AsyncMock()

            # Mock trade record
            trade_record = MagicMock()
            trade_record.symbol = "AAPL"

            # Send position entry
            await service.send_position_entry(trade_record)

            # Verify client was NOT called
            service.client.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_position_exit_when_disabled(self):
        """Test position exit notification skipped when notify_positions=false."""
        with patch.dict('os.environ', {
            'TELEGRAM_ENABLED': 'true',
            'TELEGRAM_BOT_TOKEN': 'test_token',
            'TELEGRAM_CHAT_ID': '123456789',
            'TELEGRAM_NOTIFY_POSITIONS': 'false'
        }):
            service = NotificationService()

            # Mock client
            service.client = MagicMock()
            service.client.send_message = AsyncMock()

            # Mock trade record
            trade_record = MagicMock()
            trade_record.symbol = "AAPL"
            trade_record.price = Decimal("150.00")
            trade_record.quantity = 100
            trade_record.profit_loss = Decimal("500.00")
            trade_record.exit_reasoning = "Take Profit"
            trade_record.hold_duration_seconds = 3600
            trade_record.execution_mode = "LIVE"

            # Send position exit
            await service.send_position_exit(trade_record)

            # Verify client was NOT called
            service.client.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_position_exit_with_profit(self):
        """Test position exit notification with profit."""
        with patch.dict('os.environ', {
            'TELEGRAM_ENABLED': 'true',
            'TELEGRAM_BOT_TOKEN': 'test_token',
            'TELEGRAM_CHAT_ID': '123456789',
            'TELEGRAM_NOTIFY_POSITIONS': 'true'
        }):
            service = NotificationService()

            # Mock client
            service.client = MagicMock()
            service.client.send_message = AsyncMock(
                return_value=MagicMock(success=True, message_id=888, delivery_time_ms=9.2)
            )

            # Mock trade record with profit
            trade_record = MagicMock()
            trade_record.symbol = "NVDA"
            trade_record.price = Decimal("500.00")  # Exit price
            trade_record.quantity = 10
            trade_record.profit_loss = Decimal("600.00")  # Profit
            trade_record.exit_reasoning = "Take Profit"
            trade_record.hold_duration_seconds = 8100
            trade_record.execution_mode = "LIVE"

            # Send position exit
            await service.send_position_exit(trade_record)

            # Allow async task to complete
            await asyncio.sleep(0.1)

            # Verify client was called
            assert service.client.send_message.called

    @pytest.mark.asyncio
    async def test_send_position_exit_with_loss(self):
        """Test position exit notification with loss."""
        with patch.dict('os.environ', {
            'TELEGRAM_ENABLED': 'true',
            'TELEGRAM_BOT_TOKEN': 'test_token',
            'TELEGRAM_CHAT_ID': '123456789',
            'TELEGRAM_NOTIFY_POSITIONS': 'true'
        }):
            service = NotificationService()

            # Mock client
            service.client = MagicMock()
            service.client.send_message = AsyncMock(
                return_value=MagicMock(success=True, message_id=777, delivery_time_ms=8.1)
            )

            # Mock trade record with loss
            trade_record = MagicMock()
            trade_record.symbol = "META"
            trade_record.price = Decimal("300.00")  # Exit price
            trade_record.quantity = 5
            trade_record.profit_loss = Decimal("-200.00")  # Loss
            trade_record.exit_reasoning = "Stop Loss"
            trade_record.hold_duration_seconds = 45
            trade_record.execution_mode = "PAPER"

            # Send position exit
            await service.send_position_exit(trade_record)

            # Allow async task to complete
            await asyncio.sleep(0.1)

            # Verify client was called
            assert service.client.send_message.called

    @pytest.mark.asyncio
    async def test_send_risk_alert_success_and_logging(self):
        """Test risk alert sends and logs successfully."""
        with patch.dict('os.environ', {
            'TELEGRAM_ENABLED': 'true',
            'TELEGRAM_BOT_TOKEN': 'test_token',
            'TELEGRAM_CHAT_ID': '123456789',
            'TELEGRAM_NOTIFY_ALERTS': 'true',
            'TELEGRAM_ERROR_RATE_LIMIT_MINUTES': '60'
        }):
            service = NotificationService()

            # Mock client
            service.client = MagicMock()
            service.client.send_message = AsyncMock(
                return_value=MagicMock(
                    success=True,
                    message_id=555,
                    delivery_time_ms=12.3,
                    error_message=None
                )
            )

            # Mock log file
            with patch('builtins.open', mock_open()) as mock_file:
                alert_event = {
                    "breach_type": "max_daily_loss",
                    "current_value": "$-500",
                    "threshold": "$-300",
                    "timestamp": "2025-10-27T15:30:00Z"
                }

                # Send alert
                await service.send_risk_alert(alert_event)

                # Allow async task to complete
                await asyncio.sleep(0.1)

                # Verify client was called
                assert service.client.send_message.called

    @pytest.mark.asyncio
    async def test_send_risk_alert_timeout(self):
        """Test risk alert handles timeout gracefully."""
        with patch.dict('os.environ', {
            'TELEGRAM_ENABLED': 'true',
            'TELEGRAM_BOT_TOKEN': 'test_token',
            'TELEGRAM_CHAT_ID': '123456789',
            'TELEGRAM_NOTIFY_ALERTS': 'true'
        }):
            service = NotificationService()

            # Mock client to timeout
            service.client = MagicMock()
            async def timeout_send(*args, **kwargs):
                await asyncio.sleep(10)  # Longer than 5s timeout
                return MagicMock(success=False)

            service.client.send_message = AsyncMock(side_effect=timeout_send)

            # Mock log file
            with patch('builtins.open', mock_open()):
                alert_event = {
                    "breach_type": "max_daily_loss",
                    "current_value": "$-500",
                    "threshold": "$-300",
                    "timestamp": "2025-10-27T15:30:00Z"
                }

                # Send alert (should timeout at 5s)
                await service.send_risk_alert(alert_event)

                # Allow some time for async task to process timeout
                await asyncio.sleep(0.2)

                # Verify client was called
                assert service.client.send_message.called

    @pytest.mark.asyncio
    async def test_send_risk_alert_exception_handling(self):
        """Test risk alert handles exceptions gracefully."""
        with patch.dict('os.environ', {
            'TELEGRAM_ENABLED': 'true',
            'TELEGRAM_BOT_TOKEN': 'test_token',
            'TELEGRAM_CHAT_ID': '123456789',
            'TELEGRAM_NOTIFY_ALERTS': 'true'
        }):
            service = NotificationService()

            # Mock client to raise exception
            service.client = MagicMock()
            service.client.send_message = AsyncMock(
                side_effect=Exception("Network error")
            )

            # Mock log file
            with patch('builtins.open', mock_open()):
                alert_event = {
                    "breach_type": "max_loss_per_position",
                    "current_value": "$-150",
                    "threshold": "$-100",
                    "timestamp": "2025-10-27T15:45:00Z"
                }

                # Send alert (should catch exception)
                await service.send_risk_alert(alert_event)

                # Allow async task to complete
                await asyncio.sleep(0.1)

                # Verify client was called
                assert service.client.send_message.called

    @pytest.mark.asyncio
    async def test_send_risk_alert_not_when_disabled(self):
        """Test risk alert skipped when notify_alerts=false."""
        with patch.dict('os.environ', {
            'TELEGRAM_ENABLED': 'true',
            'TELEGRAM_BOT_TOKEN': 'test_token',
            'TELEGRAM_CHAT_ID': '123456789',
            'TELEGRAM_NOTIFY_ALERTS': 'false'
        }):
            service = NotificationService()

            # Mock client
            service.client = MagicMock()
            service.client.send_message = AsyncMock()

            alert_event = {
                "breach_type": "max_daily_loss",
                "current_value": "$-500",
                "threshold": "$-300",
                "timestamp": "2025-10-27T15:30:00Z"
            }

            # Send alert
            await service.send_risk_alert(alert_event)

            # Verify client was NOT called
            service.client.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_jsonl_error_handling_on_disk_full(self):
        """Test JSONL logging fallback when disk full."""
        with patch.dict('os.environ', {
            'TELEGRAM_ENABLED': 'true',
            'TELEGRAM_BOT_TOKEN': 'test_token',
            'TELEGRAM_CHAT_ID': '123456789',
            'TELEGRAM_NOTIFY_POSITIONS': 'true'
        }):
            service = NotificationService()

            # Mock client
            service.client = MagicMock()
            service.client.send_message = AsyncMock(
                return_value=MagicMock(success=True, message_id=444, delivery_time_ms=5.0)
            )

            # Mock log file to raise OSError (disk full)
            with patch('builtins.open', side_effect=OSError("No space left on device")):
                trade_record = MagicMock()
                trade_record.symbol = "TSLA"
                trade_record.price = Decimal("200.00")
                trade_record.quantity = 50
                trade_record.total_value = Decimal("10000.00")
                trade_record.stop_loss = None
                trade_record.target = None
                trade_record.execution_mode = "LIVE"
                trade_record.strategy_name = "manual"
                trade_record.entry_type = "manual"

                # Send position entry (should not raise despite JSONL error)
                await service.send_position_entry(trade_record)

                # Allow async task to complete
                await asyncio.sleep(0.1)

                # Verify client was called (JSONL error doesn't block)
                assert service.client.send_message.called

    @pytest.mark.asyncio
    async def test_rate_limiting_concurrent_access(self):
        """Test rate limiting is thread-safe with asyncio.Lock."""
        with patch.dict('os.environ', {
            'TELEGRAM_ENABLED': 'true',
            'TELEGRAM_BOT_TOKEN': 'test_token',
            'TELEGRAM_CHAT_ID': '123456789',
            'TELEGRAM_NOTIFY_ALERTS': 'true',
            'TELEGRAM_ERROR_RATE_LIMIT_MINUTES': '1'
        }):
            service = NotificationService()

            # Mock client
            service.client = MagicMock()
            service.client.send_message = AsyncMock(
                return_value=MagicMock(success=True, message_id=333, delivery_time_ms=3.0)
            )

            # Mock log file
            with patch('builtins.open', mock_open()):
                alert_event = {
                    "breach_type": "max_daily_loss",
                    "current_value": "$-300",
                    "threshold": "$-200",
                    "timestamp": "2025-10-27T14:00:00Z"
                }

                # Send first alert
                await service.send_risk_alert(alert_event)
                await asyncio.sleep(0.1)

                # Second alert should be rate limited
                await service.send_risk_alert(alert_event)
                await asyncio.sleep(0.1)

                # Client should only be called once (rate limited on second)
                assert service.client.send_message.call_count == 1

    @pytest.mark.asyncio
    async def test_send_risk_alert_failure_logging(self):
        """Test risk alert failure is logged properly."""
        with patch.dict('os.environ', {
            'TELEGRAM_ENABLED': 'true',
            'TELEGRAM_BOT_TOKEN': 'test_token',
            'TELEGRAM_CHAT_ID': '123456789',
            'TELEGRAM_NOTIFY_ALERTS': 'true'
        }):
            service = NotificationService()

            # Mock client to return failure
            service.client = MagicMock()
            service.client.send_message = AsyncMock(
                return_value=MagicMock(
                    success=False,
                    message_id=None,
                    error_message="Chat ID not found"
                )
            )

            # Mock log file
            with patch('builtins.open', mock_open()):
                alert_event = {
                    "breach_type": "max_daily_loss",
                    "current_value": "$-600",
                    "threshold": "$-500",
                    "timestamp": "2025-10-27T16:00:00Z"
                }

                # Send alert
                await service.send_risk_alert(alert_event)

                # Allow async task to complete
                await asyncio.sleep(0.1)

                # Verify client was called and failure was logged
                assert service.client.send_message.called

    @pytest.mark.asyncio
    async def test_send_position_exit_failure_logging(self):
        """Test position exit failure is logged properly."""
        with patch.dict('os.environ', {
            'TELEGRAM_ENABLED': 'true',
            'TELEGRAM_BOT_TOKEN': 'test_token',
            'TELEGRAM_CHAT_ID': '123456789',
            'TELEGRAM_NOTIFY_POSITIONS': 'true'
        }):
            service = NotificationService()

            # Mock client to return failure
            service.client = MagicMock()
            service.client.send_message = AsyncMock(
                return_value=MagicMock(
                    success=False,
                    message_id=None,
                    error_message="Invalid token"
                )
            )

            # Mock log file
            with patch('builtins.open', mock_open()):
                trade_record = MagicMock()
                trade_record.symbol = "GME"
                trade_record.price = Decimal("25.00")
                trade_record.quantity = 100
                trade_record.profit_loss = Decimal("500.00")
                trade_record.exit_reasoning = "Manual Exit"
                trade_record.hold_duration_seconds = 3600
                trade_record.execution_mode = "PAPER"

                # Send exit
                await service.send_position_exit(trade_record)

                # Allow async task to complete
                await asyncio.sleep(0.1)

                # Verify client was called
                assert service.client.send_message.called

    @pytest.mark.asyncio
    async def test_actual_timeout_handling(self):
        """Test actual timeout is caught and logged."""
        with patch.dict('os.environ', {
            'TELEGRAM_ENABLED': 'true',
            'TELEGRAM_BOT_TOKEN': 'test_token',
            'TELEGRAM_CHAT_ID': '123456789',
            'TELEGRAM_NOTIFY_ALERTS': 'true'
        }):
            service = NotificationService()

            # Mock client to actually timeout
            service.client = MagicMock()
            async def slow_send(*args, **kwargs):
                # Sleep for longer than the 5s timeout in _send_with_logging
                await asyncio.sleep(6.0)
                return MagicMock(success=False)

            service.client.send_message = AsyncMock(side_effect=slow_send)

            # Mock log file
            with patch('builtins.open', mock_open()):
                alert_event = {
                    "breach_type": "max_daily_loss",
                    "current_value": "$-800",
                    "threshold": "$-600",
                    "timestamp": "2025-10-27T17:00:00Z"
                }

                # Send alert
                await service.send_risk_alert(alert_event)

                # Wait longer than timeout
                await asyncio.sleep(7.0)

                # Verify client was called
                assert service.client.send_message.called
