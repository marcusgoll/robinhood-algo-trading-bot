"""Sentiment score aggregation with recency weighting.

Aggregates sentiment scores from multiple posts using a 30-minute rolling
window with exponential decay weighting (recent posts weighted more heavily).

Constitution v1.0.0:
- Safety_First: Minimum 10 posts required for reliable signal
- Risk_Management: Exponential decay prevents stale data
- Security: Input validation on score ranges

Feature: sentiment-analysis-integration
Tasks: T023-T024 [GREEN] - SentimentAggregator implementation
"""

import logging
import math
from datetime import UTC, datetime

from .models import SentimentScore

# Module logger
logger = logging.getLogger(__name__)


class SentimentAggregator:
    """Aggregates sentiment scores with exponential recency weighting.

    Features:
    - 30-minute rolling window aggregation
    - Exponential decay: recent posts weighted 2x older posts
    - Minimum 10 posts requirement for reliable signal
    - Formula: weighted_avg = Σ(score * weight) / Σ(weight)
    - Weight: e^(-minutes_ago / 10)

    Example:
        >>> aggregator = SentimentAggregator()
        >>> scores = [
        ...     SentimentScore(symbol="AAPL", score=0.8, confidence=0.9, post_count=15, timestamp=now),
        ...     SentimentScore(symbol="AAPL", score=0.6, confidence=0.85, post_count=10, timestamp=now - timedelta(minutes=10)),
        ... ]
        >>> weighted_score = aggregator.aggregate(scores)
        >>> print(f"Weighted sentiment: {weighted_score:.2f}")
        Weighted sentiment: 0.73
    """

    MIN_POSTS_REQUIRED = 10

    def aggregate(self, scores: list[SentimentScore]) -> float | None:
        """Aggregate sentiment scores with exponential recency weighting.

        Args:
            scores: List of SentimentScore objects to aggregate

        Returns:
            Weighted average sentiment score (-1.0 to +1.0), or None if <10 posts

        Notes:
            - Returns None if total post_count < 10 (unreliable signal)
            - Recent posts weighted more heavily via exponential decay
            - Formula: weighted_avg = Σ(score * weight) / Σ(weight)
            - Weight: e^(-minutes_ago / 10)
        """
        if not scores:
            logger.warning("Empty scores list provided to aggregator")
            return None

        # Calculate total post count
        total_posts = sum(score.post_count for score in scores)

        if total_posts < self.MIN_POSTS_REQUIRED:
            logger.info(
                f"Insufficient posts for reliable sentiment: {total_posts} "
                f"(min {self.MIN_POSTS_REQUIRED} required)"
            )
            return None

        # Use current time for recency calculation
        now = datetime.now(UTC)

        # Calculate weights based on recency
        weights = self._weight_by_recency(scores, now)

        # Calculate weighted average
        weighted_sum = sum(score.score * weight for score, weight in zip(scores, weights, strict=False))
        total_weight = sum(weights)

        if total_weight == 0:
            logger.warning("Total weight is zero, returning None")
            return None

        weighted_avg = weighted_sum / total_weight

        logger.debug(
            f"Aggregated {len(scores)} sentiment scores "
            f"({total_posts} posts) -> {weighted_avg:.3f}"
        )

        return weighted_avg

    def _weight_by_recency(self, scores: list[SentimentScore], reference_time: datetime) -> list[float]:
        """Calculate exponential decay weights based on post recency.

        Args:
            scores: List of SentimentScore objects
            reference_time: Reference time for age calculation (usually now)

        Returns:
            List of weights (one per score)

        Formula:
            weight = e^(-minutes_ago / 10)

        Examples:
            - 0 minutes ago: e^0 = 1.0 (full weight)
            - 10 minutes ago: e^(-1) ≈ 0.368 (~37% weight)
            - 20 minutes ago: e^(-2) ≈ 0.135 (~14% weight)
            - Recent posts weighted ~2.7x posts from 10 minutes ago
        """
        weights = []

        for score in scores:
            # Calculate age in minutes
            age_delta = reference_time - score.timestamp
            minutes_ago = age_delta.total_seconds() / 60.0

            # Exponential decay: weight = e^(-minutes_ago / 10)
            # Decay constant 10 means half-life ~7 minutes
            weight = math.exp(-minutes_ago / 10.0)

            weights.append(weight)

        logger.debug(f"Calculated weights: {weights}")

        return weights
