"""
Proximity Alert Service

Monitors current price proximity to support/resistance zones and generates
alerts when price approaches within threshold (default 2%).

Constitution v1.0.0:
- §Safety_First: Alerts for manual review, no auto-trading
- §Risk_Management: Threshold validation, graceful degradation

Feature: support-resistance-mapping
Tasks: T025-T027 - Proximity alert implementation
"""

import logging
from datetime import UTC, datetime
from decimal import Decimal

from .config import ZoneDetectionConfig
from .models import ProximityAlert, Zone, ZoneType
from .zone_logger import ZoneLogger

# Module logger
logger = logging.getLogger(__name__)


class ProximityChecker:
    """Proximity alert service for support/resistance zones.

    Checks if current price is within proximity_threshold_pct (default 2%)
    of any zone and generates ProximityAlert objects for manual review.

    Features:
    - Configurable distance threshold (default 2%)
    - Direction detection (approaching support vs resistance)
    - Structured logging of all alerts
    - Graceful degradation (invalid prices → empty results)

    Example:
        >>> config = ZoneDetectionConfig.from_env()
        >>> checker = ProximityChecker(config)
        >>> zones = [Zone(...), Zone(...)]
        >>> alerts = checker.check_proximity("AAPL", Decimal("152.00"), zones)
        >>> for alert in alerts:
        ...     print(f"{alert.direction}: {alert.distance_percent}% away")
    """

    def __init__(
        self,
        config: ZoneDetectionConfig,
        zone_logger: ZoneLogger | None = None
    ):
        """Initialize proximity checker with configuration.

        Args:
            config: Zone detection configuration (proximity threshold)
            zone_logger: Optional logger instance (creates default if None)
        """
        self.config = config
        self.logger = zone_logger or ZoneLogger()

    def check_proximity(
        self,
        symbol: str,
        current_price: Decimal,
        zones: list[Zone]
    ) -> list[ProximityAlert]:
        """Check if current price is near any support/resistance zones.

        Compares current price against all zones and generates alerts for
        zones within proximity_threshold_pct (default 2%).

        Args:
            symbol: Stock ticker symbol (e.g., "AAPL")
            current_price: Current market price
            zones: List of Zone objects to check against

        Returns:
            List of ProximityAlert objects (empty if no zones within threshold)

        Raises:
            ValueError: If symbol is empty or current_price <= 0

        Example:
            >>> zones = [
            ...     Zone(price_level=Decimal("150.00"), zone_type=ZoneType.SUPPORT, ...),
            ...     Zone(price_level=Decimal("200.00"), zone_type=ZoneType.RESISTANCE, ...)
            ... ]
            >>> alerts = checker.check_proximity("AAPL", Decimal("151.00"), zones)
            >>> len(alerts)
            1
            >>> alerts[0].distance_percent
            Decimal('0.66')
        """
        # Input validation
        if not symbol or not symbol.strip():
            raise ValueError("symbol must be non-empty")
        if current_price <= 0:
            raise ValueError("current_price must be positive")

        alerts = []
        timestamp = datetime.now(UTC)

        for zone in zones:
            # Calculate distance percentage
            distance_pct = abs((current_price - zone.price_level) / zone.price_level) * Decimal('100')

            # Check if within threshold
            if distance_pct <= self.config.proximity_threshold_pct:
                # Determine direction
                if zone.zone_type == ZoneType.SUPPORT:
                    direction = "approaching_support"
                else:
                    direction = "approaching_resistance"

                # Create alert
                # zone_id is auto-generated in Zone.__post_init__, so should never be None
                if zone.zone_id is None:
                    raise ValueError("Zone must have zone_id after initialization")
                alert = ProximityAlert(
                    symbol=symbol,
                    zone_id=zone.zone_id,
                    current_price=current_price,
                    zone_price=zone.price_level,
                    distance_percent=distance_pct,
                    direction=direction,
                    timestamp=timestamp
                )

                alerts.append(alert)

                # Log alert
                self.logger.log_proximity_alert(alert)

        return alerts

    def find_nearest_support(
        self,
        current_price: Decimal,
        zones: list[Zone]
    ) -> Zone | None:
        """Find nearest support zone below current price.

        Args:
            current_price: Current market price
            zones: List of Zone objects

        Returns:
            Nearest support zone below current price, or None if not found

        Example:
            >>> zones = [
            ...     Zone(price_level=Decimal("150.00"), zone_type=ZoneType.SUPPORT, ...),
            ...     Zone(price_level=Decimal("145.00"), zone_type=ZoneType.SUPPORT, ...)
            ... ]
            >>> nearest = checker.find_nearest_support(Decimal("152.00"), zones)
            >>> nearest.price_level
            Decimal('150.00')
        """
        support_zones = [
            zone for zone in zones
            if zone.zone_type == ZoneType.SUPPORT and zone.price_level < current_price
        ]

        if not support_zones:
            return None

        # Return support zone with highest price_level (closest below current)
        return max(support_zones, key=lambda z: z.price_level)

    def find_nearest_resistance(
        self,
        current_price: Decimal,
        zones: list[Zone]
    ) -> Zone | None:
        """Find nearest resistance zone above current price.

        Args:
            current_price: Current market price
            zones: List of Zone objects

        Returns:
            Nearest resistance zone above current price, or None if not found

        Example:
            >>> zones = [
            ...     Zone(price_level=Decimal("160.00"), zone_type=ZoneType.RESISTANCE, ...),
            ...     Zone(price_level=Decimal("165.00"), zone_type=ZoneType.RESISTANCE, ...)
            ... ]
            >>> nearest = checker.find_nearest_resistance(Decimal("152.00"), zones)
            >>> nearest.price_level
            Decimal('160.00')
        """
        resistance_zones = [
            zone for zone in zones
            if zone.zone_type == ZoneType.RESISTANCE and zone.price_level > current_price
        ]

        if not resistance_zones:
            return None

        # Return resistance zone with lowest price_level (closest above current)
        return min(resistance_zones, key=lambda z: z.price_level)
