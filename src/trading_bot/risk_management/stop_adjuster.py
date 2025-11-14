"""Stop-loss adjustment strategies."""

from __future__ import annotations

from decimal import Decimal

from .config import RiskManagementConfig
from .models import PositionPlan


class StopAdjuster:
    """Manages stop-loss adjustments including trailing stops and ATR-based dynamic stops."""

    def __init__(
        self,
        activation_pct: float = 10.0,
        trailing_distance_pct: float = 5.0,
        config: RiskManagementConfig | None = None,
    ) -> None:
        """Initialize stop adjuster.

        Args:
            activation_pct: Profit percentage to activate trailing stop
            trailing_distance_pct: Distance to maintain below high
            config: Optional risk management config (for ATR integration)
        """
        self.activation_pct = activation_pct
        self.trailing_distance_pct = trailing_distance_pct
        self.config = config

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

    def calculate_adjustment(
        self,
        current_price: Decimal,
        position_plan: PositionPlan,
        config: RiskManagementConfig,
        current_atr: Decimal | None = None,
    ) -> tuple[Decimal, str] | None:
        """Calculate stop-loss adjustment based on current price and position progress.

        Args:
            current_price: Current market price
            position_plan: Position plan with entry, stop, and target prices
            config: Risk management configuration
            current_atr: Optional current ATR value (for dynamic ATR stop adjustment)

        Returns:
            Tuple of (new_stop_price, adjustment_reason) if adjustment needed, None otherwise

        ATR Dynamic Stop Adjustment Logic:
            1. If current_atr provided and position is ATR-based (pullback_source="atr")
            2. Calculate initial ATR from position: (entry - stop) / multiplier
            3. Check if ATR changed >threshold (default 20%)
            4. If yes, recalculate stop: current_price - (current_atr * multiplier)
            5. Compare ATR stop with breakeven/trailing stop, select widest (most protective)
        """
        # ATR Dynamic Stop Adjustment (T019)
        if (
            current_atr is not None
            and config.atr_enabled
            and position_plan.pullback_source == "atr"
        ):
            # Calculate initial ATR from position plan
            # initial_stop = entry - (initial_atr * multiplier)
            # Therefore: initial_atr = (entry - initial_stop) / multiplier
            initial_stop_distance = position_plan.entry_price - position_plan.stop_price
            initial_atr = initial_stop_distance / Decimal(str(config.atr_multiplier))

            # Check if ATR changed significantly (>threshold)
            atr_change_pct = abs(current_atr - initial_atr) / initial_atr

            if atr_change_pct >= Decimal(str(config.atr_recalc_threshold)):
                # Recalculate stop using current ATR
                new_stop_price = current_price - (
                    current_atr * Decimal(str(config.atr_multiplier))
                )

                adjustment_reason = (
                    f"ATR recalculation: ATR changed from {initial_atr:.2f} to {current_atr:.2f} "
                    f"({float(atr_change_pct * 100):.1f}% change, threshold: {config.atr_recalc_threshold * 100:.0f}%)"
                )

                return (new_stop_price, adjustment_reason)

        # Standard trailing stop logic (if ATR recalc not triggered)
        # If trailing is disabled, no adjustment
        if not config.trailing_enabled:
            return None

        # Calculate progress toward target
        # Progress = (current_price - entry_price) / (target_price - entry_price)
        price_distance = position_plan.target_price - position_plan.entry_price
        if price_distance == 0:
            return None

        current_progress = (current_price - position_plan.entry_price) / price_distance

        # If progress >= breakeven threshold, move stop to breakeven
        if current_progress >= Decimal(str(config.trailing_breakeven_threshold)):
            new_stop_price = position_plan.entry_price
            adjustment_reason = "moved to breakeven - price reached 50% of target"
            return (new_stop_price, adjustment_reason)

        return None
