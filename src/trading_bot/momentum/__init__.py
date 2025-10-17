"""
Momentum and Catalyst Detection Module

Provides momentum detection services for identifying high-probability trading opportunities
through catalyst events, pre-market movers, and chart patterns.

Main components:
- MomentumConfig: Configuration dataclass
- MomentumSignal: Base signal dataclass (to be implemented)
- CatalystDetector: News catalyst detection (to be implemented)
- PreMarketScanner: Pre-market momentum scanner (to be implemented)
- BullFlagDetector: Bull flag pattern detector (to be implemented)
"""

from .config import MomentumConfig

__all__ = ["MomentumConfig"]
