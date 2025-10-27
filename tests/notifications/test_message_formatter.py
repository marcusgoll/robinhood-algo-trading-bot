"""
Unit tests for MessageFormatter.

Tests:
- Markdown formatting and escaping
- Emoji insertion
- Message truncation (4096 char limit)
- Duration formatting
- P&L calculation and display

Coverage target: >90%
Task: T053 [GREEN]
"""

import pytest
from decimal import Decimal

from src.trading_bot.notifications.message_formatter import (
    MessageFormatter,
    PositionEntryData,
    PositionExitData,
    RiskAlertData,
)


class TestMessageFormatter:
    """Unit tests for MessageFormatter class."""

    def test_format_position_entry_with_emoji(self):
        """Test position entry formatting with emoji enabled."""
        formatter = MessageFormatter(include_emojis=True)

        data = PositionEntryData(
            symbol="AAPL",
            entry_price=Decimal("150.00"),
            quantity=100,
            total_value=Decimal("15000.00"),
            stop_loss=Decimal("147.00"),
            target=Decimal("156.00"),
            execution_mode="PAPER",
            strategy_name="bull-flag-breakout",
            entry_type="breakout",
        )

        message = formatter.format_position_entry(data)

        assert "📈" in message
        assert "[PAPER]" in message
        assert "AAPL" in message
        assert "$150.00" in message
        assert "100" in message  # quantity
        assert "$15,000.00" in message  # total value
        assert "$147.00" in message  # stop loss
        assert "$156.00" in message  # target

    def test_format_position_entry_without_emoji(self):
        """Test position entry formatting with emoji disabled."""
        formatter = MessageFormatter(include_emojis=False)

        data = PositionEntryData(
            symbol="TSLA",
            entry_price=Decimal("200.50"),
            quantity=50,
            total_value=Decimal("10025.00"),
            stop_loss=None,
            target=None,
            execution_mode="LIVE",
            strategy_name="manual",
            entry_type="manual",
        )

        message = formatter.format_position_entry(data)

        assert "📈" not in message
        assert "[PAPER]" not in message  # LIVE mode
        assert "TSLA" in message
        assert "$200.50" in message

    def test_format_position_exit_profit(self):
        """Test position exit formatting with profit."""
        formatter = MessageFormatter(include_emojis=True)

        data = PositionExitData(
            symbol="NVDA",
            exit_price=Decimal("500.00"),
            exit_reasoning="Take Profit",
            profit_loss=Decimal("600.00"),
            profit_loss_pct=4.0,
            hold_duration_seconds=8100,  # 2h 15m
            execution_mode="LIVE",
        )

        message = formatter.format_position_exit(data)

        assert "✅" in message  # Profit emoji
        assert "NVDA" in message
        assert "Take Profit" in message
        assert "+$600.00" in message
        assert "+4.0%" in message
        assert "2h 15m" in message

    def test_format_position_exit_loss(self):
        """Test position exit formatting with loss."""
        formatter = MessageFormatter(include_emojis=True)

        data = PositionExitData(
            symbol="META",
            exit_price=Decimal("300.00"),
            exit_reasoning="Stop Loss",
            profit_loss=Decimal("-200.00"),
            profit_loss_pct=-2.5,
            hold_duration_seconds=45,  # 45s
            execution_mode="PAPER",
        )

        message = formatter.format_position_exit(data)

        assert "❌" in message  # Loss emoji
        assert "[PAPER]" in message
        assert "META" in message
        assert "Stop Loss" in message
        assert "$-200.00" in message  # Loss formatted as $-200.00
        assert "-2.5%" in message
        assert "45s" in message

    def test_format_risk_alert(self):
        """Test risk alert formatting."""
        formatter = MessageFormatter(include_emojis=True)

        data = RiskAlertData(
            breach_type="max_daily_loss",
            current_value="$-450.00",
            threshold="$-300.00",
            timestamp="2025-10-27T14:32:15Z",
        )

        message = formatter.format_risk_alert(data)

        assert "🚨" in message
        assert "RISK ALERT" in message
        assert "Max Daily Loss" in message  # Title case
        assert "$-450.00" in message
        assert "$-300.00" in message
        assert "2025-10-27T14:32:15Z" in message

    def test_markdown_escaping(self):
        """Test Markdown special character escaping."""
        formatter = MessageFormatter()

        # Test escape_markdown method
        text = "Test *bold* _italic_ `code` [link]"
        escaped = formatter._escape_markdown(text)

        assert "\\*bold\\*" in escaped  # Asterisks escaped
        assert "\\_italic\\_" in escaped  # Underscores escaped
        assert "\\`code\\`" in escaped  # Backticks escaped
        assert "\\[link]" in escaped  # Opening bracket escaped (closing bracket OK per Telegram spec)

    def test_message_truncation(self):
        """Test message truncation at 4096 character limit."""
        formatter = MessageFormatter()

        # Create very long message (>4096 chars)
        long_text = "A" * 5000

        truncated = formatter._truncate(long_text)

        assert len(truncated) == 4096
        assert truncated.endswith("...")

    def test_message_no_truncation(self):
        """Test message not truncated if under limit."""
        formatter = MessageFormatter()

        short_text = "Short message"

        result = formatter._truncate(short_text)

        assert result == short_text
        assert len(result) < 4096

    def test_duration_formatting(self):
        """Test human-readable duration formatting."""
        formatter = MessageFormatter()

        # Test various durations
        assert formatter._format_duration(30) == "30s"
        assert formatter._format_duration(90) == "1m"
        assert formatter._format_duration(3600) == "1h"
        assert formatter._format_duration(8100) == "2h 15m"  # 2h 15m
        assert formatter._format_duration(7200) == "2h"  # Exactly 2h

    @pytest.mark.parametrize("entry_price,stop_loss,expected_pct", [
        (Decimal("100.00"), Decimal("98.00"), -2.0),
        (Decimal("150.00"), Decimal("147.00"), -2.0),
        (Decimal("50.00"), Decimal("51.00"), 2.0),
    ])
    def test_stop_loss_percentage(self, entry_price, stop_loss, expected_pct):
        """Test stop loss percentage calculation."""
        formatter = MessageFormatter()

        data = PositionEntryData(
            symbol="TEST",
            entry_price=entry_price,
            quantity=100,
            total_value=entry_price * 100,
            stop_loss=stop_loss,
            target=None,
            execution_mode="PAPER",
            strategy_name="test",
            entry_type="test",
        )

        message = formatter.format_position_entry(data)

        # Check percentage is in message
        assert f"{expected_pct:+.1f}%" in message

    def test_position_entry_with_target_no_stop_loss(self):
        """Test position entry with target but no stop loss."""
        formatter = MessageFormatter(include_emojis=True)

        data = PositionEntryData(
            symbol="GOOGL",
            entry_price=Decimal("140.00"),
            quantity=50,
            total_value=Decimal("7000.00"),
            stop_loss=None,  # No stop loss
            target=Decimal("150.00"),  # But has target
            execution_mode="LIVE",
            strategy_name="momentum",
            entry_type="breakout",
        )

        message = formatter.format_position_entry(data)

        # Verify message contains target and handles blank line correctly
        assert "Target:" in message
        assert "$150.00" in message
        assert "GOOGL" in message

    def test_position_exit_without_emoji_loss(self):
        """Test position exit loss without emoji."""
        formatter = MessageFormatter(include_emojis=False)

        data = PositionExitData(
            symbol="MSFT",
            exit_price=Decimal("350.00"),
            exit_reasoning="Stop Loss",
            profit_loss=Decimal("-250.00"),
            profit_loss_pct=-1.5,
            hold_duration_seconds=7200,  # 2h
            execution_mode="PAPER",
        )

        message = formatter.format_position_exit(data)

        # Verify no emoji when disabled
        assert "❌" not in message
        assert "✅" not in message
        assert "MSFT" in message
        assert "Stop Loss" in message
        assert "$-250.00" in message
