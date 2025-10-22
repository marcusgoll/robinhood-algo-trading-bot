"""
Breakout Detection Service

Detects price breakouts from support/resistance zones with volume confirmation.
Implements composition pattern - works alongside ZoneDetector, doesn't extend it.

Example:
    >>> from decimal import Decimal
    >>> detector = BreakoutDetector(config, market_data_service, logger)
    >>> signal = detector.detect_breakout(
    ...     zone=resistance_zone,
    ...     current_price=Decimal("156.60"),
    ...     current_volume=Decimal("1500000"),
    ...     historical_volumes=[Decimal("1000000")] * 20
    ... )
    >>> if signal:
    ...     print(f"Breakout detected! Zone flipped to {signal.flipped_zone.zone_type}")
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from .breakout_config import BreakoutConfig
from .breakout_models import BreakoutEvent, BreakoutSignal, BreakoutStatus
from .models import Zone, ZoneType
from .zone_logger import ZoneLogger


class BreakoutDetector:
    """
    Service for detecting price breakouts from support/resistance zones.

    Uses composition pattern - accepts ZoneDetector output and adds breakout detection.
    Stateless service with no mutable state (thread-safe).

    Attributes:
        config: Configuration for thresholds and parameters
        market_data_service: Service for fetching market data (injected)
        logger: Logger for breakout events (injected)

    Example:
        >>> config = BreakoutConfig()
        >>> detector = BreakoutDetector(config, market_data_service, logger)
        >>> signal = detector.detect_breakout(zone, price, volume, historical_volumes)
    """

    def __init__(
        self,
        config: BreakoutConfig,
        market_data_service: Any,  # MarketDataService (avoid circular import)
        logger: ZoneLogger,
    ) -> None:
        """
        Initialize BreakoutDetector with configuration and dependencies.

        Args:
            config: Breakout detection configuration
            market_data_service: Service for market data fetching
            logger: Logger for breakout events

        Raises:
            TypeError: If any required parameter is None
        """
        if config is None:
            raise TypeError("config cannot be None")
        if market_data_service is None:
            raise TypeError("market_data_service cannot be None")
        if logger is None:
            raise TypeError("logger cannot be None")

        self.config: BreakoutConfig = config
        self.market_data_service: Any = market_data_service
        self.logger: ZoneLogger = logger

    def _calculate_price_change_pct(
        self,
        zone_price: Decimal,
        current_price: Decimal,
    ) -> Decimal:
        """
        Calculate percentage price change from zone level to current price.

        Args:
            zone_price: Price level of the zone
            current_price: Current market price

        Returns:
            Percentage change as Decimal (e.g., Decimal("1.03") for +1.03%)

        Example:
            >>> detector._calculate_price_change_pct(Decimal("155.00"), Decimal("156.60"))
            Decimal('1.032258064516129032258064516')
        """
        return (current_price - zone_price) / zone_price * 100

    def _calculate_volume_ratio(
        self,
        current_volume: Decimal,
        historical_volumes: list[Decimal],
    ) -> Decimal:
        """
        Calculate ratio of current volume to historical average.

        Args:
            current_volume: Trading volume at current bar
            historical_volumes: List of volumes for previous bars (requires >=20)

        Returns:
            Volume ratio as Decimal (e.g., Decimal("1.40") for 1.4x average)

        Raises:
            ValueError: If historical_volumes has <20 bars

        Example:
            >>> detector._calculate_volume_ratio(
            ...     Decimal("1500000"),
            ...     [Decimal("1000000")] * 20
            ... )
            Decimal('1.5')
        """
        if len(historical_volumes) < 20:
            raise ValueError(
                f"historical_volumes must have >=20 bars, got {len(historical_volumes)}"
            )

        avg_volume = sum(historical_volumes) / Decimal(len(historical_volumes))
        return current_volume / avg_volume

    def detect_breakout(
        self,
        zone: Zone,
        current_price: Decimal,
        current_volume: Decimal,
        historical_volumes: list[Decimal],
    ) -> BreakoutSignal | None:
        """
        Detect if current price/volume represents a breakout from the zone.

        Breakout criteria (from spec.md US1):
        - Price closes >1% above resistance (or <1% below support)
        - Volume >1.3x the 20-bar average
        - Both conditions must be met simultaneously

        Args:
            zone: Zone to check for breakout
            current_price: Current closing price
            current_volume: Current bar volume
            historical_volumes: Previous 20+ bars of volume data

        Returns:
            BreakoutSignal with zone, event, flipped_zone if breakout detected
            None if no breakout (price or volume threshold not met)

        Raises:
            ValueError: If inputs are invalid (None zone, negative price, etc.)

        Example:
            >>> signal = detector.detect_breakout(
            ...     zone=resistance_zone,
            ...     current_price=Decimal("156.60"),
            ...     current_volume=Decimal("1500000"),
            ...     historical_volumes=[Decimal("1000000")] * 20
            ... )
            >>> if signal:
            ...     print(f"Breakout! {signal.event.old_zone_type} -> {signal.event.new_zone_type}")
        """
        # Input validation
        if zone is None:
            raise ValueError("zone cannot be None")
        if current_price <= 0:
            raise ValueError(f"current_price must be > 0, got {current_price}")
        if current_volume < 0:
            raise ValueError(f"current_volume must be >= 0, got {current_volume}")

        # Calculate price change and volume ratio
        price_change_pct = self._calculate_price_change_pct(
            zone.price_level, current_price
        )
        volume_ratio = self._calculate_volume_ratio(current_volume, historical_volumes)

        # Check breakout conditions
        price_threshold_met = abs(price_change_pct) > self.config.price_threshold_pct
        volume_threshold_met = volume_ratio > self.config.volume_threshold

        if not (price_threshold_met and volume_threshold_met):
            return None  # No breakout

        # Determine new zone type (flip)
        if zone.zone_type == ZoneType.RESISTANCE:
            new_zone_type = ZoneType.SUPPORT
        else:
            new_zone_type = ZoneType.RESISTANCE

        # Create breakout event
        event = BreakoutEvent(
            event_id=f"evt_{uuid.uuid4().hex[:12]}",
            zone_id=zone.zone_id or f"zone_{zone.price_level}",
            timestamp=datetime.now(UTC),
            breakout_price=zone.price_level,
            close_price=current_price,
            volume=current_volume,
            volume_ratio=volume_ratio,
            old_zone_type=zone.zone_type,
            new_zone_type=new_zone_type,
            status=BreakoutStatus.CONFIRMED,
            timeframe=zone.timeframe,
        )

        # Log event (T034)
        self.logger.log_breakout_event(event)

        # Flip zone
        flipped_zone = self.flip_zone(zone, event)

        # Return signal
        return BreakoutSignal(
            zone=zone,
            event=event,
            flipped_zone=flipped_zone,
        )

    def flip_zone(
        self,
        zone: Zone,
        breakout_event: BreakoutEvent,
    ) -> Zone:
        """
        Create new Zone with flipped type and updated strength.

        Preserves immutability - creates new Zone instance rather than mutating.
        Adds strength bonus for volume-confirmed breakouts.

        Args:
            zone: Original zone before breakout
            breakout_event: Breakout event metadata

        Returns:
            New Zone instance with flipped type and updated strength

        Raises:
            ValueError: If zone.zone_type doesn't match breakout_event.old_zone_type

        Example:
            >>> flipped = detector.flip_zone(resistance_zone, breakout_event)
            >>> flipped.zone_type
            <ZoneType.SUPPORT: 'support'>
            >>> flipped.strength_score
            Decimal('7.0')  # Original 5.0 + 2.0 bonus
        """
        # Validate zone type matches event
        if zone.zone_type != breakout_event.old_zone_type:
            raise ValueError(
                f"zone_type mismatch: zone has {zone.zone_type}, "
                f"event expects {breakout_event.old_zone_type}"
            )

        # Calculate new strength
        new_strength = zone.strength_score + self.config.strength_bonus

        # Create new zone with flipped type (immutability preserved)
        return Zone(
            zone_id=zone.zone_id,
            price_level=zone.price_level,
            zone_type=breakout_event.new_zone_type,
            strength_score=new_strength,
            touch_count=zone.touch_count,
            first_touch_date=zone.first_touch_date,
            last_touch_date=zone.last_touch_date,
            average_volume=zone.average_volume,
            highest_volume_touch=zone.highest_volume_touch,
            timeframe=zone.timeframe,
        )
