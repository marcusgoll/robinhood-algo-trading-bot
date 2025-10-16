"""Target price monitoring and partial profit logic."""

from __future__ import annotations

from decimal import Decimal


class TargetMonitor:
    """Monitors price targets and manages partial profit-taking."""

    def __init__(self, partial_exit_pct: float = 50.0) -> None:
        """Initialize target monitor.

        Args:
            partial_exit_pct: Percentage of position to exit at first target
        """
        self.partial_exit_pct = partial_exit_pct

    def is_target_hit(self, current_price: Decimal, target_price: Decimal) -> bool:
        """Check if target price has been reached.

        Args:
            current_price: Current market price
            target_price: Target price

        Returns:
            True if current price meets or exceeds target
        """
        return current_price >= target_price

    def calculate_partial_exit_size(self, position_size: int) -> int:
        """Calculate shares to exit for partial profit.

        Args:
            position_size: Current position size

        Returns:
            Number of shares to sell
        """
        return int(position_size * self.partial_exit_pct / 100)

    def calculate_remaining_position(
        self, original_size: int, exit_size: int
    ) -> int:
        """Calculate remaining position after partial exit.

        Args:
            original_size: Original position size
            exit_size: Shares being sold

        Returns:
            Remaining position size
        """
        return original_size - exit_size
