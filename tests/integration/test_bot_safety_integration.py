"""
Integration tests for TradingBot with SafetyChecks module.

Tests the complete integration of safety checks into the bot's trading workflow.

Constitution v1.0.0 - §Testing_Requirements: Integration testing
"""

import pytest
from decimal import Decimal
from unittest.mock import Mock, patch
from src.trading_bot.bot import TradingBot


class TestBotSafetyIntegration:
    """Test suite for bot integration with SafetyChecks."""

    def test_bot_initialization_with_safety_checks(self):
        """
        Test bot initializes with SafetyChecks module.

        GIVEN: Bot initialization with safety parameters
        WHEN: TradingBot() called
        THEN: SafetyChecks module initialized correctly
        """
        bot = TradingBot(
            paper_trading=True,
            max_position_pct=5.0,
            max_daily_loss_pct=3.0,
            max_consecutive_losses=3,
            trading_timezone="America/New_York"
        )

        # Verify SafetyChecks initialized
        assert hasattr(bot, 'safety_checks')
        assert bot.safety_checks is not None

        # Verify config passed correctly
        assert bot.safety_checks.config.max_daily_loss_pct == 3.0
        assert bot.safety_checks.config.max_consecutive_losses == 3
        assert bot.safety_checks.config.max_position_pct == 5.0
        assert bot.safety_checks.config.trading_timezone == "America/New_York"

    def test_trade_execution_with_sufficient_buying_power(self, caplog):
        """
        Test trade executes when all safety checks pass.

        GIVEN: Bot running, sufficient buying power, within trading hours
        WHEN: execute_trade() called
        THEN: Trade executes successfully
        """
        # Set caplog level to capture INFO logs
        caplog.set_level("INFO")

        bot = TradingBot(paper_trading=True)
        bot.start()

        # Mock check_trading_hours to return True
        with patch.object(bot.safety_checks, 'check_trading_hours', return_value=True):
            # Execute trade with sufficient buying power
            bot.execute_trade(
                symbol="AAPL",
                action="buy",
                shares=10,
                price=Decimal("150.00"),
                reason="Test trade"
            )

        # Verify trade executed
        assert "TRADE EXECUTED" in caplog.text
        assert "AAPL" in caplog.text
        assert "PAPER TRADE" in caplog.text

    def test_trade_blocked_insufficient_buying_power(self, caplog):
        """
        Test trade blocked when buying power insufficient.

        GIVEN: Bot running, insufficient buying power
        WHEN: execute_trade() called with large order
        THEN: Trade blocked with buying power reason
        """
        bot = TradingBot(paper_trading=True)
        bot.start()

        # Mock check_trading_hours to return True
        with patch.object(bot.safety_checks, 'check_trading_hours', return_value=True):
            # Execute trade exceeding buying power ($10k mock)
            bot.execute_trade(
                symbol="AAPL",
                action="buy",
                shares=1000,  # 1000 * $150 = $150,000 (exceeds $10k buying power)
                price=Decimal("150.00"),
                reason="Test trade - should block"
            )

        # Verify trade blocked
        assert "TRADE BLOCKED" in caplog.text
        assert "buying power" in caplog.text.lower()
        assert "TRADE EXECUTED" not in caplog.text

    def test_trade_blocked_outside_trading_hours(self, caplog):
        """
        Test trade blocked when outside trading hours.

        GIVEN: Bot running, outside trading hours (7am-10am EST)
        WHEN: execute_trade() called
        THEN: Trade blocked with trading hours reason
        """
        bot = TradingBot(paper_trading=True)
        bot.start()

        # Mock check_trading_hours to return False (outside hours)
        with patch.object(bot.safety_checks, 'check_trading_hours', return_value=False):
            # Execute trade outside trading hours
            bot.execute_trade(
                symbol="AAPL",
                action="buy",
                shares=10,
                price=Decimal("150.00"),
                reason="Test trade - should block"
            )

        # Verify trade blocked
        assert "TRADE BLOCKED" in caplog.text
        assert "trading hours" in caplog.text.lower()
        assert "TRADE EXECUTED" not in caplog.text

    def test_circuit_breaker_blocks_all_trades(self, caplog):
        """
        Test circuit breaker blocks all trades when active.

        GIVEN: Bot running, circuit breaker triggered
        WHEN: execute_trade() called
        THEN: Trade blocked with circuit breaker reason
        """
        bot = TradingBot(paper_trading=True)
        bot.start()

        # Trigger circuit breaker
        bot.safety_checks.trigger_circuit_breaker(reason="Test trigger")

        # Mock check_trading_hours to return True (won't matter, breaker trips first)
        with patch.object(bot.safety_checks, 'check_trading_hours', return_value=True):
            # Attempt trade
            bot.execute_trade(
                symbol="AAPL",
                action="buy",
                shares=10,
                price=Decimal("150.00"),
                reason="Test trade - should block"
            )

        # Verify trade blocked
        assert "TRADE BLOCKED" in caplog.text
        assert "Circuit breaker" in caplog.text
        assert "CIRCUIT BREAKER ACTIVE" in caplog.text
        assert "TRADE EXECUTED" not in caplog.text

    def test_circuit_breaker_reset_allows_trading(self, caplog):
        """
        Test circuit breaker reset allows trading again.

        GIVEN: Circuit breaker was active, then reset
        WHEN: execute_trade() called after reset
        THEN: Trade executes successfully
        """
        # Set caplog level to capture INFO logs
        caplog.set_level("INFO")

        bot = TradingBot(paper_trading=True)
        bot.start()

        # Trigger circuit breaker
        bot.safety_checks.trigger_circuit_breaker(reason="Test trigger")

        # Reset circuit breaker
        bot.safety_checks.reset_circuit_breaker()

        # Clear log
        caplog.clear()

        # Mock check_trading_hours to return True
        with patch.object(bot.safety_checks, 'check_trading_hours', return_value=True):
            # Attempt trade after reset
            bot.execute_trade(
                symbol="AAPL",
                action="buy",
                shares=10,
                price=Decimal("150.00"),
                reason="Test trade - should execute"
            )

        # Verify trade executed
        assert "TRADE EXECUTED" in caplog.text
        assert "TRADE BLOCKED" not in caplog.text

    def test_invalid_input_raises_error(self):
        """
        Test invalid inputs raise ValueError.

        GIVEN: Bot running
        WHEN: execute_trade() called with invalid symbol
        THEN: ValueError raised (from SafetyChecks validation)
        """
        bot = TradingBot(paper_trading=True)
        bot.start()

        # Invalid symbol should raise ValueError
        with pytest.raises(ValueError, match="Invalid symbol"):
            bot.execute_trade(
                symbol="",  # Empty symbol
                action="buy",
                shares=10,
                price=Decimal("150.00"),
                reason="Test"
            )

    def test_bot_start_checks_circuit_breaker(self, caplog):
        """
        Test bot start blocked if circuit breaker tripped.

        GIVEN: Circuit breaker already tripped
        WHEN: bot.start() called
        THEN: RuntimeError raised, bot does not start
        """
        bot = TradingBot(paper_trading=True)

        # Trigger old circuit breaker (for backward compatibility test)
        bot.circuit_breaker.is_tripped = True

        # Attempt to start should fail
        with pytest.raises(RuntimeError, match="Circuit breaker is tripped"):
            bot.start()

        # Verify bot not running
        assert not bot.is_running

    def test_get_buying_power_returns_mock_value(self):
        """
        Test get_buying_power returns mock value.

        GIVEN: Bot initialized
        WHEN: get_buying_power() called
        THEN: Returns mock value ($10,000)

        NOTE: Will be updated when account-data-module integrated
        """
        bot = TradingBot(paper_trading=True)

        buying_power = bot.get_buying_power()

        assert buying_power == 10000.00
        assert isinstance(buying_power, float)


