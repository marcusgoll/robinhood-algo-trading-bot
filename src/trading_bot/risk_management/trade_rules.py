"""Trade Management Rules for Position Management.

This module implements ATR-based trade management rules:
- Break-even rule: Move stop to entry at 2xATR favorable move
- Scale-in rule: Add 50% position at 1.5xATR favorable move (max 3 scale-ins)
- Catastrophic exit rule: Close position at 3xATR adverse move

References:
- Feature: trade-management-rules
- Tests: tests/risk_management/test_trade_management_rules.py
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class PositionState:
    """Position state for trade management rules.

    Tracks current position state including entry price, current market price,
    ATR value, scale-in history, and rule activation flags.

    Attributes:
        symbol: Trading symbol (e.g., "TSLA", "AAPL")
        entry_price: Original entry price for the position
        current_price: Current market price
        scale_in_count: Number of times position has been scaled in (0-3)
        quantity: Current position size in shares
        current_atr: Current Average True Range value (for volatility-based rules)
        break_even_activated: Whether break-even rule has been triggered
        stop_price: Current stop-loss price (optional)
        target_price: Current profit target price (optional)
    """

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
    """Rule activation decision with action and metadata.

    Represents the outcome of evaluating a trade management rule,
    including what action to take and supporting audit information.

    Attributes:
        action: Action to take - "hold", "add_position", "close_position", "move_stop"
        reason: Human-readable explanation of the rule activation
        quantity: Number of shares for add_position or close_position actions
        new_stop_price: New stop price for move_stop actions
    """

    action: str  # "hold", "add_position", "close_position", "move_stop"
    reason: str
    quantity: int | None = None
    new_stop_price: Decimal | None = None


def evaluate_break_even_rule(position: PositionState) -> RuleActivation:
    """Evaluate break-even rule: move stop to entry at 2xATR favorable move.

    When a position moves 2xATR in the favorable direction (above entry for longs),
    move the stop-loss to the entry price to protect capital (break-even).

    Rule is idempotent - only triggers once per position (checked via break_even_activated flag).

    Args:
        position: Current position state with entry_price, current_price, current_atr

    Returns:
        RuleActivation with:
        - action="move_stop" if threshold reached and not yet activated
        - action="hold" if already activated or threshold not reached

    Examples:
        >>> position = PositionState(
        ...     symbol="TSLA",
        ...     entry_price=Decimal("100.00"),
        ...     current_price=Decimal("106.00"),  # 2xATR above entry
        ...     current_atr=Decimal("3.00"),
        ...     scale_in_count=0,
        ...     quantity=100,
        ...     break_even_activated=False,
        ... )
        >>> result = evaluate_break_even_rule(position)
        >>> result.action
        'move_stop'
        >>> result.new_stop_price
        Decimal('100.00')
    """
    # Check if rule already activated (idempotency)
    if position.break_even_activated:
        return RuleActivation(
            action="hold",
            reason="Break-even rule already activated once for this position",
        )

    # Check if ATR data available
    if position.current_atr is None:
        return RuleActivation(
            action="hold",
            reason="ATR data not available for break-even evaluation",
        )

    # Calculate favorable distance (above entry for longs)
    distance_above_entry = position.current_price - position.entry_price

    # Check if position reached 2xATR threshold
    threshold = Decimal("2.0") * position.current_atr

    if distance_above_entry >= threshold:
        return RuleActivation(
            action="move_stop",
            reason=f"Break-even rule: Position moved 2xATR (${threshold}) above entry, moving stop to entry price for capital protection",
            new_stop_price=position.entry_price,
        )

    return RuleActivation(
        action="hold",
        reason=f"Break-even threshold not reached: ${distance_above_entry} < 2xATR (${threshold})",
    )


def evaluate_scale_in_rule(
    position: PositionState,
    portfolio_risk_pct: Decimal | None = None,
    max_portfolio_risk_pct: Decimal | None = None,
) -> RuleActivation:
    """Evaluate scale-in rule: add 50% position at 1.5xATR favorable move.

    When a position moves 1.5xATR in the favorable direction, add 50% to the position
    to capitalize on momentum. Maximum 3 scale-ins per position.

    Rule respects portfolio risk limits - won't scale in if total portfolio risk
    would exceed max_portfolio_risk_pct (typically 2%).

    Args:
        position: Current position state
        portfolio_risk_pct: Current portfolio risk as percentage (optional)
        max_portfolio_risk_pct: Maximum allowed portfolio risk percentage (optional)

    Returns:
        RuleActivation with:
        - action="add_position" if threshold reached and limits not exceeded
        - action="hold" if max scale-ins reached or portfolio risk exceeded

    Examples:
        >>> position = PositionState(
        ...     symbol="TSLA",
        ...     entry_price=Decimal("100.00"),
        ...     current_price=Decimal("104.50"),  # 1.5xATR above entry
        ...     current_atr=Decimal("3.00"),
        ...     scale_in_count=0,
        ...     quantity=100,
        ... )
        >>> result = evaluate_scale_in_rule(position)
        >>> result.action
        'add_position'
        >>> result.quantity
        50
    """
    # Check if max scale-ins reached (limit: 3)
    MAX_SCALE_INS = 3
    if position.scale_in_count >= MAX_SCALE_INS:
        return RuleActivation(
            action="hold",
            reason=f"Scale-in limit reached: {position.scale_in_count} of max {MAX_SCALE_INS} scale-ins executed",
        )

    # Check if ATR data available
    if position.current_atr is None:
        return RuleActivation(
            action="hold",
            reason="ATR data not available for scale-in evaluation",
        )

    # Calculate favorable distance
    distance_above_entry = position.current_price - position.entry_price

    # Check if position reached 1.5xATR threshold
    threshold = Decimal("1.5") * position.current_atr

    # Position must be above threshold to be eligible for scale-in
    if distance_above_entry < threshold:
        return RuleActivation(
            action="hold",
            reason=f"Scale-in threshold not reached: ${distance_above_entry} < 1.5xATR (${threshold})",
        )

    # Check portfolio risk limits AFTER confirming threshold is met
    # This prevents scale-in even if position is favorable
    if portfolio_risk_pct is not None and max_portfolio_risk_pct is not None:
        if portfolio_risk_pct >= max_portfolio_risk_pct:
            return RuleActivation(
                action="hold",
                reason=f"Portfolio risk limit exceeded: {portfolio_risk_pct}% >= {max_portfolio_risk_pct}% max, cannot scale in",
            )

    # All checks passed - execute scale-in
    # Calculate 50% of original position
    scale_in_quantity = int(position.quantity * Decimal("0.5"))

    return RuleActivation(
        action="add_position",
        reason=f"Scale-in rule: Position moved 1.5xATR (${threshold}) above entry, adding 50% position",
        quantity=scale_in_quantity,
    )


def evaluate_catastrophic_exit_rule(position: PositionState) -> RuleActivation:
    """Evaluate catastrophic exit rule: close position at 3xATR adverse move.

    When a position moves 3xATR in the adverse direction (below entry for longs),
    immediately close the entire position to prevent catastrophic losses.

    This is an emergency exit triggered by extreme adverse price movement,
    overriding regular stop-loss logic.

    Args:
        position: Current position state

    Returns:
        RuleActivation with:
        - action="close_position" if catastrophic move detected
        - action="hold" if position within acceptable limits

    Examples:
        >>> position = PositionState(
        ...     symbol="TSLA",
        ...     entry_price=Decimal("100.00"),
        ...     current_price=Decimal("91.00"),  # 3xATR adverse move
        ...     current_atr=Decimal("3.00"),
        ...     scale_in_count=0,
        ...     quantity=100,
        ... )
        >>> result = evaluate_catastrophic_exit_rule(position)
        >>> result.action
        'close_position'
        >>> result.quantity
        100
    """
    # Check if ATR data available
    if position.current_atr is None:
        return RuleActivation(
            action="hold",
            reason="ATR data not available for catastrophic exit evaluation",
        )

    # Calculate adverse distance (below entry for longs)
    adverse_move = position.entry_price - position.current_price

    # Check if position hit 3xATR adverse threshold
    catastrophic_threshold = Decimal("3.0") * position.current_atr

    if adverse_move >= catastrophic_threshold:
        return RuleActivation(
            action="close_position",
            reason=f"CATASTROPHIC EXIT: Position moved 3xATR (${catastrophic_threshold}) against entry, closing entire position immediately",
            quantity=position.quantity,
        )

    return RuleActivation(
        action="hold",
        reason=f"Position within acceptable limits: ${adverse_move} adverse move < 3xATR (${catastrophic_threshold}) threshold",
    )
