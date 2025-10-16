"""Target price monitoring and partial profit logic."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from .models import RiskManagementEnvelope


class TargetMonitor:
    """Monitors price targets and manages partial profit-taking."""

    def __init__(
        self,
        partial_exit_pct: float = 50.0,
        order_manager: Any | None = None,
        account_data: Any | None = None,
        logger: Any | None = None,
    ) -> None:
        """Initialize target monitor.

        Args:
            partial_exit_pct: Percentage of position to exit at first target
            order_manager: OrderManager instance for order operations
            account_data: AccountData instance for cache invalidation
            logger: Logger instance for event logging
        """
        self.partial_exit_pct = partial_exit_pct
        self.order_manager = order_manager
        self.account_data = account_data
        self.logger = logger

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

    def poll_and_handle_fills(self, envelope: RiskManagementEnvelope) -> bool:
        """Poll order statuses and handle target/stop fills.

        Implements FR-009 (target fill) and FR-010 (stop fill) from spec.md.
        When either order fills, cancels the other and invalidates account cache.

        Args:
            envelope: RiskManagementEnvelope with active position details

        Returns:
            True if position was closed (target or stop filled), False otherwise
        """
        if not self.order_manager:
            return False

        # Step 1: Poll target order status
        target_status = self.order_manager.get_order_status(envelope.target_order_id)

        # Step 2: If target filled, cancel stop order and cleanup
        if target_status["status"] == "filled":
            # Cancel stop order
            self.order_manager.cancel_order(envelope.stop_order_id)

            # Log target_hit event
            if self.logger:
                self.logger.log(
                    action="target_hit",
                    symbol=envelope.position_plan.symbol,
                    target_order_id=envelope.target_order_id,
                    stop_order_id=envelope.stop_order_id,
                    filled_quantity=target_status["filled_quantity"],
                    average_fill_price=target_status["average_fill_price"],
                )

            # Invalidate account cache
            if self.account_data:
                self.account_data.invalidate_cache()

            return True

        # Step 3: Poll stop order status
        stop_status = self.order_manager.get_order_status(envelope.stop_order_id)

        # Step 4: If stop filled, cancel target order and cleanup
        if stop_status["status"] == "filled":
            # Cancel target order
            self.order_manager.cancel_order(envelope.target_order_id)

            # Log stop_hit event
            if self.logger:
                self.logger.log(
                    action="stop_hit",
                    symbol=envelope.position_plan.symbol,
                    stop_order_id=envelope.stop_order_id,
                    target_order_id=envelope.target_order_id,
                    filled_quantity=stop_status["filled_quantity"],
                    average_fill_price=stop_status["average_fill_price"],
                )

            # Invalidate account cache
            if self.account_data:
                self.account_data.invalidate_cache()

            return True

        # Step 5: Neither filled
        return False
