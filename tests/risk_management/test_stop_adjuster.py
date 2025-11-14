"""Tests for StopAdjuster component.

Tests cover:
- Trailing stop adjustment to breakeven at 50% progress
- Respect for trailing_enabled configuration
- Position progress calculation
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from src.trading_bot.risk_management.config import RiskManagementConfig
from src.trading_bot.risk_management.models import PositionPlan
from src.trading_bot.risk_management.stop_adjuster import StopAdjuster


class TestStopAdjuster:
    """Test suite for StopAdjuster trailing stop logic."""

    def test_adjust_to_breakeven_at_50_percent(self) -> None:
        """Test stop adjustment to breakeven at 50% progress to target.

        Scenario (from spec.md FR-007 and tasks.md T016):
        - Given: Position with entry=$250.30, stop=$248.00, target=$254.90
                 Distance to target: $254.90 - $250.30 = $4.60
        - When: current_price=$252.60 (50% progress: $250.30 + $4.60 * 0.5 = $252.60)
        - Then: Returns:
            - new_stop_price=$250.30 (breakeven = entry price)
            - adjustment_reason="moved to breakeven - price reached 50% of target"

        Test validates:
        - Progress calculation: (current - entry) / (target - entry) = 0.5
        - Stop moves to entry price when 50% threshold reached
        - Adjustment reason provided for audit trail
        - Breakeven logic triggers at exactly 50% progress

        References:
        - spec.md FR-007: Trailing stop at 50% progress
        - tasks.md T016: Test breakeven adjustment
        - plan.md [RESEARCH DECISIONS]: Trailing stop at 50% progress
        """
        # Arrange: Create position plan matching spec scenario
        position_plan = PositionPlan(
            symbol="TSLA",
            entry_price=Decimal("250.30"),
            stop_price=Decimal("248.00"),
            target_price=Decimal("254.90"),
            quantity=434,
            risk_amount=Decimal("997.80"),  # 434 shares * $2.30 risk per share
            reward_amount=Decimal("1996.40"),  # 434 shares * $4.60 reward per share
            reward_ratio=2.0,
            pullback_source="detected",
            pullback_price=Decimal("248.00"),
        )

        # Config with trailing enabled and 50% breakeven threshold
        # Use default() factory and verify trailing settings
        config = RiskManagementConfig.default()

        # Current price at exactly 50% progress to target
        # Progress = (252.60 - 250.30) / (254.90 - 250.30) = 2.30 / 4.60 = 0.5
        current_price = Decimal("252.60")

        adjuster = StopAdjuster()

        # Act: Calculate stop adjustment at 50% progress
        result = adjuster.calculate_adjustment(
            current_price=current_price,
            position_plan=position_plan,
            config=config,
        )

        # Assert: Should return breakeven adjustment
        assert result is not None, "Should return adjustment at 50% progress"

        new_stop_price, adjustment_reason = result

        assert new_stop_price == Decimal("250.30"), (
            "Stop should move to breakeven (entry price) at 50% progress"
        )
        assert adjustment_reason == "moved to breakeven - price reached 50% of target", (
            "Should provide audit trail reason for breakeven adjustment"
        )

        # Verify the math: new stop should equal entry price
        assert new_stop_price == position_plan.entry_price, (
            "Breakeven stop must equal original entry price"
        )

    def test_no_adjustment_when_trailing_disabled(self) -> None:
        """Test no adjustment when trailing_enabled=False.

        Scenario (from tasks.md T017):
        - Given: Config with trailing_enabled=False
                 Price at 50% progress (same as T016)
        - When: calculate_adjustment() is called
        - Then: Returns None (no adjustment)

        Test validates:
        - trailing_enabled flag is respected
        - No stop adjustment occurs when trailing disabled
        - Position can reach target without stop movement

        References:
        - spec.md FR-007: Trailing stop configuration
        - tasks.md T017: Test trailing disabled
        - plan.md [SCHEMA]: RiskManagementConfig.trailing_enabled
        """
        # Arrange: Same position as T016, but trailing disabled
        position_plan = PositionPlan(
            symbol="TSLA",
            entry_price=Decimal("250.30"),
            stop_price=Decimal("248.00"),
            target_price=Decimal("254.90"),
            quantity=434,
            risk_amount=Decimal("997.80"),
            reward_amount=Decimal("1996.40"),
            reward_ratio=2.0,
            pullback_source="detected",
        )

        # Config with trailing DISABLED
        # Start with default, then override trailing_enabled
        config = RiskManagementConfig(
            account_risk_pct=1.0,
            min_risk_reward_ratio=2.0,
            default_stop_pct=2.0,
            trailing_enabled=False,  # DISABLED
            pullback_lookback_candles=20,
            trailing_breakeven_threshold=0.5,
        )

        # Current price at 50% progress (same as T016)
        current_price = Decimal("252.60")

        adjuster = StopAdjuster()

        # Act: Attempt to calculate adjustment with trailing disabled
        result = adjuster.calculate_adjustment(
            current_price=current_price,
            position_plan=position_plan,
            config=config,
        )

        # Assert: Should return None (no adjustment)
        assert result is None, (
            "Should return None when trailing_enabled=False, even at 50% progress"
        )
