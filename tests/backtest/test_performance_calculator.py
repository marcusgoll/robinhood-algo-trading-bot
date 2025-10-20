"""
Tests for PerformanceCalculator metric calculations.

Tests win rate, Sharpe ratio, maximum drawdown, and metrics accuracy.
Following TDD RED phase - tests written before PerformanceCalculator implementation.
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Tuple

# Import will FAIL because PerformanceCalculator doesn't exist yet (TDD RED phase)
from src.trading_bot.backtest.performance_calculator import PerformanceCalculator
from src.trading_bot.backtest.models import Trade, BacktestConfig


def test_drawdown_calculation():
    """
    Test maximum drawdown calculation with known peak-to-trough decline.

    Given: Equity curve with known drawdown
    - Start: $100,000
    - Peak: $110,000 (Feb 1)
    - Trough: $93,500 (Mar 15) - 15% drawdown from peak
    - Recovery: $105,000 (Apr 1)

    Expected:
    - Max drawdown = 15% (from peak $110k to trough $93.5k)
    - Max drawdown duration = 42 days (Feb 1 to Mar 15)

    This test validates:
    - Correct peak tracking
    - Accurate percentage calculation: (110000 - 93500) / 110000 = 0.15
    - Duration counting in calendar days
    """
    # Equity curve with known drawdown
    equity_curve = [
        (datetime(2023, 1, 1, tzinfo=timezone.utc), Decimal("100000")),  # Start
        (datetime(2023, 2, 1, tzinfo=timezone.utc), Decimal("110000")),  # Peak
        (datetime(2023, 3, 15, tzinfo=timezone.utc), Decimal("93500")),  # Trough (15% drawdown, 42 days)
        (datetime(2023, 4, 1, tzinfo=timezone.utc), Decimal("105000")),  # Recovery
    ]

    calculator = PerformanceCalculator()
    max_dd, max_dd_duration = calculator.calculate_max_drawdown(equity_curve)

    # Verify max drawdown percentage (15%)
    assert abs(max_dd - 0.15) < 0.001, f"Expected 15% drawdown, got {max_dd*100}%"

    # Verify max drawdown duration (42 days from Feb 1 to Mar 15)
    expected_duration = (datetime(2023, 3, 15) - datetime(2023, 2, 1)).days
    assert max_dd_duration == expected_duration, f"Expected {expected_duration} days duration, got {max_dd_duration}"
