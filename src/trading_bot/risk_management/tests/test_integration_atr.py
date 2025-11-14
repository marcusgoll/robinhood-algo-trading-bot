"""
Integration tests for ATR-based position planning workflow.

Tests the complete end-to-end workflow from price bars → ATR calculation →
stop calculation → position planning. This validates that all components
work together correctly.

From: specs/atr-stop-adjustment/tasks.md T028
Pattern: TDD RED phase - test MUST FAIL (integration doesn't exist yet)
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from trading_bot.market_data.data_models import PriceBar
from trading_bot.risk_management.atr_calculator import ATRCalculator
from trading_bot.risk_management.calculator import calculate_position_plan
from trading_bot.risk_management.models import ATRStopData, PositionPlan


def test_atr_workflow_end_to_end():
    """
    Test complete workflow from price bars → ATR → position plan.

    Workflow:
        1. Given: 15 realistic TSLA price bars
        2. When: ATRCalculator.calculate_atr_from_bars(price_bars)
        3. Then: Calculate ATR value
        4. When: ATRCalculator.calculate_atr_stop(entry, atr, multiplier)
        5. Then: Get ATRStopData with stop_price
        6. When: calculate_position_plan(entry, stop, target_rr, account, risk_pct, pullback_source="atr")
        7. Then: Returns PositionPlan with pullback_source="atr" and correct stop

    This test validates:
        - ATR calculation from realistic price data
        - ATR stop calculation using volatility-based logic
        - Integration with existing position planning infrastructure
        - pullback_source="atr" propagates through workflow

    From: specs/atr-stop-adjustment/tasks.md T028
    Pattern: TDD RED phase - test MUST FAIL (integration doesn't exist yet)
    """
    # Step 1: Create realistic TSLA price bars (15 bars for ATR calculation)
    # Using realistic TSLA volatility: ~$3-$5 daily range on $250 stock
    base_timestamp = datetime.now(UTC)
    base_price = Decimal("250.00")

    # Simulate 15 days of price action with realistic TSLA volatility
    price_bars: list[PriceBar] = []

    # Day 1-5: Moderate volatility (2% daily range)
    volatility_patterns = [
        # (open_offset, high_offset, low_offset, close_offset)
        (0, 5, -3, 2),    # Day 1: Up day
        (2, 4, -4, -2),   # Day 2: Down day
        (-2, 6, -2, 4),   # Day 3: Strong up day
        (4, 5, -5, -3),   # Day 4: Down day
        (-3, 3, -4, 1),   # Day 5: Recovery

        # Day 6-10: Higher volatility (3% daily range)
        (1, 8, -4, 5),    # Day 6: Volatility spike
        (5, 7, -6, -4),   # Day 7: Sharp pullback
        (-4, 2, -7, -2),  # Day 8: Continued weakness
        (-2, 9, -3, 6),   # Day 9: Strong bounce
        (6, 8, -2, 4),    # Day 10: Consolidation

        # Day 11-15: Moderate volatility (2.5% daily range)
        (4, 6, -4, 2),    # Day 11: Range day
        (2, 7, -3, 5),    # Day 12: Up trend
        (5, 6, -3, 3),    # Day 13: Continuation
        (3, 5, -5, -2),   # Day 14: Pullback
        (-2, 4, -4, 2),   # Day 15: Current day
    ]

    for i, (open_off, high_off, low_off, close_off) in enumerate(volatility_patterns):
        day_base = base_price + Decimal(str(i * 0.5))  # Slight uptrend

        price_bars.append(
            PriceBar(
                symbol="TSLA",
                timestamp=base_timestamp + timedelta(days=i),
                open=day_base + Decimal(str(open_off)),
                high=day_base + Decimal(str(high_off)),
                low=day_base + Decimal(str(low_off)),
                close=day_base + Decimal(str(close_off)),
                volume=50_000_000,  # Typical TSLA volume
            )
        )

    # Step 2: Calculate ATR from price bars (14-period default)
    atr_calculator = ATRCalculator(period=14)
    atr_value = atr_calculator.calculate(price_bars)

    # Verify ATR is calculated (should be > 0 for volatile TSLA data)
    assert atr_value > Decimal("0"), "ATR should be positive for volatile price data"
    assert atr_value < Decimal("20.00"), "ATR should be reasonable for $250 stock"

    # Step 3: Calculate ATR-based stop
    entry_price = Decimal("257.00")  # Entry at current price (day 15 close area)
    atr_multiplier = 2.0
    position_type = "long"

    atr_stop_data = ATRCalculator.calculate_atr_stop(
        entry_price=entry_price,
        atr_value=atr_value,
        multiplier=atr_multiplier,
        position_type=position_type,
        atr_period=14
    )

    # Verify ATRStopData structure
    assert isinstance(atr_stop_data, ATRStopData), "Should return ATRStopData"
    assert atr_stop_data.stop_price < entry_price, "Stop should be below entry for long"
    assert atr_stop_data.atr_value == atr_value, "ATR value should match calculation"
    assert atr_stop_data.atr_multiplier == atr_multiplier, "Multiplier should match input"
    assert atr_stop_data.source == "atr", "Source should be 'atr'"

    # Step 4: Create position plan using ATR stop
    account_balance = Decimal("10000.00")
    risk_pct = 1.0  # 1% risk per trade
    target_rr = 2.0  # 2:1 risk-reward ratio

    position_plan = calculate_position_plan(
        symbol="TSLA",
        entry_price=entry_price,
        stop_price=atr_stop_data.stop_price,
        target_rr=target_rr,
        account_balance=account_balance,
        risk_pct=risk_pct,
        pullback_source="atr"  # KEY: This marks the stop as ATR-based
    )

    # Step 5: Verify position plan integration
    assert isinstance(position_plan, PositionPlan), "Should return PositionPlan"

    # Verify prices
    assert position_plan.entry_price == entry_price, "Entry price should match input"
    assert position_plan.stop_price == atr_stop_data.stop_price, "Stop should match ATR calculation"
    assert position_plan.stop_price < entry_price, "Stop should be below entry for long"

    # Verify pullback source propagation (CRITICAL for ATR workflow)
    assert position_plan.pullback_source == "atr", \
        f"Expected pullback_source='atr', got '{position_plan.pullback_source}'"

    # Verify position sizing calculations
    assert position_plan.quantity > 0, "Should calculate valid quantity"
    assert position_plan.risk_amount > Decimal("0"), "Risk amount should be positive"
    assert position_plan.reward_amount > Decimal("0"), "Reward amount should be positive"

    # Verify risk-reward ratio (allow 5% tolerance for integer rounding)
    assert position_plan.reward_ratio >= target_rr * 0.95, \
        f"Reward ratio {position_plan.reward_ratio} should be >= {target_rr * 0.95:.2f} (95% of target {target_rr})"

    # Verify symbol
    assert position_plan.symbol == "TSLA", "Symbol should match input"

    # Verify target price is above entry (for long position with 2:1 RR)
    assert position_plan.target_price > entry_price, "Target should be above entry for long"

    # Verify risk calculation: risk_amount = account_balance * risk_pct / 100
    expected_risk_amount = account_balance * Decimal(str(risk_pct)) / Decimal("100")
    assert abs(position_plan.risk_amount - expected_risk_amount) < Decimal("0.01"), \
        f"Risk amount {position_plan.risk_amount} should equal {expected_risk_amount}"

    # Verify quantity calculation: quantity = risk_amount / (entry - stop)
    risk_per_share = entry_price - atr_stop_data.stop_price
    expected_quantity = int(expected_risk_amount / risk_per_share)
    assert position_plan.quantity == expected_quantity, \
        f"Quantity {position_plan.quantity} should equal {expected_quantity}"


def test_atr_workflow_with_insufficient_data():
    """
    Test that workflow gracefully handles insufficient price data.

    Given:
        - Only 10 price bars (need 14+ for ATR)

    When:
        ATRCalculator.calculate_atr_from_bars() is called

    Then:
        Raises ATRCalculationError with clear message about insufficient data

    This ensures the workflow fails fast with actionable error messages
    rather than producing invalid position plans.

    From: specs/atr-stop-adjustment/tasks.md T028 (error path)
    Pattern: TDD RED phase - test MUST FAIL
    """
    from trading_bot.risk_management.exceptions import ATRCalculationError

    # Create only 10 price bars (insufficient for 14-period ATR)
    base_timestamp = datetime.now(UTC)
    price_bars: list[PriceBar] = []

    for i in range(10):
        price_bars.append(
            PriceBar(
                symbol="TSLA",
                timestamp=base_timestamp + timedelta(days=i),
                open=Decimal("250.00"),
                high=Decimal("255.00"),
                low=Decimal("245.00"),
                close=Decimal("252.00"),
                volume=50_000_000,
            )
        )

    # Attempt ATR calculation with insufficient data
    atr_calculator = ATRCalculator(period=14)

    with pytest.raises(ATRCalculationError) as exc_info:
        atr_calculator.calculate(price_bars)

    # Verify error message is actionable
    error_msg = str(exc_info.value).lower()
    assert "insufficient" in error_msg or "14" in error_msg, \
        "Error should mention insufficient data or required period"


def test_atr_workflow_stop_validation_integration():
    """
    Test that ATR workflow respects existing stop distance validation.

    Given:
        - ATR value that would produce stop distance < 0.7% (too tight)

    When:
        calculate_position_plan() is called with ATR stop

    Then:
        Raises PositionPlanningError because stop distance violates bounds

    This ensures ATR-based stops are still subject to the same safety
    validations as manual/pullback stops (0.7%-10% range from T011).

    From: specs/atr-stop-adjustment/tasks.md T028 (validation path)
    Pattern: TDD RED phase - test MUST FAIL
    """
    from trading_bot.risk_management.exceptions import PositionPlanningError

    # Setup: Calculate stop that would be too tight (0.4% distance)
    entry_price = Decimal("250.00")
    stop_price = Decimal("249.00")  # 0.4% distance - below 0.7% minimum

    account_balance = Decimal("10000.00")
    risk_pct = 1.0
    target_rr = 2.0

    # Attempt to create position plan with too-tight ATR stop
    with pytest.raises(PositionPlanningError) as exc_info:
        calculate_position_plan(
            symbol="TSLA",
            entry_price=entry_price,
            stop_price=stop_price,
            target_rr=target_rr,
            account_balance=account_balance,
            risk_pct=risk_pct,
            pullback_source="atr"
        )

    # Verify error mentions stop distance validation
    error_msg = str(exc_info.value).lower()
    assert "tight" in error_msg or "0.7" in error_msg or "distance" in error_msg, \
        "Error should mention stop distance validation failure"
