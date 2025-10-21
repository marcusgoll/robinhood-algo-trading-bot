"""
Shared test fixtures for backtesting tests.

Provides reusable test strategies and configuration fixtures for orchestrator testing.
"""

import pytest
from typing import List
from datetime import datetime, timezone
from decimal import Decimal

from src.trading_bot.backtest.models import HistoricalDataBar, Position
from src.trading_bot.backtest.strategy_protocol import IStrategy


class MockStrategyAlwaysBuy:
    """
    Mock strategy that always enters positions (100% buy signal).

    Used for testing orchestrator multi-strategy execution.
    """

    def should_enter(self, bars: List[HistoricalDataBar]) -> bool:
        """Always return True to enter position."""
        return len(bars) > 0  # Enter if data available

    def should_exit(self, position: Position, bars: List[HistoricalDataBar]) -> bool:
        """Never exit positions."""
        return False


class MockStrategyAlwaysHold:
    """
    Mock strategy that never enters or exits positions (100% hold signal).

    Used for testing orchestrator multi-strategy execution with inactive strategies.
    """

    def should_enter(self, bars: List[HistoricalDataBar]) -> bool:
        """Never enter positions."""
        return False

    def should_exit(self, position: Position, bars: List[HistoricalDataBar]) -> bool:
        """Never exit positions."""
        return False


class MockStrategyMomentumBased:
    """
    Mock strategy that uses simple moving average crossover.

    Enters when price > 5-bar MA, exits when price < 5-bar MA.
    Used for testing orchestrator with realistic strategy logic.
    """

    def should_enter(self, bars: List[HistoricalDataBar]) -> bool:
        """Enter when current price is above 5-bar moving average."""
        if len(bars) < 5:
            return False  # Need at least 5 bars for MA calculation

        # Calculate 5-bar simple moving average
        ma5 = sum(bar.close for bar in bars[-5:]) / 5
        current_price = bars[-1].close

        return current_price > ma5

    def should_exit(self, position: Position, bars: List[HistoricalDataBar]) -> bool:
        """Exit when current price falls below 5-bar moving average."""
        if len(bars) < 5:
            return False  # Need at least 5 bars for MA calculation

        # Calculate 5-bar simple moving average
        ma5 = sum(bar.close for bar in bars[-5:]) / 5
        current_price = bars[-1].close

        return current_price < ma5


@pytest.fixture
def sample_strategies() -> List[IStrategy]:
    """
    Provide list of 3 test strategies for orchestrator testing.

    Returns:
        List of 3 mock strategy instances:
        - MockStrategyAlwaysBuy (aggressive)
        - MockStrategyAlwaysHold (passive)
        - MockStrategyMomentumBased (trend-following)

    Usage:
        def test_orchestrator(sample_strategies):
            orchestrator = StrategyOrchestrator(sample_strategies)
            assert len(orchestrator.strategies) == 3
    """
    return [
        MockStrategyAlwaysBuy(),
        MockStrategyAlwaysHold(),
        MockStrategyMomentumBased(),
    ]


@pytest.fixture
def sample_weights() -> dict[str, float]:
    """
    Provide valid capital allocation weights for orchestrator testing.

    Returns:
        Dictionary mapping strategy identifiers to allocation percentages.
        Weights sum to 1.0 (100% of capital allocated).

    Example allocation:
        - strategy1: 40% (0.4)
        - strategy2: 30% (0.3)
        - strategy3: 30% (0.3)

    Usage:
        def test_orchestrator_allocation(sample_weights):
            orchestrator = StrategyOrchestrator(strategies, sample_weights)
            assert sum(sample_weights.values()) == 1.0
    """
    return {
        "strategy1": 0.4,  # 40% allocation
        "strategy2": 0.3,  # 30% allocation
        "strategy3": 0.3,  # 30% allocation
    }
