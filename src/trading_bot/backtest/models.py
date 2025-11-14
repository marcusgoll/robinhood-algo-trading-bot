"""
Backtest Data Models

Dataclasses for backtesting engine: BacktestConfig, HistoricalDataBar, Trade,
PerformanceMetrics, BacktestResult, Position, BacktestState, OrchestratorConfig,
OrchestratorResult.

All models use Decimal for money fields, UTC timestamps, and comprehensive validation
to ensure data integrity throughout the backtesting process.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class BacktestConfig:
    """
    Configuration parameters for a backtest run.

    Defines the strategy, time period, symbols, and trading parameters
    (capital, commission, slippage) for backtesting a trading strategy.

    Attributes:
        strategy_class: Strategy class to instantiate and test
        symbols: Stock symbols to backtest (non-empty list)
        start_date: Start of historical data range (UTC)
        end_date: End of historical data range (UTC)
        initial_capital: Starting portfolio value in USD (default: 100000.0)
        commission: Commission per trade in dollars (default: 0.0 for Robinhood)
        slippage_pct: Slippage as percentage 0-1 (default: 0.001 for 0.1%)
        risk_free_rate: Annual risk-free rate for Sharpe ratio (default: 0.02)
        cache_enabled: Whether to cache historical data (default: True)

    Raises:
        ValueError: If validation fails (empty symbols, invalid dates, negative capital, etc.)
    """
    strategy_class: type
    symbols: list[str]
    start_date: datetime
    end_date: datetime
    initial_capital: Decimal = Decimal("100000.0")
    commission: Decimal = Decimal("0.0")
    slippage_pct: Decimal = Decimal("0.001")
    risk_free_rate: Decimal = Decimal("0.02")
    cache_enabled: bool = True

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        # Validate symbols non-empty
        if not self.symbols:
            raise ValueError("BacktestConfig: symbols list cannot be empty")

        # Validate date range
        if self.start_date >= self.end_date:
            raise ValueError(
                f"BacktestConfig: start_date ({self.start_date}) must be before "
                f"end_date ({self.end_date})"
            )

        # Validate positive initial capital
        if self.initial_capital <= 0:
            raise ValueError(
                f"BacktestConfig: initial_capital ({self.initial_capital}) must be positive"
            )

        # Validate non-negative commission
        if self.commission < 0:
            raise ValueError(
                f"BacktestConfig: commission ({self.commission}) must be non-negative"
            )

        # Validate slippage percentage range
        if not (0 <= self.slippage_pct < 1):
            raise ValueError(
                f"BacktestConfig: slippage_pct ({self.slippage_pct}) must be in range [0, 1)"
            )


@dataclass(frozen=True, slots=True)
class HistoricalDataBar:
    """
    OHLCV data for single time period (daily bar for MVP).

    Represents a single historical price bar with open, high, low, close,
    and volume data. Validates price consistency (high >= low, etc.).

    Attributes:
        symbol: Stock ticker symbol (e.g., 'AAPL', 'TSLA')
        timestamp: Bar timestamp in UTC
        open: Opening price in USD (Decimal for precision)
        high: Highest price during period (Decimal for precision)
        low: Lowest price during period (Decimal for precision)
        close: Closing price in USD (Decimal for precision)
        volume: Trading volume (number of shares traded)
        split_adjusted: Whether prices are split-adjusted (default: True)
        dividend_adjusted: Whether prices are dividend-adjusted (default: True)

    Raises:
        ValueError: If price relationships are invalid or prices are non-positive
    """
    symbol: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    split_adjusted: bool = True
    dividend_adjusted: bool = True

    def __post_init__(self) -> None:
        """Validate price bar consistency after initialization."""
        # Validate UTC timestamp (check timezone awareness)
        if self.timestamp.tzinfo is None:
            raise ValueError(
                f"HistoricalDataBar for {self.symbol}: timestamp must be timezone-aware (UTC)"
            )

        # Validate positive prices
        if self.open <= 0:
            raise ValueError(
                f"HistoricalDataBar for {self.symbol}: open ({self.open}) must be positive"
            )
        if self.high <= 0:
            raise ValueError(
                f"HistoricalDataBar for {self.symbol}: high ({self.high}) must be positive"
            )
        if self.low <= 0:
            raise ValueError(
                f"HistoricalDataBar for {self.symbol}: low ({self.low}) must be positive"
            )
        if self.close <= 0:
            raise ValueError(
                f"HistoricalDataBar for {self.symbol}: close ({self.close}) must be positive"
            )

        # Validate high >= open, close, low
        if self.high < self.low:
            raise ValueError(
                f"HistoricalDataBar for {self.symbol}: high ({self.high}) "
                f"must be >= low ({self.low})"
            )
        if not (self.low <= self.open <= self.high):
            raise ValueError(
                f"HistoricalDataBar for {self.symbol}: open ({self.open}) "
                f"must be between low ({self.low}) and high ({self.high})"
            )
        if not (self.low <= self.close <= self.high):
            raise ValueError(
                f"HistoricalDataBar for {self.symbol}: close ({self.close}) "
                f"must be between low ({self.low}) and high ({self.high})"
            )

        # Validate non-negative volume
        if self.volume < 0:
            raise ValueError(
                f"HistoricalDataBar for {self.symbol}: volume ({self.volume}) must be >= 0"
            )


@dataclass(frozen=True)
class Trade:
    """
    Individual simulated trade record.

    Captures complete trade lifecycle from entry to exit with P&L calculations,
    commission, slippage, and exit reason.

    Attributes:
        symbol: Stock ticker symbol
        entry_date: When position opened (UTC)
        entry_price: Fill price for entry (Decimal for precision)
        exit_date: When position closed (UTC)
        exit_price: Fill price for exit (Decimal for precision)
        shares: Number of shares traded (positive integer)
        pnl: Profit/loss in dollars (Decimal)
        pnl_pct: Return percentage (Decimal)
        duration_days: Holding period in days
        exit_reason: Why position closed (stop_loss, take_profit, strategy_signal, end_of_data)
        commission: Total commission paid entry + exit (Decimal)
        slippage: Total slippage cost in dollars (Decimal)
        metadata: Optional dict for additional info (e.g., strategy_id)

    Raises:
        ValueError: If validation fails (exit before entry, non-positive shares, etc.)
    """
    symbol: str
    entry_date: datetime
    entry_price: Decimal
    exit_date: datetime
    exit_price: Decimal
    shares: int
    pnl: Decimal
    pnl_pct: Decimal
    duration_days: int
    exit_reason: str
    commission: Decimal
    slippage: Decimal
    metadata: dict[str, str] | None = None

    def __post_init__(self) -> None:
        """Validate trade consistency after initialization."""
        # Validate UTC timestamps
        if self.entry_date.tzinfo is None:
            raise ValueError(
                f"Trade for {self.symbol}: entry_date must be timezone-aware (UTC)"
            )
        if self.exit_date.tzinfo is None:
            raise ValueError(
                f"Trade for {self.symbol}: exit_date must be timezone-aware (UTC)"
            )

        # Validate exit_date > entry_date
        if self.exit_date <= self.entry_date:
            raise ValueError(
                f"Trade for {self.symbol}: exit_date ({self.exit_date}) must be after "
                f"entry_date ({self.entry_date})"
            )

        # Validate positive shares
        if self.shares <= 0:
            raise ValueError(
                f"Trade for {self.symbol}: shares ({self.shares}) must be positive"
            )

        # Validate positive entry/exit prices
        if self.entry_price <= 0:
            raise ValueError(
                f"Trade for {self.symbol}: entry_price ({self.entry_price}) must be positive"
            )
        if self.exit_price <= 0:
            raise ValueError(
                f"Trade for {self.symbol}: exit_price ({self.exit_price}) must be positive"
            )

        # Validate non-negative commission and slippage
        if self.commission < 0:
            raise ValueError(
                f"Trade for {self.symbol}: commission ({self.commission}) must be non-negative"
            )
        if self.slippage < 0:
            raise ValueError(
                f"Trade for {self.symbol}: slippage ({self.slippage}) must be non-negative"
            )

        # Validate duration_days matches date difference
        expected_duration = (self.exit_date - self.entry_date).days
        if self.duration_days != expected_duration:
            raise ValueError(
                f"Trade for {self.symbol}: duration_days ({self.duration_days}) does not match "
                f"calculated duration ({expected_duration})"
            )

        # Validate P&L calculation: pnl = (exit_price - entry_price) * shares - commission - slippage
        expected_pnl = (self.exit_price - self.entry_price) * self.shares - self.commission - self.slippage
        # Allow small floating point error (1 cent)
        if abs(self.pnl - expected_pnl) > Decimal("0.01"):
            raise ValueError(
                f"Trade for {self.symbol}: pnl ({self.pnl}) does not match "
                f"calculated pnl ({expected_pnl})"
            )

        # Validate P&L percentage: pnl_pct = pnl / (entry_price * shares)
        expected_pnl_pct = self.pnl / (self.entry_price * self.shares)
        # Allow small floating point error (0.01%)
        if abs(self.pnl_pct - expected_pnl_pct) > Decimal("0.0001"):
            raise ValueError(
                f"Trade for {self.symbol}: pnl_pct ({self.pnl_pct}) does not match "
                f"calculated pnl_pct ({expected_pnl_pct})"
            )


@dataclass(frozen=True)
class PerformanceMetrics:
    """
    Aggregated statistics from backtest results.

    Comprehensive performance metrics including returns, risk metrics,
    win rate, profit factor, and drawdown statistics.

    Attributes:
        total_return: Total percentage return (Decimal)
        annualized_return: Annualized percentage return (Decimal)
        cagr: Compound annual growth rate (Decimal)
        win_rate: Percentage of profitable trades 0-1 (Decimal)
        profit_factor: Gross profit / gross loss (Decimal)
        average_win: Average profit on winning trades (Decimal)
        average_loss: Average loss on losing trades (Decimal)
        max_drawdown: Maximum peak-to-trough decline 0-1 (Decimal)
        max_drawdown_duration_days: Longest drawdown period in days
        sharpe_ratio: Risk-adjusted return metric (Decimal)
        total_trades: Number of completed trades
        winning_trades: Number of profitable trades
        losing_trades: Number of unprofitable trades

    Raises:
        ValueError: If validation fails (incorrect trade counts, invalid ranges, etc.)
    """
    total_return: Decimal
    annualized_return: Decimal
    cagr: Decimal
    win_rate: Decimal
    profit_factor: Decimal
    average_win: Decimal
    average_loss: Decimal
    max_drawdown: Decimal
    max_drawdown_duration_days: int
    sharpe_ratio: Decimal
    total_trades: int
    winning_trades: int
    losing_trades: int

    def __post_init__(self) -> None:
        """Validate performance metrics after initialization."""
        # Validate total_trades >= winning_trades + losing_trades (accounts for breakeven trades with pnl == 0)
        if self.total_trades < self.winning_trades + self.losing_trades:
            raise ValueError(
                f"PerformanceMetrics: total_trades ({self.total_trades}) must be >= "
                f"winning_trades ({self.winning_trades}) + losing_trades ({self.losing_trades})"
            )

        # Validate non-negative trade counts
        if self.total_trades < 0:
            raise ValueError(
                f"PerformanceMetrics: total_trades ({self.total_trades}) must be non-negative"
            )
        if self.winning_trades < 0:
            raise ValueError(
                f"PerformanceMetrics: winning_trades ({self.winning_trades}) must be non-negative"
            )
        if self.losing_trades < 0:
            raise ValueError(
                f"PerformanceMetrics: losing_trades ({self.losing_trades}) must be non-negative"
            )

        # Validate win_rate calculation (only if trades exist)
        if self.total_trades > 0:
            expected_win_rate = Decimal(self.winning_trades) / Decimal(self.total_trades)
            # Allow small floating point error (0.01%)
            if abs(self.win_rate - expected_win_rate) > Decimal("0.0001"):
                raise ValueError(
                    f"PerformanceMetrics: win_rate ({self.win_rate}) does not match "
                    f"calculated win_rate ({expected_win_rate})"
                )

        # Validate win_rate range
        if not (0 <= self.win_rate <= 1):
            raise ValueError(
                f"PerformanceMetrics: win_rate ({self.win_rate}) must be in range [0, 1]"
            )

        # Validate max_drawdown range
        if not (0 <= self.max_drawdown <= 1):
            raise ValueError(
                f"PerformanceMetrics: max_drawdown ({self.max_drawdown}) must be in range [0, 1]"
            )

        # Validate non-negative drawdown duration
        if self.max_drawdown_duration_days < 0:
            raise ValueError(
                f"PerformanceMetrics: max_drawdown_duration_days ({self.max_drawdown_duration_days}) "
                f"must be non-negative"
            )

        # Validate profit_factor is positive (or zero if no trades)
        if self.profit_factor < 0:
            raise ValueError(
                f"PerformanceMetrics: profit_factor ({self.profit_factor}) must be non-negative"
            )


@dataclass(frozen=True)
class Position:
    """
    Open position during backtest execution.

    Represents a currently held position with entry price, current price,
    entry date, and auto-calculated unrealized P&L.

    Attributes:
        symbol: Stock ticker symbol
        shares: Number of shares held (positive integer)
        entry_price: Average entry price (Decimal for precision)
        entry_date: When position was opened (UTC)
        current_price: Current market price (Decimal for precision)

    Raises:
        ValueError: If validation fails (non-positive shares/prices, invalid dates)
    """
    symbol: str
    shares: int
    entry_price: Decimal
    entry_date: datetime
    current_price: Decimal

    def __post_init__(self) -> None:
        """Validate position consistency after initialization."""
        # Validate positive shares
        if self.shares <= 0:
            raise ValueError(
                f"Position for {self.symbol}: shares ({self.shares}) must be positive"
            )

        # Validate positive entry price
        if self.entry_price <= 0:
            raise ValueError(
                f"Position for {self.symbol}: entry_price ({self.entry_price}) must be positive"
            )

        # Validate positive current price
        if self.current_price <= 0:
            raise ValueError(
                f"Position for {self.symbol}: current_price ({self.current_price}) must be positive"
            )

        # Validate UTC timestamp
        if self.entry_date.tzinfo is None:
            raise ValueError(
                f"Position for {self.symbol}: entry_date must be timezone-aware (UTC)"
            )


@dataclass
class BacktestState:
    """
    Internal state during backtest execution.

    Mutable state object that tracks current date, cash, open positions,
    equity history, completed trades, and warnings during backtesting.

    Attributes:
        current_date: Current simulation date (UTC)
        cash: Available cash in portfolio (Decimal)
        positions: Open positions by symbol (Dict[str, Position])
        equity_history: Portfolio value over time (List of timestamp, value tuples)
        trades: Completed trades (List[Trade])
        warnings: Data quality issues encountered (List[str])

    Raises:
        ValueError: If validation fails (negative cash, etc.)
    """
    current_date: datetime
    cash: Decimal
    positions: dict[str, Position] = field(default_factory=dict)
    equity_history: list[tuple[datetime, Decimal]] = field(default_factory=list)
    trades: list[Trade] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate backtest state after initialization."""
        # Validate UTC timestamp
        if self.current_date.tzinfo is None:
            raise ValueError("BacktestState: current_date must be timezone-aware (UTC)")

        # Validate non-negative cash
        if self.cash < 0:
            raise ValueError(f"BacktestState: cash ({self.cash}) must be non-negative")


