"""
Unit tests for SentimentAnalyzer service.

Tests:
- T015: SentimentAnalyzer loads FinBERT model
- T016: analyze_post returns sentiment scores
- T017: analyze_batch processes multiple posts

Feature: sentiment-analysis-integration
Tasks: T015-T017 [RED] - Write tests for SentimentAnalyzer
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.trading_bot.momentum.sentiment.sentiment_analyzer import SentimentAnalyzer


class TestSentimentAnalyzerInit:
    """Test suite for SentimentAnalyzer.__init__() method."""

    @patch("src.trading_bot.momentum.sentiment.sentiment_analyzer.AutoTokenizer")
    @patch("src.trading_bot.momentum.sentiment.sentiment_analyzer.AutoModelForSequenceClassification")
    def test_init_loads_finbert_model(self, mock_model_class, mock_tokenizer_class):
        """Test that __init__ loads FinBERT model from Hugging Face."""
        # Given: Mocked FinBERT model and tokenizer
        mock_tokenizer = MagicMock()
        mock_tokenizer_class.from_pretrained.return_value = mock_tokenizer

        mock_model = MagicMock()
        mock_model_class.from_pretrained.return_value = mock_model

        # When: Creating SentimentAnalyzer
        analyzer = SentimentAnalyzer()

        # Then: Model and tokenizer loaded from ProsusAI/finbert
        mock_tokenizer_class.from_pretrained.assert_called_once_with("ProsusAI/finbert")
        mock_model_class.from_pretrained.assert_called_once_with("ProsusAI/finbert")
        assert analyzer.tokenizer is not None
        assert analyzer.model is not None

    @patch("src.trading_bot.momentum.sentiment.sentiment_analyzer.AutoTokenizer")
    @patch("src.trading_bot.momentum.sentiment.sentiment_analyzer.AutoModelForSequenceClassification")
    def test_init_handles_model_load_failure(self, mock_model_class, mock_tokenizer_class):
        """Test graceful handling when model loading fails."""
        # Reset class state
        from src.trading_bot.momentum.sentiment.sentiment_analyzer import SentimentAnalyzer as SA
        SA._model_loaded = False
        SA._model = None
        SA._tokenizer = None

        # Given: Model loading raises exception
        mock_tokenizer_class.from_pretrained.side_effect = Exception("Download failed")

        # When/Then: Should not raise exception (graceful degradation)
        try:
            analyzer = SentimentAnalyzer()
            # Analyzer should still be created but model disabled
            assert analyzer.model is None
            assert analyzer.tokenizer is None
        except Exception as e:
            pytest.fail(f"SentimentAnalyzer should handle model loading failures gracefully: {e}")


class TestAnalyzePost:
    """Test suite for SentimentAnalyzer.analyze_post() method."""

    @patch("src.trading_bot.momentum.sentiment.sentiment_analyzer.AutoTokenizer")
    @patch("src.trading_bot.momentum.sentiment.sentiment_analyzer.AutoModelForSequenceClassification")
    @patch("src.trading_bot.momentum.sentiment.sentiment_analyzer.torch")
    def test_analyze_post_returns_sentiment_scores(self, mock_torch, mock_model_class, mock_tokenizer_class):
        """Test that analyze_post returns dict with negative/neutral/positive scores."""
        # Reset singleton state
        from src.trading_bot.momentum.sentiment.sentiment_analyzer import SentimentAnalyzer as SA
        SA._model_loaded = False
        SA._model = None
        SA._tokenizer = None

        # Mock torch.cuda to avoid format string issues
        mock_torch.cuda.is_available.return_value = False

        # Given: Mocked model that returns bullish sentiment
        mock_tokenizer = MagicMock()
        mock_tokenizer_class.from_pretrained.return_value = mock_tokenizer
        mock_tokenizer.return_value = {"input_ids": MagicMock(), "attention_mask": MagicMock()}

        # Mock model output: [negative, neutral, positive] logits
        mock_output = MagicMock()
        mock_output.logits = [[0.1, 0.2, 0.7]]  # Bullish (positive=0.7)

        mock_model = MagicMock()
        mock_model.return_value = mock_output
        mock_model.eval = MagicMock()
        mock_model_class.from_pretrained.return_value = mock_model

        # Mock softmax to return tensor-like object
        mock_softmax_result = MagicMock()
        mock_softmax_result.__getitem__ = lambda self, idx: 0.6 if idx == 2 else (0.2 if idx in [0, 1] else 0)
        mock_torch.nn.functional.softmax.return_value = mock_softmax_result

        analyzer = SentimentAnalyzer()

        # When: Analyzing bullish text
        result = analyzer.analyze_post("AAPL to the moon! Great earnings!")

        # Then: Returns dict with three scores
        assert isinstance(result, dict)
        assert "negative" in result
        assert "neutral" in result
        assert "positive" in result
        assert all(0 <= score <= 1 for score in result.values())
        assert abs(sum(result.values()) - 1.0) < 0.01  # Should sum to ~1.0

    @patch("src.trading_bot.momentum.sentiment.sentiment_analyzer.AutoTokenizer")
    @patch("src.trading_bot.momentum.sentiment.sentiment_analyzer.AutoModelForSequenceClassification")
    def test_analyze_post_handles_empty_text(self, mock_model_class, mock_tokenizer_class):
        """Test graceful handling of empty text."""
        # Given: Valid analyzer
        mock_tokenizer = MagicMock()
        mock_tokenizer_class.from_pretrained.return_value = mock_tokenizer

        mock_model = MagicMock()
        mock_model_class.from_pretrained.return_value = mock_model

        analyzer = SentimentAnalyzer()

        # When: Analyzing empty text
        result = analyzer.analyze_post("")

        # Then: Returns neutral sentiment (0.33/0.33/0.33) or None
        if result is not None:
            assert isinstance(result, dict)
            assert all(0 <= score <= 1 for score in result.values())


class TestAnalyzeBatch:
    """Test suite for SentimentAnalyzer.analyze_batch() method."""

    @patch("src.trading_bot.momentum.sentiment.sentiment_analyzer.AutoTokenizer")
    @patch("src.trading_bot.momentum.sentiment.sentiment_analyzer.AutoModelForSequenceClassification")
    @patch("src.trading_bot.momentum.sentiment.sentiment_analyzer.torch")
    def test_analyze_batch_processes_multiple_posts(self, mock_torch, mock_model_class, mock_tokenizer_class):
        """Test that analyze_batch returns sentiment scores for all posts."""
        # Reset singleton state
        from src.trading_bot.momentum.sentiment.sentiment_analyzer import SentimentAnalyzer as SA
        SA._model_loaded = False
        SA._model = None
        SA._tokenizer = None

        # Mock torch.cuda to avoid format string issues
        mock_torch.cuda.is_available.return_value = False

        # Given: Mocked model with batch inference
        mock_tokenizer = MagicMock()
        mock_tokenizer_class.from_pretrained.return_value = mock_tokenizer
        mock_tokenizer.return_value = {"input_ids": MagicMock(), "attention_mask": MagicMock()}

        # Mock batch output: 3 posts with different sentiments
        mock_output = MagicMock()
        mock_output.logits = [
            [0.7, 0.2, 0.1],  # Bearish (negative=0.7)
            [0.2, 0.6, 0.2],  # Neutral (neutral=0.6)
            [0.1, 0.2, 0.7],  # Bullish (positive=0.7)
        ]

        mock_model = MagicMock()
        mock_model.return_value = mock_output
        mock_model.eval = MagicMock()
        mock_model_class.from_pretrained.return_value = mock_model

        # Mock softmax to return list of tensor-like objects
        mock_probs = []
        for probs in [[0.6, 0.3, 0.1], [0.2, 0.6, 0.2], [0.1, 0.3, 0.6]]:
            mock_prob = MagicMock()
            mock_prob.__getitem__ = lambda self, idx, p=probs: p[idx]
            mock_probs.append(mock_prob)
        mock_torch.nn.functional.softmax.return_value = mock_probs

        analyzer = SentimentAnalyzer()

        # When: Analyzing batch of 3 posts
        posts = [
            "AAPL crashing, sell now!",
            "AAPL trading sideways",
            "AAPL to the moon!",
        ]
        results = analyzer.analyze_batch(posts)

        # Then: Returns list of 3 sentiment dicts
        assert isinstance(results, list)
        assert len(results) == 3
        assert all(isinstance(r, dict) for r in results)
        assert all("negative" in r and "neutral" in r and "positive" in r for r in results)

    @patch("src.trading_bot.momentum.sentiment.sentiment_analyzer.AutoTokenizer")
    @patch("src.trading_bot.momentum.sentiment.sentiment_analyzer.AutoModelForSequenceClassification")
    def test_analyze_batch_handles_empty_list(self, mock_model_class, mock_tokenizer_class):
        """Test graceful handling of empty batch."""
        # Given: Valid analyzer
        mock_tokenizer = MagicMock()
        mock_tokenizer_class.from_pretrained.return_value = mock_tokenizer

        mock_model = MagicMock()
        mock_model_class.from_pretrained.return_value = mock_model

        analyzer = SentimentAnalyzer()

        # When: Analyzing empty batch
        results = analyzer.analyze_batch([])

        # Then: Returns empty list (not None or error)
        assert results == []

    @patch("src.trading_bot.momentum.sentiment.sentiment_analyzer.AutoTokenizer")
    @patch("src.trading_bot.momentum.sentiment.sentiment_analyzer.AutoModelForSequenceClassification")
    @patch("src.trading_bot.momentum.sentiment.sentiment_analyzer.torch")
    def test_analyze_batch_performance_under_200ms_per_post(self, mock_torch, mock_model_class, mock_tokenizer_class):
        """Test that batch inference meets performance target (<200ms per post amortized)."""
        # Reset singleton state
        from src.trading_bot.momentum.sentiment.sentiment_analyzer import SentimentAnalyzer as SA
        SA._model_loaded = False
        SA._model = None
        SA._tokenizer = None

        # Mock torch.cuda to avoid format string issues
        mock_torch.cuda.is_available.return_value = False

        # Given: Mocked fast model
        mock_tokenizer = MagicMock()
        mock_tokenizer_class.from_pretrained.return_value = mock_tokenizer
        mock_tokenizer.return_value = {"input_ids": MagicMock(), "attention_mask": MagicMock()}

        mock_output = MagicMock()
        mock_output.logits = [[0.3, 0.4, 0.3]] * 50  # 50 posts

        mock_model = MagicMock()
        mock_model.return_value = mock_output
        mock_model.eval = MagicMock()
        mock_model_class.from_pretrained.return_value = mock_model

        # Mock softmax for 50 posts
        mock_probs = []
        for _ in range(50):
            mock_prob = MagicMock()
            mock_prob.__getitem__ = lambda self, idx: [0.33, 0.34, 0.33][idx]
            mock_probs.append(mock_prob)
        mock_torch.nn.functional.softmax.return_value = mock_probs

        analyzer = SentimentAnalyzer()

        # When: Analyzing batch of 50 posts
        import time
        posts = ["AAPL post " + str(i) for i in range(50)]
        start = time.time()
        results = analyzer.analyze_batch(posts)
        duration_ms = (time.time() - start) * 1000

        # Then: Completes in <10s total (200ms * 50 posts)
        # Note: This is mocked, real test would measure actual inference time
        assert len(results) == 50
        assert duration_ms < 10000  # 10s for 50 posts = 200ms/post target
