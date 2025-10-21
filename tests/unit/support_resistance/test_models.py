"""
Unit tests for support_resistance models.

Tests Zone, ZoneTouch, and ProximityAlert dataclasses with validation,
serialization, and edge case handling.
"""

import pytest
from datetime import datetime, UTC
from decimal import Decimal

from src.trading_bot.support_resistance.models import (
    Zone,
    ZoneTouch,
    ProximityAlert,
    ZoneType,
    Timeframe,
    TouchType
)


class TestZone:
    """Test Zone dataclass validation and serialization."""

    def test_zone_valid_creation(self):
        """Test creating a valid Zone with all required fields."""
        zone = Zone(
            price_level=Decimal("150.50"),
            zone_type=ZoneType.SUPPORT,
            strength_score=Decimal("5.0"),
            touch_count=4,
            first_touch_date=datetime(2025, 1, 1, tzinfo=UTC),
            last_touch_date=datetime(2025, 1, 15, tzinfo=UTC),
            average_volume=Decimal("1000000"),
            highest_volume_touch=Decimal("1500000"),
            timeframe=Timeframe.DAILY
        )

        assert zone.price_level == Decimal("150.50")
        assert zone.zone_type == ZoneType.SUPPORT
        assert zone.strength_score == Decimal("5.0")
        assert zone.touch_count == 4
        assert zone.zone_id == "support_150.50_daily"

    def test_zone_negative_price_raises_error(self):
        """Test Zone with negative price_level raises ValueError."""
        with pytest.raises(ValueError, match="price_level must be positive"):
            Zone(
                price_level=Decimal("-10.0"),
                zone_type=ZoneType.SUPPORT,
                strength_score=Decimal("5.0"),
                touch_count=3,
                first_touch_date=datetime(2025, 1, 1, tzinfo=UTC),
                last_touch_date=datetime(2025, 1, 15, tzinfo=UTC),
                average_volume=Decimal("1000000"),
                highest_volume_touch=Decimal("1500000"),
                timeframe=Timeframe.DAILY
            )

    def test_zone_zero_price_raises_error(self):
        """Test Zone with zero price_level raises ValueError."""
        with pytest.raises(ValueError, match="price_level must be positive"):
            Zone(
                price_level=Decimal("0"),
                zone_type=ZoneType.SUPPORT,
                strength_score=Decimal("5.0"),
                touch_count=3,
                first_touch_date=datetime(2025, 1, 1, tzinfo=UTC),
                last_touch_date=datetime(2025, 1, 15, tzinfo=UTC),
                average_volume=Decimal("1000000"),
                highest_volume_touch=Decimal("1500000"),
                timeframe=Timeframe.DAILY
            )

    def test_zone_invalid_date_order_raises_error(self):
        """Test Zone with first_touch > last_touch raises ValueError."""
        with pytest.raises(ValueError, match="first_touch_date .* must be <= last_touch_date"):
            Zone(
                price_level=Decimal("150.50"),
                zone_type=ZoneType.SUPPORT,
                strength_score=Decimal("5.0"),
                touch_count=3,
                first_touch_date=datetime(2025, 1, 15, tzinfo=UTC),
                last_touch_date=datetime(2025, 1, 1, tzinfo=UTC),  # Earlier than first
                average_volume=Decimal("1000000"),
                highest_volume_touch=Decimal("1500000"),
                timeframe=Timeframe.DAILY
            )

    def test_zone_negative_touch_count_raises_error(self):
        """Test Zone with negative touch_count raises ValueError."""
        with pytest.raises(ValueError, match="touch_count must be non-negative"):
            Zone(
                price_level=Decimal("150.50"),
                zone_type=ZoneType.SUPPORT,
                strength_score=Decimal("5.0"),
                touch_count=-1,
                first_touch_date=datetime(2025, 1, 1, tzinfo=UTC),
                last_touch_date=datetime(2025, 1, 15, tzinfo=UTC),
                average_volume=Decimal("1000000"),
                highest_volume_touch=Decimal("1500000"),
                timeframe=Timeframe.DAILY
            )

    def test_zone_negative_volume_raises_error(self):
        """Test Zone with negative average_volume raises ValueError."""
        with pytest.raises(ValueError, match="average_volume must be non-negative"):
            Zone(
                price_level=Decimal("150.50"),
                zone_type=ZoneType.SUPPORT,
                strength_score=Decimal("5.0"),
                touch_count=3,
                first_touch_date=datetime(2025, 1, 1, tzinfo=UTC),
                last_touch_date=datetime(2025, 1, 15, tzinfo=UTC),
                average_volume=Decimal("-1000"),
                highest_volume_touch=Decimal("1500000"),
                timeframe=Timeframe.DAILY
            )

    def test_zone_to_dict_serialization(self):
        """Test Zone.to_dict() serializes all fields correctly."""
        zone = Zone(
            price_level=Decimal("150.50"),
            zone_type=ZoneType.RESISTANCE,
            strength_score=Decimal("6.5"),
            touch_count=5,
            first_touch_date=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
            last_touch_date=datetime(2025, 1, 15, 14, 30, 0, tzinfo=UTC),
            average_volume=Decimal("2000000"),
            highest_volume_touch=Decimal("3000000"),
            timeframe=Timeframe.FOUR_HOUR
        )

        result = zone.to_dict()

        assert result["zone_id"] == "resistance_150.50_4h"
        assert result["price_level"] == "150.50"
        assert result["zone_type"] == "resistance"
        assert result["strength_score"] == "6.5"
        assert result["touch_count"] == 5
        assert result["first_touch_date"] == "2025-01-01T12:00:00+00:00"
        assert result["last_touch_date"] == "2025-01-15T14:30:00+00:00"
        assert result["average_volume"] == "2000000"
        assert result["highest_volume_touch"] == "3000000"
        assert result["timeframe"] == "4h"

    def test_zone_to_jsonl_line(self):
        """Test Zone.to_jsonl_line() produces valid JSON."""
        import json

        zone = Zone(
            price_level=Decimal("150.50"),
            zone_type=ZoneType.SUPPORT,
            strength_score=Decimal("5.0"),
            touch_count=3,
            first_touch_date=datetime(2025, 1, 1, tzinfo=UTC),
            last_touch_date=datetime(2025, 1, 15, tzinfo=UTC),
            average_volume=Decimal("1000000"),
            highest_volume_touch=Decimal("1500000"),
            timeframe=Timeframe.DAILY
        )

        jsonl_line = zone.to_jsonl_line()

        # Verify it's valid JSON
        parsed = json.loads(jsonl_line)
        assert parsed["zone_id"] == "support_150.50_daily"
        assert parsed["price_level"] == "150.50"


