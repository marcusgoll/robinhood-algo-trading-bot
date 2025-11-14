"""Rule-based ensemble strategy generator.

Combines multiple rule-based strategies using weighted voting for robust signals.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

from trading_bot.ml.generators.rule_based import RuleBasedStrategy, RuleSignal
from trading_bot.ml.models import MLStrategy, StrategyMetrics, StrategyType, StrategyStatus

logger = logging.getLogger(__name__)


@dataclass
class EnsembleMember:
    """Member of the ensemble with weight."""
    strategy: RuleBasedStrategy
    weight: float
    sharpe: float


class RuleEnsembleStrategy(RuleBasedStrategy):
    """Ensemble that combines multiple rule strategies with weighted voting.

    Vote Aggregation:
    - Each member generates signals with confidence
    - Signals are weighted by member weight and confidence
    - Final signal = weighted majority vote
    - Confidence = agreement strength among members
    """

    def __init__(
        self,
        name: str,
        members: list[EnsembleMember],
        min_agreement: float = 0.6
    ):
        """Initialize ensemble.

        Args:
            name: Ensemble name
            members: List of strategies with weights
            min_agreement: Minimum agreement threshold (0-1) to generate signal
        """
        super().__init__(name)
        self.members = members
        self.min_agreement = min_agreement

        # Normalize weights
        total_weight = sum(m.weight for m in members)
        for member in members:
            member.weight /= total_weight

        # Build entry/exit logic description
        member_names = [m.strategy.name for m in members]
        self.entry_logic = f"Weighted vote from {len(members)} rules: {', '.join(member_names[:3])}..."
        self.exit_logic = "Weighted exit vote from ensemble members"

        logger.info(f"Created ensemble '{name}' with {len(members)} members")
        for m in members:
            logger.info(f"  - {m.strategy.name}: weight={m.weight:.3f}, sharpe={m.sharpe:.2f}")

    def generate_signals(self, data: pd.DataFrame) -> list[RuleSignal]:
        """Generate ensemble signals by weighted voting.

        Args:
            data: OHLCV data

        Returns:
            List of ensemble signals
        """
        # Get signals from all members
        member_signals = []
        for member in self.members:
            try:
                # Access the original RuleBasedStrategy, not the MLStrategy wrapper
                rule_strat = getattr(member.strategy, 'rule_strategy', member.strategy)
                signals = rule_strat.generate_signals(data)
                member_signals.append((member, signals))
            except Exception as e:
                logger.warning(f"Member {member.strategy.name} failed: {e}")
                continue

        if not member_signals:
            logger.error("All ensemble members failed!")
            return [RuleSignal(action=0, confidence=0.0, reason="All members failed")
                   for _ in range(len(data))]

        # Aggregate signals
        num_bars = len(data)
        ensemble_signals = []

        for i in range(num_bars):
            # Collect weighted votes
            buy_votes = 0.0
            sell_votes = 0.0
            buy_reasons = []
            sell_reasons = []

            for member, signals in member_signals:
                if i >= len(signals):
                    continue

                signal = signals[i]
                weighted_vote = member.weight * signal.confidence

                if signal.action == 1:  # Buy
                    buy_votes += weighted_vote
                    if weighted_vote > 0.1:  # Significant vote
                        buy_reasons.append(f"{member.strategy.name}")
                elif signal.action == -1:  # Sell
                    sell_votes += weighted_vote
                    if weighted_vote > 0.1:
                        sell_reasons.append(f"{member.strategy.name}")

            # Determine ensemble action
            total_votes = buy_votes + sell_votes

            if total_votes == 0:
                # No votes
                ensemble_signals.append(RuleSignal(
                    action=0,
                    confidence=0.0,
                    reason="No votes"
                ))
            elif buy_votes > sell_votes and buy_votes >= self.min_agreement:
                # Buy signal
                confidence = buy_votes
                num_agreeing = len(buy_reasons)
                reason = f"Buy: {num_agreeing}/{len(self.members)} agree ({', '.join(buy_reasons[:2])})"
                ensemble_signals.append(RuleSignal(
                    action=1,
                    confidence=confidence,
                    reason=reason
                ))
            elif sell_votes > buy_votes and sell_votes >= self.min_agreement:
                # Sell signal
                confidence = sell_votes
                num_agreeing = len(sell_reasons)
                reason = f"Sell: {num_agreeing}/{len(self.members)} agree ({', '.join(sell_reasons[:2])})"
                ensemble_signals.append(RuleSignal(
                    action=-1,
                    confidence=confidence,
                    reason=reason
                ))
            else:
                # No agreement or below threshold
                ensemble_signals.append(RuleSignal(
                    action=0,
                    confidence=0.0,
                    reason=f"No consensus (buy={buy_votes:.2f}, sell={sell_votes:.2f})"
                ))

        return ensemble_signals


class RuleEnsembleGenerator:
    """Generates ensemble strategies from top-performing rules."""

    def __init__(self):
        """Initialize generator."""
        pass

    def create_ensemble(
        self,
        strategies: list[RuleBasedStrategy],
        weighting: str = "sharpe",
        top_k: int = 5,
        min_agreement: float = 0.6
    ) -> RuleEnsembleStrategy:
        """Create ensemble from top strategies.

        Args:
            strategies: List of backtested strategies
            weighting: Weight scheme ("sharpe", "equal", "inverse_dd")
            top_k: Number of top strategies to include
            min_agreement: Minimum vote threshold

        Returns:
            Ensemble strategy
        """
        # Filter strategies with metrics
        valid_strategies = [
            s for s in strategies
            if s.backtest_metrics and s.backtest_metrics.num_trades > 0
        ]

        if not valid_strategies:
            raise ValueError("No valid strategies with backtest metrics")

        # Sort by Sharpe ratio
        sorted_strategies = sorted(
            valid_strategies,
            key=lambda s: s.backtest_metrics.sharpe_ratio,
            reverse=True
        )

        # Select top K
        top_strategies = sorted_strategies[:top_k]

        logger.info(f"Selected top {len(top_strategies)} strategies for ensemble:")
        for i, s in enumerate(top_strategies, 1):
            metrics = s.backtest_metrics
            logger.info(
                f"  {i}. {s.name}: Sharpe={metrics.sharpe_ratio:.2f}, "
                f"Trades={metrics.num_trades}, DD={metrics.max_drawdown:.1%}"
            )

        # Calculate weights
        members = []
        for strategy in top_strategies:
            metrics = strategy.backtest_metrics

            if weighting == "sharpe":
                # Weight by Sharpe ratio (positive only)
                weight = max(metrics.sharpe_ratio, 0.1)
            elif weighting == "equal":
                weight = 1.0
            elif weighting == "inverse_dd":
                # Weight by inverse drawdown (smaller DD = higher weight)
                weight = 1.0 / (abs(metrics.max_drawdown) + 0.01)
            else:
                raise ValueError(f"Unknown weighting: {weighting}")

            members.append(EnsembleMember(
                strategy=strategy,
                weight=weight,
                sharpe=metrics.sharpe_ratio
            ))

        # Create ensemble
        ensemble_name = f"Ensemble_Top{top_k}_{weighting}"
        ensemble = RuleEnsembleStrategy(
            name=ensemble_name,
            members=members,
            min_agreement=min_agreement
        )

        return ensemble

    def create_multi_timeframe_ensemble(
        self,
        strategies_by_timeframe: dict[str, list[RuleBasedStrategy]],
        weighting: str = "sharpe",
        top_k_per_tf: int = 3
    ) -> RuleEnsembleStrategy:
        """Create ensemble combining strategies across timeframes.

        Args:
            strategies_by_timeframe: Dict mapping timeframe to strategies
            weighting: Weight scheme
            top_k_per_tf: Top K strategies per timeframe

        Returns:
            Multi-timeframe ensemble
        """
        all_members = []

        for timeframe, strategies in strategies_by_timeframe.items():
            # Get top K for this timeframe
            valid = [s for s in strategies if s.backtest_metrics and s.backtest_metrics.num_trades > 0]
            sorted_strats = sorted(valid, key=lambda s: s.backtest_metrics.sharpe_ratio, reverse=True)
            top_strats = sorted_strats[:top_k_per_tf]

            # Create members with timeframe prefix
            for strategy in top_strats:
                metrics = strategy.backtest_metrics

                if weighting == "sharpe":
                    weight = max(metrics.sharpe_ratio, 0.1)
                elif weighting == "equal":
                    weight = 1.0
                else:
                    weight = 1.0 / (abs(metrics.max_drawdown) + 0.01)

                # Add timeframe to strategy name
                strategy.name = f"{timeframe}_{strategy.name}"

                all_members.append(EnsembleMember(
                    strategy=strategy,
                    weight=weight,
                    sharpe=metrics.sharpe_ratio
                ))

        if not all_members:
            raise ValueError("No valid strategies across any timeframe")

        logger.info(f"Created multi-timeframe ensemble with {len(all_members)} members across {len(strategies_by_timeframe)} timeframes")

        # Create ensemble
        ensemble = RuleEnsembleStrategy(
            name=f"MTF_Ensemble_{len(strategies_by_timeframe)}TF",
            members=all_members,
            min_agreement=0.5  # Lower threshold for multi-TF
        )

        return ensemble
