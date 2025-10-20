"""
Domain exceptions for backtest operations.

Follows error hierarchy from src/trading_bot/error_handling/exceptions.py:
- BacktestException(NonRetriableError): Base exception for all backtest errors
- DataQualityError(BacktestException): Data validation failures, gaps, invalid prices
- InsufficientDataError(BacktestException): Not enough historical data for backtest
- StrategyError(BacktestException): Strategy execution errors
"""

from __future__ import annotations

from trading_bot.error_handling.exceptions import NonRetriableError


class BacktestException(NonRetriableError):
    """
    Base exception for all backtest-related errors.

    This is a NonRetriableError because backtest errors indicate configuration
    or data quality issues that require correction before retry. All backtest
    exceptions inherit from this base class.

    Common causes:
    - Invalid backtest configuration (negative capital, invalid date range)
    - Data quality issues (gaps, invalid prices, missing bars)
    - Strategy implementation errors (invalid signals, runtime errors)
    - Insufficient historical data for analysis

    Example:
        raise BacktestException("Backtest failed: invalid configuration")
    """

    pass


class DataQualityError(BacktestException):
    """
    Raised when historical data fails validation checks.

    This is a NonRetriableError because invalid data (e.g., negative prices,
    missing timestamps, data gaps) indicates a data quality issue that won't
    be resolved by retrying the same backtest.

    Common causes:
    - Price <= 0 or volume < 0
    - Missing OHLCV fields in historical bars
    - Data gaps exceeding acceptable threshold
    - Timestamps not in UTC or chronologically out of order
    - Invalid price relationships (high < low, close outside OHLC range)

    Example:
        raise DataQualityError(
            "Invalid price data for AAPL on 2023-06-15: close price -5.00 is negative"
        )
    """

    pass


class InsufficientDataError(BacktestException):
    """
    Raised when there is not enough historical data to run the backtest.

    This is a NonRetriableError because it indicates that the requested date
    range or data requirements cannot be satisfied with available data. The
    user must adjust the backtest configuration or wait for more data.

    Common causes:
    - Requested date range has too few trading days for strategy requirements
    - Strategy needs minimum lookback period not satisfied by available data
    - Symbol has insufficient trading history (e.g., recent IPO)
    - Data provider does not have data for requested date range

    Example:
        raise InsufficientDataError(
            "Strategy requires 50 bars for moving average, only 30 bars available for AAPL"
        )
    """

    pass


class StrategyError(BacktestException):
    """
    Raised when strategy execution fails during backtest.

    This is a NonRetriableError because it indicates an error in the strategy
    implementation that must be fixed before the backtest can succeed.

    Common causes:
    - Strategy does not implement required IStrategy protocol methods
    - should_enter() or should_exit() raises unhandled exception
    - Strategy returns invalid signal types (not bool)
    - Strategy attempts to access future data (look-ahead bias)
    - Runtime errors in custom strategy logic (division by zero, etc.)

    Example:
        raise StrategyError(
            "Strategy MomentumStrategy.should_enter() raised AttributeError: 'NoneType' has no attribute 'close'"
        )
    """

    pass
