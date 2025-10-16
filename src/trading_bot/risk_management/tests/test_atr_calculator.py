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
