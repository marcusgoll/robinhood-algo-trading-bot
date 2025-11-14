"""Data models for ML-based trading strategies."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Protocol
from uuid import UUID, uuid4

import numpy as np
from numpy.typing import NDArray


class StrategyType(str, Enum):
    """Strategy generation method."""

    GENETIC_PROGRAMMING = "genetic_programming"
    REINFORCEMENT_LEARNING = "reinforcement_learning"
    LLM_GENERATED = "llm_generated"
    RULE_BASED = "rule_based"
    ENSEMBLE = "ensemble"
    HYBRID = "hybrid"


class StrategyStatus(str, Enum):
    """Strategy lifecycle status."""

    GENERATED = "generated"  # Just created
    BACKTESTING = "backtesting"  # In backtest
    VALIDATED = "validated"  # Passed validation
    FORWARD_TESTING = "forward_testing"  # Walk-forward test
    DEPLOYED = "deployed"  # Live trading
    RETIRED = "retired"  # Removed from production
    FAILED = "failed"  # Failed validation


@dataclass
class StrategyMetrics:
    """Performance metrics for a trading strategy.

    Attributes:
        sharpe_ratio: Risk-adjusted return (target: >1.5)
        max_drawdown: Maximum peak-to-trough decline (target: <20%)
        win_rate: Percentage of profitable trades (target: >55%)
        profit_factor: Gross profit / gross loss (target: >1.5)
        avg_win_loss_ratio: Average win / average loss (target: >1.5)
        total_return: Cumulative return (%)
        num_trades: Total number of trades
        consecutive_wins: Max consecutive winning trades
        consecutive_losses: Max consecutive losing trades
        avg_trade_duration: Average holding period (minutes)
        recovery_factor: Total return / max drawdown
        sortino_ratio: Downside risk-adjusted return
        calmar_ratio: Annual return / max drawdown
        correlation_to_spy: Correlation with S&P 500 (target: <0.7)
    """

    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_win_loss_ratio: float = 0.0
    total_return: float = 0.0
    num_trades: int = 0
    consecutive_wins: int = 0
    consecutive_losses: int = 0
    avg_trade_duration: float = 0.0
    recovery_factor: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    correlation_to_spy: float = 0.0

    # Additional metrics
    daily_sharpe: float = 0.0
    monthly_sharpe: float = 0.0
    value_at_risk_95: float = 0.0  # 95% VaR
    conditional_var_95: float = 0.0  # 95% CVaR (Expected Shortfall)
    ulcer_index: float = 0.0  # Drawdown severity measure

    def get_fitness_score(self) -> float:
        """Calculate multi-objective fitness score.

        Weighted combination of key metrics:
        - Sharpe ratio: 30%
        - Profit factor: 20%
        - Win rate: 20%
        - Max drawdown (inverted): 30%

        Returns:
            Fitness score (0-100, higher is better)
        """
        sharpe_component = min(self.sharpe_ratio / 3.0, 1.0) * 30
        pf_component = min(self.profit_factor / 3.0, 1.0) * 20
        wr_component = self.win_rate * 20
        dd_component = max(1.0 - self.max_drawdown, 0.0) * 30

        return sharpe_component + pf_component + wr_component + dd_component

    def is_production_ready(self) -> bool:
        """Check if strategy meets minimum production thresholds.

        Criteria:
        - Sharpe ratio >= 1.5
        - Max drawdown <= 20%
        - Win rate >= 50%
        - Profit factor >= 1.5
        - Num trades >= 30 (statistical significance)
        - Consecutive losses <= 5

        Returns:
            True if all criteria met
        """
        return (
            self.sharpe_ratio >= 1.5
            and self.max_drawdown <= 0.20
            and self.win_rate >= 0.50
            and self.profit_factor >= 1.5
            and self.num_trades >= 30
            and self.consecutive_losses <= 5
        )


@dataclass
class StrategyGene:
    """Gene representation for genetic programming strategies.

    A gene encodes a trading rule as a syntax tree:
    - Nodes: Operators (add, sub, mul, div, max, min, etc.)
    - Leaves: Features (price, volume, indicators) or constants

    Example tree:
        (and
            (> (/ close (sma close 20)) 1.02)  # Price > SMA(20) * 1.02
            (> rsi 30)                          # RSI > 30
        )

    Attributes:
        tree: String representation of syntax tree
        depth: Tree depth (complexity measure)
        num_nodes: Total nodes in tree
        features_used: Set of feature names referenced
        constants: Constant values used in tree
        entry_rule: Compiled entry function
        exit_rule: Compiled exit function
    """

    tree: str
    depth: int
    num_nodes: int
    features_used: set[str] = field(default_factory=set)
    constants: dict[str, float] = field(default_factory=dict)
    entry_rule: Callable[[dict[str, float]], bool] | None = None
    exit_rule: Callable[[dict[str, float]], bool] | None = None

    def complexity_score(self) -> float:
        """Calculate complexity penalty (0-1, lower is better)."""
        # Penalize deep trees and many nodes
        depth_penalty = min(self.depth / 10.0, 1.0)
        node_penalty = min(self.num_nodes / 50.0, 1.0)
        return (depth_penalty + node_penalty) / 2.0


@dataclass
class FeatureSet:
    """Feature vector for ML model input.

    Contains technical indicators, price patterns, sentiment, etc.
    All features are normalized to [-1, 1] range for model stability.

    Attributes:
        timestamp: Feature calculation time (UTC)
        symbol: Ticker symbol

        # Price features (10)
        returns_1d: 1-day return
        returns_5d: 5-day return
        returns_20d: 20-day return
        volatility_20d: 20-day realized volatility
        volume_ratio: Volume / 20-day average
        high_low_range: (high - low) / close
        close_to_high: (close - low) / (high - low)
        price_to_sma20: close / SMA(20)
        price_to_sma50: close / SMA(50)
        price_to_vwap: close / VWAP

        # Technical indicators (15)
        rsi_14: RSI (14-period)
        macd: MACD line
        macd_signal: MACD signal line
        macd_histogram: MACD histogram
        stoch_k: Stochastic %K
        stoch_d: Stochastic %D
        atr_14: ATR (14-period)
        adx_14: ADX (trend strength)
        cci_20: Commodity Channel Index
        williams_r: Williams %R
        roc_10: Rate of Change (10-period)
        momentum_20: Momentum (20-period)
        bollinger_pct: (close - bb_lower) / (bb_upper - bb_lower)
        keltner_pct: (close - kc_lower) / (kc_upper - kc_lower)
        donchian_pct: (close - dc_lower) / (dc_upper - dc_lower)

        # Market microstructure (5)
        bid_ask_spread: Spread as % of mid
        order_imbalance: Buy volume / total volume - 0.5
        tick_direction: +1 (uptick), -1 (downtick), 0 (no change)
        vwap_distance: (close - vwap) / vwap
        volume_profile_rank: Percentile in today's volume distribution

        # Sentiment (3)
        news_sentiment: FinBERT sentiment score (-1 to 1)
        social_sentiment: Twitter/Reddit sentiment (-1 to 1)
        options_sentiment: Put/call ratio deviation

        # Time features (4)
        hour_of_day: Hour (0-23) / 23
        day_of_week: Weekday (0-4) / 4
        days_to_earnings: Days until earnings / 90 (capped)
        days_from_earnings: Days since earnings / 90 (capped)

        # Support/Resistance features (9)
        distance_to_nearest_support: % distance to nearest support below (-0.05 to 0)
        distance_to_nearest_resistance: % distance to nearest resistance above (0 to +0.05)
        support_strength: Strength of nearest support (0-1)
        resistance_strength: Strength of nearest resistance (0-1)
        between_levels: 1 if price between strong S/R, else 0
        num_supports_below: Count of support levels below price
        num_resistances_above: Count of resistance levels above price
        avg_support_distance: Average % distance to all supports below
        avg_resistance_distance: Average % distance to all resistances above

        # Pattern features (6)
        in_uptrend: 1 if above rising SMA(50), else 0
        in_downtrend: 1 if below falling SMA(50), else 0
        bull_flag_score: Bull flag pattern strength (0-1)
        bear_flag_score: Bear flag pattern strength (0-1)
        breakout_signal: Breakout strength (-1 to 1)
        reversal_signal: Reversal strength (-1 to 1)
    """

    timestamp: datetime
    symbol: str

    # Price features (10)
    returns_1d: float = 0.0
    returns_5d: float = 0.0
    returns_20d: float = 0.0
    volatility_20d: float = 0.0
    volume_ratio: float = 1.0
    high_low_range: float = 0.0
    close_to_high: float = 0.5
    price_to_sma20: float = 1.0
    price_to_sma50: float = 1.0
    price_to_vwap: float = 1.0

    # Technical indicators (15)
    rsi_14: float = 50.0
    macd: float = 0.0
    macd_signal: float = 0.0
    macd_histogram: float = 0.0
    stoch_k: float = 50.0
    stoch_d: float = 50.0
    atr_14: float = 0.0
    adx_14: float = 0.0
    cci_20: float = 0.0
    williams_r: float = -50.0
    roc_10: float = 0.0
    momentum_20: float = 0.0
    bollinger_pct: float = 0.5
    keltner_pct: float = 0.5
    donchian_pct: float = 0.5

    # Market microstructure (5)
    bid_ask_spread: float = 0.0
    order_imbalance: float = 0.0
    tick_direction: float = 0.0
    vwap_distance: float = 0.0
    volume_profile_rank: float = 0.5

    # Sentiment (3)
    news_sentiment: float = 0.0
    social_sentiment: float = 0.0
    options_sentiment: float = 0.0

    # Time features (4)
    hour_of_day: float = 0.5
    day_of_week: float = 0.5
    days_to_earnings: float = 1.0
    days_from_earnings: float = 1.0

    # Support/Resistance features (9)
    distance_to_nearest_support: float = -0.05
    distance_to_nearest_resistance: float = 0.05
    support_strength: float = 0.0
    resistance_strength: float = 0.0
    between_levels: float = 0.0
    num_supports_below: float = 0.0
    num_resistances_above: float = 0.0
    avg_support_distance: float = -0.05
    avg_resistance_distance: float = 0.05

    # Pattern features (6)
    in_uptrend: float = 0.0
    in_downtrend: float = 0.0
    bull_flag_score: float = 0.0
    bear_flag_score: float = 0.0
    breakout_signal: float = 0.0
    reversal_signal: float = 0.0

    def to_array(self) -> NDArray[np.float64]:
        """Convert to NumPy array for ML model input.

        Returns:
            Array of shape (52,) with all features
            (10 price + 15 technical + 5 microstructure + 3 sentiment + 4 time + 9 S/R + 6 pattern)
        """
        return np.array(
            [
                # Price features
                self.returns_1d,
                self.returns_5d,
                self.returns_20d,
                self.volatility_20d,
                self.volume_ratio,
                self.high_low_range,
                self.close_to_high,
                self.price_to_sma20,
                self.price_to_sma50,
                self.price_to_vwap,
                # Technical indicators
                self.rsi_14,
                self.macd,
                self.macd_signal,
                self.macd_histogram,
                self.stoch_k,
                self.stoch_d,
                self.atr_14,
                self.adx_14,
                self.cci_20,
                self.williams_r,
                self.roc_10,
                self.momentum_20,
                self.bollinger_pct,
                self.keltner_pct,
                self.donchian_pct,
                # Market microstructure
                self.bid_ask_spread,
                self.order_imbalance,
                self.tick_direction,
                self.vwap_distance,
                self.volume_profile_rank,
                # Sentiment
                self.news_sentiment,
                self.social_sentiment,
                self.options_sentiment,
                # Time features
                self.hour_of_day,
                self.day_of_week,
                self.days_to_earnings,
                self.days_from_earnings,
                # Support/Resistance features
                self.distance_to_nearest_support,
                self.distance_to_nearest_resistance,
                self.support_strength,
                self.resistance_strength,
                self.between_levels,
                self.num_supports_below,
                self.num_resistances_above,
                self.avg_support_distance,
                self.avg_resistance_distance,
                # Pattern features
                self.in_uptrend,
                self.in_downtrend,
                self.bull_flag_score,
                self.bear_flag_score,
                self.breakout_signal,
                self.reversal_signal,
            ],
            dtype=np.float64,
        )

    @classmethod
    def feature_names(cls) -> list[str]:
        """Get ordered list of feature names."""
        return [
            # Price features
            "returns_1d",
            "returns_5d",
            "returns_20d",
            "volatility_20d",
            "volume_ratio",
            "high_low_range",
            "close_to_high",
            "price_to_sma20",
            "price_to_sma50",
            "price_to_vwap",
            # Technical indicators
            "rsi_14",
            "macd",
            "macd_signal",
            "macd_histogram",
            "stoch_k",
            "stoch_d",
            "atr_14",
            "adx_14",
            "cci_20",
            "williams_r",
            "roc_10",
            "momentum_20",
            "bollinger_pct",
            "keltner_pct",
            "donchian_pct",
            # Market microstructure
            "bid_ask_spread",
            "order_imbalance",
            "tick_direction",
            "vwap_distance",
            "volume_profile_rank",
            # Sentiment
            "news_sentiment",
            "social_sentiment",
            "options_sentiment",
            # Time features
            "hour_of_day",
            "day_of_week",
            "days_to_earnings",
            "days_from_earnings",
            # Support/Resistance features
            "distance_to_nearest_support",
            "distance_to_nearest_resistance",
            "support_strength",
            "resistance_strength",
            "between_levels",
            "num_supports_below",
            "num_resistances_above",
            "avg_support_distance",
            "avg_resistance_distance",
            # Pattern features
            "in_uptrend",
            "in_downtrend",
            "bull_flag_score",
            "bear_flag_score",
            "breakout_signal",
            "reversal_signal",
        ]


@dataclass
class MLStrategy:
    """ML-generated trading strategy.

    Represents a complete trading strategy with entry/exit rules,
    parameters, performance metrics, and metadata.

    Attributes:
        id: Unique strategy identifier
        name: Human-readable name
        type: Strategy generation method
        status: Lifecycle status
        created_at: Creation timestamp
        updated_at: Last update timestamp

        # Strategy definition
        entry_logic: Entry rule (code or model)
        exit_logic: Exit rule (code or model)
        parameters: Strategy hyperparameters
        gene: Genetic programming gene (if applicable)
        model_path: Path to RL model weights (if applicable)
        llm_prompt: LLM generation prompt (if applicable)

        # Performance
        backtest_metrics: Metrics from historical backtest
        forward_test_metrics: Metrics from walk-forward test
        live_metrics: Metrics from live trading

        # Metadata
        generation_config: Config used for generation
        feature_importance: Feature importance scores
        training_duration_sec: Time to train/generate
        num_parameters: Total trainable parameters
        complexity_score: Complexity measure (0-1)

        # Deployment
        deployed_at: Deployment timestamp
        retirement_reason: Why strategy was retired
        ensemble_weight: Weight in ensemble (0-1)
    """

    id: UUID = field(default_factory=uuid4)
    name: str = ""
    type: StrategyType = StrategyType.GENETIC_PROGRAMMING
    status: StrategyStatus = StrategyStatus.GENERATED
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    # Strategy definition
    entry_logic: str | Callable = ""
    exit_logic: str | Callable = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    gene: StrategyGene | None = None
    model_path: str = ""
    llm_prompt: str = ""

    # Performance
    backtest_metrics: StrategyMetrics = field(default_factory=StrategyMetrics)
    forward_test_metrics: StrategyMetrics = field(default_factory=StrategyMetrics)
    live_metrics: StrategyMetrics = field(default_factory=StrategyMetrics)

    # Metadata
    generation_config: dict[str, Any] = field(default_factory=dict)
    feature_importance: dict[str, float] = field(default_factory=dict)
    training_duration_sec: float = 0.0
    num_parameters: int = 0
    complexity_score: float = 0.0

    # Deployment
    deployed_at: datetime | None = None
    retirement_reason: str = ""
    ensemble_weight: float = 0.0

    def get_overall_score(self) -> float:
        """Calculate weighted score across all test phases.

        Weights:
        - Backtest: 30%
        - Forward test: 50% (most important)
        - Live: 20%

        Returns:
            Overall fitness score (0-100)
        """
        backtest_score = self.backtest_metrics.get_fitness_score() * 0.30
        forward_score = self.forward_test_metrics.get_fitness_score() * 0.50
        live_score = self.live_metrics.get_fitness_score() * 0.20

        # Apply complexity penalty
        complexity_penalty = self.complexity_score * 10  # Max -10 points

        return max(backtest_score + forward_score + live_score - complexity_penalty, 0.0)

    def is_deployable(self) -> bool:
        """Check if strategy is ready for live deployment.

        Criteria:
        - Status is VALIDATED or FORWARD_TESTING
        - Backtest metrics pass minimum thresholds
        - Forward test metrics pass minimum thresholds
        - Overall score >= 60

        Returns:
            True if deployable
        """
        return (
            self.status
            in [StrategyStatus.VALIDATED, StrategyStatus.FORWARD_TESTING]
            and self.backtest_metrics.is_production_ready()
            and self.forward_test_metrics.is_production_ready()
            and self.get_overall_score() >= 60.0
        )


class IMLStrategyGenerator(Protocol):
    """Protocol for strategy generators.

    All strategy generators (GP, RL, LLM) must implement this interface.
    """

    def generate(
        self,
        num_strategies: int,
        historical_data: Any,
        config: dict[str, Any],
    ) -> list[MLStrategy]:
        """Generate new strategies.

        Args:
            num_strategies: Number of strategies to generate
            historical_data: Historical market data for training
            config: Generator-specific configuration

        Returns:
            List of generated strategies
        """
        ...

    def mutate(self, strategy: MLStrategy) -> MLStrategy:
        """Mutate existing strategy to create variant.

        Args:
            strategy: Strategy to mutate

        Returns:
            Mutated strategy
        """
        ...

    def crossover(
        self, strategy1: MLStrategy, strategy2: MLStrategy
    ) -> MLStrategy:
        """Combine two strategies to create offspring.

        Args:
            strategy1: First parent strategy
            strategy2: Second parent strategy

        Returns:
            Offspring strategy
        """
        ...


@dataclass
class StrategyEnsemble:
    """Ensemble of multiple strategies.

    Combines predictions from multiple strategies using weighted voting.

    Attributes:
        id: Unique ensemble identifier
        name: Ensemble name
        strategies: Component strategies
        weights: Strategy weights (must sum to 1.0)
        aggregation_method: How to combine signals (weighted_avg, majority_vote)
        created_at: Creation timestamp
        metrics: Ensemble performance metrics
    """

    id: UUID = field(default_factory=uuid4)
    name: str = ""
    strategies: list[MLStrategy] = field(default_factory=list)
    weights: list[float] = field(default_factory=list)
    aggregation_method: str = "weighted_avg"
    created_at: datetime = field(default_factory=datetime.utcnow)
    metrics: StrategyMetrics = field(default_factory=StrategyMetrics)

    def __post_init__(self) -> None:
        """Validate ensemble configuration."""
        if len(self.strategies) != len(self.weights):
            raise ValueError("Number of strategies must match number of weights")

        if len(self.weights) > 0 and not np.isclose(sum(self.weights), 1.0):
            raise ValueError(f"Weights must sum to 1.0, got {sum(self.weights)}")

    def predict_signal(self, features: FeatureSet) -> float:
        """Generate ensemble trading signal.

        Args:
            features: Current market features

        Returns:
            Signal strength (-1 to 1): -1=strong sell, 0=neutral, 1=strong buy
        """
        if not self.strategies:
            return 0.0

        signals = []
        for strategy, weight in zip(self.strategies, self.weights):
            # Get signal from each strategy (implementation depends on strategy type)
            # This is a placeholder - actual implementation in execution module
            signal = 0.0  # TODO: Implement signal generation
            signals.append(signal * weight)

        if self.aggregation_method == "weighted_avg":
            return sum(signals)
        elif self.aggregation_method == "majority_vote":
            # Count positive/negative signals
            positive = sum(1 for s in signals if s > 0)
            negative = sum(1 for s in signals if s < 0)
            if positive > negative:
                return 1.0
            elif negative > positive:
                return -1.0
            else:
                return 0.0
        else:
            raise ValueError(f"Unknown aggregation method: {self.aggregation_method}")