@dataclass(frozen=True)
class OrchestratorConfig:
    """
    Configuration parameters for strategy orchestrator.

    Defines orchestrator behavior for managing multiple strategies,
    including logging level and weight validation settings.

    Attributes:
        logging_level: Logging verbosity level (default: "INFO")
        validate_weights: Whether to validate strategy weight sum (default: True)

    Raises:
        ValueError: If validation fails (invalid logging_level)
    """
    logging_level: str = "INFO"
    validate_weights: bool = True

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        # Validate logging_level is one of the allowed values
        allowed_levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
        if self.logging_level not in allowed_levels:
            raise ValueError(
                f"OrchestratorConfig: logging_level ('{self.logging_level}') must be one of "
                f"{allowed_levels}"
            )



@dataclass
class StrategyAllocation:
    """
    Capital allocation tracking for a single strategy in orchestrator.

    Mutable dataclass that tracks allocated capital, used capital, and
    available capital for a strategy. Provides methods to allocate and
    release capital with validation.

    Attributes:
        strategy_id: Unique identifier for the strategy
        allocated_capital: Total capital allocated to this strategy (Decimal)
        used_capital: Capital currently in use by open positions (Decimal)
        available_capital: Capital available for new positions (Decimal)

    Raises:
        ValueError: If validation fails (negative capital, invariant violations)
    """
    strategy_id: str
    allocated_capital: Decimal
    used_capital: Decimal = Decimal("0.0")
    available_capital: Decimal = field(init=False)

    def __post_init__(self) -> None:
        """Validate allocation state and calculate available capital."""
        # Validate allocated_capital > 0
        if self.allocated_capital <= 0:
            raise ValueError(
                f"StrategyAllocation for {self.strategy_id}: allocated_capital "
                f"({self.allocated_capital}) must be positive"
            )

        # Validate used_capital >= 0
        if self.used_capital < 0:
            raise ValueError(
                f"StrategyAllocation for {self.strategy_id}: used_capital "
                f"({self.used_capital}) must be non-negative"
            )

        # Validate used_capital <= allocated_capital
        if self.used_capital > self.allocated_capital:
            raise ValueError(
                f"StrategyAllocation for {self.strategy_id}: used_capital "
                f"({self.used_capital}) cannot exceed allocated_capital ({self.allocated_capital})"
            )

        # Calculate available_capital = allocated - used
        object.__setattr__(self, 'available_capital', self.allocated_capital - self.used_capital)

    def allocate(self, amount: Decimal) -> None:
        """
        Allocate capital for a new position.

        Increases used_capital and decreases available_capital by the specified amount.
        Validates that sufficient capital is available before allocation.

        Args:
            amount: Amount of capital to allocate (must be positive)

        Raises:
            ValueError: If amount is non-positive or exceeds available capital
        """
        if amount <= 0:
            raise ValueError(
                f"StrategyAllocation.allocate for {self.strategy_id}: amount "
                f"({amount}) must be positive"
            )

        if amount > self.available_capital:
            raise ValueError(
                f"StrategyAllocation.allocate for {self.strategy_id}: amount "
                f"({amount}) exceeds available_capital ({self.available_capital})"
            )

        self.used_capital += amount
        self.available_capital -= amount

    def release(self, amount: Decimal) -> None:
        """
        Release capital from a closed position.

        Decreases used_capital and increases available_capital by the specified amount.
        Validates that sufficient capital is currently in use.

        Args:
            amount: Amount of capital to release (must be positive)

        Raises:
            ValueError: If amount is non-positive or exceeds used capital
        """
        if amount <= 0:
            raise ValueError(
                f"StrategyAllocation.release for {self.strategy_id}: amount "
                f"({amount}) must be positive"
            )

        if amount > self.used_capital:
            raise ValueError(
                f"StrategyAllocation.release for {self.strategy_id}: amount "
                f"({amount}) exceeds used_capital ({self.used_capital})"
            )

        self.used_capital -= amount
        self.available_capital += amount

    def can_allocate(self, amount: Decimal) -> bool:
        """
        Check if sufficient capital is available for allocation.

        Args:
            amount: Amount of capital to check (must be positive)

        Returns:
            True if amount <= available_capital, False otherwise

        Raises:
            ValueError: If amount is non-positive
        """
        if amount <= 0:
            raise ValueError(
                f"StrategyAllocation.can_allocate for {self.strategy_id}: amount "
                f"({amount}) must be positive"
            )

        return amount <= self.available_capital



