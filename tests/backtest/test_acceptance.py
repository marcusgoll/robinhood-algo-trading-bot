"""
Acceptance Tests for NFR Validation

Tests Non-Functional Requirements:
- NFR-001: Performance benchmark (1 year backtest in <30 seconds)
- NFR-002: Data fetch performance (10 stocks in <60 seconds)
- NFR-003: Accuracy validation (results within 0.01% of manual calculation)
- NFR-010: Reproducibility (same inputs produce same outputs)

All tests marked with @pytest.mark.acceptance for selective execution.
All tests are parallelizable (marked with [P]).
"""

import time
import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import List

from src.trading_bot.backtest.models import (
    BacktestConfig,
    HistoricalDataBar,
    PerformanceMetrics,
)
from src.trading_bot.backtest.engine import BacktestEngine
from src.trading_bot.backtest.performance_calculator import PerformanceCalculator
from src.trading_bot.backtest.historical_data_manager import HistoricalDataManager
from examples.sample_strategies import BuyAndHoldStrategy, MomentumStrategy


def create_mock_data(num_days: int, start_price: Decimal = Decimal("100")) -> List[HistoricalDataBar]:
    """
    Create mock historical data for testing.

    Args:
        num_days: Number of trading days to generate
        start_price: Starting price (default: $100)

    Returns:
        List of HistoricalDataBar objects with realistic price movements
    """
    bars = []
    current_price = start_price
    start_date = datetime(2023, 1, 1, tzinfo=timezone.utc)

    for i in range(num_days):
        # Simulate realistic daily price movement (±2%)
        daily_change = Decimal("0.02") * (Decimal(i % 10) / Decimal("10") - Decimal("0.5"))
        current_price = current_price * (Decimal("1") + daily_change)

        # Ensure high >= low with realistic spread
        low = current_price * Decimal("0.99")
        high = current_price * Decimal("1.01")
        open_price = current_price * Decimal("0.995")
        close_price = current_price * Decimal("1.005")

        bar = HistoricalDataBar(
            symbol="TEST",
            timestamp=start_date + timedelta(days=i),
            open=open_price,
            high=high,
            low=low,
            close=close_price,
            volume=1000000,
            split_adjusted=True,
            dividend_adjusted=True,
        )
        bars.append(bar)

    return bars


@pytest.mark.acceptance
def test_performance_benchmark():
    """
    Validate NFR-001: 1-year backtest completes in <30 seconds.

    Setup:
        - 252 trading days (1 year)
        - MomentumStrategy with short_window=10, long_window=30
        - Mock historical data

    Assert:
        - Execution time < 30 seconds (NFR-001 requirement)

    Note: This is a performance test, not functional. Results may vary
    by system, but should consistently pass on modern hardware.
    """
    # Setup 252 trading days (1 year)
    historical_data = create_mock_data(252)

    config = BacktestConfig(
        strategy_class=MomentumStrategy,
        symbols=["TEST"],
        start_date=datetime(2023, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2023, 12, 31, tzinfo=timezone.utc),
        initial_capital=Decimal("100000"),
    )

    strategy = MomentumStrategy(short_window=10, long_window=30)

    # Measure execution time
    start_time = time.time()
    engine = BacktestEngine(config)
    result = engine.run(strategy, historical_data)
    execution_time = time.time() - start_time

    # Assert <30 seconds (NFR-001)
    assert execution_time < 30.0, (
        f"Backtest took {execution_time:.2f}s, expected <30s (NFR-001)"
    )

    # Verify backtest completed successfully
    assert result is not None
    assert result.execution_time_seconds > 0
    assert len(result.equity_curve) > 0


