#!/usr/bin/env python3
"""Rule-Based Strategy Generator

Creates simple, interpretable trading strategies using well-known technical indicators.
Unlike GP which searches for complex patterns, this uses proven rules from literature.

Usage:
    python -m trading_bot.ml.generate_strategies --generator rule_based --num-strategies 15
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from trading_bot.ml.models import (
    MLStrategy,
    StrategyGene,
    StrategyMetrics,
    StrategyStatus,
    StrategyType,
)

logger = logging.getLogger(__name__)


@dataclass
class RuleSignal:
    """Trading signal from a rule.

    Attributes:
        action: 1=buy, 0=hold, -1=sell
        confidence: 0.0-1.0 strength of signal
        reason: Human-readable explanation
    """
    action: int  # 1=buy, 0=hold, -1=sell
    confidence: float  # 0.0-1.0
    reason: str


class RuleBasedStrategy(ABC):
    """Base class for rule-based trading strategies.

    Each subclass implements a specific technical analysis rule.
    Rules are intentionally simple and interpretable.
    """

    def __init__(self, name: str):
        """Initialize rule strategy.

        Args:
            name: Strategy name (e.g., "RSI_Oversold")
        """
        self.name = name
        self.entry_logic = ""  # Will be set by subclass
        self.exit_logic = ""   # Will be set by subclass

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> list[RuleSignal]:
        """Generate trading signals from market data.

        Args:
            data: DataFrame with OHLCV + indicators

        Returns:
            List of signals (one per bar)
        """
        pass

    def backtest(self, data: pd.DataFrame) -> StrategyMetrics:
        """Backtest rule strategy.

        Args:
            data: Historical OHLCV data

        Returns:
            Performance metrics
        """
        try:
            # Generate signals
            signals = self.generate_signals(data)

            # Simulate trading
            returns = []
            trades = []
            position = 0  # 0=flat, 1=long
            entry_price = 0.0
            equity = 1.0
            peak_equity = 1.0
            max_drawdown = 0.0

            for i in range(1, len(signals)):
                signal = signals[i]
                current_price = float(data["close"].iloc[i])
                prev_price = float(data["close"].iloc[i - 1])

                # Entry: signal action = 1 and no position
                if signal.action == 1 and position == 0:
                    position = 1
                    entry_price = current_price
                    returns.append(0.0)

                # Exit: signal action = -1 and have position
                elif signal.action == -1 and position == 1:
                    trade_return = (current_price - entry_price) / entry_price
                    returns.append(trade_return)
                    trades.append(trade_return)
                    equity *= (1 + trade_return)
                    position = 0

                    # Update drawdown
                    if equity > peak_equity:
                        peak_equity = equity
                    drawdown = (peak_equity - equity) / peak_equity
                    if drawdown > max_drawdown:
                        max_drawdown = drawdown

                # Holding position
                elif position == 1:
                    bar_return = (current_price - prev_price) / prev_price
                    returns.append(bar_return)
                    equity *= (1 + bar_return)

                    # Update drawdown
                    if equity > peak_equity:
                        peak_equity = equity
                    drawdown = (peak_equity - equity) / peak_equity
                    if drawdown > max_drawdown:
                        max_drawdown = drawdown

                else:
                    returns.append(0.0)

            # Close any open position at end
            if position == 1 and len(data) > 0:
                final_price = float(data["close"].iloc[-1])
                trade_return = (final_price - entry_price) / entry_price
                trades.append(trade_return)
                equity *= (1 + trade_return)

            # Calculate metrics
            num_trades = len(trades)

            if num_trades == 0:
                return StrategyMetrics(
                    sharpe_ratio=0.0,
                    max_drawdown=0.0,
                    win_rate=0.0,
                    profit_factor=0.0,
                    num_trades=0,
                    total_return=0.0,
                )

            returns_array = np.array(returns)
            mean_return = returns_array.mean()
            std_return = returns_array.std()

            sharpe = 0.0
            if std_return > 0:
                sharpe = (mean_return / std_return) * np.sqrt(252)

            # Trade statistics
            trades_array = np.array(trades)
            winners = (trades_array > 0).sum()
            win_rate = winners / num_trades if num_trades > 0 else 0.0

            gross_wins = trades_array[trades_array > 0].sum()
            gross_losses = abs(trades_array[trades_array < 0].sum())
            profit_factor = gross_wins / gross_losses if gross_losses > 0 else 0.0

            metrics = StrategyMetrics(
                sharpe_ratio=float(sharpe),
                max_drawdown=float(max_drawdown),
                win_rate=float(win_rate),
                profit_factor=float(profit_factor),
                num_trades=int(num_trades),
                total_return=float(equity - 1.0),
            )

            return metrics

        except Exception as e:
            logger.warning(f"Backtest failed for {self.name}: {e}")
            return StrategyMetrics(
                sharpe_ratio=0.0,
                max_drawdown=0.0,
                win_rate=0.0,
                profit_factor=0.0,
                num_trades=0,
                total_return=0.0,
            )

    def to_ml_strategy(self) -> MLStrategy:
        """Convert rule to MLStrategy object.

        Returns:
            MLStrategy compatible with existing pipeline
        """
        gene = StrategyGene(
            tree=self.entry_logic,
            depth=1,  # Rules are simple by design
            num_nodes=1,
        )

        strategy = MLStrategy(
            name=self.name,
            type=StrategyType.RULE_BASED,
            status=StrategyStatus.GENERATED,
            entry_logic=self.entry_logic,
            exit_logic=self.exit_logic,
            gene=gene,
            backtest_metrics=StrategyMetrics(),  # Will be filled by backtest
            generation_config={"type": "rule_based"},
            complexity_score=0.1,  # Rules are simple
        )

        # Store reference to original rule for ensemble use
        strategy.rule_strategy = self

        return strategy


class RuleBasedGenerator:
    """Generator for rule-based strategies.

    Creates a collection of interpretable technical analysis rules.
    """

    def __init__(self):
        """Initialize generator."""
        self.rules: list[type[RuleBasedStrategy]] = []
        self._register_rules()

    def _register_rules(self):
        """Register all available rule classes."""
        # Will be populated as we create rule classes
        # For now, empty - we'll add rules in separate files
        pass

    def generate(
        self,
        num_strategies: int,
        historical_data: Any,
        config: dict[str, Any],
    ) -> list[MLStrategy]:
        """Generate rule-based strategies.

        Args:
            num_strategies: Number of strategies to generate
            historical_data: Historical market data
            config: Additional configuration

        Returns:
            List of generated strategies
        """
        logger.info(f"Generating {num_strategies} rule-based strategies")

        # Import rules from rules/ directory
        from trading_bot.ml.rules import ALL_RULES

        strategies = []

        # Create instances of each rule
        for i, rule_class in enumerate(ALL_RULES[:num_strategies]):
            rule = rule_class()

            # Backtest on historical data
            metrics = rule.backtest(historical_data)

            # Convert to MLStrategy
            strategy = rule.to_ml_strategy()
            strategy.backtest_metrics = metrics

            # Update status based on performance
            if metrics.is_production_ready():
                strategy.status = StrategyStatus.VALIDATED

            strategies.append(strategy)

            logger.info(
                f"Rule {i+1}/{len(ALL_RULES)}: {rule.name} - "
                f"Sharpe={metrics.sharpe_ratio:.2f}, "
                f"Trades={metrics.num_trades}"
            )

        logger.info(
            f"Generated {len(strategies)} rule-based strategies, "
            f"{sum(1 for s in strategies if s.status == StrategyStatus.VALIDATED)} "
            f"production-ready"
        )

        return strategies
