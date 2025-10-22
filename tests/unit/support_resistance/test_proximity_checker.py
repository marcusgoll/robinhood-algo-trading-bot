"""
Unit tests for ProximityChecker

Tests proximity alert generation, nearest zone finding, and validation.
"""

import pytest
from datetime import datetime, UTC
from decimal import Decimal
from pathlib import Path
import tempfile

from src.trading_bot.support_resistance.proximity_checker import ProximityChecker
from src.trading_bot.support_resistance.config import ZoneDetectionConfig
from src.trading_bot.support_resistance.models import Zone, ZoneType, Timeframe, ProximityAlert
from src.trading_bot.support_resistance.zone_logger import ZoneLogger


@pytest.fixture
def config():
    """Provide ZoneDetectionConfig with default settings."""
    return ZoneDetectionConfig(
        touch_threshold=3,
        volume_threshold=Decimal("1.5"),
        proximity_threshold_pct=Decimal("2.0"),
        min_days=30,
        tolerance_pct=Decimal("1.5")
    )


@pytest.fixture
def temp_log_dir():
    """Provide temporary directory for zone logs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def zone_logger(temp_log_dir):
    """Provide ZoneLogger with temporary log directory."""
    return ZoneLogger(log_dir=temp_log_dir)


@pytest.fixture
def checker(config, zone_logger):
    """Provide ProximityChecker instance."""
    return ProximityChecker(config, zone_logger)


@pytest.fixture
def sample_zones():
    """Provide sample zones for testing."""
    base_date = datetime(2025, 1, 1, tzinfo=UTC)
    return [
        Zone(
            price_level=Decimal("150.00"),
            zone_type=ZoneType.SUPPORT,
            strength_score=Decimal("5"),
            touch_count=5,
            first_touch_date=base_date,
            last_touch_date=base_date,
            average_volume=Decimal("1000000"),
            highest_volume_touch=Decimal("1500000"),
            timeframe=Timeframe.DAILY
        ),
        Zone(
            price_level=Decimal("145.00"),
            zone_type=ZoneType.SUPPORT,
            strength_score=Decimal("4"),
            touch_count=4,
            first_touch_date=base_date,
            last_touch_date=base_date,
            average_volume=Decimal("1000000"),
            highest_volume_touch=Decimal("1500000"),
            timeframe=Timeframe.DAILY
        ),
        Zone(
            price_level=Decimal("160.00"),
            zone_type=ZoneType.RESISTANCE,
            strength_score=Decimal("6"),
            touch_count=6,
            first_touch_date=base_date,
            last_touch_date=base_date,
            average_volume=Decimal("1000000"),
            highest_volume_touch=Decimal("1500000"),
            timeframe=Timeframe.DAILY
        ),
        Zone(
            price_level=Decimal("165.00"),
            zone_type=ZoneType.RESISTANCE,
            strength_score=Decimal("3"),
            touch_count=3,
            first_touch_date=base_date,
            last_touch_date=base_date,
            average_volume=Decimal("1000000"),
            highest_volume_touch=Decimal("1500000"),
            timeframe=Timeframe.DAILY
        ),
    ]


class TestProximityCheckerInitialization:
    """Tests for ProximityChecker initialization."""

    def test_initialization_with_config_and_logger(self, config, zone_logger):
        """Test initialization with both config and logger."""
        checker = ProximityChecker(config, zone_logger)
        assert checker.config == config
        assert checker.logger == zone_logger

    def test_initialization_with_default_logger(self, config):
        """Test initialization creates default logger when None provided."""
        checker = ProximityChecker(config)
        assert checker.config == config
        assert checker.logger is not None
        assert isinstance(checker.logger, ZoneLogger)


class TestCheckProximity:
    """Tests for check_proximity method."""

    def test_check_proximity_within_threshold_support(self, checker, sample_zones):
        """Test alert generated when price within 2% of support zone."""
        current_price = Decimal("151.00")  # 0.66% from 150.00 support
        alerts = checker.check_proximity("AAPL", current_price, sample_zones)

        assert len(alerts) == 1
        assert alerts[0].symbol == "AAPL"
        assert alerts[0].zone_price == Decimal("150.00")
        assert alerts[0].current_price == current_price
        assert alerts[0].direction == "approaching_support"
        assert alerts[0].distance_percent < Decimal("2.0")

    def test_check_proximity_within_threshold_resistance(self, checker, sample_zones):
        """Test alert generated when price within 2% of resistance zone."""
        current_price = Decimal("158.00")  # 1.25% from 160.00 resistance
        alerts = checker.check_proximity("AAPL", current_price, sample_zones)

        assert len(alerts) == 1
        assert alerts[0].zone_price == Decimal("160.00")
        assert alerts[0].direction == "approaching_resistance"

    def test_check_proximity_multiple_alerts(self, checker):
        """Test multiple alerts when price near multiple zones."""
        base_date = datetime(2025, 1, 1, tzinfo=UTC)
        # Create two zones very close to each other
        zones = [
            Zone(
                price_level=Decimal("150.00"),
                zone_type=ZoneType.SUPPORT,
                strength_score=Decimal("5"),
                touch_count=5,
                first_touch_date=base_date,
                last_touch_date=base_date,
                average_volume=Decimal("1000000"),
                highest_volume_touch=Decimal("1500000"),
                timeframe=Timeframe.DAILY
            ),
            Zone(
                price_level=Decimal("151.00"),
                zone_type=ZoneType.SUPPORT,
                strength_score=Decimal("4"),
                touch_count=4,
                first_touch_date=base_date,
                last_touch_date=base_date,
                average_volume=Decimal("1000000"),
                highest_volume_touch=Decimal("1500000"),
                timeframe=Timeframe.DAILY
            ),
        ]

        current_price = Decimal("151.50")  # Within 2% of both zones
        alerts = checker.check_proximity("AAPL", current_price, zones)

        assert len(alerts) == 2

    def test_check_proximity_outside_threshold(self, checker, sample_zones):
        """Test no alert when price outside 2% threshold."""
        current_price = Decimal("200.00")  # Far from all zones
        alerts = checker.check_proximity("AAPL", current_price, sample_zones)

        assert len(alerts) == 0

    def test_check_proximity_empty_zones(self, checker):
        """Test returns empty list when no zones provided."""
        alerts = checker.check_proximity("AAPL", Decimal("150.00"), [])
        assert alerts == []

    def test_check_proximity_empty_symbol_raises_error(self, checker, sample_zones):
        """Test ValueError raised when symbol is empty."""
        with pytest.raises(ValueError, match="symbol must be non-empty"):
            checker.check_proximity("", Decimal("150.00"), sample_zones)

    def test_check_proximity_whitespace_symbol_raises_error(self, checker, sample_zones):
        """Test ValueError raised when symbol is only whitespace."""
        with pytest.raises(ValueError, match="symbol must be non-empty"):
            checker.check_proximity("   ", Decimal("150.00"), sample_zones)

    def test_check_proximity_zero_price_raises_error(self, checker, sample_zones):
        """Test ValueError raised when price is zero."""
        with pytest.raises(ValueError, match="current_price must be positive"):
            checker.check_proximity("AAPL", Decimal("0"), sample_zones)

    def test_check_proximity_negative_price_raises_error(self, checker, sample_zones):
        """Test ValueError raised when price is negative."""
        with pytest.raises(ValueError, match="current_price must be positive"):
            checker.check_proximity("AAPL", Decimal("-10.00"), sample_zones)

    def test_check_proximity_exact_zone_price(self, checker, sample_zones):
        """Test alert generated when price exactly at zone level (0% distance)."""
        current_price = Decimal("150.00")  # Exact match with support zone
        alerts = checker.check_proximity("AAPL", current_price, sample_zones)

        assert len(alerts) == 1
        assert alerts[0].distance_percent == Decimal("0")

    def test_check_proximity_alert_has_timestamp(self, checker, sample_zones):
        """Test proximity alert includes timestamp in UTC."""
        current_price = Decimal("151.00")
        alerts = checker.check_proximity("AAPL", current_price, sample_zones)

        assert len(alerts) == 1
        assert alerts[0].timestamp is not None
        assert alerts[0].timestamp.tzinfo == UTC

    def test_check_proximity_distance_calculation_accuracy(self, checker):
        """Test distance percentage calculated accurately."""
        base_date = datetime(2025, 1, 1, tzinfo=UTC)
        zone = Zone(
            price_level=Decimal("100.00"),
            zone_type=ZoneType.SUPPORT,
            strength_score=Decimal("5"),
            touch_count=5,
            first_touch_date=base_date,
            last_touch_date=base_date,
            average_volume=Decimal("1000000"),
            highest_volume_touch=Decimal("1500000"),
            timeframe=Timeframe.DAILY
        )

        current_price = Decimal("101.50")  # 1.5% above zone
        alerts = checker.check_proximity("AAPL", current_price, [zone])

        assert len(alerts) == 1
        # Distance should be abs((101.50 - 100.00) / 100.00) * 100 = 1.5%
        assert alerts[0].distance_percent == Decimal("1.50")


class TestFindNearestSupport:
    """Tests for find_nearest_support method."""

    def test_find_nearest_support_single_zone(self, checker):
        """Test returns nearest support zone below current price."""
        base_date = datetime(2025, 1, 1, tzinfo=UTC)
        zones = [
            Zone(
                price_level=Decimal("150.00"),
                zone_type=ZoneType.SUPPORT,
                strength_score=Decimal("5"),
                touch_count=5,
                first_touch_date=base_date,
                last_touch_date=base_date,
                average_volume=Decimal("1000000"),
                highest_volume_touch=Decimal("1500000"),
                timeframe=Timeframe.DAILY
            ),
        ]

        nearest = checker.find_nearest_support(Decimal("152.00"), zones)
        assert nearest is not None
        assert nearest.price_level == Decimal("150.00")

    def test_find_nearest_support_multiple_zones(self, checker, sample_zones):
        """Test returns closest support zone when multiple exist."""
        current_price = Decimal("152.00")
        # sample_zones has support at 150.00 and 145.00
        nearest = checker.find_nearest_support(current_price, sample_zones)

        assert nearest is not None
        assert nearest.price_level == Decimal("150.00")  # Closest below 152.00

    def test_find_nearest_support_no_zones_below_price(self, checker, sample_zones):
        """Test returns None when no support zones below current price."""
        current_price = Decimal("140.00")  # Below all support zones
        nearest = checker.find_nearest_support(current_price, sample_zones)

        assert nearest is None

    def test_find_nearest_support_empty_zones(self, checker):
        """Test returns None when no zones provided."""
        nearest = checker.find_nearest_support(Decimal("150.00"), [])
        assert nearest is None

    def test_find_nearest_support_only_resistance_zones(self, checker):
        """Test returns None when only resistance zones exist."""
        base_date = datetime(2025, 1, 1, tzinfo=UTC)
        resistance_zones = [
            Zone(
                price_level=Decimal("160.00"),
                zone_type=ZoneType.RESISTANCE,
                strength_score=Decimal("5"),
                touch_count=5,
                first_touch_date=base_date,
                last_touch_date=base_date,
                average_volume=Decimal("1000000"),
                highest_volume_touch=Decimal("1500000"),
                timeframe=Timeframe.DAILY
            ),
        ]

        nearest = checker.find_nearest_support(Decimal("152.00"), resistance_zones)
        assert nearest is None

    def test_find_nearest_support_price_at_zone_level(self, checker):
        """Test returns None when price exactly at zone level (not below)."""
        base_date = datetime(2025, 1, 1, tzinfo=UTC)
        zones = [
            Zone(
                price_level=Decimal("150.00"),
                zone_type=ZoneType.SUPPORT,
                strength_score=Decimal("5"),
                touch_count=5,
                first_touch_date=base_date,
                last_touch_date=base_date,
                average_volume=Decimal("1000000"),
                highest_volume_touch=Decimal("1500000"),
                timeframe=Timeframe.DAILY
            ),
        ]

        nearest = checker.find_nearest_support(Decimal("150.00"), zones)
        assert nearest is None  # Price must be strictly above zone


class TestFindNearestResistance:
    """Tests for find_nearest_resistance method."""

    def test_find_nearest_resistance_single_zone(self, checker):
        """Test returns nearest resistance zone above current price."""
        base_date = datetime(2025, 1, 1, tzinfo=UTC)
        zones = [
            Zone(
                price_level=Decimal("160.00"),
                zone_type=ZoneType.RESISTANCE,
                strength_score=Decimal("5"),
                touch_count=5,
                first_touch_date=base_date,
                last_touch_date=base_date,
                average_volume=Decimal("1000000"),
                highest_volume_touch=Decimal("1500000"),
                timeframe=Timeframe.DAILY
            ),
        ]

        nearest = checker.find_nearest_resistance(Decimal("152.00"), zones)
        assert nearest is not None
        assert nearest.price_level == Decimal("160.00")

    def test_find_nearest_resistance_multiple_zones(self, checker, sample_zones):
        """Test returns closest resistance zone when multiple exist."""
        current_price = Decimal("152.00")
        # sample_zones has resistance at 160.00 and 165.00
        nearest = checker.find_nearest_resistance(current_price, sample_zones)

        assert nearest is not None
        assert nearest.price_level == Decimal("160.00")  # Closest above 152.00

    def test_find_nearest_resistance_no_zones_above_price(self, checker, sample_zones):
        """Test returns None when no resistance zones above current price."""
        current_price = Decimal("170.00")  # Above all resistance zones
        nearest = checker.find_nearest_resistance(current_price, sample_zones)

        assert nearest is None

    def test_find_nearest_resistance_empty_zones(self, checker):
        """Test returns None when no zones provided."""
        nearest = checker.find_nearest_resistance(Decimal("150.00"), [])
        assert nearest is None

    def test_find_nearest_resistance_only_support_zones(self, checker):
        """Test returns None when only support zones exist."""
        base_date = datetime(2025, 1, 1, tzinfo=UTC)
        support_zones = [
            Zone(
                price_level=Decimal("150.00"),
                zone_type=ZoneType.SUPPORT,
                strength_score=Decimal("5"),
                touch_count=5,
                first_touch_date=base_date,
                last_touch_date=base_date,
                average_volume=Decimal("1000000"),
                highest_volume_touch=Decimal("1500000"),
                timeframe=Timeframe.DAILY
            ),
        ]

        nearest = checker.find_nearest_resistance(Decimal("152.00"), support_zones)
        assert nearest is None

    def test_find_nearest_resistance_price_at_zone_level(self, checker):
        """Test returns None when price exactly at zone level (not above)."""
        base_date = datetime(2025, 1, 1, tzinfo=UTC)
        zones = [
            Zone(
                price_level=Decimal("160.00"),
                zone_type=ZoneType.RESISTANCE,
                strength_score=Decimal("5"),
                touch_count=5,
                first_touch_date=base_date,
                last_touch_date=base_date,
                average_volume=Decimal("1000000"),
                highest_volume_touch=Decimal("1500000"),
                timeframe=Timeframe.DAILY
            ),
        ]

        nearest = checker.find_nearest_resistance(Decimal("160.00"), zones)
        assert nearest is None  # Price must be strictly below zone
