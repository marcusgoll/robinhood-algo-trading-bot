"""
Market Data Validators

Validation functions for prices, timestamps, quotes, and historical data.
"""
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import pandas as pd

from trading_bot.market_data.exceptions import DataValidationError, TradingHoursError


# T028: Common validation helpers
def _check_required_fields(data: Dict[str, Any], required_fields: list[str]) -> None:
    """
    Check that all required fields are present in data dictionary.

    Args:
        data: Dictionary to check
        required_fields: List of required field names

    Raises:
        DataValidationError: If any required field is missing
    """
    for field in required_fields:
        if field not in data:
            raise DataValidationError(f"Missing required field: {field}")


def _check_date_continuity(df: pd.DataFrame, date_column: str = 'date', max_gap_ratio: float = 0.1) -> None:
    """
    Check for excessive gaps in date series (for business days).

    Args:
        df: DataFrame with date column
        date_column: Name of the date column
        max_gap_ratio: Maximum allowed ratio of missing days (default 0.1 = 10%)

    Raises:
        DataValidationError: If gaps exceed threshold
    """
    df_sorted = df.sort_values(date_column)
    dates = pd.to_datetime(df_sorted[date_column])

    # Calculate expected number of days (accounting for weekends)
    if len(dates) > 1:
        date_range = pd.date_range(start=dates.iloc[0], end=dates.iloc[-1], freq='D')
        # Filter to business days only (Mon-Fri)
        business_days = date_range[date_range.dayofweek < 5]

        # Allow some missing days for holidays (up to max_gap_ratio)
        expected_days = len(business_days)
        actual_days = len(dates)
        gap_count = expected_days - actual_days

        if gap_count > expected_days * max_gap_ratio:
            raise DataValidationError(
                f"Missing dates detected: {gap_count} gaps in {expected_days} expected business days"
            )


# T017: Implement validate_price
def validate_price(price: float) -> None:
    """
    Validate that a price is positive.

    Args:
        price: Price value to validate

    Raises:
        DataValidationError: If price is <= 0
    """
    if price <= 0:
        raise DataValidationError(f"Price must be > 0, got {price}")


# T021: Implement validate_timestamp
def validate_timestamp(timestamp: datetime, max_age_seconds: int = 300) -> None:
    """
    Validate that a timestamp is UTC and not stale.

    Args:
        timestamp: Timestamp to validate
        max_age_seconds: Maximum age in seconds (default 300 = 5 minutes)

    Raises:
        DataValidationError: If timestamp is not UTC or is stale
    """
    # Check if timestamp has timezone info and is UTC
    if timestamp.tzinfo is None:
        raise DataValidationError(f"Timestamp must have UTC timezone, got naive datetime")

    if timestamp.tzinfo != timezone.utc:
        raise DataValidationError(f"Timestamp must be UTC, got {timestamp.tzinfo}")

    # Check if timestamp is recent enough
    now_utc = datetime.now(timezone.utc)
    age_seconds = (now_utc - timestamp).total_seconds()

    if age_seconds > max_age_seconds:
        raise DataValidationError(
            f"Timestamp is stale: {age_seconds:.0f}s old (max {max_age_seconds}s)"
        )

    # Also reject future timestamps (clock skew)
    if age_seconds < -60:  # Allow 60s clock skew
        raise DataValidationError(f"Timestamp is in the future: {timestamp}")


# T024: Implement validate_quote
def validate_quote(data: Dict[str, Any]) -> None:
    """
    Validate quote data dictionary.

    Args:
        data: Quote data dictionary with symbol, price, timestamp, market_state

    Raises:
        DataValidationError: If any required field is missing or invalid
    """
    # Check required fields using helper (T028)
    required_fields = ['symbol', 'price', 'timestamp', 'market_state']
    _check_required_fields(data, required_fields)

    # Validate price
    validate_price(data['price'])

    # Validate timestamp
    validate_timestamp(data['timestamp'])


# T027: Implement validate_historical_data
def validate_historical_data(df: pd.DataFrame) -> None:
    """
    Validate historical OHLCV data.

    Args:
        df: DataFrame with date, open, high, low, close, volume columns

    Raises:
        DataValidationError: If data is incomplete or invalid
    """
    # Check required columns (using dict-like interface for consistency with helper)
    required_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise DataValidationError(f"Missing required columns: {missing_columns}")

    # Check for empty DataFrame
    if len(df) == 0:
        raise DataValidationError("Historical data is empty")

    # Validate OHLC prices
    for col in ['open', 'high', 'low', 'close']:
        for idx, price in df[col].items():
            try:
                validate_price(float(price))
            except DataValidationError as e:
                raise DataValidationError(f"Invalid {col} at row {idx}: {e}")

    # Validate volume >= 0
    if (df['volume'] < 0).any():
        raise DataValidationError("Volume cannot be negative")

    # Check for date continuity using helper (T028)
    _check_date_continuity(df, date_column='date', max_gap_ratio=0.1)


# T045-T051: Trading hours validation
def validate_trade_time(current_time: Optional[datetime] = None) -> None:
    """
    Validate that current time is within trading hours (7am-10am EST).

    Args:
        current_time: Optional datetime to check (defaults to now if not provided)

    Raises:
        TradingHoursError: If current time is outside trading hours
    """
    from trading_bot.utils.time_utils import is_trading_hours

    if not is_trading_hours("America/New_York", current_time):
        raise TradingHoursError("Trading blocked outside 7am-10am EST")
