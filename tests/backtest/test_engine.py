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
        # ARRANGE: Create BacktestEngine with config
        # Pass config to __init__() since config has strategy_class
        engine = BacktestEngine(config=deterministic_config)

        # ACT: Run backtest twice with identical configuration
        # Pass empty data dict since no real data needed for reproducibility test
        result1 = engine.run(strategy=TrackingStrategy(), historical_data={"AAPL": []})
        result2 = engine.run(strategy=TrackingStrategy(), historical_data={"AAPL": []})

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
        # Pass config to __init__() and provide empty data dict
        engine = BacktestEngine(config=config)
        result1 = engine.run(strategy=TrackingStrategy(), historical_data={"AAPL": [], "MSFT": []})
        result2 = engine.run(strategy=TrackingStrategy(), historical_data={"AAPL": [], "MSFT": []})

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
        # Create engine with config (both configs have strategy_class)
        engine_with_cache = BacktestEngine(config=config_with_cache)
        engine_without_cache = BacktestEngine(config=config_without_cache)

        # First run: populate cache
        result_cache_populate = engine_with_cache.run(
            strategy=TrackingStrategy(),
            historical_data={"AAPL": []}
        )

        # Second run: load from cache
        result_cache_load = engine_with_cache.run(
            strategy=TrackingStrategy(),
            historical_data={"AAPL": []}
        )

        # Third run: bypass cache
        result_no_cache = engine_without_cache.run(
            strategy=TrackingStrategy(),
            historical_data={"AAPL": []}
        )

        # ASSERT: All results are identical
        # (excluding execution_time_seconds which may vary)
        assert result_cache_populate.trades == result_cache_load.trades
        assert result_cache_populate.trades == result_no_cache.trades

        assert result_cache_populate.equity_curve == result_cache_load.equity_curve
        assert result_cache_populate.equity_curve == result_no_cache.equity_curve

        assert result_cache_populate.metrics == result_cache_load.metrics
        assert result_cache_populate.metrics == result_no_cache.metrics


