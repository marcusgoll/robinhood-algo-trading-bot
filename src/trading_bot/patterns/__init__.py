"""
Trading Patterns Module

Provides chart pattern detection and analysis for trading strategies.

This module implements bull flag pattern detection for entry signal validation,
including multi-phase pattern recognition, risk parameter calculation, and
quality scoring.

Constitution v1.0.0: Support for bull flag and other technical patterns.

Main Components:
    - BullFlagDetector: Primary class for bull flag pattern detection
    - BullFlagConfig: Configuration for pattern detection parameters
    - BullFlagResult: Detection result with pattern metadata and risk parameters

Example:
    from trading_bot.patterns import BullFlagDetector, BullFlagConfig
    from decimal import Decimal

    # Configure detector
    config = BullFlagConfig(min_flagpole_gain=Decimal('7.0'))
    detector = BullFlagDetector(config)

    # Detect pattern
    result = detector.detect(bars, symbol='AAPL')
    if result.detected:
        print(f"Entry: {result.entry_price}, Target: {result.target_price}")
        print(f"Quality Score: {result.quality_score}/100")
"""

from .bull_flag import BullFlagDetector
from .config import BullFlagConfig
from .exceptions import InvalidConfigurationError, PatternNotFoundError
from .models import BullFlagResult, ConsolidationData, FlagpoleData

__all__ = [
    # Main detector class
    "BullFlagDetector",
    # Configuration
    "BullFlagConfig",
    # Result models
    "BullFlagResult",
    "FlagpoleData",
    "ConsolidationData",
    # Exceptions
    "InvalidConfigurationError",
    "PatternNotFoundError",
]
