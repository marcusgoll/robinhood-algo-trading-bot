"""Training pipeline for hierarchical stacking ensemble.

Orchestrates the two-phase training process:
1. Train base models on training data
2. Generate out-of-fold predictions and train meta-learner

Includes support for:
- PyTorch base model training with early stopping
- K-fold cross-validation for meta-features
- Model checkpointing
- Performance tracking
"""

import logging
from pathlib import Path
from typing import Optional

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from numpy.typing import NDArray

from trading_bot.ml.ensemble.base_models import BaseModel
from trading_bot.ml.ensemble.meta_learner import MetaLearner, StackingEnsemble

logger = logging.getLogger(__name__)


class FocalLoss(nn.Module):
    """Focal Loss for addressing class imbalance.

    Focuses learning on hard, misclassified examples by down-weighting
    easy examples. More aggressive than standard class weights.

    Formula: FL(p_t) = -alpha_t * (1 - p_t)^gamma * log(p_t)

    Args:
        alpha: Class weights (list of 3 floats for BUY/HOLD/SELL)
        gamma: Focusing parameter (default 2.0). Higher = more focus on hard examples
        reduction: 'mean' or 'sum'
    """

    def __init__(self, alpha: Optional[torch.Tensor] = None, gamma: float = 2.0, reduction: str = 'mean'):
        super().__init__()
        self.alpha = alpha
        self.gamma = gamma
        self.reduction = reduction

    def forward(self, inputs: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        """Compute focal loss.

        Args:
            inputs: Raw logits of shape (batch_size, num_classes)
            targets: Ground truth labels of shape (batch_size,)

        Returns:
            Focal loss value
        """
        # Get probabilities
        ce_loss = nn.functional.cross_entropy(inputs, targets, reduction='none')
        p_t = torch.exp(-ce_loss)  # p_t = probability of correct class

        # Apply focal term (1 - p_t)^gamma
        focal_term = (1 - p_t) ** self.gamma
        loss = focal_term * ce_loss

        # Apply class weights (alpha)
        if self.alpha is not None:
            alpha_t = self.alpha[targets]
            loss = alpha_t * loss

        # Reduction
        if self.reduction == 'mean':
            return loss.mean()
        elif self.reduction == 'sum':
            return loss.sum()
        else:
            return loss


class EnsembleTrainer:
    """Training coordinator for hierarchical stacking ensemble.

    Manages the full training workflow:
    - Base model training with PyTorch
    - Meta-feature generation (out-of-fold predictions)
    - Meta-learner training with XGBoost
    - Final ensemble assembly
    """

    def __init__(
        self,
        base_models: list[BaseModel],
        meta_learner: MetaLearner,
        learning_rate: float = 0.001,
        batch_size: int = 32,
        max_epochs: int = 50,
        patience: int = 10,
        device: str = "cpu",
    ):
        """Initialize ensemble trainer.

        Args:
            base_models: List of untrained base models
            meta_learner: Untrained meta-learner
            learning_rate: Learning rate for base model training
            batch_size: Batch size for base model training
            max_epochs: Maximum epochs per base model
            patience: Early stopping patience
            device: Device for PyTorch training ('cpu' or 'cuda')
        """
        self.base_models = base_models
        self.meta_learner = meta_learner
        self.learning_rate = learning_rate
        self.batch_size = batch_size
        self.max_epochs = max_epochs
        self.patience = patience
        self.device = device

        # Move models to device
        for model in self.base_models:
            model.to(device)

        # Training history
        self.training_history: dict[str, list[float]] = {
            f"model_{i}": [] for i in range(len(base_models))
        }

    def train(
        self,
        X_train: NDArray[np.float64],
        y_train: NDArray[np.int64],
        X_val: NDArray[np.float64],
        y_val: NDArray[np.int64],
    ) -> StackingEnsemble:
        """Train full ensemble using hierarchical stacking.

        Process:
        1. Train each base model on training data
        2. Generate predictions on validation data
        3. Train meta-learner on validation predictions
        4. Return complete ensemble

        Args:
            X_train: Training features of shape (n_train, 52)
            y_train: Training labels of shape (n_train,)
            X_val: Validation features of shape (n_val, 52)
            y_val: Validation labels of shape (n_val,)

        Returns:
            Trained StackingEnsemble ready for inference
        """
        logger.info("Starting ensemble training...")
        logger.info(f"  Training samples: {len(X_train)}")
        logger.info(f"  Validation samples: {len(X_val)}")
        logger.info(f"  Base models: {len(self.base_models)}")

        # Phase 1: Train base models
        logger.info("\n[Phase 1] Training base models...")
        for i, model in enumerate(self.base_models):
            model_name = model.__class__.__name__
            logger.info(f"  Training {model_name} ({i+1}/{len(self.base_models)})...")

            # Train base model
            train_loss, val_loss = self._train_base_model(
                model, X_train, y_train, X_val, y_val
            )

            # Store history
            self.training_history[f"model_{i}"] = [train_loss, val_loss]

            logger.info(
                f"    Final - Train loss: {train_loss:.4f}, Val loss: {val_loss:.4f}"
            )

        # Phase 2: Generate meta-features and train meta-learner
        logger.info("\n[Phase 2] Training meta-learner...")

        # Generate out-of-fold predictions on validation set
        meta_features_val = self._generate_meta_features(X_val)
        logger.info(
            f"  Generated meta-features: {meta_features_val.shape} (12 features from 4 models)"
        )

        # Train meta-learner
        self.meta_learner.fit(meta_features_val, y_val)
        logger.info("  Meta-learner training complete")

        # Show feature importance
        importance = self.meta_learner.get_feature_importance()
        if importance:
            logger.info("  Feature importance:")
            for name, score in sorted(importance.items(), key=lambda x: -x[1])[:5]:
                logger.info(f"    {name}: {score:.4f}")

        # Create final ensemble
        ensemble = StackingEnsemble(
            base_models=self.base_models, meta_learner=self.meta_learner
        )

        logger.info("\nEnsemble training complete!")
        return ensemble

    def _train_base_model(
        self,
        model: BaseModel,
        X_train: NDArray[np.float64],
        y_train: NDArray[np.int64],
        X_val: NDArray[np.float64],
        y_val: NDArray[np.int64],
    ) -> tuple[float, float]:
        """Train a single base model with early stopping.

        Args:
            model: Base model to train
            X_train: Training features
            y_train: Training labels
            X_val: Validation features
            y_val: Validation labels

        Returns:
            Tuple of (final_train_loss, final_val_loss)
        """
        # Setup with strong regularization (weight_decay for limited data)
        optimizer = optim.Adam(model.parameters(), lr=self.learning_rate, weight_decay=0.01)

        # Calculate class weights (inverse frequency squared for more aggressive balancing)
        class_counts = np.bincount(y_train, minlength=3)
        total = len(y_train)
        class_weights = torch.FloatTensor([
            (total / (3 * count)) ** 1.5 if count > 0 else 1.0
            for count in class_counts
        ]).to(self.device)
        logger.info(f"    Class weights (^1.5): BUY={class_weights[0]:.2f}, "
                   f"HOLD={class_weights[1]:.2f}, SELL={class_weights[2]:.2f}")

        # Use Focal Loss with gamma=3.0 for very aggressive focus on hard examples
        criterion = FocalLoss(alpha=class_weights, gamma=3.0)
        logger.info(f"    Using Focal Loss (gamma=3.0) for aggressive class balancing")

        # Convert to tensors
        X_train_t = torch.FloatTensor(X_train).to(self.device)
        y_train_t = torch.LongTensor(y_train).to(self.device)
        X_val_t = torch.FloatTensor(X_val).to(self.device)
        y_val_t = torch.LongTensor(y_val).to(self.device)

        # Early stopping
        best_val_loss = float("inf")
        patience_counter = 0
        best_state = None

        # Training loop
        for epoch in range(self.max_epochs):
            # Training phase
            model.train()
            train_loss = 0.0
            n_batches = 0

            # Mini-batch training
            for i in range(0, len(X_train_t), self.batch_size):
                batch_X = X_train_t[i : i + self.batch_size]
                batch_y = y_train_t[i : i + self.batch_size]

                optimizer.zero_grad()
                logits = model(batch_X)
                loss = criterion(logits, batch_y)
                loss.backward()
                optimizer.step()

                train_loss += loss.item()
                n_batches += 1

            train_loss /= n_batches

            # Validation phase
            model.eval()
            with torch.no_grad():
                val_logits = model(X_val_t)
                val_loss = criterion(val_logits, y_val_t).item()

            # Early stopping check
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
                best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            else:
                patience_counter += 1

            # Log progress every 10 epochs
            if (epoch + 1) % 10 == 0:
                logger.debug(
                    f"    Epoch {epoch+1}/{self.max_epochs}: "
                    f"Train={train_loss:.4f}, Val={val_loss:.4f}"
                )

            # Stop if patience exhausted
            if patience_counter >= self.patience:
                logger.debug(f"    Early stopping at epoch {epoch+1}")
                break

        # Restore best model
        if best_state is not None:
            model.load_state_dict(best_state)
            model.to(self.device)

        return train_loss, best_val_loss

    def _generate_meta_features(self, X: NDArray[np.float64]) -> NDArray[np.float64]:
        """Generate meta-features from base model predictions.

        Args:
            X: Input features of shape (n_samples, 52)

        Returns:
            Meta-features of shape (n_samples, 12)
        """
        predictions = []

        for model in self.base_models:
            model.eval()
            probs = model.predict_proba(X)
            predictions.append(probs)

        # Concatenate: (n_samples, 4 * 3) = (n_samples, 12)
        meta_features = np.hstack(predictions)

        return meta_features

    def save_ensemble(self, ensemble: StackingEnsemble, save_dir: str) -> None:
        """Save trained ensemble to disk.

        Args:
            ensemble: Trained ensemble to save
            save_dir: Directory to save models
        """
        save_path = Path(save_dir)
        save_path.mkdir(parents=True, exist_ok=True)

        # Save base models
        for i, model in enumerate(ensemble.base_models):
            model_path = save_path / f"base_model_{i}.pt"
            torch.save(model.state_dict(), model_path)
            logger.info(f"Saved {model.__class__.__name__} to {model_path}")

        # Save meta-learner (XGBoost has built-in save)
        meta_path = save_path / "meta_learner.json"
        ensemble.meta_learner.model.save_model(meta_path)
        logger.info(f"Saved meta-learner to {meta_path}")

        logger.info(f"Ensemble saved to {save_dir}")

    def load_ensemble(self, load_dir: str) -> StackingEnsemble:
        """Load trained ensemble from disk.

        Args:
            load_dir: Directory containing saved models

        Returns:
            Loaded StackingEnsemble
        """
        load_path = Path(load_dir)

        # Load base models
        for i, model in enumerate(self.base_models):
            model_path = load_path / f"base_model_{i}.pt"
            model.load_state_dict(torch.load(model_path))
            model.to(self.device)
            model.eval()
            logger.info(f"Loaded {model.__class__.__name__} from {model_path}")

        # Load meta-learner
        meta_path = load_path / "meta_learner.json"
        self.meta_learner.model.load_model(meta_path)
        logger.info(f"Loaded meta-learner from {meta_path}")

        # Create ensemble
        ensemble = StackingEnsemble(
            base_models=self.base_models, meta_learner=self.meta_learner
        )

        logger.info(f"Ensemble loaded from {load_dir}")
        return ensemble
