"""Walk-forward optimization for strategy validation.

Prevents overfitting by testing strategies on unseen data using rolling windows.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from trading_bot.ml.config import BacktestConfig
from trading_bot.ml.models import MLStrategy, StrategyMetrics

logger = logging.getLogger(__name__)


@dataclass
class WalkForwardWindow:
    """Single walk-forward window.

    Attributes:
        train_start: Training period start
        train_end: Training period end
        test_start: Test period start
        test_end: Test period end
        train_metrics: Metrics on training data
        test_metrics: Metrics on test data
        degradation_pct: Performance degradation (%)
    """

    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime
    train_metrics: StrategyMetrics
    test_metrics: StrategyMetrics
    degradation_pct: float = 0.0

    def __post_init__(self) -> None:
        """Calculate degradation percentage."""
        if self.train_metrics.sharpe_ratio > 0:
            self.degradation_pct = (
                (self.train_metrics.sharpe_ratio - self.test_metrics.sharpe_ratio)
                / self.train_metrics.sharpe_ratio
                * 100
            )


class WalkForwardOptimizer:
    """Walk-forward optimization validator.

    Implements anchored or rolling window approach:
    - Anchored: Train on growing window, test on next period
    - Rolling: Train on fixed window, test on next period

    Process:
    1. Split data into N windows
    2. For each window:
       - Train/optimize on training data
       - Test on unseen out-of-sample data
    3. Aggregate results
    4. Check for overfitting (train >> test performance)

    Usage:
        ```python
        optimizer = WalkForwardOptimizer(config)
        results = optimizer.validate(strategy, historical_data)

        if results.is_overfit:
            print("Strategy likely overfit!")
        ```
    """

    def __init__(self, config: BacktestConfig) -> None:
        """Initialize walk-forward optimizer.

        Args:
            config: Backtest configuration
        """
        self.config = config

    def create_windows(
        self,
        data: pd.DataFrame,
        window_type: str = "rolling",
    ) -> list[tuple[pd.DataFrame, pd.DataFrame]]:
        """Create walk-forward windows.

        Args:
            data: Full historical data
            window_type: 'rolling' or 'anchored'

        Returns:
            List of (train_df, test_df) tuples
        """
        n_rows = len(data)
        train_size = int(n_rows * self.config.train_test_split)
        test_size = n_rows // self.config.walk_forward_windows

        windows = []

        for i in range(self.config.walk_forward_windows):
            if window_type == "rolling":
                # Fixed-size rolling window
                train_start_idx = i * test_size
                train_end_idx = train_start_idx + train_size
            else:  # anchored
                # Growing window (anchored to start)
                train_start_idx = 0
                train_end_idx = train_size + (i * test_size)

            test_start_idx = train_end_idx
            test_end_idx = test_start_idx + test_size

            # Check bounds
            if test_end_idx > n_rows:
                break

            train_df = data.iloc[train_start_idx:train_end_idx].copy()
            test_df = data.iloc[test_start_idx:test_end_idx].copy()

            if len(train_df) > 0 and len(test_df) > 0:
                windows.append((train_df, test_df))

        logger.info(f"Created {len(windows)} walk-forward windows ({window_type})")
        return windows

    def backtest_strategy(
        self,
        strategy: MLStrategy,
        data: pd.DataFrame,
    ) -> StrategyMetrics:
        """Run backtest on strategy.

        Args:
            strategy: Strategy to test
            data: OHLCV data

        Returns:
            Performance metrics
        """
        # TODO: Integrate with existing backtest engine
        # For now, return mock metrics

        # Simulate random performance
        returns = np.random.randn(len(data)) * 0.02  # 2% daily vol
        cumulative_returns = np.cumprod(1 + returns) - 1

        sharpe = (
            np.mean(returns) / (np.std(returns) + 1e-9) * np.sqrt(252)
        )  # Annualized
        max_dd = np.min(cumulative_returns)

        metrics = StrategyMetrics(
            sharpe_ratio=float(sharpe),
            max_drawdown=float(abs(max_dd)),
            win_rate=np.random.uniform(0.45, 0.65),
            profit_factor=np.random.uniform(1.2, 2.5),
            total_return=cumulative_returns[-1] if len(cumulative_returns) > 0 else 0.0,
            num_trades=len(data) // 10,
        )

        return metrics

    def validate(
        self,
        strategy: MLStrategy,
        historical_data: pd.DataFrame,
        window_type: str = "rolling",
    ) -> WalkForwardResult:
        """Perform walk-forward validation.

        Args:
            strategy: Strategy to validate
            historical_data: Full historical OHLCV data
            window_type: 'rolling' or 'anchored'

        Returns:
            Walk-forward validation result
        """
        logger.info(f"Starting walk-forward validation: {strategy.name}")

        # Create windows
        windows = self.create_windows(historical_data, window_type)

        if len(windows) == 0:
            logger.error("No walk-forward windows created")
            return WalkForwardResult(
                strategy_id=strategy.id,
                windows=[],
                avg_train_sharpe=0.0,
                avg_test_sharpe=0.0,
                avg_degradation_pct=0.0,
                is_overfit=True,
            )

        # Test each window
        wf_windows = []
        for i, (train_df, test_df) in enumerate(windows):
            logger.info(f"Testing window {i + 1}/{len(windows)}")

            # Train metrics
            train_metrics = self.backtest_strategy(strategy, train_df)

            # Test metrics (out-of-sample)
            test_metrics = self.backtest_strategy(strategy, test_df)

            # Create window result
            wf_window = WalkForwardWindow(
                train_start=train_df.index[0].to_pydatetime()
                if isinstance(train_df.index, pd.DatetimeIndex)
                else datetime.now(),
                train_end=train_df.index[-1].to_pydatetime()
                if isinstance(train_df.index, pd.DatetimeIndex)
                else datetime.now(),
                test_start=test_df.index[0].to_pydatetime()
                if isinstance(test_df.index, pd.DatetimeIndex)
                else datetime.now(),
                test_end=test_df.index[-1].to_pydatetime()
                if isinstance(test_df.index, pd.DatetimeIndex)
                else datetime.now(),
                train_metrics=train_metrics,
                test_metrics=test_metrics,
            )

            wf_windows.append(wf_window)

        # Aggregate results
        avg_train_sharpe = np.mean([w.train_metrics.sharpe_ratio for w in wf_windows])
        avg_test_sharpe = np.mean([w.test_metrics.sharpe_ratio for w in wf_windows])
        avg_degradation_pct = np.mean([w.degradation_pct for w in wf_windows])

        # Check for overfitting
        # Rule: Test performance < 50% of train performance = likely overfit
        is_overfit = avg_test_sharpe < (avg_train_sharpe * 0.5)

        if is_overfit:
            logger.warning(
                f"Strategy {strategy.name} shows signs of overfitting: "
                f"Train Sharpe={avg_train_sharpe:.2f}, Test Sharpe={avg_test_sharpe:.2f}"
            )

        result = WalkForwardResult(
            strategy_id=strategy.id,
            windows=wf_windows,
            avg_train_sharpe=avg_train_sharpe,
            avg_test_sharpe=avg_test_sharpe,
            avg_degradation_pct=avg_degradation_pct,
            is_overfit=is_overfit,
        )

        logger.info(
            f"Walk-forward validation complete: "
            f"Avg degradation={avg_degradation_pct:.1f}%, "
            f"Overfit={is_overfit}"
        )

        return result


@dataclass
class WalkForwardResult:
    """Result of walk-forward validation.

    Attributes:
        strategy_id: Strategy UUID
        windows: List of window results
        avg_train_sharpe: Average Sharpe on training windows
        avg_test_sharpe: Average Sharpe on test windows
        avg_degradation_pct: Average performance degradation (%)
        is_overfit: True if likely overfit
    """

    strategy_id: Any  # UUID
    windows: list[WalkForwardWindow]
    avg_train_sharpe: float
    avg_test_sharpe: float
    avg_degradation_pct: float
    is_overfit: bool

    def get_consistency_score(self) -> float:
        """Calculate consistency score across windows.

        Returns:
            Score 0-100: Higher = more consistent performance
        """
        if len(self.windows) == 0:
            return 0.0

        test_sharpes = [w.test_metrics.sharpe_ratio for w in self.windows]
        sharpe_std = np.std(test_sharpes)

        # Lower std = higher consistency
        # Normalize to 0-100 scale
        consistency = max(100 - (sharpe_std * 50), 0)

        return float(consistency)

    def get_robustness_score(self) -> float:
        """Calculate robustness score.

        Combines:
        - Low degradation
        - High consistency
        - Not overfit

        Returns:
            Score 0-100
        """
        # Degradation component (0-40 points)
        degradation_score = max(40 - self.avg_degradation_pct, 0)

        # Consistency component (0-40 points)
        consistency_score = self.get_consistency_score() * 0.4

        # Overfit penalty (-20 points)
        overfit_penalty = -20 if self.is_overfit else 0

        robustness = max(degradation_score + consistency_score + overfit_penalty, 0)

        return float(robustness)
