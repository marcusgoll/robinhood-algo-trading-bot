"""
StrategyOrchestrator - Multi-strategy portfolio backtesting coordinator.

Coordinates execution of multiple trading strategies with independent capital
allocations, tracking per-strategy performance and generating aggregate portfolio
metrics for comparison and optimization.

Implements TDD pattern: Tests written before implementation (T015-T018).
"""

import logging
from datetime import datetime
from decimal import Decimal

from src.trading_bot.backtest.models import (
    HistoricalDataBar,
    OrchestratorConfig,
    OrchestratorResult,
    Position,
    StrategyAllocation,
    Trade,
)
from src.trading_bot.backtest.strategy_protocol import IStrategy

logger = logging.getLogger(__name__)


class StrategyOrchestrator:
    """
    Multi-strategy portfolio backtesting coordinator.

    Executes multiple trading strategies simultaneously with independent capital
    allocations, tracking per-strategy performance and generating aggregate
    portfolio metrics. Prevents look-ahead bias through chronological execution
    and enforces capital limits per strategy.

    Attributes:
        _strategies: Strategy instances indexed by unique strategy ID
        _allocations: Capital allocation tracking by strategy ID
        _config: Orchestrator configuration parameters

    Example:
        from decimal import Decimal
        from trading_bot.backtest import StrategyOrchestrator, OrchestratorConfig

        # Define strategies with weights (weights must sum ≤ 1.0)
        strategies_with_weights = [
            (MomentumStrategy(), Decimal("0.4")),  # 40% allocation
            (MeanReversionStrategy(), Decimal("0.3")),  # 30% allocation
            (BreakoutStrategy(), Decimal("0.3"))  # 30% allocation
        ]

        # Create orchestrator with initial capital
        config = OrchestratorConfig(logging_level="INFO", validate_weights=True)
        orchestrator = StrategyOrchestrator(
            strategies_with_weights=strategies_with_weights,
            initial_capital=Decimal("100000.0"),
            config=config
        )

        # Run multi-strategy backtest
        result = orchestrator.run(
            historical_data={"AAPL": bars, "MSFT": bars2}
        )

        # Access aggregate and per-strategy results
        print(f"Portfolio Total Return: {result.aggregate_metrics.total_return * 100:.2f}%")
        print(f"Portfolio Sharpe Ratio: {result.aggregate_metrics.sharpe_ratio:.2f}")

        for strategy_id, strategy_result in result.strategy_results.items():
            print(f"{strategy_id} Return: {strategy_result.metrics.total_return * 100:.2f}%")

    Note:
        - Strategies execute independently with separate capital allocations
        - Capital limits enforced per strategy (FR-007)
        - All trading decisions logged for auditability (FR-012)
        - Chronological execution prevents look-ahead bias (FR-015)
    """

    def __init__(
        self,
        strategies_with_weights: list[tuple[IStrategy, Decimal]],
        initial_capital: Decimal = Decimal("100000.0"),
        config: OrchestratorConfig | None = None
    ):
        """
        Initialize StrategyOrchestrator with strategies and capital allocations.

        Validates strategy weights sum to ≤1.0 and creates capital allocations
        for each strategy based on weights and initial capital.

        Args:
            strategies_with_weights: List of (strategy, weight) tuples.
                                    Weights must be Decimal in range [0, 1] and sum ≤1.0.
            initial_capital: Total portfolio capital to allocate across strategies.
                            Must be positive Decimal (default: 100000.0).
            config: Optional orchestrator configuration. If None, uses default
                   OrchestratorConfig(logging_level="INFO", validate_weights=True).

        Raises:
            ValueError: If weights validation fails (negative, sum >1.0, etc.)
            ValueError: If initial_capital is non-positive
            ValueError: If strategies_with_weights is empty

        Example:
            orchestrator = StrategyOrchestrator(
                strategies_with_weights=[
                    (Strategy1(), Decimal("0.5")),
                    (Strategy2(), Decimal("0.3")),
                    (Strategy3(), Decimal("0.2"))
                ],
                initial_capital=Decimal("100000.0")
            )

        From:
            - spec.md FR-002: Weights must sum to ≤1.0 (≤100%)
            - spec.md FR-003: Capital allocated proportionally based on weights
            - spec.md NFR-003: Fail-fast validation at initialization
            - tasks.md T016: Implement __init__ with weight validation
            - Pattern: src/trading_bot/backtest/engine.py __init__ validation
        """
        # Store initial capital
        self.initial_capital = initial_capital

        # Use default config if not provided
        if config is None:
            config = OrchestratorConfig()

        self._config = config

        # Setup structured logging if configured
        if self._config.logging_level:
            logging.basicConfig(
                level=getattr(logging, self._config.logging_level),
                format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
                       '"logger": "%(name)s", "message": "%(message)s"}',
            )

        # Validate initial capital is positive
        if initial_capital <= 0:
            raise ValueError(
                f"initial_capital ({initial_capital}) must be positive"
            )

        # Validate non-empty strategies
        if not strategies_with_weights:
            raise ValueError("strategies_with_weights list cannot be empty")

        # Validate weights if enabled in config
        total_weight = Decimal("0.0")
        if self._config.validate_weights:
            for i, (strategy, weight) in enumerate(strategies_with_weights):
                # Validate weight is non-negative
                if weight < 0:
                    raise ValueError(
                        f"Strategy weight at index {i} is {weight}, must be non-negative"
                    )
                total_weight += weight

            # FR-002: Validate weights sum to ≤1.0 (≤100%)
            if total_weight > Decimal("1.0"):
                raise ValueError(
                    f"Strategy weights sum to {total_weight}, must be ≤1.0 (≤100%). "
                    f"Reduce weights so sum ≤ 1.0."
                )

        # Initialize strategy registry (dict by strategy ID)
        self._strategies: dict[str, IStrategy] = {}

        # Initialize capital allocations (list for ordered access)
        self._allocations: list[StrategyAllocation] = []

        # Initialize per-strategy state tracking
        self._strategy_positions: dict[str, dict[str, "Position"]] = {}  # strategy_id -> {symbol -> Position}
        self._strategy_trades: dict[str, list["Trade"]] = {}  # strategy_id -> list[Trade]
        self._strategy_equity: dict[str, list[tuple["datetime", Decimal]]] = {}  # strategy_id -> equity curve

        # FR-003: Register strategies and create capital allocations
        for i, (strategy, weight) in enumerate(strategies_with_weights):
            # Generate unique strategy ID (zero-indexed: "strategy_0", "strategy_1", etc.)
            strategy_id = f"strategy_{i}"

            # Store strategy instance
            self._strategies[strategy_id] = strategy

            # Calculate allocated capital = initial_capital × weight
            allocated_capital = initial_capital * weight

            # Create StrategyAllocation for this strategy
            allocation = StrategyAllocation(
                strategy_id=strategy_id,
                allocated_capital=allocated_capital,
            )

            # Store allocation in list (maintains insertion order)
            self._allocations.append(allocation)

            # Initialize per-strategy state tracking
            self._strategy_positions[strategy_id] = {}
            self._strategy_trades[strategy_id] = []
            self._strategy_equity[strategy_id] = []

            logger.info(
                f"Strategy initialized: {strategy_id} with weight={weight} "
                f"(${allocated_capital} / ${initial_capital})"
            )

        logger.info(
            f"StrategyOrchestrator initialized with {len(self._strategies)} strategies, "
            f"total capital=${initial_capital}, total weight={total_weight}"
        )

    def run(
        self,
        historical_data: dict[str, list[HistoricalDataBar]]
    ) -> OrchestratorResult:
        """
        Execute multi-strategy backtest across all strategies.

        Runs all registered strategies chronologically against historical data,
        tracking per-strategy performance and generating aggregate portfolio metrics.
        Enforces capital limits and prevents look-ahead bias.

        Args:
            historical_data: Historical bars by symbol. Dict mapping symbol to
                            list of HistoricalDataBar objects in chronological order.

        Returns:
            OrchestratorResult containing:
                - aggregate_metrics: Portfolio-level performance metrics
                - strategy_results: Per-strategy BacktestResult by strategy_id
                - comparison_table: Comparative metrics across strategies

        Raises:
            ValueError: If historical_data is empty or invalid
            ValueError: If historical_data contains no valid bars

        Example:
            result = orchestrator.run(
                historical_data={
                    "AAPL": [bar1, bar2, bar3],
                    "MSFT": [bar1, bar2, bar3]
                }
            )

            # Access portfolio metrics
            print(f"Portfolio Sharpe: {result.aggregate_metrics.sharpe_ratio}")

            # Access individual strategy results
            strategy1_result = result.get_strategy_result("strategy_1")
            print(f"Strategy 1 Return: {strategy1_result.metrics.total_return}")

        Note:
            - Executes chronologically to prevent look-ahead bias (FR-015)
            - Tracks capital usage per strategy (FR-007)
            - Logs all trading decisions (FR-012)
            - Generates comparison table (FR-013)

        From:
            - spec.md FR-004: Execute all strategies chronologically on every bar
            - spec.md FR-015: Maintain chronological order guarantee (no look-ahead bias)
            - tasks.md T017: Implement run() with chronological execution
            - Pattern: src/trading_bot/backtest/engine.py run() method
        """
        # Validate historical_data
        if not historical_data:
            raise ValueError("historical_data dictionary cannot be empty")

        logger.info(
            f"Starting multi-strategy backtest with {len(self._strategies)} strategies"
        )

        # T017: Extract all unique timestamps and sort chronologically
        all_timestamps: set["datetime"] = set()
        for symbol_bars in historical_data.values():
            for bar in symbol_bars:
                all_timestamps.add(bar.timestamp)

        # Sort timestamps chronologically for deterministic execution
        sorted_timestamps = sorted(all_timestamps)

        if not sorted_timestamps:
            raise ValueError("historical_data contains no valid bars")

        logger.info(
            f"Processing {len(sorted_timestamps)} unique timestamps across "
            f"{len(historical_data)} symbols"
        )

        # T017: For each timestamp, execute all strategies on that bar
        for timestamp in sorted_timestamps:
            # Create current_bars dict with bars for this timestamp across all symbols
            current_bars: dict[str, HistoricalDataBar] = {}
            for symbol, bars in historical_data.items():
                # Find bar matching this timestamp
                for bar in bars:
                    if bar.timestamp == timestamp:
                        current_bars[symbol] = bar
                        break

            # Execute all strategies for this timestamp (T018)
            self._execute_bar(current_bars, historical_data, timestamp)

        logger.info(
            f"Completed backtest execution for {len(sorted_timestamps)} timestamps"
        )

        # T024-T027: Calculate per-strategy metrics and comparison table
        from datetime import UTC
        from src.trading_bot.backtest.models import PerformanceMetrics, BacktestResult, BacktestConfig
        from src.trading_bot.backtest.performance_calculator import PerformanceCalculator

        calculator = PerformanceCalculator()
        strategy_results: dict[str, BacktestResult] = {}
        current_time = datetime.now(UTC)

        # Calculate metrics for each strategy (FR-009)
        for strategy_id in self._strategies.keys():
            # Get allocation and strategy for this strategy_id
            allocation = next(
                alloc for alloc in self._allocations if alloc.strategy_id == strategy_id
            )
            strategy = self._strategies[strategy_id]

            # Create minimal BacktestConfig for performance calculation
            strategy_config = BacktestConfig(
                strategy_class=type(strategy),  # Use actual strategy class
                symbols=list(historical_data.keys()),  # All symbols being traded
                initial_capital=allocation.allocated_capital,
                start_date=sorted_timestamps[0] if sorted_timestamps else datetime.now(UTC),
                end_date=sorted_timestamps[-1] if sorted_timestamps else datetime.now(UTC),
                risk_free_rate=Decimal("0.02")  # Default 2% risk-free rate
            )

            # Calculate performance metrics using PerformanceCalculator
            metrics = calculator.calculate_metrics(
                trades=self._strategy_trades[strategy_id],
                equity_curve=self._strategy_equity[strategy_id],
                config=strategy_config
            )

            # Create BacktestResult for this strategy
            strategy_results[strategy_id] = BacktestResult(
                config=strategy_config,
                trades=self._strategy_trades[strategy_id],
                equity_curve=self._strategy_equity[strategy_id],
                metrics=metrics,
                data_warnings=[],
                execution_time_seconds=0.001,  # Minimal execution time
                completed_at=current_time
            )

        # Calculate aggregate portfolio metrics
        # Combine all trades across strategies
        all_trades = []
        for trades in self._strategy_trades.values():
            all_trades.extend(trades)

        # Create aggregate equity curve from all strategies
        aggregate_equity: dict[datetime, Decimal] = {}
        for strategy_id, equity_curve in self._strategy_equity.items():
            for timestamp, equity in equity_curve:
                if timestamp not in aggregate_equity:
                    aggregate_equity[timestamp] = Decimal("0.0")
                aggregate_equity[timestamp] += equity

        aggregate_equity_curve = sorted(aggregate_equity.items())

        # Create aggregate config
        aggregate_config = BacktestConfig(
            strategy_class=type(list(self._strategies.values())[0]) if self._strategies else type(None),
            symbols=list(historical_data.keys()),
            initial_capital=self.initial_capital,
            start_date=sorted_timestamps[0] if sorted_timestamps else datetime.now(UTC),
            end_date=sorted_timestamps[-1] if sorted_timestamps else datetime.now(UTC),
            risk_free_rate=Decimal("0.02")
        )

        # Calculate aggregate metrics
        aggregate_metrics = calculator.calculate_metrics(
            trades=all_trades,
            equity_curve=aggregate_equity_curve,
            config=aggregate_config
        )

        # T027: Generate comparison table (FR-013)
        comparison_table: dict[str, dict[str, Decimal]] = {}
        for strategy_id, result in strategy_results.items():
            comparison_table[strategy_id] = {
                "total_return": result.metrics.total_return,
                "sharpe_ratio": result.metrics.sharpe_ratio,
                "max_drawdown": result.metrics.max_drawdown,
                "win_rate": result.metrics.win_rate,
                "total_trades": Decimal(str(result.metrics.total_trades))
            }

        # Return OrchestratorResult
        return OrchestratorResult(
            aggregate_metrics=aggregate_metrics,
            strategy_results=strategy_results,
            comparison_table=comparison_table
        )

    def _execute_bar(
        self,
        current_bars: dict[str, HistoricalDataBar],
        historical_data: dict[str, list[HistoricalDataBar]],
        current_timestamp: datetime
    ) -> None:
        """
        Execute all strategies for the current bar timestamp.

        For each strategy:
        1. Collect visible historical data up to current timestamp
        2. Check for entry signals (if no position held)
        3. Check for exit signals (if position held)
        4. Execute trades and update capital allocations
        5. Track equity curve progression

        Args:
            current_bars: Dict mapping symbol to HistoricalDataBar for current timestamp
            historical_data: Complete historical data for all symbols
            current_timestamp: Current bar timestamp being processed

        Side Effects:
            - Updates self._strategy_positions (opens/closes positions)
            - Updates self._strategy_trades (records completed trades)
            - Updates self._strategy_equity (tracks equity curve)
            - Updates self._allocations (allocates/releases capital)

        From:
            - spec.md FR-004: Execute all strategies on every bar
            - spec.md FR-006: Tag all trades with strategy_id
            - spec.md FR-015: No look-ahead bias (current bar only)
            - tasks.md T018: Implement _execute_bar() for per-strategy processing
            - Pattern: src/trading_bot/backtest/engine.py bar processing logic
        """
        # For each strategy, execute entry/exit logic
        for strategy_id, strategy in self._strategies.items():
            # Get allocation for this strategy
            allocation = next(
                alloc for alloc in self._allocations if alloc.strategy_id == strategy_id
            )

            # For each symbol in current_bars, build visible history
            for symbol, current_bar in current_bars.items():
                # Get all bars for this symbol up to and including current timestamp
                visible_bars = [
                    bar for bar in historical_data[symbol]
                    if bar.timestamp <= current_timestamp
                ]

                # Check if strategy already has position for this symbol
                has_position = symbol in self._strategy_positions[strategy_id]

                if not has_position:
                    # Check for entry signal
                    should_enter = strategy.should_enter(visible_bars)

                    if should_enter:
                        # Try to enter position
                        self._enter_position(
                            strategy_id=strategy_id,
                            symbol=symbol,
                            current_bar=current_bar,
                            allocation=allocation
                        )
                else:
                    # Has position - check for exit signal
                    position = self._strategy_positions[strategy_id][symbol]
                    should_exit = strategy.should_exit(position, visible_bars)

                    if should_exit:
                        # Exit position
                        self._exit_position(
                            strategy_id=strategy_id,
                            symbol=symbol,
                            position=position,
                            current_bar=current_bar,
                            allocation=allocation,
                            exit_reason="strategy_signal"
                        )

            # Update equity curve for this strategy at this timestamp
            self._update_strategy_equity(strategy_id, current_timestamp, current_bars)

    def _enter_position(
        self,
        strategy_id: str,
        symbol: str,
        current_bar: HistoricalDataBar,
        allocation: StrategyAllocation
    ) -> None:
        """
        Enter a new position for a strategy with capital limit enforcement.

        Args:
            strategy_id: Strategy identifier
            symbol: Stock symbol to enter
            current_bar: Current bar with entry price
            allocation: Strategy capital allocation

        Side Effects:
            - Creates position in self._strategy_positions if capital available
            - Updates allocation.used_capital via allocation.allocate()
            - Logs warning if capital limit blocks entry (FR-007)
        """
        # Use current bar's close as fill price (conservative fill simulation)
        fill_price = current_bar.close

        # Calculate position size using available capital
        # Use 95% of available capital to leave buffer for price movements
        position_size_pct = Decimal("0.95")
        target_capital = allocation.available_capital * position_size_pct
        max_shares = int(target_capital / fill_price)

        if max_shares <= 0:
            logger.warning(
                f"[CAPITAL_LIMIT] {strategy_id}: Blocked entry for {symbol} at ${fill_price}. "
                f"Insufficient capital. Available: ${allocation.available_capital}, "
                f"Allocated: ${allocation.allocated_capital}, Used: ${allocation.used_capital}"
            )
            return

        # Calculate actual position cost
        position_cost = max_shares * fill_price

        # FR-007: Check if we can allocate capital before entering position
        if not allocation.can_allocate(position_cost):
            logger.warning(
                f"[CAPITAL_LIMIT] {strategy_id}: Blocked entry for {symbol}. "
                f"Position cost ${position_cost} exceeds available capital ${allocation.available_capital}. "
                f"Strategy at allocation limit: {allocation.used_capital}/{allocation.allocated_capital}"
            )
            return

        # Allocate capital for this position (T035: Capital allocation)
        allocation.allocate(position_cost)

        # Create position
        position = Position(
            symbol=symbol,
            shares=max_shares,
            entry_price=fill_price,
            entry_date=current_bar.timestamp,
            current_price=fill_price
        )

        # Store position
        self._strategy_positions[strategy_id][symbol] = position

        logger.info(
            f"{strategy_id}: Entered {max_shares} shares of {symbol} "
            f"at ${fill_price} on {current_bar.timestamp.date()}"
        )

    def _exit_position(
        self,
        strategy_id: str,
        symbol: str,
        position: Position,
        current_bar: HistoricalDataBar,
        allocation: StrategyAllocation,
        exit_reason: str
    ) -> None:
        """
        Exit an existing position for a strategy.

        Args:
            strategy_id: Strategy identifier
            symbol: Stock symbol to exit
            position: Position to close
            current_bar: Current bar with exit price
            allocation: Strategy capital allocation
            exit_reason: Reason for exit (strategy_signal, end_of_data, etc.)

        Side Effects:
            - Removes position from self._strategy_positions
            - Releases capital back to allocation
            - Creates Trade record in self._strategy_trades
        """
        # Use current bar's close as fill price
        fill_price = current_bar.close

        # Calculate proceeds and P&L
        proceeds = position.shares * fill_price
        cost_basis = position.shares * position.entry_price
        pnl = proceeds - cost_basis
        pnl_pct = pnl / cost_basis if cost_basis > 0 else Decimal("0.0")

        # Calculate duration
        duration_days = (current_bar.timestamp - position.entry_date).days

        # Create trade record (FR-006: tag with strategy_id)
        trade = Trade(
            symbol=symbol,
            entry_date=position.entry_date,
            entry_price=position.entry_price,
            exit_date=current_bar.timestamp,
            exit_price=fill_price,
            shares=position.shares,
            pnl=pnl,
            pnl_pct=pnl_pct,
            duration_days=duration_days,
            exit_reason=exit_reason,
            commission=Decimal("0.0"),  # No commission for MVP
            slippage=Decimal("0.0"),  # No slippage for MVP
            metadata={"strategy_id": strategy_id}  # FR-006: Tag trade with strategy
        )

        # Store trade
        self._strategy_trades[strategy_id].append(trade)

        # Release capital back to allocation
        allocation.release(cost_basis)

        # Remove position
        del self._strategy_positions[strategy_id][symbol]

        logger.info(
            f"{strategy_id}: Exited {position.shares} shares of {symbol} "
            f"at ${fill_price} on {current_bar.timestamp.date()}, "
            f"P&L: ${pnl:.2f} ({pnl_pct * 100:.2f}%)"
        )

    def _update_strategy_equity(
        self,
        strategy_id: str,
        current_timestamp: datetime,
        current_bars: dict[str, HistoricalDataBar]
    ) -> None:
        """
        Calculate and record current equity for a strategy.

        Equity = available_capital + mark-to-market value of positions

        Args:
            strategy_id: Strategy identifier
            current_timestamp: Current bar timestamp
            current_bars: Current bars with prices for mark-to-market valuation

        Side Effects:
            - Appends (timestamp, equity) to self._strategy_equity[strategy_id]
        """
        # Get allocation for this strategy
        allocation = next(
            alloc for alloc in self._allocations if alloc.strategy_id == strategy_id
        )

        # Calculate mark-to-market value of all positions
        mark_to_market_value = Decimal("0.0")
        for symbol, position in self._strategy_positions[strategy_id].items():
            # Get current price from current_bars
            if symbol in current_bars:
                current_price = current_bars[symbol].close
                # Calculate position value at current price
                position_value = position.shares * current_price
                mark_to_market_value += position_value

        # Calculate total equity = available capital + mark-to-market position values
        total_equity = allocation.available_capital + mark_to_market_value

        # Record equity point
        self._strategy_equity[strategy_id].append((current_timestamp, total_equity))
