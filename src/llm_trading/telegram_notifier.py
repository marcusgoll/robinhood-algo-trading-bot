"""
Telegram Notifications for LLM Trading System

Sends real-time notifications for:
- Morning watchlist generation
- Trade entries/exits
- Parameter adjustments (optimizer)
- Circuit breaker triggers
- Daily summaries

Uses existing Telegram infrastructure from src/trading_bot/notifications
"""

import asyncio
import os
import sys
from datetime import datetime
from typing import Optional, Dict, List

# Add src to path to access existing telegram client
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from trading_bot.notifications.telegram_client import TelegramClient, TelegramResponse
except ImportError:
    print("Warning: Telegram client not available. Install: pip install python-telegram-bot")
    TelegramClient = None
    TelegramResponse = None


class LLMTradingNotifier:
    """
    Telegram notifier for LLM trading system.

    Sends non-blocking notifications for all trading events.
    """

    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None, enabled: bool = True):
        """
        Initialize Telegram notifier.

        Args:
            bot_token: Telegram bot token (from .env if not provided)
            chat_id: Telegram chat ID (from .env if not provided)
            enabled: Enable/disable notifications (useful for testing)
        """
        self.enabled = enabled and TelegramClient is not None

        if not self.enabled:
            print("[Telegram] Notifications disabled")
            return

        # Load from env if not provided
        if bot_token is None:
            bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if chat_id is None:
            chat_id = os.getenv('TELEGRAM_CHAT_ID')

        if not bot_token or not chat_id:
            print("[Telegram] Missing credentials. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env")
            self.enabled = False
            return

        self.bot_token = bot_token
        self.chat_id = chat_id
        self.client = TelegramClient(bot_token=bot_token, timeout=5.0)

        print(f"[Telegram] Notifier initialized (chat_id={chat_id})")

    def _send(self, message: str) -> bool:
        """Send message (blocking helper)"""
        if not self.enabled:
            return False

        try:
            # Run async send in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                response = loop.run_until_complete(
                    self.client.send_message(
                        chat_id=self.chat_id,
                        text=message,
                        parse_mode="Markdown"
                    )
                )
                return response.success
            finally:
                loop.close()
        except Exception as e:
            print(f"[Telegram] Failed to send: {e}")
            return False

    # Morning Screener Notifications

    def notify_screener_start(self, num_candidates: int):
        """Notify that morning screener is starting"""
        message = f"""
*Morning Screener Started*

Analyzing {num_candidates} candidate stocks...
Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
        self._send(message.strip())

    def notify_watchlist_generated(self, watchlist: List[Dict]):
        """Notify that watchlist has been generated"""
        if not watchlist:
            self._send("*Watchlist Generated*\n\nNo stocks selected today.")
            return

        # Build watchlist summary
        items = []
        for entry in watchlist[:10]:  # Limit to top 10 for brevity
            items.append(
                f"• *{entry['symbol']}* ({entry['confidence']}%)\n"
                f"  {entry['setup_type']} - {entry['catalyst'][:50]}..."
            )

        message = f"""
*Watchlist Generated* 📋

{len(watchlist)} stocks selected for trading:

{chr(10).join(items)}
"""

        if len(watchlist) > 10:
            message += f"\n_({len(watchlist) - 10} more stocks...)_"

        self._send(message.strip())

    # Trading Session Notifications

    def notify_session_start(self):
        """Notify that trading session has started"""
        message = f"""
*Trading Session Started* 📈

Monitoring watchlist for entry signals...
Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
        self._send(message.strip())

    def notify_trade_entry(self, symbol: str, setup: Dict, price: float, shares: int):
        """Notify that a trade was entered"""
        message = f"""
*Trade Entry* 🟢

Symbol: *{symbol}*
Setup: {setup.get('setup_type', 'Unknown')}
Entry: ${price:.2f} x {shares} shares
Value: ${price * shares:,.2f}

Target: +{setup['exit'].get('take_profit_pct', 0):.1f}%
Stop: {setup['exit'].get('stop_loss_pct', 0):.1f}%
Max Hold: {setup['exit'].get('max_hold_minutes', 0)} min

Reason: {setup.get('catalyst', 'N/A')[:100]}
"""
        self._send(message.strip())

    def notify_trade_exit(self, symbol: str, reason: str, entry_price: float, exit_price: float, pnl: float, pnl_pct: float):
        """Notify that a trade was exited"""
        emoji = "✅" if pnl > 0 else "❌"
        sign = "+" if pnl > 0 else ""

        message = f"""
*Trade Exit* {emoji}

Symbol: *{symbol}*
Reason: {reason}

Entry: ${entry_price:.2f}
Exit: ${exit_price:.2f}

P&L: {sign}${pnl:.2f} ({sign}{pnl_pct:.1f}%)
"""
        self._send(message.strip())

    def notify_circuit_breaker(self, loss_pct: float):
        """Notify that circuit breaker was triggered"""
        message = f"""
*CIRCUIT BREAKER TRIGGERED* 🚨

Daily loss exceeded threshold:
Loss: {loss_pct:.1f}%
Threshold: -10.0%

All positions closed.
Trading HALTED for safety.
"""
        self._send(message.strip())

    def notify_session_end(self, num_trades: int, daily_pnl: float):
        """Notify that trading session ended"""
        emoji = "✅" if daily_pnl >= 0 else "❌"
        sign = "+" if daily_pnl >= 0 else ""

        message = f"""
*Trading Session Ended* {emoji}

Trades: {num_trades}
Daily P&L: {sign}${daily_pnl:.2f}

Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
        self._send(message.strip())

    # Optimizer Notifications

    def notify_optimizer_start(self, autonomy_level: int):
        """Notify that evening optimizer is starting"""
        levels = {1: "Supervised", 2: "Bounded", 3: "Fully Autonomous"}

        message = f"""
