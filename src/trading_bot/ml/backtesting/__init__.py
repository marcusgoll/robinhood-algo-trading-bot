"""Enhanced backtesting with walk-forward optimization.

Extends existing backtest module with:
- Walk-forward analysis
- Out-of-sample validation
- Overfitting detection
- Multi-strategy testing
"""

from trading_bot.ml.backtesting.walk_forward import WalkForwardOptimizer
from trading_bot.ml.backtesting.validator import StrategyValidator

__all__ = [
    "WalkForwardOptimizer",
    "StrategyValidator",
]