class TestZoneTouch:
    """Test ZoneTouch dataclass validation and serialization."""

    def test_zone_touch_valid_creation(self):
        """Test creating a valid ZoneTouch."""
        touch = ZoneTouch(
            zone_id="support_150.50_daily",
            touch_date=datetime(2025, 1, 10, tzinfo=UTC),
            price=Decimal("150.75"),
            volume=Decimal("2000000"),
            touch_type=TouchType.BOUNCE
        )

        assert touch.zone_id == "support_150.50_daily"
        assert touch.price == Decimal("150.75")
        assert touch.volume == Decimal("2000000")
        assert touch.touch_type == TouchType.BOUNCE

    def test_zone_touch_negative_price_raises_error(self):
        """Test ZoneTouch with negative price raises ValueError."""
        with pytest.raises(ValueError, match="price must be positive"):
            ZoneTouch(
                zone_id="support_150.50_daily",
                touch_date=datetime(2025, 1, 10, tzinfo=UTC),
                price=Decimal("-10.0"),
                volume=Decimal("2000000"),
                touch_type=TouchType.BOUNCE
            )

    def test_zone_touch_negative_volume_raises_error(self):
        """Test ZoneTouch with negative volume raises ValueError."""
        with pytest.raises(ValueError, match="volume must be non-negative"):
            ZoneTouch(
                zone_id="support_150.50_daily",
                touch_date=datetime(2025, 1, 10, tzinfo=UTC),
                price=Decimal("150.75"),
                volume=Decimal("-1000"),
                touch_type=TouchType.BOUNCE
            )

    def test_zone_touch_to_dict(self):
        """Test ZoneTouch.to_dict() serialization."""
        touch = ZoneTouch(
            zone_id="resistance_200.00_daily",
            touch_date=datetime(2025, 1, 12, 10, 30, 0, tzinfo=UTC),
            price=Decimal("199.80"),
            volume=Decimal("3000000"),
            touch_type=TouchType.REJECTION
        )

        result = touch.to_dict()

        assert result["zone_id"] == "resistance_200.00_daily"
        assert result["touch_date"] == "2025-01-12T10:30:00+00:00"
        assert result["price"] == "199.80"
        assert result["volume"] == "3000000"
        assert result["touch_type"] == "rejection"

    def test_zone_touch_to_jsonl_line(self):
        """Test ZoneTouch.to_jsonl_line() produces valid JSON."""
        import json

        touch = ZoneTouch(
            zone_id="support_150.50_daily",
            touch_date=datetime(2025, 1, 10, tzinfo=UTC),
            price=Decimal("150.75"),
            volume=Decimal("2000000"),
            touch_type=TouchType.BREAKOUT
        )

        jsonl_line = touch.to_jsonl_line()

        # Verify valid JSON
        parsed = json.loads(jsonl_line)
        assert parsed["zone_id"] == "support_150.50_daily"
        assert parsed["touch_type"] == "breakout"


