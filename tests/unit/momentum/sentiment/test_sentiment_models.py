"""
Unit tests for sentiment data models

Tests validation logic in SentimentPost and SentimentScore dataclasses.

Constitution v1.0.0:
- Testing_Requirements: Test all validation edge cases

Feature: sentiment-analysis-integration
Tasks: Coverage improvement for models.py
"""

import pytest
from datetime import datetime, UTC
from src.trading_bot.momentum.sentiment.models import SentimentPost, SentimentScore


class TestSentimentPostValidation:
    """Test suite for SentimentPost validation."""

    def test_valid_sentiment_post_creation(self):
        """Test creating valid SentimentPost."""
        post = SentimentPost(
            text="AAPL to the moon!",
            author="user123",
            timestamp=datetime.now(UTC),
            source="Twitter",
            symbol="AAPL"
        )
        assert post.text == "AAPL to the moon!"
        assert post.symbol == "AAPL"

    def test_empty_text_raises_error(self):
        """Test that empty text raises ValueError."""
        with pytest.raises(ValueError, match="text must be non-empty"):
            SentimentPost(
                text="",
                author="user123",
                timestamp=datetime.now(UTC),
                source="Twitter",
                symbol="AAPL"
            )

    def test_whitespace_only_text_raises_error(self):
        """Test that whitespace-only text raises ValueError."""
        with pytest.raises(ValueError, match="text must be non-empty"):
            SentimentPost(
                text="   ",
                author="user123",
                timestamp=datetime.now(UTC),
                source="Twitter",
                symbol="AAPL"
            )

    def test_invalid_source_raises_error(self):
        """Test that invalid source raises ValueError."""
        with pytest.raises(ValueError, match="must be 'Twitter' or 'Reddit'"):
            SentimentPost(
                text="AAPL news",
                author="user123",
                timestamp=datetime.now(UTC),
                source="Facebook",  # Invalid
                symbol="AAPL"
            )

    def test_invalid_timestamp_type_raises_error(self):
        """Test that non-datetime timestamp raises ValueError."""
        with pytest.raises(ValueError, match="timestamp must be a datetime object"):
            SentimentPost(
                text="AAPL news",
                author="user123",
                timestamp="2025-10-29",  # String instead of datetime
                source="Twitter",
                symbol="AAPL"
            )

    def test_invalid_symbol_format_raises_error(self):
        """Test that invalid symbol format raises ValueError."""
        with pytest.raises(ValueError, match="must be 1-5 uppercase characters"):
            SentimentPost(
                text="AAPL news",
                author="user123",
                timestamp=datetime.now(UTC),
                source="Twitter",
                symbol="aapl"  # Lowercase invalid
            )

    def test_symbol_too_long_raises_error(self):
        """Test that symbol > 5 characters raises ValueError."""
        with pytest.raises(ValueError, match="must be 1-5 uppercase characters"):
            SentimentPost(
                text="News",
                author="user123",
                timestamp=datetime.now(UTC),
                source="Twitter",
                symbol="TOOLONG"  # 7 characters
            )


class TestSentimentScoreValidation:
    """Test suite for SentimentScore validation."""

    def test_valid_sentiment_score_creation(self):
        """Test creating valid SentimentScore."""
        score = SentimentScore(
            symbol="AAPL",
            score=0.75,
            confidence=0.95,
            post_count=50,
            timestamp=datetime.now(UTC)
        )
        assert score.symbol == "AAPL"
        assert score.score == 0.75
        assert score.confidence == 0.95

    def test_score_above_range_raises_error(self):
        """Test that score > 1.0 raises ValueError."""
        with pytest.raises(ValueError, match="score .* must be between -1.0 and 1.0"):
            SentimentScore(
                symbol="AAPL",
                score=1.5,  # Invalid
                confidence=0.95,
                post_count=50,
                timestamp=datetime.now(UTC)
            )

    def test_score_below_range_raises_error(self):
        """Test that score < -1.0 raises ValueError."""
        with pytest.raises(ValueError, match="score .* must be between -1.0 and 1.0"):
            SentimentScore(
                symbol="AAPL",
                score=-1.5,  # Invalid
                confidence=0.95,
                post_count=50,
                timestamp=datetime.now(UTC)
            )

    def test_confidence_above_range_raises_error(self):
        """Test that confidence > 1.0 raises ValueError."""
        with pytest.raises(ValueError, match="confidence .* must be between 0.0 and 1.0"):
            SentimentScore(
                symbol="AAPL",
                score=0.75,
                confidence=1.5,  # Invalid
                post_count=50,
                timestamp=datetime.now(UTC)
            )

    def test_confidence_below_range_raises_error(self):
        """Test that confidence < 0.0 raises ValueError."""
        with pytest.raises(ValueError, match="confidence .* must be between 0.0 and 1.0"):
            SentimentScore(
                symbol="AAPL",
                score=0.75,
                confidence=-0.1,  # Invalid
                post_count=50,
                timestamp=datetime.now(UTC)
            )

    def test_negative_post_count_raises_error(self):
        """Test that negative post_count raises ValueError."""
        with pytest.raises(ValueError, match="post_count .* must be non-negative"):
            SentimentScore(
                symbol="AAPL",
                score=0.75,
                confidence=0.95,
                post_count=-5,  # Invalid
                timestamp=datetime.now(UTC)
            )

    def test_invalid_timestamp_type_raises_error(self):
        """Test that non-datetime timestamp raises ValueError."""
        with pytest.raises(ValueError, match="timestamp must be a datetime object"):
            SentimentScore(
                symbol="AAPL",
                score=0.75,
                confidence=0.95,
                post_count=50,
                timestamp="2025-10-29"  # String instead of datetime
            )

    def test_invalid_symbol_format_raises_error(self):
        """Test that invalid symbol format raises ValueError."""
        with pytest.raises(ValueError, match="must be 1-5 uppercase characters"):
            SentimentScore(
                symbol="aapl",  # Lowercase invalid
                score=0.75,
                confidence=0.95,
                post_count=50,
                timestamp=datetime.now(UTC)
            )
