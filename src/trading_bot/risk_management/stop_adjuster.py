"""Stop-loss adjustment strategies."""

from __future__ import annotations

from decimal import Decimal


class StopAdjuster:
    """Manages stop-loss adjustments including trailing stops."""

    def __init__(
        self,
        activation_pct: float = 10.0,
        trailing_distance_pct: float = 5.0,
    ) -> None:
        """Initialize stop adjuster.

        Args:
            activation_pct: Profit percentage to activate trailing stop
            trailing_distance_pct: Distance to maintain below high
        """
        self.activation_pct = activation_pct
        self.trailing_distance_pct = trailing_distance_pct

    def should_activate_trailing(
        self, entry_price: Decimal, current_price: Decimal
    ) -> bool:
        """Check if trailing stop should be activated.

        Args:
            entry_price: Original entry price
            current_price: Current market price

        Returns:
            True if profit exceeds activation threshold
        """
        if entry_price == 0:
            return False

        profit_pct = float((current_price - entry_price) / entry_price * 100)
        return profit_pct >= self.activation_pct

    def calculate_trailing_stop(
        self, highest_price: Decimal, trailing_distance_pct: float | None = None
    ) -> Decimal:
        """Calculate trailing stop price.

        Args:
            highest_price: Highest price since entry
            trailing_distance_pct: Override default trailing distance

        Returns:
            New stop-loss price
        """
        distance_pct = trailing_distance_pct or self.trailing_distance_pct
        stop_price = highest_price * Decimal(1 - distance_pct / 100)
        return stop_price

    def adjust_stop_to_breakeven(self, entry_price: Decimal) -> Decimal:
        """Move stop to break-even price.

        Args:
            entry_price: Original entry price

        Returns:
            Break-even stop price
        """
        return entry_price
