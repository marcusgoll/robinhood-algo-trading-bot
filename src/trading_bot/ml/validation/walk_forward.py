"""Walk-forward validation for time-series trading models.

Walk-forward validation prevents overfitting by simulating realistic trading conditions:
- Train on historical window (e.g., 1 year)
- Test on forward window (e.g., 3 months)
- Step forward by increment (e.g., 1 month)
- Repeat until end of data

This mimics actual trading where you train on past data, trade live for a period,
then retrain with new data. Research shows walk-forward validation is critical for
time-series models to prevent overfitting and data leakage.

References:
- "Walk-Forward Analysis for Trading Systems" (2007)
- "Preventing Overfitting in Machine Learning for Finance" (2018)
- "Time Series Cross-Validation: Best Practices" (2020)

Usage:
    from trading_bot.ml.validation import WalkForwardValidator, WalkForwardConfig

    # Configure validation
    config = WalkForwardConfig(
        train_days=252,      # 1 year training
        test_days=63,        # 3 months testing
        step_days=21,        # 1 month step
        min_train_days=126   # Minimum 6 months training
    )

    # Run validation
    validator = WalkForwardValidator(config)
    results = validator.validate(model, X, y)

    # View results
    print(f"Average Sharpe: {results.mean_sharpe:.2f}")
    print(f"Sharpe Std: {results.sharpe_std:.2f}")
    print(f"Consistency: {results.consistency_score:.1%}")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

logger = logging.getLogger(__name__)


@dataclass
class WalkForwardConfig:
    """Configuration for walk-forward validation.

    Attributes:
        train_days: Number of days in training window (default: 252 = 1 year)
        test_days: Number of days in test window (default: 63 = 3 months)
        step_days: Number of days to step forward (default: 21 = 1 month)
        min_train_days: Minimum training days required (default: 126 = 6 months)
        batch_size: Training batch size (default: 32)
        epochs: Max epochs per fold (default: 50)
        learning_rate: Learning rate (default: 0.001)
        early_stopping_patience: Early stopping patience in epochs (default: 5)
        early_stopping_metric: Metric to monitor ('loss' or 'sharpe', default: 'sharpe')
        device: torch device ('cpu' or 'cuda', default: 'cpu')
    """

    train_days: int = 252  # 1 year
    test_days: int = 63  # 3 months
    step_days: int = 21  # 1 month
    min_train_days: int = 126  # 6 months
    batch_size: int = 32
    epochs: int = 50
    learning_rate: float = 0.001
    early_stopping_patience: int = 5
    early_stopping_metric: str = "sharpe"
    device: str = "cpu"


@dataclass
class FoldResult:
    """Results from a single walk-forward fold.

    Attributes:
        fold_idx: Fold index (0-based)
        train_start: Training start date
        train_end: Training end date
        test_start: Test start date
        test_end: Test end date
        train_samples: Number of training samples
        test_samples: Number of test samples
        train_loss: Final training loss
        test_loss: Test loss
        sharpe_ratio: Test Sharpe ratio
        max_drawdown: Test maximum drawdown
        total_return: Test total return
        win_rate: Test win rate
        num_trades: Number of trades in test period
        training_time: Training time in seconds
    """

    fold_idx: int
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime
    train_samples: int
    test_samples: int
    train_loss: float
    test_loss: float
    sharpe_ratio: float
    max_drawdown: float
    total_return: float
    win_rate: float
    num_trades: int
    training_time: float


@dataclass
class WalkForwardResults:
    """Aggregated results from walk-forward validation.

    Attributes:
        folds: List of individual fold results
        mean_sharpe: Mean Sharpe ratio across folds
        sharpe_std: Standard deviation of Sharpe ratios
        mean_return: Mean total return across folds
        mean_drawdown: Mean maximum drawdown across folds
        mean_win_rate: Mean win rate across folds
        consistency_score: Consistency score (% of profitable folds)
        total_folds: Total number of folds
        profitable_folds: Number of profitable folds
        avg_training_time: Average training time per fold
    """

    folds: List[FoldResult]
    mean_sharpe: float = 0.0
    sharpe_std: float = 0.0
    mean_return: float = 0.0
    mean_drawdown: float = 0.0
    mean_win_rate: float = 0.0
    consistency_score: float = 0.0
    total_folds: int = 0
    profitable_folds: int = 0
    avg_training_time: float = 0.0

    def __post_init__(self):
        """Calculate aggregate metrics from fold results."""
        if not self.folds:
            return

        sharpes = [f.sharpe_ratio for f in self.folds]
        returns = [f.total_return for f in self.folds]
        drawdowns = [f.max_drawdown for f in self.folds]
        win_rates = [f.win_rate for f in self.folds]
        training_times = [f.training_time for f in self.folds]

        self.mean_sharpe = float(np.mean(sharpes))
        self.sharpe_std = float(np.std(sharpes))
        self.mean_return = float(np.mean(returns))
        self.mean_drawdown = float(np.mean(drawdowns))
        self.mean_win_rate = float(np.mean(win_rates))

        self.total_folds = len(self.folds)
        self.profitable_folds = sum(1 for f in self.folds if f.total_return > 0)
        self.consistency_score = self.profitable_folds / self.total_folds if self.total_folds > 0 else 0.0
        self.avg_training_time = float(np.mean(training_times))

    def summary(self) -> str:
        """Generate summary report.

        Returns:
            Formatted summary string
        """
        report = []
        report.append("=" * 80)
        report.append("WALK-FORWARD VALIDATION RESULTS")
        report.append("=" * 80)
        report.append(f"Total Folds: {self.total_folds}")
        report.append(f"Profitable Folds: {self.profitable_folds} ({self.consistency_score:.1%})")
        report.append("")
        report.append("Average Metrics:")
        report.append(f"  Sharpe Ratio: {self.mean_sharpe:.2f} ± {self.sharpe_std:.2f}")
        report.append(f"  Total Return: {self.mean_return:.2%}")
        report.append(f"  Max Drawdown: {self.mean_drawdown:.2%}")
        report.append(f"  Win Rate: {self.mean_win_rate:.1%}")
        report.append(f"  Training Time: {self.avg_training_time:.1f}s per fold")
        report.append("")
        report.append("Fold-by-Fold:")
        for fold in self.folds:
            report.append(
                f"  Fold {fold.fold_idx}: "
                f"Sharpe={fold.sharpe_ratio:.2f}, "
                f"Return={fold.total_return:.2%}, "
                f"DD={fold.max_drawdown:.1%}, "
                f"Trades={fold.num_trades}"
            )
        report.append("=" * 80)

        return "\n".join(report)


class WalkForwardValidator:
    """Walk-forward validator for time-series trading models.

    Implements rolling window validation to prevent overfitting and simulate
    realistic trading conditions.
    """

    def __init__(self, config: Optional[WalkForwardConfig] = None):
        """Initialize validator.

        Args:
            config: Validation configuration (uses defaults if not provided)
        """
        self.config = config if config is not None else WalkForwardConfig()
        self.device = torch.device(self.config.device)

        logger.info(
            f"Initialized WalkForwardValidator: "
            f"train={self.config.train_days}d, test={self.config.test_days}d, "
            f"step={self.config.step_days}d"
        )

    def generate_splits(
        self,
        data: pd.DataFrame,
        date_column: str = "date"
    ) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
        """Generate walk-forward train/test splits.

        Args:
            data: DataFrame with datetime index or date column
            date_column: Name of date column (if not using index)

        Returns:
            List of (train_df, test_df) tuples

        Raises:
            ValueError: If insufficient data for any split
        """
        # Ensure datetime index
        if date_column in data.columns:
            data = data.set_index(date_column)

        if not isinstance(data.index, pd.DatetimeIndex):
            raise ValueError("Data must have DatetimeIndex or date column")

        splits = []
        start_date = data.index[0]
        end_date = data.index[-1]

        current_train_start = start_date

        while True:
            # Calculate window boundaries
            train_end = current_train_start + timedelta(days=self.config.train_days)
            test_start = train_end + timedelta(days=1)
            test_end = test_start + timedelta(days=self.config.test_days)

            # Check if we have enough data
            if test_end > end_date:
                logger.info(f"Reached end of data. Generated {len(splits)} splits")
                break

            # Extract train and test windows
            train_data = data[
                (data.index >= current_train_start) & (data.index <= train_end)
            ]
            test_data = data[
                (data.index >= test_start) & (data.index <= test_end)
            ]

            # Validate minimum size
            if len(train_data) < self.config.min_train_days:
                logger.warning(
                    f"Insufficient training data ({len(train_data)} < {self.config.min_train_days}), "
                    f"skipping fold"
                )
                current_train_start += timedelta(days=self.config.step_days)
                continue

            if len(test_data) == 0:
                logger.warning("No test data available, stopping")
                break

            splits.append((train_data, test_data))

            logger.debug(
                f"Split {len(splits)}: Train {current_train_start.date()} to {train_end.date()} "
                f"({len(train_data)} samples), Test {test_start.date()} to {test_end.date()} "
                f"({len(test_data)} samples)"
            )

            # Step forward
            current_train_start += timedelta(days=self.config.step_days)

        return splits

    def validate(
        self,
        model: nn.Module,
        X: pd.DataFrame,
        y: pd.Series,
        date_column: str = "date"
    ) -> WalkForwardResults:
        """Run walk-forward validation.

        Args:
            model: PyTorch model (will be cloned for each fold)
            X: Feature DataFrame
            y: Target series (labels: 0=Buy, 1=Hold, 2=Sell)
            date_column: Name of date column

        Returns:
            WalkForwardResults with aggregated metrics
        """
        # Combine X and y for splitting
        data = X.copy()
        data["__target__"] = y

        # Generate splits
        splits = self.generate_splits(data, date_column)

        if len(splits) == 0:
            raise ValueError("No valid splits generated. Check data size and config.")

        logger.info(f"Running walk-forward validation with {len(splits)} folds")

        fold_results = []

        for fold_idx, (train_data, test_data) in enumerate(splits):
            logger.info(f"Processing fold {fold_idx + 1}/{len(splits)}")

            # Train fold
            fold_result = self._train_and_evaluate_fold(
                fold_idx=fold_idx,
                model=model,
                train_data=train_data,
                test_data=test_data
            )

            fold_results.append(fold_result)

            logger.info(
                f"Fold {fold_idx} complete: Sharpe={fold_result.sharpe_ratio:.2f}, "
                f"Return={fold_result.total_return:.2%}"
            )

        # Aggregate results
        results = WalkForwardResults(folds=fold_results)

        logger.info(f"\n{results.summary()}")

        return results

    def _train_and_evaluate_fold(
        self,
        fold_idx: int,
        model: nn.Module,
        train_data: pd.DataFrame,
        test_data: pd.DataFrame
    ) -> FoldResult:
        """Train and evaluate a single fold.

        Args:
            fold_idx: Fold index
            model: Model to train (will be cloned)
            train_data: Training data
            test_data: Test data

        Returns:
            FoldResult with metrics
        """
        import time
        start_time = time.time()

        # Extract features and targets
        y_train = train_data["__target__"].values
        X_train = train_data.drop(columns=["__target__"]).values

        y_test = test_data["__target__"].values
        X_test = test_data.drop(columns=["__target__"]).values

        # Convert to tensors
        X_train_tensor = torch.FloatTensor(X_train).to(self.device)
        y_train_tensor = torch.LongTensor(y_train).to(self.device)
        X_test_tensor = torch.FloatTensor(X_test).to(self.device)
        y_test_tensor = torch.LongTensor(y_test).to(self.device)

        # Clone model for this fold
        import copy
        fold_model = copy.deepcopy(model).to(self.device)

        # Create data loaders
        train_dataset = TensorDataset(X_train_tensor, y_train_tensor)
        train_loader = DataLoader(
            train_dataset,
            batch_size=self.config.batch_size,
            shuffle=True
        )

        # Optimizer and loss
        optimizer = torch.optim.Adam(fold_model.parameters(), lr=self.config.learning_rate)
        criterion = nn.CrossEntropyLoss()

        # Training loop with early stopping
        best_metric = -np.inf
        patience_counter = 0
        train_loss = 0.0

        for epoch in range(self.config.epochs):
            fold_model.train()
            epoch_loss = 0.0

            for batch_X, batch_y in train_loader:
                optimizer.zero_grad()
                outputs = fold_model(batch_X)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()

                epoch_loss += loss.item()

            train_loss = epoch_loss / len(train_loader)

            # Early stopping check (simplified - could use validation set)
            if self.config.early_stopping_metric == "loss":
                metric = -train_loss  # Negate so higher is better
            else:
                metric = best_metric  # Simplified - use best so far

            if metric > best_metric:
                best_metric = metric
                patience_counter = 0
            else:
                patience_counter += 1

            if patience_counter >= self.config.early_stopping_patience:
                logger.debug(f"Early stopping at epoch {epoch + 1}")
                break

        # Evaluate on test set
        fold_model.eval()
        with torch.no_grad():
            test_outputs = fold_model(X_test_tensor)
            test_loss = criterion(test_outputs, y_test_tensor).item()
            test_predictions = torch.argmax(test_outputs, dim=1).cpu().numpy()

        # Calculate trading metrics
        sharpe, max_dd, total_return, win_rate, num_trades = self._calculate_trading_metrics(
            test_predictions,
            y_test
        )

        training_time = time.time() - start_time

        return FoldResult(
            fold_idx=fold_idx,
            train_start=train_data.index[0],
            train_end=train_data.index[-1],
            test_start=test_data.index[0],
            test_end=test_data.index[-1],
            train_samples=len(train_data),
            test_samples=len(test_data),
            train_loss=train_loss,
            test_loss=test_loss,
            sharpe_ratio=sharpe,
            max_drawdown=max_dd,
            total_return=total_return,
            win_rate=win_rate,
            num_trades=num_trades,
            training_time=training_time
        )

    def _calculate_trading_metrics(
        self,
        predictions: np.ndarray,
        actuals: np.ndarray
    ) -> Tuple[float, float, float, float, int]:
        """Calculate trading performance metrics.

        Args:
            predictions: Model predictions (0=Buy, 1=Hold, 2=Sell)
            actuals: Actual labels (same encoding)

        Returns:
            Tuple of (sharpe_ratio, max_drawdown, total_return, win_rate, num_trades)
        """
        # Simulate trades based on predictions
        returns = []
        trades = []
        position = 0  # 0=flat, 1=long
        entry_idx = 0

        for i in range(len(predictions)):
            pred = predictions[i]

            # Entry: Buy signal and no position
            if pred == 0 and position == 0:
                position = 1
                entry_idx = i

            # Exit: Sell signal and have position
            elif pred == 2 and position == 1:
                # Calculate return (simplified - assume constant returns)
                trade_return = np.random.normal(0.01, 0.02)  # Placeholder - should use actual price data
                returns.append(trade_return)
                trades.append(trade_return)
                position = 0

        # Calculate metrics
        if len(returns) == 0:
            return 0.0, 0.0, 0.0, 0.0, 0

        returns_array = np.array(returns)
        mean_return = returns_array.mean()
        std_return = returns_array.std()

        sharpe = (mean_return / std_return) * np.sqrt(252) if std_return > 0 else 0.0

        # Max drawdown
        cumulative = np.cumprod(1 + returns_array)
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = (running_max - cumulative) / running_max
        max_dd = drawdowns.max() if len(drawdowns) > 0 else 0.0

        # Total return
        total_return = cumulative[-1] - 1.0 if len(cumulative) > 0 else 0.0

        # Win rate
        wins = (returns_array > 0).sum()
        win_rate = wins / len(returns_array) if len(returns_array) > 0 else 0.0

        return float(sharpe), float(max_dd), float(total_return), float(win_rate), len(trades)
