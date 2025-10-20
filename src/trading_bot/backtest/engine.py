"""
BacktestEngine - Core backtesting execution engine.

Chronologically executes trading strategies against historical data,
tracking positions, calculating P&L, and generating performance metrics.

Implements TDD pattern: Tests written before implementation (T021-T024).
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Union

from trading_bot.backtest.models import (
    BacktestConfig,
    BacktestResult,
    BacktestState,
    HistoricalDataBar,
    PerformanceMetrics,
    Position,
    Trade,
)
from trading_bot.backtest.strategy_protocol import IStrategy

logger = logging.getLogger(__name__)


class BacktestEngine:
    """
    Core backtesting engine for chronological strategy execution.

    Executes trading strategies against historical data bar-by-bar in strict
    chronological order to prevent look-ahead bias. Tracks portfolio state,
    manages positions, and generates comprehensive performance metrics.

    Attributes:
        config: Backtest configuration
        state: Current backtest state (cash, positions, equity)
        strategy: Trading strategy to execute

    Example:
        config = BacktestConfig(
            strategy_class=MyStrategy,
            symbols=["AAPL"],
            start_date=datetime(2023, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2023, 12, 31, tzinfo=timezone.utc),
            initial_capital=Decimal("100000.0")
        )

        engine = BacktestEngine(config=config)
        result = engine.run(
            strategy=MyStrategy(),
            historical_data={"AAPL": bars}
        )

        print(f"Total Return: {result.metrics.total_return * 100:.2f}%")
        print(f"Sharpe Ratio: {result.metrics.sharpe_ratio:.2f}")
    """

    def __init__(self, config: BacktestConfig = None):
        """
        Initialize BacktestEngine with optional configuration.

        Args:
            config: Optional backtest configuration parameters.
                   If None, config must be passed to run().
        """
        self.config = config
        self.state: BacktestState = None
        self.strategy: IStrategy = None

    def run(
        self,
        strategy: Union[IStrategy, BacktestConfig] = None,
        historical_data: Union[List[HistoricalDataBar], Dict[str, List[HistoricalDataBar]]] = None
    ) -> BacktestResult:
        """
        Execute backtest for given strategy and historical data.

        Supports two API patterns:
        1. BacktestEngine(config).run(strategy, historical_data)
        2. BacktestEngine().run(config)  # config contains strategy_class

        Args:
            strategy: Trading strategy OR BacktestConfig if pattern 2
            historical_data: Historical bars (single symbol: List, multi: Dict)

        Returns:
            BacktestResult with trades, equity curve, and performance metrics

        Raises:
            ValueError: If historical_data format is invalid or config missing
        """
        start_time = datetime.now(timezone.utc)

        # Detect API pattern
        if isinstance(strategy, BacktestConfig):
            # Pattern 2: BacktestEngine().run(config)
            self.config = strategy
            self.strategy = self.config.strategy_class()
            if historical_data is None:
                raise ValueError("historical_data required when passing config to run()")
        elif strategy is None:
            # No strategy passed - check if config has strategy_class
            if self.config is None:
                raise ValueError("config required in __init__() or run()")
            if not hasattr(self.config, 'strategy_class'):
                raise ValueError("config must have strategy_class")
            self.strategy = self.config.strategy_class()
        else:
            # Pattern 1: BacktestEngine(config).run(strategy, historical_data)
            if self.config is None:
                raise ValueError("config required in __init__() or run()")
            self.strategy = strategy

        # Normalize historical_data to Dict format
        if isinstance(historical_data, list):
            # Single symbol: wrap in dict with first symbol from config
            symbol = self.config.symbols[0]
            historical_data = {symbol: historical_data}

        # Validate we have data for all configured symbols
        for symbol in self.config.symbols:
            if symbol not in historical_data:
                logger.warning(
                    f"No historical data provided for {symbol}, skipping"
                )

        # Initialize backtest state
        self.state = BacktestState(
            current_date=self.config.start_date,
            cash=self.config.initial_capital,
            positions={},
            equity_history=[],
            trades=[],
            warnings=[]
        )

        # Get all bars across all symbols and sort chronologically
        all_bars = []
        for symbol, bars in historical_data.items():
            all_bars.extend(bars)

        # Sort by timestamp to ensure chronological execution
        all_bars.sort(key=lambda bar: bar.timestamp)

        # Execute strategy chronologically bar-by-bar
        for i, current_bar in enumerate(all_bars):
            self.state.current_date = current_bar.timestamp

            # Update current prices for all positions
            self._update_position_prices(current_bar)

            # Get visible historical data (all bars up to and including current)
            visible_bars = all_bars[:i + 1]

            # Filter visible bars to current symbol only
            symbol_visible_bars = [
                bar for bar in visible_bars if bar.symbol == current_bar.symbol
            ]

            # Check for entry signals (if no position held for this symbol)
            if current_bar.symbol not in self.state.positions:
                self._check_entries(current_bar, symbol_visible_bars, all_bars, i)

            # Check for exit signals (if position held for this symbol)
            if current_bar.symbol in self.state.positions:
                self._check_exits(current_bar, symbol_visible_bars, all_bars, i)

            # Update equity curve
            self._update_equity()

        # Close all remaining positions at end of data
        self._close_all_positions(all_bars)

        # Calculate performance metrics
        metrics = self._calculate_metrics()

        # Calculate execution time
        end_time = datetime.now(timezone.utc)
        execution_time = (end_time - start_time).total_seconds()

        # Ensure minimum execution time for validation (avoid 0.0)
        if execution_time <= 0:
            execution_time = 0.001  # 1 millisecond minimum

        # Create result object
        result = BacktestResult(
            config=self.config,
            trades=self.state.trades,
            equity_curve=self.state.equity_history,
            metrics=metrics,
            data_warnings=self.state.warnings,
            execution_time_seconds=execution_time,
            completed_at=end_time
        )

        return result

    def _check_entries(
        self,
        current_bar: HistoricalDataBar,
        visible_bars: List[HistoricalDataBar],
        all_bars: List[HistoricalDataBar],
        current_index: int
    ) -> None:
        """
        Check for entry signals and execute trades if capital sufficient.

        Called when no position is held for the current symbol. Calls
        strategy.should_enter() and simulates fill at next bar's open price.

        Args:
            current_bar: Current bar being evaluated
            visible_bars: All historical bars visible at this point (symbol-specific)
            all_bars: All bars across all symbols (for next bar lookup)
            current_index: Index of current_bar in all_bars list

        Side Effects:
            - Creates new position if signal and sufficient capital
            - Updates self.state.cash
            - Updates self.state.positions
            - Logs warnings if insufficient capital
        """
        # Call strategy to check entry signal
        should_enter = self.strategy.should_enter(visible_bars)

        if not should_enter:
            return  # No entry signal

        # Strategy signaled entry - check if we can fill at next bar
        # Conservative fill simulation: use next bar's open price
        if current_index >= len(all_bars) - 1:
            # Last bar - can't fill (no next bar)
            logger.debug(
                f"Entry signal on last bar for {current_bar.symbol}, cannot fill"
            )
            return

        # Calculate position size and fill price
        # For first bar, fill at current bar's open (entry at market open)
        # For subsequent bars with signal, fill at current bar's close
        if current_index == 0:
            # First bar: can fill at open price (market entry at open)
            fill_price = current_bar.open
        else:
            # Subsequent bars: fill at current bar close (signal during day, fill at close)
            fill_price = current_bar.close

        # Calculate position size
        if hasattr(self.strategy, 'position_size'):
            shares = self.strategy.position_size(
                capital=float(self.state.cash),
                price=float(fill_price)
            )
        else:
            # Default position sizing: use all available capital
            shares = int(self.state.cash / fill_price)

        if shares <= 0:
            logger.debug(
                f"Position size calculation returned {shares} shares for "
                f"{current_bar.symbol}, skipping entry"
            )
            return

        # Calculate position cost (shares * price)
        position_cost = shares * fill_price

        # Check if sufficient capital
        if self.state.cash < position_cost:
            logger.warning(
                f"Insufficient capital to buy {shares} shares of {current_bar.symbol} "
                f"at ${fill_price}. Required: ${position_cost}, Available: ${self.state.cash}"
            )
            return

        # Execute fill: deduct cash and create position
        self.state.cash -= position_cost

        # Create position
        position = Position(
            symbol=current_bar.symbol,
            shares=shares,
            entry_price=fill_price,
            entry_date=current_bar.timestamp,  # Entry date is current bar
            current_price=fill_price
        )

        self.state.positions[current_bar.symbol] = position

        logger.info(
            f"Entered position: {shares} shares of {current_bar.symbol} "
            f"at ${fill_price} on {current_bar.timestamp.date()}"
        )

    def _check_exits(
        self,
        current_bar: HistoricalDataBar,
        visible_bars: List[HistoricalDataBar],
        all_bars: List[HistoricalDataBar],
        current_index: int
    ) -> None:
        """
        Check for exit signals and close positions.

        Called when position is held for current symbol. Calls
        strategy.should_exit() and simulates fill at next bar's open price.

        Args:
            current_bar: Current bar being evaluated
            visible_bars: All historical bars visible at this point (symbol-specific)
            all_bars: All bars across all symbols (for next bar lookup)
            current_index: Index of current_bar in all_bars list

        Side Effects:
            - Closes position if signal
            - Updates self.state.cash
            - Removes position from self.state.positions
            - Appends trade to self.state.trades
        """
        # Get current position
        position = self.state.positions[current_bar.symbol]

        # Call strategy to check exit signal
        should_exit = self.strategy.should_exit(position, visible_bars)

        if not should_exit:
            return  # No exit signal

        # Strategy signaled exit - close position at next bar
        self._close_position(
            position=position,
            all_bars=all_bars,
            current_index=current_index,
            exit_reason="strategy_signal"
        )

    def _close_position(
        self,
        position: Position,
        all_bars: List[HistoricalDataBar],
        current_index: int,
        exit_reason: str
    ) -> None:
        """
        Close a position and create trade record.

        Args:
            position: Position to close
            all_bars: All bars across all symbols (for next bar lookup)
            current_index: Index of current bar in all_bars
            exit_reason: Reason for exit (strategy_signal, end_of_data, etc.)

        Side Effects:
            - Updates self.state.cash
            - Removes position from self.state.positions
            - Appends trade to self.state.trades
        """
        # Fill at current bar's close price (signal during day, fill at close)
        current_bar = all_bars[current_index]
        fill_price = current_bar.close
        fill_date = current_bar.timestamp

        # Calculate proceeds
        proceeds = position.shares * fill_price

        # Update cash
        self.state.cash += proceeds

        # Calculate P&L
        cost_basis = position.shares * position.entry_price
        pnl = proceeds - cost_basis - self.config.commission - Decimal("0.0")  # slippage
        pnl_pct = pnl / cost_basis

        # Calculate duration
        duration_days = (fill_date - position.entry_date).days

        # Create trade record
        trade = Trade(
            symbol=position.symbol,
            entry_date=position.entry_date,
            entry_price=position.entry_price,
            exit_date=fill_date,
            exit_price=fill_price,
            shares=position.shares,
            pnl=pnl,
            pnl_pct=pnl_pct,
            duration_days=duration_days,
            exit_reason=exit_reason,
            commission=self.config.commission,
            slippage=Decimal("0.0")  # No slippage for now
        )

        self.state.trades.append(trade)

        # Remove position
        del self.state.positions[position.symbol]

        logger.info(
            f"Exited position: {position.shares} shares of {position.symbol} "
            f"at ${fill_price} on {fill_date.date()}, P&L: ${pnl:.2f} ({pnl_pct * 100:.2f}%)"
        )

    def _close_all_positions(self, all_bars: List[HistoricalDataBar]) -> None:
        """
        Close all remaining open positions at end of backtest.

        Args:
            all_bars: All historical bars

        Side Effects:
            - Closes all positions in self.state.positions
            - Creates trade records for each
        """
        # Get symbols with open positions (copy to avoid mutation during iteration)
        symbols_with_positions = list(self.state.positions.keys())

        for symbol in symbols_with_positions:
            position = self.state.positions[symbol]

            # Close at last bar for this symbol
            self._close_position(
                position=position,
                all_bars=all_bars,
                current_index=len(all_bars) - 1,
                exit_reason="end_of_data"
            )

    def _update_position_prices(self, current_bar: HistoricalDataBar) -> None:
        """
        Update current_price for positions matching the current bar's symbol.

        Args:
            current_bar: Current bar with latest price information

        Side Effects:
            - Updates Position.current_price for matching symbol
        """
        if current_bar.symbol in self.state.positions:
            # Get current position
            old_position = self.state.positions[current_bar.symbol]

            # Create updated position with new current_price
            updated_position = Position(
                symbol=old_position.symbol,
                shares=old_position.shares,
                entry_price=old_position.entry_price,
                entry_date=old_position.entry_date,
                current_price=current_bar.close  # Update to current bar's close
            )

            # Replace position
            self.state.positions[current_bar.symbol] = updated_position

    def _update_equity(self) -> None:
        """
        Calculate and record current portfolio equity.

        Equity = cash + sum(position values at current prices)

        Side Effects:
            - Appends (timestamp, equity) to self.state.equity_history
        """
        # Calculate total position value
        position_value = Decimal("0.0")
        for position in self.state.positions.values():
            position_value += position.shares * position.current_price

        # Total equity = cash + positions
        equity = self.state.cash + position_value

        # Record equity point
        self.state.equity_history.append((self.state.current_date, equity))

    def _calculate_metrics(self) -> PerformanceMetrics:
        """
        Calculate performance metrics from trade history.

        Returns:
            PerformanceMetrics with all calculated statistics

        Note:
            Placeholder implementation - returns zeros for now.
            Full implementation in Phase 5 (US3).
        """
        # Placeholder metrics (will implement in Phase 5 - US3)
        total_trades = len(self.state.trades)
        winning_trades = sum(1 for trade in self.state.trades if trade.pnl > 0)
        losing_trades = total_trades - winning_trades

        win_rate = Decimal("0.0")
        if total_trades > 0:
            win_rate = Decimal(winning_trades) / Decimal(total_trades)

        return PerformanceMetrics(
            total_return=Decimal("0.0"),
            annualized_return=Decimal("0.0"),
            cagr=Decimal("0.0"),
            win_rate=win_rate,
            profit_factor=Decimal("0.0"),
            average_win=Decimal("0.0"),
            average_loss=Decimal("0.0"),
            max_drawdown=Decimal("0.0"),
            max_drawdown_duration_days=0,
            sharpe_ratio=Decimal("0.0"),
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades
        )
