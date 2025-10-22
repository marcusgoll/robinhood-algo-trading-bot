"""
Breakout Detection Models

Data models for tracking and managing price breakouts from support/resistance zones.
Extends the zone detection system with volume-confirmed breakout events.

Example:
    >>> from decimal import Decimal
    >>> from datetime import datetime, UTC
    >>> event = BreakoutEvent(
    ...     event_id="evt_001",
    ...     zone_id="zone_123",
    ...     timestamp=datetime.now(UTC),
    ...     breakout_price=Decimal("156.00"),
    ...     close_price=Decimal("156.60"),
    ...     volume=Decimal("1500000"),
    ...     volume_ratio=Decimal("1.4"),
    ...     old_zone_type=ZoneType.RESISTANCE,
    ...     new_zone_type=ZoneType.SUPPORT,
    ...     status=BreakoutStatus.CONFIRMED,
    ...     symbol="AAPL",
    ...     timeframe=Timeframe.DAILY
    ... )
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any
import json

from .models import ZoneType, Timeframe


class BreakoutStatus(Enum):
    """
    Status of a breakout event.

    Attributes:
        PENDING: Breakout detected but not yet validated (within 5-bar window)
        CONFIRMED: Breakout validated (price held above zone for 5+ bars)
        WHIPSAW: Failed breakout (price returned below zone within 5 bars)
    """
    PENDING = "pending"
    CONFIRMED = "confirmed"
    WHIPSAW = "whipsaw"


@dataclass(frozen=True)
class BreakoutEvent:
    """
    Represents a single breakout event when price breaks through a zone.

    Immutable record of breakout metadata for auditing and backtesting.
    All price/volume fields use Decimal for precision (no float arithmetic).

    Attributes:
        event_id: Unique identifier for this breakout event
        zone_id: ID of the zone that was broken
        timestamp: UTC timestamp when breakout was detected
        breakout_price: Price level of the original zone
        close_price: Actual closing price that triggered breakout
        volume: Trading volume at breakout bar
        volume_ratio: Ratio of current volume to 20-bar average
        old_zone_type: Zone type before flip (RESISTANCE or SUPPORT)
        new_zone_type: Zone type after flip (opposite of old_zone_type)
        status: Current breakout status (PENDING/CONFIRMED/WHIPSAW)
        timeframe: Timeframe of the breakout (DAILY, FOUR_HOUR, etc.)

    Example:
        >>> event = BreakoutEvent(
        ...     event_id="evt_001",
        ...     zone_id="zone_123",
        ...     timestamp=datetime.now(UTC),
        ...     breakout_price=Decimal("155.00"),
        ...     close_price=Decimal("156.60"),
        ...     volume=Decimal("1500000"),
        ...     volume_ratio=Decimal("1.4"),
        ...     old_zone_type=ZoneType.RESISTANCE,
        ...     new_zone_type=ZoneType.SUPPORT,
        ...     status=BreakoutStatus.CONFIRMED,
        ...     timeframe=Timeframe.DAILY
        ... )
    """

    event_id: str
    zone_id: str
    timestamp: datetime
    breakout_price: Decimal
    close_price: Decimal
    volume: Decimal
    volume_ratio: Decimal
    old_zone_type: ZoneType
    new_zone_type: ZoneType
    status: BreakoutStatus
    timeframe: Timeframe

    def __post_init__(self) -> None:
        """Validate breakout event fields."""
        if self.breakout_price <= 0:
            raise ValueError(f"breakout_price must be > 0, got {self.breakout_price}")
        if self.close_price <= 0:
            raise ValueError(f"close_price must be > 0, got {self.close_price}")
        if self.volume < 0:
            raise ValueError(f"volume must be >= 0, got {self.volume}")
        if self.volume_ratio < 0:
            raise ValueError(f"volume_ratio must be >= 0, got {self.volume_ratio}")
        if self.timestamp.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware (use UTC)")
        if not isinstance(self.status, BreakoutStatus):
            raise ValueError(f"status must be BreakoutStatus, got {type(self.status)}")

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.

        Returns:
            Dictionary with all fields, Decimals as strings, datetime as ISO format

        Example:
            >>> event.to_dict()
            {
                "event_id": "evt_001",
                "zone_id": "zone_123",
                "timestamp": "2025-10-21T12:00:00+00:00",
                "breakout_price": "155.00",
                ...
            }
        """
        return {
            "event_id": self.event_id,
            "zone_id": self.zone_id,
            "timestamp": self.timestamp.isoformat(),
            "breakout_price": str(self.breakout_price),
            "close_price": str(self.close_price),
            "volume": str(self.volume),
            "volume_ratio": str(self.volume_ratio),
            "old_zone_type": self.old_zone_type.value,
            "new_zone_type": self.new_zone_type.value,
            "status": self.status.value,
            "timeframe": self.timeframe.value,
        }

    def to_jsonl_line(self) -> str:
        """
        Convert to single-line JSON string for JSONL logging.

        Returns:
            Compact JSON string (no whitespace, no newlines)

        Example:
            >>> event.to_jsonl_line()
            '{"event_id":"evt_001","zone_id":"zone_123",...}\n'
        """
        return json.dumps(self.to_dict(), ensure_ascii=False, separators=(',', ':'))


@dataclass(frozen=True)
class BreakoutSignal:
    """
    Return value for detect_breakout() containing all breakout context.

    Bundles the original zone, breakout event, and flipped zone together
    for easy consumption by calling code.

    Attributes:
        zone: Original zone before breakout
        event: Breakout event metadata
        flipped_zone: New zone with flipped type and updated strength

    Example:
        >>> signal = BreakoutSignal(
        ...     zone=original_zone,
        ...     event=breakout_event,
        ...     flipped_zone=new_zone
        ... )
    """

    zone: Any  # Zone type (avoiding circular import)
    event: BreakoutEvent
    flipped_zone: Any  # Zone type (avoiding circular import)
