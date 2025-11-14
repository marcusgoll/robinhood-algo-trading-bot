"""
LLM Integration Module for Trading Bot

Provides dual LLM integration:

**OpenAI API** (legacy):
- Pre-trade signal validation and confidence scoring
- Strategy optimization based on historical performance
- Risk assessment for position sizing
- Performance insights generation

**Claude Code Headless** (primary):
- Subprocess CLI invocation of Claude Code
- Pre-market stock screening
- Trade analysis and pattern recognition
- Position optimization
- Performance review and strategy adjustment
- Uses Claude Haiku 4.5 for fast, cost-effective operations

Features:
- Rate limiting to respect API limits
- Response caching to minimize costs
- Budget tracking and alerting
- Graceful degradation if LLM unavailable
- JSONL logging of all LLM calls

Usage (Claude Code):
    from trading_bot.llm import ClaudeCodeManager, LLMConfig

    config = LLMConfig(daily_budget_usd=5.0, model="haiku")
    manager = ClaudeCodeManager(config)

    result = manager.screen_stocks()
    if result.success:
        symbols = result.data["symbols"]
        # Process symbols...

Usage (OpenAI - legacy):
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

Constitution v1.0.0 - §Security: API keys from environment only, subprocess sandboxing
"""

from .openai_client import OpenAIClient
from .trade_analyzer import TradeAnalyzer, TradeAnalysisResult
from .rate_limiter import RateLimiter
from .claude_manager import (
    ClaudeCodeManager,
    LLMConfig,
    LLMResponse,
    LLMModel,
    BudgetExceededError
)

__all__ = [
    # OpenAI (legacy)
    "OpenAIClient",
    "TradeAnalyzer",
    "TradeAnalysisResult",
    "RateLimiter",
    # Claude Code (primary)
    "ClaudeCodeManager",
    "LLMConfig",
    "LLMResponse",
    "LLMModel",
    "BudgetExceededError",
]
