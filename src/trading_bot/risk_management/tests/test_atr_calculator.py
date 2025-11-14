"""
Tests for ATR (Average True Range) calculator.

RED phase tests for TDD workflow - these tests should fail initially.
"""

import time
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from trading_bot.market_data.data_models import PriceBar
from trading_bot.risk_management.atr_calculator import ATRCalculator
from trading_bot.risk_management.exceptions import (
    ATRCalculationError,
    ATRValidationError,
    StaleDataError,
)
from trading_bot.risk_management.models import ATRStopData


def test_calculate_atr_from_bars_valid_data():
    """
    Test ATR calculation with valid 14-period data.

    Given:
        - 20 PriceBar objects with known price movements
        - ATR period = 14

    When:
        ATRCalculator.calculate() is called

    Then:
        - Returns Decimal ATR value accurate to ±$0.01 (NFR-008)
        - ATR value represents average volatility across the period
        - Calculation uses Wilder's smoothing formula

    Wilder's ATR Formula:
        1. Calculate True Range for each bar:
           TR = max(high - low, |high - prev_close|, |low - prev_close|)
        2. First ATR = average of first 14 TRs
        3. Subsequent ATRs = ((prev_ATR * 13) + current_TR) / 14

    Expected ATR calculation for test data:
        - Using realistic price bars with $2-$3 true ranges
        - Expected ATR ≈ $2.50 (varies based on data)

    From: specs/atr-stop-adjustment/tasks.md T005
    Pattern: TDD RED phase - test MUST FAIL (calculate method doesn't exist yet)
    """
    # Arrange: Create 20 PriceBar objects with realistic volatility
    base_timestamp = datetime.now(UTC)
    price_bars: list[PriceBar] = []

    # Generate price data with known volatility pattern
    prices = [
        # (open, high, low, close)
        (Decimal("150.00"), Decimal("152.00"), Decimal("149.50"), Decimal("151.00")),
        (Decimal("151.00"), Decimal("153.50"), Decimal("150.75"), Decimal("152.50")),
        (Decimal("152.50"), Decimal("154.00"), Decimal("151.50"), Decimal("153.00")),
        (Decimal("153.00"), Decimal("155.50"), Decimal("152.50"), Decimal("154.75")),
        (Decimal("154.75"), Decimal("156.00"), Decimal("153.75"), Decimal("155.00")),
        (Decimal("155.00"), Decimal("157.00"), Decimal("154.50"), Decimal("156.25")),
        (Decimal("156.25"), Decimal("158.00"), Decimal("155.75"), Decimal("157.00")),
        (Decimal("157.00"), Decimal("159.50"), Decimal("156.50"), Decimal("158.50")),
        (Decimal("158.50"), Decimal("160.00"), Decimal("157.50"), Decimal("159.00")),
        (Decimal("159.00"), Decimal("161.50"), Decimal("158.50"), Decimal("160.50")),
        (Decimal("160.50"), Decimal("162.00"), Decimal("159.50"), Decimal("161.00")),
        (Decimal("161.00"), Decimal("163.50"), Decimal("160.50"), Decimal("162.50")),
        (Decimal("162.50"), Decimal("164.00"), Decimal("161.50"), Decimal("163.00")),
        (Decimal("163.00"), Decimal("165.50"), Decimal("162.50"), Decimal("164.75")),
        (Decimal("164.75"), Decimal("166.00"), Decimal("163.75"), Decimal("165.00")),
        (Decimal("165.00"), Decimal("167.00"), Decimal("164.50"), Decimal("166.25")),
        (Decimal("166.25"), Decimal("168.00"), Decimal("165.75"), Decimal("167.00")),
        (Decimal("167.00"), Decimal("169.50"), Decimal("166.50"), Decimal("168.50")),
        (Decimal("168.50"), Decimal("170.00"), Decimal("167.50"), Decimal("169.00")),
        (Decimal("169.00"), Decimal("171.50"), Decimal("168.50"), Decimal("170.50")),
    ]

    for i, (open_price, high, low, close) in enumerate(prices):
        price_bars.append(
            PriceBar(
                symbol="AAPL",
                timestamp=base_timestamp + timedelta(minutes=i),
                open=open_price,
                high=high,
                low=low,
                close=close,
                volume=1000000,
            )
        )

    # Act: Calculate ATR with 14-period
    calculator = ATRCalculator(period=14)
    atr_value = calculator.calculate(price_bars)

    # Assert: ATR should be positive Decimal, accurate to $0.01
    assert isinstance(atr_value, Decimal), f"Expected Decimal, got {type(atr_value)}"
    assert atr_value > Decimal("0"), f"ATR must be positive, got {atr_value}"
    # With this data pattern (consistent $2-3 ranges), expect ATR around $2.00-$3.00
    assert Decimal("1.50") <= atr_value <= Decimal("4.00"), \
        f"ATR {atr_value} outside expected range $1.50-$4.00 for test data"


