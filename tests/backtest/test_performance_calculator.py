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


def test_sharpe_ratio_calculation():
    """
    Test Sharpe ratio calculation with sample equity curve.

    The Sharpe ratio measures risk-adjusted return:
    Formula: (annualized_return - risk_free_rate) / annualized_volatility

    Given: Monthly equity curve data for 1 year (13 data points)
    - Returns vary from -1.5% to +3% monthly
    - Risk-free rate: 2% annual (0.02)
    - Expected: Positive Sharpe ratio (strategy outperforms risk-free rate)

    This test validates:
    - Correct return calculation from equity curve
    - Annualization of returns and volatility
    - Risk-adjusted return formula
    - Reasonable Sharpe ratio range (-3 to 3)

    Expected to FAIL until PerformanceCalculator.calculate_sharpe_ratio() is implemented.
    """
    # Sample equity curve with monthly data points
    # Monthly returns: +2%, +2.94%, +1%, -1.5%, +3%, +2%, +1.51%, -0.5%, +2.5%, +1%, +2%, +1.8%
    # Total return: ~19.15% over 12 months
    equity_curve = [
        (datetime(2023, 1, 1, tzinfo=timezone.utc), Decimal("100000.00")),   # Start
        (datetime(2023, 2, 1, tzinfo=timezone.utc), Decimal("102000.00")),   # +2.00%
        (datetime(2023, 3, 1, tzinfo=timezone.utc), Decimal("105000.00")),   # +2.94%
        (datetime(2023, 4, 1, tzinfo=timezone.utc), Decimal("106050.00")),   # +1.00%
        (datetime(2023, 5, 1, tzinfo=timezone.utc), Decimal("104459.25")),   # -1.50%
        (datetime(2023, 6, 1, tzinfo=timezone.utc), Decimal("107593.03")),   # +3.00%
        (datetime(2023, 7, 1, tzinfo=timezone.utc), Decimal("109744.89")),   # +2.00%
        (datetime(2023, 8, 1, tzinfo=timezone.utc), Decimal("111401.06")),   # +1.51%
        (datetime(2023, 9, 1, tzinfo=timezone.utc), Decimal("110844.06")),   # -0.50%
        (datetime(2023, 10, 1, tzinfo=timezone.utc), Decimal("113615.16")),  # +2.50%
        (datetime(2023, 11, 1, tzinfo=timezone.utc), Decimal("114751.31")),  # +1.00%
        (datetime(2023, 12, 1, tzinfo=timezone.utc), Decimal("117046.34")),  # +2.00%
        (datetime(2024, 1, 1, tzinfo=timezone.utc), Decimal("119153.17")),   # +1.80%
    ]

    # Risk-free rate: 2% annual (typical U.S. Treasury bill rate)
    risk_free_rate = Decimal("0.02")

    calculator = PerformanceCalculator()
    sharpe = calculator.calculate_sharpe_ratio(equity_curve, risk_free_rate)

    # Verify Sharpe ratio is numeric
    assert isinstance(sharpe, (Decimal, float)), f"Sharpe ratio must be numeric, got {type(sharpe)}"

    # Verify Sharpe ratio is in reasonable range
    # Typical ranges for strategies:
    # < 0: Strategy underperforms risk-free rate
    # 0 - 1: Suboptimal (low risk-adjusted return)
    # 1 - 2: Good
    # 2 - 3: Very good
    # > 3: Excellent (rare, may indicate overfitting or data issues)
    assert -3 <= sharpe <= 3, f"Sharpe ratio out of expected range: {sharpe}"

    # Additional validation: positive equity curve should yield positive Sharpe
    # (given total return ~19% > risk-free rate 2%)
    assert sharpe > 0, f"Sharpe ratio should be positive for profitable strategy, got {sharpe}"

    # Verify Sharpe is at least moderately good (> 1.0) for this positive return series
    assert sharpe > 1.0, f"Expected Sharpe > 1.0 for 19% return strategy, got {sharpe}"
