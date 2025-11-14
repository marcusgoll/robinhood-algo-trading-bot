"""Strategy validation orchestrator."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import pandas as pd

from trading_bot.ml.backtesting.walk_forward import (
    WalkForwardOptimizer,
    WalkForwardResult,
)
from trading_bot.ml.config import BacktestConfig
from trading_bot.ml.models import MLStrategy, StrategyMetrics, StrategyStatus

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Complete strategy validation result.

    Attributes:
        strategy: Validated strategy
        backtest_metrics: Simple backtest metrics
        walk_forward_result: Walk-forward validation result
        passed: True if strategy passes all checks
        failure_reasons: List of failure reasons (if any)
    """

    strategy: MLStrategy
    backtest_metrics: StrategyMetrics
    walk_forward_result: WalkForwardResult
    passed: bool
    failure_reasons: list[str]


class StrategyValidator:
    """Validate ML-generated strategies.

    Multi-stage validation:
    1. Simple backtest on full dataset
    2. Walk-forward out-of-sample validation
    3. Minimum threshold checks
    4. Overfitting detection

    Usage:
        ```python
        validator = StrategyValidator(config)
        result = validator.validate(strategy, historical_data)

        if result.passed:
            strategy.status = StrategyStatus.VALIDATED
        ```
    """

    def __init__(self, config: BacktestConfig) -> None:
        """Initialize validator.

        Args:
            config: Backtest configuration
        """
        self.config = config
        self.wf_optimizer = WalkForwardOptimizer(config)

    def simple_backtest(
        self, strategy: MLStrategy, data: pd.DataFrame
    ) -> StrategyMetrics:
        """Run simple backtest on full dataset.

        Args:
            strategy: Strategy to test
            data: Historical OHLCV data

        Returns:
            Performance metrics
        """
        # TODO: Integrate with existing backtest engine
        # For now, use walk-forward backtest method
        return self.wf_optimizer.backtest_strategy(strategy, data)

    def validate(
        self, strategy: MLStrategy, historical_data: pd.DataFrame
    ) -> ValidationResult:
        """Perform complete strategy validation.

        Args:
            strategy: Strategy to validate
            historical_data: Historical OHLCV data

        Returns:
            Validation result
        """
        logger.info(f"Validating strategy: {strategy.name}")

        failure_reasons = []

        # Stage 1: Simple backtest
        backtest_metrics = self.simple_backtest(strategy, historical_data)

        # Check minimum trades
        if backtest_metrics.num_trades < self.config.min_trades_required:
            failure_reasons.append(
                f"Insufficient trades: {backtest_metrics.num_trades} < {self.config.min_trades_required}"
            )

        # Check minimum thresholds
        if not backtest_metrics.is_production_ready():
            failure_reasons.append(
                f"Failed production readiness checks: "
                f"Sharpe={backtest_metrics.sharpe_ratio:.2f}, "
                f"MaxDD={backtest_metrics.max_drawdown:.1%}, "
                f"WinRate={backtest_metrics.win_rate:.1%}"
            )

        # Stage 2: Walk-forward validation
        wf_result = self.wf_optimizer.validate(strategy, historical_data)

        # Check for overfitting
        if wf_result.is_overfit:
            failure_reasons.append(
                f"Strategy appears overfit: "
                f"Train Sharpe={wf_result.avg_train_sharpe:.2f}, "
                f"Test Sharpe={wf_result.avg_test_sharpe:.2f}"
            )

        # Check degradation
        if wf_result.avg_degradation_pct > 50:
            failure_reasons.append(
                f"High performance degradation: {wf_result.avg_degradation_pct:.1f}%"
            )

        # Update strategy status
        passed = len(failure_reasons) == 0

        if passed:
            strategy.status = StrategyStatus.VALIDATED
            strategy.backtest_metrics = backtest_metrics
            strategy.forward_test_metrics = StrategyMetrics(
                sharpe_ratio=wf_result.avg_test_sharpe,
                # TODO: Aggregate other metrics from WF windows
            )
            logger.info(f"Strategy {strategy.name} PASSED validation")
        else:
            strategy.status = StrategyStatus.FAILED
            logger.warning(
                f"Strategy {strategy.name} FAILED validation: {', '.join(failure_reasons)}"
            )

        result = ValidationResult(
            strategy=strategy,
            backtest_metrics=backtest_metrics,
            walk_forward_result=wf_result,
            passed=passed,
            failure_reasons=failure_reasons,
        )

        return result

    def batch_validate(
        self,
        strategies: list[MLStrategy],
        historical_data: pd.DataFrame,
    ) -> list[ValidationResult]:
        """Validate multiple strategies.

        Args:
            strategies: List of strategies
            historical_data: Historical data

        Returns:
            List of validation results
        """
        logger.info(f"Batch validating {len(strategies)} strategies")

        results = []
        for strategy in strategies:
            result = self.validate(strategy, historical_data)
            results.append(result)

        passed_count = sum(1 for r in results if r.passed)
        logger.info(f"Validation complete: {passed_count}/{len(strategies)} passed")

        return results
