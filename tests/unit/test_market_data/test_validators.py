"""
Unit tests for market data validators
"""
import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import pandas as pd

from trading_bot.market_data.validators import (
    validate_price,
    validate_timestamp,
    validate_quote,
    validate_historical_data,
)
from trading_bot.market_data.exceptions import DataValidationError


# T014: Write failing test - validate_price rejects zero
def test_validate_price_rejects_zero():
    """Test that validate_price rejects price of zero."""
    with pytest.raises(DataValidationError, match="Price must be > 0"):
        validate_price(0.0)


# T015: Write failing test - validate_price rejects negative
def test_validate_price_rejects_negative():
    """Test that validate_price rejects negative prices."""
    with pytest.raises(DataValidationError, match="Price must be > 0"):
        validate_price(-1.0)

    with pytest.raises(DataValidationError, match="Price must be > 0"):
        validate_price(-150.25)


# T016: Write failing test - validate_price accepts positive
def test_validate_price_accepts_positive():
    """Test that validate_price accepts positive prices."""
    # Should not raise any exception
    validate_price(150.25)
    validate_price(0.01)
    validate_price(10000.99)


# T018: Write failing test - validate_timestamp rejects non-UTC
def test_validate_timestamp_rejects_non_utc():
    """Test that validate_timestamp rejects naive datetimes."""
    with pytest.raises(DataValidationError, match="must have UTC timezone"):
        validate_timestamp(datetime.now())  # Naive datetime


# T019: Write failing test - validate_timestamp rejects stale quotes
def test_validate_timestamp_rejects_stale():
    """Test that validate_timestamp rejects stale timestamps."""
    now_utc = datetime.now(timezone.utc)
    stale_time = now_utc - timedelta(minutes=10)

    with pytest.raises(DataValidationError, match="Timestamp is stale"):
        validate_timestamp(stale_time, max_age_seconds=300)


# T020: Write failing test - validate_timestamp accepts recent UTC
def test_validate_timestamp_accepts_recent_utc():
    """Test that validate_timestamp accepts recent UTC timestamps."""
    now_utc = datetime.now(timezone.utc)
    recent_time = now_utc - timedelta(minutes=1)

    # Should not raise
    validate_timestamp(recent_time, max_age_seconds=300)
    validate_timestamp(now_utc, max_age_seconds=300)


# T022: Write failing test - validate_quote with complete data
def test_validate_quote_with_complete_data():
    """Test that validate_quote accepts complete valid data."""
    now_utc = datetime.now(timezone.utc)
    quote_data = {
        'symbol': 'AAPL',
        'price': 150.25,
        'timestamp': now_utc,
        'market_state': 'regular'
    }

    # Should not raise
    validate_quote(quote_data)


# T023: Write failing test - validate_quote rejects missing fields
def test_validate_quote_rejects_missing_symbol():
    """Test that validate_quote rejects data with missing fields."""
    now_utc = datetime.now(timezone.utc)

    # Missing symbol
    with pytest.raises(DataValidationError, match="Missing required field: symbol"):
        validate_quote({'price': 150.25, 'timestamp': now_utc, 'market_state': 'regular'})

    # Missing price
    with pytest.raises(DataValidationError, match="Missing required field: price"):
        validate_quote({'symbol': 'AAPL', 'timestamp': now_utc, 'market_state': 'regular'})


# T025: Write failing test - validate_historical_data detects missing dates
def test_validate_historical_data_detects_gaps():
    """Test that validate_historical_data detects missing dates."""
    # Create DataFrame with gaps (missing many days)
    df = pd.DataFrame({
        'date': ['2025-01-01', '2025-01-03', '2025-01-10', '2025-01-20'],  # Many gaps
        'open': [150.0, 151.0, 152.0, 153.0],
        'high': [155.0, 156.0, 157.0, 158.0],
        'low': [149.0, 150.0, 151.0, 152.0],
        'close': [154.0, 155.0, 156.0, 157.0],
        'volume': [1000000, 1100000, 1200000, 1300000]
    })

    with pytest.raises(DataValidationError, match="Missing dates detected"):
        validate_historical_data(df)


# T026: Write failing test - validate_historical_data accepts complete data
def test_validate_historical_data_accepts_complete():
    """Test that validate_historical_data accepts complete consecutive data."""
    # Create DataFrame with consecutive business days
    dates = pd.date_range(start='2025-01-01', end='2025-01-31', freq='B')  # Business days
    df = pd.DataFrame({
        'date': dates,
        'open': [150.0 + i for i in range(len(dates))],
        'high': [155.0 + i for i in range(len(dates))],
        'low': [149.0 + i for i in range(len(dates))],
        'close': [154.0 + i for i in range(len(dates))],
        'volume': [1000000] * len(dates)
    })

    # Should not raise
    validate_historical_data(df)