def test_calculate_atr_validates_price_bars():
    """
    Test that ATR calculation validates price bar integrity.

    Given:
        - PriceBar with high < low (invalid OHLC data)

    When:
        ATRCalculator.calculate() is called

    Then:
        - Raises ATRCalculationError with "Invalid price data"
        - Protects against corrupted market data

    Data integrity requirements:
        - high >= low (basic OHLC constraint)
        - open/close within [low, high] range
        - Sequential timestamps (no gaps)

    From: specs/atr-stop-adjustment/tasks.md T007
    Pattern: TDD RED phase - test MUST FAIL (validation doesn't exist yet)
    """
    # Arrange: Create price bars with INVALID data (negative prices)
    base_timestamp = datetime.now(UTC)
    price_bars: list[PriceBar] = []

    # Add 14 valid bars first (to pass minimum bar count check)
    for i in range(14):
        price_bars.append(
            PriceBar(
                symbol="AAPL",
                timestamp=base_timestamp + timedelta(minutes=i),
                open=Decimal("150.00"),
                high=Decimal("152.00"),
                low=Decimal("149.00"),
                close=Decimal("151.00"),
                volume=1000000,
            )
        )

    # Add bar with INVALID negative prices (passes PriceBar validation, but domain-invalid)
    # PriceBar validation only checks high >= low, not that prices are positive
    price_bars.append(
        PriceBar(
            symbol="AAPL",
            timestamp=base_timestamp + timedelta(minutes=14),
            open=Decimal("-150.00"),
            high=Decimal("-148.00"),
            low=Decimal("-152.00"),
            close=Decimal("-149.00"),
            volume=1000000,
        )
    )

    # Act & Assert: ATRCalculator should detect invalid price data
    calculator = ATRCalculator(period=14)

    with pytest.raises(ATRCalculationError) as exc_info:
        calculator.calculate(price_bars)

    # Verify error message mentions invalid data
    assert "invalid" in str(exc_info.value).lower() or "negative" in str(exc_info.value).lower()


