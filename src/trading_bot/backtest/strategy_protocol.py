"""
IStrategy Protocol Definition

Defines the interface that all trading strategies must implement for backtesting.
Uses Python's Protocol for structural subtyping (duck typing with type checking).

Constitution v1.0.0:
- §Code_Quality: Protocol provides type-safe contracts for strategies
- §Testing_Requirements: Enables strategy validation before live deployment
"""

from typing import Protocol, runtime_checkable

from trading_bot.backtest.models import HistoricalDataBar, Position


@runtime_checkable
class IStrategy(Protocol):
    """
    Protocol defining the interface for trading strategies.

    All strategies must implement should_enter() and should_exit() methods
    to participate in backtesting. This protocol enables type-safe strategy
    contracts while maintaining flexibility for strategy implementations.

    Methods:
        should_enter: Determine if strategy should enter a new position
        should_exit: Determine if strategy should exit an open position

    Example:
        class SimpleStrategy:
            def should_enter(self, bars: List[HistoricalDataBar]) -> bool:
                # Buy when price crosses above 50-day MA
                if len(bars) < 50:
                    return False
                ma50 = sum(bar.close for bar in bars[-50:]) / 50
                return bars[-1].close > ma50

            def should_exit(
                self,
                position: Position,
                bars: List[HistoricalDataBar]
            ) -> bool:
                # Sell when price crosses below 50-day MA
                if len(bars) < 50:
                    return False
                ma50 = sum(bar.close for bar in bars[-50:]) / 50
                return bars[-1].close < ma50

    Note:
        - Strategies receive only historical data visible at current time
        - No look-ahead bias: bars list ends at current simulation time
        - All strategies are invoked on every bar (event-driven)
        - Strategies are stateless: all state passed via parameters
    """

    def should_enter(self, bars: list[HistoricalDataBar]) -> bool:
        """
        Determine whether to enter a new position.

        Called on every bar during backtest when no position is currently held.
        Strategy receives all historical bars visible up to current time.

        Args:
            bars: Historical price bars in chronological order (oldest first).
                  Last bar (bars[-1]) is the current bar being evaluated.
                  All previous bars (bars[:-1]) are historical context.

        Returns:
            True if strategy wants to enter a long position, False otherwise.

        Raises:
            StrategyError: If strategy encounters an error during evaluation.

        Example:
            def should_enter(self, bars: List[HistoricalDataBar]) -> bool:
                # Enter when RSI < 30 (oversold)
                if len(bars) < 14:
                    return False  # Need 14 bars for RSI
                rsi = calculate_rsi(bars, period=14)
                return rsi < 30

        Note:
            - Must NOT modify bars list (treat as immutable)
            - Must NOT have side effects (stateless evaluation)
            - Must complete quickly (called on every bar)
            - Return False if insufficient data for indicators
        """
        ...

    def should_exit(
        self,
        position: Position,
        bars: list[HistoricalDataBar]
    ) -> bool:
        """
        Determine whether to exit an open position.

        Called on every bar during backtest when a position is currently held.
        Strategy receives current position details and all visible historical data.

        Args:
            position: Current open position with entry price, shares, entry date.
            bars: Historical price bars in chronological order (oldest first).
                  Last bar (bars[-1]) is the current bar being evaluated.

        Returns:
            True if strategy wants to close the position, False to hold.

        Raises:
            StrategyError: If strategy encounters an error during evaluation.

        Example:
            def should_exit(
                self,
                position: Position,
                bars: List[HistoricalDataBar]
            ) -> bool:
                # Exit if loss > 5% or gain > 10%
                current_price = bars[-1].close
                pnl = (current_price - position.entry_price) * position.shares
                cost_basis = position.entry_price * position.shares
                pnl_pct = pnl / cost_basis
                return pnl_pct < -0.05 or pnl_pct > 0.10

        Note:
            - Must NOT modify position or bars (treat as immutable)
            - Must NOT have side effects (stateless evaluation)
            - Must complete quickly (called on every bar)
            - Calculate P&L using position.entry_price and bars[-1].close
        """
        ...
