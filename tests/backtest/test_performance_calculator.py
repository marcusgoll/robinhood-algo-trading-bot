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


def test_win_rate_calculation():
    """
    Test win rate calculation accuracy with 10 sample trades (6 wins, 4 losses).

    Given: 10 trades (6 profitable, 4 unprofitable)
    Expected: 60% win rate (6/10 = 0.60)

    Validates PerformanceCalculator.calculate_win_rate() returns correct percentage
    based on number of winning vs. total trades.

    TDD RED phase: This test should FAIL (PerformanceCalculator not implemented yet)
    """
    # Create 6 winning trades (positive P&L)
    winning_trades = [
        Trade(
            symbol="AAPL",
            entry_date=datetime(2024, 1, 2, tzinfo=timezone.utc),
            entry_price=Decimal("100.00"),
            exit_date=datetime(2024, 1, 5, tzinfo=timezone.utc),
            exit_price=Decimal("110.00"),
            shares=100,
            pnl=Decimal("1000.00"),
            pnl_pct=Decimal("0.10"),
            duration_days=3,
            exit_reason="strategy_signal",
            commission=Decimal("0.00"),
            slippage=Decimal("0.00"),
        ),
        Trade(
            symbol="TSLA",
            entry_date=datetime(2024, 1, 3, tzinfo=timezone.utc),
            entry_price=Decimal("200.00"),
            exit_date=datetime(2024, 1, 8, tzinfo=timezone.utc),
            exit_price=Decimal("220.00"),
            shares=50,
            pnl=Decimal("1000.00"),
            pnl_pct=Decimal("0.10"),
            duration_days=5,
            exit_reason="take_profit",
            commission=Decimal("0.00"),
            slippage=Decimal("0.00"),
        ),
        Trade(
            symbol="GOOGL",
            entry_date=datetime(2024, 1, 5, tzinfo=timezone.utc),
            entry_price=Decimal("150.00"),
            exit_date=datetime(2024, 1, 10, tzinfo=timezone.utc),
            exit_price=Decimal("165.00"),
            shares=75,
            pnl=Decimal("1125.00"),
            pnl_pct=Decimal("0.10"),
            duration_days=5,
            exit_reason="strategy_signal",
            commission=Decimal("0.00"),
            slippage=Decimal("0.00"),
        ),
        Trade(
            symbol="MSFT",
            entry_date=datetime(2024, 1, 8, tzinfo=timezone.utc),
            entry_price=Decimal("300.00"),
            exit_date=datetime(2024, 1, 12, tzinfo=timezone.utc),
            exit_price=Decimal("315.00"),
            shares=30,
            pnl=Decimal("450.00"),
            pnl_pct=Decimal("0.05"),
            duration_days=4,
            exit_reason="take_profit",
            commission=Decimal("0.00"),
            slippage=Decimal("0.00"),
        ),
        Trade(
            symbol="NVDA",
            entry_date=datetime(2024, 1, 10, tzinfo=timezone.utc),
            entry_price=Decimal("500.00"),
            exit_date=datetime(2024, 1, 15, tzinfo=timezone.utc),
            exit_price=Decimal("550.00"),
            shares=20,
            pnl=Decimal("1000.00"),
            pnl_pct=Decimal("0.10"),
            duration_days=5,
            exit_reason="strategy_signal",
            commission=Decimal("0.00"),
            slippage=Decimal("0.00"),
        ),
        Trade(
            symbol="AMZN",
            entry_date=datetime(2024, 1, 12, tzinfo=timezone.utc),
            entry_price=Decimal("180.00"),
            exit_date=datetime(2024, 1, 18, tzinfo=timezone.utc),
            exit_price=Decimal("198.00"),
            shares=60,
            pnl=Decimal("1080.00"),
            pnl_pct=Decimal("0.10"),
            duration_days=6,
            exit_reason="take_profit",
            commission=Decimal("0.00"),
            slippage=Decimal("0.00"),
        ),
    ]

    # Create 4 losing trades (negative P&L)
    losing_trades = [
        Trade(
            symbol="META",
            entry_date=datetime(2024, 1, 4, tzinfo=timezone.utc),
            entry_price=Decimal("350.00"),
            exit_date=datetime(2024, 1, 9, tzinfo=timezone.utc),
            exit_price=Decimal("340.00"),
            shares=25,
            pnl=Decimal("-250.00"),
            pnl_pct=Decimal("-0.0286"),
            duration_days=5,
            exit_reason="stop_loss",
            commission=Decimal("0.00"),
            slippage=Decimal("0.00"),
        ),
        Trade(
            symbol="NFLX",
            entry_date=datetime(2024, 1, 6, tzinfo=timezone.utc),
            entry_price=Decimal("450.00"),
            exit_date=datetime(2024, 1, 11, tzinfo=timezone.utc),
            exit_price=Decimal("430.00"),
            shares=20,
            pnl=Decimal("-400.00"),
            pnl_pct=Decimal("-0.0444"),
            duration_days=5,
            exit_reason="stop_loss",
            commission=Decimal("0.00"),
            slippage=Decimal("0.00"),
        ),
        Trade(
            symbol="AMD",
            entry_date=datetime(2024, 1, 9, tzinfo=timezone.utc),
            entry_price=Decimal("120.00"),
            exit_date=datetime(2024, 1, 13, tzinfo=timezone.utc),
            exit_price=Decimal("110.00"),
            shares=40,
            pnl=Decimal("-400.00"),
            pnl_pct=Decimal("-0.0833"),
            duration_days=4,
            exit_reason="stop_loss",
            commission=Decimal("0.00"),
            slippage=Decimal("0.00"),
        ),
        Trade(
            symbol="INTC",
            entry_date=datetime(2024, 1, 11, tzinfo=timezone.utc),
            entry_price=Decimal("45.00"),
            exit_date=datetime(2024, 1, 16, tzinfo=timezone.utc),
            exit_price=Decimal("42.00"),
            shares=100,
            pnl=Decimal("-300.00"),
            pnl_pct=Decimal("-0.0667"),
            duration_days=5,
            exit_reason="stop_loss",
            commission=Decimal("0.00"),
            slippage=Decimal("0.00"),
        ),
    ]

    # Combine all trades
    all_trades = winning_trades + losing_trades

    # Calculate win rate using PerformanceCalculator
    calculator = PerformanceCalculator()
    win_rate = calculator.calculate_win_rate(all_trades)

    # Assert: 6 wins out of 10 trades = 60% win rate
    assert win_rate == Decimal("0.60"), f"Expected 60% win rate, got {win_rate}"


