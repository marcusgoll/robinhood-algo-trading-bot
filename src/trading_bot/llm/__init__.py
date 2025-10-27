"""
LLM Integration Module for Trading Bot

Provides OpenAI API integration for:
- Pre-trade signal validation and confidence scoring
- Strategy optimization based on historical performance
- Risk assessment for position sizing
- Performance insights generation

Features:
- Rate limiting to respect OpenAI API limits
- Response caching to minimize costs
- Budget tracking and alerting
- Graceful degradation if LLM unavailable

Usage:
    from trading_bot.llm import TradeAnalyzer

    analyzer = TradeAnalyzer()
    result = analyzer.analyze_trade_signal(
        symbol="AAPL",
        price=150.50,
        pattern="bull_flag",
        indicators={"rsi": 55, "volume_ratio": 2.5}
    )

    if result.confidence > 70:
        # Execute trade
        pass

Constitution v1.0.0 - §Security: API keys from environment only
"""

from .openai_client import OpenAIClient
from .trade_analyzer import TradeAnalyzer, TradeAnalysisResult
from .rate_limiter import RateLimiter

__all__ = [
    "OpenAIClient",
    "TradeAnalyzer",
    "TradeAnalysisResult",
    "RateLimiter",
]
