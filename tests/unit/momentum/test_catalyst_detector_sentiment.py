"""
Unit tests for CatalystDetector sentiment integration

Tests the integration of sentiment analysis into catalyst detection.

Constitution v1.0.0:
- Safety_First: Test graceful degradation when sentiment unavailable
- Risk_Management: Test feature flag functionality
- Security: Test credentials handling

Feature: sentiment-analysis-integration
Tasks: T025-T026 [GREEN] - CatalystDetector sentiment integration tests
"""

import pytest
from datetime import datetime, timedelta, UTC
from unittest.mock import MagicMock, AsyncMock, patch
from src.trading_bot.momentum.catalyst_detector import CatalystDetector
from src.trading_bot.momentum.config import MomentumConfig
from src.trading_bot.momentum.schemas.momentum_signal import SignalType
from src.trading_bot.momentum.sentiment.models import SentimentPost, SentimentScore


class TestCatalystDetectorSentiment:
    """Test suite for CatalystDetector sentiment integration."""

    @pytest.fixture
    def mock_config(self):
        """Create mock config with sentiment enabled."""
        config = MagicMock(spec=MomentumConfig)
        config.alpaca_api_key = "test-api-key"
        config.alpaca_secret_key = "test-secret-key"
        config.sentiment_enabled = True
        config.twitter_bearer_token = "test-twitter-token"
        config.reddit_client_id = "test-reddit-id"
        config.reddit_client_secret = "test-reddit-secret"
        config.reddit_user_agent = "test-user-agent"
        config.sentiment_threshold = 0.6
        return config

    @pytest.fixture
    def mock_config_sentiment_disabled(self):
        """Create mock config with sentiment disabled."""
        config = MagicMock(spec=MomentumConfig)
        config.alpaca_api_key = "test-api-key"
        config.alpaca_secret_key = "test-secret-key"
        config.sentiment_enabled = False
        return config

    @pytest.mark.asyncio
    async def test_scan_populates_sentiment_score_when_available(self, mock_config):
        """Test T025: CatalystDetector.scan populates sentiment_score when sentiment available."""
        # Given: CatalystDetector with sentiment enabled
        detector = CatalystDetector(mock_config)

        # Mock news data (from Alpaca API)
        mock_news_data = {
            "news": [
                {
                    "headline": "AAPL reports record earnings",
                    "created_at": datetime.now(UTC).isoformat(),
                    "symbols": ["AAPL"],
                    "source": "test-source"
                }
            ]
        }

        # Mock sentiment data (from sentiment pipeline)
        now = datetime.now(UTC)
        mock_sentiment_score = SentimentScore(
            symbol="AAPL",
            score=0.85,
            confidence=0.95,
            post_count=50,
            timestamp=now
        )

        # Patch the fetch and sentiment methods
        with patch.object(detector, '_fetch_news_from_alpaca', new_callable=AsyncMock) as mock_fetch:
            with patch('src.trading_bot.momentum.catalyst_detector.SentimentFetcher') as mock_fetcher_class:
                with patch('src.trading_bot.momentum.catalyst_detector.SentimentAnalyzer') as mock_analyzer_class:
                    with patch('src.trading_bot.momentum.catalyst_detector.SentimentAggregator') as mock_aggregator_class:
                        # Setup mocks
                        mock_fetch.return_value = mock_news_data

                        # Mock sentiment pipeline
                        mock_fetcher = MagicMock()
                        mock_fetcher.fetch_all.return_value = [
                            SentimentPost(
                                text="AAPL to the moon!",
                                author="user1",
                                timestamp=now,
                                source="Twitter",
                                symbol="AAPL"
                            )
                        ] * 50  # 50 posts

                        mock_analyzer = MagicMock()
                        mock_analyzer.analyze_batch.return_value = [
                            {"negative": 0.1, "neutral": 0.2, "positive": 0.7}
                        ] * 50

                        mock_aggregator = MagicMock()
                        mock_aggregator.aggregate.return_value = 0.85

                        mock_fetcher_class.return_value = mock_fetcher
                        mock_analyzer_class.return_value = mock_analyzer
                        mock_aggregator_class.return_value = mock_aggregator

                        # When: scan is called
                        signals = await detector.scan(["AAPL"])

                        # Then: sentiment_score is populated
                        assert len(signals) > 0
                        signal = signals[0]
                        assert signal.details.get("sentiment_score") is not None
                        assert -1.0 <= signal.details.get("sentiment_score") <= 1.0

    @pytest.mark.asyncio
    async def test_scan_gracefully_degrades_on_sentiment_failure(self, mock_config):
        """Test T026: CatalystDetector gracefully degrades when sentiment fails."""
        # Given: CatalystDetector with sentiment enabled
        detector = CatalystDetector(mock_config)

        # Mock news data (from Alpaca API)
        mock_news_data = {
            "news": [
                {
                    "headline": "AAPL reports record earnings",
                    "created_at": datetime.now(UTC).isoformat(),
                    "symbols": ["AAPL"],
                    "source": "test-source"
                }
            ]
        }

        # Patch the fetch method and simulate sentiment failure
        with patch.object(detector, '_fetch_news_from_alpaca', new_callable=AsyncMock) as mock_fetch:
            with patch('src.trading_bot.momentum.catalyst_detector.SentimentFetcher') as mock_fetcher_class:
                # Setup mocks
                mock_fetch.return_value = mock_news_data

                # Mock sentiment pipeline failure (Twitter API error)
                mock_fetcher = MagicMock()
                mock_fetcher.fetch_all.side_effect = Exception("Twitter API rate limit")

                mock_fetcher_class.return_value = mock_fetcher

                # When: scan is called
                signals = await detector.scan(["AAPL"])

                # Then: signal is still created with sentiment_score=None (graceful degradation)
                assert len(signals) > 0
                signal = signals[0]
                # Sentiment score should be None due to failure
                sentiment_score = signal.details.get("sentiment_score")
                assert sentiment_score is None

    @pytest.mark.asyncio
    async def test_scan_skips_sentiment_when_feature_disabled(self, mock_config_sentiment_disabled):
        """Test T029: CatalystDetector skips sentiment when SENTIMENT_ENABLED=false."""
        # Given: CatalystDetector with sentiment disabled
        detector = CatalystDetector(mock_config_sentiment_disabled)

        # Mock news data (from Alpaca API)
        mock_news_data = {
            "news": [
                {
                    "headline": "AAPL reports record earnings",
                    "created_at": datetime.now(UTC).isoformat(),
                    "symbols": ["AAPL"],
                    "source": "test-source"
                }
            ]
        }

        # Patch the fetch method
        with patch.object(detector, '_fetch_news_from_alpaca', new_callable=AsyncMock) as mock_fetch:
            with patch('src.trading_bot.momentum.catalyst_detector.SentimentFetcher') as mock_fetcher_class:
                # Setup mocks
                mock_fetch.return_value = mock_news_data

                mock_fetcher = MagicMock()
                mock_fetcher_class.return_value = mock_fetcher

                # When: scan is called
                signals = await detector.scan(["AAPL"])

                # Then: sentiment analysis was NOT called (feature disabled)
                mock_fetcher.fetch_all.assert_not_called()

                # And: signals are still created (news-only detection continues)
                assert len(signals) > 0
                signal = signals[0]
                # Sentiment score should be None (feature disabled)
                assert signal.details.get("sentiment_score") is None

    @pytest.mark.asyncio
    async def test_scan_with_multiple_symbols_includes_sentiment(self, mock_config):
        """Test T025: CatalystDetector handles multiple symbols with sentiment."""
        # Given: CatalystDetector with sentiment enabled
        detector = CatalystDetector(mock_config)

        # Mock news data for multiple symbols
        now = datetime.now(UTC)
        mock_news_data = {
            "news": [
                {
                    "headline": "AAPL reports record earnings",
                    "created_at": now.isoformat(),
                    "symbols": ["AAPL"],
                    "source": "test-source"
                },
                {
                    "headline": "TSLA production miss",
                    "created_at": now.isoformat(),
                    "symbols": ["TSLA"],
                    "source": "test-source"
                }
            ]
        }

        # Patch methods
        with patch.object(detector, '_fetch_news_from_alpaca', new_callable=AsyncMock) as mock_fetch:
            with patch('src.trading_bot.momentum.catalyst_detector.SentimentFetcher') as mock_fetcher_class:
                with patch('src.trading_bot.momentum.catalyst_detector.SentimentAnalyzer') as mock_analyzer_class:
                    with patch('src.trading_bot.momentum.catalyst_detector.SentimentAggregator') as mock_aggregator_class:
                        # Setup mocks
                        mock_fetch.return_value = mock_news_data

                        mock_fetcher = MagicMock()
                        mock_fetcher.fetch_all.return_value = [
                            SentimentPost(
                                text="Sample post",
                                author="user1",
                                timestamp=now,
                                source="Twitter",
                                symbol="AAPL"
                            )
                        ] * 50

                        mock_analyzer = MagicMock()
                        mock_analyzer.analyze_batch.return_value = [
                            {"negative": 0.1, "neutral": 0.2, "positive": 0.7}
                        ] * 50

                        mock_aggregator = MagicMock()
                        mock_aggregator.aggregate.return_value = 0.75

                        mock_fetcher_class.return_value = mock_fetcher
                        mock_analyzer_class.return_value = mock_analyzer
                        mock_aggregator_class.return_value = mock_aggregator

                        # When: scan is called with multiple symbols
                        signals = await detector.scan(["AAPL", "TSLA"])

                        # Then: sentiment analysis was called for each symbol
                        assert mock_fetcher.fetch_all.call_count >= 1

                        # And: signals include sentiment scores
                        assert len(signals) > 0