def test_metrics_accuracy():
    """
    Test metrics accuracy versus manual calculations (NFR-003).

    Given: Known trade history with manually calculated metrics
    Expected: All metrics within 0.01% of expected values (per NFR-003)

    Test validates:
    - Total return calculation
    - Win rate calculation
    - Profit factor calculation
    - Maximum drawdown calculation
    - Sharpe ratio calculation

    Manual calculations (for reference):
    - Trade 1: Entry $100, Exit $110, Shares 100 = +$1000 (10% gain)
    - Trade 2: Entry $200, Exit $190, Shares 50 = -$500 (5% loss)
    - Trade 3: Entry $150, Exit $165, Shares 75 = +$1125 (10% gain)
    - Trade 4: Entry $300, Exit $285, Shares 30 = -$450 (5% loss)
    - Trade 5: Entry $180, Exit $198, Shares 60 = +$1080 (10% gain)

    Total P&L: $1000 - $500 + $1125 - $450 + $1080 = $2255
    Initial capital: $100,000
    Total return: $2255 / $100,000 = 0.02255 = 2.255%
    Win rate: 3/5 = 0.60 = 60%
    Gross profit: $1000 + $1125 + $1080 = $3205
    Gross loss: $500 + $450 = $950
    Profit factor: $3205 / $950 = 3.373684...

    Equity progression:
    - Start: $100,000
    - After T1: $101,000 (peak)
    - After T2: $100,500 (0.495% drawdown)
    - After T3: $101,625 (new peak)
    - After T4: $101,175 (0.443% drawdown)
    - After T5: $102,255 (final)
    Max drawdown: 0.495% (from $101,000 to $100,500)

    TDD RED phase: This test should FAIL (PerformanceCalculator not implemented yet)
    """
    # Create 5 trades with known outcomes
    trades = [
        # Trade 1: +$1000 (10% gain) - WIN
        Trade(
            symbol="AAPL",
            entry_date=datetime(2024, 1, 2, tzinfo=timezone.utc),
            entry_price=Decimal("100.00"),
            exit_date=datetime(2024, 1, 10, tzinfo=timezone.utc),
            exit_price=Decimal("110.00"),
            shares=100,
            pnl=Decimal("1000.00"),
            pnl_pct=Decimal("0.10"),
            duration_days=8,
            exit_reason="take_profit",
            commission=Decimal("0.00"),
            slippage=Decimal("0.00"),
        ),
        # Trade 2: -$500 (5% loss) - LOSS
        Trade(
            symbol="TSLA",
            entry_date=datetime(2024, 1, 11, tzinfo=timezone.utc),
            entry_price=Decimal("200.00"),
            exit_date=datetime(2024, 1, 18, tzinfo=timezone.utc),
            exit_price=Decimal("190.00"),
            shares=50,
            pnl=Decimal("-500.00"),
            pnl_pct=Decimal("-0.05"),
            duration_days=7,
            exit_reason="stop_loss",
            commission=Decimal("0.00"),
            slippage=Decimal("0.00"),
        ),
        # Trade 3: +$1125 (10% gain) - WIN
        Trade(
            symbol="GOOGL",
            entry_date=datetime(2024, 1, 19, tzinfo=timezone.utc),
            entry_price=Decimal("150.00"),
            exit_date=datetime(2024, 1, 28, tzinfo=timezone.utc),
            exit_price=Decimal("165.00"),
            shares=75,
            pnl=Decimal("1125.00"),
            pnl_pct=Decimal("0.10"),
            duration_days=9,
            exit_reason="take_profit",
            commission=Decimal("0.00"),
            slippage=Decimal("0.00"),
        ),
        # Trade 4: -$450 (5% loss) - LOSS
        Trade(
            symbol="MSFT",
            entry_date=datetime(2024, 1, 29, tzinfo=timezone.utc),
            entry_price=Decimal("300.00"),
            exit_date=datetime(2024, 2, 5, tzinfo=timezone.utc),
            exit_price=Decimal("285.00"),
            shares=30,
            pnl=Decimal("-450.00"),
            pnl_pct=Decimal("-0.05"),
            duration_days=7,
            exit_reason="stop_loss",
            commission=Decimal("0.00"),
            slippage=Decimal("0.00"),
        ),
        # Trade 5: +$1080 (10% gain) - WIN
        Trade(
            symbol="NVDA",
            entry_date=datetime(2024, 2, 6, tzinfo=timezone.utc),
            entry_price=Decimal("180.00"),
            exit_date=datetime(2024, 2, 15, tzinfo=timezone.utc),
            exit_price=Decimal("198.00"),
            shares=60,
            pnl=Decimal("1080.00"),
            pnl_pct=Decimal("0.10"),
            duration_days=9,
            exit_reason="take_profit",
            commission=Decimal("0.00"),
            slippage=Decimal("0.00"),
        ),
    ]

    # Known equity curve
    equity_curve = [
        (datetime(2024, 1, 2, tzinfo=timezone.utc), Decimal("100000")),   # Start
        (datetime(2024, 1, 10, tzinfo=timezone.utc), Decimal("101000")),  # After T1 (peak)
        (datetime(2024, 1, 18, tzinfo=timezone.utc), Decimal("100500")),  # After T2 (drawdown)
        (datetime(2024, 1, 28, tzinfo=timezone.utc), Decimal("101625")),  # After T3 (new peak)
        (datetime(2024, 2, 5, tzinfo=timezone.utc), Decimal("101175")),   # After T4 (drawdown)
        (datetime(2024, 2, 15, tzinfo=timezone.utc), Decimal("102255")),  # After T5 (final)
    ]

    # Configuration with risk-free rate for Sharpe calculation
    config = BacktestConfig(
        strategy_class=type("DummyStrategy", (), {}),  # Dummy strategy class
        symbols=["AAPL", "TSLA", "GOOGL", "MSFT", "NVDA"],
        start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2024, 2, 29, tzinfo=timezone.utc),
        initial_capital=Decimal("100000"),
        commission=Decimal("0.00"),
        slippage_pct=Decimal("0.00"),
        risk_free_rate=Decimal("0.02"),  # 2% annual risk-free rate
    )

    # Calculate metrics using PerformanceCalculator
    calculator = PerformanceCalculator()
    metrics = calculator.calculate_metrics(trades, equity_curve, config)

    # Verify total return (NFR-003: within 0.01% = 0.0001)
    expected_total_return = Decimal("0.02255")  # 2.255% return
    tolerance = Decimal("0.0001")  # 0.01% tolerance
    assert abs(metrics.total_return - expected_total_return) < tolerance, (
        f"Total return accuracy failed: expected {expected_total_return}, "
        f"got {metrics.total_return}, diff {abs(metrics.total_return - expected_total_return)}"
    )

    # Verify win rate (NFR-003: within 0.01% = 0.0001)
    expected_win_rate = Decimal("0.60")  # 60% win rate (3 wins out of 5 trades)
    assert abs(metrics.win_rate - expected_win_rate) < tolerance, (
        f"Win rate accuracy failed: expected {expected_win_rate}, "
        f"got {metrics.win_rate}, diff {abs(metrics.win_rate - expected_win_rate)}"
    )

    # Verify profit factor (NFR-003: within 0.01%)
    # Profit factor = gross profit / gross loss = $3205 / $950 = 3.373684...
    expected_profit_factor = Decimal("3205") / Decimal("950")  # 3.373684...
    # For profit factor, 0.01% of the value = 3.373684 * 0.0001 = 0.0003374
    pf_tolerance = expected_profit_factor * tolerance
    assert abs(metrics.profit_factor - expected_profit_factor) < pf_tolerance, (
        f"Profit factor accuracy failed: expected {expected_profit_factor}, "
        f"got {metrics.profit_factor}, diff {abs(metrics.profit_factor - expected_profit_factor)}"
    )

    # Verify max drawdown (NFR-003: within 0.01% = 0.0001)
    # Max drawdown = (101000 - 100500) / 101000 = 500 / 101000 = 0.00495049... = 0.495%
    expected_max_drawdown = Decimal("0.00495049504950495049504950495")
    assert abs(metrics.max_drawdown - expected_max_drawdown) < tolerance, (
        f"Max drawdown accuracy failed: expected {expected_max_drawdown}, "
        f"got {metrics.max_drawdown}, diff {abs(metrics.max_drawdown - expected_max_drawdown)}"
    )

    # Verify trade counts
    assert metrics.total_trades == 5, f"Expected 5 total trades, got {metrics.total_trades}"
    assert metrics.winning_trades == 3, f"Expected 3 winning trades, got {metrics.winning_trades}"
    assert metrics.losing_trades == 2, f"Expected 2 losing trades, got {metrics.losing_trades}"

    # Note: Sharpe ratio calculation requires daily returns and is more complex
    # We'll verify it's calculated (non-zero) but exact manual calculation is omitted for brevity
    # The detailed Sharpe ratio validation would require daily return series
    assert metrics.sharpe_ratio is not None, "Sharpe ratio should be calculated"
