"""Tests for Trade Management Rules.

Tests cover:
- Scale-in limit enforcement (max 3 scale-ins per position)
- Position state tracking
- Rule activation logic

References:
- Feature: trade-management-rules
- Test structure pattern: test_stop_adjuster.py
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import pytest


# Test Models (will be moved to src when implementation exists)
@dataclass(frozen=True)
class PositionState:
    """Position state for trade management rules."""

    symbol: str
    entry_price: Decimal
    current_price: Decimal
    scale_in_count: int
    quantity: int
    current_atr: Decimal | None = None


@dataclass(frozen=True)
class RuleActivation:
    """Rule activation decision."""

    action: str  # "hold", "add", "close_position"
    reason: str
    quantity: int | None = None  # Full position quantity for close_position


class TestScaleInRules:
    """Test suite for scale-in trade management rules."""

    def test_scale_in_respects_max_limit(self) -> None:
        """Test that scale-in rule respects maximum 3 scale-ins limit.

        Scenario (from T009 requirements):
        - Given: Position with entry=$100, current_price=$110, scale_in_count=3
        - When: Evaluate scale-in rule eligibility
        - Then: Returns RuleActivation with action="hold" (no additional scale-in)

        Test validates:
        - Max scale-in limit of 3 is enforced
        - Position with 3 existing scale-ins cannot add more
        - Rule returns "hold" action instead of "add"
        - Audit reason explains max limit reached

        References:
        - Task T009: Scale-in max limit rule
        - Expected behavior: No scale-ins beyond count=3
        """
        # Arrange: Position that has already scaled in 3 times
        position = PositionState(
            symbol="TSLA",
            entry_price=Decimal("100.00"),
            current_price=Decimal("110.00"),  # 10% profit
            scale_in_count=3,  # Already at maximum
            quantity=100,
        )

        # Act: Evaluate scale-in eligibility (implementation doesn't exist yet)
        # This will fail because evaluate_scale_in_rule() doesn't exist
        from src.trading_bot.risk_management.trade_rules import evaluate_scale_in_rule

        result = evaluate_scale_in_rule(position)

        # Assert: Should return "hold" action due to max limit
        assert result.action == "hold", (
            "Should return 'hold' action when scale_in_count=3 (maximum reached)"
        )
        assert "max" in result.reason.lower() or "limit" in result.reason.lower(), (
            "Reason should explain that maximum scale-in limit has been reached"
        )
        assert "3" in result.reason, "Reason should reference the max limit of 3"


class TestCatastrophicExitRules:
    """Test suite for catastrophic exit trade management rules."""

    def test_catastrophic_exit_triggers_at_3x_atr_adverse_move(self) -> None:
        """Test catastrophic exit rule triggers at 3xATR adverse move.

        Scenario (from T011 requirements):
        - Given: Position with entry=$100, current_price=$91, current_atr=$3
        - When: Single-bar adverse move = $100 - $91 = $9 = 3 * $3 ATR
        - Then: Returns RuleActivation with action="close_position", quantity=full position

        Test validates:
        - Catastrophic exit rule triggers at exactly 3xATR adverse move
        - Rule returns "close_position" action for immediate exit
        - Quantity equals full position size (exit entire position)
        - Audit reason explains catastrophic move and ATR threshold

        References:
        - Task T011: Catastrophic exit rule at 3xATR
        - Pattern: test_stop_adjuster.py test structure
        - Expected behavior: Immediate position closure on extreme adverse move
        """
        # Arrange: Position with 3xATR adverse move ($9 move = 3 * $3 ATR)
        position = PositionState(
            symbol="TSLA",
            entry_price=Decimal("100.00"),
            current_price=Decimal("91.00"),  # $9 adverse move (long position)
            scale_in_count=0,
            quantity=100,
            current_atr=Decimal("3.00"),  # 3xATR = $9
        )

        # Act: Evaluate catastrophic exit rule (implementation doesn't exist yet)
        # This will fail because evaluate_catastrophic_exit_rule() doesn't exist
        from src.trading_bot.risk_management.trade_rules import (
            evaluate_catastrophic_exit_rule,
        )

        result = evaluate_catastrophic_exit_rule(position)

        # Assert: Should trigger immediate exit
        assert result.action == "close_position", (
            "Should return 'close_position' action when adverse move = 3xATR"
        )

        assert result.quantity == position.quantity, (
            "Should close entire position (quantity=100)"
        )

        # Verify reason explains catastrophic move
        assert "catastrophic" in result.reason.lower() or "3x" in result.reason.lower(), (
            "Reason should explain catastrophic move threshold"
        )

        assert "atr" in result.reason.lower(), (
            "Reason should reference ATR as the threshold metric"
        )