*Evening Optimizer Started* 🔧

Autonomy: Level {autonomy_level} ({levels.get(autonomy_level, 'Unknown')})
Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}

Analyzing today's performance...
"""
        self._send(message.strip())

    def notify_parameter_change(self, param: str, old_value, new_value, reasoning: str, auto_applied: bool):
        """Notify that a parameter was changed"""
        status = "AUTO-APPLIED" if auto_applied else "PENDING APPROVAL"
        emoji = "✅" if auto_applied else "⏳"

        message = f"""
*Parameter Adjustment* {emoji}

Status: {status}

Parameter: `{param}`
Old: {old_value}
New: {new_value}

Reasoning: {reasoning[:200]}
"""
        self._send(message.strip())

    def notify_optimization_summary(self, num_proposals: int, num_applied: int, num_rejected: int):
        """Notify optimization summary"""
        message = f"""
*Optimization Complete* 📊

Proposals: {num_proposals}
Applied: {num_applied}
Rejected: {num_rejected}

Strategy parameters updated.
"""
        self._send(message.strip())

    # Error Notifications

    def notify_error(self, component: str, error_msg: str):
        """Notify that an error occurred"""
        message = f"""
*Error* ⚠️

Component: {component}
Error: {error_msg[:300]}

Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
        self._send(message.strip())

    # Daily Summary

    def notify_daily_summary(self, date: str, metrics: Dict):
        """Send end-of-day summary"""
        message = f"""
*Daily Summary* 📅

Date: {date}

*Trading:*
• Trades: {metrics.get('num_trades', 0)}
• Win Rate: {metrics.get('win_rate', 0):.1f}%
• P&L: ${metrics.get('daily_pnl', 0):.2f}

*Performance:*
• Avg Win: ${metrics.get('avg_win', 0):.2f}
• Avg Loss: ${metrics.get('avg_loss', 0):.2f}
• Profit Factor: {metrics.get('profit_factor', 0):.2f}

*Parameters Adjusted:*
{metrics.get('params_changed', 0)} changes applied
"""
        self._send(message.strip())

    def send_test_message(self):
        """Send test message to verify setup"""
        message = """
*LLM Trading System*

Telegram notifications are working! ✅

You will receive updates for:
• Morning watchlist generation
• Trade entries/exits
• Parameter adjustments
• Errors and circuit breakers
• Daily summaries
"""
        success = self._send(message.strip())
        if success:
            print("[Telegram] Test message sent successfully!")
        else:
            print("[Telegram] Test message failed to send")
        return success


# Convenience function for easy initialization
def create_notifier(enabled: bool = True) -> LLMTradingNotifier:
    """
    Create notifier from environment variables.

    Args:
        enabled: Enable/disable notifications

    Returns:
        LLMTradingNotifier instance

    Usage:
        notifier = create_notifier()
        notifier.notify_watchlist_generated(watchlist)
    """
    return LLMTradingNotifier(enabled=enabled)


if __name__ == "__main__":
    # Test notifications
    from dotenv import load_dotenv
    load_dotenv()

    print("Testing Telegram notifications...")

    notifier = create_notifier()

    if notifier.enabled:
        print("\nSending test message...")
        notifier.send_test_message()

        print("\nTest notifications:")
        notifier.notify_screener_start(20)

        # Mock watchlist
        mock_watchlist = [
            {
                'symbol': 'NVDA',
                'confidence': 75,
                'setup_type': 'oversold_bounce',
                'catalyst': 'RSI 28 + touching lower BB + high volume spike'
            },
            {
                'symbol': 'TSLA',
                'confidence': 68,
                'setup_type': 'breakout',
                'catalyst': 'Breaking above resistance with strong volume'
            }
        ]

        notifier.notify_watchlist_generated(mock_watchlist)

        print("\nAll test notifications sent!")
    else:
        print("\nTelegram not configured. Add to .env:")
        print("TELEGRAM_BOT_TOKEN=your_bot_token")
        print("TELEGRAM_CHAT_ID=your_chat_id")