@dataclass(frozen=True)
class BacktestResult:
    """
    Complete output of backtest run with all data and metrics.

    Immutable result object containing configuration, all trades,
    equity curve, performance metrics, and execution metadata.

    Attributes:
        config: Configuration used for this run
        trades: All simulated trades in chronological order (List[Trade])
        equity_curve: Portfolio value over time (List of timestamp, value tuples)
        metrics: Calculated performance statistics
        data_warnings: Data quality issues encountered during backtest (List[str])
        execution_time_seconds: Time taken to run backtest
        completed_at: Timestamp when backtest finished (UTC)

    Raises:
        ValueError: If validation fails (unsorted trades, negative execution time, etc.)
    """
    config: BacktestConfig
    trades: list[Trade]
    equity_curve: list[tuple[datetime, Decimal]]
    metrics: PerformanceMetrics
    data_warnings: list[str]
    execution_time_seconds: float
    completed_at: datetime

    def __post_init__(self) -> None:
        """Validate backtest result after initialization."""
        # Validate UTC timestamp
        if self.completed_at.tzinfo is None:
            raise ValueError("BacktestResult: completed_at must be timezone-aware (UTC)")

        # Validate positive execution time
        if self.execution_time_seconds <= 0:
            raise ValueError(
                f"BacktestResult: execution_time_seconds ({self.execution_time_seconds}) "
                f"must be positive"
            )

        # Validate trades are sorted by entry_date (chronological)
        if len(self.trades) > 1:
            for i in range(len(self.trades) - 1):
                if self.trades[i].entry_date > self.trades[i + 1].entry_date:
                    raise ValueError(
                        f"BacktestResult: trades must be sorted by entry_date "
                        f"(trade at index {i} entered after trade at index {i + 1})"
                    )

        # Validate equity_curve is sorted by timestamp (chronological)
        if len(self.equity_curve) > 1:
            for i in range(len(self.equity_curve) - 1):
                if self.equity_curve[i][0] > self.equity_curve[i + 1][0]:
                    raise ValueError(
                        f"BacktestResult: equity_curve must be sorted by timestamp "
                        f"(point at index {i} is after point at index {i + 1})"
                    )

    @property
    def final_equity(self) -> Decimal:
        """
        Get final portfolio equity value.

        Convenience property that returns the last equity value from the
        equity curve, or initial_capital if no equity data exists.

        Returns:
            Final portfolio equity value (Decimal)
        """
        if not self.equity_curve:
            return self.config.initial_capital
        return self.equity_curve[-1][1]


