"""
Unit tests for SafetyChecks module.

Tests pre-trade safety validation, circuit breakers, and risk management.

Constitution v1.0.0 - §Testing_Requirements: TDD with RED-GREEN-REFACTOR
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

# Import data classes from safety_checks module
from src.trading_bot.safety_checks import SafetyResult, PositionSize


class TestBuyingPowerCheck:
    """Test suite for buying power validation."""

    def test_check_buying_power_sufficient_funds(self):
        """
        Test buying power check with sufficient funds.

        GIVEN: Buying power = $10,000, order cost = $5,000
        WHEN: check_buying_power(quantity=100, price=50.00, current_buying_power=10000) called
        THEN: Returns True

        From: spec.md FR-001
        Task: T007 [RED]
        """
        from src.trading_bot.safety_checks import SafetyChecks
        from src.trading_bot.config import Config

        config = Mock(spec=Config)
        safety = SafetyChecks(config)

        result = safety.check_buying_power(
            quantity=100,
            price=50.00,
            current_buying_power=10000.00
        )

        assert result is True, "Should allow trade with sufficient buying power"

    def test_check_buying_power_insufficient_funds(self):
        """
        Test buying power check with insufficient funds.

        GIVEN: Buying power = $1,000, order cost = $1,500
        WHEN: check_buying_power(quantity=100, price=15.00, current_buying_power=1000) called
        THEN: Returns False

        From: spec.md FR-001, Scenario 1
        Task: T008 [RED]
        """
        from src.trading_bot.safety_checks import SafetyChecks
        from src.trading_bot.config import Config

        config = Mock(spec=Config)
        safety = SafetyChecks(config)

        result = safety.check_buying_power(
            quantity=100,
            price=15.00,
            current_buying_power=1000.00
        )

        assert result is False, "Should block trade with insufficient buying power"


class TestTradingHoursEnforcement:
    """Test suite for trading hours enforcement."""

    @patch('src.trading_bot.safety_checks.is_trading_hours')
    def test_check_trading_hours_blocks_outside_hours(self, mock_is_trading_hours):
        """
        Test trading hours enforcement blocks orders outside trading window.

        GIVEN: Current time is 6:45 AM EST (before 7am)
        WHEN: check_trading_hours() called
        THEN: Returns False

        From: spec.md FR-002, Scenario 2
        Task: T009 [RED]
        """
        from src.trading_bot.safety_checks import SafetyChecks
        from src.trading_bot.config import Config

        config = Mock(spec=Config)
        config.trading_timezone = "America/New_York"

        # Mock time utils to return False (outside hours)
        mock_is_trading_hours.return_value = False

        safety = SafetyChecks(config)
        result = safety.check_trading_hours()

        assert result is False, "Should block trade outside trading hours"
        mock_is_trading_hours.assert_called_once_with("America/New_York")


class TestDailyLossCircuitBreaker:
    """Test suite for daily loss limit circuit breaker."""

    def test_check_daily_loss_limit_exceeds_threshold(self):
        """
        Test daily loss circuit breaker triggers when limit exceeded.

        GIVEN: Daily PnL = -3.5%, limit = 3.0%
        WHEN: check_daily_loss_limit(current_daily_pnl=-3500, portfolio_value=100000) called
        THEN: Returns False

        From: spec.md FR-003, Scenario 3
        Task: T010 [RED]
        """
        from src.trading_bot.safety_checks import SafetyChecks
        from src.trading_bot.config import Config

        config = Mock(spec=Config)
        config.max_daily_loss_pct = 3.0

        safety = SafetyChecks(config)
        result = safety.check_daily_loss_limit(
            current_daily_pnl=-3500.00,
            portfolio_value=100000.00
        )

        assert result is False, "Should block trade when daily loss exceeds limit"


class TestConsecutiveLossDetector:
    """Test suite for consecutive loss detection."""

    def test_check_consecutive_losses_detects_pattern(self):
        """
        Test consecutive loss detector triggers at limit.

        GIVEN: Last 3 trades are losses
        WHEN: check_consecutive_losses() called
        THEN: Returns False

        From: spec.md FR-004, Scenario 4
        Task: T011 [RED]
        """
        from src.trading_bot.safety_checks import SafetyChecks
        from src.trading_bot.config import Config

        config = Mock(spec=Config)
        config.max_consecutive_losses = 3

        safety = SafetyChecks(config)

        # Mock trade history with 3 consecutive losses
        safety._trade_history = [
            {"outcome": "loss"},
            {"outcome": "loss"},
            {"outcome": "loss"}
        ]

        result = safety.check_consecutive_losses()

        assert result is False, "Should block trade after 3 consecutive losses"


class TestPositionSizeCalculator:
    """Test suite for position size calculation."""

    def test_calculate_position_size_enforces_max_limit(self):
        """
        Test position size calculator enforces 5% portfolio limit.

        GIVEN: Account balance = $100,000, max position = 5%
        WHEN: calculate_position_size(entry_price=10, stop_loss_price=9, account_balance=100000) called
        THEN: Returns PositionSize with dollar_amount ≤ $5,000

        From: spec.md FR-005
        Task: T012 [RED]
        """
        from src.trading_bot.safety_checks import SafetyChecks
        from src.trading_bot.config import Config

        config = Mock(spec=Config)
        config.max_position_pct = 5.0

        safety = SafetyChecks(config)
        result = safety.calculate_position_size(
            entry_price=10.00,
            stop_loss_price=9.00,
            account_balance=100000.00
        )

        assert isinstance(result, PositionSize), "Should return PositionSize object"
        assert result.dollar_amount <= 5000.00, "Position size should not exceed 5% of portfolio"


class TestDuplicateOrderPrevention:
    """Test suite for duplicate order prevention."""

    def test_check_duplicate_order_blocks_duplicate(self):
        """
        Test duplicate order prevention blocks same symbol.

        GIVEN: Pending buy order for AAPL exists
        WHEN: check_duplicate_order(symbol="AAPL", action="BUY") called
        THEN: Returns False

        From: spec.md FR-006, Scenario 6
        Task: T013 [RED]
        """
        from src.trading_bot.safety_checks import SafetyChecks
        from src.trading_bot.config import Config

        config = Mock(spec=Config)
        safety = SafetyChecks(config)

        # Simulate existing pending order
        safety._pending_orders = {"AAPL": "BUY"}

        result = safety.check_duplicate_order(symbol="AAPL", action="BUY")

        assert result is False, "Should block duplicate order for same symbol"


class TestCircuitBreakerManagement:
    """Test suite for circuit breaker trigger and reset."""

    def test_trigger_circuit_breaker_sets_active_flag(self):
        """
        Test circuit breaker trigger sets active flag.

        GIVEN: Circuit breaker is not active
        WHEN: trigger_circuit_breaker(reason="3 consecutive losses") called
        THEN: Circuit breaker active flag is True, reason is logged

        From: spec.md FR-007
        Task: T014 [RED]
        """
        from src.trading_bot.safety_checks import SafetyChecks
        from src.trading_bot.config import Config

        config = Mock(spec=Config)
        safety = SafetyChecks(config)

        # Ensure circuit breaker is initially not active
        assert not safety._circuit_breaker_active

        safety.trigger_circuit_breaker(reason="3 consecutive losses")

        assert safety._circuit_breaker_active is True, "Circuit breaker should be active"

    def test_reset_circuit_breaker_clears_flag(self):
        """
        Test circuit breaker reset clears active flag.

        GIVEN: Circuit breaker is active
        WHEN: reset_circuit_breaker() called
        THEN: Circuit breaker active flag is False

        From: spec.md FR-007
        Task: T015 [RED]
        """
        from src.trading_bot.safety_checks import SafetyChecks
        from src.trading_bot.config import Config

        config = Mock(spec=Config)
        safety = SafetyChecks(config)

        # Set circuit breaker active
        safety._circuit_breaker_active = True

        safety.reset_circuit_breaker()

        assert safety._circuit_breaker_active is False, "Circuit breaker should be reset"


class TestValidateTradeOrchestration:
    """Test suite for validate_trade() orchestration."""

    @patch('src.trading_bot.safety_checks.is_trading_hours')
    def test_validate_trade_passes_all_checks(self, mock_trading_hours):
        """
        Test validate_trade() returns safe when all checks pass.

        GIVEN: All safety checks pass
        WHEN: validate_trade(symbol="AAPL", action="BUY", quantity=100, price=150, current_buying_power=20000) called
        THEN: Returns SafetyResult(is_safe=True, reason=None)

        From: spec.md Requirements FR-001 through FR-007
        Task: T016 [RED]
        """
        from src.trading_bot.safety_checks import SafetyChecks
        from src.trading_bot.config import Config

        # Mock trading hours check to pass
        mock_trading_hours.return_value = True

        config = Mock(spec=Config)
        config.trading_timezone = "America/New_York"
        config.max_daily_loss_pct = 3.0
        config.max_consecutive_losses = 3
        config.max_position_pct = 5.0

        safety = SafetyChecks(config)

        # Mock all checks to pass
        safety._circuit_breaker_active = False
        safety._pending_orders = {}
        safety._trade_history = []

        result = safety.validate_trade(
            symbol="AAPL",
            action="BUY",
            quantity=100,
            price=150.00,
            current_buying_power=20000.00
        )

        assert isinstance(result, SafetyResult), "Should return SafetyResult"
        assert result.is_safe is True, "Trade should be allowed when all checks pass"
        assert result.reason is None, "No failure reason when trade is safe"

    @patch('src.trading_bot.safety_checks.is_trading_hours')
    def test_validate_trade_blocks_on_buying_power_failure(self, mock_trading_hours):
        """
        Test validate_trade() blocks on buying power failure (fail-safe).

        GIVEN: Buying power check fails
        WHEN: validate_trade(...) called
        THEN: Returns SafetyResult(is_safe=False, reason="Insufficient buying power...")

        From: spec.md NFR-002 (fail-safe design)
        Task: T017 [RED]
        """
        from src.trading_bot.safety_checks import SafetyChecks
        from src.trading_bot.config import Config

        # Mock trading hours check to pass (so we reach buying power check)
        mock_trading_hours.return_value = True

        config = Mock(spec=Config)
        config.trading_timezone = "America/New_York"

        safety = SafetyChecks(config)
        safety._circuit_breaker_active = False

        # Insufficient buying power scenario
        result = safety.validate_trade(
            symbol="AAPL",
            action="BUY",
            quantity=100,
            price=150.00,
            current_buying_power=1000.00  # Only $1,000 available, need $15,000
        )

        assert isinstance(result, SafetyResult), "Should return SafetyResult"
        assert result.is_safe is False, "Trade should be blocked"
        assert "buying power" in result.reason.lower(), "Reason should mention buying power"


class TestFailSafeBehavior:
    """Test suite for fail-safe error handling."""

    @patch('builtins.open', new_callable=MagicMock)
    @patch('json.load')
    def test_corrupt_state_file_trips_circuit_breaker(self, mock_json_load, mock_open):
        """
        Test corrupt circuit breaker state file trips circuit breaker (fail-safe).

        GIVEN: logs/circuit_breaker.json contains invalid JSON
        WHEN: SafetyChecks initialized
        THEN: Circuit breaker automatically trips (fail-safe)

        From: spec.md NFR-002, plan.md [RISK MITIGATION]
        Task: T035 [RED]
        """
        from src.trading_bot.safety_checks import SafetyChecks
        from src.trading_bot.config import Config
        import json as json_module

        # Mock json.load to raise JSONDecodeError (simulates corrupt file)
        mock_json_load.side_effect = json_module.JSONDecodeError("Invalid", "", 0)

        # Mock config
        config = Mock(spec=Config)

        safety = SafetyChecks(config)

        # Circuit breaker should be tripped (fail-safe)
        assert safety._circuit_breaker_active is True, "Circuit breaker should trip on corrupt state file"

    def test_missing_trades_log_assumes_zero_losses(self):
        """
        Test missing trades.log is handled gracefully.

        GIVEN: logs/trades.log does not exist
        WHEN: check_consecutive_losses() called
        THEN: Returns True (assume 0 losses), logs warning

        From: plan.md [RISK MITIGATION] Parse errors in trades.log
        Task: T037 [RED]
        """
        from src.trading_bot.safety_checks import SafetyChecks
        from src.trading_bot.config import Config

        config = Mock(spec=Config)
        config.max_consecutive_losses = 3

        safety = SafetyChecks(config)

        # Ensure trade history is empty (simulates missing log file)
        safety._trade_history = []

        result = safety.check_consecutive_losses()

        # Should return True (pass check) when no history available
        assert result is True, "Should assume 0 losses when trades.log missing"
