"""
Daily Profit Goal Management Module

Provides profit protection automation to prevent overtrading and profit giveback.

Public API:
- DailyProfitTracker: Core tracker for profit goal management
- ProfitGoalConfig: Configuration dataclass
- DailyProfitState: State tracking dataclass
- load_profit_goal_config: Load configuration from environment/config
"""

from .config import load_profit_goal_config
from .models import DailyProfitState, ProfitGoalConfig, ProfitProtectionEvent
from .tracker import DailyProfitTracker

__all__ = [
    # Core tracker
    "DailyProfitTracker",
    # Configuration
    "ProfitGoalConfig",
    "load_profit_goal_config",
    # State models
    "DailyProfitState",
    "ProfitProtectionEvent",
]