class TestBackwardCompatibility:
    """Test backward compatibility with old CircuitBreaker."""

    def test_old_circuit_breaker_still_exists(self):
        """
        Test old CircuitBreaker still accessible for backward compatibility.

        GIVEN: Bot initialized
        WHEN: Accessing circuit_breaker attribute
        THEN: Old CircuitBreaker instance exists
        """
        bot = TradingBot(paper_trading=True)

        assert hasattr(bot, 'circuit_breaker')
        assert bot.circuit_breaker is not None
        assert hasattr(bot.circuit_breaker, 'is_tripped')
        assert hasattr(bot.circuit_breaker, 'check_and_trip')
        assert hasattr(bot.circuit_breaker, 'reset_daily')

    def test_both_circuit_breakers_coexist(self):
        """
        Test both old and new circuit breakers can coexist.

        GIVEN: Bot initialized
        WHEN: Checking both circuit breakers
        THEN: Both exist independently
        """
        bot = TradingBot(paper_trading=True)

        # Old circuit breaker
        assert hasattr(bot, 'circuit_breaker')

        # New SafetyChecks
        assert hasattr(bot, 'safety_checks')
        assert hasattr(bot.safety_checks, '_circuit_breaker_active')

        # They should be independent
        bot.circuit_breaker.is_tripped = True
        assert bot.circuit_breaker.is_tripped is True
        assert bot.safety_checks._circuit_breaker_active is False
