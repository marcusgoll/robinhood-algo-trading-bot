"""Sentiment Analysis Module for Momentum Trading Bot.

This module provides social media sentiment analysis integration using FinBERT
to score Twitter and Reddit posts for bullish/bearish sentiment.

Components:
- SentimentFetcher: Fetch social media posts from Twitter and Reddit APIs
- SentimentAnalyzer: Score posts using FinBERT model
- SentimentAggregator: Aggregate sentiment scores with recency weighting
- Models: SentimentPost and SentimentScore dataclasses
"""

__version__ = "1.0.0"

__all__ = [
    "SentimentFetcher",
    "SentimentAnalyzer",
    "SentimentAggregator",
    "SentimentPost",
    "SentimentScore",
]
