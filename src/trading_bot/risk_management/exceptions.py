"""
Domain exceptions for risk management operations.

Follows error hierarchy from src/trading_bot/error_handling/exceptions.py:
- PositionPlanningError(NonRetriableError): Invalid risk parameters, fail fast
- StopPlacementError(RetriableError): Broker API failures on stop submission
- TargetAdjustmentError(RetriableError): Trailing stop modification failures
"""

from __future__ import annotations

from trading_bot.error_handling.exceptions import (
    NonRetriableError,
    RetriableError,
)


class PositionPlanningError(NonRetriableError):
    """
    Raised when risk parameters are invalid or stop distance validation fails.

    This is a NonRetriableError because it indicates invalid input that requires
    correction before retry. Common causes:
    - Invalid position size (negative, zero, or exceeds account balance)
    - Stop distance too tight (violates minimum distance rules)
    - Invalid risk percentage (outside 0-100% range)
    - Missing required parameters (entry_price, stop_price, account_size)

    Example:
        raise PositionPlanningError(
            "Stop distance 0.05 is below minimum 0.10 for AAPL"
        )
    """

    pass


class StopPlacementError(RetriableError):
    """
    Raised when broker API fails to accept or place stop order.

    This is a RetriableError because broker API failures are often transient:
    - Network timeouts during order submission
    - Broker server errors (5xx responses)
    - Rate limiting on order placement endpoints
    - Temporary market data unavailability

    Example:
        raise StopPlacementError(
            "Failed to place stop order for AAPL: broker timeout after 30s"
        )
    """

    pass


class TargetAdjustmentError(RetriableError):
    """
    Raised when trailing stop cancellation or replacement fails.

    This is a RetriableError because adjustments can fail due to timing:
    - Order already filled before cancellation
    - Network errors during cancel/replace sequence
    - Broker rate limiting on modification requests
    - Transient order management system errors

    Example:
        raise TargetAdjustmentError(
            "Failed to trail stop for AAPL: cancel-replace sequence interrupted"
        )
    """

    pass


class ATRCalculationError(PositionPlanningError):
    """
    Raised when ATR calculation fails due to insufficient or invalid data.

    This is a NonRetriableError because it indicates data quality issues that
    require correction before retry. Common causes:
    - Insufficient price bars (need minimum period for ATR)
    - Invalid input data (NaN, negative prices, missing OHLC fields)
    - Empty price series or all-zero values
    - Mismatched data types or array lengths

    Example:
        raise ATRCalculationError(
            "ATR calculation requires 14 bars, got 5 for AAPL"
        )
    """

    pass


class ATRValidationError(PositionPlanningError):
    """
    Raised when ATR-based stop fails validation checks.

    This is a NonRetriableError because it indicates invalid risk parameters
    that require adjustment before retry. Common causes:
    - Stop distance exceeds maximum allowed range (out of bounds)
    - ATR multiplier produces stop too far from entry
    - Calculated stop violates minimum distance rules
    - Stale ATR value used in calculation

    Example:
        raise ATRValidationError(
            "ATR stop distance 5.2 exceeds maximum 3.0 for AAPL"
        )
    """

    pass


class StaleDataError(PositionPlanningError):
    """
    Raised when price data is too old for reliable ATR calculation.

    This is a NonRetriableError because it indicates data freshness issues
    that require new data before retry. Common causes:
    - Last price update timestamp exceeds staleness threshold
    - Market closed and no recent real-time data available
    - Data feed disconnected or delayed beyond acceptable limits
    - Using end-of-day data during trading hours

    Example:
        raise StaleDataError(
            "Price data for AAPL is 45 minutes old, max staleness is 5 minutes"
        )
    """

    pass
