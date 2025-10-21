"""Trade limit enforcement for phase progression.

Enforces daily trade limits based on current phase:
- Experience: No limit (paper trading)
- Proof of Concept: 1 trade/day maximum
- Real Money Trial: No limit
- Scaling: No limit

Based on specs/022-pos-scale-progress/spec.md FR-003
Tasks: T075-T078 (GREEN phase)
"""

from datetime import date, datetime, time, timedelta, timezone
from typing import Dict, Optional

from trading_bot.config import Config
from trading_bot.phase.models import Phase


class TradeLimitExceeded(Exception):
    """Raised when daily trade limit reached.

    Attributes:
        phase: Current trading phase
        limit: Daily trade limit for this phase
        next_allowed: Next datetime when trading is allowed
    """

    def __init__(self, phase: Phase, limit: int, next_allowed: datetime):
        """Initialize exception with limit details.

        Args:
            phase: Current trading phase
            limit: Daily trade limit that was exceeded
            next_allowed: Next datetime when trading is allowed
        """
        self.phase = phase
        self.limit = limit
        self.next_allowed = next_allowed
        super().__init__(
            f"Trade limit exceeded: {limit} trade(s) allowed in {phase.value} phase. "
            f"Next trade at: {next_allowed.strftime('%Y-%m-%d %H:%M:%S %Z')}"
        )


class TradeLimiter:
    """Enforce daily trade limits based on phase.

    Manages per-day trade counters and validates against phase-specific limits.

    Attributes:
        config: Trading bot configuration
        _trade_counts: Dictionary mapping dates to trade counts
    """

    def __init__(self, config: Config):
        """Initialize TradeLimiter with configuration.

        Args:
            config: Trading bot configuration instance
        """
        self.config = config
        self._trade_counts: Dict[date, int] = {}

    def _get_limit(self, phase: Phase) -> Optional[int]:
        """Get daily trade limit for phase.

        Args:
            phase: Trading phase to check

        Returns:
            Daily trade limit, or None if unlimited
        """
        limits = {
            Phase.EXPERIENCE: None,  # No limit (paper trading)
            Phase.PROOF_OF_CONCEPT: 1,  # 1 trade/day
            Phase.REAL_MONEY_TRIAL: None,  # No limit
            Phase.SCALING: None  # No limit
        }
        return limits[phase]

    def check_limit(self, phase: Phase, trade_date: date) -> None:
        """Check if daily trade limit would be exceeded.

        Increments counter if limit not exceeded.
        Only tracks counts for phases with limits.

        Args:
            phase: Current trading phase
            trade_date: Date of proposed trade

        Raises:
            TradeLimitExceeded: If limit hit for this phase
        """
        # Get phase-specific limit
        limit = self._get_limit(phase)

        # No limit - allow trade and don't track counter
        if limit is None:
            return

        # Get current count for this date
        current_count = self._trade_counts.get(trade_date, 0)

        # Check if limit exceeded
        if current_count >= limit:
            # Calculate next allowed trade time (next day at 7:00 AM UTC)
            next_allowed = datetime.combine(
                trade_date + timedelta(days=1),
                time(7, 0)  # Market open at 7:00 AM EST
            ).replace(tzinfo=timezone.utc)

            raise TradeLimitExceeded(
                phase=phase,
                limit=limit,
                next_allowed=next_allowed
            )

        # Increment counter (only for limited phases)
        self._trade_counts[trade_date] = current_count + 1

    def reset_daily_counter(self, current_date: date) -> None:
        """Clear old date counters to prevent memory leak.

        Removes counters for dates before current_date.
        Keeps current and future dates.

        Args:
            current_date: Current date (counters before this are removed)
        """
        # Keep only current and future dates
        self._trade_counts = {
            d: count for d, count in self._trade_counts.items()
            if d >= current_date
        }

    def get_next_allowed_trade(self, phase: Phase, trade_date: date) -> Optional[datetime]:
        """Get next allowed trade time if limit hit.

        Args:
            phase: Current trading phase
            trade_date: Current date

        Returns:
            Next allowed trade datetime, or None if no limit or under limit
        """
        # Get phase-specific limit
        limit = self._get_limit(phase)

        # No limit - no countdown needed
        if limit is None:
            return None

        # Get current count
        current_count = self._trade_counts.get(trade_date, 0)

        # Under limit - no countdown needed
        if current_count < limit:
            return None

        # At limit - return next day 7:00 AM
        return datetime.combine(
            trade_date + timedelta(days=1),
            time(7, 0)
        ).replace(tzinfo=timezone.utc)
