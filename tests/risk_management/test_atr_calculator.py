"""
Tests for ATR (Average True Range) Calculator module.

Validates ATR calculation using Wilder's smoothing method with 14-period default.
ATR measures market volatility to set dynamic stop-loss distances.

From: specs/atr-stop-adjustment/tasks.md T005-T008
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from src.trading_bot.market_data.data_models import PriceBar
from src.trading_bot.risk_management.atr_calculator import ATRCalculator
from src.trading_bot.risk_management.exceptions import ATRCalculationError


def test_calculate_atr_from_bars_valid_data() -> None:
    """
    Test ATR calculation with valid 14-period price bar data.

    Given:
        - 15 PriceBar objects (14 periods + 1 for calculation)
        - Symbol: TSLA
        - Price data with realistic OHLC values
        - 14-period ATR calculation (Wilder's method)

    When:
        ATRCalculator.calculate_atr_from_bars(price_bars, period=14) is called

    Then:
        Returns Decimal ATR value > 0
        ATR represents average true range over 14 periods

    ATR Formula (Wilder's Smoothing):
        True Range (TR) = max(high - low, |high - prev_close|, |low - prev_close|)
        First ATR = average of first 14 TRs
        Subsequent ATR = ((prev_ATR * 13) + current_TR) / 14

    From: spec.md FR-014, tasks.md T005
    Pattern: TDD RED phase - test must FAIL until ATRCalculator implemented
    """
    # Arrange - Create 15 price bars with realistic TSLA data
    base_timestamp = datetime(2024, 1, 1, 9, 30, 0)  # Market open
    price_bars = []

    # Generate 15 bars with incrementing timestamps and realistic price action
    # Using realistic TSLA volatility patterns
    bar_data = [
        # (open, high, low, close, volume)
        (Decimal("250.00"), Decimal("252.50"), Decimal("249.00"), Decimal("251.00"), 1000000),
        (Decimal("251.00"), Decimal("253.00"), Decimal("250.50"), Decimal("252.50"), 1100000),
        (Decimal("252.50"), Decimal("254.00"), Decimal("251.00"), Decimal("253.00"), 1200000),
        (Decimal("253.00"), Decimal("255.50"), Decimal("252.50"), Decimal("254.50"), 1150000),
        (Decimal("254.50"), Decimal("256.00"), Decimal("253.00"), Decimal("255.00"), 1300000),
        (Decimal("255.00"), Decimal("257.00"), Decimal("254.00"), Decimal("256.50"), 1250000),
        (Decimal("256.50"), Decimal("258.50"), Decimal("255.50"), Decimal("257.00"), 1400000),
        (Decimal("257.00"), Decimal("259.00"), Decimal("256.00"), Decimal("258.00"), 1350000),
        (Decimal("258.00"), Decimal("260.00"), Decimal("257.00"), Decimal("259.50"), 1450000),
        (Decimal("259.50"), Decimal("261.50"), Decimal("258.50"), Decimal("260.00"), 1500000),
        (Decimal("260.00"), Decimal("262.00"), Decimal("259.00"), Decimal("261.00"), 1550000),
        (Decimal("261.00"), Decimal("263.00"), Decimal("260.00"), Decimal("262.50"), 1600000),
        (Decimal("262.50"), Decimal("264.50"), Decimal("261.50"), Decimal("263.00"), 1650000),
        (Decimal("263.00"), Decimal("265.00"), Decimal("262.00"), Decimal("264.00"), 1700000),
        (Decimal("264.00"), Decimal("266.00"), Decimal("263.00"), Decimal("265.50"), 1750000),
    ]

    for i, (open_price, high, low, close, volume) in enumerate(bar_data):
        timestamp = base_timestamp + timedelta(minutes=i)
        price_bars.append(
            PriceBar(
                symbol="TSLA",
                timestamp=timestamp,
                open=open_price,
                high=high,
                low=low,
                close=close,
                volume=volume,
            )
        )

    # Act
    atr_value = ATRCalculator.calculate_atr_from_bars(price_bars, period=14)

    # Assert
    assert isinstance(atr_value, Decimal), "ATR must be Decimal for precision"
    assert atr_value > Decimal("0"), f"ATR must be positive, got {atr_value}"
    # Expected ATR should be in range $2-$4 for TSLA with $3 average true range
    assert Decimal("1.5") < atr_value < Decimal("5.0"), (
        f"ATR {atr_value} outside expected range $1.5-$5.0 for TSLA volatility"
    )
