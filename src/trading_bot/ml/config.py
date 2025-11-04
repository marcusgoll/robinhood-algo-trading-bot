"""Configuration for ML strategy generation system."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


@dataclass
class GeneticProgrammingConfig:
    """Configuration for genetic programming strategy generator.

    Genetic programming evolves trading rules as syntax trees:
    - Population: Pool of candidate strategies
    - Generations: Iterations of evolution
    - Selection: Tournament selection for breeding
    - Mutation: Random tree modification
    - Crossover: Combine two parent trees

    Attributes:
        population_size: Number of strategies in population (500-5000)
        num_generations: Evolution iterations (20-100)
        tournament_size: Candidates per tournament (10-50)
        mutation_rate: Probability of mutation (0.01-0.3)
        crossover_rate: Probability of crossover (0.5-0.9)
        elitism_pct: Top % to preserve unchanged (0.05-0.2)
        max_tree_depth: Maximum syntax tree depth (3-10)
        function_set: Allowed operators (add, sub, mul, div, etc.)
        terminal_set: Allowed features/constants
        fitness_metric: Optimization target (sharpe, profit_factor, etc.)
        parsimony_coefficient: Complexity penalty weight (0.0-0.1)
    """

    population_size: int = 2000
    num_generations: int = 50
    tournament_size: int = 20
    mutation_rate: float = 0.15
    crossover_rate: float = 0.75
    elitism_pct: float = 0.10
    max_tree_depth: int = 6
    function_set: list[str] = field(
        default_factory=lambda: [
            "add",
            "sub",
            "mul",
            "div",
            "sqrt",
            "abs",
            "log",
            "exp",
            "max",
            "min",
            "and",
            "or",
            "not",
            "gt",
            "lt",
            "gte",
            "lte",
        ]
    )
    terminal_set: list[str] = field(
        default_factory=lambda: [
            "close",
            "volume",
            "rsi",
            "macd",
            "atr",
            "sma_20",
            "sma_50",
            "ema_12",
            "ema_26",
            "const",
        ]
    )
    fitness_metric: str = "sharpe_ratio"
    parsimony_coefficient: float = 0.05


@dataclass
class ReinforcementLearningConfig:
    """Configuration for RL-based strategy generator.

    Uses PPO (Proximal Policy Optimization) to learn trading policies:
    - Environment: Custom Gym env with market data
    - Policy: Neural network mapping state -> action
    - Reward: Risk-adjusted returns (Sharpe, Sortino, etc.)

    Attributes:
        algorithm: RL algorithm (PPO, A2C, SAC, TD3)
        total_timesteps: Training steps (1M-10M)
        learning_rate: Adam optimizer LR (1e-5 to 1e-3)
        n_steps: Steps per update (128-2048)
        batch_size: Minibatch size (32-256)
        n_epochs: Gradient descent epochs per update (3-10)
        gamma: Discount factor (0.95-0.999)
        gae_lambda: GAE parameter (0.9-0.99)
        clip_range: PPO clipping parameter (0.1-0.3)
        ent_coef: Entropy bonus coefficient (0.0-0.1)
        vf_coef: Value function loss coefficient (0.5-1.0)
        max_grad_norm: Gradient clipping threshold (0.3-1.0)
        policy_network_arch: Hidden layer sizes
        value_network_arch: Hidden layer sizes
        activation: Activation function (relu, tanh, elu)
        normalize_observations: Whether to normalize inputs
        normalize_rewards: Whether to normalize rewards
        reward_function: Reward shaping (sharpe, sortino, profit)
        observation_window: Historical bars in state (20-100)
    """

    algorithm: Literal["PPO", "A2C", "SAC", "TD3"] = "PPO"
    total_timesteps: int = 2_000_000
    learning_rate: float = 3e-4
    n_steps: int = 2048
    batch_size: int = 64
    n_epochs: int = 10
    gamma: float = 0.99
    gae_lambda: float = 0.95
    clip_range: float = 0.2
    ent_coef: float = 0.01
    vf_coef: float = 0.5
    max_grad_norm: float = 0.5
    policy_network_arch: list[int] = field(default_factory=lambda: [256, 256])
    value_network_arch: list[int] = field(default_factory=lambda: [256, 256])
    activation: str = "tanh"
    normalize_observations: bool = True
    normalize_rewards: bool = True
    reward_function: str = "sharpe"
    observation_window: int = 60


@dataclass
class LLMConfig:
    """Configuration for LLM-guided strategy generation.

    Uses OpenAI GPT-4 to generate interpretable trading rules:
    - Prompt: Description of market regime + constraints
    - Output: JSON with entry/exit rules + parameters
    - Validation: Syntax check + backtest filter

    Attributes:
        model: OpenAI model (gpt-4, gpt-3.5-turbo)
        temperature: Sampling temperature (0.0-1.0)
        max_tokens: Max response tokens (500-2000)
        num_strategies_per_prompt: Strategies per API call (5-20)
        system_prompt_template: Base system prompt
        market_regime_analysis: Whether to analyze regime first
        constraint_spec: Trading constraints to enforce
        output_format: Response format (json, python, pseudocode)
        validation_mode: How to validate generated code (strict, lenient)
        max_retries: Max regeneration attempts for invalid output (3-10)
    """

    model: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: int = 1500
    num_strategies_per_prompt: int = 10
    system_prompt_template: str = """You are an expert quantitative trader generating algorithmic trading strategies.

