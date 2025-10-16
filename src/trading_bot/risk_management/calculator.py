"""Risk and position sizing calculations."""

from __future__ import annotations

from decimal import Decimal


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
