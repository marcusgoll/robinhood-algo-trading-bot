"""ML-based trading strategy generation and execution.

This module provides automated strategy generation using:
- Genetic Programming (GP) for rule evolution
- Reinforcement Learning (RL) for adaptive strategies
- LLM-guided rule generation for interpretable strategies

Architecture:
    ml/
    ├── models.py              # Data models
    ├── config.py              # Configuration
    ├── features/              # Feature extraction
    ├── generators/            # Strategy generators (GP, RL, LLM)
    ├── backtesting/           # Enhanced backtesting
    ├── selection/             # Strategy selection & ensemble
    ├── execution/             # Live execution orchestration
    └── monitoring/            # Performance tracking
"""

__version__ = "1.0.0"

from trading_bot.ml.models import (
    MLStrategy,
    StrategyType,
    StrategyMetrics,
    StrategyGene,
    FeatureSet,
)
from trading_bot.ml.config import MLConfig

__all__ = [
    "MLStrategy",
    "StrategyType",
    "StrategyMetrics",
    "StrategyGene",
    "FeatureSet",
    "MLConfig",
]
