"""
LLM Trading System

Autonomous trading system powered by Claude (LLM) for strategic decisions
and rule-based execution for tactical speed.

Components:
- MarketContextBuilder: Transform raw data into human-readable context
- LLMScreener: Morning watchlist generation
- RuleExecutor: Fast intraday execution
- LLMOptimizer: Evening strategy optimization
- TradingSystem: Main orchestrator

Example usage:
    from llm_trading import TradingSystem

    system = TradingSystem(
        alpaca_api_key='your_key',
        alpaca_secret_key='your_secret',
        anthropic_api_key='your_key',
        autonomy_level=1,
        paper=True
    )

    system.run_daily_cycle()
"""

from .market_context import MarketContextBuilder
from .llm_screener import LLMScreener
from .rule_executor import RuleExecutor
from .llm_optimizer import LLMOptimizer
from .main import TradingSystem

__version__ = '0.1.0'
__all__ = [
    'MarketContextBuilder',
    'LLMScreener',
    'RuleExecutor',
    'LLMOptimizer',
    'TradingSystem'
]
