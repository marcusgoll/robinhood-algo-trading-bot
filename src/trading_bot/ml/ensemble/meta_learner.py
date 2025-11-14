"""Meta-learner and stacking ensemble for Phase 3.

Implements XGBoost meta-learner that combines predictions from diverse base models
(LSTM, GRU, Transformer) to produce final trading signals. Uses hierarchical stacking
where base models form Layer 1 and XGBoost forms Layer 2.
"""

from typing import Optional

import numpy as np
import xgboost as xgb
from numpy.typing import NDArray

from trading_bot.ml.ensemble.base_models import BaseModel


class MetaLearner:
    """XGBoost meta-learner for combining base model predictions.

    Takes concatenated predictions from base models (12D: 4 models × 3 classes)
    and learns optimal non-linear combination strategy.

    Features:
    - Multi-class classification (BUY/HOLD/SELL)
    - Automatic feature importance tracking
    - Early stopping support
    - Probability output for downstream use
    """

    def __init__(
        self,
        n_estimators: int = 100,
        max_depth: int = 5,
        learning_rate: float = 0.1,
        subsample: float = 0.8,
        colsample_bytree: float = 0.8,
        reg_alpha: float = 0.1,
        reg_lambda: float = 1.0,
        random_state: int = 42,
    ):
        """Initialize XGBoost meta-learner.

        Args:
            n_estimators: Number of boosting rounds
            max_depth: Maximum tree depth
            learning_rate: Learning rate (eta)
            subsample: Subsample ratio of training data
            colsample_bytree: Subsample ratio of features
            reg_alpha: L1 regularization
            reg_lambda: L2 regularization
            random_state: Random seed for reproducibility
        """
        self.model = xgb.XGBClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            subsample=subsample,
            colsample_bytree=colsample_bytree,
            reg_alpha=reg_alpha,
            reg_lambda=reg_lambda,
            objective="multi:softprob",
            eval_metric="mlogloss",
            random_state=random_state,
            n_jobs=-1,  # Use all CPU cores
            verbosity=0,  # Suppress XGBoost output
        )

        self.feature_importance_: Optional[dict[str, float]] = None

    def fit(
        self,
        X: NDArray[np.float64],
        y: NDArray[np.int64],
        X_val: Optional[NDArray[np.float64]] = None,
        y_val: Optional[NDArray[np.int64]] = None,
        early_stopping_rounds: int = 10,
    ) -> "MetaLearner":
        """Train meta-learner on base model predictions.

        Args:
            X: Meta-features (base model predictions) of shape (n_samples, 12)
            y: Target labels of shape (n_samples,)
            X_val: Validation meta-features (optional)
            y_val: Validation labels (optional)
            early_stopping_rounds: Stop if validation metric doesn't improve

        Returns:
            Self for chaining
        """
        if X_val is not None and y_val is not None:
            eval_set = [(X_val, y_val)]
            self.model.fit(
                X,
                y,
                eval_set=eval_set,
                verbose=False,
            )
        else:
            self.model.fit(X, y, verbose=False)

        # Extract feature importance
        self._compute_feature_importance()

        return self

    def predict(self, X: NDArray[np.float64]) -> NDArray[np.int64]:
        """Predict class labels.

        Args:
            X: Meta-features of shape (n_samples, 12)

        Returns:
            Predicted class labels of shape (n_samples,)
        """
        return self.model.predict(X)

    def predict_proba(self, X: NDArray[np.float64]) -> NDArray[np.float64]:
        """Predict class probabilities.

        Args:
            X: Meta-features of shape (n_samples, 12)

        Returns:
            Class probabilities of shape (n_samples, 3)
        """
        return self.model.predict_proba(X)

    def _compute_feature_importance(self) -> None:
        """Compute feature importance from trained model.

        Maps feature indices to base model names for interpretability.
        """
        # Get raw feature importance
        importances = self.model.feature_importances_

        # Map to base model names
        # Features: [LSTM_0, LSTM_1, LSTM_2, GRU_0, GRU_1, GRU_2,
        #            Transformer_0, Transformer_1, Transformer_2,
        #            HTF_0, HTF_1, HTF_2]
        model_names = ["LSTM", "GRU", "Transformer", "HTF"]
        class_names = ["BUY", "HOLD", "SELL"]

        self.feature_importance_ = {}
        for i, importance in enumerate(importances):
            model_idx = i // 3
            class_idx = i % 3
            feature_name = f"{model_names[model_idx]}_{class_names[class_idx]}"
            self.feature_importance_[feature_name] = float(importance)

    def get_feature_importance(self) -> Optional[dict[str, float]]:
        """Get feature importance dictionary.

        Returns:
            Dictionary mapping feature names to importance scores
        """
        return self.feature_importance_


