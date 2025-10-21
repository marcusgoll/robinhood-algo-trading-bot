"""
StrategyOrchestrator - Multi-strategy portfolio backtesting coordinator.

Coordinates execution of multiple trading strategies with independent capital
allocations, tracking per-strategy performance and generating aggregate portfolio
metrics for comparison and optimization.

Implements TDD pattern: Tests written before implementation (T015-T018).
"""

import logging
from decimal import Decimal

from src.trading_bot.backtest.models import (
    HistoricalDataBar,
    OrchestratorConfig,
    OrchestratorResult,
    StrategyAllocation,
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
        """
        # Validate historical_data
        if not historical_data:
            raise ValueError("historical_data dictionary cannot be empty")

        # Placeholder implementation - actual execution logic in T016-T018
        logger.info(
            f"Starting multi-strategy backtest with {len(self._strategies)} strategies"
        )

        # TODO (T016): Implement chronological bar iteration
        # TODO (T017): Implement per-strategy signal collection and execution
        # TODO (T018): Implement aggregate metrics calculation and result assembly

        # Placeholder return - will be replaced with actual result in T016-T018
        raise NotImplementedError(
            "StrategyOrchestrator.run() implementation pending (T016-T018)"
        )
