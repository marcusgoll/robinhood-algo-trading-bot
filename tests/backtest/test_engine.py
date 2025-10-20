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