@pytest.mark.acceptance
def test_buy_and_hold_accuracy():
    """
    Validate NFR-003: Results within 0.01% of manual calculation.

    Setup:
        - Known buy-and-hold scenario with exact prices
        - Entry: $100, Exit: $150 (50% return)
        - Initial capital: $100,000
        - Expected shares: floor(100000 / 100) = 1000 shares
        - Expected P&L: ($150 - $100) * 1000 = $50,000
        - Expected return: $50,000 / $100,000 = 50.00%

    Assert:
        - Total return within 0.01% of 50% (manual calculation)

    Note: This validates calculation accuracy, a core requirement
    for trustworthy backtest results.
    """
    # Known buy-and-hold scenario
    historical_data = [
        # First bar: entry at open $100
        HistoricalDataBar(
            symbol="TEST",
            timestamp=datetime(2023, 1, 1, tzinfo=timezone.utc),
            open=Decimal("100"),
            high=Decimal("102"),
            low=Decimal("99"),
            close=Decimal("101"),
            volume=1000000,
            split_adjusted=True,
            dividend_adjusted=True,
        ),
        # Second bar: price movement
        HistoricalDataBar(
            symbol="TEST",
            timestamp=datetime(2023, 1, 2, tzinfo=timezone.utc),
            open=Decimal("101"),
            high=Decimal("125"),
            low=Decimal("100"),
            close=Decimal("120"),
            volume=1000000,
            split_adjusted=True,
            dividend_adjusted=True,
        ),
        # Last bar: exit at close $150
        HistoricalDataBar(
            symbol="TEST",
            timestamp=datetime(2023, 12, 31, tzinfo=timezone.utc),
            open=Decimal("148"),
            high=Decimal("152"),
            low=Decimal("147"),
            close=Decimal("150"),
            volume=1000000,
            split_adjusted=True,
            dividend_adjusted=True,
        ),
    ]

    # Calculate expected return manually
    # Entry: $100 (open of bar 2), Exit: $150 (close of bar 3)
    # Shares: floor($100,000 / $100) = 1000 shares
    # P&L: ($150 - $100) * 1000 = $50,000
    # Return: $50,000 / $100,000 = 50%
    expected_return = Decimal("0.50")

    # Run backtest
    config = BacktestConfig(
        strategy_class=BuyAndHoldStrategy,
        symbols=["TEST"],
        start_date=datetime(2023, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2023, 12, 31, tzinfo=timezone.utc),
        initial_capital=Decimal("100000"),
    )

    strategy = BuyAndHoldStrategy()
    engine = BacktestEngine(config)
    result = engine.run(strategy, historical_data)

    # Calculate metrics
    calculator = PerformanceCalculator()
    metrics = calculator.calculate_metrics(result.trades, result.equity_curve, config)

    # Assert within 0.01% accuracy (NFR-003)
    tolerance = Decimal("0.0001")  # 0.01%
    actual_return = metrics.total_return
    difference = abs(actual_return - expected_return)

    assert difference < tolerance, (
        f"Total return {actual_return:.4f} differs from expected {expected_return:.4f} "
        f"by {difference:.6f}, exceeds tolerance {tolerance} (NFR-003)"
    )

    # Additional validation: verify trade details
    assert len(result.trades) == 1, "Expected exactly 1 trade for buy-and-hold"
    trade = result.trades[0]
    assert trade.entry_price == Decimal("100"), f"Entry price {trade.entry_price} != $100"
    assert trade.exit_price == Decimal("150"), f"Exit price {trade.exit_price} != $150"
    assert trade.shares == 1000, f"Shares {trade.shares} != 1000"