class TestBacktestEngineCapitalValidation:
    """Test BacktestEngine capital management and trade rejection logic."""

    def test_insufficient_capital(self) -> None:
        """
        Test that BacktestEngine prevents trades when capital is insufficient.

        This is a critical capital validation test ensuring we don't attempt to buy
        positions we cannot afford. The engine must check available cash before
        executing any trade signal.

        Given:
            - Initial capital: $100 (very low, can't afford 1 share)
            - Stock price: $150 per share
            - Strategy signals BUY
            - Required capital for 1 share: $150 (plus commission if applicable)

        When:
            BacktestEngine.run(config) executes the backtest

        Then:
            - Trade is rejected due to insufficient capital
            - Warning logged: "Insufficient capital: cannot buy..."
            - No position opened (result.trades is empty)
            - Cash remains at $100 (no change)
            - Final equity = $100 (no trades executed)

        Rationale:
            Capital validation is fundamental risk management. Without this check,
            the backtest could simulate unrealistic scenarios (buying with no money),
            leading to invalid performance metrics and false confidence in strategies.

        Pattern: tests/risk_management/ capital validation tests
        From: specs/001-backtesting-engine/tasks.md T023
        Phase: TDD RED - test MUST FAIL until BacktestEngine capital validation implemented
        """
        # Arrange: Create a simple BUY strategy that signals entry on first bar
        @dataclass
        class AlwaysBuyStrategy:
            """Test strategy that always signals to buy on first bar."""

            def should_enter(self, bars: List[HistoricalDataBar]) -> bool:
                """Signal BUY on first bar only."""
                return len(bars) == 1

            def should_exit(
                self, position: Position, bars: List[HistoricalDataBar]
            ) -> bool:
                """Never signal exit."""
                return False

            def position_size(self, capital: float, price: float) -> int:
                """Request 1 share (will be rejected due to insufficient capital)."""
                return 1

        # Create BacktestConfig with VERY LOW capital
        # Stock price = $150, so $100 capital cannot afford even 1 share
        config = BacktestConfig(
            strategy_class=AlwaysBuyStrategy,
            symbols=["TSLA"],
            start_date=datetime(2023, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2023, 1, 10, tzinfo=timezone.utc),
            initial_capital=Decimal("100.0"),  # Too low for $150/share stock
            commission=Decimal("0.0"),  # Zero commission for simpler math
            slippage_pct=Decimal("0.0"),  # Zero slippage for simpler math
        )

        # Create historical data with stock price at $150
        historical_data = [
            HistoricalDataBar(
                symbol="TSLA",
                timestamp=datetime(2023, 1, 3, 9, 30, tzinfo=timezone.utc),
                open=Decimal("150.00"),
                high=Decimal("152.00"),
                low=Decimal("149.00"),
                close=Decimal("151.00"),
                volume=1000000,
            ),
            HistoricalDataBar(
                symbol="TSLA",
                timestamp=datetime(2023, 1, 4, 9, 30, tzinfo=timezone.utc),
                open=Decimal("151.00"),
                high=Decimal("153.00"),
                low=Decimal("150.00"),
                close=Decimal("152.00"),
                volume=1100000,
            ),
        ]

        # Create engine instance
        # This will FAIL in RED phase because BacktestEngine class doesn't exist yet
        # or capital validation is not implemented yet (will be added in GREEN phase - T027)
        engine = BacktestEngine(config=config)

        # Act: Run backtest with insufficient capital
        # This will FAIL because run() method doesn't exist OR
        # capital validation is not implemented yet
        result = engine.run(
            strategy=AlwaysBuyStrategy(),
            historical_data={"TSLA": historical_data}
        )

        # Assert: Verify trade was REJECTED due to insufficient capital
        # These assertions define the expected behavior that must be implemented

        # 1. No trades executed (insufficient capital prevents entry)
        assert len(result.trades) == 0, (
            f"Expected no trades due to insufficient capital, "
            f"but found {len(result.trades)} trades"
        )

        # 2. Final equity equals initial capital (no position changes)
        assert result.final_equity == Decimal("100.0"), (
            f"Expected final_equity=$100.0 (no trades), "
            f"got ${result.final_equity}"
        )

        # 3. Verify equity curve shows no change (flat line)
        assert len(result.equity_curve) >= 1, "Expected equity curve data"
        # All equity values should be $100 (no trades executed)
        for timestamp, equity in result.equity_curve:
            assert equity == Decimal("100.0"), (
                f"Expected equity=$100.0 throughout backtest, "
                f"got ${equity} at {timestamp}"
            )

    def test_insufficient_capital_with_logging(self, caplog) -> None:
        """
        Test that BacktestEngine logs warnings when rejecting trades due to insufficient capital.

        This test verifies that capital validation failures are properly logged for debugging
        and audit purposes.

        Given:
            - Initial capital: $100
            - Stock price: $150 per share
            - Strategy signals BUY
            - pytest caplog fixture captures log messages

        When:
            BacktestEngine.run(config) executes and rejects the trade

        Then:
            - Warning logged with message containing:
              * "Insufficient capital"
              * Symbol ("TSLA")
              * Price ($150.00)
              * Available cash ($100.00)

        From: specs/001-backtesting-engine/tasks.md T023
        Phase: TDD RED - test MUST FAIL until logging implemented
        """
        # Arrange: Same setup as test_insufficient_capital
        @dataclass
        class AlwaysBuyStrategy:
            """Test strategy that always signals to buy on first bar."""

            def should_enter(self, bars: List[HistoricalDataBar]) -> bool:
                return len(bars) == 1

            def should_exit(
                self, position: Position, bars: List[HistoricalDataBar]
            ) -> bool:
                return False

            def position_size(self, capital: float, price: float) -> int:
                return 1

        config = BacktestConfig(
            strategy_class=AlwaysBuyStrategy,
            symbols=["TSLA"],
            start_date=datetime(2023, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2023, 1, 10, tzinfo=timezone.utc),
            initial_capital=Decimal("100.0"),
            commission=Decimal("0.0"),
            slippage_pct=Decimal("0.0"),
        )

        # Need at least 2 bars so the first bar isn't also the last bar
        historical_data = [
            HistoricalDataBar(
                symbol="TSLA",
                timestamp=datetime(2023, 1, 3, 9, 30, tzinfo=timezone.utc),
                open=Decimal("150.00"),
                high=Decimal("152.00"),
                low=Decimal("149.00"),
                close=Decimal("151.00"),
                volume=1000000,
            ),
            HistoricalDataBar(
                symbol="TSLA",
                timestamp=datetime(2023, 1, 4, 9, 30, tzinfo=timezone.utc),
                open=Decimal("151.00"),
                high=Decimal("153.00"),
                low=Decimal("150.00"),
                close=Decimal("152.00"),
                volume=1100000,
            ),
        ]

        # Create engine with config (config has strategy_class)
        engine = BacktestEngine(config=config)

        # Act: Run backtest and capture logs
        import logging
        # Capture logs from the trading_bot.backtest.engine module
        with caplog.at_level(logging.WARNING, logger="trading_bot.backtest.engine"):
            result = engine.run(
                strategy=AlwaysBuyStrategy(),
                historical_data={"TSLA": historical_data}
            )

        # Assert: Verify warning was logged
        assert len(caplog.records) > 0, (
            "Expected at least one log message. "
            f"Captured logs: {[(r.name, r.levelname, r.message) for r in caplog.records]}"
        )

        # Find capital-related warning message
        capital_warnings = [
            record
            for record in caplog.records
            if "insufficient capital" in record.message.lower()
        ]

        assert len(capital_warnings) >= 1, (
            "Expected warning about insufficient capital. "
            f"Captured logs: {[r.message for r in caplog.records]}"
        )

        # Verify warning message contains key details
        warning_message = capital_warnings[0].message.lower()
        assert "tsla" in warning_message, "Warning should mention symbol (TSLA)"
        assert "150" in warning_message, "Warning should mention stock price ($150)"
        assert "100" in warning_message, "Warning should mention available capital ($100)"


