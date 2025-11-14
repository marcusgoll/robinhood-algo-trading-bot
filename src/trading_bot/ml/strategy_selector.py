"""Strategy Selection and Ranking System

Evaluates ML strategies across multiple criteria and selects the best candidates
for deployment or ensemble creation.

Usage:
    selector = StrategySelector()

    # Rank all strategies
    ranked = selector.rank_strategies(all_strategies, validation_results)

    # Select top N strategies
    top_5 = selector.select_top_n(ranked, n=5)

    # Select diverse strategies for ensemble
    ensemble_set = selector.select_for_ensemble(ranked, n=5, diversity_threshold=0.3)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from trading_bot.ml.backtesting.validator import ValidationResult
from trading_bot.ml.models import MLStrategy, StrategyMetrics

logger = logging.getLogger(__name__)


@dataclass
class StrategyScore:
    """Multi-dimensional score for a strategy.

    Attributes:
        strategy: The evaluated strategy
        validation_result: Walk-forward validation result
        composite_score: Overall score (0-100)
        performance_score: Performance metrics score (0-100)
        robustness_score: Out-of-sample consistency score (0-100)
        simplicity_score: Complexity penalty score (0-100)
        diversity_score: Diversity from other strategies (0-100)
        rank: Final rank (1 = best)
        percentile: Percentile ranking (0-100)
    """

    strategy: MLStrategy
    validation_result: ValidationResult | None = None

    # Component scores
    composite_score: float = 0.0
    performance_score: float = 0.0
    robustness_score: float = 0.0
    simplicity_score: float = 0.0
    diversity_score: float = 0.0

    # Rankings
    rank: int = 0
    percentile: float = 0.0

    # Reasons
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class StrategySelector:
    """Strategy selection and ranking system.

    Evaluates strategies across multiple dimensions:
    1. Performance: Sharpe, returns, win rate
    2. Robustness: Walk-forward consistency, low overfitting
    3. Simplicity: Low complexity, interpretable rules
    4. Diversity: Low correlation with other strategies

    Weights (configurable):
    - Performance: 40%
    - Robustness: 40%
    - Simplicity: 20%
    """

    def __init__(
        self,
        performance_weight: float = 0.40,
        robustness_weight: float = 0.40,
        simplicity_weight: float = 0.20,
        diversity_weight: float = 0.0,  # Only used for ensemble selection
    ) -> None:
        """Initialize selector with scoring weights.

        Args:
            performance_weight: Weight for performance metrics (0-1)
            robustness_weight: Weight for walk-forward robustness (0-1)
            simplicity_weight: Weight for simplicity/complexity (0-1)
            diversity_weight: Weight for diversity (0-1, used in ensemble selection)
        """
        self.performance_weight = performance_weight
        self.robustness_weight = robustness_weight
        self.simplicity_weight = simplicity_weight
        self.diversity_weight = diversity_weight

        # Normalize weights (excluding diversity for now)
        total = performance_weight + robustness_weight + simplicity_weight
        self.performance_weight /= total
        self.robustness_weight /= total
        self.simplicity_weight /= total

    def calculate_performance_score(
        self,
        strategy: MLStrategy,
        validation_result: ValidationResult | None,
    ) -> tuple[float, list[str], list[str]]:
        """Calculate performance score (0-100).

        Components:
        - Sharpe ratio: 35%
        - Total return: 25%
        - Win rate: 20%
        - Profit factor: 20%

        Args:
            strategy: Strategy to evaluate
            validation_result: Validation results

        Returns:
            Tuple of (score, strengths, weaknesses)
        """
        strengths = []
        weaknesses = []

        # Use walk-forward test metrics if available, else backtest metrics
        if validation_result and validation_result.walk_forward_result:
            metrics = validation_result.walk_forward_result.windows[-1].test_metrics
        else:
            metrics = strategy.backtest_metrics

        # Sharpe ratio (35%)
        sharpe_target = 2.0
        sharpe_component = min(metrics.sharpe_ratio / sharpe_target, 1.0) * 35

        if metrics.sharpe_ratio >= 2.0:
            strengths.append(f"Excellent Sharpe ratio: {metrics.sharpe_ratio:.2f}")
        elif metrics.sharpe_ratio < 1.0:
            weaknesses.append(f"Low Sharpe ratio: {metrics.sharpe_ratio:.2f}")

        # Total return (25%)
        return_target = 0.50  # 50% return target
        return_component = min(metrics.total_return / return_target, 1.0) * 25

        if metrics.total_return >= 0.50:
            strengths.append(f"Strong returns: {metrics.total_return:.1%}")
        elif metrics.total_return < 0.10:
            weaknesses.append(f"Low returns: {metrics.total_return:.1%}")

        # Win rate (20%)
        win_rate_component = metrics.win_rate * 20

        if metrics.win_rate >= 0.60:
            strengths.append(f"High win rate: {metrics.win_rate:.1%}")
        elif metrics.win_rate < 0.45:
            weaknesses.append(f"Low win rate: {metrics.win_rate:.1%}")

        # Profit factor (20%)
        pf_target = 2.0
        pf_component = min(metrics.profit_factor / pf_target, 1.0) * 20

        if metrics.profit_factor >= 2.0:
            strengths.append(f"Excellent profit factor: {metrics.profit_factor:.2f}")
        elif metrics.profit_factor < 1.2:
            weaknesses.append(f"Low profit factor: {metrics.profit_factor:.2f}")

        score = sharpe_component + return_component + win_rate_component + pf_component
        return score, strengths, weaknesses

    def calculate_robustness_score(
        self,
        strategy: MLStrategy,
        validation_result: ValidationResult | None,
    ) -> tuple[float, list[str], list[str]]:
        """Calculate robustness score (0-100).

        Measures out-of-sample consistency:
        - Low train/test degradation: 40%
        - Not overfit: 30%
        - Consistent across windows: 30%

        Args:
            strategy: Strategy to evaluate
            validation_result: Validation results

        Returns:
            Tuple of (score, strengths, weaknesses)
        """
        strengths = []
        weaknesses = []

        if not validation_result or not validation_result.walk_forward_result:
            # No walk-forward data = cannot assess robustness
            weaknesses.append("No walk-forward validation data")
            return 0.0, strengths, weaknesses

        wf_result = validation_result.walk_forward_result

        # Degradation score (40%)
        # Lower degradation = higher score
        max_acceptable_degradation = 50.0  # 50% degradation is maximum
        degradation_pct = abs(wf_result.avg_degradation_pct)
        degradation_component = max(40 - (degradation_pct / max_acceptable_degradation * 40), 0)

        if degradation_pct <= 20.0:
            strengths.append(f"Low performance degradation: {degradation_pct:.1f}%")
        elif degradation_pct >= 50.0:
            weaknesses.append(f"High performance degradation: {degradation_pct:.1f}%")

        # Overfit penalty (30%)
        overfit_component = 0.0 if wf_result.is_overfit else 30.0

        if not wf_result.is_overfit:
            strengths.append("Not overfit to training data")
        else:
            weaknesses.append("Shows signs of overfitting")

        # Consistency across windows (30%)
        consistency_score = wf_result.get_consistency_score()
        consistency_component = (consistency_score / 100) * 30

        if consistency_score >= 70:
            strengths.append(f"Highly consistent performance: {consistency_score:.1f}")
        elif consistency_score < 40:
            weaknesses.append(f"Inconsistent performance: {consistency_score:.1f}")

        score = degradation_component + overfit_component + consistency_component
        return score, strengths, weaknesses

    def calculate_simplicity_score(
        self,
        strategy: MLStrategy,
    ) -> tuple[float, list[str], list[str]]:
        """Calculate simplicity score (0-100).

        Simpler strategies are preferred:
        - Low complexity penalty
        - Fewer parameters
        - More interpretable

        Args:
            strategy: Strategy to evaluate

        Returns:
            Tuple of (score, strengths, weaknesses)
        """
        strengths = []
        weaknesses = []

        # Gene complexity (if GP strategy)
        if strategy.gene:
            complexity = strategy.gene.complexity_score()

            # Invert complexity to get simplicity (high complexity = low simplicity)
            complexity_component = (1.0 - complexity) * 60

            if complexity <= 0.3:
                strengths.append(f"Simple, interpretable rule: complexity={complexity:.2f}")
            elif complexity >= 0.7:
                weaknesses.append(f"Complex rule: complexity={complexity:.2f}")
        else:
            # No gene data = assume moderate complexity
            complexity_component = 40.0

        # Number of trades (40%)
        # Prefer strategies with moderate trade frequency
        # Too few = unreliable, too many = overtrading
        num_trades = strategy.backtest_metrics.num_trades

        if 30 <= num_trades <= 100:
            trade_component = 40.0
            strengths.append(f"Optimal trade frequency: {num_trades} trades")
        elif num_trades < 10:
            trade_component = 10.0
            weaknesses.append(f"Too few trades: {num_trades}")
        elif num_trades > 200:
            trade_component = 20.0
            weaknesses.append(f"High trade frequency: {num_trades}")
        else:
            trade_component = 30.0

        score = complexity_component + trade_component
        return score, strengths, weaknesses

    def calculate_composite_score(
        self,
        performance: float,
        robustness: float,
        simplicity: float,
        diversity: float = 0.0,
    ) -> float:
        """Calculate weighted composite score.

        Args:
            performance: Performance score (0-100)
            robustness: Robustness score (0-100)
            simplicity: Simplicity score (0-100)
            diversity: Diversity score (0-100, optional)

        Returns:
            Composite score (0-100)
        """
        if self.diversity_weight > 0:
            # Renormalize with diversity
            total_weight = (
                self.performance_weight
                + self.robustness_weight
                + self.simplicity_weight
                + self.diversity_weight
            )

            score = (
                performance * (self.performance_weight / total_weight)
                + robustness * (self.robustness_weight / total_weight)
                + simplicity * (self.simplicity_weight / total_weight)
                + diversity * (self.diversity_weight / total_weight)
            )
        else:
            score = (
                performance * self.performance_weight
                + robustness * self.robustness_weight
                + simplicity * self.simplicity_weight
            )

        return score

    def score_strategy(
        self,
        strategy: MLStrategy,
        validation_result: ValidationResult | None = None,
    ) -> StrategyScore:
        """Calculate comprehensive score for a strategy.

        Args:
            strategy: Strategy to score
            validation_result: Optional validation results

        Returns:
            StrategyScore with all components
        """
        # Calculate component scores
        perf_score, perf_strengths, perf_weaknesses = self.calculate_performance_score(
            strategy, validation_result
        )

        robust_score, robust_strengths, robust_weaknesses = self.calculate_robustness_score(
            strategy, validation_result
        )

        simple_score, simple_strengths, simple_weaknesses = self.calculate_simplicity_score(
            strategy
        )

        # Composite score
        composite = self.calculate_composite_score(
            perf_score, robust_score, simple_score
        )

        # Aggregate strengths/weaknesses
        strengths = perf_strengths + robust_strengths + simple_strengths
        weaknesses = perf_weaknesses + robust_weaknesses + simple_weaknesses

        # Warnings
        warnings = []
        if validation_result and not validation_result.passed:
            warnings.append(f"Failed validation: {', '.join(validation_result.failure_reasons)}")

        return StrategyScore(
            strategy=strategy,
            validation_result=validation_result,
            composite_score=composite,
            performance_score=perf_score,
            robustness_score=robust_score,
            simplicity_score=simple_score,
            diversity_score=0.0,  # Calculated later if needed
            strengths=strengths,
            weaknesses=weaknesses,
            warnings=warnings,
        )

    def rank_strategies(
        self,
        strategies: list[MLStrategy],
        validation_results: dict[str, ValidationResult] | None = None,
    ) -> list[StrategyScore]:
        """Rank strategies by composite score.

        Args:
            strategies: List of strategies to rank
            validation_results: Optional dict mapping strategy.id to ValidationResult

        Returns:
            List of StrategyScore, sorted by rank (best first)
        """
        if not strategies:
            logger.warning("No strategies to rank")
            return []

        logger.info(f"Ranking {len(strategies)} strategies...")

        # Score all strategies
        scores = []
        for strategy in strategies:
            validation_result = None
            if validation_results:
                validation_result = validation_results.get(str(strategy.id))

            score = self.score_strategy(strategy, validation_result)
            scores.append(score)

        # Sort by composite score (descending)
        scores.sort(key=lambda x: x.composite_score, reverse=True)

        # Assign ranks and percentiles
        for i, score in enumerate(scores, 1):
            score.rank = i
            score.percentile = ((len(scores) - i) / len(scores)) * 100

        logger.info(
            f"Ranked strategies: "
            f"Best={scores[0].composite_score:.1f}, "
            f"Worst={scores[-1].composite_score:.1f}, "
            f"Avg={np.mean([s.composite_score for s in scores]):.1f}"
        )

        return scores

    def select_top_n(
        self,
        ranked_scores: list[StrategyScore],
        n: int = 5,
        min_score: float = 50.0,
    ) -> list[StrategyScore]:
        """Select top N strategies.

        Args:
            ranked_scores: Ranked strategy scores
            n: Number to select
            min_score: Minimum composite score threshold

        Returns:
            Top N strategies that meet minimum score
        """
        # Filter by minimum score
        qualified = [s for s in ranked_scores if s.composite_score >= min_score]

        # Take top N
        selected = qualified[:n]

        logger.info(
            f"Selected {len(selected)}/{len(ranked_scores)} strategies "
            f"(top {n}, min_score={min_score:.1f})"
        )

        return selected

    def calculate_strategy_correlation(
        self,
        strategy1: MLStrategy,
        strategy2: MLStrategy,
    ) -> float:
        """Calculate correlation between two strategies.

        For GP strategies, compares tree structure and features used.
        Returns correlation estimate (0-1): 0=independent, 1=identical

        Args:
            strategy1: First strategy
            strategy2: Second strategy

        Returns:
            Correlation estimate (0-1)
        """
        # For now, use simple heuristics based on gene similarity
        if not strategy1.gene or not strategy2.gene:
            # Can't compare without gene data
            return 0.5  # Assume moderate correlation

        # Compare features used
        features1 = strategy1.gene.features_used
        features2 = strategy2.gene.features_used

        if not features1 or not features2:
            # No feature data
            return 0.5

        # Jaccard similarity of features
        intersection = len(features1 & features2)
        union = len(features1 | features2)

        if union == 0:
            return 0.0

        feature_similarity = intersection / union

        # Compare tree depth and complexity
        depth_diff = abs(strategy1.gene.depth - strategy2.gene.depth)
        complexity_diff = abs(
            strategy1.gene.complexity_score() - strategy2.gene.complexity_score()
        )

        # Higher depth/complexity difference = lower correlation
        structure_similarity = 1.0 - min((depth_diff / 10.0 + complexity_diff) / 2.0, 1.0)

        # Combined correlation estimate
        correlation = (feature_similarity * 0.6 + structure_similarity * 0.4)

        return correlation

    def select_for_ensemble(
        self,
        ranked_scores: list[StrategyScore],
        n: int = 5,
        min_score: float = 50.0,
        diversity_threshold: float = 0.5,
    ) -> list[StrategyScore]:
        """Select diverse strategies for ensemble.

        Uses greedy selection to maximize diversity while maintaining quality:
        1. Select best strategy
        2. Iteratively add strategies that are least correlated with selected set
        3. Stop when N strategies selected or diversity threshold not met

        Args:
            ranked_scores: Ranked strategy scores
            n: Number to select
            min_score: Minimum composite score
            diversity_threshold: Maximum average correlation allowed (0-1)

        Returns:
            Selected diverse strategies
        """
        # Filter by minimum score
        qualified = [s for s in ranked_scores if s.composite_score >= min_score]

        if len(qualified) == 0:
            logger.warning("No strategies meet minimum score threshold")
            return []

        if len(qualified) <= n:
            logger.info(f"Only {len(qualified)} qualified strategies, selecting all")
            return qualified

        # Greedy diversity selection
        selected = [qualified[0]]  # Start with best strategy

        logger.info(f"Starting ensemble selection: {qualified[0].strategy.name} (score={qualified[0].composite_score:.1f})")

        while len(selected) < n:
            best_candidate = None
            best_diversity = -1.0

            for candidate in qualified:
                if candidate in selected:
                    continue

                # Calculate average correlation with selected set
                correlations = []
                for selected_score in selected:
                    corr = self.calculate_strategy_correlation(
                        candidate.strategy,
                        selected_score.strategy
                    )
                    correlations.append(corr)

                avg_correlation = np.mean(correlations)
                diversity = 1.0 - avg_correlation

                # Select candidate with highest diversity
                if diversity > best_diversity:
                    best_diversity = diversity
                    best_candidate = candidate

            if best_candidate is None:
                break

            # Check diversity threshold
            if best_diversity < (1.0 - diversity_threshold):
                logger.warning(
                    f"Cannot add more strategies: diversity={best_diversity:.2f} "
                    f"below threshold={1.0 - diversity_threshold:.2f}"
                )
                break

            selected.append(best_candidate)
            logger.info(
                f"  Added {best_candidate.strategy.name}: "
                f"score={best_candidate.composite_score:.1f}, "
                f"diversity={best_diversity:.2f}"
            )

        logger.info(f"Selected {len(selected)} diverse strategies for ensemble")

        return selected

    def generate_report(
        self,
        ranked_scores: list[StrategyScore],
        top_n: int = 10,
    ) -> str:
        """Generate human-readable ranking report.

        Args:
            ranked_scores: Ranked strategy scores
            top_n: Number of top strategies to include in detail

        Returns:
            Markdown-formatted report
        """
        report = []
        report.append("# Strategy Ranking Report\n")
        report.append(f"Total strategies evaluated: {len(ranked_scores)}\n")

        if not ranked_scores:
            report.append("No strategies to rank.\n")
            return "\n".join(report)

        # Summary statistics
        scores = [s.composite_score for s in ranked_scores]
        report.append("## Summary Statistics\n")
        report.append(f"- Best score: {max(scores):.1f}")
        report.append(f"- Worst score: {min(scores):.1f}")
        report.append(f"- Average score: {np.mean(scores):.1f}")
        report.append(f"- Median score: {np.median(scores):.1f}\n")

        # Top N strategies
        report.append(f"## Top {top_n} Strategies\n")

        for i, score in enumerate(ranked_scores[:top_n], 1):
            report.append(f"### {i}. {score.strategy.name}")
            report.append(f"**Composite Score:** {score.composite_score:.1f}/100 (Rank {score.rank}, {score.percentile:.0f}th percentile)\n")

            report.append("**Component Scores:**")
            report.append(f"- Performance: {score.performance_score:.1f}/100")
            report.append(f"- Robustness: {score.robustness_score:.1f}/100")
            report.append(f"- Simplicity: {score.simplicity_score:.1f}/100\n")

            if score.strengths:
                report.append("**Strengths:**")
                for strength in score.strengths:
                    report.append(f"- {strength}")
                report.append("")

            if score.weaknesses:
                report.append("**Weaknesses:**")
                for weakness in score.weaknesses:
                    report.append(f"- {weakness}")
                report.append("")

            if score.warnings:
                report.append("**Warnings:**")
                for warning in score.warnings:
                    report.append(f"- ⚠️ {warning}")
                report.append("")

            report.append("---\n")

        return "\n".join(report)
