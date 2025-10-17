"""
Trading Patterns Module

Provides chart pattern detection and analysis for trading strategies.
Constitution v1.0.0: Support for bull flag and other technical patterns.
"""

from .config import BullFlagConfig
from .exceptions import InvalidConfigurationError, PatternNotFoundError

__all__ = [
    "BullFlagConfig",
    "InvalidConfigurationError",
    "PatternNotFoundError",
]
