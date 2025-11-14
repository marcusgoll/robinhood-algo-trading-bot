"""Response formatter for Telegram command handlers.

Formats bot state data into mobile-optimized Telegram messages with
markdown and emoji for visual hierarchy.

Constitution v1.0.0:
- §Code_Quality: Type hints required
- §Testing_Requirements: Testable pure functions (no side effects)
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class ResponseFormatter:
    """
    Formats data into Telegram-friendly markdown messages.

    Pattern: Pure functions (no state, no side effects)
    Mobile-first: Concise, scannable, emoji for visual hierarchy
    Markdown: Bold, code blocks, lists for structure
    """

    @staticmethod
    def format_status(state: Dict[str, Any]) -> str:
        """
        Format bot status message.

        Args:
            state: Bot state dict from API (mode, positions, balance, etc.)

        Returns:
            str: Formatted status message with markdown

        Example:
            >>> state = {"mode": "running", "positions": [...], "balance": 10500.00}
            >>> formatter = ResponseFormatter()
            >>> print(formatter.format_status(state))
            📊 **Bot Status**

            **Mode**: 🟢 Running
            **Positions**: 2 open (+$125.50 / +2.3%)
            ...
        """
        # Determine mode from config_summary.paper_trading
        config_summary = state.get("config_summary", {})
        paper_trading = config_summary.get("paper_trading", True)
        mode = "Paper Trading" if paper_trading else "Live Trading"
        mode_emoji = "📝" if paper_trading else "💰"

        # Calculate aggregate position P/L
        positions = state.get("positions", [])
        position_count = len(positions)

        if position_count > 0:
            total_pnl = sum(float(p.get("unrealized_pl", 0.0)) for p in positions)
            # Calculate weighted average percentage
            avg_pnl_pct = sum(float(p.get("unrealized_pl_pct", 0.0)) for p in positions) / position_count

            pnl_sign = "+" if total_pnl >= 0 else ""
            positions_line = f"{position_count} open ({pnl_sign}${total_pnl:.2f} / {pnl_sign}{avg_pnl_pct:.1f}%)"
        else:
            positions_line = "0 open"

        # Account info from nested account object
        account = state.get("account", {})
        balance = float(account.get("account_balance", 0.0))
        buying_power = float(account.get("buying_power", 0.0))

        # Last signal
        last_signal = state.get("last_signal_timestamp")
        if last_signal:
            last_signal_display = ResponseFormatter._format_relative_time(last_signal)
        else:
            last_signal_display = "None"

        # Circuit breakers
        circuit_breakers = state.get("circuit_breakers", [])
        if circuit_breakers:
            cb_display = ", ".join(circuit_breakers)
        else:
            cb_display = "None active"

        message = f"""📊 **Bot Status**

**Mode**: {mode_emoji} {mode}
**Positions**: {positions_line}
**Account**: ${balance:,.2f} (BP: ${buying_power:,.2f})
**Last Signal**: {last_signal_display}
**Circuit Breakers**: {cb_display}

_Updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC_"""

        return message

    @staticmethod
    def format_positions(positions: List[Dict[str, Any]]) -> str:
        """
        Format open positions list.

        Args:
            positions: List of position dicts from API

        Returns:
            str: Formatted positions message

        Example:
            💼 **Open Positions** (2)

            **AAPL** 🟢
            Entry: $150.00 | Current: $152.50
            P/L: +$250.00 (+1.67%)
            Size: 100 shares | Hold: 2h 15m
        """
        if not positions:
            return "💼 **Open Positions** (0)\n\n_No open positions_"

        message_lines = [f"💼 **Open Positions** ({len(positions)})", ""]

        total_pnl = 0.0
        total_pnl_pct_sum = 0.0

        for position in positions:
            symbol = position.get("symbol", "UNKNOWN")
            entry_price = float(position.get("entry_price", 0.0))
            current_price = float(position.get("current_price", 0.0))
            unrealized_pnl = float(position.get("unrealized_pl", 0.0))
            pnl_pct = float(position.get("unrealized_pl_pct", 0.0))
            quantity = position.get("quantity", 0)

            # Calculate hold duration from last_updated if available
            last_updated = position.get("last_updated")
            if last_updated:
                try:
                    updated_time = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
                    now = datetime.now(timezone.utc)
                    hold_duration = int((now - updated_time).total_seconds() / 60)
                except:
                    hold_duration = 0
            else:
                hold_duration = 0

            # P/L emoji
            if unrealized_pnl > 0:
                pnl_emoji = "🟢"
                pnl_sign = "+"
            elif unrealized_pnl < 0:
                pnl_emoji = "🔴"
                pnl_sign = "-"
            else:
                pnl_emoji = "⚪"
                pnl_sign = ""

            # Format hold duration
            hold_display = ResponseFormatter._format_duration(hold_duration)

            position_block = f"""**{symbol}** {pnl_emoji}
