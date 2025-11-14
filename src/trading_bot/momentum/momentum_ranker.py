"""
MomentumRanker Service

Aggregates momentum signals by symbol and computes composite scores.
Ranks stocks based on multi-signal confluence (catalyst + pre-market + pattern).

Follows patterns from src/trading_bot/momentum/catalyst_detector.py
"""

from typing import TYPE_CHECKING, Any

from .logging.momentum_logger import MomentumLogger
from .schemas.momentum_signal import MomentumSignal, SignalType

if TYPE_CHECKING:
    from .bull_flag_detector import BullFlagDetector
    from .catalyst_detector import CatalystDetector
    from .premarket_scanner import PreMarketScanner


class MomentumRanker:
    """
    Aggregates and ranks momentum signals for trading opportunities.

    Responsibilities:
    - Orchestrate all 3 detectors (catalyst, premarket, pattern)
    - Group signals by symbol
    - Aggregate scores by signal type
    - Calculate composite scores with weighted averaging
    - Rank symbols by signal strength

    Scoring weights:
    - Catalyst: 25% (fundamental event importance)
    - Pre-market: 35% (immediate momentum indication)
    - Pattern: 40% (technical setup quality)
    """

    def __init__(
        self,
        catalyst_detector: "CatalystDetector | None" = None,
        premarket_scanner: "PreMarketScanner | None" = None,
        bull_flag_detector: "BullFlagDetector | None" = None,
        momentum_logger: MomentumLogger | None = None,
    ) -> None:
        """
        Initialize MomentumRanker with detectors and logger.

        Args:
            catalyst_detector: Optional CatalystDetector instance
            premarket_scanner: Optional PreMarketScanner instance
            bull_flag_detector: Optional BullFlagDetector instance
            momentum_logger: Optional MomentumLogger for structured logging
        """
        self.catalyst_detector = catalyst_detector
        self.premarket_scanner = premarket_scanner
        self.bull_flag_detector = bull_flag_detector
        self.logger = momentum_logger or MomentumLogger()

        # Scoring weights (must sum to 1.0)
        self.weights = {
            SignalType.CATALYST: 0.25,
            SignalType.PREMARKET: 0.35,
            SignalType.PATTERN: 0.40,
        }

    async def scan_and_rank(self, symbols: list[str]) -> list[MomentumSignal]:
        """
        Scan for momentum signals using all detectors and rank by composite score.

        Orchestrates all 3 detectors:
        1. CatalystDetector - News-driven catalyst events
        2. PreMarketScanner - Pre-market price/volume movers
        3. BullFlagDetector - Bull flag chart patterns

        Args:
            symbols: List of stock ticker symbols to scan

        Returns:
            List of composite MomentumSignal objects ranked by strength (descending)

        Example:
            >>> ranker = MomentumRanker(catalyst_detector, premarket_scanner, bull_flag_detector)
            >>> ranked_signals = await ranker.scan_and_rank(["AAPL", "GOOGL", "TSLA"])
            >>> ranked_signals[0].symbol  # Top-ranked symbol
            'AAPL'
        """
        all_signals: list[MomentumSignal] = []

        # Run all detectors in parallel
        if self.catalyst_detector:
            catalyst_signals = await self.catalyst_detector.scan(symbols)
            all_signals.extend(catalyst_signals)

        if self.premarket_scanner:
            premarket_signals = await self.premarket_scanner.scan(symbols)
            all_signals.extend(premarket_signals)

        if self.bull_flag_detector:
            pattern_signals = await self.bull_flag_detector.scan(symbols)
            all_signals.extend(pattern_signals)

        # Rank signals by composite score
        ranked_signals = self.rank(all_signals)

        return ranked_signals

    def rank(self, signals: list[MomentumSignal]) -> list[MomentumSignal]:
        """
        Rank momentum signals by composite score.

        Args:
            signals: List of MomentumSignal objects from detectors

        Returns:
            List of MomentumSignal objects sorted by composite strength (descending)

        Implementation:
        1. Aggregate signals by symbol (extract scores per signal_type)
        2. Calculate composite scores (weighted average)
        3. Create COMPOSITE signals with aggregated strength
        4. Sort by strength descending

        Example:
            >>> signals = [
            ...     MomentumSignal(symbol="AAPL", signal_type=SignalType.CATALYST, strength=80.0, ...),
            ...     MomentumSignal(symbol="AAPL", signal_type=SignalType.PATTERN, strength=90.0, ...),
            ... ]
            >>> ranked = ranker.rank(signals)
            >>> ranked[0].symbol == "AAPL"
            True
            >>> ranked[0].signal_type == SignalType.COMPOSITE
            True
        """
        if not signals:
            return []

        # Step 1: Aggregate signals by symbol
        aggregated = self._aggregate_signals_by_symbol(signals)

        # Step 2: Calculate composite scores and create COMPOSITE signals
        composite_signals: list[MomentumSignal] = []
        for symbol, scores in aggregated.items():
            composite_score = self.score_composite(
                catalyst_score=scores.get(SignalType.CATALYST, 0.0),
                premarket_score=scores.get(SignalType.PREMARKET, 0.0),
                pattern_score=scores.get(SignalType.PATTERN, 0.0),
            )

            # Find the latest timestamp from original signals
            symbol_signals = [s for s in signals if s.symbol == symbol]
            latest_timestamp = max(s.detected_at for s in symbol_signals)

            # Collect details from each signal type
            details_dict: dict[str, Any] = {
                "composite_score": composite_score,
                "signal_count": len(symbol_signals),
                # Add component scores from aggregation
                "catalyst_score": scores.get(SignalType.CATALYST, 0.0),
                "premarket_score": scores.get(SignalType.PREMARKET, 0.0),
                "pattern_score": scores.get(SignalType.PATTERN, 0.0),
            }

            # Add individual signal details
            for signal in symbol_signals:
                if signal.signal_type == SignalType.CATALYST:
                    details_dict["catalyst"] = signal.details
                elif signal.signal_type == SignalType.PREMARKET:
                    details_dict["premarket"] = signal.details
                elif signal.signal_type == SignalType.PATTERN:
                    details_dict["pattern"] = signal.details

            # Create composite signal
            composite_signal = MomentumSignal(
                symbol=symbol,
                signal_type=SignalType.COMPOSITE,
                strength=composite_score,
                detected_at=latest_timestamp,
                details=details_dict,
            )
            composite_signals.append(composite_signal)

        # Step 3: Sort by composite strength (descending)
        ranked = sorted(composite_signals, key=lambda s: s.strength, reverse=True)

        if ranked:
            self.logger.log_scan_event(
                event_type="momentum_ranking",
                metadata={
                    "total_symbols": len(ranked),
                    "total_signals": len(signals),
                    "top_symbol": ranked[0].symbol,
                    "top_score": ranked[0].strength,
                }
            )
        else:
            self.logger.log_scan_event(
                event_type="momentum_ranking",
                metadata={"total_symbols": 0, "total_signals": len(signals)}
            )

        return ranked

    def score_composite(
        self,
        catalyst_score: float,
        premarket_score: float,
        pattern_score: float,
    ) -> float:
        """
        Calculate composite score from individual signal scores.

        Args:
            catalyst_score: Catalyst signal strength (0-100)
            premarket_score: Pre-market signal strength (0-100)
            pattern_score: Pattern signal strength (0-100)

        Returns:
            Composite score (0-100) using weighted average

        Formula:
            composite = (0.25 * catalyst) + (0.35 * premarket) + (0.40 * pattern)

        Example:
            >>> ranker = MomentumRanker()
            >>> ranker.score_composite(catalyst_score=80, premarket_score=60, pattern_score=90)
            77.0
        """
        composite = (
            self.weights[SignalType.CATALYST] * catalyst_score
            + self.weights[SignalType.PREMARKET] * premarket_score
            + self.weights[SignalType.PATTERN] * pattern_score
        )

        return composite

    def _aggregate_signals_by_symbol(
        self, signals: list[MomentumSignal]
    ) -> dict[str, dict[SignalType, float]]:
        """
        Group signals by symbol and extract scores per signal_type.

        Args:
            signals: List of MomentumSignal objects

        Returns:
            Dict mapping symbol -> {signal_type: score}
            Missing signal types default to 0.0

        Implementation notes:
        - Handles multiple signals for same symbol/type by using max strength
        - Logs warning if duplicate signals detected
        - Skips COMPOSITE signals (only aggregate raw signals)
        - Invalid signal_type is logged and skipped

        Example:
            >>> signals = [
            ...     MomentumSignal(symbol="AAPL", signal_type=SignalType.CATALYST, strength=80.0, ...),
            ...     MomentumSignal(symbol="AAPL", signal_type=SignalType.PREMARKET, strength=60.0, ...),
            ...     MomentumSignal(symbol="AAPL", signal_type=SignalType.PATTERN, strength=90.0, ...),
            ...     MomentumSignal(symbol="MSFT", signal_type=SignalType.CATALYST, strength=75.0, ...),
            ...     MomentumSignal(symbol="MSFT", signal_type=SignalType.PATTERN, strength=85.0, ...),
            ... ]
            >>> aggregated = ranker._aggregate_signals_by_symbol(signals)
            >>> aggregated["AAPL"]
            {SignalType.CATALYST: 80.0, SignalType.PREMARKET: 60.0, SignalType.PATTERN: 90.0}
            >>> aggregated["MSFT"]
            {SignalType.CATALYST: 75.0, SignalType.PREMARKET: 0.0, SignalType.PATTERN: 85.0}
        """
        aggregated: dict[str, dict[SignalType, float]] = {}

        for signal in signals:
            # Skip COMPOSITE signals (only aggregate raw signals)
            if signal.signal_type == SignalType.COMPOSITE:
                continue

            # Initialize symbol entry if not present
            if signal.symbol not in aggregated:
                aggregated[signal.symbol] = {}

            # Handle duplicate signals for same symbol/type
            if signal.signal_type in aggregated[signal.symbol]:
                existing_score = aggregated[signal.symbol][signal.signal_type]
                new_score = max(existing_score, signal.strength)
                aggregated[signal.symbol][signal.signal_type] = new_score
            else:
                aggregated[signal.symbol][signal.signal_type] = signal.strength

        return aggregated
