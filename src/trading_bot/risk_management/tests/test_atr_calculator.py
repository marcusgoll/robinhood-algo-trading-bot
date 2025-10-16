"""
Tests for ATR (Average True Range) calculator.

RED phase tests for TDD workflow - these tests should fail initially.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from trading_bot.market_data.data_models import PriceBar
from trading_bot.risk_management.atr_calculator import ATRCalculator
from trading_bot.risk_management.exceptions import ATRCalculationError
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