Generate {num_strategies} distinct trading strategies for {market_regime} market conditions.

Each strategy must:
1. Have clear entry conditions (technical indicators + thresholds)
2. Have clear exit conditions (profit target, stop loss, time-based)
3. Include risk parameters (position size, max loss)
4. Be executable as Python code
5. Avoid overfitting - use robust indicators

Output format: JSON array of strategies with:
- name: Strategy name
- description: Brief explanation
- entry_conditions: List of conditions (AND logic)
- exit_conditions: List of conditions (OR logic)
- risk_params: {max_position_pct, stop_loss_pct, profit_target_pct}

Focus on strategies with different approaches:
- Trend following (MA crossovers, breakouts)
- Mean reversion (RSI, Bollinger Bands)
- Momentum (MACD, ROC)
- Pattern-based (support/resistance, flags)
- Sentiment-driven (news, social media)
"""
    market_regime_analysis: bool = True
    constraint_spec: dict[str, float] = field(
        default_factory=lambda: {
            "max_position_pct": 5.0,
            "max_stop_loss_pct": 5.0,
            "min_profit_target_pct": 1.0,
            "max_holding_hours": 24,
        }
    )
    output_format: str = "json"
    validation_mode: str = "strict"
    max_retries: int = 5


@dataclass
class BacktestConfig:
    """Configuration for strategy backtesting.

    Attributes:
        initial_capital: Starting capital ($)
        commission_per_trade: Commission cost ($)
        slippage_bps: Slippage in basis points (5-50)
        data_frequency: Bar frequency (1min, 5min, 1h, 1d)
        lookback_days: Historical data window (252-1260)
        train_test_split: Train/test split ratio (0.7-0.8)
        walk_forward_windows: Number of WF windows (5-20)
        min_trades_required: Minimum trades for statistical significance (30-100)
        benchmark_symbol: Benchmark ticker (SPY, QQQ)
    """

    initial_capital: float = 100_000.0
    commission_per_trade: float = 1.0
    slippage_bps: float = 10.0
    data_frequency: str = "5min"
    lookback_days: int = 504  # 2 years
    train_test_split: float = 0.75
    walk_forward_windows: int = 10
    min_trades_required: int = 50
    benchmark_symbol: str = "SPY"


@dataclass
class SelectionConfig:
    """Configuration for strategy selection and ensemble creation.

    Attributes:
        selection_method: How to select strategies (top_n, threshold, pareto)
        num_strategies_to_select: Top N strategies to keep (5-20)
        min_fitness_threshold: Minimum fitness score (0-100)
        max_correlation: Max pairwise correlation (0.5-0.8)
        diversity_weight: Diversity vs performance tradeoff (0.0-1.0)
        ensemble_method: Aggregation method (weighted_avg, majority_vote)
        weight_calculation: How to compute weights (equal, performance, kelly)
        rebalance_frequency_hours: How often to update weights (1-24)
    """

    selection_method: str = "pareto"
    num_strategies_to_select: int = 10
    min_fitness_threshold: float = 60.0
    max_correlation: float = 0.70
    diversity_weight: float = 0.30
    ensemble_method: str = "weighted_avg"
    weight_calculation: str = "kelly"
    rebalance_frequency_hours: int = 24


@dataclass
class MonitoringConfig:
    """Configuration for strategy performance monitoring.

    Attributes:
        degradation_threshold: Performance drop triggering alert (%)
        min_sharpe_ratio: Minimum acceptable Sharpe ratio
        max_drawdown_threshold: Max drawdown before pause (%)
        lookback_window_trades: Recent trades for rolling metrics (20-100)
        alert_on_consecutive_losses: Alert after N losses (3-5)
        auto_retire_on_failure: Auto-retire failing strategies
        retraining_frequency_days: How often to retrain (1-30)
        metric_update_frequency_sec: Real-time metric updates (5-60)
    """

    degradation_threshold: float = 0.30  # 30% drop
    min_sharpe_ratio: float = 1.0
    max_drawdown_threshold: float = 0.15  # 15%
    lookback_window_trades: int = 50
    alert_on_consecutive_losses: int = 4
    auto_retire_on_failure: bool = True
    retraining_frequency_days: int = 7
    metric_update_frequency_sec: int = 30


@dataclass
class MLConfig:
    """Master configuration for ML strategy generation system.

    Attributes:
        # Generator configs
        gp_config: Genetic programming config
        rl_config: Reinforcement learning config
        llm_config: LLM generation config

        # Pipeline configs
        backtest_config: Backtesting config
        selection_config: Strategy selection config
        monitoring_config: Performance monitoring config

        # General settings
        output_dir: Directory for saving strategies/models
        cache_dir: Directory for caching data
        log_dir: Directory for logs
        enable_parallel: Enable parallel strategy generation
        num_workers: Number of parallel workers (1-8)
        random_seed: Random seed for reproducibility
        verbose: Logging verbosity (0-2)

        # Safety limits
        max_strategies_in_memory: Max strategies to keep loaded (100-1000)
        max_deployed_strategies: Max strategies in production (5-20)
        daily_generation_limit: Max new strategies per day (50-500)
    """

    # Generator configs
    gp_config: GeneticProgrammingConfig = field(
        default_factory=GeneticProgrammingConfig
    )
    rl_config: ReinforcementLearningConfig = field(
        default_factory=ReinforcementLearningConfig
    )
    llm_config: LLMConfig = field(default_factory=LLMConfig)

    # Pipeline configs
    backtest_config: BacktestConfig = field(default_factory=BacktestConfig)
    selection_config: SelectionConfig = field(default_factory=SelectionConfig)
    monitoring_config: MonitoringConfig = field(default_factory=MonitoringConfig)

    # General settings
    output_dir: Path = field(default_factory=lambda: Path("ml_strategies"))
    cache_dir: Path = field(default_factory=lambda: Path("ml_cache"))
    log_dir: Path = field(default_factory=lambda: Path("logs/ml"))
    enable_parallel: bool = True
    num_workers: int = 4
    random_seed: int = 42
    verbose: int = 1

    # Safety limits
    max_strategies_in_memory: int = 500
    max_deployed_strategies: int = 10
    daily_generation_limit: int = 200

    def __post_init__(self) -> None:
        """Create directories if they don't exist."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_dict(cls, config_dict: dict) -> MLConfig:
        """Create config from dictionary.

        Args:
            config_dict: Configuration dictionary

        Returns:
            MLConfig instance
        """
        # Parse nested configs
        gp_config = GeneticProgrammingConfig(
            **config_dict.get("gp_config", {})
        )
        rl_config = ReinforcementLearningConfig(
            **config_dict.get("rl_config", {})
        )
        llm_config = LLMConfig(**config_dict.get("llm_config", {}))
        backtest_config = BacktestConfig(**config_dict.get("backtest_config", {}))
        selection_config = SelectionConfig(
            **config_dict.get("selection_config", {})
        )
        monitoring_config = MonitoringConfig(
            **config_dict.get("monitoring_config", {})
        )

        # Parse general settings
        general = config_dict.get("general", {})

        return cls(
            gp_config=gp_config,
            rl_config=rl_config,
            llm_config=llm_config,
            backtest_config=backtest_config,
            selection_config=selection_config,
            monitoring_config=monitoring_config,
            output_dir=Path(general.get("output_dir", "ml_strategies")),
            cache_dir=Path(general.get("cache_dir", "ml_cache")),
            log_dir=Path(general.get("log_dir", "logs/ml")),
            enable_parallel=general.get("enable_parallel", True),
            num_workers=general.get("num_workers", 4),
            random_seed=general.get("random_seed", 42),
            verbose=general.get("verbose", 1),
            max_strategies_in_memory=general.get("max_strategies_in_memory", 500),
            max_deployed_strategies=general.get("max_deployed_strategies", 10),
            daily_generation_limit=general.get("daily_generation_limit", 200),
        )

    def to_dict(self) -> dict:
        """Convert config to dictionary for serialization."""
        return {
            "gp_config": {
                "population_size": self.gp_config.population_size,
                "num_generations": self.gp_config.num_generations,
                "tournament_size": self.gp_config.tournament_size,
                "mutation_rate": self.gp_config.mutation_rate,
                "crossover_rate": self.gp_config.crossover_rate,
                "elitism_pct": self.gp_config.elitism_pct,
                "max_tree_depth": self.gp_config.max_tree_depth,
                "function_set": self.gp_config.function_set,
                "terminal_set": self.gp_config.terminal_set,
                "fitness_metric": self.gp_config.fitness_metric,
                "parsimony_coefficient": self.gp_config.parsimony_coefficient,
            },
            "rl_config": {
                "algorithm": self.rl_config.algorithm,
                "total_timesteps": self.rl_config.total_timesteps,
                "learning_rate": self.rl_config.learning_rate,
                "n_steps": self.rl_config.n_steps,
                "batch_size": self.rl_config.batch_size,
                "n_epochs": self.rl_config.n_epochs,
                "gamma": self.rl_config.gamma,
                "gae_lambda": self.rl_config.gae_lambda,
                "clip_range": self.rl_config.clip_range,
                "ent_coef": self.rl_config.ent_coef,
                "vf_coef": self.rl_config.vf_coef,
                "max_grad_norm": self.rl_config.max_grad_norm,
                "policy_network_arch": self.rl_config.policy_network_arch,
                "value_network_arch": self.rl_config.value_network_arch,
                "activation": self.rl_config.activation,
                "normalize_observations": self.rl_config.normalize_observations,
                "normalize_rewards": self.rl_config.normalize_rewards,
                "reward_function": self.rl_config.reward_function,
                "observation_window": self.rl_config.observation_window,
            },
            "llm_config": {
                "model": self.llm_config.model,
                "temperature": self.llm_config.temperature,
                "max_tokens": self.llm_config.max_tokens,
                "num_strategies_per_prompt": self.llm_config.num_strategies_per_prompt,
                "market_regime_analysis": self.llm_config.market_regime_analysis,
                "constraint_spec": self.llm_config.constraint_spec,
                "output_format": self.llm_config.output_format,
                "validation_mode": self.llm_config.validation_mode,
                "max_retries": self.llm_config.max_retries,
            },
            "backtest_config": {
                "initial_capital": self.backtest_config.initial_capital,
                "commission_per_trade": self.backtest_config.commission_per_trade,
                "slippage_bps": self.backtest_config.slippage_bps,
                "data_frequency": self.backtest_config.data_frequency,
                "lookback_days": self.backtest_config.lookback_days,
                "train_test_split": self.backtest_config.train_test_split,
                "walk_forward_windows": self.backtest_config.walk_forward_windows,
                "min_trades_required": self.backtest_config.min_trades_required,
                "benchmark_symbol": self.backtest_config.benchmark_symbol,
            },
            "selection_config": {
                "selection_method": self.selection_config.selection_method,
                "num_strategies_to_select": self.selection_config.num_strategies_to_select,
                "min_fitness_threshold": self.selection_config.min_fitness_threshold,
                "max_correlation": self.selection_config.max_correlation,
                "diversity_weight": self.selection_config.diversity_weight,
                "ensemble_method": self.selection_config.ensemble_method,
                "weight_calculation": self.selection_config.weight_calculation,
                "rebalance_frequency_hours": self.selection_config.rebalance_frequency_hours,
            },
            "monitoring_config": {
                "degradation_threshold": self.monitoring_config.degradation_threshold,
                "min_sharpe_ratio": self.monitoring_config.min_sharpe_ratio,
                "max_drawdown_threshold": self.monitoring_config.max_drawdown_threshold,
                "lookback_window_trades": self.monitoring_config.lookback_window_trades,
                "alert_on_consecutive_losses": self.monitoring_config.alert_on_consecutive_losses,
                "auto_retire_on_failure": self.monitoring_config.auto_retire_on_failure,
                "retraining_frequency_days": self.monitoring_config.retraining_frequency_days,
                "metric_update_frequency_sec": self.monitoring_config.metric_update_frequency_sec,
            },
            "general": {
                "output_dir": str(self.output_dir),
                "cache_dir": str(self.cache_dir),
                "log_dir": str(self.log_dir),
                "enable_parallel": self.enable_parallel,
                "num_workers": self.num_workers,
                "random_seed": self.random_seed,
                "verbose": self.verbose,
                "max_strategies_in_memory": self.max_strategies_in_memory,
                "max_deployed_strategies": self.max_deployed_strategies,
                "daily_generation_limit": self.daily_generation_limit,
            },
        }
