"""
Emotional Control Data Models

Data structures for emotional control state tracking and event logging.

Constitution v1.0.0:
- §Safety_First: Fail-safe default to ACTIVE state on corruption
- §Data_Integrity: All monetary values use Decimal precision
- §Audit_Everything: Complete event tracking with timestamps

Feature: emotional-control-me
Tasks: T004-T006 - Core dataclasses with validation
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from uuid import uuid4


@dataclass
class EmotionalControlState:
    """Current emotional control state (T004).

    Tracks activation status, trigger reasons, consecutive counters, and
    account context at time of activation.

    Attributes:
        is_active: Whether emotional control is currently active
        activated_at: UTC timestamp of activation (ISO 8601), None if inactive
        trigger_reason: Why control activated ("SINGLE_LOSS" | "STREAK_LOSS")
        account_balance_at_activation: Account balance when activated
        loss_amount: Loss amount that triggered activation (if SINGLE_LOSS)
        consecutive_losses: Current consecutive loss streak count
        consecutive_wins: Current consecutive win streak count
        last_updated: UTC timestamp of last state update (ISO 8601)

    Validation Rules (from data-model.md):
        - If is_active=True, activated_at and trigger_reason must be set
        - consecutive_losses and consecutive_wins >= 0
        - trigger_reason must be "SINGLE_LOSS" or "STREAK_LOSS" if active

    Example:
        >>> state = EmotionalControlState(
        ...     is_active=True,
        ...     activated_at="2025-10-22T14:30:00Z",
        ...     trigger_reason="SINGLE_LOSS",
        ...     account_balance_at_activation=Decimal("100000"),
        ...     loss_amount=Decimal("3000"),
        ...     consecutive_losses=1,
        ...     consecutive_wins=0,
        ...     last_updated="2025-10-22T14:30:00Z"
        ... )
        >>> assert state.is_active is True
        >>> assert state.trigger_reason == "SINGLE_LOSS"
    """

    is_active: bool
    activated_at: Optional[str]
    trigger_reason: Optional[str]
    account_balance_at_activation: Optional[Decimal]
    loss_amount: Optional[Decimal]
    consecutive_losses: int
    consecutive_wins: int
    last_updated: str

    def __post_init__(self) -> None:
        """Validate state consistency after initialization.

        Raises:
            ValueError: If state violates activation invariants
        """
        # Validate consecutive counters
        if self.consecutive_losses < 0:
            raise ValueError(
                f"Consecutive losses must be >= 0, got {self.consecutive_losses}"
            )
        if self.consecutive_wins < 0:
            raise ValueError(
                f"Consecutive wins must be >= 0, got {self.consecutive_wins}"
            )

        # Validate active state has required fields
        if self.is_active:
            if not self.activated_at:
                raise ValueError("Active state must have activated_at timestamp")
            if not self.trigger_reason:
                raise ValueError("Active state must have trigger_reason")
            if self.trigger_reason not in ["SINGLE_LOSS", "STREAK_LOSS"]:
                raise ValueError(
                    f"Invalid trigger_reason: {self.trigger_reason}. "
                    "Must be SINGLE_LOSS or STREAK_LOSS"
                )


@dataclass
class EmotionalControlEvent:
    """Audit event for emotional control state changes (T005).

    Logged when activation, recovery, or manual reset occurs.
    Provides complete audit trail per §Audit_Everything.

    Attributes:
        event_id: Unique identifier (UUID)
        timestamp: Event time (ISO 8601 UTC)
        event_type: Event category ("ACTIVATION" | "RECOVERY" | "MANUAL_RESET")
        trigger_reason: Why event occurred (e.g., "SINGLE_LOSS", "STREAK_LOSS",
                       "PROFITABLE_RECOVERY", "MANUAL_RESET")
        account_balance: Current account balance at event time
        loss_amount: Loss amount (for ACTIVATION events), None otherwise
        consecutive_losses: Consecutive loss count at event time
        consecutive_wins: Consecutive win count at event time
        admin_id: Admin user ID (for MANUAL_RESET events), None otherwise
        reset_reason: Human-readable reset reason (for MANUAL_RESET), None otherwise
        position_size_multiplier: Active multiplier after event (0.25 or 1.00)

    Validation Rules (from data-model.md):
        - event_type must be ACTIVATION, RECOVERY, or MANUAL_RESET
        - If event_type=MANUAL_RESET, admin_id and reset_reason required
        - position_size_multiplier must be Decimal("0.25") or Decimal("1.00")

    Example:
        >>> event = EmotionalControlEvent(
        ...     event_id="550e8400-e29b-41d4-a716-446655440000",
        ...     timestamp="2025-10-22T14:30:00Z",
        ...     event_type="ACTIVATION",
        ...     trigger_reason="SINGLE_LOSS",
        ...     account_balance=Decimal("100000"),
        ...     loss_amount=Decimal("3000"),
        ...     consecutive_losses=1,
        ...     consecutive_wins=0,
        ...     admin_id=None,
        ...     reset_reason=None,
        ...     position_size_multiplier=Decimal("0.25")
        ... )
        >>> assert event.event_type == "ACTIVATION"
        >>> assert event.position_size_multiplier == Decimal("0.25")
    """

    event_id: str
    timestamp: str
    event_type: str
    trigger_reason: str
    account_balance: Decimal
    loss_amount: Optional[Decimal]
    consecutive_losses: int
    consecutive_wins: int
    admin_id: Optional[str]
    reset_reason: Optional[str]
    position_size_multiplier: Decimal

    def __post_init__(self) -> None:
        """Validate event data after initialization.

        Raises:
            ValueError: If event data violates business rules
        """
        # Validate event_type
        valid_types = ["ACTIVATION", "RECOVERY", "MANUAL_RESET"]
        if self.event_type not in valid_types:
            raise ValueError(
                f"Invalid event_type: {self.event_type}. "
                f"Must be one of {valid_types}"
            )

        # Validate manual reset has admin context
        if self.event_type == "MANUAL_RESET":
            if not self.admin_id:
                raise ValueError("MANUAL_RESET event must have admin_id")
            if not self.reset_reason:
                raise ValueError("MANUAL_RESET event must have reset_reason")

        # Validate position size multiplier
        valid_multipliers = [Decimal("0.25"), Decimal("1.00")]
        if self.position_size_multiplier not in valid_multipliers:
            raise ValueError(
                f"Invalid position_size_multiplier: {self.position_size_multiplier}. "
                f"Must be 0.25 or 1.00"
            )

        # Validate consecutive counters
        if self.consecutive_losses < 0:
            raise ValueError(
                f"Consecutive losses must be >= 0, got {self.consecutive_losses}"
            )
        if self.consecutive_wins < 0:
            raise ValueError(
                f"Consecutive wins must be >= 0, got {self.consecutive_wins}"
            )

    @staticmethod
    def create(
        event_type: str,
        trigger_reason: str,
        account_balance: Decimal,
        consecutive_losses: int,
        consecutive_wins: int,
        position_size_multiplier: Decimal,
        loss_amount: Optional[Decimal] = None,
        admin_id: Optional[str] = None,
        reset_reason: Optional[str] = None,
    ) -> "EmotionalControlEvent":
        """Factory method to create event with auto-generated ID and timestamp.

        Args:
            event_type: Event category (ACTIVATION, RECOVERY, MANUAL_RESET)
            trigger_reason: Why event occurred
            account_balance: Current account balance
            consecutive_losses: Current loss streak count
            consecutive_wins: Current win streak count
            position_size_multiplier: Active multiplier after event (0.25 or 1.00)
            loss_amount: Loss amount for ACTIVATION events
            admin_id: Admin user ID for MANUAL_RESET events
            reset_reason: Reset reason for MANUAL_RESET events

        Returns:
            EmotionalControlEvent with auto-generated ID and timestamp
        """
        from datetime import datetime, timezone

        return EmotionalControlEvent(
            event_id=str(uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type=event_type,
            trigger_reason=trigger_reason,
            account_balance=account_balance,
            loss_amount=loss_amount,
            consecutive_losses=consecutive_losses,
            consecutive_wins=consecutive_wins,
            admin_id=admin_id,
            reset_reason=reset_reason,
            position_size_multiplier=position_size_multiplier,
        )
