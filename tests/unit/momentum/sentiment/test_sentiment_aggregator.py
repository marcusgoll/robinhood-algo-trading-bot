"""
Unit tests for SentimentAggregator

Tests the 30-min rolling window aggregation with exponential recency weighting.

Constitution v1.0.0:
- Safety_First: Test edge cases (empty list, <10 posts)
- Risk_Management: Test validation logic
- Security: Test data sanitization

Feature: sentiment-analysis-integration
Tasks: T021-T022 [GREEN] - Aggregation unit tests
"""

import pytest
from datetime import datetime, timedelta, UTC
from src.trading_bot.momentum.sentiment.sentiment_aggregator import SentimentAggregator
from src.trading_bot.momentum.sentiment.models import SentimentScore


class TestSentimentAggregator:
    """Test suite for SentimentAggregator class."""

    def test_aggregate_returns_none_if_post_count_less_than_10(self):
        """Test T021: aggregate returns None if post_count <10."""
        # Given: 5 sentiment scores (below min threshold)
        now = datetime.now(UTC)
        scores = [
            SentimentScore(
                symbol="AAPL",
                score=0.8,
                confidence=0.9,
                post_count=5,
                timestamp=now
            )
        ]

        aggregator = SentimentAggregator()

        # When: aggregate is called
        result = aggregator.aggregate(scores)

        # Then: returns None (insufficient data)
        assert result is None

    def test_aggregate_returns_none_if_total_posts_less_than_10(self):
        """Test T021: aggregate returns None if total post_count <10."""
        # Given: Multiple scores but total posts <10
        now = datetime.now(UTC)
        scores = [
            SentimentScore(symbol="AAPL", score=0.7, confidence=0.9, post_count=3, timestamp=now),
            SentimentScore(symbol="AAPL", score=0.6, confidence=0.85, post_count=4, timestamp=now - timedelta(minutes=10)),
            SentimentScore(symbol="AAPL", score=0.5, confidence=0.8, post_count=2, timestamp=now - timedelta(minutes=20)),
        ]

        aggregator = SentimentAggregator()

        # When: aggregate is called
        result = aggregator.aggregate(scores)

        # Then: returns None (total posts = 9, below threshold)
        assert result is None

    def test_aggregate_returns_none_if_empty_list(self):
        """Test T021: aggregate returns None if scores list is empty."""
        # Given: Empty scores list
        scores = []

        aggregator = SentimentAggregator()

        # When: aggregate is called
        result = aggregator.aggregate(scores)

        # Then: returns None
        assert result is None

    def test_aggregate_applies_exponential_recency_weighting(self):
        """Test T022: aggregate applies exponential recency weighting."""
        # Given: 15 posts with recent posts more bullish than older posts
        now = datetime.now(UTC)

        # Recent posts (last 5 minutes): very bullish (0.9)
        recent_scores = [
            SentimentScore(symbol="AAPL", score=0.9, confidence=0.95, post_count=5, timestamp=now - timedelta(minutes=i))
            for i in range(0, 5)
        ]

        # Older posts (15-25 minutes ago): bearish (0.3)
        older_scores = [
            SentimentScore(symbol="AAPL", score=0.3, confidence=0.85, post_count=5, timestamp=now - timedelta(minutes=i))
            for i in range(15, 25)
        ]

        all_scores = recent_scores + older_scores

        aggregator = SentimentAggregator()

        # When: aggregate is called
        weighted_avg = aggregator.aggregate(all_scores)

        # Calculate simple average for comparison
        simple_avg = sum(score.score for score in all_scores) / len(all_scores)

        # Then: weighted average should be higher than simple average
        # (recent bullish posts weighted more heavily)
        assert weighted_avg is not None
        assert weighted_avg > simple_avg
        assert 0.6 < weighted_avg < 1.0  # Should be closer to recent bullish scores

    def test_aggregate_with_exact_10_posts_returns_score(self):
        """Test T021: aggregate returns score when exactly 10 posts."""
        # Given: Exactly 10 posts (minimum threshold)
        now = datetime.now(UTC)
        scores = [
            SentimentScore(symbol="AAPL", score=0.7, confidence=0.9, post_count=10, timestamp=now)
        ]

        aggregator = SentimentAggregator()

        # When: aggregate is called
        result = aggregator.aggregate(scores)

        # Then: returns the score (meets minimum threshold)
        assert result is not None
        assert isinstance(result, float)
        assert -1.0 <= result <= 1.0

    def test_aggregate_normalizes_score_to_range(self):
        """Test T022: aggregate returns score in valid range [-1.0, 1.0]."""
        # Given: 15 posts with mixed sentiment
        now = datetime.now(UTC)
        scores = [
            SentimentScore(symbol="AAPL", score=0.8, confidence=0.9, post_count=5, timestamp=now),
            SentimentScore(symbol="AAPL", score=-0.6, confidence=0.85, post_count=5, timestamp=now - timedelta(minutes=10)),
            SentimentScore(symbol="AAPL", score=0.2, confidence=0.8, post_count=5, timestamp=now - timedelta(minutes=20)),
        ]

        aggregator = SentimentAggregator()

        # When: aggregate is called
        result = aggregator.aggregate(scores)

        # Then: returns score in valid range
        assert result is not None
        assert -1.0 <= result <= 1.0

    def test_weight_by_recency_applies_exponential_decay(self):
        """Test T024: _weight_by_recency applies exponential decay formula."""
        # Given: Posts at different timestamps
        now = datetime.now(UTC)
        scores = [
            SentimentScore(symbol="AAPL", score=0.8, confidence=0.9, post_count=10, timestamp=now),
            SentimentScore(symbol="AAPL", score=0.6, confidence=0.85, post_count=10, timestamp=now - timedelta(minutes=10)),
            SentimentScore(symbol="AAPL", score=0.4, confidence=0.8, post_count=10, timestamp=now - timedelta(minutes=20)),
        ]

        aggregator = SentimentAggregator()

        # When: _weight_by_recency is called
        weights = aggregator._weight_by_recency(scores, now)

        # Then: weights decrease exponentially with age
        assert len(weights) == 3
        assert weights[0] > weights[1] > weights[2]  # Most recent has highest weight
        assert all(w > 0 for w in weights)  # All weights positive

        # Recent post should be weighted ~2x older post (approximately)
        # weight = e^(-minutes_ago / 10)
        # At 0 min: e^0 = 1.0
        # At 10 min: e^(-10/10) = e^(-1) ≈ 0.368
        # At 20 min: e^(-20/10) = e^(-2) ≈ 0.135
        assert abs(weights[0] - 1.0) < 0.01  # ~1.0
        assert abs(weights[1] - 0.368) < 0.05  # ~0.368
        assert abs(weights[2] - 0.135) < 0.05  # ~0.135

    def test_aggregate_with_all_recent_posts_returns_average(self):
        """Test T022: aggregate with all posts at same time returns simple average."""
        # Given: All posts at same timestamp (no recency weighting)
        now = datetime.now(UTC)
        scores = [
            SentimentScore(symbol="AAPL", score=0.8, confidence=0.9, post_count=5, timestamp=now),
            SentimentScore(symbol="AAPL", score=0.6, confidence=0.85, post_count=5, timestamp=now),
            SentimentScore(symbol="AAPL", score=0.4, confidence=0.8, post_count=5, timestamp=now),
        ]

        aggregator = SentimentAggregator()

        # When: aggregate is called
        result = aggregator.aggregate(scores)

        # Then: returns simple average (0.8 + 0.6 + 0.4) / 3 = 0.6
        assert result is not None
        assert abs(result - 0.6) < 0.01  # Allow small floating point error
