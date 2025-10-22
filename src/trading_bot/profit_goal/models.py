"""
Profit Goal Management Data Models

Data structures for daily profit goal tracking and protection.

Constitution v1.0.0:
- §Risk_Management: Automated profit protection at configurable thresholds
- §Data_Integrity: All monetary values use Decimal precision
- §Audit_Everything: Complete state tracking with timestamps

Feature: daily-profit-goal-ma
Tasks: T005-T007 - Core dataclasses with validation
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from uuid import uuid4


@dataclass
class ProfitGoalConfig:
    """Configuration for daily profit goal and protection thresholds (T005).

    Defines trader's daily profit target and giveback threshold for automated
    protection. All monetary values use Decimal for precision.

    Attributes:
        target: Daily profit target in dollars ($0-$10,000)
        threshold: Drawdown percentage to trigger protection (0.10-0.90)
        enabled: Whether profit protection is active (auto-set based on target)

    Validation Rules (from data-model.md):
        - target must be >= 0 and <= 10000
        - threshold must be >= 0.10 and <= 0.90
        - enabled auto-set to (target > 0)

    Example:
        >>> config = ProfitGoalConfig(target=Decimal("500"), threshold=Decimal("0.50"))
        >>> assert config.enabled is True
        >>> assert config.threshold == Decimal("0.50")
    """

    target: Decimal
    threshold: Decimal
    enabled: bool = False

    def __post_init__(self) -> None:
        """Validate configuration values after initialization.

        Raises:
            ValueError: If target or threshold out of valid range
        """
        # Validate target range (FR-010)
        if self.target < 0 or self.target > 10000:
            raise ValueError(
                f"Profit target must be between $0 and $10,000, got {self.target}"
            )

        # Validate threshold range (FR-010)
        if self.threshold < Decimal("0.10") or self.threshold > Decimal("0.90"):
            raise ValueError(
                f"Threshold must be between 0.10 and 0.90, got {self.threshold}"
            )

        # Auto-set enabled flag
        self.enabled = self.target > 0


@dataclass
class DailyProfitState:
    """Current daily profit tracking state (T006).

    Tracks realized and unrealized P&L, peak profit high-water mark, and
    protection status throughout the trading session.

    Attributes:
        session_date: Current session date (YYYY-MM-DD)
        daily_pnl: Total P&L for session (realized + unrealized)
        realized_pnl: Closed position profits/losses
        unrealized_pnl: Open position profits/losses
        peak_profit: Highest daily_pnl reached during session
        protection_active: Whether profit protection mode is triggered
        last_reset: UTC timestamp of last daily reset (ISO 8601)
        last_updated: UTC timestamp of last state update (ISO 8601)

    Validation Rules (from data-model.md):
        - peak_profit must be >= daily_pnl (high-water mark property)
        - timestamps must be valid ISO 8601 format
        - daily_pnl = realized_pnl + unrealized_pnl (enforced by tracker, not here)

    Example:
        >>> state = DailyProfitState(
        ...     session_date="2025-10-21",
        ...     daily_pnl=Decimal("300"),
        ...     realized_pnl=Decimal("200"),
        ...     unrealized_pnl=Decimal("100"),
        ...     peak_profit=Decimal("600"),
        ...     protection_active=True,
        ...     last_reset="2025-10-21T04:00:00Z",
        ...     last_updated="2025-10-21T14:30:00Z"
        ... )
        >>> assert state.peak_profit >= state.daily_pnl
    """

    session_date: str
    daily_pnl: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    peak_profit: Decimal
    protection_active: bool
    last_reset: str
    last_updated: str

    def __post_init__(self) -> None:
        """Validate state consistency after initialization.

        Raises:
            ValueError: If peak_profit < daily_pnl (violates high-water mark)
        """
        # Validate high-water mark property
        if self.peak_profit < self.daily_pnl:
            raise ValueError(
                f"Peak profit ({self.peak_profit}) cannot be less than "
                f"daily P&L ({self.daily_pnl}). Peak is high-water mark."
            )

        # Note: We don't validate daily_pnl = realized + unrealized here
        # because that's the tracker's responsibility. State can be loaded
        # from file and may have intermediate values.


@dataclass
class ProfitProtectionEvent:
    """Audit event for profit protection triggers (T007).

    Logged when drawdown threshold is breached and protection mode activates.
    Provides complete audit trail per §Audit_Everything.

    Attributes:
        event_id: Unique identifier (UUID)
        timestamp: Event time (ISO 8601 UTC)
        session_date: Trading session date (YYYY-MM-DD)
        peak_profit: Peak profit before drawdown
        current_profit: Current profit when triggered
        drawdown_percent: Calculated drawdown (peak - current) / peak
        threshold: Configured threshold that was breached
        session_id: Links to trading session for correlation

    Validation Rules (from data-model.md):
        - peak_profit must be > 0 (can't have drawdown from $0)
        - current_profit must be < peak_profit (drawdown event)
        - drawdown_percent must be >= threshold (trigger condition)

    Example:
        >>> event = ProfitProtectionEvent(
        ...     event_id="550e8400-e29b-41d4-a716-446655440000",
        ...     timestamp="2025-10-21T14:30:00Z",
        ...     session_date="2025-10-21",
        ...     peak_profit=Decimal("600"),
        ...     current_profit=Decimal("300"),
        ...     drawdown_percent=Decimal("0.50"),
        ...     threshold=Decimal("0.50"),
        ...     session_id="session-2025-10-21"
        ... )
        >>> assert event.drawdown_percent >= event.threshold
    """

    event_id: str
    timestamp: str
    session_date: str
    peak_profit: Decimal
    current_profit: Decimal
    drawdown_percent: Decimal
    threshold: Decimal
    session_id: str

    def __post_init__(self) -> None:
        """Validate event data after initialization.

        Raises:
            ValueError: If event data violates trigger conditions
        """
        # Validate peak_profit > 0 (can't have drawdown from zero)
        if self.peak_profit <= 0:
            raise ValueError(
                f"Peak profit must be > 0 for drawdown event, got {self.peak_profit}"
            )

        # Validate current < peak (drawdown property)
        if self.current_profit >= self.peak_profit:
            raise ValueError(
                f"Current profit ({self.current_profit}) must be less than "
                f"peak profit ({self.peak_profit}) for protection event"
            )

        # Validate drawdown >= threshold (trigger condition)
        if self.drawdown_percent < self.threshold:
            raise ValueError(
                f"Drawdown ({self.drawdown_percent}) must be >= threshold "
                f"({self.threshold}) to trigger protection"
            )

    @staticmethod
    def create(
        session_date: str,
        peak_profit: Decimal,
        current_profit: Decimal,
        threshold: Decimal,
        session_id: str,
    ) -> "ProfitProtectionEvent":
        """Factory method to create event with calculated fields.

        Args:
            session_date: Trading session date (YYYY-MM-DD)
            peak_profit: Peak profit before drawdown
            current_profit: Current profit when triggered
            threshold: Configured threshold that was breached
            session_id: Trading session identifier

        Returns:
            ProfitProtectionEvent with auto-generated ID, timestamp, and drawdown
        """
        from datetime import datetime, timezone

        drawdown = (peak_profit - current_profit) / peak_profit

        return ProfitProtectionEvent(
            event_id=str(uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            session_date=session_date,
            peak_profit=peak_profit,
            current_profit=current_profit,
            drawdown_percent=drawdown,
            threshold=threshold,
            session_id=session_id,
        )
