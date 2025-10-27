"""
Telegram Message Formatter

Formats trading bot data into Telegram-compatible Markdown messages.

Features:
- Position entry/exit formatting
- Risk alert formatting with urgent styling
- Emoji support for visual clarity
- Markdown escaping for special characters
- 4096 character truncation (Telegram limit)

Constitution v1.0.0:
- §User_Experience: Clear, actionable notifications
- §Data_Integrity: Accurate formatting of trade data

Tasks: T011 [GREEN] - Implement MessageFormatter
"""

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass
class PositionEntryData:
    """Data for position entry notification."""

    symbol: str
    entry_price: Decimal
    quantity: int
    total_value: Decimal
    stop_loss: Optional[Decimal]
    target: Optional[Decimal]
    execution_mode: str  # "PAPER" | "LIVE"
    strategy_name: str
    entry_type: str


@dataclass
class PositionExitData:
    """Data for position exit notification."""

    symbol: str
    exit_price: Decimal
    exit_reasoning: str
    profit_loss: Decimal
    profit_loss_pct: float
    hold_duration_seconds: int
    execution_mode: str  # "PAPER" | "LIVE"


@dataclass
class RiskAlertData:
    """Data for risk alert notification."""

    breach_type: str  # "max_daily_loss" | "consecutive_losses" | etc
    current_value: str
    threshold: str
    timestamp: str


