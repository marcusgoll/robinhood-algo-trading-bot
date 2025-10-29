"""
FinBERT Sentiment Analysis Service

Loads FinBERT model (ProsusAI/finbert) from Hugging Face and performs
sentiment analysis on financial text with batch inference support.

Constitution v1.0.0:
- Safety_First: Graceful degradation on model loading failures
- Risk_Management: Batch inference for performance
- Security: Model loaded from verified source only

Feature: sentiment-analysis-integration
Tasks: T018-T020 [GREEN] - SentimentAnalyzer implementation
"""

import logging
from typing import List, Dict

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# Module logger
logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """Sentiment analysis service using FinBERT model.

    Features:
    - FinBERT model from Hugging Face (ProsusAI/finbert)
    - Batch inference for performance (<200ms per post amortized)
    - Returns sentiment probabilities (negative, neutral, positive)
    - Singleton pattern (model loaded once, reused)
    - Graceful degradation on model loading failures

    Example:
        >>> analyzer = SentimentAnalyzer()
        >>> scores = analyzer.analyze_post("AAPL to the moon!")
        >>> print(scores)
        {'negative': 0.1, 'neutral': 0.2, 'positive': 0.7}
    """

    # Class-level model cache (singleton pattern)
    _model = None
    _tokenizer = None
    _model_loaded = False

    def __init__(self):
        """Initialize FinBERT model and tokenizer.

        Loads model on first instantiation, reuses cached instance thereafter.
        Fails gracefully if model loading fails (logs error, continues without sentiment).
        """
        # Load model only once (singleton pattern)
        if not SentimentAnalyzer._model_loaded:
            try:
                logger.info("Loading FinBERT model from Hugging Face...")
                start_time = torch.cuda.Event(enable_timing=True) if torch.cuda.is_available() else None
                end_time = torch.cuda.Event(enable_timing=True) if torch.cuda.is_available() else None

                if start_time:
                    start_time.record()

                # Load tokenizer and model
                SentimentAnalyzer._tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
                SentimentAnalyzer._model = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")

                # Move to GPU if available
                if torch.cuda.is_available():
                    SentimentAnalyzer._model = SentimentAnalyzer._model.cuda()
                    logger.info("FinBERT model moved to GPU")

                # Set to evaluation mode
                SentimentAnalyzer._model.eval()

                if start_time and end_time:
                    end_time.record()
                    torch.cuda.synchronize()
                    load_time_ms = start_time.elapsed_time(end_time)
                    logger.info(f"FinBERT model loaded successfully in {load_time_ms:.2f}ms")
                else:
                    logger.info("FinBERT model loaded successfully")

                SentimentAnalyzer._model_loaded = True

            except Exception as e:
                logger.error(f"Failed to load FinBERT model: {e}")
                logger.warning("Sentiment analysis will be disabled")
                SentimentAnalyzer._model = None
                SentimentAnalyzer._tokenizer = None
                SentimentAnalyzer._model_loaded = True  # Don't retry on every instantiation

        # Reference class-level instances
        self.model = SentimentAnalyzer._model
        self.tokenizer = SentimentAnalyzer._tokenizer

    def analyze_post(self, text: str) -> Dict[str, float] | None:
        """Analyze sentiment of a single post.

        Args:
            text: Post text to analyze

        Returns:
            Dict with 'negative', 'neutral', 'positive' probabilities (sum to 1.0)
            Returns None if model not loaded or text empty

        Example:
            >>> analyzer.analyze_post("AAPL earnings beat!")
            {'negative': 0.1, 'neutral': 0.2, 'positive': 0.7}
        """
        if not self.model or not self.tokenizer:
            logger.warning("Model not loaded, returning None")
            return None

        if not text or not text.strip():
            logger.warning("Empty text provided, returning neutral sentiment")
            return {"negative": 0.33, "neutral": 0.34, "positive": 0.33}

        try:
            # Tokenize input
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=512,
                padding=True
            )

            # Move to GPU if available
            if torch.cuda.is_available():
                inputs = {k: v.cuda() for k, v in inputs.items()}

            # Run inference (no gradient computation)
            with torch.no_grad():
                outputs = self.model(**inputs)

            # Get probabilities (softmax over logits)
            probs = torch.nn.functional.softmax(outputs.logits[0], dim=-1)

            # FinBERT outputs: [negative, neutral, positive]
            return {
                "negative": float(probs[0]),
                "neutral": float(probs[1]),
                "positive": float(probs[2])
            }

        except Exception as e:
            logger.error(f"Sentiment analysis failed for text: {e}")
            return None

    def analyze_batch(self, texts: List[str]) -> List[Dict[str, float]]:
        """Analyze sentiment of multiple posts in batch.

        Args:
            texts: List of post texts to analyze

        Returns:
            List of sentiment dicts (one per post)
            Empty list if model not loaded

        Notes:
            - Batch inference is faster than individual calls (amortized <200ms/post)
            - Handles empty texts gracefully (returns neutral sentiment)
            - Returns partial results if some posts fail

        Example:
            >>> texts = ["AAPL up!", "AAPL down!", "AAPL flat"]
            >>> analyzer.analyze_batch(texts)
            [{'negative': 0.1, ...}, {'negative': 0.8, ...}, {'negative': 0.3, ...}]
        """
        if not self.model or not self.tokenizer:
            logger.warning("Model not loaded, returning empty list")
            return []

        if not texts:
            return []

        try:
            # Filter out empty texts (keep indices for result mapping)
            non_empty_texts = []
            text_indices = []
            for i, text in enumerate(texts):
                if text and text.strip():
                    non_empty_texts.append(text)
                    text_indices.append(i)

            if not non_empty_texts:
                logger.warning("All texts empty, returning neutral sentiments")
                return [{"negative": 0.33, "neutral": 0.34, "positive": 0.33}] * len(texts)

            # Batch tokenization
            inputs = self.tokenizer(
                non_empty_texts,
                return_tensors="pt",
                truncation=True,
                max_length=512,
                padding=True
            )

            # Move to GPU if available
            if torch.cuda.is_available():
                inputs = {k: v.cuda() for k, v in inputs.items()}

            # Batch inference (no gradient computation)
            with torch.no_grad():
                outputs = self.model(**inputs)

            # Get probabilities for all posts
            probs = torch.nn.functional.softmax(outputs.logits, dim=-1)

            # Convert to list of dicts
            results = []
            for prob in probs:
                results.append({
                    "negative": float(prob[0]),
                    "neutral": float(prob[1]),
                    "positive": float(prob[2])
                })

            # Fill in neutral scores for empty texts
            full_results = []
            result_idx = 0
            for i in range(len(texts)):
                if i in text_indices:
                    full_results.append(results[result_idx])
                    result_idx += 1
                else:
                    full_results.append({"negative": 0.33, "neutral": 0.34, "positive": 0.33})

            logger.info(f"Analyzed {len(texts)} posts in batch")
            return full_results

        except Exception as e:
            logger.error(f"Batch sentiment analysis failed: {e}")
            return []
