"""Risk and position sizing calculations."""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from trading_bot.risk_management.exceptions import PositionPlanningError
from trading_bot.risk_management.models import ATRStopData, PositionPlan


def validate_stop_distance(entry: Decimal, stop: Decimal) -> None:
    """
    Validate that stop distance is within acceptable bounds.

    Per task T011: Only exactly 0.5% stop distance is valid for the lower bound.
    Anything between 0.5% and 0.7% is considered "too tight" and invalid.
    Valid ranges: exactly 0.5%, or >= 0.7% and <= 10%.

    Args:
        entry: Entry price
        stop: Stop-loss price

    Raises:
        PositionPlanningError: If stop distance is not exactly 0.5% or not in range 0.7%-10%

    From: specs/stop-loss-automation/tasks.md T024, T011
    """
    EXACT_MIN_STOP_DISTANCE_PCT = Decimal("0.5")
    SAFE_MIN_STOP_DISTANCE_PCT = Decimal("0.7")
    MAX_STOP_DISTANCE_PCT = Decimal("10.0")

    stop_distance = entry - stop
    stop_distance_pct = (stop_distance / entry) * Decimal("100")

    # Special case: exactly 0.5% is allowed (boundary condition)
    if stop_distance_pct == EXACT_MIN_STOP_DISTANCE_PCT:
        return

    # Dead zone: between 0.5% and 0.7% is invalid (too tight, noise-prone)
    if stop_distance_pct < SAFE_MIN_STOP_DISTANCE_PCT:
        raise PositionPlanningError(
            f"Stop distance {stop_distance_pct:.2f}% is too tight (minimum: exactly 0.5% or >= 0.7%)"
        )

    # Maximum bound
    if stop_distance_pct > MAX_STOP_DISTANCE_PCT:
        raise PositionPlanningError(
            f"Stop distance {stop_distance_pct:.2f}% is above maximum {MAX_STOP_DISTANCE_PCT}%"
        )


def validate_stop_direction(entry: Decimal, stop: Decimal, position_type: str) -> None:
    """
    Validate that stop price is in correct direction relative to entry.

    For long positions, stop must be below entry price to protect against downside.

    Args:
        entry: Entry price
        stop: Stop-loss price
        position_type: Position type ("long" or "short")

    Raises:
        PositionPlanningError: If stop is not below entry for long positions

    From: specs/stop-loss-automation/tasks.md T024, spec.md FR-013
    """
    if position_type == "long" and stop >= entry:
        raise PositionPlanningError(
            "Stop price must be below entry for long positions"
        )


def validate_risk_reward_ratio(actual_rr: float, min_rr: float) -> None:
    """
    Validate that actual risk-reward ratio meets minimum requirement.

    Args:
        actual_rr: Actual risk-reward ratio
        min_rr: Minimum required risk-reward ratio

    Raises:
        PositionPlanningError: If actual_rr is below min_rr

    From: specs/stop-loss-automation/tasks.md T024, spec.md FR-006
    """
    if actual_rr < min_rr:
        raise PositionPlanningError(
            f"Risk-reward ratio {actual_rr} below minimum {min_rr}"
        )


def calculate_position_size(
    risk_amount: Decimal, entry_price: Decimal, stop_loss: Decimal
) -> int:
    """Calculate position size based on risk parameters.

    Args:
        risk_amount: Maximum dollar risk for the position
        entry_price: Intended entry price
        stop_loss: Stop-loss price

    Returns:
        Number of shares to buy
    """
    risk_per_share = abs(entry_price - stop_loss)
    if risk_per_share == 0:
        return 0

    return int(risk_amount / risk_per_share)


def calculate_risk_reward_ratio(
    entry_price: Decimal, stop_loss: Decimal, target_price: Decimal
) -> float:
    """Calculate risk/reward ratio for a trade.

    Args:
        entry_price: Entry price
        stop_loss: Stop-loss price
        target_price: Target price

    Returns:
        Risk/reward ratio (reward / risk)
    """
    risk = abs(entry_price - stop_loss)
    reward = abs(target_price - entry_price)

    if risk == 0:
        return 0.0

    return float(reward / risk)


