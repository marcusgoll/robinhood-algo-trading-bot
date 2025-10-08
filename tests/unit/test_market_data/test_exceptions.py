"""
Unit tests for market data exceptions
"""
import pytest
from trading_bot.error_handling.exceptions import NonRetriableError


# T010 [RED]: Write failing test for DataValidationError inheritance
def test_data_validation_error_inheritance():
    """Test that DataValidationError is a NonRetriableError."""
    from trading_bot.market_data.exceptions import DataValidationError

    error = DataValidationError("Test validation error")

    assert isinstance(error, NonRetriableError)
    assert str(error) == "Test validation error"


# T012 [RED]: Write failing test for TradingHoursError inheritance
def test_trading_hours_error_inheritance():
    """Test that TradingHoursError is a NonRetriableError."""
    from trading_bot.market_data.exceptions import TradingHoursError

    error = TradingHoursError("Test trading hours error")

    assert isinstance(error, NonRetriableError)
    assert str(error) == "Test trading hours error"