class MessageFormatter:
    """
    Format trading data into Telegram Markdown messages.

    Usage:
        formatter = MessageFormatter(include_emojis=True)
        message = formatter.format_position_entry(entry_data)
        # Returns: "📈 *Position Opened: AAPL*\nPrice: $150.00\n..."

    Performance: <10ms formatting latency
    """

    # Telegram character limit
    MAX_MESSAGE_LENGTH = 4096

    # Emoji configuration
    EMOJI = {
        "position_entry": "📈",
        "position_exit_profit": "✅",
        "position_exit_loss": "❌",
        "risk_alert": "🚨",
        "paper_trading": "📝",
    }

    def __init__(self, include_emojis: bool = True):
        """
        Initialize message formatter.

        Args:
            include_emojis: Include emoji in messages for visual clarity
        """
        self.include_emojis = include_emojis

    def format_position_entry(self, data: PositionEntryData) -> str:
        """
        Format position entry notification.

        Args:
            data: Position entry data from TradeRecord

        Returns:
            Telegram Markdown formatted message

        Example output:
            📈 *Position Opened: AAPL*
            [PAPER] bull-flag-breakout (breakout entry)

            Price: $150.00
            Shares: 100
            Total: $15,000.00

            Stop Loss: $147.00 (-2.0%)
            Target: $156.00 (+4.0%)
        """
        emoji = self.EMOJI["position_entry"] if self.include_emojis else ""
        paper_prefix = "[PAPER] " if data.execution_mode == "PAPER" else ""

        # Calculate stop loss and target percentages
        stop_loss_pct = ""
        if data.stop_loss:
            pct = ((data.stop_loss - data.entry_price) / data.entry_price) * 100
            stop_loss_pct = f" ({pct:+.1f}%)"

        target_pct = ""
        if data.target:
            pct = ((data.target - data.entry_price) / data.entry_price) * 100
            target_pct = f" ({pct:+.1f}%)"

        # Build message
        lines = [
            f"{emoji} *Position Opened: {self._escape_markdown(data.symbol)}*",
            f"{paper_prefix}{data.strategy_name} ({data.entry_type} entry)",
            "",
            f"Price: ${data.entry_price:.2f}",
            f"Shares: {data.quantity:,}",
            f"Total: ${data.total_value:,.2f}",
        ]

        if data.stop_loss:
            lines.append("")
            lines.append(f"Stop Loss: ${data.stop_loss:.2f}{stop_loss_pct}")

        if data.target:
            if not data.stop_loss:
                lines.append("")
            lines.append(f"Target: ${data.target:.2f}{target_pct}")

        message = "\n".join(lines)
        return self._truncate(message)

    def format_position_exit(self, data: PositionExitData) -> str:
        """
        Format position exit notification with P&L.

        Args:
            data: Position exit data from TradeRecord

        Returns:
            Telegram Markdown formatted message

        Example output:
            ✅ *Position Closed: AAPL*
            [PAPER] Exit Reason: Take Profit

            P&L: +$600.00 (+4.0%)
            Duration: 2h 15m
        """
        # Choose emoji based on profit/loss
        if data.profit_loss > 0:
            emoji = self.EMOJI["position_exit_profit"]
        else:
            emoji = self.EMOJI["position_exit_loss"]

        if not self.include_emojis:
            emoji = ""

        paper_prefix = "[PAPER] " if data.execution_mode == "PAPER" else ""

        # Format duration (human-readable)
        duration_str = self._format_duration(data.hold_duration_seconds)

        # Format P&L with sign
        pnl_sign = "+" if data.profit_loss > 0 else ""
        pnl_pct_sign = "+" if data.profit_loss_pct > 0 else ""

        # Build message
        lines = [
            f"{emoji} *Position Closed: {self._escape_markdown(data.symbol)}*",
            f"{paper_prefix}Exit Reason: {data.exit_reasoning}",
            "",
            f"P&L: {pnl_sign}${data.profit_loss:.2f} ({pnl_pct_sign}{data.profit_loss_pct:.1f}%)",
            f"Duration: {duration_str}",
        ]

        message = "\n".join(lines)
        return self._truncate(message)

    def format_risk_alert(self, data: RiskAlertData) -> str:
        """
        Format urgent risk alert notification.

        Args:
            data: Risk alert event data

        Returns:
            Telegram Markdown formatted message

        Example output:
            🚨 *RISK ALERT: Max Daily Loss*

            Current: `$-450.00`
            Threshold: `$-300.00`
            Time: 2025-10-27 14:32:15 UTC
        """
        emoji = self.EMOJI["risk_alert"] if self.include_emojis else ""

        # Format breach type (convert snake_case to Title Case)
        breach_display = data.breach_type.replace("_", " ").title()

        # Build message with bold and code formatting
        lines = [
            f"{emoji} *RISK ALERT: {breach_display}*",
            "",
            f"Current: `{self._escape_markdown(data.current_value)}`",
            f"Threshold: `{self._escape_markdown(data.threshold)}`",
            f"Time: {data.timestamp}",
        ]

        message = "\n".join(lines)
        return self._truncate(message)

    def _format_duration(self, seconds: int) -> str:
        """
        Convert seconds to human-readable duration.

        Args:
            seconds: Duration in seconds

        Returns:
            Formatted duration string (e.g., "2h 15m", "45m", "30s")
        """
        if seconds < 60:
            return f"{seconds}s"

        minutes = seconds // 60
        if minutes < 60:
            return f"{minutes}m"

        hours = minutes // 60
        remaining_minutes = minutes % 60

        if remaining_minutes == 0:
            return f"{hours}h"

        return f"{hours}h {remaining_minutes}m"

    def _escape_markdown(self, text: str) -> str:
        """
        Escape Telegram Markdown special characters.

        Telegram Markdown special characters: * _ ` [
        See: https://core.telegram.org/bots/api#markdown-style

        Args:
            text: Raw text to escape

        Returns:
            Escaped text safe for Telegram Markdown
        """
        # Escape special characters
        special_chars = ["*", "_", "`", "["]
        escaped_text = text

        for char in special_chars:
            escaped_text = escaped_text.replace(char, f"\\{char}")

        return escaped_text

    def _truncate(self, message: str) -> str:
        """
        Truncate message to Telegram's 4096 character limit.

        Args:
            message: Raw message text

        Returns:
            Truncated message with "..." suffix if exceeded limit
        """
        if len(message) <= self.MAX_MESSAGE_LENGTH:
            return message

        # Truncate to 4093 chars and add "..." suffix
        truncated = message[:4093] + "..."
        return truncated
