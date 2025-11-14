"""Strategy selection algorithms."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

from trading_bot.ml.config import SelectionConfig
from trading_bot.ml.models import MLStrategy, StrategyMetrics

logger = logging.getLogger(__name__)


@dataclass
class SelectionResult:
    """Result of strategy selection.

    Attributes:
        selected_strategies: Strategies that passed selection
        rejected_strategies: Strategies that were rejected
        selection_method: Method used for selection
        selection_scores: Score for each selected strategy
    """

    selected_strategies: list[MLStrategy]
    rejected_strategies: list[MLStrategy]
    selection_method: str
    selection_scores: dict[str, float]  # strategy_id -> score


class StrategySelector:
    """Select best strategies from a pool using various methods.

    Selection methods:
    - top_n: Select top N by fitness score
    - threshold: Select all above fitness threshold
    - pareto: Pareto frontier (multi-objective optimization)
    - diversity: Maximize diversity while maintaining quality

    Considerations:
    - Performance metrics (Sharpe, profit factor, etc.)
    - Diversity (low correlation between strategies)
    - Complexity (penalize overly complex strategies)

    Usage:
        ```python
        selector = StrategySelector(config)
        result = selector.select(strategies, correlation_matrix)
        ```
    """

    def __init__(self, config: SelectionConfig) -> None:
        """Initialize selector.

        Args:
            config: Selection configuration
        """
        self.config = config

    def calculate_correlation_matrix(
        self, strategies: list[MLStrategy], returns_data: dict[str, list[float]]
    ) -> np.ndarray:
        """Calculate pairwise correlation matrix.

        Args:
            strategies: List of strategies
            returns_data: Dict mapping strategy_id -> list of returns

        Returns:
            NxN correlation matrix
        """
        n = len(strategies)
        corr_matrix = np.eye(n)  # Identity matrix

        for i in range(n):
            for j in range(i + 1, n):
                id_i = str(strategies[i].id)
                id_j = str(strategies[j].id)

                returns_i = returns_data.get(id_i, [])
                returns_j = returns_data.get(id_j, [])

                if len(returns_i) > 0 and len(returns_j) > 0:
                    correlation = np.corrcoef(returns_i, returns_j)[0, 1]
                    corr_matrix[i, j] = correlation
                    corr_matrix[j, i] = correlation

        return corr_matrix

    def select_top_n(self, strategies: list[MLStrategy]) -> list[MLStrategy]:
        """Select top N strategies by overall score.

        Args:
            strategies: Pool of strategies

        Returns:
            Top N strategies
        """
        # Sort by overall score
        sorted_strategies = sorted(
            strategies,
            key=lambda s: s.get_overall_score(),
            reverse=True,
        )

        # Take top N
        selected = sorted_strategies[: self.config.num_strategies_to_select]

        scores = [f"{s.get_overall_score():.1f}" for s in selected[:5]]
        logger.info(
            f"Selected top {len(selected)} strategies "
            f"(scores: {scores}...)"
        )

        return selected

    def select_by_threshold(self, strategies: list[MLStrategy]) -> list[MLStrategy]:
        """Select all strategies above fitness threshold.

        Args:
            strategies: Pool of strategies

        Returns:
            Strategies passing threshold
        """
        selected = [
            s
            for s in strategies
            if s.get_overall_score() >= self.config.min_fitness_threshold
        ]

        logger.info(
            f"Selected {len(selected)} strategies above threshold "
            f"{self.config.min_fitness_threshold}"
        )

        return selected

    def select_pareto_frontier(
        self, strategies: list[MLStrategy]
    ) -> list[MLStrategy]:
        """Select Pareto-optimal strategies.

        A strategy is Pareto-optimal if no other strategy is better
        on ALL objectives simultaneously.

        Objectives:
        - Maximize Sharpe ratio
        - Minimize max drawdown
        - Minimize complexity

        Args:
            strategies: Pool of strategies

        Returns:
            Pareto-optimal strategies
        """
        pareto_front = []

        for candidate in strategies:
            is_dominated = False

            # Extract objectives
            candidate_sharpe = candidate.forward_test_metrics.sharpe_ratio
            candidate_dd = candidate.forward_test_metrics.max_drawdown
            candidate_complexity = candidate.complexity_score

            for other in strategies:
                if candidate.id == other.id:
                    continue

                other_sharpe = other.forward_test_metrics.sharpe_ratio
                other_dd = other.forward_test_metrics.max_drawdown
                other_complexity = other.complexity_score

                # Check if 'other' dominates 'candidate'
                # (better on all objectives)
                if (
                    other_sharpe >= candidate_sharpe
                    and other_dd <= candidate_dd
                    and other_complexity <= candidate_complexity
                ):
                    # Check strict inequality (at least one better)
                    if (
                        other_sharpe > candidate_sharpe
                        or other_dd < candidate_dd
                        or other_complexity < candidate_complexity
                    ):
                        is_dominated = True
                        break

            if not is_dominated:
                pareto_front.append(candidate)

        logger.info(f"Selected {len(pareto_front)} Pareto-optimal strategies")

        # If Pareto front too large, take top N by overall score
        if len(pareto_front) > self.config.num_strategies_to_select:
            pareto_front = sorted(
                pareto_front,
                key=lambda s: s.get_overall_score(),
                reverse=True,
            )[: self.config.num_strategies_to_select]

        return pareto_front

    def select_diverse(
        self,
        strategies: list[MLStrategy],
        correlation_matrix: np.ndarray | None = None,
    ) -> list[MLStrategy]:
        """Select diverse strategies with low correlation.

        Greedy algorithm:
        1. Start with best strategy
        2. Iteratively add strategy with lowest avg correlation to selected
        3. Repeat until N strategies selected

        Args:
            strategies: Pool of strategies
            correlation_matrix: Pairwise correlations (optional)

        Returns:
            Diverse strategy set
        """
        if len(strategies) <= self.config.num_strategies_to_select:
            return strategies

        # Sort by score
        sorted_strategies = sorted(
            strategies,
            key=lambda s: s.get_overall_score(),
            reverse=True,
        )

        # Start with best strategy
        selected = [sorted_strategies[0]]
        remaining = sorted_strategies[1:]

        # Greedy selection
        while len(selected) < self.config.num_strategies_to_select and remaining:
            best_candidate = None
            lowest_avg_corr = float("inf")

            for candidate in remaining:
                if correlation_matrix is not None:
                    # Calculate avg correlation with selected strategies
                    candidate_idx = strategies.index(candidate)
                    selected_indices = [strategies.index(s) for s in selected]

                    avg_corr = np.mean(
                        [
                            abs(correlation_matrix[candidate_idx, idx])
                            for idx in selected_indices
                        ]
                    )
                else:
                    # No correlation data - use random
                    avg_corr = np.random.random()

                # Balance quality and diversity
                quality_score = candidate.get_overall_score() / 100.0  # Normalize
                diversity_score = 1.0 - avg_corr

                combined_score = (
                    quality_score * (1 - self.config.diversity_weight)
                    + diversity_score * self.config.diversity_weight
                )

                if avg_corr < lowest_avg_corr:
                    lowest_avg_corr = avg_corr
                    best_candidate = candidate

            if best_candidate:
                selected.append(best_candidate)
                remaining.remove(best_candidate)

        logger.info(
            f"Selected {len(selected)} diverse strategies "
            f"(diversity weight={self.config.diversity_weight})"
        )

        return selected

    def select(
        self,
        strategies: list[MLStrategy],
        correlation_matrix: np.ndarray | None = None,
    ) -> SelectionResult:
        """Select best strategies using configured method.

        Args:
            strategies: Pool of validated strategies
            correlation_matrix: Optional correlation matrix

        Returns:
            Selection result with selected and rejected strategies
        """
        logger.info(
            f"Selecting strategies using method: {self.config.selection_method}"
        )

        # Apply selection method
        if self.config.selection_method == "top_n":
            selected = self.select_top_n(strategies)
        elif self.config.selection_method == "threshold":
            selected = self.select_by_threshold(strategies)
        elif self.config.selection_method == "pareto":
            selected = self.select_pareto_frontier(strategies)
        elif self.config.selection_method == "diversity":
            selected = self.select_diverse(strategies, correlation_matrix)
        else:
            logger.warning(
                f"Unknown selection method: {self.config.selection_method}, "
                f"defaulting to top_n"
            )
            selected = self.select_top_n(strategies)

        # Filter by max correlation if specified
        if correlation_matrix is not None and self.config.max_correlation < 1.0:
            selected = self._filter_by_correlation(selected, correlation_matrix)

        # Create rejected list
        rejected = [s for s in strategies if s not in selected]

        # Calculate selection scores
        selection_scores = {
            str(s.id): s.get_overall_score() for s in selected
        }

        result = SelectionResult(
            selected_strategies=selected,
            rejected_strategies=rejected,
            selection_method=self.config.selection_method,
            selection_scores=selection_scores,
        )

        logger.info(
            f"Selection complete: {len(selected)} selected, {len(rejected)} rejected"
        )

        return result

    def _filter_by_correlation(
        self,
        strategies: list[MLStrategy],
        correlation_matrix: np.ndarray,
    ) -> list[MLStrategy]:
        """Remove highly correlated strategies.

        Args:
            strategies: Strategy list
            correlation_matrix: Full correlation matrix

        Returns:
            Filtered strategy list
        """
        filtered = []

        for candidate in strategies:
            if len(filtered) == 0:
                filtered.append(candidate)
                continue

            # Check correlation with already selected
            candidate_idx = strategies.index(candidate)
            max_corr = 0.0

            for selected in filtered:
                selected_idx = strategies.index(selected)
                corr = abs(correlation_matrix[candidate_idx, selected_idx])
                max_corr = max(max_corr, corr)

            # Add if correlation below threshold
            if max_corr <= self.config.max_correlation:
                filtered.append(candidate)
            else:
                logger.debug(
                    f"Filtered {candidate.name} due to high correlation: {max_corr:.2f}"
                )

        return filtered
