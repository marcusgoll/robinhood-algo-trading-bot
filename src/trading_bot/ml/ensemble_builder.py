"""Ensemble Builder

Creates and optimizes ensembles of ML strategies with correlation analysis
and optimal weight allocation.

Usage:
    builder = EnsembleBuilder()

    # Create ensemble from selected strategies
    ensemble = builder.create_ensemble(
        strategies=top_5_strategies,
        method="equal_weight"
    )

    # Optimize weights using historical performance
    optimized = builder.optimize_weights(
        strategies=top_5_strategies,
        historical_data=df,
        method="sharpe_maximization"
    )
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from numpy.typing import NDArray
from scipy.optimize import minimize

from trading_bot.ml.models import FeatureSet, MLStrategy, StrategyEnsemble, StrategyMetrics

logger = logging.getLogger(__name__)


@dataclass
class EnsembleAnalysis:
    """Analysis of ensemble composition.

    Attributes:
        ensemble: The ensemble being analyzed
        correlation_matrix: Pairwise strategy correlation matrix
        avg_correlation: Average pairwise correlation
        diversity_score: Diversity score (0-100, higher = more diverse)
        weight_concentration: How concentrated are weights (0-1, lower = more balanced)
        expected_sharpe: Expected Sharpe ratio
        expected_return: Expected annual return
        expected_drawdown: Expected max drawdown
    """

    ensemble: StrategyEnsemble
    correlation_matrix: NDArray[np.float64]
    avg_correlation: float
    diversity_score: float
    weight_concentration: float
    expected_sharpe: float
    expected_return: float
    expected_drawdown: float


class EnsembleBuilder:
    """Build and optimize strategy ensembles.

    Methods:
    - create_ensemble: Create ensemble with specified weighting method
    - optimize_weights: Find optimal weights using historical data
    - analyze_ensemble: Analyze correlation and diversity
    - backtest_ensemble: Test ensemble performance
    """

    def __init__(self) -> None:
        """Initialize ensemble builder."""
        pass

    def calculate_correlation_matrix(
        self,
        strategies: list[MLStrategy],
    ) -> NDArray[np.float64]:
        """Calculate pairwise correlation matrix for strategies.

        For GP strategies, uses feature overlap and structural similarity.
        For RL strategies, would use signal correlation (not implemented).

        Args:
            strategies: List of strategies

        Returns:
            NxN correlation matrix (0-1)
        """
        n = len(strategies)
        corr_matrix = np.eye(n)  # Diagonal = 1.0 (self-correlation)

        for i in range(n):
            for j in range(i + 1, n):
                # Calculate correlation between strategy i and j
                corr = self._calculate_strategy_correlation(
                    strategies[i], strategies[j]
                )
                corr_matrix[i, j] = corr
                corr_matrix[j, i] = corr

        return corr_matrix

    def _calculate_strategy_correlation(
        self,
        strategy1: MLStrategy,
        strategy2: MLStrategy,
    ) -> float:
        """Calculate correlation between two strategies.

        Args:
            strategy1: First strategy
            strategy2: Second strategy

        Returns:
            Correlation (0-1)
        """
        # Use same logic as StrategySelector
        if not strategy1.gene or not strategy2.gene:
            return 0.5

        features1 = strategy1.gene.features_used
        features2 = strategy2.gene.features_used

        if not features1 or not features2:
            return 0.5

        # Jaccard similarity
        intersection = len(features1 & features2)
        union = len(features1 | features2)
        if union == 0:
            return 0.0

        feature_similarity = intersection / union

        # Structure similarity
        depth_diff = abs(strategy1.gene.depth - strategy2.gene.depth)
        complexity_diff = abs(
            strategy1.gene.complexity_score() - strategy2.gene.complexity_score()
        )

        structure_similarity = 1.0 - min((depth_diff / 10.0 + complexity_diff) / 2.0, 1.0)

        # Combined
        correlation = feature_similarity * 0.6 + structure_similarity * 0.4

        return correlation

    def create_ensemble(
        self,
        strategies: list[MLStrategy],
        method: str = "equal_weight",
        name: str = "Strategy_Ensemble",
    ) -> StrategyEnsemble:
        """Create ensemble with specified weighting method.

        Methods:
        - equal_weight: 1/N for each strategy
        - sharpe_weighted: Weight by Sharpe ratio
        - inverse_variance: Weight by inverse return variance
        - custom: Provide custom weights

        Args:
            strategies: Strategies to include
            method: Weighting method
            name: Ensemble name

        Returns:
            StrategyEnsemble
        """
        if len(strategies) == 0:
            raise ValueError("Cannot create ensemble with no strategies")

        logger.info(f"Creating ensemble with {len(strategies)} strategies using {method}")

        # Calculate weights
        if method == "equal_weight":
            weights = self._equal_weights(strategies)
        elif method == "sharpe_weighted":
            weights = self._sharpe_weights(strategies)
        elif method == "inverse_variance":
            weights = self._inverse_variance_weights(strategies)
        else:
            raise ValueError(f"Unknown weighting method: {method}")

        # Create ensemble
        ensemble = StrategyEnsemble(
            name=name,
            strategies=strategies,
            weights=weights,
            aggregation_method="weighted_avg",
        )

        logger.info(f"Created ensemble: {name}")
        for i, (strat, weight) in enumerate(zip(strategies, weights), 1):
            logger.info(f"  {i}. {strat.name}: {weight:.1%}")

        return ensemble

    def _equal_weights(self, strategies: list[MLStrategy]) -> list[float]:
        """Equal weighting (1/N)."""
        n = len(strategies)
        return [1.0 / n] * n

    def _sharpe_weights(self, strategies: list[MLStrategy]) -> list[float]:
        """Weight by Sharpe ratio."""
        sharpes = []
        for strat in strategies:
            # Use forward_test_metrics if available, else backtest_metrics
            if strat.forward_test_metrics.sharpe_ratio > 0:
                sharpes.append(max(strat.forward_test_metrics.sharpe_ratio, 0.1))
            else:
                sharpes.append(max(strat.backtest_metrics.sharpe_ratio, 0.1))

        sharpes_array = np.array(sharpes)
        weights = sharpes_array / sharpes_array.sum()

        return weights.tolist()

    def _inverse_variance_weights(self, strategies: list[MLStrategy]) -> list[float]:
        """Weight by inverse variance (minimum variance portfolio)."""
        # Estimate variance from max drawdown
        # Higher drawdown = higher variance = lower weight
        variances = []

        for strat in strategies:
            if strat.forward_test_metrics.max_drawdown > 0:
                dd = strat.forward_test_metrics.max_drawdown
            else:
                dd = strat.backtest_metrics.max_drawdown

            # Convert drawdown to variance estimate
            variance = max(dd, 0.01)  # Minimum variance
            variances.append(variance)

        variances_array = np.array(variances)
        inv_variances = 1.0 / variances_array
        weights = inv_variances / inv_variances.sum()

        return weights.tolist()

    def optimize_weights(
        self,
        strategies: list[MLStrategy],
        historical_data: pd.DataFrame,
        method: str = "sharpe_maximization",
        constraints: dict[str, Any] | None = None,
    ) -> tuple[list[float], StrategyMetrics]:
        """Optimize ensemble weights using historical data.

        Methods:
        - sharpe_maximization: Maximize Sharpe ratio
        - min_variance: Minimize portfolio variance
        - max_return: Maximize returns (subject to constraints)

        Args:
            strategies: Strategies to optimize
            historical_data: Historical OHLCV data
            method: Optimization method
            constraints: Optional constraints (min_weight, max_weight, min_sharpe)

        Returns:
            Tuple of (optimal_weights, ensemble_metrics)
        """
        if len(strategies) == 0:
            raise ValueError("Cannot optimize with no strategies")

        logger.info(f"Optimizing weights for {len(strategies)} strategies using {method}")

        # TODO: Implement actual optimization using scipy.optimize
        # For now, use Sharpe weighting as fallback
        logger.warning("Weight optimization not fully implemented, using Sharpe weighting")

        weights = self._sharpe_weights(strategies)

        # Calculate expected metrics
        expected_sharpe = 0.0
        expected_return = 0.0
        expected_dd = 0.0

        for strat, weight in zip(strategies, weights):
            metrics = strat.backtest_metrics
            expected_sharpe += metrics.sharpe_ratio * weight
            expected_return += metrics.total_return * weight
            expected_dd = max(expected_dd, metrics.max_drawdown)  # Use max DD

        ensemble_metrics = StrategyMetrics(
            sharpe_ratio=expected_sharpe,
            total_return=expected_return,
            max_drawdown=expected_dd,
            num_trades=sum(s.backtest_metrics.num_trades for s in strategies),
        )

        logger.info(f"Optimized weights: Expected Sharpe={expected_sharpe:.2f}")

        return weights, ensemble_metrics

    def analyze_ensemble(
        self,
        ensemble: StrategyEnsemble,
    ) -> EnsembleAnalysis:
        """Analyze ensemble composition and diversity.

        Args:
            ensemble: Ensemble to analyze

        Returns:
            EnsembleAnalysis with correlation and diversity metrics
        """
        logger.info(f"Analyzing ensemble: {ensemble.name}")

        # Calculate correlation matrix
        corr_matrix = self.calculate_correlation_matrix(ensemble.strategies)

        # Average pairwise correlation (exclude diagonal)
        n = len(ensemble.strategies)
        if n > 1:
            triu_indices = np.triu_indices(n, k=1)
            avg_correlation = corr_matrix[triu_indices].mean()
        else:
            avg_correlation = 0.0

        # Diversity score (inverse of correlation)
        diversity_score = (1.0 - avg_correlation) * 100

        # Weight concentration (Herfindahl index)
        weights_array = np.array(ensemble.weights)
        weight_concentration = (weights_array ** 2).sum()

        # Expected performance (weighted average)
        expected_sharpe = 0.0
        expected_return = 0.0
        expected_dd = 0.0

        for strat, weight in zip(ensemble.strategies, ensemble.weights):
            metrics = strat.backtest_metrics
            expected_sharpe += metrics.sharpe_ratio * weight
            expected_return += metrics.total_return * weight
            expected_dd = max(expected_dd, metrics.max_drawdown)

        analysis = EnsembleAnalysis(
            ensemble=ensemble,
            correlation_matrix=corr_matrix,
            avg_correlation=avg_correlation,
            diversity_score=diversity_score,
            weight_concentration=weight_concentration,
            expected_sharpe=expected_sharpe,
            expected_return=expected_return,
            expected_drawdown=expected_dd,
        )

        logger.info(f"  Avg correlation: {avg_correlation:.2f}")
        logger.info(f"  Diversity score: {diversity_score:.1f}/100")
        logger.info(f"  Weight concentration: {weight_concentration:.2f}")
        logger.info(f"  Expected Sharpe: {expected_sharpe:.2f}")

        return analysis

    def generate_report(
        self,
        analysis: EnsembleAnalysis,
    ) -> str:
        """Generate human-readable ensemble report.

        Args:
            analysis: Ensemble analysis

        Returns:
            Markdown-formatted report
        """
        ensemble = analysis.ensemble
        report = []

        report.append(f"# Ensemble Analysis Report: {ensemble.name}\n")
        report.append(f"**Created:** {ensemble.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        report.append(f"**Number of strategies:** {len(ensemble.strategies)}")
        report.append(f"**Aggregation method:** {ensemble.aggregation_method}\n")

        # Diversity metrics
        report.append("## Diversity Metrics\n")
        report.append(f"- **Average correlation:** {analysis.avg_correlation:.2f}")
        report.append(f"- **Diversity score:** {analysis.diversity_score:.1f}/100")
        report.append(f"- **Weight concentration:** {analysis.weight_concentration:.2f} (lower = more balanced)\n")

        # Expected performance
        report.append("## Expected Performance\n")
        report.append(f"- **Expected Sharpe:** {analysis.expected_sharpe:.2f}")
        report.append(f"- **Expected return:** {analysis.expected_return:.1%}")
        report.append(f"- **Expected max drawdown:** {analysis.expected_drawdown:.1%}\n")

        # Component strategies
        report.append("## Component Strategies\n")
        report.append("| # | Strategy | Weight | Sharpe | Max DD | Win Rate |")
        report.append("|---|----------|--------|--------|--------|----------|")

        for i, (strat, weight) in enumerate(zip(ensemble.strategies, ensemble.weights), 1):
            metrics = strat.backtest_metrics
            report.append(
                f"| {i} | {strat.name} | {weight:.1%} | "
                f"{metrics.sharpe_ratio:.2f} | {metrics.max_drawdown:.1%} | "
                f"{metrics.win_rate:.1%} |"
            )

        report.append("")

        # Correlation matrix
        report.append("## Correlation Matrix\n")
        report.append("Strategy pairwise correlations:\n")
        report.append("```")

        # Header
        header = "     " + " ".join([f"S{i:2d}" for i in range(1, len(ensemble.strategies) + 1)])
        report.append(header)

        # Rows
        for i, row in enumerate(analysis.correlation_matrix):
            row_str = f"S{i+1:2d}  " + " ".join([f"{val:4.2f}" for val in row])
            report.append(row_str)

        report.append("```\n")

        # Recommendations
        report.append("## Recommendations\n")

        if analysis.diversity_score >= 70:
            report.append("✓ Excellent diversity - strategies are well-differentiated")
        elif analysis.diversity_score >= 50:
            report.append("✓ Good diversity - acceptable for ensemble")
        else:
            report.append("⚠️ Low diversity - strategies may be too similar")

        if analysis.weight_concentration <= 0.3:
            report.append("✓ Well-balanced weights across strategies")
        elif analysis.weight_concentration <= 0.5:
            report.append("✓ Moderately balanced weights")
        else:
            report.append("⚠️ Highly concentrated weights - ensemble dominated by few strategies")

        if analysis.expected_sharpe >= 2.0:
            report.append("✓ Strong expected risk-adjusted returns")
        elif analysis.expected_sharpe >= 1.5:
            report.append("✓ Acceptable expected risk-adjusted returns")
        else:
            report.append("⚠️ Low expected Sharpe ratio - consider improving component strategies")

        report.append("")

        return "\n".join(report)


def create_ensemble_from_selection(
    selected_strategies: list[MLStrategy],
    weighting_method: str = "sharpe_weighted",
    ensemble_name: str = "ML_Ensemble_v1",
) -> tuple[StrategyEnsemble, EnsembleAnalysis]:
    """Convenience function to create and analyze ensemble.

    Args:
        selected_strategies: Pre-selected strategies
        weighting_method: Weighting method
        ensemble_name: Name for ensemble

    Returns:
        Tuple of (ensemble, analysis)
    """
    builder = EnsembleBuilder()

    # Create ensemble
    ensemble = builder.create_ensemble(
        strategies=selected_strategies,
        method=weighting_method,
        name=ensemble_name,
    )

    # Analyze
    analysis = builder.analyze_ensemble(ensemble)

    return ensemble, analysis
