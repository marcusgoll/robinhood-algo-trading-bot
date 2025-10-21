"""
Support/Resistance Zone Data Models

Dataclasses for support/resistance zone detection: Zone, ZoneTouch, ProximityAlert.

All models use Decimal for price fields, comprehensive validation, and serialization
to ensure data integrity throughout zone detection and proximity monitoring.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any


class ZoneType(Enum):
    """Type of support/resistance zone."""
    SUPPORT = "support"
    RESISTANCE = "resistance"


class Timeframe(Enum):
    """Timeframe for zone analysis."""
    DAILY = "daily"
    FOUR_HOUR = "4h"


class TouchType(Enum):
    """Type of price interaction with a zone."""
    BOUNCE = "bounce"
    REJECTION = "rejection"
    BREAKOUT = "breakout"


@dataclass
class Zone:
    """
    Support or resistance zone with strength metrics.

    Represents a price level where multiple touches (bounces/rejections) occurred,
    indicating institutional interest. Zones are identified by clustering swing points
    within tolerance_pct and scored by touch count + volume bonus.

    Attributes:
        price_level: Central price of the zone in USD
        zone_type: SUPPORT or RESISTANCE
        strength_score: Touch count + volume bonus (higher = stronger)
        touch_count: Number of times price touched this zone
        first_touch_date: Date of first price touch (UTC)
        last_touch_date: Date of most recent touch (UTC)
        average_volume: Average trading volume across all touches
        highest_volume_touch: Highest volume observed in a single touch
        timeframe: DAILY or FOUR_HOUR

    Raises:
        ValueError: If validation fails (negative price, invalid dates, etc.)
    """
    price_level: Decimal
    zone_type: ZoneType
    strength_score: Decimal
    touch_count: int
    first_touch_date: datetime
    last_touch_date: datetime
    average_volume: Decimal
    highest_volume_touch: Decimal
    timeframe: Timeframe
    zone_id: str | None = None  # Auto-generated from price_level + zone_type

    def __post_init__(self) -> None:
        """Validate zone attributes after initialization."""
        if self.price_level <= 0:
            raise ValueError(f"price_level must be positive, got {self.price_level}")

        if self.first_touch_date > self.last_touch_date:
            raise ValueError(
                f"first_touch_date ({self.first_touch_date}) must be <= last_touch_date ({self.last_touch_date})"
            )

        if self.touch_count < 0:
            raise ValueError(f"touch_count must be non-negative, got {self.touch_count}")

        if self.average_volume < 0:
            raise ValueError(f"average_volume must be non-negative, got {self.average_volume}")

        # Auto-generate zone_id if not provided
        if self.zone_id is None:
            object.__setattr__(
                self,
                'zone_id',
                f"{self.zone_type.value}_{self.price_level}_{self.timeframe.value}"
            )

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize zone to dictionary for storage/transmission.

        Returns:
            Dictionary with all zone fields, dates as ISO strings
        """
        return {
            "zone_id": self.zone_id,
            "price_level": str(self.price_level),
            "zone_type": self.zone_type.value,
            "strength_score": str(self.strength_score),
            "touch_count": self.touch_count,
            "first_touch_date": self.first_touch_date.isoformat(),
            "last_touch_date": self.last_touch_date.isoformat(),
            "average_volume": str(self.average_volume),
            "highest_volume_touch": str(self.highest_volume_touch),
            "timeframe": self.timeframe.value
        }

    def to_jsonl_line(self) -> str:
        """
        Serialize zone to JSONL line for structured logging.

        Returns:
            JSON string (single line, no newline)
        """
        import json
        return json.dumps(self.to_dict())


@dataclass
class ZoneTouch:
    """
    Record of a single price touch at a support/resistance zone.

    Tracks each time price approached a zone within tolerance, including
    the type of interaction (bounce, rejection, breakout) and volume context.

    Attributes:
        zone_id: ID of the zone being touched
        touch_date: Date/time of the touch (UTC)
        price: Exact price at the touch
        volume: Trading volume at the touch
        touch_type: BOUNCE, REJECTION, or BREAKOUT

    Raises:
        ValueError: If validation fails (negative price/volume, etc.)
    """
    zone_id: str
    touch_date: datetime
    price: Decimal
    volume: Decimal
    touch_type: TouchType

    def __post_init__(self) -> None:
        """Validate touch attributes after initialization."""
        if self.price <= 0:
            raise ValueError(f"price must be positive, got {self.price}")

        if self.volume < 0:
            raise ValueError(f"volume must be non-negative, got {self.volume}")

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize touch to dictionary.

        Returns:
            Dictionary with all touch fields
        """
        return {
            "zone_id": self.zone_id,
            "touch_date": self.touch_date.isoformat(),
            "price": str(self.price),
            "volume": str(self.volume),
            "touch_type": self.touch_type.value
        }

    def to_jsonl_line(self) -> str:
        """
        Serialize touch to JSONL line.

        Returns:
            JSON string (single line, no newline)
        """
        import json
        return json.dumps(self.to_dict())


@dataclass
class ProximityAlert:
    """
    Alert when current price approaches a support/resistance zone.

    Generated when price is within proximity_threshold_pct (default 2%) of
    a zone, useful for entry/exit signals or stop-loss placement.

    Attributes:
        symbol: Stock symbol (e.g., "AAPL")
        zone_id: ID of the nearby zone
        current_price: Current market price
        zone_price: Price level of the zone
        distance_percent: Distance to zone as percentage (0.0-2.0)
        direction: "approaching_support" or "approaching_resistance"
        timestamp: When alert was generated (UTC)

    Raises:
        ValueError: If validation fails (distance > 2%, etc.)
    """
    symbol: str
    zone_id: str
    current_price: Decimal
    zone_price: Decimal
    distance_percent: Decimal
    direction: str  # "approaching_support" or "approaching_resistance"
    timestamp: datetime

    def __post_init__(self) -> None:
        """Validate proximity alert attributes."""
        if self.current_price <= 0:
            raise ValueError(f"current_price must be positive, got {self.current_price}")

        if self.zone_price <= 0:
            raise ValueError(f"zone_price must be positive, got {self.zone_price}")

        if self.distance_percent < 0 or self.distance_percent > Decimal("2.0"):
            raise ValueError(
                f"distance_percent must be 0-2%, got {self.distance_percent}"
            )

        if self.direction not in ("approaching_support", "approaching_resistance"):
            raise ValueError(
                f"direction must be 'approaching_support' or 'approaching_resistance', "
                f"got {self.direction}"
            )

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize alert to dictionary.

        Returns:
            Dictionary with all alert fields
        """
        return {
            "symbol": self.symbol,
            "zone_id": self.zone_id,
            "current_price": str(self.current_price),
            "zone_price": str(self.zone_price),
            "distance_percent": str(self.distance_percent),
            "direction": self.direction,
            "timestamp": self.timestamp.isoformat()
        }

    def to_jsonl_line(self) -> str:
        """
        Serialize alert to JSONL line.

        Returns:
            JSON string (single line, no newline)
        """
        import json
        return json.dumps(self.to_dict())
