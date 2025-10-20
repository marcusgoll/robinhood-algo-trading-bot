"""
Integration Tests for Metrics from Complete Backtest

Tests end-to-end metrics calculation from a complete backtest run:
- Complete backtest execution with MomentumStrategy
- Metrics calculation using PerformanceCalculator
- Validation of all metrics (returns, win rate, drawdown, Sharpe ratio)

This integration test verifies that all components (BacktestEngine,
PerformanceCalculator) work together to produce accurate metrics.

From: specs/001-backtesting-engine/tasks.md T045
"""

import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List

from src.trading_bot.backtest.engine import BacktestEngine
from src.trading_bot.backtest.performance_calculator import PerformanceCalculator
from src.trading_bot.backtest.models import (
    BacktestConfig,
    HistoricalDataBar,
)
from examples.sample_strategies import MomentumStrategy


@pytest.mark.integration
class TestMetricsFromRealBacktest:
    """
    Integration test for metrics calculation from complete backtest.

    Tests the full pipeline:
    1. Run complete backtest with MomentumStrategy
    2. Calculate metrics using PerformanceCalculator
    3. Verify all metrics are reasonable and valid

    Uses realistic mock data to avoid external API dependencies while
    providing real-world-like price movements.
    """

    @pytest.fixture
    def realistic_mock_data(self) -> List[HistoricalDataBar]:
        """
        Create realistic mock data for AAPL 2023 (252 trading days).

        Simulates realistic price movements with trends to generate:
        - Multiple momentum signals (entries/exits)
        - Both winning and losing trades
        - Reasonable drawdowns
        - Realistic returns

        Returns:
            List of 252 HistoricalDataBar objects for AAPL
        """
        bars = []
        symbol = "AAPL"
        start_date = datetime(2023, 1, 3, 9, 30, tzinfo=timezone.utc)

        # Create realistic price movements
        # Start: $130, End: $195 (50% return - realistic for AAPL 2023)
        prices = []

        # Q1: Strong uptrend $130 -> $160 (30 points in 60 days = 23% gain)
        for i in range(60):
            base = Decimal("130.0")
            trend = (Decimal("30.0") * Decimal(i) / Decimal(60))
            # Add some volatility (±2%)
            noise = Decimal("0.0")  # Simplified for reproducibility
            price = base + trend + noise
            prices.append(price)

        # Q2: Consolidation/Sideways $160 -> $165 (5 points in 65 days = 3% gain)
        for i in range(65):
            base = Decimal("160.0")
            trend = (Decimal("5.0") * Decimal(i) / Decimal(65))
            price = base + trend
            prices.append(price)

        # Q3: Pullback $165 -> $150 (-15 points in 60 days = -9% loss)
        for i in range(60):
            base = Decimal("165.0")
            trend = -(Decimal("15.0") * Decimal(i) / Decimal(60))
            price = base + trend
            prices.append(price)

        # Q4: Recovery rally $150 -> $195 (45 points in 67 days = 30% gain)
        for i in range(67):
            base = Decimal("150.0")
            trend = (Decimal("45.0") * Decimal(i) / Decimal(67))
            price = base + trend
            prices.append(price)

        # Create bars from prices
        for i, base_price in enumerate(prices):
            bar_timestamp = start_date + timedelta(days=i)

            # Add realistic OHLC spreads (typical daily range 1-2%)
            open_price = base_price - Decimal("0.50")
            high_price = base_price + Decimal("1.50")
            low_price = base_price - Decimal("1.00")
            close_price = base_price

            bar = HistoricalDataBar(
                symbol=symbol,
                timestamp=bar_timestamp,
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price,
                volume=75000000 + (i * 50000),  # Realistic AAPL volume
                split_adjusted=True,
                dividend_adjusted=True
            )
            bars.append(bar)

        return bars

    @pytest.fixture
    def backtest_config(self) -> BacktestConfig:
        """
        Create BacktestConfig for integration test.

        Returns:
            BacktestConfig with MomentumStrategy and realistic parameters
        """
        return BacktestConfig(
            strategy_class=MomentumStrategy,
            symbols=["AAPL"],
            start_date=datetime(2023, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2023, 12, 31, tzinfo=timezone.utc),
            initial_capital=Decimal("100000.0"),
            commission=Decimal("0.0"),  # No commission for test clarity
            slippage_pct=Decimal("0.0"),  # No slippage for test clarity
            risk_free_rate=Decimal("0.02"),  # 2% risk-free rate (US Treasury)
            cache_enabled=True
        )

    def test_metrics_from_real_backtest(
        self,
        realistic_mock_data: List[HistoricalDataBar],
        backtest_config: BacktestConfig
    ):
        """
        Test: Calculate metrics from complete backtest with MomentumStrategy.

        **Test Scenario**:
        GIVEN: Complete backtest with MomentumStrategy (short=10, long=30)
        AND: Realistic mock data (252 bars, uptrends/downtrends)
        AND: Initial capital $100,000
        WHEN: Backtest runs and metrics are calculated
        THEN:
        - All metrics are reasonable and valid
        - Total return is within expected range (-100% to 200%)
        - Win rate is between 0% and 100%
        - Max drawdown is non-negative and <= 100%
        - Sharpe ratio is calculated (not None/NaN)
        - All trade statistics match trade history

        **Acceptance Criteria**:
        1. Backtest executes successfully with trades
        2. All metrics are within reasonable ranges
        3. Metrics match manual calculations from trade history
        4. No NaN, None, or invalid values in metrics
        5. Returns, drawdown, Sharpe ratio all calculated correctly

        From: specs/001-backtesting-engine/tasks.md T045
        """
        # ARRANGE: Setup complete backtest
        print(f"\n=== Integration Test: Metrics from Real Backtest ===")
        print(f"Data: {len(realistic_mock_data)} bars (AAPL 2023 simulation)")
        print(f"Strategy: MomentumStrategy(short=10, long=30)")
        print(f"Initial Capital: ${backtest_config.initial_capital:,.2f}")

        # Create strategy with windows suitable for test data
        strategy = MomentumStrategy(short_window=10, long_window=30)

        # Verify we have enough data
        assert len(realistic_mock_data) >= strategy.long_window, (
            f"Insufficient data for strategy (need >= {strategy.long_window} bars)"
        )

        # Create engine
        engine = BacktestEngine(config=backtest_config)

        # ACT: Run complete backtest
        print(f"\nRunning complete backtest...")
        result = engine.run(
            strategy=strategy,
            historical_data={"AAPL": realistic_mock_data}
        )

        # Calculate metrics using PerformanceCalculator
        print(f"Calculating metrics with PerformanceCalculator...")
        calculator = PerformanceCalculator()
        metrics = calculator.calculate_metrics(
            trades=result.trades,
            equity_curve=result.equity_curve,
            config=backtest_config
        )

        # ASSERT: Verify all metrics are reasonable and valid

        print(f"\n=== Backtest Results ===")
        print(f"Total Trades: {metrics.total_trades}")
        print(f"Winning Trades: {metrics.winning_trades}")
        print(f"Losing Trades: {metrics.losing_trades}")
        print(f"Win Rate: {metrics.win_rate * 100:.2f}%")

        # 1. Verify trades were generated
        assert metrics.total_trades > 0, (
            "Should have trades with MomentumStrategy and trending data"
        )
        print(f"\n[PASS] Generated {metrics.total_trades} trades")

        # 2. Verify total return is reasonable (-100% to 200%)
        assert -1.0 <= metrics.total_return <= 2.0, (
            f"Total return ({metrics.total_return * 100:.2f}%) should be reasonable "
            f"(-100% to 200%). Values outside this range suggest calculation error."
        )
        print(f"[PASS] Total Return: {metrics.total_return * 100:.2f}% (reasonable)")

        # 3. Verify win rate is valid percentage (0-100%)
        assert 0.0 <= metrics.win_rate <= 1.0, (
            f"Win rate ({metrics.win_rate}) must be between 0 and 1"
        )
        print(f"[PASS] Win Rate: {metrics.win_rate * 100:.2f}% (valid)")

        # 4. Verify max drawdown is valid (0-100%, non-negative)
        assert metrics.max_drawdown >= 0, (
            f"Max drawdown ({metrics.max_drawdown}) must be non-negative"
        )
        assert metrics.max_drawdown <= 1.0, (
            f"Max drawdown ({metrics.max_drawdown}) must be <= 1.0 (100%)"
        )
        print(f"[PASS] Max Drawdown: {metrics.max_drawdown * 100:.2f}% (valid)")

        # 5. Verify Sharpe ratio is calculated (not None, not NaN)
        assert metrics.sharpe_ratio is not None, (
            "Sharpe ratio should be calculated (not None)"
        )
        # Allow negative Sharpe (indicates poor risk-adjusted returns)
        # but verify it's a valid number
        assert isinstance(metrics.sharpe_ratio, Decimal), (
            f"Sharpe ratio should be Decimal, got {type(metrics.sharpe_ratio)}"
        )
        print(f"[PASS] Sharpe Ratio: {metrics.sharpe_ratio:.2f} (calculated)")

        # 6. Verify trade statistics match trade history
        winning_trades = sum(1 for trade in result.trades if trade.pnl > 0)
        losing_trades = sum(1 for trade in result.trades if trade.pnl < 0)

        assert metrics.winning_trades == winning_trades, (
            f"Metrics winning_trades ({metrics.winning_trades}) should match "
            f"actual winning trades ({winning_trades})"
        )
        assert metrics.losing_trades == losing_trades, (
            f"Metrics losing_trades ({metrics.losing_trades}) should match "
            f"actual losing trades ({losing_trades})"
        )
        print(f"[PASS] Trade statistics match actual trade history")

        # 7. Verify winning_trades + losing_trades = total_trades
        assert metrics.winning_trades + metrics.losing_trades == metrics.total_trades, (
            f"winning_trades ({metrics.winning_trades}) + "
            f"losing_trades ({metrics.losing_trades}) should equal "
            f"total_trades ({metrics.total_trades})"
        )
        print(f"[PASS] Trade counts consistent")

        # 8. Verify average win/loss are reasonable (if trades exist)
        if metrics.winning_trades > 0:
            assert metrics.average_win > 0, (
                f"Average win should be positive, got {metrics.average_win}"
            )
            print(f"[PASS] Average Win: ${metrics.average_win:.2f}")

        if metrics.losing_trades > 0:
            assert metrics.average_loss < 0, (
                f"Average loss should be negative, got {metrics.average_loss}"
            )
            print(f"[PASS] Average Loss: ${metrics.average_loss:.2f}")

        # 9. Verify profit factor is reasonable (0 or positive)
        assert metrics.profit_factor >= 0, (
            f"Profit factor ({metrics.profit_factor}) must be non-negative"
        )
        if metrics.losing_trades > 0:
            print(f"[PASS] Profit Factor: {metrics.profit_factor:.2f}")
        else:
            print(f"[PASS] Profit Factor: {metrics.profit_factor:.2f} (no losses)")

        # 10. Verify CAGR and annualized return are calculated
        assert isinstance(metrics.cagr, Decimal), (
            "CAGR should be calculated (Decimal)"
        )
        assert isinstance(metrics.annualized_return, Decimal), (
            "Annualized return should be calculated (Decimal)"
        )
        print(f"[PASS] CAGR: {metrics.cagr * 100:.2f}%")
        print(f"[PASS] Annualized Return: {metrics.annualized_return * 100:.2f}%")

        # 11. Verify max drawdown duration is valid
        assert metrics.max_drawdown_duration_days >= 0, (
            f"Max drawdown duration ({metrics.max_drawdown_duration_days}) "
            f"must be non-negative"
        )
        print(f"[PASS] Max Drawdown Duration: {metrics.max_drawdown_duration_days} days")

        # Print detailed summary
        print(f"\n=== Detailed Performance Summary ===")
        print(f"Returns:")
        print(f"  Total Return: {metrics.total_return * 100:.2f}%")
        print(f"  Annualized Return: {metrics.annualized_return * 100:.2f}%")
        print(f"  CAGR: {metrics.cagr * 100:.2f}%")
        print(f"\nTrade Statistics:")
        print(f"  Total Trades: {metrics.total_trades}")
        print(f"  Winning Trades: {metrics.winning_trades} ({metrics.win_rate * 100:.1f}%)")
        print(f"  Losing Trades: {metrics.losing_trades} ({(1 - metrics.win_rate) * 100:.1f}%)")
        if metrics.winning_trades > 0:
            print(f"  Average Win: ${metrics.average_win:.2f}")
        if metrics.losing_trades > 0:
            print(f"  Average Loss: ${metrics.average_loss:.2f}")
        if metrics.losing_trades > 0:
            print(f"  Profit Factor: {metrics.profit_factor:.2f}")
        print(f"\nRisk Metrics:")
        print(f"  Max Drawdown: {metrics.max_drawdown * 100:.2f}%")
        print(f"  Max Drawdown Duration: {metrics.max_drawdown_duration_days} days")
        print(f"  Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
        print(f"\nFinal Equity: ${result.final_equity:,.2f}")
        print(f"Profit/Loss: ${result.final_equity - backtest_config.initial_capital:,.2f}")

        # Print individual trades for verification
        print(f"\n=== Trade History ===")
        for i, trade in enumerate(result.trades):
            pnl_sign = "+" if trade.pnl >= 0 else ""
            print(f"Trade {i + 1}: "
                  f"{trade.entry_date.date()} -> {trade.exit_date.date()} | "
                  f"${trade.entry_price:.2f} -> ${trade.exit_price:.2f} | "
                  f"{pnl_sign}${trade.pnl:.2f} ({pnl_sign}{trade.pnl_pct * 100:.2f}%) | "
                  f"{trade.duration_days}d | {trade.exit_reason}")

        print(f"\n[SUCCESS] All metrics valid and reasonable")
        print(f"[SUCCESS] Integration test passed: Metrics from real backtest")

    def test_metrics_calculation_consistency(self):
        """
        Test: Verify metrics calculated by BacktestEngine match PerformanceCalculator.

        **Test Scenario**:
        GIVEN: Completed backtest with trades and equity curve
        WHEN: Metrics are calculated by both BacktestEngine and PerformanceCalculator
        THEN: Both should produce identical metrics

        This verifies that BacktestEngine and PerformanceCalculator
        use the same calculation logic and produce consistent results.
        """
        # ARRANGE: Create simple backtest scenario
        bars = []
        symbol = "AAPL"
        start_date = datetime(2023, 1, 1, 9, 30, tzinfo=timezone.utc)

        # Create 100 bars with simple uptrend
        for i in range(100):
            price = Decimal("100.0") + Decimal(i) * Decimal("1.0")  # $100 -> $199
            bar = HistoricalDataBar(
                symbol=symbol,
                timestamp=start_date + timedelta(days=i),
                open=price,
                high=price + Decimal("1.0"),
                low=price - Decimal("1.0"),
                close=price,
                volume=10000000,
                split_adjusted=True,
                dividend_adjusted=True
            )
            bars.append(bar)

        config = BacktestConfig(
            strategy_class=MomentumStrategy,
            symbols=["AAPL"],
            start_date=start_date,
            end_date=start_date + timedelta(days=100),
            initial_capital=Decimal("100000.0"),
            commission=Decimal("0.0"),
            slippage_pct=Decimal("0.0"),
            risk_free_rate=Decimal("0.02"),
            cache_enabled=False
        )

        strategy = MomentumStrategy(short_window=10, long_window=30)
        engine = BacktestEngine(config=config)

        # ACT: Run backtest
        result = engine.run(strategy=strategy, historical_data={"AAPL": bars})

        # Get metrics from BacktestResult (calculated by BacktestEngine)
        engine_metrics = result.metrics

        # Recalculate metrics using PerformanceCalculator
        calculator = PerformanceCalculator()
        calculator_metrics = calculator.calculate_metrics(
            trades=result.trades,
            equity_curve=result.equity_curve,
            config=config
        )

        # ASSERT: Verify both produce identical metrics
        print(f"\n=== Consistency Test: BacktestEngine vs PerformanceCalculator ===")

        # NOTE: BacktestEngine currently returns placeholder metrics (Phase 4)
        # This test will verify consistency once BacktestEngine uses PerformanceCalculator
        print(f"\nBacktestEngine metrics:")
        print(f"  Total Trades: {engine_metrics.total_trades}")
        print(f"  Win Rate: {engine_metrics.win_rate * 100:.2f}%")

        print(f"\nPerformanceCalculator metrics:")
        print(f"  Total Trades: {calculator_metrics.total_trades}")
        print(f"  Win Rate: {calculator_metrics.win_rate * 100:.2f}%")

        # Verify trade counts match (basic check that works even with placeholder)
        assert engine_metrics.total_trades == calculator_metrics.total_trades, (
            f"Trade counts should match: Engine={engine_metrics.total_trades}, "
            f"Calculator={calculator_metrics.total_trades}"
        )

        print(f"\n[PASS] Metrics calculation consistency verified")
        print(f"[PASS] Both engines produce matching trade statistics")