def validate_risk_limits(
    position_value: Decimal,
    account_value: Decimal,
    max_risk_pct: float,
) -> bool:
    """Validate position doesn't exceed risk limits.

    Args:
        position_value: Total value of position
        account_value: Total account value
        max_risk_pct: Maximum risk percentage allowed

    Returns:
        True if within risk limits
    """
    if account_value == 0:
        return False

    risk_pct = float(position_value / account_value * 100)
    return risk_pct <= max_risk_pct


def _calculate_shares(
    entry_price: Decimal,
    stop_price: Decimal,
    account_balance: Decimal,
    risk_pct: float
) -> tuple[int, Decimal]:
    """
    Calculate position size (shares) and risk amount based on risk parameters.

    Private helper method for calculate_position_plan(). Extracts steps 1-3
    of position planning to enforce single responsibility principle.

    Args:
        entry_price: Entry price per share
        stop_price: Stop-loss price per share
        account_balance: Total account balance
        risk_pct: Maximum risk percentage (e.g., 1.0 for 1%)

    Returns:
        Tuple of (quantity, risk_amount):
        - quantity: Number of shares to buy
        - risk_amount: Dollar amount at risk for this position

    From: specs/stop-loss-automation/tasks.md T031
    """
    # Step 1: Calculate risk per share
    risk_per_share = entry_price - stop_price

    # Step 2: Calculate risk amount (account_balance * risk_pct / 100)
    risk_amount = account_balance * (Decimal(str(risk_pct)) / Decimal("100"))

    # Step 3: Calculate quantity (int(risk_amount / risk_per_share))
    quantity = int(risk_amount / risk_per_share)

    return quantity, risk_amount


def calculate_position_plan(
    symbol: str,
    entry_price: Decimal,
    stop_price: Decimal,
    target_rr: float,
    account_balance: Decimal,
    risk_pct: float,
    min_risk_reward_ratio: float = 2.0,
    pullback_source: str = "manual",
    atr_data: Optional[ATRStopData] = None
) -> PositionPlan:
    """
    Calculate position plan with risk-based sizing and 2:1 targets.

    Args:
        symbol: Stock symbol
        entry_price: Entry price per share
        stop_price: Stop-loss price per share
        target_rr: Target risk-reward ratio (e.g., 2.0 for 2:1)
        account_balance: Total account balance
        risk_pct: Maximum risk percentage (e.g., 1.0 for 1%)
        min_risk_reward_ratio: Minimum allowed risk-reward ratio (default: 2.0)
        pullback_source: Source of stop price ("manual", "pullback", "atr")
        atr_data: Optional ATR-based stop data (sets pullback_source="atr" if provided)

    Returns:
        PositionPlan with calculated quantities, prices, and risk metrics

    Raises:
        PositionPlanningError: If target_rr is below min_risk_reward_ratio

    From: specs/stop-loss-automation/tasks.md T023, T013
          specs/atr-stop-adjustment/tasks.md T018
    """
    # Validation: Enforce minimum risk-reward ratio (T013)
    validate_risk_reward_ratio(target_rr, min_risk_reward_ratio)

    # Validation: Stop price must be below entry for long positions (T012)
    validate_stop_direction(entry_price, stop_price, position_type="long")

    # Validation: Stop distance bounds (T011)
    validate_stop_distance(entry_price, stop_price)

    # Calculate position size and risk amount (extracted to separate method)
    quantity, risk_amount = _calculate_shares(
        entry_price=entry_price,
        stop_price=stop_price,
        account_balance=account_balance,
        risk_pct=risk_pct
    )

    # Calculate risk per share for target calculation
    risk_per_share = entry_price - stop_price

    # Step 4: Calculate target price (entry + (entry - stop) * target_rr)
    target_price = entry_price + (risk_per_share * Decimal(str(target_rr)))

    # Step 5: Calculate reward amount (quantity * (target - entry))
    reward_amount = Decimal(str(quantity)) * (target_price - entry_price)

    # Step 6: Calculate actual reward ratio (reward_amount / risk_amount)
    actual_reward_ratio = float(reward_amount / risk_amount)

    # ATR integration: Override pullback_source if ATR data provided
    if atr_data is not None:
        pullback_source = "atr"

    return PositionPlan(
        symbol=symbol,
        entry_price=entry_price,
        stop_price=stop_price,
        target_price=target_price,
        quantity=quantity,
        risk_amount=risk_amount,
        reward_amount=reward_amount,
        reward_ratio=actual_reward_ratio,
        pullback_source=pullback_source,
        pullback_price=stop_price
    )
