"""
Tests for ATR (Average True Range) calculator.

RED phase tests for TDD workflow - these tests should fail initially.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from trading_bot.market_data.data_models import PriceBar
from trading_bot.risk_management.atr_calculator import ATRCalculator
from trading_bot.risk_management.exceptions import ATRCalculationError, ATRValidationError
from trading_bot.risk_management.models import ATRStopData


def test_calculate_atr_insufficient_data():
    """
    Test that ATR calculation raises error when given insufficient data.

    ATR requires minimum 14 periods for calculation. This test verifies
    that attempting to calculate ATR with only 10 price bars raises
    ATRCalculationError.

    Expected behavior (RED phase - test should FAIL):
    - ATRCalculator doesn't exist yet
    - Test should fail with ImportError or AttributeError
    """
    # Create only 10 PriceBar objects (insufficient for 14-period ATR)
    base_timestamp = datetime.now(UTC)
    price_bars: list[PriceBar] = []

    for i in range(10):
        price_bars.append(
            PriceBar(
                symbol="AAPL",
                timestamp=base_timestamp + timedelta(minutes=i),
                open=Decimal("150.00"),
                high=Decimal("151.00"),
                low=Decimal("149.00"),
                close=Decimal("150.50"),
                volume=1000000,
            )
        )

    # ATRCalculator should raise ATRCalculationError for insufficient data
    calculator = ATRCalculator(period=14)

    with pytest.raises(ATRCalculationError) as exc_info:
        calculator.calculate(price_bars)

    # Verify error message mentions insufficient data
    assert "insufficient" in str(exc_info.value).lower() or "14" in str(exc_info.value)


def test_calculate_atr_stop_long_position():
    """
    Test ATR stop calculation for long position.

    Given:
        - entry_price = $250.00
        - atr_value = $5.00
        - multiplier = 2.0
        - position_type = "long"

    When:
        ATRCalculator.calculate_atr_stop() is called

    Then:
        Returns ATRStopData with:
        - stop_price = $240.00 (entry - atr_value * multiplier)
        - atr_value = $5.00
        - atr_multiplier = 2.0
        - atr_period = 14 (default)

    Calculation:
        stop_price = entry_price - (atr_value * multiplier)
                   = $250.00 - ($5.00 * 2.0)
                   = $250.00 - $10.00
                   = $240.00

    From: specs/atr-stop-adjustment/tasks.md T008
    Pattern: TDD RED phase - test MUST FAIL (method doesn't exist yet)
    """
    # Arrange
    entry_price = Decimal("250.00")
    atr_value = Decimal("5.00")
    multiplier = 2.0
    position_type = "long"
    atr_period = 14

    # Act
    result = ATRCalculator.calculate_atr_stop(
        entry_price=entry_price,
        atr_value=atr_value,
        multiplier=multiplier,
        position_type=position_type,
        atr_period=atr_period
    )

    # Assert
    assert isinstance(result, ATRStopData), "Should return ATRStopData instance"
    assert result.stop_price == Decimal("240.00"), f"Expected stop at $240.00, got ${result.stop_price}"
    assert result.atr_value == Decimal("5.00"), f"Expected ATR $5.00, got ${result.atr_value}"
    assert result.atr_multiplier == 2.0, f"Expected multiplier 2.0, got {result.atr_multiplier}"
    assert result.atr_period == 14, f"Expected period 14, got {result.atr_period}"
    assert result.source == "atr", f"Expected source 'atr', got '{result.source}'"


def test_atr_stop_validation_min_distance():
    """
    Test that ATR stop validation rejects stop distance below 0.7% minimum.

    Given:
        - entry_price = $250.00
        - atr_value = $0.50
        - multiplier = 2.0
        - position_type = "long"
        - Calculated stop = $249.00 (entry - atr * multiplier)
        - Stop distance = $1.00 / $250.00 = 0.4% (BELOW 0.7% minimum)

    When:
        ATRCalculator.validate_atr_stop() is called

    Then:
        Raises ATRValidationError with message mentioning "0.7% minimum"

    Risk management safety requirement:
        - Stops must be at least 0.7% away from entry
        - Prevents stops too tight to accommodate normal price volatility
        - Reduces risk of premature stop-out due to bid-ask spread or minor fluctuations

    Calculation:
        stop_price = entry_price - (atr_value * multiplier)
                   = $250.00 - ($0.50 * 2.0)
                   = $250.00 - $1.00
                   = $249.00
        stop_distance_pct = abs(entry_price - stop_price) / entry_price * 100
                          = abs($250.00 - $249.00) / $250.00 * 100
                          = $1.00 / $250.00 * 100
                          = 0.4%
        VALIDATION FAILS: 0.4% < 0.7% minimum

    From: specs/atr-stop-adjustment/tasks.md T009
    Pattern: TDD RED phase - test MUST FAIL (validate_atr_stop method doesn't exist yet)
    """
    # Arrange
    entry_price = Decimal("250.00")
    atr_value = Decimal("0.50")
    multiplier = 2.0
    position_type = "long"

    # Calculate expected stop (too tight)
    expected_stop = Decimal("249.00")  # 0.4% distance - below 0.7% minimum

    # Act & Assert
    with pytest.raises(ATRValidationError) as exc_info:
        ATRCalculator.validate_atr_stop(
            entry_price=entry_price,
            stop_price=expected_stop,
            atr_value=atr_value,
            multiplier=multiplier,
            position_type=position_type
        )

    # Verify error message mentions minimum distance
    error_message = str(exc_info.value).lower()
    assert "0.7" in error_message or "0.007" in error_message, \
        f"Error message should mention 0.7% minimum, got: {exc_info.value}"
    assert "minimum" in error_message, \
        f"Error message should mention 'minimum', got: {exc_info.value}"


def test_atr_stop_validation_max_distance():
    """
    Test that ATR stop validation rejects stop distance exceeding 10% maximum.

    Given:
        - entry_price = $250.00
        - atr_value = $15.00
        - multiplier = 2.0
        - position_type = "long"

    When:
        ATRCalculator.validate_atr_stop() is called

    Then:
        Raises ATRValidationError because stop distance exceeds 10% maximum

    Calculation:
        stop_price = entry_price - (atr_value * multiplier)
                   = $250.00 - ($15.00 * 2.0)
                   = $250.00 - $30.00
                   = $220.00

        stop_distance = (entry_price - stop_price) / entry_price
                      = ($250.00 - $220.00) / $250.00
                      = $30.00 / $250.00
                      = 0.12 (12%)

    Validation: 12% > 10% maximum → REJECT

    From: specs/atr-stop-adjustment/tasks.md T010
    Pattern: TDD RED phase - test MUST FAIL (validation method doesn't exist yet)
    """
    # Arrange
    entry_price = Decimal("250.00")
    atr_value = Decimal("15.00")
    multiplier = 2.0
    position_type = "long"
    stop_price = Decimal("220.00")  # 12% distance - TOO WIDE

    # Act & Assert
    with pytest.raises(ATRValidationError) as exc_info:
        ATRCalculator.validate_atr_stop(
            entry_price=entry_price,
            stop_price=stop_price,
            position_type=position_type
        )

    # Verify error message mentions 10% maximum
    error_message = str(exc_info.value).lower()
    assert "10%" in error_message or "maximum" in error_message, (
        f"Error message should mention 10% maximum, got: {exc_info.value}"
    )
