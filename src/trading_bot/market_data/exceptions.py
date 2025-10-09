"""
Market Data Exceptions

Custom exception classes for market data validation and trading hours enforcement.

All exceptions inherit from NonRetriableError since data validation and trading hours
violations should fail fast without retry.
"""

from trading_bot.error_handling.exceptions import NonRetriableError


class DataValidationError(NonRetriableError):
    """
    Raised when market data fails validation checks.

    This is a non-retriable error because invalid data (e.g., negative prices,
    missing timestamps, stale quotes) indicates a data quality issue that won't
    be resolved by retrying the same request.

    Examples:
        - Price <= 0
        - Timestamp not in UTC
        - Quote older than staleness threshold
        - Missing required fields
        - Historical data with date gaps

    Usage:
        if price <= 0:
            raise DataValidationError(f"Price must be > 0, got {price}")
    """
    pass


class TradingHoursError(NonRetriableError):
    """
    Raised when trading is attempted outside allowed hours (7am-10am EST).

    This is a non-retriable error because the trading window is a hard business
    rule that won't change by retrying. The bot must wait until the next
    trading window opens.

    Usage:
        if not is_trading_hours():
            raise TradingHoursError("Trading blocked outside 7am-10am EST")
    """
    pass
