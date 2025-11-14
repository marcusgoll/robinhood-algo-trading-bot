"""
Tests for Calculator integration with ATR-based stop-loss data.

RED phase test for TDD workflow - test should fail initially.

From: specs/atr-stop-adjustment/tasks.md T011
"""

from decimal import Decimal

from trading_bot.risk_management.calculator import calculate_position_plan
from trading_bot.risk_management.models import ATRStopData


def test_calculate_position_plan_with_atr_data():
    """
    Test Calculator.calculate_position_plan() integration with ATR data.

    Given:
        - entry_price=$250.00
        - stop_price=$248.00 (from ATR calculation)
        - atr_data=ATRStopData(stop=$248.00, atr=$2.50)
        - account_balance=$100,000
        - account_risk_pct=1.0% (max $1,000 risk)
        - target_rr=2.0 (2:1 risk-reward ratio)

    When:
        calculate_position_plan() is called WITH atr_data parameter

    Then:
        Returns PositionPlan with:
        - pullback_source="atr" (indicates ATR-based stop)
        - stop_price=$248.00 (from ATR data)
        - quantity=500 shares (risk_amount / risk_per_share = $1,000 / $2.00)
        - target_price=$254.00 (entry + 2 * stop_distance = $250.00 + 2 * $2.00)

    Calculation breakdown:
        risk_per_share = entry_price - stop_price = $250.00 - $248.00 = $2.00
        risk_amount = account_balance * (account_risk_pct / 100) = $100,000 * 0.01 = $1,000
        quantity = floor(risk_amount / risk_per_share) = floor($1,000 / $2.00) = 500 shares
        target_price = entry_price + (entry_price - stop_price) * target_rr
                     = $250.00 + ($250.00 - $248.00) * 2.0
                     = $250.00 + ($2.00 * 2.0)
                     = $250.00 + $4.00
                     = $254.00

    From: specs/atr-stop-adjustment/tasks.md T011
    Pattern: TDD RED phase - test MUST FAIL (atr_data parameter doesn't exist yet)
    """
    # Arrange
    symbol = "AAPL"
    entry_price = Decimal("250.00")
    stop_price = Decimal("248.00")
    account_balance = Decimal("100000.00")
    account_risk_pct = 1.0
    target_rr = 2.0

    # Create ATRStopData with ATR metrics
    atr_data = ATRStopData(
        stop_price=Decimal("248.00"),
        atr_value=Decimal("2.50"),
        atr_multiplier=2.0,
        atr_period=14
    )

    # Act - Call calculate_position_plan WITH atr_data parameter
    # This will FAIL because atr_data parameter doesn't exist yet
    position_plan = calculate_position_plan(
        symbol=symbol,
        entry_price=entry_price,
        stop_price=stop_price,
        target_rr=target_rr,
        account_balance=account_balance,
        risk_pct=account_risk_pct,
        atr_data=atr_data  # NEW PARAMETER - will cause TypeError
    )

    # Assert
    assert position_plan.symbol == "AAPL"
    assert position_plan.entry_price == Decimal("250.00")
    assert position_plan.stop_price == Decimal("248.00")
    assert position_plan.pullback_source == "atr", \
        f"Expected pullback_source='atr', got '{position_plan.pullback_source}'"
    assert position_plan.quantity == 500, \
        f"Expected 500 shares, got {position_plan.quantity}"
    assert position_plan.target_price == Decimal("254.00"), \
        f"Expected target $254.00, got ${position_plan.target_price}"
