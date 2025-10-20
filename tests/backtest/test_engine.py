"""
Tests for BacktestEngine execution logic.

Tests chronological execution (no look-ahead bias), buy-and-hold strategy,
capital validation, and reproducibility. Following TDD RED phase - tests
written before BacktestEngine implementation.
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from dataclasses import dataclass

from src.trading_bot.backtest.models import (
    HistoricalDataBar,
    Position,
    BacktestConfig,
    Trade,
)

# Import will FAIL because BacktestEngine doesn't exist yet (TDD RED phase)
from src.trading_bot.backtest.engine import BacktestEngine


@dataclass
class TrackingStrategy:
    """
    Test strategy that records visible data at each bar to detect look-ahead bias.

    This strategy tracks what data is available when each bar is processed.
    Used to verify chronological execution and absence of look-ahead bias.
    """
    visible_timestamps: List[datetime] = None
    visible_bars: List[List[HistoricalDataBar]] = None

    def __post_init__(self):
        """Initialize tracking lists."""
        if self.visible_timestamps is None:
            self.visible_timestamps = []
        if self.visible_bars is None:
            self.visible_bars = []

    def should_enter(self, bars: List[HistoricalDataBar]) -> bool:
        """
        Record what bars are visible and always return False (no trades).

        Args:
            bars: Historical data bars available at this point in time

        Returns:
            False (this strategy never enters trades, just tracks visibility)
        """
        # Record the current bar being processed (last bar in the list)
        if bars:
            current_bar = bars[-1]
            self.visible_timestamps.append(current_bar.timestamp)
            # Store a copy of all visible bars at this point
            self.visible_bars.append(bars.copy())

        return False  # Never enter trades

    def should_exit(self, position: Position, bars: List[HistoricalDataBar]) -> bool:
        """
        Strategy never enters, so this won't be called.

        Args:
            position: Current position (won't exist for this strategy)
            bars: Historical data bars available at this point

        Returns:
            False
        """
        return False

    def position_size(self, capital: float, price: float) -> int:
        """
        Return default position size (not used by this strategy).

        Args:
            capital: Available capital
            price: Current price

        Returns:
            Default of 100 shares
        """
        return 100


class TestBacktestEngineChronologicalExecution:
    """Test BacktestEngine chronological execution and look-ahead bias prevention."""

    @pytest.fixture
    def mock_historical_data(self) -> List[HistoricalDataBar]:
        """
        Create 10 bars of mock historical data with unique identifiers.

        Each bar has a unique timestamp and price to make it identifiable.
        This allows us to verify exact execution order and data visibility.

        Returns:
            List of 10 HistoricalDataBar objects with sequential timestamps
        """
        bars = []
        base_date = datetime(2024, 1, 2, 9, 30, tzinfo=timezone.utc)  # Trading day

        for i in range(10):
            bar = HistoricalDataBar(
                symbol="TEST",
                timestamp=datetime(2024, 1, 2 + i, 9, 30, tzinfo=timezone.utc),
                open=Decimal(f"{100 + i}.00"),
                high=Decimal(f"{102 + i}.00"),
                low=Decimal(f"{99 + i}.00"),
                close=Decimal(f"{101 + i}.00"),
                volume=1000000 + (i * 10000),
                split_adjusted=True,
                dividend_adjusted=True,
            )
            bars.append(bar)

        return bars

    @pytest.fixture
    def backtest_config(self) -> BacktestConfig:
        """
        Create minimal BacktestConfig for testing.

        Returns:
            BacktestConfig with TrackingStrategy and 10-day date range
        """
        return BacktestConfig(
            strategy_class=TrackingStrategy,
            symbols=["TEST"],
            start_date=datetime(2024, 1, 2, tzinfo=timezone.utc),
            end_date=datetime(2024, 1, 12, tzinfo=timezone.utc),
            initial_capital=Decimal("100000.0"),
            commission=Decimal("0.0"),
            slippage_pct=Decimal("0.0"),
            cache_enabled=False,  # Don't cache test data
        )

    def test_chronological_execution(
        self,
        mock_historical_data: List[HistoricalDataBar],
        backtest_config: BacktestConfig
    ):
        """
        Test: BacktestEngine processes bars in chronological order without look-ahead bias.

        **Acceptance Criteria**:
        1. Strategy processes bars in exact chronological order (bar[0] → bar[9])
        2. At bar[i], strategy can only see bars[0:i+1], not future bars[i+1:]
        3. Number of calls to should_enter() equals number of bars (10)
        4. Each call has progressively more visible data (1 bar, then 2, then 3, etc.)
        5. No future bar timestamps are visible when processing current bar

        **Look-Ahead Bias Prevention**:
        - When processing bar at index i=5 (timestamp 2024-01-07):
          * Can see bars 0-5 (timestamps 2024-01-02 through 2024-01-07)
          * Cannot see bars 6-9 (timestamps 2024-01-08 through 2024-01-11)

        This test will FAIL because BacktestEngine doesn't exist yet (TDD RED phase).
        """
        # Arrange: Create engine and strategy
        engine = BacktestEngine(config=backtest_config)
        strategy = TrackingStrategy()

        # Act: Run backtest (engine will call should_enter() for each bar)
        # NOTE: This will fail with ImportError in RED phase
        result = engine.run(strategy=strategy, historical_data=mock_historical_data)

        # Assert 1: Strategy was called exactly once per bar
        assert len(strategy.visible_timestamps) == 10, (
            f"Expected 10 calls to should_enter() (one per bar), "
            f"got {len(strategy.visible_timestamps)}"
        )

        # Assert 2: Bars were processed in chronological order
        expected_timestamps = [bar.timestamp for bar in mock_historical_data]
        assert strategy.visible_timestamps == expected_timestamps, (
            "Bars were not processed in chronological order. "
            f"Expected: {expected_timestamps}, "
            f"Got: {strategy.visible_timestamps}"
        )

        # Assert 3: At each step, strategy could only see past data (no look-ahead bias)
        for i, visible_bars_at_step in enumerate(strategy.visible_bars):
            # At step i, strategy should see bars[0:i+1]
            expected_count = i + 1
            actual_count = len(visible_bars_at_step)

            assert actual_count == expected_count, (
                f"At bar {i}, strategy should see {expected_count} bars (0 to {i}), "
                f"but saw {actual_count} bars. This indicates look-ahead bias!"
            )

            # Verify the last visible bar is the current bar being processed
            current_bar = mock_historical_data[i]
            visible_current_bar = visible_bars_at_step[-1]

            assert visible_current_bar.timestamp == current_bar.timestamp, (
                f"At bar {i}, last visible bar timestamp should be {current_bar.timestamp}, "
                f"but was {visible_current_bar.timestamp}"
            )

            # Verify no future bars are visible
            future_timestamps = [bar.timestamp for bar in mock_historical_data[i+1:]]
            visible_timestamps = [bar.timestamp for bar in visible_bars_at_step]

            for future_ts in future_timestamps:
                assert future_ts not in visible_timestamps, (
                    f"LOOK-AHEAD BIAS DETECTED! At bar {i} ({current_bar.timestamp}), "
                    f"strategy can see future bar {future_ts}"
                )

        # Assert 4: Verify first bar sees only itself, last bar sees all 10
        assert len(strategy.visible_bars[0]) == 1, "First bar should only see itself"
        assert len(strategy.visible_bars[-1]) == 10, "Last bar should see all 10 bars"

        # Assert 5: No trades were made (TrackingStrategy never enters)
        assert len(result.trades) == 0, (
            f"TrackingStrategy should not make any trades, but found {len(result.trades)}"
        )

    def test_chronological_execution_validates_bar_data_visibility(
        self,
        mock_historical_data: List[HistoricalDataBar],
        backtest_config: BacktestConfig
    ):
        """
        Test: Verify specific example of no look-ahead bias at bar index 5.

        **Detailed Verification**:
        - At bar index 5 (timestamp 2024-01-07, close price $106.00):
          * Strategy CAN see bars 0-5 (Jan 2-7)
          * Strategy CANNOT see bars 6-9 (Jan 8-11)

        This is a focused test to verify the core anti-look-ahead logic.
        """
        # Arrange
        engine = BacktestEngine(config=backtest_config)
        strategy = TrackingStrategy()

        # Act
        result = engine.run(strategy=strategy, historical_data=mock_historical_data)

        # Assert: Focus on bar index 5
        bar_index = 5
        visible_at_bar_5 = strategy.visible_bars[bar_index]

        # Should see exactly 6 bars (indices 0-5)
        assert len(visible_at_bar_5) == 6, (
            f"At bar 5, should see 6 bars (indices 0-5), but saw {len(visible_at_bar_5)}"
        )

        # Verify visible timestamps are exactly bars 0-5
        expected_visible = [mock_historical_data[i].timestamp for i in range(6)]
        actual_visible = [bar.timestamp for bar in visible_at_bar_5]

        assert actual_visible == expected_visible, (
            f"At bar 5, visible timestamps should be {expected_visible}, "
            f"but were {actual_visible}"
        )

        # Verify future bars (6-9) are NOT visible
        future_bars = mock_historical_data[6:]
        future_timestamps = [bar.timestamp for bar in future_bars]

        for future_ts in future_timestamps:
            assert future_ts not in actual_visible, (
                f"LOOK-AHEAD BIAS! At bar 5, can see future timestamp {future_ts}"
            )

        # Verify the close prices to ensure correct bar data
        # Bar 5 should have close price of $106.00 (100 + 5 + 1)
        current_bar = visible_at_bar_5[-1]
        assert current_bar.close == Decimal("106.00"), (
            f"Bar 5 should have close price $106.00, but has {current_bar.close}"
        )


class TestBacktestEngineReproducibility:
    """
    Test Suite: Reproducibility (NFR-010)

    Verifies that backtest engine produces deterministic, reproducible results.
    Running the same configuration multiple times must produce identical outcomes.

    From: spec.md NFR-010, tasks.md T024
    TDD Phase: RED (tests written before BacktestEngine implementation)
    """

    @pytest.fixture
    def deterministic_config(self) -> BacktestConfig:
        """
        Create BacktestConfig with fixed parameters for reproducibility testing.

        Fixed seed, dates, and parameters ensure deterministic execution.
        Any randomness should produce the same sequence given the same config.

        Returns:
            BacktestConfig with deterministic parameters
        """
        return BacktestConfig(
            strategy_class=TrackingStrategy,
            symbols=["AAPL"],
            start_date=datetime(2023, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2023, 12, 31, tzinfo=timezone.utc),
            initial_capital=Decimal("100000.0"),
            commission=Decimal("0.0"),
            slippage_pct=Decimal("0.001"),
            risk_free_rate=Decimal("0.02"),
            cache_enabled=True,
        )

    def test_reproducibility(self, deterministic_config: BacktestConfig):
        """
        Test: Reproducibility - Same inputs produce identical outputs (NFR-010).

        **Acceptance Criteria**:
        1. Run backtest twice with identical BacktestConfig
        2. Both runs produce identical results:
           - Same number of trades
           - Identical trade entry/exit prices, dates, and durations
           - Identical trade P&L and P&L percentages
           - Identical performance metrics (total_return, sharpe_ratio, win_rate, etc.)
           - Identical equity curve (timestamps and values)
           - Identical data warnings

        **Determinism Requirements**:
        - Fixed random seeds if any randomness is used
        - Consistent data loading order from cache
        - Consistent strategy execution logic
        - Consistent float/Decimal arithmetic

        This test will FAIL because BacktestEngine doesn't exist yet (TDD RED phase).

        From: spec.md NFR-010 (Reproducibility), spec.md Success Criteria #4
        """
        # ARRANGE: Create BacktestEngine
        # This will fail with ImportError until BacktestEngine is implemented
        engine = BacktestEngine()

        # ACT: Run backtest twice with identical configuration
        result1 = engine.run(deterministic_config)
        result2 = engine.run(deterministic_config)

        # ASSERT 1: Same number of trades
        assert len(result1.trades) == len(result2.trades), (
            f"Trade count mismatch between runs: "
            f"run1={len(result1.trades)}, run2={len(result2.trades)}"
        )

        # ASSERT 2: Identical trades (entry/exit prices, dates, shares, P&L)
        for i, (trade1, trade2) in enumerate(zip(result1.trades, result2.trades)):
            assert trade1.symbol == trade2.symbol, (
                f"Trade {i}: symbol mismatch ({trade1.symbol} != {trade2.symbol})"
            )
            assert trade1.entry_date == trade2.entry_date, (
                f"Trade {i}: entry_date mismatch ({trade1.entry_date} != {trade2.entry_date})"
            )
            assert trade1.entry_price == trade2.entry_price, (
                f"Trade {i}: entry_price mismatch ({trade1.entry_price} != {trade2.entry_price})"
            )
            assert trade1.exit_date == trade2.exit_date, (
                f"Trade {i}: exit_date mismatch ({trade1.exit_date} != {trade2.exit_date})"
            )
            assert trade1.exit_price == trade2.exit_price, (
                f"Trade {i}: exit_price mismatch ({trade1.exit_price} != {trade2.exit_price})"
            )
            assert trade1.shares == trade2.shares, (
                f"Trade {i}: shares mismatch ({trade1.shares} != {trade2.shares})"
            )
            assert trade1.pnl == trade2.pnl, (
                f"Trade {i}: pnl mismatch ({trade1.pnl} != {trade2.pnl})"
            )
            assert trade1.pnl_pct == trade2.pnl_pct, (
                f"Trade {i}: pnl_pct mismatch ({trade1.pnl_pct} != {trade2.pnl_pct})"
            )
            assert trade1.duration_days == trade2.duration_days, (
                f"Trade {i}: duration_days mismatch "
                f"({trade1.duration_days} != {trade2.duration_days})"
            )
            assert trade1.exit_reason == trade2.exit_reason, (
                f"Trade {i}: exit_reason mismatch "
                f"({trade1.exit_reason} != {trade2.exit_reason})"
            )
            assert trade1.commission == trade2.commission, (
                f"Trade {i}: commission mismatch ({trade1.commission} != {trade2.commission})"
            )
            assert trade1.slippage == trade2.slippage, (
                f"Trade {i}: slippage mismatch ({trade1.slippage} != {trade2.slippage})"
            )

        # ASSERT 3: Identical performance metrics
        metrics1 = result1.metrics
        metrics2 = result2.metrics

        assert metrics1.total_return == metrics2.total_return, (
            f"total_return mismatch ({metrics1.total_return} != {metrics2.total_return})"
        )
        assert metrics1.annualized_return == metrics2.annualized_return, (
            f"annualized_return mismatch "
            f"({metrics1.annualized_return} != {metrics2.annualized_return})"
        )
        assert metrics1.cagr == metrics2.cagr, (
            f"cagr mismatch ({metrics1.cagr} != {metrics2.cagr})"
        )
        assert metrics1.win_rate == metrics2.win_rate, (
            f"win_rate mismatch ({metrics1.win_rate} != {metrics2.win_rate})"
        )
        assert metrics1.profit_factor == metrics2.profit_factor, (
            f"profit_factor mismatch ({metrics1.profit_factor} != {metrics2.profit_factor})"
        )
        assert metrics1.average_win == metrics2.average_win, (
            f"average_win mismatch ({metrics1.average_win} != {metrics2.average_win})"
        )
        assert metrics1.average_loss == metrics2.average_loss, (
            f"average_loss mismatch ({metrics1.average_loss} != {metrics2.average_loss})"
        )
        assert metrics1.max_drawdown == metrics2.max_drawdown, (
            f"max_drawdown mismatch ({metrics1.max_drawdown} != {metrics2.max_drawdown})"
        )
        assert metrics1.max_drawdown_duration_days == metrics2.max_drawdown_duration_days, (
            f"max_drawdown_duration_days mismatch "
            f"({metrics1.max_drawdown_duration_days} != {metrics2.max_drawdown_duration_days})"
        )
        assert metrics1.sharpe_ratio == metrics2.sharpe_ratio, (
            f"sharpe_ratio mismatch ({metrics1.sharpe_ratio} != {metrics2.sharpe_ratio})"
        )
        assert metrics1.total_trades == metrics2.total_trades, (
            f"total_trades mismatch ({metrics1.total_trades} != {metrics2.total_trades})"
        )
        assert metrics1.winning_trades == metrics2.winning_trades, (
            f"winning_trades mismatch "
            f"({metrics1.winning_trades} != {metrics2.winning_trades})"
        )
        assert metrics1.losing_trades == metrics2.losing_trades, (
            f"losing_trades mismatch ({metrics1.losing_trades} != {metrics2.losing_trades})"
        )

        # ASSERT 4: Identical equity curve (timestamps and values)
        assert len(result1.equity_curve) == len(result2.equity_curve), (
            f"Equity curve length mismatch: "
            f"run1={len(result1.equity_curve)}, run2={len(result2.equity_curve)}"
        )

        for i, ((ts1, value1), (ts2, value2)) in enumerate(
            zip(result1.equity_curve, result2.equity_curve)
        ):
            assert ts1 == ts2, (
                f"Equity curve point {i}: timestamp mismatch ({ts1} != {ts2})"
            )
            assert value1 == value2, (
                f"Equity curve point {i}: value mismatch ({value1} != {value2})"
            )

        # ASSERT 5: Identical data warnings (deterministic data loading)
        assert result1.data_warnings == result2.data_warnings, (
            f"data_warnings mismatch: "
            f"run1={result1.data_warnings}, run2={result2.data_warnings}"
        )

    def test_reproducibility_with_multiple_trades(self):
        """
        Test: Reproducibility with complex strategy generating multiple trades.

        **Scenario**: Use a strategy that generates multiple buy/sell signals
        to verify reproducibility holds for non-trivial backtests.

        **Expected**: 10 identical trades with exact same entry/exit points.

        This test ensures reproducibility isn't just for simple cases but
        holds for realistic trading scenarios with multiple positions.

        TDD Phase: RED (expected to fail - BacktestEngine not implemented)
        """
        # ARRANGE: Create config with a more complex strategy
        # (This would use a real momentum or mean-reversion strategy)
        # For now, using TrackingStrategy as placeholder

        config = BacktestConfig(
            strategy_class=TrackingStrategy,
            symbols=["AAPL", "MSFT"],  # Multiple symbols
            start_date=datetime(2023, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2023, 6, 30, tzinfo=timezone.utc),
            initial_capital=Decimal("100000.0"),
            commission=Decimal("1.0"),  # $1 commission
            slippage_pct=Decimal("0.002"),  # 0.2% slippage
            risk_free_rate=Decimal("0.04"),
            cache_enabled=True,
        )

        # ACT: Run backtest twice
        engine = BacktestEngine()
        result1 = engine.run(config)
        result2 = engine.run(config)

        # ASSERT: All fields match
        # Using dataclass equality (BacktestResult is frozen)
        # Note: Exclude execution_time_seconds and completed_at as they vary
        assert result1.config == result2.config
        assert result1.trades == result2.trades
        assert result1.equity_curve == result2.equity_curve
        assert result1.metrics == result2.metrics
        assert result1.data_warnings == result2.data_warnings

    def test_reproducibility_across_cache_states(self, deterministic_config: BacktestConfig):
        """
        Test: Reproducibility with and without cache.

        **Scenario**:
        1. Run backtest with cache_enabled=True (first run caches data)
        2. Run backtest with cache_enabled=True (second run loads from cache)
        3. Run backtest with cache_enabled=False (bypasses cache)

        **Expected**: All three runs produce identical results.

        This verifies that caching doesn't introduce non-determinism.

        TDD Phase: RED (expected to fail - BacktestEngine not implemented)
        """
        # ARRANGE: Create three configs with different cache settings
        config_with_cache = BacktestConfig(
            strategy_class=TrackingStrategy,
            symbols=["AAPL"],
            start_date=datetime(2023, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2023, 3, 31, tzinfo=timezone.utc),
            initial_capital=Decimal("100000.0"),
            commission=Decimal("0.0"),
            slippage_pct=Decimal("0.001"),
            risk_free_rate=Decimal("0.02"),
            cache_enabled=True,
        )

        config_without_cache = BacktestConfig(
            strategy_class=TrackingStrategy,
            symbols=["AAPL"],
            start_date=datetime(2023, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2023, 3, 31, tzinfo=timezone.utc),
            initial_capital=Decimal("100000.0"),
            commission=Decimal("0.0"),
            slippage_pct=Decimal("0.001"),
            risk_free_rate=Decimal("0.02"),
            cache_enabled=False,
        )

        # ACT: Run backtests
        engine = BacktestEngine()

        # First run: populate cache
        result_cache_populate = engine.run(config_with_cache)

        # Second run: load from cache
        result_cache_load = engine.run(config_with_cache)

        # Third run: bypass cache
        result_no_cache = engine.run(config_without_cache)

        # ASSERT: All results are identical
        # (excluding execution_time_seconds which may vary)
        assert result_cache_populate.trades == result_cache_load.trades
        assert result_cache_populate.trades == result_no_cache.trades

        assert result_cache_populate.equity_curve == result_cache_load.equity_curve
        assert result_cache_populate.equity_curve == result_no_cache.equity_curve

        assert result_cache_populate.metrics == result_cache_load.metrics
        assert result_cache_populate.metrics == result_no_cache.metrics
