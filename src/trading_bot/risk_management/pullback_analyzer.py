"""Pullback detection and analysis logic."""

from __future__ import annotations

from decimal import Decimal


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
