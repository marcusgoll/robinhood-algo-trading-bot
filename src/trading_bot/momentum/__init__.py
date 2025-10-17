"""
Momentum and Catalyst Detection Module

Provides momentum detection services for identifying high-probability trading opportunities
through catalyst events, pre-market movers, and chart patterns.

Main components:
- MomentumConfig: Configuration dataclass
- MomentumEngine: Composition root orchestrating all detectors
- CatalystDetector: News catalyst detection
- PreMarketScanner: Pre-market momentum scanner
- BullFlagDetector: Bull flag pattern detector
- MomentumRanker: Signal aggregation and ranking
"""

import asyncio
import logging
from typing import List

from ..market_data.market_data_service import MarketDataService
from .bull_flag_detector import BullFlagDetector
from .catalyst_detector import CatalystDetector
from .config import MomentumConfig
from .logging.momentum_logger import MomentumLogger
from .momentum_ranker import MomentumRanker
from .premarket_scanner import PreMarketScanner
from .schemas.momentum_signal import MomentumSignal

logger = logging.getLogger(__name__)

__all__ = ["MomentumConfig", "MomentumEngine"]


class MomentumEngine:
    """Main entry point orchestrating all momentum detection services.

    Composition root pattern that creates and manages all detector instances,
    executes parallel scanning, and ranks results by composite strength.

    Features:
    - Parallel execution of all detectors via asyncio.gather()
    - Graceful degradation if individual detectors fail
    - Composite signal ranking (catalyst 25%, premarket 35%, pattern 40%)
    - Comprehensive logging of scan lifecycle events

    Example:
        >>> config = MomentumConfig.from_env()
        >>> market_data = MarketDataService(...)
        >>> engine = MomentumEngine(config, market_data)
        >>> signals = await engine.scan(["AAPL", "GOOGL", "TSLA"])
        >>> for signal in signals:
        ...     print(f"{signal.symbol}: {signal.strength:.1f}")
        AAPL: 85.3
        GOOGL: 78.2
    """

    def __init__(
        self,
        config: MomentumConfig,
        market_data_service: MarketDataService,
        momentum_logger: MomentumLogger | None = None
    ):
        """Initialize MomentumEngine with all detector dependencies.

        Args:
            config: Momentum detection configuration
            market_data_service: Service for fetching market data
            momentum_logger: Optional logger instance (creates default if None)
        """
        self.config = config
        self.market_data = market_data_service
        self.logger = momentum_logger or MomentumLogger()

        # Create detector instances
        self.catalyst_detector = CatalystDetector(config, self.logger)
        self.premarket_scanner = PreMarketScanner(config, market_data_service, self.logger)
        self.bull_flag_detector = BullFlagDetector(config, market_data_service, self.logger)
        self.ranker = MomentumRanker(config, self.logger)

        logger.info("MomentumEngine initialized with all detectors")

    async def scan(self, symbols: List[str]) -> List[MomentumSignal]:
        """Execute all detection methods and rank results.

        Runs catalyst, premarket, and pattern detectors in parallel using
        asyncio.gather() for optimal performance. Aggregates signals and
        ranks by composite strength.

        Args:
            symbols: List of stock ticker symbols to scan (e.g., ["AAPL", "GOOGL"])

        Returns:
            List of MomentumSignal objects sorted by composite strength (descending)
            Empty list if all detectors fail or no signals detected

        Example:
            >>> engine = MomentumEngine(config, market_data)
            >>> signals = await engine.scan(["AAPL", "MSFT"])
            >>> len(signals) > 0
            True
        """
        # Log scan start
        self.logger.log_scan_event("scan_started", {
            "symbols": symbols,
            "symbol_count": len(symbols)
        })

        try:
            # Execute all detectors in parallel
            tasks = [
                self.catalyst_detector.scan(symbols),
                self.premarket_scanner.scan(symbols),
                self.bull_flag_detector.scan(symbols),
            ]

            catalyst_signals, premarket_signals, pattern_signals = await asyncio.gather(
                *tasks, return_exceptions=True
            )

            # Handle exceptions from individual detectors (graceful degradation)
            all_signals = []

            if isinstance(catalyst_signals, Exception):
                logger.warning(f"CatalystDetector failed: {catalyst_signals}")
                self.logger.log_error(catalyst_signals, {"detector": "CatalystDetector"})
                catalyst_signals = []
            all_signals.extend(catalyst_signals)

            if isinstance(premarket_signals, Exception):
                logger.warning(f"PreMarketScanner failed: {premarket_signals}")
                self.logger.log_error(premarket_signals, {"detector": "PreMarketScanner"})
                premarket_signals = []
            all_signals.extend(premarket_signals)

            if isinstance(pattern_signals, Exception):
                logger.warning(f"BullFlagDetector failed: {pattern_signals}")
                self.logger.log_error(pattern_signals, {"detector": "BullFlagDetector"})
                pattern_signals = []
            all_signals.extend(pattern_signals)

            # Rank signals by composite strength
            ranked_signals = self.ranker.rank(all_signals)

            # Log scan completion
            self.logger.log_scan_event("scan_completed", {
                "symbols": symbols,
                "signal_count": len(ranked_signals),
                "catalyst_count": len(catalyst_signals) if not isinstance(catalyst_signals, Exception) else 0,
                "premarket_count": len(premarket_signals) if not isinstance(premarket_signals, Exception) else 0,
                "pattern_count": len(pattern_signals) if not isinstance(pattern_signals, Exception) else 0
            })

            logger.info(f"Scan completed: {len(ranked_signals)} signals detected for {len(symbols)} symbols")

            return ranked_signals

        except Exception as e:
            # Unexpected error during scan orchestration
            logger.error(f"Scan failed with unexpected error: {e}")
            self.logger.log_error(e, {
                "detector": "MomentumEngine",
                "symbols": symbols
            })
            return []
