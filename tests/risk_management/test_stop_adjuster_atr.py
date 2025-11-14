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

    def test_average_entry_price_for_partial_fills(self) -> None:
        """Test that stop rules evaluate against average entry price for scaled positions.

        Scenario (from T013 [RED] requirement - partial fills):
        - Given: Position scaled in 3 times:
                 Initial: 100 shares @ $100.00
                 Scale 1: 50 shares @ $104.00
                 Scale 2: 50 shares @ $108.00
        - When: Calculating average entry price
        - Then: Average entry = (100*100 + 50*104 + 50*108) / 200 = $103.00
                Rules should evaluate against $103.00, not original $100.00 entry

        Test validates:
        - Weighted average calculation for partial fills
        - Stop rules use average entry price, not first entry price
        - Proper handling of position scaling scenarios
        - Audit trail includes average entry price calculation

        References:
        - Trade management rules for scaled positions
        - Position sizing with partial fills
        - Risk management with average entry price
        """
        # Arrange: Create position plan representing scaled-in position
        # This test will FAIL because PositionPlan doesn't support partial fills yet

        # Initial fill: 100 shares @ $100
        initial_entry = Decimal("100.00")
        initial_quantity = 100

        # Scale-in fills:
        # Fill 1: 50 shares @ $104
        # Fill 2: 50 shares @ $108
        scale_fills = [
            (50, Decimal("104.00")),
            (50, Decimal("108.00")),
        ]

        # Expected average entry:
        # (100 * 100 + 50 * 104 + 50 * 108) / 200
        # = (10000 + 5200 + 5400) / 200
        # = 20600 / 200
        # = 103.00
        expected_average_entry = Decimal("103.00")

        total_quantity = initial_quantity + sum(qty for qty, _ in scale_fills)

        # Currently PositionPlan only has single entry_price
        # This test expects a new field or method to calculate average entry
        position_plan = PositionPlan(
            symbol="TSLA",
            entry_price=initial_entry,  # Original entry
            stop_price=Decimal("97.00"),  # 3% below original entry
            target_price=Decimal("109.00"),  # 2:1 reward ratio from average entry
            quantity=total_quantity,  # Total position size: 200 shares
            risk_amount=Decimal("1200.00"),  # Based on average entry
            reward_amount=Decimal("2400.00"),
            reward_ratio=2.0,
            pullback_source="detected",
            pullback_price=Decimal("97.00"),
            # NEW FIELD (doesn't exist yet - will cause test to fail):
            # partial_fills=[(initial_quantity, initial_entry)] + scale_fills,
        )

        config = RiskManagementConfig.default()

        # Current price at 50% progress from AVERAGE entry (not original entry)
        # Progress from average entry: $103.00 + (($109.00 - $103.00) * 0.5) = $106.00
        current_price = Decimal("106.00")

        adjuster = StopAdjuster()

        # Act: Calculate stop adjustment
        # This will FAIL because:
        # 1. PositionPlan doesn't have average_entry_price property/method
        # 2. calculate_adjustment() uses entry_price directly instead of average
        result = adjuster.calculate_adjustment(
            current_price=current_price,
            position_plan=position_plan,
            config=config,
        )

        # Assert: Should return breakeven at AVERAGE entry price, not original entry
        assert result is not None, (
            "Should return adjustment at 50% progress from average entry"
        )

        new_stop_price, adjustment_reason = result

        # Stop should move to average entry price ($103.00), not original entry ($100.00)
        assert new_stop_price == expected_average_entry, (
            f"Stop should move to average entry price ${expected_average_entry} "
            f"(not original entry ${initial_entry}), got ${new_stop_price}"
        )

        assert "breakeven" in adjustment_reason.lower(), (
            "Should indicate breakeven adjustment in reason"
        )

        # Verify that average entry is calculated correctly
        # This will fail because the functionality doesn't exist yet
        if hasattr(position_plan, 'average_entry_price'):
            calculated_average = position_plan.average_entry_price
            assert calculated_average == expected_average_entry, (
                f"Average entry price calculation incorrect: "
                f"expected ${expected_average_entry}, got ${calculated_average}"
            )
        else:
            # Test will fail here - attribute doesn't exist
            pytest.fail(
                "PositionPlan missing average_entry_price property. "
                "Need to add partial_fills tracking and average_entry_price calculation."
            )
