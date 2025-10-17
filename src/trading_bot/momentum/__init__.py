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

import logging as stdlib_logging

from ..market_data.market_data_service import MarketDataService
from .bull_flag_detector import BullFlagDetector
from .catalyst_detector import CatalystDetector
from .config import MomentumConfig
from .logging.momentum_logger import MomentumLogger
from .momentum_ranker import MomentumRanker
from .premarket_scanner import PreMarketScanner
from .schemas.momentum_signal import MomentumSignal

logger = stdlib_logging.getLogger(__name__)

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
        self.ranker = MomentumRanker(
            catalyst_detector=self.catalyst_detector,
            premarket_scanner=self.premarket_scanner,
            bull_flag_detector=self.bull_flag_detector,
            momentum_logger=self.logger
        )

        stdlib_logging.info("MomentumEngine initialized with all detectors")

    async def scan(self, symbols: list[str]) -> list[MomentumSignal]:
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
            # Execute all detectors and rank via MomentumRanker
            ranked_signals = await self.ranker.scan_and_rank(symbols)

            # Log scan completion
            self.logger.log_scan_event("scan_completed", {
                "symbols": symbols,
                "signal_count": len(ranked_signals),
            })

            stdlib_logging.info(f"Scan completed: {len(ranked_signals)} signals detected for {len(symbols)} symbols")

            return ranked_signals

        except Exception as e:
            # Unexpected error during scan orchestration
            stdlib_logging.error(f"Scan failed with unexpected error: {e}")
            self.logger.log_error(e, {
                "detector": "MomentumEngine",
                "symbols": symbols
            })
            return []

    def health_check(self) -> dict:
        """Verify system dependencies and return health status.

        Checks:
        - NEWS_API_KEY configured (optional, graceful degradation if missing)
        - MarketDataService accessible (can instantiate Quote objects)
        - JSONL log directory writable (can log events)

        Returns:
            dict: Health status with structure:
                {
                    "status": "ok" | "degraded" | "error",
                    "dependencies": {
                        "news_api": "ok" | "missing" | "error",
                        "market_data": "ok" | "error",
                        "logging": "ok" | "error"
                    },
                    "warnings": [str] (optional, only if status == "degraded")
                }

        Example:
            >>> engine = MomentumEngine(config, market_data)
            >>> health = engine.health_check()
            >>> health["status"]
            'ok'
            >>> health["dependencies"]["news_api"]
            'ok'
        """
        dependencies = {}
        warnings = []
        overall_status = "ok"

        # Check 1: NEWS_API_KEY (optional - graceful degradation)
        if self.config.news_api_key:
            dependencies["news_api"] = "ok"
            stdlib_logging.debug("Health check: NEWS_API_KEY configured")
        else:
            dependencies["news_api"] = "missing"
            warnings.append("NEWS_API_KEY not configured - catalyst detection disabled")
            overall_status = "degraded"
            stdlib_logging.warning("Health check: NEWS_API_KEY missing (graceful degradation)")

        # Check 2: MarketDataService accessible
        try:
            # Test if market data service is functional
            # Simple check: verify service exists and has required methods
            if hasattr(self.market_data, 'get_quote') and hasattr(self.market_data, 'get_historical_data'):
                dependencies["market_data"] = "ok"
                stdlib_logging.debug("Health check: MarketDataService accessible")
            else:
                dependencies["market_data"] = "error"
                warnings.append("MarketDataService missing required methods")
                overall_status = "error"
                stdlib_logging.error("Health check: MarketDataService invalid")
        except Exception as e:
            dependencies["market_data"] = "error"
            warnings.append(f"MarketDataService error: {e}")
            overall_status = "error"
            stdlib_logging.error(f"Health check: MarketDataService error: {e}")

        # Check 3: Logging system writable
        try:
            # Test if logger can write events
            self.logger.log_scan_event("health_check", {"test": True})
            dependencies["logging"] = "ok"
            stdlib_logging.debug("Health check: Logging system writable")
        except Exception as e:
            dependencies["logging"] = "error"
            warnings.append(f"Logging system error: {e}")
            overall_status = "error"
            stdlib_logging.error(f"Health check: Logging error: {e}")

        # Build response
        response = {
            "status": overall_status,
            "dependencies": dependencies,
        }

        # Add warnings if any exist
        if warnings:
            response["warnings"] = warnings

        stdlib_logging.info(f"Health check completed: {overall_status}")
        return response
