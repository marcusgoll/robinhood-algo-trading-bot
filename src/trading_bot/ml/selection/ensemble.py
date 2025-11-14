"""Ensemble creation and weighting."""

from __future__ import annotations

import logging

import numpy as np
from numpy.typing import NDArray

from trading_bot.ml.config import SelectionConfig
from trading_bot.ml.models import MLStrategy, StrategyEnsemble, StrategyType

logger = logging.getLogger(__name__)


class EnsembleBuilder:
    """Build strategy ensembles with optimal weighting.

    Weight calculation methods:
    - equal: Equal weights (1/N)
    - performance: Weight by Sharpe ratio
    - kelly: Kelly criterion optimal weights
    - inverse_volatility: Weight by inverse volatility
    - risk_parity: Risk parity allocation

    Usage:
        ```python
        builder = EnsembleBuilder(config)
        ensemble = builder.create_ensemble(
            strategies,
            method='kelly'
        )
        ```
    """

    def __init__(self, config: SelectionConfig) -> None:
        """Initialize ensemble builder.

        Args:
            config: Selection configuration
        """
        self.config = config

    def calculate_equal_weights(self, n_strategies: int) -> list[float]:
        """Equal weight allocation.

        Args:
            n_strategies: Number of strategies

        Returns:
            List of equal weights (1/N each)
        """
        return [1.0 / n_strategies] * n_strategies

    def calculate_performance_weights(
        self, strategies: list[MLStrategy]
    ) -> list[float]:
        """Weight by Sharpe ratio.

        Args:
            strategies: List of strategies

        Returns:
            List of weights (sum to 1.0)
        """
        sharpe_ratios = [
            max(s.forward_test_metrics.sharpe_ratio, 0.0) for s in strategies
        ]

        total_sharpe = sum(sharpe_ratios)

        if total_sharpe == 0:
            return self.calculate_equal_weights(len(strategies))

        weights = [sharpe / total_sharpe for sharpe in sharpe_ratios]

        return weights

    def calculate_kelly_weights(
        self,
        strategies: list[MLStrategy],
        correlation_matrix: NDArray[np.float64] | None = None,
    ) -> list[float]:
        """Calculate Kelly criterion weights.

        For single strategy: f* = (p*b - q) / b
        where p=win rate, q=loss rate, b=avg win/loss ratio

        For portfolio: Use simplified approximation based on Sharpe ratios.

        Args:
            strategies: List of strategies
            correlation_matrix: Optional correlation matrix

        Returns:
            List of Kelly weights (sum to 1.0)
        """
        kelly_fractions = []

        for strategy in strategies:
            metrics = strategy.forward_test_metrics

            win_rate = metrics.win_rate
            loss_rate = 1.0 - win_rate
            win_loss_ratio = metrics.avg_win_loss_ratio

            # Kelly criterion
            if win_loss_ratio > 0:
                kelly = (win_rate * win_loss_ratio - loss_rate) / win_loss_ratio
            else:
                kelly = 0.0

            # Apply fractional Kelly (25% to be conservative)
            kelly_fractions.append(max(kelly * 0.25, 0.0))

        # Normalize to sum to 1.0
        total = sum(kelly_fractions)

        if total == 0:
            return self.calculate_equal_weights(len(strategies))

        weights = [k / total for k in kelly_fractions]

        # Cap individual weights at 30% (diversification)
        weights = [min(w, 0.30) for w in weights]

        # Renormalize
        total = sum(weights)
        weights = [w / total for w in weights]

        return weights

    def calculate_inverse_volatility_weights(
        self, strategies: list[MLStrategy]
    ) -> list[float]:
        """Weight by inverse volatility.

        Lower volatility strategies get higher weight.

        Args:
            strategies: List of strategies

        Returns:
            List of weights (sum to 1.0)
        """
        volatilities = []

        for strategy in strategies:
            # Use max drawdown as proxy for volatility
            vol = max(strategy.forward_test_metrics.max_drawdown, 0.01)
            volatilities.append(vol)

        # Inverse weights
        inverse_vols = [1.0 / vol for vol in volatilities]

        total = sum(inverse_vols)

        if total == 0:
            return self.calculate_equal_weights(len(strategies))

        weights = [inv / total for inv in inverse_vols]

        return weights

    def calculate_risk_parity_weights(
        self, strategies: list[MLStrategy]
    ) -> list[float]:
        """Risk parity allocation.

        Each strategy contributes equally to portfolio risk.

        Args:
            strategies: List of strategies

        Returns:
            List of weights (sum to 1.0)
        """
        # Simplified risk parity using drawdown as risk measure
        drawdowns = [
            max(s.forward_test_metrics.max_drawdown, 0.01) for s in strategies
        ]

        # Target equal risk contribution
        inverse_dd = [1.0 / dd for dd in drawdowns]

        total = sum(inverse_dd)
        weights = [inv / total for inv in inverse_dd]

        return weights

    def calculate_weights(
        self,
        strategies: list[MLStrategy],
        method: str,
        correlation_matrix: NDArray[np.float64] | None = None,
    ) -> list[float]:
        """Calculate ensemble weights using specified method.

        Args:
            strategies: List of strategies
            method: Weight calculation method
            correlation_matrix: Optional correlation matrix

        Returns:
            List of weights (sum to 1.0)
        """
        logger.info(f"Calculating ensemble weights using method: {method}")

        if method == "equal":
            weights = self.calculate_equal_weights(len(strategies))
        elif method == "performance":
            weights = self.calculate_performance_weights(strategies)
        elif method == "kelly":
            weights = self.calculate_kelly_weights(strategies, correlation_matrix)
        elif method == "inverse_volatility":
            weights = self.calculate_inverse_volatility_weights(strategies)
        elif method == "risk_parity":
            weights = self.calculate_risk_parity_weights(strategies)
        else:
            logger.warning(f"Unknown method: {method}, defaulting to equal")
            weights = self.calculate_equal_weights(len(strategies))

        # Validate weights
        assert len(weights) == len(strategies)
        assert abs(sum(weights) - 1.0) < 0.01, f"Weights sum to {sum(weights)}"

        logger.info(f"Calculated weights: {[f'{w:.3f}' for w in weights]}")

        return weights

    def create_ensemble(
        self,
        strategies: list[MLStrategy],
        name: str = "Default_Ensemble",
        method: str | None = None,
        correlation_matrix: NDArray[np.float64] | None = None,
    ) -> StrategyEnsemble:
        """Create strategy ensemble with optimal weights.

        Args:
            strategies: Strategies to include in ensemble
            name: Ensemble name
            method: Weight calculation method (uses config if None)
            correlation_matrix: Optional correlation matrix

        Returns:
            StrategyEnsemble instance
        """
        if len(strategies) == 0:
            raise ValueError("Cannot create ensemble from empty strategy list")

        # Use config method if not specified
        if method is None:
            method = self.config.weight_calculation

        # Calculate weights
        weights = self.calculate_weights(strategies, method, correlation_matrix)

        # Create ensemble
        ensemble = StrategyEnsemble(
            name=name,
            strategies=strategies,
            weights=weights,
            aggregation_method=self.config.ensemble_method,
        )

        # Calculate ensemble metrics (weighted average of individual metrics)
        ensemble.metrics.sharpe_ratio = sum(
            s.forward_test_metrics.sharpe_ratio * w
            for s, w in zip(strategies, weights)
        )

        ensemble.metrics.max_drawdown = max(
            s.forward_test_metrics.max_drawdown for s in strategies
        )

        ensemble.metrics.win_rate = sum(
            s.forward_test_metrics.win_rate * w for s, w in zip(strategies, weights)
        )

        ensemble.metrics.profit_factor = sum(
            s.forward_test_metrics.profit_factor * w
            for s, w in zip(strategies, weights)
        )

        logger.info(
            f"Created ensemble '{name}' with {len(strategies)} strategies: "
            f"Sharpe={ensemble.metrics.sharpe_ratio:.2f}, "
            f"MaxDD={ensemble.metrics.max_drawdown:.1%}"
        )

        return ensemble

    def create_multi_ensembles(
        self,
        strategies: list[MLStrategy],
        n_ensembles: int = 3,
    ) -> list[StrategyEnsemble]:
        """Create multiple ensembles with different methods.

        Creates ensembles using different weighting schemes for comparison.

        Args:
            strategies: Pool of strategies
            n_ensembles: Number of ensembles to create

        Returns:
            List of ensembles
        """
        methods = [
            "equal",
            "performance",
            "kelly",
            "inverse_volatility",
            "risk_parity",
        ]

        ensembles = []

        for i in range(min(n_ensembles, len(methods))):
            method = methods[i]
            ensemble = self.create_ensemble(
                strategies, name=f"Ensemble_{method}", method=method
            )
            ensembles.append(ensemble)

        logger.info(f"Created {len(ensembles)} ensembles with different methods")

        return ensembles