@dataclass(frozen=True)
class OrchestratorConfig:
    """
    Configuration parameters for strategy orchestrator.

    Defines orchestrator-level settings for logging and validation
    when coordinating multiple strategies in a single backtest.

    Attributes:
        logging_level: Logging verbosity level (default: "INFO")
        validate_weights: Whether to validate strategy weight sum (default: True)

    Raises:
        ValueError: If logging_level is not one of ["DEBUG", "INFO", "WARNING", "ERROR"]
    """
    logging_level: str = "INFO"
    validate_weights: bool = True

    def __post_init__(self) -> None:
        """Validate orchestrator configuration after initialization."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
        if self.logging_level not in valid_levels:
            raise ValueError(
                f"OrchestratorConfig: logging_level ({self.logging_level}) must be one of {valid_levels}"
            )


@dataclass(frozen=True)
class OrchestratorResult:
    """
    Aggregated results from multi-strategy orchestrator run.

    Contains aggregate portfolio metrics, individual strategy results,
    and comparison data for multi-strategy backtesting analysis.

    Attributes:
        aggregate_metrics: Combined performance metrics for entire portfolio
        strategy_results: Individual BacktestResult for each strategy by strategy_id
        comparison_table: Comparative metrics across strategies (e.g., returns, Sharpe ratios)

    Raises:
        ValueError: If validation fails (empty results, missing strategy data, etc.)
    """
    aggregate_metrics: PerformanceMetrics
    strategy_results: dict[str, BacktestResult]
    comparison_table: dict[str, dict]

    def __post_init__(self) -> None:
        """Validate orchestrator result after initialization."""
        # Validate non-empty strategy_results
        if not self.strategy_results:
            raise ValueError(
                "OrchestratorResult: strategy_results dictionary cannot be empty"
            )

        # Validate all values are BacktestResult instances
        for strategy_id, result in self.strategy_results.items():
            if not isinstance(result, BacktestResult):
                raise ValueError(
                    f"OrchestratorResult: strategy_results['{strategy_id}'] must be "
                    f"BacktestResult instance, got {type(result).__name__}"
                )

        # Validate comparison_table keys match strategy_results keys
        if self.comparison_table:
            for strategy_id in self.comparison_table.keys():
                if strategy_id not in self.strategy_results:
                    raise ValueError(
                        f"OrchestratorResult: comparison_table contains strategy_id "
                        f"'{strategy_id}' not found in strategy_results"
                    )

    def to_dict(self) -> dict:
        """
        Convert orchestrator result to dictionary for serialization.

        Returns dictionary with aggregate metrics, per-strategy results,
        and comparison data suitable for JSON/YAML export.

        Returns:
            Dictionary representation of orchestrator result
        """
        return {
            "aggregate_metrics": {
                "total_return": float(self.aggregate_metrics.total_return),
                "annualized_return": float(self.aggregate_metrics.annualized_return),
                "cagr": float(self.aggregate_metrics.cagr),
                "win_rate": float(self.aggregate_metrics.win_rate),
                "profit_factor": float(self.aggregate_metrics.profit_factor),
                "average_win": float(self.aggregate_metrics.average_win),
                "average_loss": float(self.aggregate_metrics.average_loss),
                "max_drawdown": float(self.aggregate_metrics.max_drawdown),
                "max_drawdown_duration_days": self.aggregate_metrics.max_drawdown_duration_days,
                "sharpe_ratio": float(self.aggregate_metrics.sharpe_ratio),
                "total_trades": self.aggregate_metrics.total_trades,
                "winning_trades": self.aggregate_metrics.winning_trades,
                "losing_trades": self.aggregate_metrics.losing_trades,
            },
            "strategy_results": {
                strategy_id: {
                    "final_equity": float(result.final_equity),
                    "total_trades": result.metrics.total_trades,
                    "win_rate": float(result.metrics.win_rate),
                    "total_return": float(result.metrics.total_return),
                    "sharpe_ratio": float(result.metrics.sharpe_ratio),
                    "max_drawdown": float(result.metrics.max_drawdown),
                }
                for strategy_id, result in self.strategy_results.items()
            },
            "comparison_table": self.comparison_table,
        }

    def get_strategy_result(self, strategy_id: str) -> BacktestResult:
        """
        Retrieve BacktestResult for specific strategy by ID.

        Args:
            strategy_id: Strategy identifier (must exist in strategy_results)

        Returns:
            BacktestResult for the requested strategy

        Raises:
            KeyError: If strategy_id not found in results
        """
        if strategy_id not in self.strategy_results:
            raise KeyError(
                f"Strategy ID '{strategy_id}' not found in results. "
                f"Available strategies: {list(self.strategy_results.keys())}"
            )
        return self.strategy_results[strategy_id]
