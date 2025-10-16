"""Pullback detection and analysis logic."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from trading_bot.risk_management.models import PullbackData

logger = logging.getLogger(__name__)


class PullbackAnalyzer:
    """Detects and analyzes price pullbacks for entry timing."""

    def __init__(self, pullback_threshold_pct: float = 5.0) -> None:
        """Initialize pullback analyzer.

        Args:
            pullback_threshold_pct: Minimum pullback percentage to detect
        """
        self.pullback_threshold_pct = pullback_threshold_pct

    def is_pullback(self, current_price: Decimal, recent_high: Decimal) -> bool:
        """Check if current price represents a pullback from recent high.

        Args:
            current_price: Current market price
            recent_high: Recent high price for comparison

        Returns:
            True if pullback exceeds threshold
        """
        if recent_high == 0:
            return False

        pullback_pct = float((recent_high - current_price) / recent_high * 100)
        return pullback_pct >= self.pullback_threshold_pct

    def calculate_pullback_pct(
        self, current_price: Decimal, recent_high: Decimal
    ) -> float:
        """Calculate pullback percentage from recent high.

        Args:
            current_price: Current market price
            recent_high: Recent high price

        Returns:
            Pullback percentage (positive value)
        """
        if recent_high == 0:
            return 0.0

        return float((recent_high - current_price) / recent_high * 100)

    def analyze_pullback(
        self,
        price_data: list[dict[str, Any]],
        entry_price: Decimal,
        default_stop_pct: float,
        lookback_candles: int,
    ) -> PullbackData:
        """Analyze price data to detect swing low or fallback to default stop.

        Args:
            price_data: List of price candles with 'timestamp', 'low', 'close' keys
            entry_price: Planned entry price
            default_stop_pct: Default stop percentage (fallback)
            lookback_candles: Number of candles to analyze

        Returns:
            PullbackData with swing low or fallback stop calculation

        Algorithm:
            1. Scan price_data for swing lows (local minimums)
            2. Confirm swing low with 2+ higher lows after it
            3. If no swing low detected, use fallback:
               - pullback_price = entry_price * (1 - default_stop_pct/100)
               - fallback_used = True
        """
        # Step 1: Find swing low with confirmation
        swing_low_data = self._find_swing_low(price_data, lookback_candles)

        if swing_low_data is not None:
            # Swing low detected
            return PullbackData(
                pullback_price=swing_low_data["price"],
                pullback_timestamp=swing_low_data["timestamp"],
                confirmation_candles=swing_low_data["confirmation_candles"],
                lookback_window=lookback_candles,
                fallback_used=False,
            )

        # Step 2: No swing low detected - use fallback
        logger.warning(
            f"No pullback detected - using default {default_stop_pct}% stop"
        )
        # Use proper Decimal arithmetic to avoid floating-point precision issues
        stop_multiplier = Decimal("1") - (Decimal(str(default_stop_pct)) / Decimal("100"))
        fallback_price = entry_price * stop_multiplier

        return PullbackData(
            pullback_price=fallback_price,
            pullback_timestamp=datetime.now(UTC),
            confirmation_candles=0,
            lookback_window=lookback_candles,
            fallback_used=True,
        )

    def _find_swing_low(
        self,
        price_data: list[dict[str, Any]],
        lookback_candles: int,
    ) -> dict[str, Any] | None:
        """Find swing low with confirmation candles.

        A swing low is a local minimum where:
        1. The low is less than or equal to the previous candle (allows consolidation at bottom)
        2. The low is strictly less than the next candle (must reverse upward)
        3. At least 2 candles after have higher lows (confirmation of reversal)

        Args:
            price_data: Price candles to analyze (oldest first, newest last)
            lookback_candles: Number of candles to look back

        Returns:
            Dict with swing low data or None if not found:
            {
                'price': Decimal,
                'timestamp': datetime,
                'confirmation_candles': int
            }
        """
        if len(price_data) < 4:  # Need: prev + swing + 2 confirmation
            return None

        # Scan for swing lows (start at index 1, need prev candle)
        for i in range(1, len(price_data) - 2):  # Leave room for confirmation
            current_low = price_data[i]["low"]
            prev_low = price_data[i - 1]["low"]
            next_low = price_data[i + 1]["low"]

            # Check swing low pattern:
            # - Allow current <= prev (consolidation at bottom is okay)
            # - Require current < next (must turn upward after this candle)
            is_swing_low = current_low <= prev_low and current_low < next_low

            if not is_swing_low:
                continue

            # Count confirmation candles (higher lows after this point)
            confirmation_count = 0
            for j in range(i + 1, len(price_data)):
                if price_data[j]["low"] > current_low:
                    confirmation_count += 1
                else:
                    break  # Stop if we find a lower or equal low

            # REQUIREMENT: Need at least 2 confirmation candles
            if confirmation_count >= 2:
                return {
                    "price": Decimal(str(current_low)),
                    "timestamp": price_data[i]["timestamp"],
                    "confirmation_candles": confirmation_count,
                }

        return None
