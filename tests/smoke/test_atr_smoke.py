"""
Smoke tests for ATR-based dynamic stop-loss adjustment feature.

These tests validate the critical path for ATR functionality in a production-like
environment. Designed for CI/CD pipeline integration.

Exit codes:
- 0: All smoke tests passed
- 1: One or more smoke tests failed
- 2: Configuration or environment error

Usage:
    pytest tests/smoke/test_atr_smoke.py -v
    # Or standalone:
    python tests/smoke/test_atr_smoke.py

From: specs/atr-stop-adjustment/tasks.md T036
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from trading_bot.market_data.data_models import PriceBar
from trading_bot.risk_management.atr_calculator import ATRCalculator
from trading_bot.risk_management.calculator import calculate_position_plan
from trading_bot.risk_management.config import RiskManagementConfig
from trading_bot.risk_management.models import ATRStopData, PositionPlan
from trading_bot.risk_management.stop_adjuster import StopAdjuster


class TestATRSmoke:
    """Smoke tests for ATR feature critical path."""

    def test_smoke_atr_calculation_basic(self):
        """
        SMOKE: Verify ATR can calculate from valid price data.

        Critical Path:
        - Create 15 price bars with realistic data
        - Calculate ATR using 14-period default
        - Verify ATR > 0 and reasonable

        Failure Impact: ATR calculation completely broken
        """
        # Create 15 realistic price bars
        base_price = Decimal("250.00")
        base_time = datetime.now(UTC)
        price_bars = []

        for i in range(15):
            price_bars.append(
                PriceBar(
                    symbol="SPY",
                    timestamp=base_time + timedelta(days=i),
                    open=base_price + Decimal(str(i)),
                    high=base_price + Decimal(str(i + 5)),
                    low=base_price + Decimal(str(i - 3)),
                    close=base_price + Decimal(str(i + 2)),
                    volume=100_000_000,
                )
            )

        # Calculate ATR
        calculator = ATRCalculator(period=14)
        atr_value = calculator.calculate(price_bars)

        # Verify ATR is positive and reasonable
        assert atr_value > Decimal("0"), "ATR must be positive"
        assert atr_value < Decimal("50.00"), "ATR should be reasonable for $250 stock"

    def test_smoke_atr_stop_calculation(self):
        """
        SMOKE: Verify ATR stop calculation produces valid stops.

        Critical Path:
        - Calculate ATR stop using 2.0x multiplier
        - Verify stop price below entry (long position)
        - Verify stop distance within 0.7%-10% bounds

        Failure Impact: Position planning will fail in production
        """
        entry_price = Decimal("250.00")
        atr_value = Decimal("5.00")  # 2% ATR
        multiplier = 2.0

        # Calculate ATR stop
        atr_stop = ATRCalculator.calculate_atr_stop(
            entry_price=entry_price,
            atr_value=atr_value,
            multiplier=multiplier,
            position_type="long",
            atr_period=14,
        )

        # Verify stop structure
        assert isinstance(atr_stop, ATRStopData), "Should return ATRStopData"
        assert atr_stop.stop_price < entry_price, "Stop must be below entry for long"
        assert atr_stop.source == "atr", "Source must be 'atr'"

        # Verify stop distance within bounds
        stop_distance_pct = (
            (entry_price - atr_stop.stop_price) / entry_price
        ) * Decimal("100")
        assert stop_distance_pct >= Decimal(
            "0.7"
        ), "Stop distance must be >= 0.7%"
        assert stop_distance_pct <= Decimal("10.0"), "Stop distance must be <= 10%"

    def test_smoke_position_plan_integration(self):
        """
        SMOKE: Verify ATR integrates with position planning.

        Critical Path:
        - Calculate ATR stop
        - Create position plan with ATR data
        - Verify pullback_source="atr"
        - Verify position sizing calculations correct

        Failure Impact: ATR stops won't be used in production trades
        """
        # Setup
        entry_price = Decimal("250.00")
        atr_value = Decimal("5.00")
        account_balance = Decimal("10000.00")
        risk_pct = 1.0
        target_rr = 2.0

        # Calculate ATR stop
        atr_stop = ATRCalculator.calculate_atr_stop(
            entry_price=entry_price,
            atr_value=atr_value,
            multiplier=2.0,
            position_type="long",
            atr_period=14,
        )

        # Create position plan with ATR data
        position_plan = calculate_position_plan(
            symbol="SPY",
            entry_price=entry_price,
            stop_price=atr_stop.stop_price,
            target_rr=target_rr,
            account_balance=account_balance,
            risk_pct=risk_pct,
            atr_data=atr_stop,
        )

        # Verify ATR integration
        assert isinstance(position_plan, PositionPlan), "Should return PositionPlan"
        assert (
            position_plan.pullback_source == "atr"
        ), "pullback_source must be 'atr' when atr_data provided"
        assert position_plan.quantity > 0, "Should calculate valid quantity"
        assert position_plan.stop_price == atr_stop.stop_price, "Stop should match ATR calculation"

    def test_smoke_atr_dynamic_adjustment(self):
        """
        SMOKE: Verify ATR dynamic stop adjustment logic.

        Critical Path:
        - Create position with ATR stop
        - Simulate ATR change >20%
        - Verify StopAdjuster recalculates stop
        - Verify new stop returned

        Failure Impact: Dynamic ATR adjustment won't work in production
        """
        # Setup position plan
        entry_price = Decimal("250.00")
        initial_atr = Decimal("5.00")
        atr_multiplier = 2.0

        initial_stop = ATRCalculator.calculate_atr_stop(
            entry_price=entry_price,
            atr_value=initial_atr,
            multiplier=atr_multiplier,
            position_type="long",
            atr_period=14,
        )

        position_plan = calculate_position_plan(
            symbol="SPY",
            entry_price=entry_price,
            stop_price=initial_stop.stop_price,
            target_rr=2.0,
            account_balance=Decimal("10000.00"),
            risk_pct=1.0,
            atr_data=initial_stop,
        )

        # Simulate ATR increase >20% (volatility spike)
        current_price = Decimal("255.00")  # Price moved up
        current_atr = Decimal("6.50")  # ATR increased 30%

        # Configure RiskManagementConfig for ATR
        config = RiskManagementConfig.default()
        config.atr_enabled = True
        config.atr_multiplier = atr_multiplier
        config.atr_recalc_threshold = 0.20  # 20% threshold
        config.trailing_enabled = False  # Disable trailing for this test

        # Calculate adjustment
        adjuster = StopAdjuster(config=config)
        adjustment = adjuster.calculate_adjustment(
            current_price=current_price,
            position_plan=position_plan,
            config=config,
            current_atr=current_atr,
        )

        # Verify adjustment triggered
        assert adjustment is not None, "Should trigger ATR recalculation when ATR changes >20%"
        new_stop_price, reason = adjustment
        assert "ATR recalculation" in reason, "Reason should mention ATR recalculation"
        assert new_stop_price < current_price, "New stop should be below current price for long"

    def test_smoke_atr_config_validation(self):
        """
        SMOKE: Verify RiskManagementConfig validates ATR parameters.

        Critical Path:
        - Create config with ATR enabled
        - Verify valid config accepted
        - Verify invalid config rejected

        Failure Impact: Invalid ATR config could cause runtime errors
        """
        # Valid config should work
        valid_config = RiskManagementConfig.default()
        valid_config.atr_enabled = True
        valid_config.atr_period = 14
        valid_config.atr_multiplier = 2.0
        valid_config.atr_recalc_threshold = 0.20

        assert valid_config.atr_enabled is True
        assert valid_config.atr_period == 14
        assert valid_config.atr_multiplier == 2.0

        # Invalid config should raise ValueError via from_dict
        with pytest.raises(ValueError, match="atr_period"):
            RiskManagementConfig.from_dict({
                "atr_enabled": True,
                "atr_period": 0,  # Invalid: must be > 0
                "atr_multiplier": 2.0,
                "atr_recalc_threshold": 0.20,
            })

        with pytest.raises(ValueError, match="atr_multiplier"):
            RiskManagementConfig.from_dict({
                "atr_enabled": True,
                "atr_period": 14,
                "atr_multiplier": 0.0,  # Invalid: must be > 0
                "atr_recalc_threshold": 0.20,
            })

        with pytest.raises(ValueError, match="atr_recalc_threshold"):
            RiskManagementConfig.from_dict({
                "atr_enabled": True,
                "atr_period": 14,
                "atr_multiplier": 2.0,
                "atr_recalc_threshold": 1.5,  # Invalid: must be <= 1.0
            })

    def test_smoke_atr_fallback_to_pullback(self):
        """
        SMOKE: Verify system falls back to pullback stops when ATR fails.

        Critical Path:
        - Attempt position plan without ATR data
        - Verify pullback_source != "atr"
        - Verify position plan still created successfully

        Failure Impact: System would fail if ATR unavailable
        """
        # Create position plan without ATR data (fallback scenario)
        entry_price = Decimal("250.00")
        stop_price = Decimal("245.00")  # Manual/pullback stop

        position_plan = calculate_position_plan(
            symbol="SPY",
            entry_price=entry_price,
            stop_price=stop_price,
            target_rr=2.0,
            account_balance=Decimal("10000.00"),
            risk_pct=1.0,
            pullback_source="pullback",  # Explicit fallback
            atr_data=None,  # No ATR data
        )

        # Verify fallback worked
        assert isinstance(position_plan, PositionPlan)
        assert position_plan.pullback_source == "pullback", "Should use pullback source"
        assert position_plan.quantity > 0, "Should calculate valid quantity"
        assert position_plan.stop_price == stop_price, "Should use provided stop"


def run_smoke_tests():
    """Run smoke tests standalone (non-pytest)."""
    import sys

    test_suite = TestATRSmoke()
    tests = [
        ("ATR Calculation", test_suite.test_smoke_atr_calculation_basic),
        ("ATR Stop Calculation", test_suite.test_smoke_atr_stop_calculation),
        ("Position Plan Integration", test_suite.test_smoke_position_plan_integration),
        ("Dynamic Adjustment", test_suite.test_smoke_atr_dynamic_adjustment),
        ("Config Validation", test_suite.test_smoke_atr_config_validation),
        ("Fallback to Pullback", test_suite.test_smoke_atr_fallback_to_pullback),
    ]

    passed = 0
    failed = 0

    print("=" * 70)
    print("ATR Feature Smoke Tests")
    print("=" * 70)

    for name, test_func in tests:
        try:
            test_func()
            print(f"✅ PASS: {name}")
            passed += 1
        except AssertionError as e:
            print(f"❌ FAIL: {name}")
            print(f"   Error: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ ERROR: {name}")
            print(f"   Exception: {e}")
            failed += 1

    print("=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 70)

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    run_smoke_tests()
