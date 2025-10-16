"""Tests for Trade Management Rules.

Tests cover:
- Break-even rule evaluation with 2xATR threshold (T006)
- Break-even idempotency (prevents multiple activations) (T007)
- Scale-in limit enforcement (max 3 scale-ins per position) (T009)
- Catastrophic exit at 3xATR adverse move (T011)
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
    break_even_activated: bool = False
    stop_price: Decimal | None = None
    target_price: Decimal | None = None


@dataclass(frozen=True)
class RuleActivation:
    """Rule activation decision."""

    action: str  # "hold", "add", "close_position", "move_stop"
    reason: str
    quantity: int | None = None  # Full position quantity for close_position
    new_stop_price: Decimal | None = None  # New stop price for move_stop action


class TestBreakEvenRules:
    """Test suite for break-even trade management rules."""

    def test_break_even_rule_activates_at_2x_atr(self) -> None:
        """Test break-even rule moves stop to entry at 2xATR favorable move.

        Scenario (from T006 requirements):
        - Given: Long position at $100, current price $106, ATR $3, stop at $98
        - When: Position moves to 2xATR above entry ($106 = $100 + 2 * $3)
        - Then: Returns RuleActivation with:
            - action="move_stop"
            - new_stop_price=$100 (break-even = entry price)
            - reason explains 2xATR threshold reached

        Test validates:
        - Distance calculation: current_price - entry_price >= 2.0 * ATR
        - New stop price equals entry price (break-even protection)
        - Rule activation includes correct action and stop price
        - Audit reason explains 2xATR break-even threshold

        References:
        - Task T006: Break-even rule evaluation with 2xATR threshold
        - spec.md FR-001: Move stop to break-even at 2x ATR
        - spec.md Acceptance Scenario 1
        - Pattern: test_stop_adjuster.py test structure
        """
        # Arrange: Position at exactly 2xATR above entry
        position = PositionState(
            symbol="TSLA",
            entry_price=Decimal("100.00"),
            current_price=Decimal("106.00"),  # 2xATR above entry ($6 = 2 * $3)
            current_atr=Decimal("3.00"),
            scale_in_count=0,
            quantity=100,
            break_even_activated=False,  # Not yet activated
            stop_price=Decimal("98.00"),  # Original stop below entry
        )

        # Act: Evaluate break-even rule (implementation doesn't exist yet)
        # This will fail because evaluate_break_even_rule() doesn't exist
        from src.trading_bot.risk_management.trade_rules import (
            evaluate_break_even_rule,
        )

        result = evaluate_break_even_rule(position)

        # Assert: Should return activation to move stop to break-even
        assert result is not None, (
            "Should return RuleActivation at 2xATR threshold, not None"
        )

        assert result.action == "move_stop", (
            "Should return 'move_stop' action at 2xATR threshold"
        )

        # Verify new stop price equals entry (break-even)
        assert result.new_stop_price is not None, (
            "RuleActivation should include new_stop_price for move_stop action"
        )
        assert result.new_stop_price == Decimal("100.00"), (
            "New stop should be at entry price ($100) for break-even protection"
        )

        # Verify the math: current_price - entry_price = 2.0 * ATR
        distance_above_entry = position.current_price - position.entry_price
        expected_distance = Decimal("2.0") * position.current_atr
        assert distance_above_entry == expected_distance, (
            f"Position should be exactly 2xATR above entry: "
            f"{distance_above_entry} == {expected_distance}"
        )

        # Verify reason explains break-even threshold
        assert "break" in result.reason.lower() or "2x" in result.reason.lower(), (
            "Reason should explain 2xATR break-even threshold"
        )
        assert "atr" in result.reason.lower(), (
            "Reason should reference ATR as threshold metric"
        )

    def test_break_even_rule_prevents_multiple_activations(self) -> None:
        """Test that break-even rule prevents multiple activations (idempotency).

        Scenario (from T007 requirements):
        - Given: Position with break_even_activated=True, price 2xATR above entry
        - When: evaluate_break_even_rule() called again
        - Then: Returns RuleActivation with action="hold" (no stop adjustment)

        Test validates:
        - Break-even rule is idempotent (only triggers once)
        - Position with break_even_activated=True should NOT trigger again
        - Rule returns "hold" action when already activated
        - Audit reason explains rule was already executed

        References:
        - Task T007: Break-even idempotency test
        - spec.md FR-008: Execute break-even stop move only once per position
        - spec.md Edge Cases: Break-even triggered multiple times
        - Pattern: test_stop_adjuster.py test structure
        """
        # Arrange: Position where break-even was already activated
        position = PositionState(
            symbol="TSLA",
            entry_price=Decimal("100.00"),
            current_price=Decimal("110.00"),  # Well above 2xATR threshold
            scale_in_count=0,
            quantity=100,
            current_atr=Decimal("3.00"),
            break_even_activated=True,  # Already activated!
            stop_price=Decimal("100.00"),  # Stop already at break-even
        )

        # Act: Evaluate break-even rule when already activated
        # This will fail because evaluate_break_even_rule() doesn't exist
        from src.trading_bot.risk_management.trade_rules import (
            evaluate_break_even_rule,
        )

        result = evaluate_break_even_rule(position)

        # Assert: Should return "hold" action (no adjustment)
        assert result is not None, "Should return RuleActivation, not None"

        assert result.action == "hold", (
            "Should return 'hold' action when break_even_activated=True"
        )

        # Verify reason explains idempotency
        assert (
            "already" in result.reason.lower()
            or "activated" in result.reason.lower()
            or "once" in result.reason.lower()
        ), "Reason should explain that break-even was already activated"

        # Verify no new stop price is provided (hold means no change)
        assert result.new_stop_price is None, (
            "new_stop_price should be None for 'hold' action"
        )


class TestScaleInRules:
    """Test suite for scale-in trade management rules."""

    def test_scale_in_at_1_5x_atr_above_entry(self) -> None:
        """Test that scale-in rule adds 50% position at 1.5xATR above entry.

        Scenario (from task T008):
        - Given: Position with entry_price=$100, current_atr=$3, quantity=100
                 Position moves to 1.5xATR above entry ($104.50)
                 No previous scale-ins (scale_in_count=0)
        - When: Position reaches $104.50 (1.5 * $3 = $4.50 above entry)
        - Then: Returns RuleActivation with:
            - action="add_position"
            - quantity=50 (50% of original 100 shares)

        Test validates:
        - Distance calculation: current_price - entry_price >= 1.5 * ATR
        - Scale-in quantity: 50% of original position size
        - First scale-in only (scale_in_count=0)
        - Rule activation includes correct action and quantity

        References:
        - Task T008: Scale-in rule test at 1.5xATR
        - Pattern: test_stop_adjuster.py structure
        - Feature: trade-management-rules
        """
        # Arrange: Position at exactly 1.5xATR above entry
        position = PositionState(
            symbol="TSLA",
            entry_price=Decimal("100.00"),
            current_price=Decimal("104.50"),  # 1.5xATR above entry ($4.50 = 1.5 * $3)
            current_atr=Decimal("3.00"),
            scale_in_count=0,  # No previous scale-ins
            quantity=100,
        )

        # Act: Evaluate scale-in rule (implementation doesn't exist yet)
        # This will fail because evaluate_scale_in_rule() doesn't exist
        from src.trading_bot.risk_management.trade_rules import evaluate_scale_in_rule

        result = evaluate_scale_in_rule(position)

        # Assert: Should return activation to add 50% position
        assert result.action == "add_position", (
            "Should return 'add_position' action at 1.5xATR threshold"
        )

        assert result.quantity == 50, (
            "Should add 50 shares (50% of original 100-share position)"
        )

        # Verify the math: current_price - entry_price = 1.5 * ATR
        distance_above_entry = position.current_price - position.entry_price
        expected_distance = Decimal("1.5") * position.current_atr
        assert distance_above_entry == expected_distance, (
            f"Position should be exactly 1.5xATR above entry: "
            f"{distance_above_entry} == {expected_distance}"
        )

        # Verify reason explains scale-in threshold
        assert "1.5" in result.reason or "scale" in result.reason.lower(), (
            "Reason should explain 1.5xATR scale-in threshold"
        )

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

    def test_scale_in_blocked_by_portfolio_risk_limit(self) -> None:
        """Test that scale-in is blocked when portfolio risk exceeds 2%.

        Scenario (from T010 requirements):
        - Given: Portfolio at 1.8% risk, scale-in would push to 2.4%
        - When: Evaluate scale-in rule with portfolio_risk_pct parameter
        - Then: Returns RuleActivation with action="hold" (blocked by risk limit)

        Test validates:
        - Scale-in is blocked when total portfolio risk would exceed 2%
        - Current portfolio risk (1.8%) + scale-in risk (0.6%) = 2.4% > 2% limit
        - Rule returns "hold" action to prevent excessive risk
        - Audit reason explains portfolio risk limit exceeded

        References:
        - Task T010: Portfolio risk limit enforcement for scale-ins
        - Pattern: test_stop_adjuster.py test structure
        - Risk management constitution: Maximum 2% portfolio risk per position
        """
        # Arrange: Position where scale-in would exceed 2% portfolio risk
        # Current risk: 1.8%, scale-in would add 0.6% → total 2.4% > 2% limit
        position = PositionState(
            symbol="AAPL",
            entry_price=Decimal("150.00"),
            current_price=Decimal("148.00"),  # Slight pullback for scale-in opportunity
            scale_in_count=1,  # Already scaled in once
            quantity=100,
            current_atr=Decimal("3.50"),
        )

        # Portfolio is currently at 1.8% risk (below 2% limit)
        # But adding scale-in would push total to 2.4% (exceeds 2% limit)
        current_portfolio_risk_pct = Decimal("1.8")
        scale_in_risk_pct = Decimal("0.6")
        max_portfolio_risk_pct = Decimal("2.0")

        # Act: Evaluate scale-in with portfolio risk constraint
        # This will fail because evaluate_scale_in_rule() doesn't accept portfolio_risk_pct yet
        from src.trading_bot.risk_management.trade_rules import evaluate_scale_in_rule

        result = evaluate_scale_in_rule(
            position,
            portfolio_risk_pct=current_portfolio_risk_pct,
            max_portfolio_risk_pct=max_portfolio_risk_pct,
        )

        # Assert: Should block scale-in due to portfolio risk limit
        assert result.action == "hold", (
            "Should return 'hold' action when scale-in would exceed 2% portfolio risk"
        )

        # Verify reason explains risk limit
        assert "risk" in result.reason.lower(), (
            "Reason should explain that portfolio risk limit prevents scale-in"
        )

        assert "2" in result.reason or "portfolio" in result.reason.lower(), (
            "Reason should reference the 2% portfolio risk limit"
        )


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
