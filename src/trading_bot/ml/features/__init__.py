"""Feature extraction pipeline for ML models.

Converts raw market data into 55-dimensional feature vectors:
- Price features (10): Returns, volatility, volume ratios
- Technical indicators (15): RSI, MACD, Bollinger Bands, etc.
- Market microstructure (5): Bid-ask spread, order flow, VWAP
- Sentiment (3): News, social media, options
- Time features (4): Hour, day, earnings proximity
- Pattern features (8): Support/resistance, trends, breakouts

All features are normalized to [-1, 1] for model stability.
"""

from trading_bot.ml.features.extractor import FeatureExtractor
from trading_bot.ml.features.technical import TechnicalFeatureCalculator
from trading_bot.ml.features.patterns import PatternFeatureCalculator
from trading_bot.ml.features.sentiment import SentimentFeatureCalculator
from trading_bot.ml.features.microstructure import MicrostructureFeatureCalculator

__all__ = [
    "FeatureExtractor",
    "TechnicalFeatureCalculator",
    "PatternFeatureCalculator",
    "SentimentFeatureCalculator",
    "MicrostructureFeatureCalculator",
]
