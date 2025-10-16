"""
Tests for RiskRewardCalculator module.

Validates position sizing with pullback stop-loss, stop distance validation,
stop direction validation, and risk-reward ratio enforcement.

From: specs/stop-loss-automation/tasks.md T010-T013
"""

from decimal import Decimal

import pytest

from src.trading_bot.risk_management.calculator import calculate_position_plan
from src.trading_bot.risk_management.exceptions import PositionPlanningError


def test_calculate_position_size_with_pullback() -> None:
    """
    Test position size calculation with pullback-based stop-loss.

    Given:
        - entry_price=$250.30
        - stop_price=$248.00 (pullback low, 2.30 point distance)
        - account_balance=$100,000
        - account_risk_pct=1.0% (max $1,000 risk)
        - target_rr=2.0 (2:1 risk-reward ratio)

    When:
        calculate_position_plan() is called

    Then:
        Returns PositionPlan with:
        - quantity=434 shares (risk_amount / risk_per_share = $1,000 / $2.30)
        - risk_amount=$1,000 (1% of $100,000)
        - target_price=$254.90 (entry + 2 * stop_distance = $250.30 + 2 * $2.30)
        - reward_ratio=2.0

    Calculation breakdown:
        risk_per_share = entry_price - stop_price = $250.30 - $248.00 = $2.30
        risk_amount = account_balance * (account_risk_pct / 100) = $100,000 * 0.01 = $1,000
        quantity = floor(risk_amount / risk_per_share) = floor($1,000 / $2.30) = 434 shares
        target_price = entry_price + (entry_price - stop_price) * target_rr
                     = $250.30 + ($250.30 - $248.00) * 2.0
                     = $250.30 + ($2.30 * 2.0)
                     = $250.30 + $4.60
                     = $254.90
        reward_amount = quantity * (target_price - entry_price)
                      = 434 * ($254.90 - $250.30)
                      = 434 * $4.60
                      = $1,996.40
        actual_reward_ratio = reward_amount / risk_amount
                            = $1,996.40 / $1,000
                            = 1.996 ≈ 2.0

    From: spec.md FR-003, tasks.md T010
    Pattern: TDD RED phase - test must FAIL until calculator module implemented
    """
    # Arrange
    symbol = "TSLA"
    entry_price = Decimal("250.30")
    stop_price = Decimal("248.00")
    account_balance = Decimal("100000.00")
    account_risk_pct = 1.0
    target_rr = 2.0

    # Act
    position_plan = calculate_position_plan(
        symbol=symbol,
        entry_price=entry_price,
        stop_price=stop_price,
        target_rr=target_rr,
        account_balance=account_balance,
        risk_pct=account_risk_pct
    )

    # Assert
    assert position_plan.symbol == "TSLA"
    assert position_plan.entry_price == Decimal("250.30")
    assert position_plan.stop_price == Decimal("248.00")
    assert position_plan.quantity == 434, f"Expected 434 shares, got {position_plan.quantity}"
    assert position_plan.risk_amount == Decimal("1000.00"), f"Expected $1,000 risk, got ${position_plan.risk_amount}"
    assert position_plan.target_price == Decimal("254.90"), f"Expected target $254.90, got ${position_plan.target_price}"
    assert position_plan.reward_ratio == pytest.approx(2.0, abs=0.01), f"Expected 2:1 ratio, got {position_plan.reward_ratio}"


def test_stop_must_be_below_entry_for_longs() -> None:
    """
    Test that stop-loss must be below entry price for long positions.

    Given:
        - entry_price=$250.30
        - stop_price=$251.00 (ABOVE entry - invalid!)
        - Long position (BUY order)

    When:
        calculate_position_plan() is called with stop above entry

    Then:
        Raises PositionPlanningError with message:
        "Stop price must be below entry for long positions"

    Rationale:
        For long positions, stop-loss protects against downside risk.
        A stop above entry would trigger immediately if filled at entry,
        or never trigger if price moves favorably. This is logically invalid.

    From: spec.md FR-013, tasks.md T012
    Pattern: TDD RED phase - test must FAIL until validation implemented
    """
    # Arrange
    symbol = "TSLA"
    entry_price = Decimal("250.30")
    stop_price = Decimal("251.00")  # Invalid: stop ABOVE entry
    account_balance = Decimal("100000.00")
    account_risk_pct = 1.0
    target_rr = 2.0

    # Act & Assert
    with pytest.raises(
        PositionPlanningError,
        match="Stop price must be below entry for long positions"
    ):
        calculate_position_plan(
            symbol=symbol,
            entry_price=entry_price,
            stop_price=stop_price,
            target_rr=target_rr,
            account_balance=account_balance,
            risk_pct=account_risk_pct
        )


def test_enforce_minimum_risk_reward_ratio() -> None:
    """
    Test that calculator enforces minimum risk-reward ratio requirement.

    Given:
        - entry_price=$100.00
        - stop_price=$98.00 (2% risk, $2.00 distance)
        - target_price=$101.00 (1% reward, $1.00 distance)
        - min_rr=2.0 (minimum 2:1 risk-reward ratio)
        - Calculated target_rr=0.5 (below minimum)

    When:
        calculate_position_plan() is called with target_rr=0.5

    Then:
        Raises PositionPlanningError with message:
        "Risk-reward ratio 0.5 below minimum 2.0"

    Reasoning:
        Risk distance: $100.00 - $98.00 = $2.00
        Reward distance (at 0.5 ratio): $2.00 * 0.5 = $1.00
        Target price (at 0.5 ratio): $100.00 + $1.00 = $101.00
        This gives 0.5:1 ratio, which is below the minimum 2.0:1 requirement.

    From: spec.md FR-006, tasks.md T013
    Pattern: TDD RED phase - test must FAIL until validation logic implemented
    """
    # Arrange
    symbol = "AAPL"
    entry_price = Decimal("100.00")
    stop_price = Decimal("98.00")  # 2% risk
    account_balance = Decimal("10000.00")
    account_risk_pct = 1.0
    target_rr = 0.5  # Below minimum 2.0 - should fail
    min_rr = 2.0

    # Act & Assert
    with pytest.raises(
        PositionPlanningError,
        match=r"Risk-reward ratio 0\.5 below minimum 2\.0"
    ):
        calculate_position_plan(
            symbol=symbol,
            entry_price=entry_price,
            stop_price=stop_price,
            target_rr=target_rr,
            account_balance=account_balance,
            risk_pct=account_risk_pct,
            min_risk_reward_ratio=min_rr
        )
