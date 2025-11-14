"""Tests for ML configuration classes.

TDD approach: Write failing tests before implementation.
"""

import pytest
from pathlib import Path

from src.trading_bot.ml.config import (
    GeneticProgrammingConfig,
    ReinforcementLearningConfig,
    BacktestConfig,
    SelectionConfig,
    MLConfig,
)


class TestGeneticProgrammingConfig:
    """Tests for GeneticProgrammingConfig dataclass."""

    def test_default_config_values(self):
        """Test: Default configuration has sensible values.

        Given: No custom configuration
        When: Creating GeneticProgrammingConfig()
        Then: Default values match expected ranges
        """
        # Given/When
        config = GeneticProgrammingConfig()

        # Then: Check defaults
        assert config.population_size == 2000
        assert config.num_generations == 50
        assert config.tournament_size == 20
        assert config.mutation_rate == 0.15
        assert config.crossover_rate == 0.75
        assert config.elitism_pct == 0.10
        assert config.max_tree_depth == 6
        assert config.fitness_metric == "sharpe_ratio"
        assert config.parsimony_coefficient == 0.05

    def test_function_set_includes_operators(self):
        """Test: function_set includes required operators.

        Given: Default GeneticProgrammingConfig
        When: Accessing function_set
        Then: Contains arithmetic, logical, and comparison operators
        """
        # Given
        config = GeneticProgrammingConfig()

        # When
        funcs = config.function_set

        # Then: Arithmetic operators
        assert "add" in funcs
        assert "sub" in funcs
        assert "mul" in funcs
        assert "div" in funcs

        # Logic operators
        assert "and" in funcs
        assert "or" in funcs
        assert "not" in funcs

        # Comparison operators
        assert "gt" in funcs
        assert "lt" in funcs

    def test_terminal_set_includes_features(self):
        """Test: terminal_set includes market features and constants.

        Given: Default GeneticProgrammingConfig
        When: Accessing terminal_set
        Then: Contains price, indicators, and constants
        """
        # Given
        config = GeneticProgrammingConfig()

        # When
        terminals = config.terminal_set

        # Then: Price features
        assert "close" in terminals
        assert "volume" in terminals

        # Technical indicators
        assert "rsi" in terminals
        assert "macd" in terminals
        assert "atr" in terminals

        # Moving averages
        assert "sma_20" in terminals
        assert "sma_50" in terminals

        # Constants
        assert "const" in terminals

    def test_custom_config_values(self):
        """Test: Custom configuration values can be set.

        Given: Custom GP parameters
        When: Creating GeneticProgrammingConfig with kwargs
        Then: Custom values applied
        """
        # Given/When
        config = GeneticProgrammingConfig(
            population_size=1000,
            num_generations=100,
            mutation_rate=0.20,
            max_tree_depth=8,
        )

        # Then
        assert config.population_size == 1000
        assert config.num_generations == 100
        assert config.mutation_rate == 0.20
        assert config.max_tree_depth == 8

    def test_mutation_and_crossover_rates_sum_to_one(self):
        """Test: Mutation + crossover rates should sum near 1.0 for full coverage.

        Given: Default GeneticProgrammingConfig
        When: Calculating mutation_rate + crossover_rate
        Then: Sum <= 1.0 (valid probability distribution)
        """
        # Given
        config = GeneticProgrammingConfig()

        # When
        total_rate = config.mutation_rate + config.crossover_rate

        # Then: Should be <= 1.0 (can have some probability left for reproduction)
        assert total_rate <= 1.0


class TestBacktestConfig:
    """Tests for BacktestConfig dataclass."""

    def test_default_backtest_config(self):
        """Test: Default backtest configuration.

        Given: No custom configuration
        When: Creating BacktestConfig()
        Then: Default values for backtesting parameters set
        """
        # Given/When
        config = BacktestConfig()

        # Then
        assert config.initial_capital == 100_000.0
        assert config.commission_per_trade == 1.0
        assert config.slippage_bps == 10.0
        assert config.min_trades_required >= 30
        assert config.walk_forward_windows > 0

    def test_custom_backtest_parameters(self):
        """Test: Custom backtest parameters can be set.

        Given: Custom parameter values
        When: Creating BacktestConfig with kwargs
        Then: Custom values applied
        """
        # Given/When
        config = BacktestConfig(
            initial_capital=50_000.0,
            commission_per_trade=0.5,
            slippage_bps=5.0,
            min_trades_required=100,
        )

        # Then
        assert config.initial_capital == 50_000.0
        assert config.commission_per_trade == 0.5
        assert config.slippage_bps == 5.0
        assert config.min_trades_required == 100


class TestSelectionConfig:
    """Tests for SelectionConfig dataclass."""

    def test_default_selection_config(self):
        """Test: Default strategy selection configuration.

        Given: No custom configuration
        When: Creating SelectionConfig()
        Then: Default values for selection parameters set
        """
        # Given/When
        config = SelectionConfig()

        # Then: Check defaults
        assert config.selection_method == "pareto"
        assert config.num_strategies_to_select == 10
        assert config.min_fitness_threshold == 60.0
        assert config.diversity_weight == 0.30


class TestMLConfig:
    """Tests for MLConfig master configuration."""

    def test_ml_config_contains_all_subconfigs(self):
        """Test: MLConfig contains all sub-configurations.

        Given: Default MLConfig
        When: Accessing sub-config attributes
        Then: All configs are present
        """
        # Given/When
        config = MLConfig()

        # Then
        assert isinstance(config.gp_config, GeneticProgrammingConfig)
        assert isinstance(config.backtest_config, BacktestConfig)
        assert isinstance(config.selection_config, SelectionConfig)

    def test_ml_config_with_custom_subconfigs(self):
        """Test: MLConfig can be initialized with custom sub-configs.

        Given: Custom sub-configuration objects
        When: Creating MLConfig with custom configs
        Then: Custom configs used
        """
        # Given
        custom_gp = GeneticProgrammingConfig(population_size=500)
        custom_backtest = BacktestConfig(initial_capital=50_000.0)

        # When
        config = MLConfig(
            gp_config=custom_gp,
            backtest_config=custom_backtest,
        )

        # Then
        assert config.gp_config.population_size == 500
        assert config.backtest_config.initial_capital == 50_000.0
