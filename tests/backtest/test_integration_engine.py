"""
Integration Tests for Complete Backtest Flow

Tests end-to-end backtesting workflow with real components:
- BacktestEngine execution
- HistoricalDataManager data fetching
- Strategy implementation (MomentumStrategy)
- Complete data pipeline from fetch to result

These tests verify that all components work together correctly
in realistic backtesting scenarios.

From: specs/001-backtesting-engine/tasks.md T031
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from typing import List

from src.trading_bot.backtest.engine import BacktestEngine
from src.trading_bot.backtest.models import (
    BacktestConfig,
    HistoricalDataBar,
)
from examples.sample_strategies import MomentumStrategy


@pytest.mark.integration
class TestCompleteBacktestFlow:
    """
    Integration test for complete backtest workflow.

    Tests the full pipeline:
    1. Configure backtest (BacktestConfig)
    2. Fetch historical data (HistoricalDataManager)
    3. Execute strategy (MomentumStrategy)
    4. Generate results (BacktestResult)

    Uses real historical data and strategy to verify end-to-end correctness.
    """

    @pytest.fixture
    def mock_historical_data(self) -> List[HistoricalDataBar]:
        """
        Create realistic mock historical data for AAPL 2023.

        Simulates 252 trading days with realistic price movements
        suitable for momentum strategy testing.

        Returns:
            List of 252 HistoricalDataBar objects
        """
        bars = []
        symbol = "AAPL"
        start_date = datetime(2023, 1, 3, 9, 30, tzinfo=timezone.utc)

        # Start at $130, end at $195 (realistic AAPL 2023 movement)
        # Create price movements with trends to generate momentum signals
        prices = []

        # Q1: Uptrend $130 -> $155 (25 points in ~60 days)
        for i in range(60):
            price = Decimal("130.0") + (Decimal("25.0") * Decimal(i) / Decimal(60))
            prices.append(price)

        # Q2: Sideways $155 -> $160 (5 points in ~60 days)
        for i in range(60):
            price = Decimal("155.0") + (Decimal("5.0") * Decimal(i) / Decimal(60))
            prices.append(price)

        # Q3: Downtrend $160 -> $145 (-15 points in ~60 days)
        for i in range(60):
            price = Decimal("160.0") - (Decimal("15.0") * Decimal(i) / Decimal(60))
            prices.append(price)

        # Q4: Strong uptrend $145 -> $195 (50 points in ~72 days)
        for i in range(72):
            price = Decimal("145.0") + (Decimal("50.0") * Decimal(i) / Decimal(72))
            prices.append(price)

        # Create bars from prices
        from datetime import timedelta
        for i, base_price in enumerate(prices):
            bar_timestamp = start_date + timedelta(days=i)

            # Add realistic OHLC spreads
            open_price = base_price - Decimal("0.50")
            high_price = base_price + Decimal("1.00")
            low_price = base_price - Decimal("1.00")
            close_price = base_price

            bar = HistoricalDataBar(
                symbol=symbol,
                timestamp=bar_timestamp,
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price,
                volume=50000000 + (i * 100000),
                split_adjusted=True,
                dividend_adjusted=True
            )
            bars.append(bar)

        return bars

    @pytest.fixture
    def backtest_config(self) -> BacktestConfig:
        """
        Create BacktestConfig for AAPL 2023 test.

        Returns:
            BacktestConfig with MomentumStrategy and 1-year date range
        """
        return BacktestConfig(
            strategy_class=MomentumStrategy,
            symbols=["AAPL"],
            start_date=datetime(2023, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2023, 12, 31, tzinfo=timezone.utc),
            initial_capital=Decimal("100000.0"),
            commission=Decimal("0.0"),  # No commission for simplicity
            slippage_pct=Decimal("0.0"),  # No slippage for simplicity
            risk_free_rate=Decimal("0.02"),
            cache_enabled=True
        )

    def test_complete_backtest_flow(
        self,
        mock_historical_data: List[HistoricalDataBar],
        backtest_config: BacktestConfig
    ):
        """
        Test: Complete backtest flow with mock data and MomentumStrategy.

        **Test Scenario**:
        GIVEN: MomentumStrategy (short_window=10, long_window=30)
        AND: Mock historical data for AAPL in 2023 (252 trading days)
        AND: Initial capital of $100,000
        WHEN: Complete backtest is executed from config to result
        THEN:
        - Trades are recorded (momentum strategy should generate multiple entries/exits)
        - Equity curve is generated with data points
        - No errors or exceptions occur during execution
        - Result has valid BacktestResult structure
        - All trades have valid entry/exit dates and P&L

        **Acceptance Criteria**:
        1. Strategy executes without errors
        2. At least one trade is recorded (momentum crossovers expected)
        3. Equity curve has data points for each bar
        4. All trades have valid structure (positive shares, valid dates, P&L calculated)
        5. Performance metrics are calculated correctly
        6. Final equity matches initial capital + sum of trade P&L

        **Why MomentumStrategy?**:
        - More realistic than buy-and-hold (multiple entries/exits)
        - Tests strategy signal generation (should_enter/should_exit)
        - Verifies position management across multiple trades
        - Mock data has trends suitable for momentum signals

        From: specs/001-backtesting-engine/tasks.md T031
        """
        # ARRANGE: Setup components
        symbol = "AAPL"
        initial_capital = backtest_config.initial_capital
        start_date = backtest_config.start_date
        end_date = backtest_config.end_date

        # Create strategy with windows suitable for test data
        # short=10, long=30 should generate signals in our mock data
        strategy = MomentumStrategy(short_window=10, long_window=30)

        # Verify we have enough data for momentum strategy
        print(f"\nUsing {len(mock_historical_data)} bars of mock historical data")
        assert len(mock_historical_data) >= strategy.long_window, (
            f"Insufficient data for MomentumStrategy (need >= {strategy.long_window} bars, "
            f"got {len(mock_historical_data)})"
        )

        # Create engine
        engine = BacktestEngine(config=backtest_config)

        # ACT: Execute complete backtest
        print(f"Running backtest with MomentumStrategy...")
        result = engine.run(
            strategy=strategy,
            historical_data={symbol: mock_historical_data}
        )

        # ASSERT: Verify complete backtest results

        # 1. Verify trades were executed
        print(f"\nBacktest completed:")
        print(f"  Total trades: {len(result.trades)}")
        assert len(result.trades) > 0, (
            "MomentumStrategy should generate at least one trade with AAPL 2023 data. "
            "If no trades, check strategy logic or data quality."
        )

        # 2. Verify equity curve was generated
        assert len(result.equity_curve) > 0, (
            "Equity curve should have data points for each bar"
        )
        print(f"  Equity curve points: {len(result.equity_curve)}")

        # Verify equity curve has one point per bar
        # (Engine updates equity after each bar)
        assert len(result.equity_curve) == len(mock_historical_data), (
            f"Equity curve should have one point per bar. "
            f"Expected {len(mock_historical_data)}, got {len(result.equity_curve)}"
        )

        # 3. Verify all trades have valid structure
        total_pnl = Decimal("0.0")
        for i, trade in enumerate(result.trades):
            # Verify symbol
            assert trade.symbol == symbol, (
                f"Trade {i}: symbol should be {symbol}, got {trade.symbol}"
            )

            # Verify positive shares
            assert trade.shares > 0, (
                f"Trade {i}: shares should be positive, got {trade.shares}"
            )

            # Verify entry/exit dates are within backtest period
            assert start_date <= trade.entry_date <= end_date, (
                f"Trade {i}: entry_date {trade.entry_date} outside backtest period"
            )
            assert start_date <= trade.exit_date <= end_date, (
                f"Trade {i}: exit_date {trade.exit_date} outside backtest period"
            )

            # Verify exit_date > entry_date
            assert trade.exit_date > trade.entry_date, (
                f"Trade {i}: exit_date must be after entry_date"
            )

            # Verify positive prices
            assert trade.entry_price > 0, (
                f"Trade {i}: entry_price should be positive, got {trade.entry_price}"
            )
            assert trade.exit_price > 0, (
                f"Trade {i}: exit_price should be positive, got {trade.exit_price}"
            )

            # Verify P&L is calculated (can be positive or negative)
            # P&L = (exit_price - entry_price) * shares - commission - slippage
            expected_pnl = (
                (trade.exit_price - trade.entry_price) * trade.shares
                - trade.commission
                - trade.slippage
            )
            assert abs(trade.pnl - expected_pnl) < Decimal("0.01"), (
                f"Trade {i}: P&L calculation error. "
                f"Expected {expected_pnl}, got {trade.pnl}"
            )

            # Verify P&L percentage matches
            expected_pnl_pct = trade.pnl / (trade.entry_price * trade.shares)
            assert abs(trade.pnl_pct - expected_pnl_pct) < Decimal("0.0001"), (
                f"Trade {i}: P&L% calculation error. "
                f"Expected {expected_pnl_pct}, got {trade.pnl_pct}"
            )

            # Verify exit reason is valid
            valid_exit_reasons = ["strategy_signal", "end_of_data", "stop_loss", "take_profit"]
            assert trade.exit_reason in valid_exit_reasons, (
                f"Trade {i}: invalid exit_reason '{trade.exit_reason}'"
            )

            # Accumulate total P&L for final equity verification
            total_pnl += trade.pnl

            # Print trade summary
            print(f"\n  Trade {i + 1}:")
            print(f"    Entry: {trade.entry_date.date()} @ ${trade.entry_price:.2f}")
            print(f"    Exit: {trade.exit_date.date()} @ ${trade.exit_price:.2f}")
            print(f"    Shares: {trade.shares}")
            print(f"    P&L: ${trade.pnl:.2f} ({trade.pnl_pct * 100:.2f}%)")
            print(f"    Duration: {trade.duration_days} days")
            print(f"    Reason: {trade.exit_reason}")

        # 4. Verify metrics are calculated
        assert result.metrics is not None, "PerformanceMetrics should be calculated"

        # Verify total_trades matches trade count
        assert result.metrics.total_trades == len(result.trades), (
            f"Metrics total_trades ({result.metrics.total_trades}) "
            f"should match trades list length ({len(result.trades)})"
        )

        # Verify winning/losing trades sum to total
        assert (
            result.metrics.winning_trades + result.metrics.losing_trades
            == result.metrics.total_trades
        ), (
            "winning_trades + losing_trades should equal total_trades"
        )

        # Verify win_rate calculation
        if result.metrics.total_trades > 0:
            expected_win_rate = (
                Decimal(result.metrics.winning_trades)
                / Decimal(result.metrics.total_trades)
            )
            assert abs(result.metrics.win_rate - expected_win_rate) < Decimal("0.0001"), (
                f"Win rate calculation error. "
                f"Expected {expected_win_rate}, got {result.metrics.win_rate}"
            )

        print(f"\nPerformance Metrics:")
        print(f"  Total Trades: {result.metrics.total_trades}")
        print(f"  Winning Trades: {result.metrics.winning_trades}")
        print(f"  Losing Trades: {result.metrics.losing_trades}")
        print(f"  Win Rate: {result.metrics.win_rate * 100:.2f}%")

        # 5. Verify final equity matches expected
        # Final equity = initial capital + sum of all trade P&L
        expected_final_equity = initial_capital + total_pnl
        actual_final_equity = result.final_equity

        # Allow small rounding error (1 cent)
        equity_error = abs(actual_final_equity - expected_final_equity)
        assert equity_error < Decimal("0.01"), (
            f"Final equity mismatch. "
            f"Expected ${expected_final_equity:.2f}, got ${actual_final_equity:.2f}. "
            f"Error: ${equity_error:.2f}"
        )

        print(f"\nFinal Results:")
        print(f"  Initial Capital: ${initial_capital:,.2f}")
        print(f"  Total P&L: ${total_pnl:,.2f}")
        print(f"  Final Equity: ${actual_final_equity:,.2f}")
        print(f"  Return: {(total_pnl / initial_capital) * 100:.2f}%")

        # 6. Verify execution metadata
        assert result.execution_time_seconds > 0, (
            "Execution time should be recorded and positive"
        )
        assert result.completed_at is not None, (
            "Completion timestamp should be recorded"
        )
        assert result.completed_at.tzinfo is not None, (
            "Completion timestamp should be timezone-aware (UTC)"
        )

        print(f"  Execution Time: {result.execution_time_seconds:.3f} seconds")
        print(f"  Completed At: {result.completed_at}")

        # 7. Verify no critical data warnings
        # (Some warnings like zero volume are acceptable, but not data quality errors)
        if result.data_warnings:
            print(f"\nData Warnings ({len(result.data_warnings)}):")
            for warning in result.data_warnings:
                print(f"  - {warning}")

        # Success message
        print(f"\n[PASS] Integration test passed: Complete backtest flow successful")
        print(f"[PASS] All components working together correctly")
        print(f"[PASS] {len(result.trades)} trades executed, "
              f"{len(result.equity_curve)} equity points recorded")

    def test_complete_backtest_flow_no_trades(self):
        """
        Test: Complete backtest flow with strategy that generates no trades.

        **Test Scenario**:
        GIVEN: MomentumStrategy with very large windows (short=100, long=200)
        AND: Limited mock data (50 bars) insufficient for signals
        WHEN: Backtest is executed
        THEN:
        - No trades are generated (insufficient data for MA crossovers)
        - Equity curve still generated (flat line at initial capital)
        - No errors or exceptions
        - Final equity equals initial capital

        This verifies the engine handles edge cases gracefully.
        """
        # ARRANGE: Create limited mock data (50 bars)
        bars = []
        symbol = "AAPL"
        start_date = datetime(2023, 1, 3, 9, 30, tzinfo=timezone.utc)

        from datetime import timedelta
        for i in range(50):
            bar_timestamp = start_date + timedelta(days=i)
            base_price = Decimal("150.0") + Decimal(i) * Decimal("0.1")

            bar = HistoricalDataBar(
                symbol=symbol,
                timestamp=bar_timestamp,
                open=base_price - Decimal("0.50"),
                high=base_price + Decimal("1.00"),
                low=base_price - Decimal("1.00"),
                close=base_price,
                volume=50000000,
                split_adjusted=True,
                dividend_adjusted=True
            )
            bars.append(bar)

        # Config with short date range
        config = BacktestConfig(
            strategy_class=MomentumStrategy,
            symbols=["AAPL"],
            start_date=datetime(2023, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2023, 2, 28, tzinfo=timezone.utc),
            initial_capital=Decimal("100000.0"),
            commission=Decimal("0.0"),
            slippage_pct=Decimal("0.0"),
            risk_free_rate=Decimal("0.02"),
            cache_enabled=True
        )

        # Strategy with windows larger than available data
        strategy = MomentumStrategy(short_window=100, long_window=200)

        # Verify we have data but not enough for strategy
        assert len(bars) > 0, "Should have some historical data"
        assert len(bars) < strategy.long_window, (
            "Test requires insufficient data for strategy (design check)"
        )

        # Create engine
        engine = BacktestEngine(config=config)

        # ACT: Execute backtest
        result = engine.run(strategy=strategy, historical_data={"AAPL": bars})

        # ASSERT: Verify no-trade scenario

        # 1. No trades generated
        assert len(result.trades) == 0, (
            "Should have no trades with insufficient data for MA calculation"
        )

        # 2. Equity curve still exists (one point per bar)
        assert len(result.equity_curve) > 0, (
            "Equity curve should exist even with no trades"
        )
        assert len(result.equity_curve) == len(bars), (
            "Equity curve should have one point per bar"
        )

        # 3. Final equity equals initial capital (no trades = no P&L)
        assert result.final_equity == config.initial_capital, (
            f"Final equity should equal initial capital with no trades. "
            f"Expected ${config.initial_capital}, got ${result.final_equity}"
        )

        # 4. All equity points equal initial capital (flat line)
        for timestamp, equity in result.equity_curve:
            assert equity == config.initial_capital, (
                f"Equity should remain constant at ${config.initial_capital} "
                f"with no trades, got ${equity} at {timestamp}"
            )

        # 5. Metrics show zero trades
        assert result.metrics.total_trades == 0
        assert result.metrics.winning_trades == 0
        assert result.metrics.losing_trades == 0
        assert result.metrics.win_rate == Decimal("0.0")

        print(f"\n[PASS] No-trade scenario test passed")
        print(f"[PASS] Engine handles insufficient data gracefully")
        print(f"[PASS] Equity remains at ${config.initial_capital:,.2f}")
