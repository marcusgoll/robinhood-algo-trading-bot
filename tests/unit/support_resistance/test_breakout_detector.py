"""
Unit tests for BreakoutDetector

Tests follow TDD approach: Tests written BEFORE implementation.
All tests should FAIL initially (RED), then PASS after implementation (GREEN).
"""

import pytest
from datetime import datetime, UTC
from decimal import Decimal
from unittest.mock import Mock

from src.trading_bot.support_resistance.breakout_detector import BreakoutDetector
from src.trading_bot.support_resistance.breakout_models import (
    BreakoutEvent,
    BreakoutStatus,
    BreakoutSignal,
)
from src.trading_bot.support_resistance.breakout_config import BreakoutConfig
from src.trading_bot.support_resistance.models import Zone, ZoneType, Timeframe


class TestBreakoutDetector:
    """Test suite for BreakoutDetector class"""

    @pytest.fixture
    def config(self):
        """Default breakout configuration"""
        return BreakoutConfig(
            price_threshold_pct=Decimal("1.0"),
            volume_threshold=Decimal("1.3"),
            validation_bars=5,
            strength_bonus=Decimal("2.0"),
        )

    @pytest.fixture
    def mock_market_data(self):
        """Mock market data service"""
        return Mock()

    @pytest.fixture
    def mock_logger(self):
        """Mock zone logger"""
        logger = Mock()
        logger.log_breakout_event = Mock()
        return logger

    @pytest.fixture
    def detector(self, config, mock_market_data, mock_logger):
        """BreakoutDetector instance with mocked dependencies"""
        return BreakoutDetector(
            config=config,
            market_data_service=mock_market_data,
            logger=mock_logger,
        )

    @pytest.fixture
    def resistance_zone(self):
        """Sample resistance zone at $155"""
        return Zone(
            zone_id="zone_123",
            price_level=Decimal("155.00"),
            zone_type=ZoneType.RESISTANCE,
            strength_score=Decimal("5.0"),
            touch_count=3,
            first_touch_date=datetime(2025, 10, 1, tzinfo=UTC),
            last_touch_date=datetime(2025, 10, 15, tzinfo=UTC),
            average_volume=Decimal("1000000"),
            highest_volume_touch=Decimal("1500000"),
            timeframe=Timeframe.DAILY,
        )

    # T010: Valid resistance breakout detection
    def test_detect_breakout_valid_resistance_breakout(
        self, detector, resistance_zone
    ):
        """
        Given: Resistance zone at $155, price $156.60 (+1.03%), volume 1.4x avg
        When: detect_breakout() called
        Then: Returns BreakoutSignal with zone, event, flipped_zone
        """
        # Given
        current_price = Decimal("156.60")  # +1.03% above zone
        current_volume = Decimal("1500000")
        historical_volumes = [Decimal("1000000")] * 20  # 1.5x volume ratio

        # When
        result = detector.detect_breakout(
            zone=resistance_zone,
            current_price=current_price,
            current_volume=current_volume,
            historical_volumes=historical_volumes,
        )

        # Then
        assert result is not None, "Breakout should be detected"
        assert isinstance(result, BreakoutSignal)
        assert result.zone == resistance_zone
        assert isinstance(result.event, BreakoutEvent)
        assert result.event.breakout_price == Decimal("155.00")
        assert result.event.close_price == current_price
        assert result.event.old_zone_type == ZoneType.RESISTANCE
        assert result.event.new_zone_type == ZoneType.SUPPORT
        assert result.event.status == BreakoutStatus.CONFIRMED
        assert result.flipped_zone.zone_type == ZoneType.SUPPORT

    # T011: Insufficient price move rejection
    def test_detect_breakout_insufficient_price_move(
        self, detector, resistance_zone
    ):
        """
        Given: Resistance zone at $155, price $156.00 (+0.65%), volume 1.5x avg
        When: detect_breakout() called
        Then: Returns None (no breakout - price <1%)
        """
        # Given
        current_price = Decimal("156.00")  # +0.65% (below 1% threshold)
        current_volume = Decimal("1500000")
        historical_volumes = [Decimal("1000000")] * 20  # 1.5x volume ratio

        # When
        result = detector.detect_breakout(
            zone=resistance_zone,
            current_price=current_price,
            current_volume=current_volume,
            historical_volumes=historical_volumes,
        )

        # Then
        assert result is None, "Breakout should NOT be detected (price <1%)"

    # T012: Insufficient volume rejection
    def test_detect_breakout_insufficient_volume(
        self, detector, resistance_zone
    ):
        """
        Given: Resistance zone at $155, price $157.00 (+1.29%), volume 0.9x avg
        When: detect_breakout() called
        Then: Returns None (no breakout - volume <1.3x)
        """
        # Given
        current_price = Decimal("157.00")  # +1.29% (above 1% threshold)
        current_volume = Decimal("900000")
        historical_volumes = [Decimal("1000000")] * 20  # 0.9x volume ratio

        # When
        result = detector.detect_breakout(
            zone=resistance_zone,
            current_price=current_price,
            current_volume=current_volume,
            historical_volumes=historical_volumes,
        )

        # Then
        assert result is None, "Breakout should NOT be detected (volume <1.3x)"

    # T013: Input validation tests
    def test_detect_breakout_invalid_zone(self, detector):
        """
        Given: None zone
        When: detect_breakout() called
        Then: Raises ValueError
        """
        with pytest.raises(ValueError, match="zone cannot be None"):
            detector.detect_breakout(
                zone=None,
                current_price=Decimal("156.60"),
                current_volume=Decimal("1500000"),
                historical_volumes=[Decimal("1000000")] * 20,
            )

    def test_detect_breakout_negative_price(self, detector, resistance_zone):
        """
        Given: Negative current_price
        When: detect_breakout() called
        Then: Raises ValueError
        """
        with pytest.raises(ValueError, match="current_price must be > 0"):
            detector.detect_breakout(
                zone=resistance_zone,
                current_price=Decimal("-10.00"),
                current_volume=Decimal("1500000"),
                historical_volumes=[Decimal("1000000")] * 20,
            )

    def test_detect_breakout_empty_volumes(self, detector, resistance_zone):
        """
        Given: Empty historical_volumes list
        When: detect_breakout() called
        Then: Raises ValueError
        """
        with pytest.raises(ValueError, match="historical_volumes must have"):
            detector.detect_breakout(
                zone=resistance_zone,
                current_price=Decimal("156.60"),
                current_volume=Decimal("1500000"),
                historical_volumes=[],
            )

    # T020: Zone flipping tests
    def test_flip_zone_resistance_to_support(self, detector, resistance_zone):
        """
        Given: Resistance zone (strength=5.0), BreakoutEvent (RESISTANCE->SUPPORT)
        When: flip_zone() called
        Then: Returns new Zone with SUPPORT type, strength=7.0, all fields preserved
        """
        # Given
        breakout_event = BreakoutEvent(
            event_id="evt_001",
            zone_id="zone_123",
            timestamp=datetime.now(UTC),
            breakout_price=Decimal("155.00"),
            close_price=Decimal("156.60"),
            volume=Decimal("1500000"),
            volume_ratio=Decimal("1.5"),
            old_zone_type=ZoneType.RESISTANCE,
            new_zone_type=ZoneType.SUPPORT,
            status=BreakoutStatus.CONFIRMED,
            timeframe=Timeframe.DAILY,
        )

        # When
        flipped_zone = detector.flip_zone(
            zone=resistance_zone,
            breakout_event=breakout_event,
        )

        # Then
        assert flipped_zone.zone_type == ZoneType.SUPPORT
        assert flipped_zone.strength_score == Decimal("7.0")  # 5.0 + 2.0 bonus
        assert flipped_zone.price_level == resistance_zone.price_level
        assert flipped_zone.touch_count == resistance_zone.touch_count
        assert flipped_zone.zone_id == resistance_zone.zone_id
        assert flipped_zone.average_volume == resistance_zone.average_volume

    # T021: Zone type mismatch validation
    def test_flip_zone_type_mismatch_raises_error(self, detector, resistance_zone):
        """
        Given: Resistance zone, BreakoutEvent with old_zone_type=SUPPORT (mismatch)
        When: flip_zone() called
        Then: Raises ValueError (type mismatch)
        """
        # Given
        breakout_event = BreakoutEvent(
            event_id="evt_001",
            zone_id="zone_123",
            timestamp=datetime.now(UTC),
            breakout_price=Decimal("155.00"),
            close_price=Decimal("145.00"),
            volume=Decimal("1500000"),
            volume_ratio=Decimal("1.5"),
            old_zone_type=ZoneType.SUPPORT,  # MISMATCH!
            new_zone_type=ZoneType.RESISTANCE,
            status=BreakoutStatus.CONFIRMED,
            timeframe=Timeframe.DAILY,
        )

        # When/Then
        with pytest.raises(ValueError, match="zone_type mismatch"):
            detector.flip_zone(
                zone=resistance_zone,
                breakout_event=breakout_event,
            )

    # T031: BreakoutEvent serialization test
    def test_breakout_event_to_jsonl_line(self):
        """
        Given: BreakoutEvent with sample data
        When: to_jsonl_line() called
        Then: Returns single-line JSON with ISO timestamps, Decimal as strings
        """
        import json

        # Given
        event = BreakoutEvent(
            event_id="evt_001",
            zone_id="zone_123",
            timestamp=datetime(2025, 10, 21, 12, 0, 0, tzinfo=UTC),
            breakout_price=Decimal("155.00"),
            close_price=Decimal("156.60"),
            volume=Decimal("1500000"),
            volume_ratio=Decimal("1.5"),
            old_zone_type=ZoneType.RESISTANCE,
            new_zone_type=ZoneType.SUPPORT,
            status=BreakoutStatus.CONFIRMED,
            timeframe=Timeframe.DAILY,
        )

        # When
        jsonl_line = event.to_jsonl_line()

        # Then
        assert "\n" not in jsonl_line, "Should be single line (no newlines)"
        parsed = json.loads(jsonl_line)
        assert parsed["event_id"] == "evt_001"
        assert parsed["breakout_price"] == "155.00"  # Decimal as string
        assert parsed["timestamp"] == "2025-10-21T12:00:00+00:00"  # ISO format
        assert parsed["old_zone_type"] == "resistance"  # lowercase enum
        assert parsed["status"] == "confirmed"
