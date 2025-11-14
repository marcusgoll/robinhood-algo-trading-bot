"""Technical Analysis Framework for informed trading decisions.

This module provides a comprehensive technical analysis framework based on 20
quantifiable tools and concepts that work for both stocks and crypto.

Components:
-----------
1. enhanced_indicators.py - All technical indicators (RSI, MACD, ATR, BB, OBV, etc.)
2. market_structure.py - Market structure analysis (HH/HL, LH/LL detection)
3. multi_timeframe.py - Multi-timeframe trend analysis
4. regime_detector.py - Breakout vs Mean Reversion regime detection
5. pattern_detector.py - Chart patterns and consolidations
6. volume_analysis.py - Volume and order flow analysis
7. risk_calculator.py - Position sizing, R-multiples, risk management
8. ta_coordinator.py - Main coordinator orchestrating all analysis
9. trading_journal.py - Performance tracking and review

The framework is designed to be:
- Quantifiable: All signals are measurable and backtestable
- Scriptable: Pure Python, no manual interpretation needed
- Regime-aware: Adapts to trending vs ranging markets
- Risk-first: Every signal includes position sizing and stop levels
- Feedback-driven: Tracks what works and what doesn't

Example usage:
--------------
    from trading_bot.technical_analysis import TACoordinator

    ta = TACoordinator()

    # Analyze a symbol with full TA suite
    analysis = ta.analyze(
        symbol='BTCUSD',
        timeframes=['1h', '4h', '1d'],
        market_data=market_data
    )

    # Get actionable signal with risk parameters
    if analysis['signal'] == 'LONG':
        entry = analysis['entry_price']
        stop = analysis['stop_loss']
        target = analysis['take_profit']
        size = analysis['position_size']
        r_multiple = analysis['r_multiple']
"""

__version__ = "1.0.0"

from .enhanced_indicators import EnhancedIndicators
from .market_structure import MarketStructureAnalyzer
from .multi_timeframe import MultiTimeframeAnalyzer
from .regime_detector import RegimeDetector
from .pattern_detector import PatternDetector
from .volume_analysis import VolumeAnalyzer
from .risk_calculator import RiskCalculator
from .ta_coordinator import TACoordinator
from .trading_journal import TradingJournal

__all__ = [
    'EnhancedIndicators',
    'MarketStructureAnalyzer',
    'MultiTimeframeAnalyzer',
    'RegimeDetector',
    'PatternDetector',
    'VolumeAnalyzer',
    'RiskCalculator',
    'TACoordinator',
    'TradingJournal',
]