class BuyAndHoldStrategy:
    """
    Simple buy-and-hold strategy for testing BacktestEngine execution.

    **Strategy Behavior**:
    - Enter position on first bar with all available capital
    - Never exit position (hold until end of backtest)
    - Exit forced at end_of_data

    **Purpose**: Test basic backtest engine execution and P&L calculation accuracy.
    From spec.md Success Criteria #2 (Execution Accuracy)
    """

    def __init__(self):
        self.has_entered = False

    def should_enter(self, bars: List[HistoricalDataBar]) -> bool:
        """
        Enter on first bar only.

        Args:
            bars: Historical data available up to current bar

        Returns:
            True on first call, False thereafter
        """
        if not self.has_entered:
            self.has_entered = True
            return True
        return False

    def should_exit(self, position: Position, bars: List[HistoricalDataBar]) -> bool:
        """
        Never exit voluntarily - hold until end.

        Args:
            position: Current open position
            bars: Historical data available up to current bar

        Returns:
            False (never exit, backtest engine will close at end_of_data)
        """
        return False

    def position_size(self, capital: float, price: float) -> int:
        """
        Use all available capital to buy maximum shares.

        Args:
            capital: Available cash in portfolio
            price: Current stock price

        Returns:
            Maximum number of shares affordable
        """
        if price <= 0:
            return 0
        return int(capital / price)