class StackingEnsemble:
    """Hierarchical stacking ensemble combining base models with meta-learner.

    Architecture:
    - Layer 1: Base models (LSTM, GRU, Transformer, HTF)
    - Layer 2: XGBoost meta-learner

    Training process:
    1. Train base models on training data
    2. Generate out-of-fold predictions on validation data
    3. Train meta-learner on validation predictions
    4. Final ensemble: base models → meta-learner → prediction
    """

    def __init__(
        self,
        base_models: list[BaseModel],
        meta_learner: MetaLearner,
    ):
        """Initialize stacking ensemble.

        Args:
            base_models: List of trained base models (LSTM, GRU, Transformer, HTF)
            meta_learner: Trained meta-learner (XGBoost)
        """
        self.base_models = base_models
        self.meta_learner = meta_learner

    def predict(self, X: NDArray[np.float64]) -> NDArray[np.int64]:
        """Predict class labels using full ensemble.

        Args:
            X: Input features of shape (n_samples, 52)

        Returns:
            Predicted class labels of shape (n_samples,)
        """
        # Generate base model predictions
        meta_features = self._generate_meta_features(X)

        # Meta-learner prediction
        return self.meta_learner.predict(meta_features)

    def predict_proba(self, X: NDArray[np.float64]) -> NDArray[np.float64]:
        """Predict class probabilities using full ensemble.

        Args:
            X: Input features of shape (n_samples, 52)

        Returns:
            Class probabilities of shape (n_samples, 3)
        """
        # Generate base model predictions
        meta_features = self._generate_meta_features(X)

        # Meta-learner prediction
        return self.meta_learner.predict_proba(meta_features)

    def _generate_meta_features(self, X: NDArray[np.float64]) -> NDArray[np.float64]:
        """Generate meta-features from base model predictions.

        Args:
            X: Input features of shape (n_samples, 52)

        Returns:
            Meta-features of shape (n_samples, 12)
            Concatenated predictions: [LSTM_probs, GRU_probs, Transformer_probs, HTF_probs]
        """
        predictions = []

        for model in self.base_models:
            # Get probability predictions from each base model
            probs = model.predict_proba(X)  # (n_samples, 3)
            predictions.append(probs)

        # Concatenate all predictions: (n_samples, 4 * 3) = (n_samples, 12)
        meta_features = np.hstack(predictions)

        return meta_features

    def get_base_model_predictions(
        self, X: NDArray[np.float64]
    ) -> dict[str, NDArray[np.float64]]:
        """Get individual predictions from each base model (for analysis).

        Args:
            X: Input features of shape (n_samples, 52)

        Returns:
            Dictionary mapping model names to predictions
        """
        model_names = ["LSTM", "GRU", "Transformer", "HTF"]
        predictions = {}

        for name, model in zip(model_names, self.base_models):
            predictions[name] = model.predict_proba(X)

        return predictions

    def get_feature_importance(self) -> Optional[dict[str, float]]:
        """Get meta-learner feature importance.

        Shows which base model predictions are most valuable.

        Returns:
            Dictionary mapping feature names to importance scores
        """
        return self.meta_learner.get_feature_importance()
