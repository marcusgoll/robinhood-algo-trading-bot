"""
Backtesting engine for validating trading strategies against historical data.

This module provides event-driven backtesting functionality with:
- Historical data fetching and caching (Alpaca + Yahoo Finance)
- Protocol-based strategy interface for type-safe strategy contracts
- Performance metric calculation (returns, Sharpe ratio, drawdown, etc.)
- Report generation (markdown + JSON)
- Deterministic execution to prevent look-ahead bias

Public API exports:
    Exceptions:
        - BacktestException: Base exception for all backtest errors
        - DataQualityError: Data validation failures
        - InsufficientDataError: Not enough historical data
        - StrategyError: Strategy execution errors
    Protocols:
        - IStrategy: Strategy protocol for type-safe strategy contracts
"""

from trading_bot.backtest.engine import BacktestEngine
from trading_bot.backtest.exceptions import (
    BacktestException,
    DataQualityError,
    InsufficientDataError,
    StrategyError,
)
from trading_bot.backtest.historical_data_manager import HistoricalDataManager
from trading_bot.backtest.models import (
    BacktestConfig,
    BacktestResult,
    BacktestState,
    HistoricalDataBar,
    OrchestratorConfig,
    OrchestratorResult,
    PerformanceMetrics,
    Position,
    StrategyAllocation,
    Trade,
)
from trading_bot.backtest.performance_calculator import PerformanceCalculator
from trading_bot.backtest.report_generator import ReportGenerator
from trading_bot.backtest.strategy_protocol import IStrategy

__all__ = [
    "BacktestEngine",
    "BacktestConfig",
    "BacktestException",
    "BacktestResult",
    "BacktestState",
    "DataQualityError",
    "HistoricalDataBar",
    "HistoricalDataManager",
    "InsufficientDataError",
    "IStrategy",
    "OrchestratorConfig",
    "OrchestratorResult",
    "PerformanceCalculator",
    "PerformanceMetrics",
    "Position",
    "ReportGenerator",
    "StrategyAllocation",
    "StrategyError",
    "Trade",
]
