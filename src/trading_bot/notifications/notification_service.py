"""
Notification Service Orchestrator

Coordinates Telegram notifications for trading bot events.

Responsibilities:
- Environment configuration validation
- Message formatting and delivery
- Rate limiting for error notifications
- Non-blocking async delivery
- Graceful degradation on missing credentials

Constitution v1.0.0:
- §Non_Blocking: Never block trading operations
- §Graceful_Degradation: Missing config disables notifications, not trading
- §Security: Credentials from environment only

Tasks: T012 [GREEN] - Implement NotificationService
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from . import ConfigurationError
from .message_formatter import (
    MessageFormatter,
    PositionEntryData,
    PositionExitData,
    RiskAlertData,
)
from .telegram_client import TelegramClient

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class NotificationService:
    """
    Orchestrate Telegram notifications for trading events.

    Features:
    - Non-blocking async delivery with fire-and-forget pattern
    - Graceful degradation when credentials missing
    - Rate limiting for error notifications
    - JSONL logging to logs/telegram-notifications.jsonl

    Usage:
        service = NotificationService()
        if service.is_enabled():
            await service.send_position_entry(trade_record)

    Configuration (from .env):
        TELEGRAM_ENABLED=true
        TELEGRAM_BOT_TOKEN=your_bot_token
        TELEGRAM_CHAT_ID=your_chat_id
        TELEGRAM_NOTIFY_POSITIONS=true
        TELEGRAM_NOTIFY_ALERTS=true
        TELEGRAM_PARSE_MODE=Markdown
        TELEGRAM_INCLUDE_EMOJIS=true
        TELEGRAM_ERROR_RATE_LIMIT_MINUTES=60
    """

    def __init__(self):
        """
        Initialize notification service with environment config.

        Raises:
            ConfigurationError: If TELEGRAM_ENABLED=true but credentials missing
        """
        # Load configuration
        self.enabled = os.getenv("TELEGRAM_ENABLED", "false").lower() == "true"
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        self.notify_positions = os.getenv("TELEGRAM_NOTIFY_POSITIONS", "true").lower() == "true"
        self.notify_alerts = os.getenv("TELEGRAM_NOTIFY_ALERTS", "true").lower() == "true"
        self.parse_mode = os.getenv("TELEGRAM_PARSE_MODE", "Markdown")
        self.include_emojis = os.getenv("TELEGRAM_INCLUDE_EMOJIS", "true").lower() == "true"
        self.error_rate_limit_minutes = int(os.getenv("TELEGRAM_ERROR_RATE_LIMIT_MINUTES", "60"))

        # Validate configuration
        if self.enabled:
            if not self.bot_token or not self.chat_id:
                raise ConfigurationError(
                    "TELEGRAM_ENABLED=true but TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID missing. "
                    "Get bot token from @BotFather and chat ID from @userinfobot."
                )
            logger.info("Telegram notifications enabled")
        else:
            logger.info("Telegram notifications disabled (TELEGRAM_ENABLED=false)")
            return

        # Initialize components
        self.client = TelegramClient(bot_token=self.bot_token, timeout=5.0)
        self.formatter = MessageFormatter(include_emojis=self.include_emojis)

        # Rate limiting cache: {error_type: last_sent_timestamp}
        self.error_cache: dict[str, datetime] = {}
        self.error_cache_lock = asyncio.Lock()  # Protect concurrent cache access

        # Notification log file
        self.log_file = Path("logs/telegram-notifications.jsonl")
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def is_enabled(self) -> bool:
        """Check if Telegram notifications are enabled."""
        return self.enabled

    async def send_position_entry(self, trade_record) -> None:
        """
        Send position entry notification.

        Args:
            trade_record: TradeRecord instance from logging module

        Returns:
            None - fire-and-forget, never blocks

        Performance: <5s timeout, non-blocking
        """
        if not self.enabled or not self.notify_positions:
            return

        # Extract data from TradeRecord
        entry_data = PositionEntryData(
            symbol=trade_record.symbol,
            entry_price=trade_record.price,
            quantity=trade_record.quantity,
            total_value=trade_record.total_value,
            stop_loss=trade_record.stop_loss,
            target=trade_record.target,
            execution_mode=trade_record.execution_mode,
            strategy_name=trade_record.strategy_name,
            entry_type=trade_record.entry_type,
        )

        # Format message
        message = self.formatter.format_position_entry(entry_data)

        # Send in background (fire-and-forget)
        asyncio.create_task(
            self._send_with_logging(
                message=message,
                notification_type="position_entry"
            )
        )

    async def send_position_exit(self, trade_record) -> None:
        """
        Send position exit notification with P&L.

        Args:
            trade_record: TradeRecord instance with exit data

        Returns:
            None - fire-and-forget, never blocks

        Performance: <5s timeout, non-blocking
        """
        if not self.enabled or not self.notify_positions:
            return

        # Calculate P&L percentage
        profit_loss_pct = 0.0
        if trade_record.price != 0:
            profit_loss_pct = (
                (trade_record.profit_loss / (trade_record.price * trade_record.quantity)) * 100
            )

        # Extract data from TradeRecord
        exit_data = PositionExitData(
            symbol=trade_record.symbol,
            exit_price=trade_record.price,  # Exit price stored in price field
            exit_reasoning=trade_record.exit_reasoning or "Unknown",
            profit_loss=trade_record.profit_loss or 0,
            profit_loss_pct=profit_loss_pct,
            hold_duration_seconds=trade_record.hold_duration_seconds or 0,
            execution_mode=trade_record.execution_mode,
        )

        # Format message
        message = self.formatter.format_position_exit(exit_data)

        # Send in background (fire-and-forget)
        asyncio.create_task(
            self._send_with_logging(
                message=message,
                notification_type="position_exit"
            )
        )

    async def send_risk_alert(self, alert_event: dict) -> None:
        """
        Send urgent risk alert notification.

        Args:
            alert_event: Risk alert event dict with keys:
                - breach_type: str
                - current_value: str
                - threshold: str
                - timestamp: str (ISO 8601)

        Returns:
            None - fire-and-forget, never blocks

        Performance: <5s timeout, non-blocking
        """
        if not self.enabled or not self.notify_alerts:
            return

        # Check rate limit (thread-safe with lock)
        breach_type = alert_event.get("breach_type", "unknown")
        async with self.error_cache_lock:
            if self._is_rate_limited(breach_type):
                logger.debug(
                    f"Risk alert '{breach_type}' rate limited "
                    f"(max 1 per {self.error_rate_limit_minutes} minutes)"
                )
                return

        # Extract data
        alert_data = RiskAlertData(
            breach_type=breach_type,
            current_value=alert_event.get("current_value", "N/A"),
            threshold=alert_event.get("threshold", "N/A"),
            timestamp=alert_event.get("timestamp", datetime.utcnow().isoformat() + "Z"),
        )

        # Format message
        message = self.formatter.format_risk_alert(alert_data)

        # Send in background (fire-and-forget)
        asyncio.create_task(
            self._send_with_logging(
                message=message,
                notification_type="risk_alert"
            )
        )

        # Update rate limit cache (thread-safe with lock)
        async with self.error_cache_lock:
            self.error_cache[breach_type] = datetime.utcnow()

    def _is_rate_limited(self, error_type: str) -> bool:
        """
        Check if error notification is rate limited.

        Args:
            error_type: Error type identifier

        Returns:
            True if rate limited, False if can send
        """
        if error_type not in self.error_cache:
            return False

        last_sent = self.error_cache[error_type]
        elapsed = datetime.utcnow() - last_sent
        rate_limit_duration = timedelta(minutes=self.error_rate_limit_minutes)

        return elapsed < rate_limit_duration

    async def _send_with_logging(
        self,
        message: str,
        notification_type: str
    ) -> None:
        """
        Send message and log delivery status to JSONL file.

        Args:
            message: Formatted Telegram message
            notification_type: "position_entry" | "position_exit" | "risk_alert"

        Returns:
            None - catches all exceptions, never raises
        """
        try:
            # Send message with timeout
            response = await asyncio.wait_for(
                self.client.send_message(
                    chat_id=self.chat_id,
                    text=message,
                    parse_mode=self.parse_mode
                ),
                timeout=5.0
            )

            # Log delivery status
            log_entry = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "notification_type": notification_type,
                "delivery_status": "success" if response.success else "failed",
                "chat_id": self.chat_id,
                "message_id": response.message_id,
                "error_message": response.error_message,
                "delivery_time_ms": response.delivery_time_ms,
            }

            self._append_log(log_entry)

            if response.success:
                logger.debug(
                    f"Telegram {notification_type} notification sent "
                    f"(message_id={response.message_id}, {response.delivery_time_ms:.1f}ms)"
                )
            else:
                logger.warning(
                    f"Telegram {notification_type} notification failed: "
                    f"{response.error_message}"
                )

        except asyncio.TimeoutError:
            logger.warning(
                f"Telegram {notification_type} notification timeout (>5s)"
            )

            log_entry = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "notification_type": notification_type,
                "delivery_status": "timeout",
                "chat_id": self.chat_id,
                "error_message": "Delivery timeout (>5s)",
            }
            self._append_log(log_entry)

        except Exception as e:
            # Catch-all to ensure trading operations never blocked
            logger.error(
                f"Unexpected error in Telegram {notification_type} notification: "
                f"{type(e).__name__}: {str(e)}"
            )

            log_entry = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "notification_type": notification_type,
                "delivery_status": "error",
                "chat_id": self.chat_id,
                "error_message": f"{type(e).__name__}: {str(e)}",
            }
            self._append_log(log_entry)

    def _append_log(self, log_entry: dict) -> None:
        """
        Append log entry to JSONL file with fallback.

        Args:
            log_entry: Log entry dict

        Returns:
            None - catches all exceptions to prevent I/O errors from blocking

        Fallback: If file write fails (disk full, permission error),
                  logs entry to application logger instead
        """
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")
        except (OSError, IOError) as e:
            # Disk full, permission denied, or other I/O errors
            # Fall back to application logger
            logger.error(
                f"Failed to write notification log to JSONL file: {type(e).__name__}: {e}. "
                f"Falling back to application logger. "
                f"Notification: {log_entry.get('notification_type')} - "
                f"{log_entry.get('delivery_status')}"
            )
        except Exception as e:
            # Other unexpected errors (JSON serialization, etc)
            logger.error(
                f"Unexpected error while logging notification: {type(e).__name__}: {e}. "
                f"Notification: {log_entry.get('notification_type')}"
            )
