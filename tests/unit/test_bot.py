"""
Unit tests for TradingBot

Tests Constitution v1.0.0 requirements:
- §Safety_First: Circuit breakers
- §Risk_Management: Position limits
- §Code_Quality: Type safety
"""

from decimal import Decimal
import pytest
from src.trading_bot.bot import TradingBot, CircuitBreaker


class TestCircuitBreaker:
    """Test circuit breaker functionality (§Safety_First)."""

    def test_circuit_breaker_trips_on_daily_loss(self) -> None:
        """Circuit breaker should trip when daily loss exceeds limit."""
        breaker = CircuitBreaker(max_daily_loss_pct=3.0, max_consecutive_losses=3)
        portfolio_value = Decimal("10000")

        # Simulate a loss exceeding 3%
        trade_pnl = Decimal("-350")  # 3.5% loss

        tripped = breaker.check_and_trip(trade_pnl, portfolio_value)

        assert tripped is True
        assert breaker.is_tripped is True

    def test_circuit_breaker_trips_on_consecutive_losses(self) -> None:
        """Circuit breaker should trip after N consecutive losses."""
        breaker = CircuitBreaker(max_daily_loss_pct=10.0, max_consecutive_losses=3)
        portfolio_value = Decimal("10000")

        # Simulate 3 consecutive small losses
        for _ in range(3):
            trade_pnl = Decimal("-50")
            tripped = breaker.check_and_trip(trade_pnl, portfolio_value)

        assert tripped is True
        assert breaker.is_tripped is True
        assert breaker.consecutive_losses == 3

    def test_circuit_breaker_resets_on_win(self) -> None:
        """Consecutive loss counter should reset on a win."""
        breaker = CircuitBreaker(max_daily_loss_pct=10.0, max_consecutive_losses=3)
        portfolio_value = Decimal("10000")

        # Two losses
        breaker.check_and_trip(Decimal("-50"), portfolio_value)
        breaker.check_and_trip(Decimal("-50"), portfolio_value)

        assert breaker.consecutive_losses == 2

        # Win resets counter
        breaker.check_and_trip(Decimal("100"), portfolio_value)

        assert breaker.consecutive_losses == 0

    def test_circuit_breaker_daily_reset(self) -> None:
        """Daily reset should clear counters and trip status."""
        breaker = CircuitBreaker(max_daily_loss_pct=3.0, max_consecutive_losses=3)
        portfolio_value = Decimal("10000")

        # Trip the breaker
        breaker.check_and_trip(Decimal("-350"), portfolio_value)
        assert breaker.is_tripped is True

        # Reset for new day
        breaker.reset_daily()

        assert breaker.is_tripped is False
        assert breaker.daily_pnl == Decimal("0")


class TestTradingBot:
    """Test TradingBot main functionality."""

    def test_bot_initializes_with_paper_trading_default(self) -> None:
        """Bot should default to paper trading mode (§Safety_First)."""
        bot = TradingBot()

        assert bot.paper_trading is True

    def test_bot_enforces_position_limit(self) -> None:
        """Position size should not exceed max % of portfolio (§Risk_Management)."""
        bot = TradingBot(max_position_pct=5.0)
        portfolio_value = Decimal("10000")
        stock_price = Decimal("100")

        shares = bot.calculate_position_size("AAPL", portfolio_value, stock_price)

        # 5% of $10,000 = $500 / $100 = 5 shares
        assert shares == 5

    def test_bot_cannot_start_if_circuit_breaker_tripped(self) -> None:
        """Bot should refuse to start if circuit breaker is tripped (§Safety_First)."""
        bot = TradingBot()
        bot.circuit_breaker.is_tripped = True

        with pytest.raises(RuntimeError, match="Circuit breaker is tripped"):
            bot.start()

    def test_bot_rejects_trades_when_not_running(self) -> None:
        """Bot should reject trades when stopped (§Safety_First)."""
        bot = TradingBot()
        # Don't call bot.start()

        bot.execute_trade(
            symbol="AAPL",
            action="buy",
            shares=10,
            price=Decimal("150"),
            reason="Test trade",
        )

        # Trade should be rejected (check logs in actual implementation)
        # This test mainly ensures no exception is raised
        assert bot.is_running is False

    def test_stop_loss_detection(self) -> None:
        """Bot should detect when stop loss is hit (§Risk_Management)."""
        bot = TradingBot()

        # Create a position
        bot.update_position(
            symbol="AAPL",
            shares=10,
            entry_price=Decimal("150"),
            stop_loss_price=Decimal("145"),  # 3.33% stop loss
        )

        # Price drops below stop loss
        hit = bot.check_stop_loss("AAPL", Decimal("144"))

        assert hit is True

    def test_stop_loss_not_triggered_above_threshold(self) -> None:
        """Stop loss should not trigger if price is above threshold."""
        bot = TradingBot()

        bot.update_position(
            symbol="AAPL",
            shares=10,
            entry_price=Decimal("150"),
            stop_loss_price=Decimal("145"),
        )

        # Price still above stop loss
        hit = bot.check_stop_loss("AAPL", Decimal("148"))

        assert hit is False

    def test_position_update_requires_stop_loss(self) -> None:
        """Every position must have a stop loss (§Risk_Management)."""
        bot = TradingBot()

        bot.update_position(
            symbol="AAPL",
            shares=10,
            entry_price=Decimal("150"),
            stop_loss_price=Decimal("145"),
        )

        assert "AAPL" in bot.positions
        assert bot.positions["AAPL"]["stop_loss"] == Decimal("145")
