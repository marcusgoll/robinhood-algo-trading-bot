"""
Sample Trading Strategies for Backtesting

Example strategy implementations demonstrating the IStrategy protocol.
These strategies serve as templates for custom strategy development and
are used in tests to validate the backtesting engine.

Strategies:
    - BuyAndHoldStrategy: Simple buy-once and hold strategy
    - MomentumStrategy: Moving average crossover strategy
"""

from decimal import Decimal
from typing import List

from src.trading_bot.backtest.models import HistoricalDataBar, Position


class BuyAndHoldStrategy:
    """
    Buy-and-Hold Strategy

    The simplest possible trading strategy:
    - Enter position on first available bar
    - Never exit until end of backtest

    This strategy is useful for:
    - Establishing baseline performance (market benchmark)
    - Testing backtesting engine correctness
    - Comparing active strategies against passive investing

    Performance characteristics:
    - Single trade per symbol
    - Zero trading costs (after initial buy)
    - Matches market returns exactly
    """

    def __init__(self) -> None:
        """Initialize Buy-and-Hold strategy."""
        self._has_entered = False

    def should_enter(self, bars: List[HistoricalDataBar]) -> bool:
        """Enter position on first bar only."""
        if not bars:
            return False

        if not self._has_entered:
            self._has_entered = True
            return True

        return False

    def should_exit(
        self,
        position: Position,
        bars: List[HistoricalDataBar]
    ) -> bool:
        """Never exit position (hold until end of backtest)."""
        return False


class MomentumStrategy:
    """
    Moving Average Crossover Strategy

    A trend-following strategy using two moving averages:
    - Short MA (20 days): Fast-moving average for short-term trends
    - Long MA (50 days): Slow-moving average for long-term trends

    Entry signal:
        Short MA crosses above Long MA (bullish crossover)

    Exit signal:
        Short MA crosses below Long MA (bearish crossover)
    """

    def __init__(self, short_window: int = 20, long_window: int = 50) -> None:
        """Initialize Momentum Strategy."""
        if short_window >= long_window:
            raise ValueError(
                f"short_window ({short_window}) must be < long_window ({long_window})"
            )
        if short_window < 1 or long_window < 1:
            raise ValueError("Moving average windows must be >= 1")

        self.short_window = short_window
        self.long_window = long_window

    def _calculate_ma(
        self,
        bars: List[HistoricalDataBar],
        window: int
    ) -> Decimal:
        """Calculate simple moving average."""
        if len(bars) < window:
            raise ValueError(
                f"Insufficient bars ({len(bars)}) for MA calculation (need {window})"
            )

        recent_bars = bars[-window:]
        total = sum(bar.close for bar in recent_bars)
        return total / window

    def should_enter(self, bars: List[HistoricalDataBar]) -> bool:
        """Enter when short MA crosses above long MA (bullish signal)."""
        if len(bars) < self.long_window:
            return False

        short_ma = self._calculate_ma(bars, self.short_window)
        long_ma = self._calculate_ma(bars, self.long_window)

        return short_ma > long_ma

    def should_exit(
        self,
        position: Position,
        bars: List[HistoricalDataBar]
    ) -> bool:
        """Exit when short MA crosses below long MA (bearish signal)."""
        if len(bars) < self.long_window:
            return False

        short_ma = self._calculate_ma(bars, self.short_window)
        long_ma = self._calculate_ma(bars, self.long_window)

        return short_ma < long_ma
