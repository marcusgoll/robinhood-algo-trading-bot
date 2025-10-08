"""
Market Data Validators

Validation functions for prices, timestamps, quotes, and historical data.
"""
from datetime import datetime, timezone
from typing import Dict, Any
import pandas as pd

from trading_bot.market_data.exceptions import DataValidationError


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
    # Check required fields
    required_fields = ['symbol', 'price', 'timestamp', 'market_state']
    for field in required_fields:
        if field not in data:
            raise DataValidationError(f"Missing required field: {field}")

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
    # Check required columns
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

    # Check for date continuity (detect gaps)
    df_sorted = df.sort_values('date')
    dates = pd.to_datetime(df_sorted['date'])

    # Calculate expected number of days (accounting for weekends)
    if len(dates) > 1:
        date_range = pd.date_range(start=dates.iloc[0], end=dates.iloc[-1], freq='D')
        # Filter to business days only (Mon-Fri)
        business_days = date_range[date_range.dayofweek < 5]

        # Allow some missing days for holidays (up to 10% gaps)
        expected_days = len(business_days)
        actual_days = len(dates)
        gap_count = expected_days - actual_days

        if gap_count > expected_days * 0.1:  # More than 10% missing
            raise DataValidationError(
                f"Missing dates detected: {gap_count} gaps in {expected_days} expected business days"
            )