@pytest.mark.acceptance
def test_reproducibility():
    """
    Validate NFR-010: Same inputs produce same outputs.

    Setup:
        - Run same backtest configuration twice
        - MomentumStrategy with fixed parameters
        - Same historical data (252 days)

    Assert:
        - Identical number of trades
        - Identical total return
        - Identical win rate
        - Identical max drawdown

    Note: This validates deterministic execution, critical for
    debugging strategies and comparing results across runs.
    """
    # Create test data
    historical_data = create_mock_data(252)

    config = BacktestConfig(
        strategy_class=MomentumStrategy,
        symbols=["TEST"],
        start_date=datetime(2023, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2023, 12, 31, tzinfo=timezone.utc),
        initial_capital=Decimal("100000"),
    )

    strategy1 = MomentumStrategy(short_window=10, long_window=30)
    strategy2 = MomentumStrategy(short_window=10, long_window=30)

    # Run backtest twice
    engine1 = BacktestEngine(config)
    result1 = engine1.run(strategy1, historical_data)

    engine2 = BacktestEngine(config)
    result2 = engine2.run(strategy2, historical_data)

    # Calculate metrics for both
    calculator = PerformanceCalculator()
    metrics1 = calculator.calculate_metrics(result1.trades, result1.equity_curve, config)
    metrics2 = calculator.calculate_metrics(result2.trades, result2.equity_curve, config)

    # Assert identical results (NFR-010)
    assert len(result1.trades) == len(result2.trades), (
        f"Trade counts differ: {len(result1.trades)} vs {len(result2.trades)} (NFR-010)"
    )

    assert metrics1.total_return == metrics2.total_return, (
        f"Total returns differ: {metrics1.total_return} vs {metrics2.total_return} (NFR-010)"
    )

    assert metrics1.win_rate == metrics2.win_rate, (
        f"Win rates differ: {metrics1.win_rate} vs {metrics2.win_rate} (NFR-010)"
    )

    assert metrics1.max_drawdown == metrics2.max_drawdown, (
        f"Max drawdowns differ: {metrics1.max_drawdown} vs {metrics2.max_drawdown} (NFR-010)"
    )

    # Verify trade details match exactly
    for i, (trade1, trade2) in enumerate(zip(result1.trades, result2.trades)):
        assert trade1.entry_date == trade2.entry_date, (
            f"Trade {i} entry dates differ: {trade1.entry_date} vs {trade2.entry_date}"
        )
        assert trade1.exit_date == trade2.exit_date, (
            f"Trade {i} exit dates differ: {trade1.exit_date} vs {trade2.exit_date}"
        )
        assert trade1.entry_price == trade2.entry_price, (
            f"Trade {i} entry prices differ: {trade1.entry_price} vs {trade2.entry_price}"
        )
        assert trade1.exit_price == trade2.exit_price, (
            f"Trade {i} exit prices differ: {trade1.exit_price} vs {trade2.exit_price}"
        )
        assert trade1.shares == trade2.shares, (
            f"Trade {i} share counts differ: {trade1.shares} vs {trade2.shares}"
        )


@pytest.mark.acceptance
@pytest.mark.slow
def test_data_fetch_performance():
    """
    Validate NFR-002: Fetch 10 stocks (1 year each) in <60 seconds.

    Setup:
        - 10 popular tech stocks (AAPL, MSFT, GOOGL, etc.)
        - 1 year of historical data per stock (2023)
        - Real API calls (Alpaca or Yahoo Finance)

    Assert:
        - Total fetch time < 60 seconds (NFR-002 requirement)
        - All stocks return data successfully

    Note: This is a real integration test requiring API access.
    Marked as 'slow' - run with: pytest -m "acceptance and not slow" to skip.
    """
    # Skip if no API credentials available
    import os
    if not os.getenv("ALPACA_API_KEY"):
        pytest.skip("ALPACA_API_KEY not set - skipping real API test")
    symbols = [
        "AAPL", "MSFT", "GOOGL", "TSLA", "NVDA",
        "AMD", "INTC", "AMZN", "META", "NFLX"
    ]
    start_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
    end_date = datetime(2023, 12, 31, tzinfo=timezone.utc)

    data_manager = HistoricalDataManager()

    # Measure total fetch time
    start_time = time.time()
    fetched_data = {}

    for symbol in symbols:
        data = data_manager.fetch_data(symbol, start_date, end_date)
        assert len(data) > 0, f"No data returned for {symbol}"
        fetched_data[symbol] = data

    total_time = time.time() - start_time

    # Assert <60 seconds (NFR-002)
    assert total_time < 60.0, (
        f"Fetching 10 stocks took {total_time:.2f}s, expected <60s (NFR-002)"
    )

    # Verify data quality
    for symbol, data in fetched_data.items():
        assert len(data) >= 200, (
            f"{symbol} returned only {len(data)} bars, expected ~252 for 1 year"
        )

        # Verify chronological order
        for i in range(len(data) - 1):
            assert data[i].timestamp < data[i + 1].timestamp, (
                f"{symbol} data not in chronological order at index {i}"
            )