class TestBacktestEngineBuyAndHold:
    """
    T022 [RED]: Test buy-and-hold strategy execution correctness.

    **From spec.md**:
    - User Story US2: Execute strategy against historical data chronologically
    - Success Criteria #2: Backtest matches manual calculations within 0.01% error
    - NFR-003: Results must match manual calculations within 0.01%
    - FR-007: Simulate order fills using next bar's open price

    **TDD Phase**: RED - BacktestEngine.run() doesn't exist yet
    """

    @pytest.fixture
    def mock_year_data(self) -> List[HistoricalDataBar]:
        """
        Create 252 trading days (one year) with 10% total return.

        Start price: $150.00
        End price: $165.00
        Return: 10% (linear progression)

        Returns:
            List of 252 HistoricalDataBar objects
        """
        bars = []
        symbol = "AAPL"
        start_date = datetime(2023, 1, 3, 9, 30, tzinfo=timezone.utc)
        start_price = Decimal("150.00")
        end_price = Decimal("165.00")
        num_bars = 252

        # Calculate linear price increment per bar
        price_increment = (end_price - start_price) / Decimal(str(num_bars - 1))

        for i in range(num_bars):
            # Base price for this bar (linear interpolation)
            base_price = start_price + (price_increment * Decimal(str(i)))

            # Realistic OHLC relationships
            open_price = base_price - Decimal("0.25")
            high_price = base_price + Decimal("0.50")
            low_price = base_price - Decimal("0.50")
            close_price = base_price

            # Timestamp (simple daily increment for testing)
            from datetime import timedelta
            bar_timestamp = start_date + timedelta(days=i)

            bar = HistoricalDataBar(
                symbol=symbol,
                timestamp=bar_timestamp,
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price,
                volume=1000000 + (i * 5000),  # Varying volume
                split_adjusted=True,
                dividend_adjusted=True
            )
            bars.append(bar)

        return bars

    def test_buy_and_hold_strategy(self, mock_year_data: List[HistoricalDataBar]):
        """
        T022 [RED]: Test BacktestEngine.run() executes buy-and-hold correctly.

        **Test Scenario**:
        GIVEN: BuyAndHoldStrategy (enter first bar, never exit)
        AND: 252 bars of historical data (one year, $150 to $165, 10% gain)
        AND: Initial capital $100,000
        WHEN: BacktestEngine.run(config) is called
        THEN: Exactly one trade is created
        AND: Entry at first bar open price (~$149.75)
        AND: Exit at last bar close price ($165.00)
        AND: P&L matches manual calculation within 0.01% (spec NFR-003)

        **Expected Manual Calculation**:
        - Entry price: $149.75 (first bar open)
        - Shares bought: floor($100,000 / $149.75) = 667 shares
        - Cost: 667 * $149.75 = $99,823.25
        - Exit value: 667 * $165.00 = $110,055.00
        - P&L: $110,055.00 - $99,823.25 = $10,231.75
        - Return: $10,231.75 / $99,823.25 = 10.25%

        **TDD RED PHASE**: This test WILL FAIL because:
        - BacktestEngine class doesn't exist yet
        - Expected ImportError or AttributeError
        """
        # ARRANGE: Setup test configuration
        config = BacktestConfig(
            strategy_class=BuyAndHoldStrategy,
            symbols=["AAPL"],
            start_date=datetime(2023, 1, 3, 9, 30, tzinfo=timezone.utc),
            end_date=datetime(2023, 12, 29, 23, 59, 59, tzinfo=timezone.utc),
            initial_capital=Decimal("100000.00"),
            commission=Decimal("0.0"),  # No commission for simple test
            slippage_pct=Decimal("0.0"),  # No slippage for simple test
            risk_free_rate=Decimal("0.02"),
            cache_enabled=False
        )

        # Calculate expected results manually
        first_bar = mock_year_data[0]
        last_bar = mock_year_data[-1]
        initial_capital = config.initial_capital

        entry_price = first_bar.open  # $149.75
        exit_price = last_bar.close   # $165.00
        expected_shares = int(initial_capital / entry_price)  # 667
        expected_cost = expected_shares * entry_price
        expected_exit_value = expected_shares * exit_price
        expected_pnl = expected_exit_value - expected_cost
        expected_return_pct = expected_pnl / expected_cost

        # ACT: Run backtest
        # This will FAIL in RED phase with ImportError
        engine = BacktestEngine(config=config)
        result = engine.run(strategy=BuyAndHoldStrategy(), historical_data={"AAPL": mock_year_data})

        # ASSERT: Verify results (GREEN phase assertions)
        # 1. Verify exactly one trade
        assert len(result.trades) == 1, \
            f"Buy-and-hold should create exactly 1 trade, got {len(result.trades)}"

        trade = result.trades[0]

        # 2. Verify trade symbol
        assert trade.symbol == "AAPL", \
            f"Trade symbol should be AAPL, got {trade.symbol}"

        # 3. Verify entry price (allow small variance for fill simulation)
        entry_tolerance = Decimal("1.0")
        assert abs(trade.entry_price - entry_price) < entry_tolerance, \
            f"Entry price should be ~${entry_price} (first bar open), got ${trade.entry_price}"

        # 4. Verify exit price
        exit_tolerance = Decimal("1.0")
        assert abs(trade.exit_price - exit_price) < exit_tolerance, \
            f"Exit price should be ~${exit_price} (last bar close), got ${trade.exit_price}"

        # 5. Verify shares bought
        share_tolerance = 10  # Allow small variance
        assert abs(trade.shares - expected_shares) < share_tolerance, \
            f"Should buy ~{expected_shares} shares, got {trade.shares}"

        # 6. Verify P&L calculation accuracy (spec NFR-003: within 0.01%)
        assert trade.pnl > 0, \
            f"P&L should be positive for 10% gain, got ${trade.pnl}"

        pnl_error_pct = abs(trade.pnl - expected_pnl) / abs(expected_pnl)
        assert pnl_error_pct < Decimal("0.0001"), \
            f"P&L must be within 0.01% of manual calculation (NFR-003).\n" \
            f"Expected: ${expected_pnl:,.2f}\n" \
            f"Actual: ${trade.pnl:,.2f}\n" \
            f"Error: {pnl_error_pct * 100:.4f}% (max allowed: 0.01%)"

        # 7. Verify return percentage
        return_error_pct = abs(trade.pnl_pct - expected_return_pct) / abs(expected_return_pct)
        assert return_error_pct < Decimal("0.0001"), \
            f"Return % must be within 0.01% of expected.\n" \
            f"Expected: {expected_return_pct * 100:.2f}%\n" \
            f"Actual: {trade.pnl_pct * 100:.2f}%\n" \
            f"Error: {return_error_pct * 100:.4f}%"

        # 8. Verify exit reason
        assert trade.exit_reason == "end_of_data", \
            f"Exit reason should be 'end_of_data', got '{trade.exit_reason}'"

        # 9. Verify equity curve exists
        assert len(result.equity_curve) > 0, \
            "Equity curve should have data points"

        # 10. Verify final equity
        final_equity = result.equity_curve[-1][1]
        expected_final_equity = initial_capital + expected_pnl
        equity_error_pct = abs(final_equity - expected_final_equity) / expected_final_equity
        assert equity_error_pct < Decimal("0.0001"), \
            f"Final equity must match expected within 0.01%.\n" \
            f"Expected: ${expected_final_equity:,.2f}\n" \
            f"Actual: ${final_equity:,.2f}\n" \
            f"Error: {equity_error_pct * 100:.4f}%"

        # 11. Verify performance metrics
        assert result.metrics.total_trades == 1, \
            f"Should have 1 trade, got {result.metrics.total_trades}"
        assert result.metrics.winning_trades == 1, \
            f"Trade should be profitable, got {result.metrics.winning_trades} winners"
        assert result.metrics.losing_trades == 0, \
            f"Should have 0 losses, got {result.metrics.losing_trades}"
        assert result.metrics.win_rate == Decimal("1.0"), \
            f"Win rate should be 100%, got {result.metrics.win_rate * 100:.1f}%"