Entry: ${entry_price:.2f} | Current: ${current_price:.2f}
P/L: {pnl_sign}${abs(unrealized_pnl):.2f} ({pnl_sign}{abs(pnl_pct):.2f}%)
Size: {quantity} shares | Hold: {hold_display}"""

            message_lines.append(position_block)
            message_lines.append("")  # Blank line between positions

            total_pnl += unrealized_pnl
            total_pnl_pct_sum += pnl_pct

        # Aggregate totals
        avg_pnl_pct = total_pnl_pct_sum / len(positions) if positions else 0.0
        pnl_sign = "+" if total_pnl > 0 else ("-" if total_pnl < 0 else "")
        message_lines.append(f"**Total P/L**: {pnl_sign}${abs(total_pnl):.2f} ({pnl_sign}{abs(avg_pnl_pct):.2f}%)")
        message_lines.append("")
        message_lines.append(f"_Updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC_")

        return "\n".join(message_lines)

    @staticmethod
    def format_performance(metrics: Dict[str, Any]) -> str:
        """
        Format performance metrics.

        Args:
            metrics: Performance dict from API (win_rate, total_pnl, etc.)

        Returns:
            str: Formatted performance message

        Example:
            📈 **Performance Metrics**

            **Win Rate**: 65.2% (30W / 16L)
            **Total P/L**: +$2,450.00 (+24.5%)
            ...
        """
        win_rate = metrics.get("win_rate", 0.0) * 100
        total_wins = metrics.get("total_wins", 0)
        total_losses = metrics.get("total_losses", 0)
        total_pnl = metrics.get("total_pnl", 0.0)
        total_pnl_pct = metrics.get("total_pnl_pct", 0.0)
        current_streak = metrics.get("current_streak", 0)
        streak_type = metrics.get("streak_type", "wins")
        best_trade = metrics.get("best_trade", 0.0)
        best_symbol = metrics.get("best_trade_symbol", "N/A")
        worst_trade = metrics.get("worst_trade", 0.0)
        worst_symbol = metrics.get("worst_trade_symbol", "N/A")

        # Streak emoji
        if streak_type == "wins" and current_streak > 0:
            streak_display = f"🔥 {current_streak} wins"
        elif streak_type == "losses" and current_streak > 0:
            streak_display = f"❄️ {current_streak} losses"
        else:
            streak_display = "None"

        pnl_sign = "+" if total_pnl > 0 else ("-" if total_pnl < 0 else "")
        pnl_pct_sign = "+" if total_pnl_pct > 0 else ("-" if total_pnl_pct < 0 else "")

        message = f"""📈 **Performance Metrics**

**Win Rate**: {win_rate:.1f}% ({total_wins}W / {total_losses}L)
**Total P/L**: {pnl_sign}${abs(total_pnl):,.2f} ({pnl_pct_sign}{abs(total_pnl_pct):.1f}%)
**Streak**: {streak_display}
**Best Trade**: +${best_trade:,.2f} ({best_symbol})
**Worst Trade**: -${abs(worst_trade):,.2f} ({worst_symbol})

_Last {total_wins + total_losses} trades | Updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC_"""

        return message

    @staticmethod
    def format_help() -> str:
        """
        Format help message with command list.

        Returns:
            str: Formatted help message
        """
        return """🤖 **Available Commands**

**/start** - Welcome message
**/status** - Current bot status
**/pause** - Pause trading (keeps positions)
**/resume** - Resume trading
**/positions** - List open positions
**/performance** - Show win rate and P/L
**/help** - This message

**Authorization**: ✅ Authorized

_Rate limit: 1 command per 5 seconds_"""

    @staticmethod
    def format_welcome(authorized: bool) -> str:
        """
        Format welcome message for /start command.

        Args:
            authorized: Whether user is authorized

        Returns:
            str: Formatted welcome message
        """
        auth_status = "✅ Authorized" if authorized else "❌ Unauthorized"

        if authorized:
            capabilities = """You can use the following commands:
• **/status** - Check bot status
• **/pause** / **/resume** - Control trading
• **/positions** - View open positions
• **/performance** - View performance metrics
• **/help** - Full command list"""
        else:
            capabilities = "⚠️ You are not authorized to control this bot. Contact the administrator to request access."

        return f"""🤖 **Trading Bot Controller**

Welcome to the Robinhood Trading Bot Telegram interface!

**Authorization Status**: {auth_status}

{capabilities}

_For help, use /help_"""

    @staticmethod
    def format_error(error_type: str, details: Optional[str] = None) -> str:
        """
        Format error message.

        Args:
            error_type: Type of error (unauthorized, rate_limit, api_error, etc.)
            details: Optional additional details

        Returns:
            str: Formatted error message
        """
        if error_type == "unauthorized":
            return "❌ **Unauthorized Access**\n\nYou are not authorized to use this bot. Contact the administrator for access."

        if error_type == "rate_limit":
            return f"⏱️ **Rate Limit**\n\nPlease wait {details or '5 seconds'} before sending another command."

        if error_type == "api_error":
            return f"🔧 **API Error**\n\nCould not connect to bot API. Please try again later.\n\n_Details: {details or 'Connection failed'}_"

        if error_type == "unknown_command":
            return "❓ **Unknown Command**\n\nCommand not recognized. Use /help to see available commands."

        # Generic error
        return f"❌ **Error**\n\n{details or 'An unexpected error occurred. Please try again.'}"

    @staticmethod
    def _get_mode_emoji(mode: str) -> str:
        """Get emoji for bot mode."""
        mode_lower = mode.lower()
        if mode_lower == "running":
            return "🟢"
        elif mode_lower == "paused":
            return "⏸️"
        elif mode_lower == "error":
            return "🔴"
        else:
            return "⚪"

    @staticmethod
    def _format_relative_time(timestamp_str: str) -> str:
        """Format timestamp as relative time (e.g., '5 minutes ago')."""
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            delta = now - timestamp

            minutes = int(delta.total_seconds() / 60)
            if minutes < 1:
                return "Just now"
            elif minutes < 60:
                return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
            else:
                hours = minutes // 60
                return f"{hours} hour{'s' if hours != 1 else ''} ago"
        except:
            return timestamp_str

    @staticmethod
    def _format_duration(minutes: int) -> str:
        """Format duration in minutes as human-readable (e.g., '2h 15m')."""
        if minutes < 60:
            return f"{minutes}m"
        else:
            hours = minutes // 60
            remaining_minutes = minutes % 60
            return f"{hours}h {remaining_minutes}m"
