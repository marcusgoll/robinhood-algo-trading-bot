"""Tests for ML trading strategy models.

TDD approach: Write failing tests before implementation.
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from src.trading_bot.ml.models import (
    StrategyType,
    StrategyStatus,
    StrategyMetrics,
    StrategyGene,
    FeatureSet,
    MLStrategy,
)


class TestStrategyMetrics:
    """Tests for StrategyMetrics dataclass and calculations."""

    def test_get_fitness_score_perfect_metrics(self):
        """Test: Perfect metrics yield high fitness score (~100).

        Given: Strategy with ideal metrics (Sharpe=3.0, PF=3.0, WR=100%, DD=0%)
        When: Calculating fitness_score()
        Then: Score near 100
        """
        # Given
        metrics = StrategyMetrics(
            sharpe_ratio=3.0,
            max_drawdown=0.0,
            win_rate=1.0,
            profit_factor=3.0,
            total_return=150.0,
            num_trades=50,
        )

        # When
        score = metrics.get_fitness_score()

        # Then: 30 + 20 + 20 + 30 = 100
        assert score == 100.0

    def test_get_fitness_score_poor_metrics(self):
        """Test: Poor metrics yield low fitness score.

        Given: Strategy with poor metrics (Sharpe=0.5, PF=1.0, WR=40%, DD=30%)
        When: Calculating fitness_score()
        Then: Score < 50
        """
        # Given
        metrics = StrategyMetrics(
            sharpe_ratio=0.5,
            max_drawdown=0.30,
            win_rate=0.40,
            profit_factor=1.0,
        )

        # When
        score = metrics.get_fitness_score()

        # Then: Each component contributes less
        # Sharpe: 0.5/3 * 30 = 5, PF: 1.0/3 * 20 = 6.67, WR: 0.4 * 20 = 8, DD: 0.7 * 30 = 21
        assert score < 50.0
        assert score > 0.0

    def test_get_fitness_score_mixed_metrics(self):
        """Test: Mixed metrics yield medium fitness score.

        Given: Strategy with mixed metrics (some good, some bad)
        When: Calculating fitness_score()
        Then: Score in range 40-70
        """
        # Given
        metrics = StrategyMetrics(
            sharpe_ratio=1.8,  # Good (30% contribution)
            max_drawdown=0.15,  # Good (30% contribution)
            win_rate=0.55,  # OK (20% contribution)
            profit_factor=1.5,  # OK (20% contribution)
        )

        # When
        score = metrics.get_fitness_score()

        # Then
        assert 40.0 < score < 80.0

    def test_is_production_ready_all_criteria_met(self):
        """Test: Strategy meeting all criteria is production-ready.

        Given: Metrics meeting all production thresholds
        When: Calling is_production_ready()
        Then: Returns True
        """
        # Given
        metrics = StrategyMetrics(
            sharpe_ratio=2.0,  # >= 1.5 ✓
            max_drawdown=0.15,  # <= 0.20 ✓
            win_rate=0.60,  # >= 0.50 ✓
            profit_factor=2.0,  # >= 1.5 ✓
            num_trades=50,  # >= 30 ✓
            consecutive_losses=3,  # <= 5 ✓
        )

        # When/Then
        assert metrics.is_production_ready() is True

    def test_is_production_ready_low_sharpe(self):
        """Test: Low Sharpe ratio fails production readiness.

        Given: Sharpe < 1.5 (other metrics pass)
        When: Calling is_production_ready()
        Then: Returns False
        """
        # Given
        metrics = StrategyMetrics(
            sharpe_ratio=1.2,  # < 1.5 ✗
            max_drawdown=0.15,
            win_rate=0.60,
            profit_factor=2.0,
            num_trades=50,
            consecutive_losses=3,
        )

        # When/Then
        assert metrics.is_production_ready() is False

    def test_is_production_ready_high_drawdown(self):
        """Test: High max drawdown fails production readiness.

        Given: Max drawdown > 20%
        When: Calling is_production_ready()
        Then: Returns False
        """
        # Given
        metrics = StrategyMetrics(
            sharpe_ratio=2.0,
            max_drawdown=0.25,  # > 0.20 ✗
            win_rate=0.60,
            profit_factor=2.0,
            num_trades=50,
            consecutive_losses=3,
        )

        # When/Then
        assert metrics.is_production_ready() is False

    def test_is_production_ready_insufficient_trades(self):
        """Test: Insufficient trade count fails production readiness.

        Given: num_trades < 30 (statistical significance threshold)
        When: Calling is_production_ready()
        Then: Returns False
        """
        # Given
        metrics = StrategyMetrics(
            sharpe_ratio=2.0,
            max_drawdown=0.15,
            win_rate=0.60,
            profit_factor=2.0,
            num_trades=25,  # < 30 ✗
            consecutive_losses=3,
        )

        # When/Then
        assert metrics.is_production_ready() is False

    def test_is_production_ready_excessive_consecutive_losses(self):
        """Test: Excessive consecutive losses fails production readiness.

        Given: consecutive_losses > 5
        When: Calling is_production_ready()
        Then: Returns False
        """
        # Given
        metrics = StrategyMetrics(
            sharpe_ratio=2.0,
            max_drawdown=0.15,
            win_rate=0.60,
            profit_factor=2.0,
            num_trades=50,
            consecutive_losses=6,  # > 5 ✗
        )

        # When/Then
        assert metrics.is_production_ready() is False


class TestStrategyGene:
    """Tests for StrategyGene genetic programming representation."""

    def test_complexity_score_simple_tree(self):
        """Test: Simple tree has low complexity penalty.

        Given: Gene with depth=2, num_nodes=5 (simple rule)
        When: Calculating complexity_score()
        Then: Score < 0.3
        """
        # Given
        gene = StrategyGene(
            tree="(> rsi 30)",
            depth=2,
            num_nodes=5,
            features_used={"rsi"},
            constants={"30": 30.0},
        )

        # When
        score = gene.complexity_score()

        # Then: (2/10 + 5/50) / 2 = (0.2 + 0.1) / 2 = 0.15
        assert score == pytest.approx(0.15, rel=0.01)
        assert score < 0.3

    def test_complexity_score_complex_tree(self):
        """Test: Complex tree has high complexity penalty.

        Given: Gene with depth=9, num_nodes=45 (complex rule)
        When: Calculating complexity_score()
        Then: Score > 0.7
        """
        # Given
        gene = StrategyGene(
            tree="(and (> (/ close (sma close 20)) 1.02) (< rsi 70) (> macd 0) ...)",
            depth=9,
            num_nodes=45,
            features_used={"close", "rsi", "macd", "sma"},
            constants={"20": 20.0, "1.02": 1.02, "70": 70.0, "0": 0.0},
        )

        # When
        score = gene.complexity_score()

        # Then: (9/10 + 45/50) / 2 = (0.9 + 0.9) / 2 = 0.9
        assert score == pytest.approx(0.90, rel=0.01)
        assert score > 0.7

    def test_complexity_score_medium_tree(self):
        """Test: Medium complexity tree has moderate penalty.

        Given: Gene with depth=5, num_nodes=20
        When: Calculating complexity_score()
        Then: Score in range 0.3-0.6
        """
        # Given
        gene = StrategyGene(
            tree="(and (> price ema_20) (> macd 0))",
            depth=5,
            num_nodes=20,
            features_used={"price", "ema_20", "macd"},
        )

        # When
        score = gene.complexity_score()

        # Then: (5/10 + 20/50) / 2 = (0.5 + 0.4) / 2 = 0.45
        assert score == pytest.approx(0.45, rel=0.01)
        assert 0.3 < score < 0.6

    def test_gene_features_tracking(self):
        """Test: Gene correctly tracks feature usage.

        Given: Gene using multiple features
        When: Accessing features_used
        Then: Set contains all referenced features
        """
        # Given
        gene = StrategyGene(
            tree="(and (> rsi 50) (< macd 0) (> close sma_20))",
            depth=4,
            num_nodes=12,
            features_used={"rsi", "macd", "close", "sma_20"},
            constants={"50": 50.0, "0": 0.0},
        )

        # When/Then
        assert "rsi" in gene.features_used
        assert "macd" in gene.features_used
        assert "close" in gene.features_used
        assert "sma_20" in gene.features_used
        assert len(gene.features_used) == 4


class TestFeatureSet:
    """Tests for FeatureSet feature vector."""

    def test_feature_set_creation_with_defaults(self):
        """Test: FeatureSet can be created with default values.

        Given: Minimal required fields (timestamp, symbol)
        When: Creating FeatureSet
        Then: Instance created with sensible defaults
        """
        # Given
        timestamp = datetime.now(timezone.utc)

        # When
        features = FeatureSet(timestamp=timestamp, symbol="AAPL")

        # Then: Check defaults
        assert features.symbol == "AAPL"
        assert features.timestamp == timestamp
        assert features.rsi_14 == 50.0  # Neutral RSI
        assert features.price_to_sma20 == 1.0  # Price at SMA
        assert features.volume_ratio == 1.0  # Average volume

    def test_feature_set_with_custom_values(self):
        """Test: FeatureSet accepts custom feature values.

        Given: Complete feature vector data
        When: Creating FeatureSet
        Then: All values correctly assigned
        """
        # Given
        timestamp = datetime.now(timezone.utc)

        # When
        features = FeatureSet(
            timestamp=timestamp,
            symbol="AAPL",
            returns_1d=0.02,
            returns_5d=0.08,
            rsi_14=65.0,
            macd=1.5,
            macd_signal=1.2,
            volume_ratio=1.3,
            price_to_sma20=1.05,
            in_uptrend=1.0,
            bull_flag_score=0.75,
        )

        # Then
        assert features.returns_1d == 0.02
        assert features.returns_5d == 0.08
        assert features.rsi_14 == 65.0
        assert features.macd == 1.5
        assert features.volume_ratio == 1.3
        assert features.bull_flag_score == 0.75


class TestMLStrategy:
    """Tests for MLStrategy main dataclass."""

    def test_ml_strategy_creation(self):
        """Test: MLStrategy can be created with all required fields.

        Given: Complete strategy data
        When: Creating MLStrategy
        Then: Instance created successfully
        """
        # Given
        timestamp = datetime.now(timezone.utc)
        backtest_metrics = StrategyMetrics(sharpe_ratio=2.0, win_rate=0.60)

        # When
        strategy = MLStrategy(
            name="Test GP Strategy",
            type=StrategyType.GENETIC_PROGRAMMING,
            status=StrategyStatus.VALIDATED,
            created_at=timestamp,
            backtest_metrics=backtest_metrics,
        )

        # Then
        assert strategy.name == "Test GP Strategy"
        assert strategy.type == StrategyType.GENETIC_PROGRAMMING
        assert strategy.status == StrategyStatus.VALIDATED
        assert strategy.backtest_metrics.sharpe_ratio == 2.0

    def test_strategy_status_enum_values(self):
        """Test: StrategyStatus enum has expected lifecycle states.

        Given: StrategyStatus enum
        When: Accessing enum values
        Then: All lifecycle states present
        """
        # Given/When/Then
        assert StrategyStatus.GENERATED.value == "generated"
        assert StrategyStatus.BACKTESTING.value == "backtesting"
        assert StrategyStatus.VALIDATED.value == "validated"
        assert StrategyStatus.FORWARD_TESTING.value == "forward_testing"
        assert StrategyStatus.DEPLOYED.value == "deployed"
        assert StrategyStatus.RETIRED.value == "retired"
        assert StrategyStatus.FAILED.value == "failed"

    def test_strategy_type_enum_values(self):
        """Test: StrategyType enum has all generation methods.

        Given: StrategyType enum
        When: Accessing enum values
        Then: All strategy types present
        """
        # Given/When/Then
        assert StrategyType.GENETIC_PROGRAMMING.value == "genetic_programming"
        assert StrategyType.REINFORCEMENT_LEARNING.value == "reinforcement_learning"
        assert StrategyType.LLM_GENERATED.value == "llm_generated"
        assert StrategyType.ENSEMBLE.value == "ensemble"
        assert StrategyType.HYBRID.value == "hybrid"
