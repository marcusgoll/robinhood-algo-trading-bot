"""Unit tests for ResponseFormatter."""

from datetime import datetime, timezone, timedelta

import pytest

from trading_bot.telegram.response_formatter import ResponseFormatter


def test_format_status_running_with_positions():
    """Test status formatting when bot is running with open positions."""
    # Arrange
    state = {
        "mode": "running",
        "positions": [
            {"unrealized_pnl": 250.0, "current_value": 15000.0},
            {"unrealized_pnl": -100.0, "current_value": 5000.0},
        ],
        "balance": 10500.00,
        "buying_power": 8200.00,
        "last_signal_timestamp": (
            datetime.now(timezone.utc) - timedelta(minutes=5)
        ).isoformat(),
        "circuit_breakers": [],
    }

    # Act
    result = ResponseFormatter.format_status(state)

    # Assert
    assert "📊 **Bot Status**" in result
    assert "🟢 Running" in result
    assert "2 open" in result
    assert "+$150.00" in result  # 250 - 100
    assert "$10,500.00" in result
    assert "BP: $8,200.00" in result
    assert "5 minute" in result
    assert "None active" in result


def test_format_status_paused_no_positions():
    """Test status formatting when bot is paused with no positions."""
    # Arrange
    state = {
        "mode": "paused",
        "positions": [],
        "balance": 10000.00,
        "buying_power": 10000.00,
        "last_signal_timestamp": None,
        "circuit_breakers": ["daily_loss_limit"],
    }

    # Act
    result = ResponseFormatter.format_status(state)

    # Assert
    assert "⏸️ Paused" in result
    assert "0 open" in result
    assert "$10,000.00" in result
    assert "None" in result  # Last signal
    assert "daily_loss_limit" in result


def test_format_positions_empty():
    """Test positions formatting with no open positions."""
    # Act
    result = ResponseFormatter.format_positions([])

    # Assert
    assert "💼 **Open Positions** (0)" in result
    assert "_No open positions_" in result


def test_format_positions_with_profit():
    """Test positions formatting with profitable position."""
    # Arrange
    positions = [
        {
            "symbol": "AAPL",
            "entry_price": 150.00,
            "current_price": 152.50,
            "unrealized_pnl": 250.00,
            "unrealized_pnl_pct": 1.67,
            "quantity": 100,
            "hold_duration_minutes": 135,  # 2h 15m
        }
    ]

    # Act
    result = ResponseFormatter.format_positions(positions)

    # Assert
    assert "💼 **Open Positions** (1)" in result
    assert "**AAPL** 🟢" in result
    assert "Entry: $150.00" in result
    assert "Current: $152.50" in result
    assert "+$250.00 (+1.67%)" in result
    assert "100 shares" in result
    assert "2h 15m" in result
    assert "**Total P/L**: +$250.00" in result


def test_format_positions_with_loss():
    """Test positions formatting with losing position."""
    # Arrange
    positions = [
        {
            "symbol": "MSFT",
            "entry_price": 350.00,
            "current_price": 348.00,
            "unrealized_pnl": -100.00,
            "unrealized_pnl_pct": -0.57,
            "quantity": 50,
            "hold_duration_minutes": 45,
        }
    ]

    # Act
    result = ResponseFormatter.format_positions(positions)

    # Assert
    assert "**MSFT** 🔴" in result
    assert "-$100.00 (-0.57%)" in result
    assert "45m" in result


def test_format_positions_multiple():
    """Test positions formatting with multiple positions."""
    # Arrange
    positions = [
        {
            "symbol": "AAPL",
            "entry_price": 150.00,
            "current_price": 152.50,
            "unrealized_pnl": 250.00,
            "unrealized_pnl_pct": 1.67,
            "quantity": 100,
            "hold_duration_minutes": 135,
        },
        {
            "symbol": "MSFT",
            "entry_price": 350.00,
            "current_price": 348.00,
            "unrealized_pnl": -100.00,
            "unrealized_pnl_pct": -0.57,
            "quantity": 50,
            "hold_duration_minutes": 45,
        },
    ]

    # Act
    result = ResponseFormatter.format_positions(positions)

    # Assert
    assert "💼 **Open Positions** (2)" in result
    assert "AAPL" in result
    assert "MSFT" in result
    assert "**Total P/L**: +$150.00" in result  # 250 - 100


def test_format_performance_positive():
    """Test performance formatting with positive metrics."""
    # Arrange
    metrics = {
        "win_rate": 0.652,
        "total_wins": 30,
        "total_losses": 16,
        "total_pnl": 2450.00,
        "total_pnl_pct": 24.5,
        "current_streak": 3,
        "streak_type": "wins",
        "best_trade": 850.00,
        "best_trade_symbol": "NVDA",
        "worst_trade": -320.00,
        "worst_trade_symbol": "TSLA",
    }

    # Act
    result = ResponseFormatter.format_performance(metrics)

    # Assert
    assert "📈 **Performance Metrics**" in result
    assert "65.2%" in result
    assert "30W / 16L" in result
    assert "+$2,450.00" in result
    assert "+24.5%" in result
    assert "🔥 3 wins" in result
    assert "+$850.00 (NVDA)" in result
    assert "-$320.00 (TSLA)" in result


