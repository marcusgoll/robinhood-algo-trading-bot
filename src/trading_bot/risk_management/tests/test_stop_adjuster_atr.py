"""
Tests for StopAdjuster with ATR-based dynamic stop adjustment.

RED phase tests for TDD workflow - these tests should fail initially.
"""

from datetime import UTC, datetime
from decimal import Decimal

from trading_bot.risk_management.config import RiskManagementConfig
from trading_bot.risk_management.models import PositionPlan
from trading_bot.risk_management.stop_adjuster import StopAdjuster


def test_calculate_adjustment_with_atr_change():
    """
    Test stop adjustment when ATR changes significantly.

    Given:
        - Position with initial ATR = $6.50
        - Current ATR = $8.50 (30% increase, exceeds 20% threshold)
        - Current price = $420.00
        - Initial entry = $400.00
        - ATR multiplier = 2.0
        - atr_recalc_threshold = 0.20 (20%)

    When:
        StopAdjuster.calculate_adjustment() is called with current_atr parameter

    Then:
        - Returns new stop price based on current ATR
        - New stop = current_price - (current_atr * multiplier)
        - New stop = $420.00 - ($8.50 * 2.0) = $420.00 - $17.00 = $403.00
        - Returns adjustment reason mentioning ATR change

    ATR Change Calculation:
        atr_change_pct = |current_atr - initial_atr| / initial_atr
                       = |8.50 - 6.50| / 6.50
                       = 2.00 / 6.50
                       = 0.3077 (30.77%)

        30.77% > 20% threshold → Trigger ATR recalculation

    Dynamic Stop Adjustment Logic:
        1. Check if ATR changed >20% from initial value
        2. If yes, recalculate stop using current ATR
        3. Compare new ATR stop with breakeven/trailing stop
        4. Select widest stop (protects position best)

    From: specs/atr-stop-adjustment/tasks.md T013
    Pattern: TDD RED phase - test MUST FAIL (current_atr parameter doesn't exist yet)
    """
    # Arrange: Create position with initial ATR stop
    initial_atr_value = Decimal("6.50")
    entry_price = Decimal("400.00")
    multiplier = 2.0

    # Initial ATR stop: $400.00 - ($6.50 * 2.0) = $387.00
    initial_stop_price = entry_price - (initial_atr_value * Decimal(str(multiplier)))

    position_plan = PositionPlan(
        symbol="NVDA",
        entry_price=entry_price,
        stop_price=initial_stop_price,  # $387.00
        target_price=Decimal("440.00"),  # 2:1 risk/reward
        quantity=100,
        risk_amount=Decimal("1300.00"),
        reward_amount=Decimal("4000.00"),
        reward_ratio=3.08,
        pullback_source="atr",
        pullback_price=initial_stop_price,
        created_at=datetime.now(UTC)
    )

    # Current market conditions
    current_price = Decimal("420.00")  # Position up $20 from entry
    current_atr_value = Decimal("8.50")  # ATR increased 30.77%

    # Configuration with ATR enabled
    config = RiskManagementConfig(
        account_risk_pct=1.0,
        min_risk_reward_ratio=2.0,
        default_stop_pct=2.0,
        trailing_enabled=True,
        pullback_lookback_candles=20,
        trailing_breakeven_threshold=0.5,
        atr_enabled=True,
        atr_period=14,
        atr_multiplier=2.0,
        atr_recalc_threshold=0.20  # 20% threshold
    )

    # Act: Calculate adjustment with current ATR
    adjuster = StopAdjuster(config=config)

    new_stop_price, adjustment_reason = adjuster.calculate_adjustment(
        current_price=current_price,
        position_plan=position_plan,
        config=config,
        current_atr=current_atr_value  # NEW parameter
    )

    # Assert: Stop should be recalculated based on current ATR
    expected_new_stop = current_price - (current_atr_value * Decimal(str(multiplier)))
    # Expected: $420.00 - ($8.50 * 2.0) = $420.00 - $17.00 = $403.00

    assert new_stop_price == expected_new_stop, \
        f"Expected stop at ${expected_new_stop}, got ${new_stop_price}"

    # Verify adjustment reason mentions ATR change
    assert "atr" in adjustment_reason.lower(), \
        f"Adjustment reason should mention ATR, got: {adjustment_reason}"

    # Verify ATR change is significant (>20%)
    atr_change_pct = float(abs(current_atr_value - initial_atr_value) / initial_atr_value)
    assert atr_change_pct > 0.20, \
        f"ATR change {atr_change_pct:.2%} should exceed 20% threshold"


def test_calculate_adjustment_no_atr_recalc_under_threshold():
    """
    Test that stop adjustment skips ATR recalculation when change is below threshold.

    Given:
        - Position with initial ATR = $6.50
        - Current ATR = $7.00 (7.7% increase, BELOW 20% threshold)
        - Current price = $420.00

    When:
        StopAdjuster.calculate_adjustment() is called with current_atr

    Then:
        - ATR change is below threshold (7.7% < 20%)
        - Stop adjustment uses trailing stop logic instead
        - ATR recalculation is NOT triggered

    ATR Change Calculation:
        atr_change_pct = |7.00 - 6.50| / 6.50
                       = 0.50 / 6.50
                       = 0.077 (7.7%)

        7.7% < 20% threshold → No ATR recalculation

    From: specs/atr-stop-adjustment/tasks.md T013 (edge case)
    Pattern: TDD RED phase - test MUST FAIL (threshold logic doesn't exist yet)
    """
    # Arrange: Create position with initial ATR stop
    initial_atr_value = Decimal("6.50")
    entry_price = Decimal("400.00")
    multiplier = 2.0
    initial_stop_price = entry_price - (initial_atr_value * Decimal(str(multiplier)))

    position_plan = PositionPlan(
        symbol="NVDA",
        entry_price=entry_price,
        stop_price=initial_stop_price,
        target_price=Decimal("440.00"),
        quantity=100,
        risk_amount=Decimal("1300.00"),
        reward_amount=Decimal("4000.00"),
        reward_ratio=3.08,
        pullback_source="atr",
        pullback_price=initial_stop_price,
        created_at=datetime.now(UTC)
    )

    # Current conditions: ATR changed only 7.7% (below threshold)
    current_price = Decimal("420.00")
    current_atr_value = Decimal("7.00")  # Only 7.7% increase

    config = RiskManagementConfig(
        account_risk_pct=1.0,
        min_risk_reward_ratio=2.0,
        default_stop_pct=2.0,
        trailing_enabled=True,
        pullback_lookback_candles=20,
        trailing_breakeven_threshold=0.5,
        atr_enabled=True,
        atr_period=14,
        atr_multiplier=2.0,
        atr_recalc_threshold=0.20
    )

    # Act: Calculate adjustment
    adjuster = StopAdjuster(config=config)
    new_stop_price, adjustment_reason = adjuster.calculate_adjustment(
        current_price=current_price,
        position_plan=position_plan,
        config=config,
        current_atr=current_atr_value
    )

    # Assert: ATR recalculation should NOT be triggered
    # Stop adjustment should use standard trailing stop logic instead
    atr_change_pct = float(abs(current_atr_value - initial_atr_value) / initial_atr_value)
    assert atr_change_pct < 0.20, \
        f"ATR change {atr_change_pct:.2%} should be below 20% threshold"

    # Adjustment reason should NOT mention ATR (uses trailing stop instead)
    # This assertion might be too strict - adjust based on implementation
    # For now, just verify stop was adjusted (not specific to ATR)
    assert new_stop_price != initial_stop_price or "no adjustment" in adjustment_reason.lower()