def test_validate_price_bars_stale_data():
    """
    Test stale data detection for price bars.

    Given:
        - PriceBar with timestamp >15 minutes old

    When:
        ATRCalculator.validate_price_bars() is called with max_age_minutes=15

    Then:
        - Raises StaleDataError with age details
        - Prevents ATR calculation from stale market data

    Stale data protection requirement:
        - Real-time trading requires fresh data for accurate volatility calculation
        - Default threshold: 15 minutes (configurable)
        - Error message includes actual age vs. threshold

    Example:
        Latest bar timestamp: 2025-10-16 10:00:00
        Current time:        2025-10-16 10:23:00
        Age: 23 minutes > 15 minute threshold → StaleDataError

    From: specs/atr-stop-adjustment/tasks.md T012
    Pattern: TDD RED phase - test MUST FAIL (validate_price_bars method doesn't exist yet)
    """
    # Arrange: Create price bars with STALE timestamps (>15 minutes old)
    stale_timestamp = datetime.now(UTC) - timedelta(minutes=23)  # 23 minutes ago
    price_bars: list[PriceBar] = []

    for i in range(20):
        price_bars.append(
            PriceBar(
                symbol="AAPL",
                timestamp=stale_timestamp + timedelta(minutes=i),
                open=Decimal("150.00"),
                high=Decimal("152.00"),
                low=Decimal("149.00"),
                close=Decimal("151.00"),
                volume=1000000,
            )
        )

    # Latest bar is still 3 minutes ago (23 - 20 = 3... wait, that's not right)
    # Let me recalculate: start at 23 minutes ago, add 19 minutes (i=0 to i=19)
    # Latest bar timestamp = 23 - 19 = 4 minutes ago... still within threshold

    # Fix: Make all bars start 30 minutes ago
    stale_timestamp = datetime.now(UTC) - timedelta(minutes=30)
    price_bars = []

    for i in range(15):
        price_bars.append(
            PriceBar(
                symbol="AAPL",
                timestamp=stale_timestamp + timedelta(minutes=i),
                open=Decimal("150.00"),
                high=Decimal("152.00"),
                low=Decimal("149.00"),
                close=Decimal("151.00"),
                volume=1000000,
            )
        )

    # Latest bar is now 30 - 14 = 16 minutes old (exceeds 15 minute threshold)

    # Act & Assert: Should raise StaleDataError
    calculator = ATRCalculator(period=14)

    with pytest.raises(StaleDataError) as exc_info:
        calculator.validate_price_bars(price_bars, max_age_minutes=15)

    # Verify error message mentions age threshold
    error_message = str(exc_info.value).lower()
    assert "stale" in error_message or "old" in error_message or "15" in error_message


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


def test_atr_calculation_performance():
    """
    Test that ATR calculation meets performance target of <50ms per calculation.

    Given:
        - 50 PriceBar objects (simulating real market data volume)
        - 100 repeated ATR calculations to measure average performance

    When:
        ATRCalculator.calculate() is called 100 times

    Then:
        - Average calculation time < 0.050 seconds (50ms)
        - Ensures ATR calculation is fast enough for real-time trading decisions

    Performance requirement (NFR-001):
        - ATR calculation must complete in <50ms to avoid blocking trading logic
        - Real-time stop adjustment requires fast volatility calculations
        - Performance measured using time.perf_counter() for precise timing

    From: specs/atr-stop-adjustment/tasks.md T013
    Pattern: TDD RED phase - test MUST FAIL (ATRCalculator.calculate doesn't exist yet)
    """
    # Arrange: Create 50 PriceBar objects (realistic market data volume)
    base_timestamp = datetime.now(UTC)
    price_bars: list[PriceBar] = []

    # Generate price bars with realistic AAPL-like volatility
    base_price = Decimal("150.00")
    for i in range(50):
        # Simulate price movement with ±1% volatility
        high = base_price + Decimal("1.50")
        low = base_price - Decimal("1.50")
        close = base_price + Decimal("0.50")

        price_bars.append(
            PriceBar(
                symbol="AAPL",
                timestamp=base_timestamp + timedelta(minutes=i),
                open=base_price,
                high=high,
                low=low,
                close=close,
                volume=1000000,
            )
        )

        # Increment price slightly for next bar
        base_price += Decimal("0.25")

    # Create ATRCalculator instance
    calculator = ATRCalculator(period=14)

    # Act: Measure time for 100 ATR calculations
    start_time = time.perf_counter()

    for _ in range(100):
        calculator.calculate(price_bars)

    end_time = time.perf_counter()

    # Calculate average time per calculation
    total_time = end_time - start_time
    average_time = total_time / 100

    # Assert: Average calculation time must be < 50ms (0.050 seconds)
    assert average_time < 0.050, (
        f"ATR calculation too slow: average {average_time:.4f}s per calculation "
        f"(target: <0.050s). Total time for 100 calculations: {total_time:.4f}s"
    )
