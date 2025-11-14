"""Ensemble learning for hierarchical signal stacking.

Phase 3 of the ML enhancement roadmap: combines multiple diverse base models
using XGBoost meta-learning for 15-25% additional performance improvement.
"""

from trading_bot.ml.ensemble.base_models import (
    BaseModel,
    LSTMModel,
    GRUModel,
    TransformerModel,
)
from trading_bot.ml.ensemble.meta_learner import MetaLearner, StackingEnsemble
from trading_bot.ml.ensemble.training import EnsembleTrainer

__all__ = [
    "BaseModel",
    "LSTMModel",
    "GRUModel",
    "TransformerModel",
    "MetaLearner",
    "StackingEnsemble",
    "EnsembleTrainer",
]
