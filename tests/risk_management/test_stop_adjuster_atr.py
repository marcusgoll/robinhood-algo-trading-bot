"""Tests for StopAdjuster ATR-based dynamic stop adjustment.

Tests cover:
- ATR recalculation when volatility changes >20%
- Stop adjustment logic with current_atr parameter
- Integration with existing breakeven/trailing stop logic
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from src.trading_bot.risk_management.config import RiskManagementConfig
from src.trading_bot.risk_management.models import PositionPlan
from src.trading_bot.risk_management.stop_adjuster import StopAdjuster


class TestStopAdjusterATR:
    """Test suite for StopAdjuster ATR-based dynamic stop adjustment."""

    def test_calculate_adjustment_with_atr_change(self) -> None:
        """Test stop adjustment when ATR changes >20%.

        Scenario (from spec.md Acceptance Scenario 5, FR-007 and tasks.md T013):
        - Given: Position with initial ATR $6.50 (at entry)
                 Position at entry=$410.00, stop=$397.00 (2x ATR), target=$436.00
                 Current ATR increased to $8.50 (30% increase, exceeds 20% threshold)
        - When: current_price=$420.00
                calculate_adjustment(current_price, position_plan, config, current_atr=$8.50)
        - Then: Returns:
            - new_stop_price=$403.00 (recalculated: $420.00 - 2.0 * $8.50)
            - adjustment_reason="adjusted for ATR increase from 6.50 to 8.50"

        Test validates:
        - ATR change detection: (8.50 - 6.50) / 6.50 = 0.307 (30.7% > 20% threshold)
        - Stop recalculation: new_stop = current_price - (multiplier * current_atr)
        - ATR-based stop takes precedence when wider than breakeven/trailing
        - Adjustment reason includes old and new ATR values for audit trail

        References:
        - spec.md Acceptance Scenario 5: "If ATR recalculates and changes by >20%..."
        - spec.md FR-007: Trailing stop adjustment with ATR awareness
        - tasks.md T013: Write test for ATR recalculation
        - tasks.md T019: Extend calculate_adjustment() with current_atr parameter
        - plan.md [INTEGRATION SCENARIOS]: ATR volatility adjustment
        """
        # Arrange: Create position plan with ATR-based stop
        # Entry: $410.00, Initial ATR: $6.50, Multiplier: 2.0
        # Initial stop: $410.00 - (2.0 * $6.50) = $397.00
        # Target: $436.00 (2:1 reward ratio)
        initial_atr = Decimal("6.50")
        atr_multiplier = 2.0

        position_plan = PositionPlan(
            symbol="NVDA",
            entry_price=Decimal("410.00"),
            stop_price=Decimal("397.00"),  # Based on initial ATR
            target_price=Decimal("436.00"),
            quantity=77,
            risk_amount=Decimal("1001.00"),  # 77 shares * $13.00 risk per share
            reward_amount=Decimal("2002.00"),  # 77 shares * $26.00 reward per share
            reward_ratio=2.0,
            pullback_source="atr",
            pullback_price=None,
        )

        # Config with ATR enabled and trailing enabled
        config = RiskManagementConfig.default()

        # Current state: Price moved up to $420.00, ATR increased to $8.50
        current_price = Decimal("420.00")
        current_atr = Decimal("8.50")

        # ATR change: (8.50 - 6.50) / 6.50 = 0.307 = 30.7% (exceeds 20% threshold)
        # Expected new stop: $420.00 - (2.0 * $8.50) = $403.00

        adjuster = StopAdjuster()

        # Act: Calculate stop adjustment with ATR recalculation
        result = adjuster.calculate_adjustment(
            current_price=current_price,
            position_plan=position_plan,
            config=config,
            current_atr=current_atr,  # NEW PARAMETER - will cause test to fail
        )

        # Assert: Should return ATR-based adjustment
        assert result is not None, (
            "Should return adjustment when ATR changes >20%"
        )

        new_stop_price, adjustment_reason = result

        # Verify new stop price based on recalculated ATR
        expected_stop = Decimal("403.00")  # $420.00 - (2.0 * $8.50)
        assert new_stop_price == expected_stop, (
            f"Stop should be recalculated using current ATR: "
            f"{current_price} - (2.0 * {current_atr}) = {expected_stop}, "
            f"got {new_stop_price}"
        )

        # Verify adjustment reason includes ATR values
        assert "6.50" in adjustment_reason, (
            "Adjustment reason should include initial ATR value"
        )
        assert "8.50" in adjustment_reason, (
            "Adjustment reason should include current ATR value"
        )
        assert "adjusted for ATR" in adjustment_reason.lower(), (
            "Adjustment reason should indicate ATR-based adjustment"
        )

        # Verify new stop is wider than original (protecting position)
        assert new_stop_price > position_plan.stop_price, (
            f"New stop ${new_stop_price} should be wider than original ${position_plan.stop_price} "
            "to accommodate increased volatility"
        )