def test_format_performance_losing_streak():
    """Test performance formatting with losing streak."""
    # Arrange
    metrics = {
        "win_rate": 0.40,
        "total_wins": 8,
        "total_losses": 12,
        "total_pnl": -1200.00,
        "total_pnl_pct": -12.0,
        "current_streak": 2,
        "streak_type": "losses",
        "best_trade": 500.00,
        "best_trade_symbol": "AAPL",
        "worst_trade": -800.00,
        "worst_trade_symbol": "AMZN",
    }

    # Act
    result = ResponseFormatter.format_performance(metrics)

    # Assert
    assert "40.0%" in result
    assert "8W / 12L" in result
    assert "-$1,200.00" in result
    assert "-12.0%" in result
    assert "❄️ 2 losses" in result


def test_format_help():
    """Test help message formatting."""
    # Act
    result = ResponseFormatter.format_help()

    # Assert
    assert "🤖 **Available Commands**" in result
    assert "/start" in result
    assert "/status" in result
    assert "/pause" in result
    assert "/resume" in result
    assert "/positions" in result
    assert "/performance" in result
    assert "/help" in result
    assert "✅ Authorized" in result
    assert "1 command per 5 seconds" in result


def test_format_welcome_authorized():
    """Test welcome message for authorized user."""
    # Act
    result = ResponseFormatter.format_welcome(authorized=True)

    # Assert
    assert "🤖 **Trading Bot Controller**" in result
    assert "✅ Authorized" in result
    assert "/status" in result
    assert "/pause" in result
    assert "/help" in result


def test_format_welcome_unauthorized():
    """Test welcome message for unauthorized user."""
    # Act
    result = ResponseFormatter.format_welcome(authorized=False)

    # Assert
    assert "🤖 **Trading Bot Controller**" in result
    assert "❌ Unauthorized" in result
    assert "not authorized" in result
    assert "Contact the administrator" in result


def test_format_error_unauthorized():
    """Test unauthorized error formatting."""
    # Act
    result = ResponseFormatter.format_error("unauthorized")

    # Assert
    assert "❌ **Unauthorized Access**" in result
    assert "not authorized" in result


def test_format_error_rate_limit():
    """Test rate limit error formatting."""
    # Act
    result = ResponseFormatter.format_error("rate_limit", "3 seconds")

    # Assert
    assert "⏱️ **Rate Limit**" in result
    assert "3 seconds" in result


def test_format_error_api_error():
    """Test API error formatting."""
    # Act
    result = ResponseFormatter.format_error("api_error", "Connection timeout")

    # Assert
    assert "🔧 **API Error**" in result
    assert "Connection timeout" in result


def test_format_error_unknown_command():
    """Test unknown command error formatting."""
    # Act
    result = ResponseFormatter.format_error("unknown_command")

    # Assert
    assert "❓ **Unknown Command**" in result
    assert "/help" in result


def test_format_error_generic():
    """Test generic error formatting."""
    # Act
    result = ResponseFormatter.format_error("other", "Something went wrong")

    # Assert
    assert "❌ **Error**" in result
    assert "Something went wrong" in result


def test_get_mode_emoji():
    """Test mode emoji selection."""
    assert ResponseFormatter._get_mode_emoji("running") == "🟢"
    assert ResponseFormatter._get_mode_emoji("paused") == "⏸️"
    assert ResponseFormatter._get_mode_emoji("error") == "🔴"
    assert ResponseFormatter._get_mode_emoji("unknown") == "⚪"


def test_format_relative_time_just_now():
    """Test relative time formatting for recent timestamps."""
    # Arrange
    now = datetime.now(timezone.utc)
    timestamp_str = now.isoformat()

    # Act
    result = ResponseFormatter._format_relative_time(timestamp_str)

    # Assert
    assert result == "Just now"


def test_format_relative_time_minutes():
    """Test relative time formatting for minutes ago."""
    # Arrange
    past = datetime.now(timezone.utc) - timedelta(minutes=15)
    timestamp_str = past.isoformat()

    # Act
    result = ResponseFormatter._format_relative_time(timestamp_str)

    # Assert
    assert "15 minutes ago" in result


def test_format_relative_time_hours():
    """Test relative time formatting for hours ago."""
    # Arrange
    past = datetime.now(timezone.utc) - timedelta(hours=2, minutes=30)
    timestamp_str = past.isoformat()

    # Act
    result = ResponseFormatter._format_relative_time(timestamp_str)

    # Assert
    assert "2 hours ago" in result


def test_format_duration():
    """Test duration formatting."""
    assert ResponseFormatter._format_duration(45) == "45m"
    assert ResponseFormatter._format_duration(60) == "1h 0m"
    assert ResponseFormatter._format_duration(135) == "2h 15m"
    assert ResponseFormatter._format_duration(0) == "0m"