class TestProximityAlert:
    """Test ProximityAlert dataclass validation and serialization."""

    def test_proximity_alert_valid_creation(self):
        """Test creating a valid ProximityAlert."""
        alert = ProximityAlert(
            symbol="AAPL",
            zone_id="support_150.50_daily",
            current_price=Decimal("152.00"),
            zone_price=Decimal("150.50"),
            distance_percent=Decimal("0.99"),
            direction="approaching_support",
            timestamp=datetime(2025, 1, 20, tzinfo=UTC)
        )

        assert alert.symbol == "AAPL"
        assert alert.zone_id == "support_150.50_daily"
        assert alert.current_price == Decimal("152.00")
        assert alert.zone_price == Decimal("150.50")
        assert alert.distance_percent == Decimal("0.99")
        assert alert.direction == "approaching_support"

    def test_proximity_alert_distance_exceeds_threshold_raises_error(self):
        """Test ProximityAlert with distance > 2% raises ValueError."""
        with pytest.raises(ValueError, match="distance_percent must be 0-2%"):
            ProximityAlert(
                symbol="AAPL",
                zone_id="support_150.50_daily",
                current_price=Decimal("155.00"),
                zone_price=Decimal("150.50"),
                distance_percent=Decimal("2.5"),  # Exceeds 2% threshold
                direction="approaching_support",
                timestamp=datetime(2025, 1, 20, tzinfo=UTC)
            )

    def test_proximity_alert_negative_distance_raises_error(self):
        """Test ProximityAlert with negative distance raises ValueError."""
        with pytest.raises(ValueError, match="distance_percent must be 0-2%"):
            ProximityAlert(
                symbol="AAPL",
                zone_id="support_150.50_daily",
                current_price=Decimal("152.00"),
                zone_price=Decimal("150.50"),
                distance_percent=Decimal("-0.5"),
                direction="approaching_support",
                timestamp=datetime(2025, 1, 20, tzinfo=UTC)
            )

    def test_proximity_alert_invalid_direction_raises_error(self):
        """Test ProximityAlert with invalid direction raises ValueError."""
        with pytest.raises(ValueError, match="direction must be 'approaching_support' or 'approaching_resistance'"):
            ProximityAlert(
                symbol="AAPL",
                zone_id="support_150.50_daily",
                current_price=Decimal("152.00"),
                zone_price=Decimal("150.50"),
                distance_percent=Decimal("0.99"),
                direction="invalid_direction",  # Invalid
                timestamp=datetime(2025, 1, 20, tzinfo=UTC)
            )

    def test_proximity_alert_negative_current_price_raises_error(self):
        """Test ProximityAlert with negative current_price raises ValueError."""
        with pytest.raises(ValueError, match="current_price must be positive"):
            ProximityAlert(
                symbol="AAPL",
                zone_id="support_150.50_daily",
                current_price=Decimal("-10.0"),
                zone_price=Decimal("150.50"),
                distance_percent=Decimal("0.99"),
                direction="approaching_support",
                timestamp=datetime(2025, 1, 20, tzinfo=UTC)
            )

    def test_proximity_alert_negative_zone_price_raises_error(self):
        """Test ProximityAlert with negative zone_price raises ValueError."""
        with pytest.raises(ValueError, match="zone_price must be positive"):
            ProximityAlert(
                symbol="AAPL",
                zone_id="support_150.50_daily",
                current_price=Decimal("152.00"),
                zone_price=Decimal("-150.50"),
                distance_percent=Decimal("0.99"),
                direction="approaching_support",
                timestamp=datetime(2025, 1, 20, tzinfo=UTC)
            )

    def test_proximity_alert_to_dict(self):
        """Test ProximityAlert.to_dict() serialization."""
        alert = ProximityAlert(
            symbol="TSLA",
            zone_id="resistance_250.00_daily",
            current_price=Decimal("248.50"),
            zone_price=Decimal("250.00"),
            distance_percent=Decimal("0.60"),
            direction="approaching_resistance",
            timestamp=datetime(2025, 1, 22, 15, 45, 0, tzinfo=UTC)
        )

        result = alert.to_dict()

        assert result["symbol"] == "TSLA"
        assert result["zone_id"] == "resistance_250.00_daily"
        assert result["current_price"] == "248.50"
        assert result["zone_price"] == "250.00"
        assert result["distance_percent"] == "0.60"
        assert result["direction"] == "approaching_resistance"
        assert result["timestamp"] == "2025-01-22T15:45:00+00:00"

    def test_proximity_alert_to_jsonl_line(self):
        """Test ProximityAlert.to_jsonl_line() produces valid JSON."""
        import json

        alert = ProximityAlert(
            symbol="AAPL",
            zone_id="support_150.50_daily",
            current_price=Decimal("152.00"),
            zone_price=Decimal("150.50"),
            distance_percent=Decimal("0.99"),
            direction="approaching_support",
            timestamp=datetime(2025, 1, 20, tzinfo=UTC)
        )

        jsonl_line = alert.to_jsonl_line()

        # Verify valid JSON
        parsed = json.loads(jsonl_line)
        assert parsed["symbol"] == "AAPL"
        assert parsed["direction"] == "approaching_support"
