"""
Unit tests for ZoneDetector service.

Tests swing point detection, clustering, zone building, and main detect_zones API.
"""

import pytest
from datetime import datetime, UTC, timedelta
from decimal import Decimal
import pandas as pd

from src.trading_bot.support_resistance.zone_detector import ZoneDetector
from src.trading_bot.support_resistance.config import ZoneDetectionConfig
from src.trading_bot.support_resistance.models import ZoneType, Timeframe
from src.trading_bot.market_data.market_data_service import MarketDataService


@pytest.fixture
def config():
    """Create test configuration."""
    return ZoneDetectionConfig(
        touch_threshold=3,
        volume_threshold=Decimal("1.5"),
        proximity_threshold_pct=Decimal("2.0"),
        min_days=30,
        tolerance_pct=Decimal("1.5")
    )


@pytest.fixture
def market_data_service():
    """Create mock MarketDataService."""
    # In actual tests, would use pytest-mock or create a proper mock
    return None


@pytest.fixture
def detector(config, market_data_service):
    """Create ZoneDetector instance."""
    return ZoneDetector(config, market_data_service)


class TestSwingPointDetection:
    """Test swing high and swing low detection."""

    def test_identify_swing_highs_with_valid_pattern(self, detector):
        """Test swing high detection with 2 swing highs in sample data."""
        # Given: OHLCV data with 2 swing highs at indices 2 and 5
        ohlcv = pd.DataFrame({
            'date': pd.date_range(start='2025-01-01', periods=8, freq='D'),
            'high': [100, 105, 110, 108, 106, 112, 109, 107]  # 110 and 112 are swing highs
        })

        # When: Identify swing highs
        swing_highs = detector._identify_swing_highs(ohlcv)

        # Then: Should find 2 swing highs
        assert len(swing_highs) == 2
        assert swing_highs[0][1] == Decimal('110')  # First swing high
        assert swing_highs[1][1] == Decimal('112')  # Second swing high

    def test_identify_swing_highs_first_bar_not_swing(self, detector):
        """Test that first bar cannot be a swing high (no previous bar)."""
        # Given: First bar is highest, but should not be identified as swing
        ohlcv = pd.DataFrame({
            'date': pd.date_range(start='2025-01-01', periods=5, freq='D'),
            'high': [110, 105, 102, 108, 106]  # 110 is first, but not swing
        })

        # When: Identify swing highs
        swing_highs = detector._identify_swing_highs(ohlcv)

        # Then: First bar (110) should not be included
        assert all(price != Decimal('110') for _, price in swing_highs)

    def test_identify_swing_highs_last_bar_not_swing(self, detector):
        """Test that last bar cannot be a swing high (no next bar)."""
        # Given: Last bar is highest, but should not be identified as swing
        ohlcv = pd.DataFrame({
            'date': pd.date_range(start='2025-01-01', periods=5, freq='D'),
            'high': [105, 102, 108, 106, 115]  # 115 is last, but not swing
        })

        # When: Identify swing highs
        swing_highs = detector._identify_swing_highs(ohlcv)

        # Then: Last bar (115) should not be included
        assert all(price != Decimal('115') for _, price in swing_highs)

    def test_identify_swing_highs_empty_dataframe(self, detector):
        """Test swing high detection with empty DataFrame."""
        # Given: Empty DataFrame
        ohlcv = pd.DataFrame()

        # When: Identify swing highs
        swing_highs = detector._identify_swing_highs(ohlcv)

        # Then: Should return empty list
        assert swing_highs == []

    def test_identify_swing_lows_with_valid_pattern(self, detector):
        """Test swing low detection with 3 swing lows in sample data."""
        # Given: OHLCV data with 3 swing lows at indices 1, 3, 6
        ohlcv = pd.DataFrame({
            'date': pd.date_range(start='2025-01-01', periods=8, freq='D'),
            'low': [100, 95, 98, 93, 96, 99, 92, 95]  # 95, 93, 92 are swing lows
        })

        # When: Identify swing lows
        swing_lows = detector._identify_swing_lows(ohlcv)

        # Then: Should find 3 swing lows
        assert len(swing_lows) == 3
        assert swing_lows[0][1] == Decimal('95')
        assert swing_lows[1][1] == Decimal('93')
        assert swing_lows[2][1] == Decimal('92')

    def test_identify_swing_lows_ignores_equal_highs(self, detector):
        """Test that equal lows do not qualify as swing lows."""
        # Given: Data with equal lows
        ohlcv = pd.DataFrame({
            'date': pd.date_range(start='2025-01-01', periods=5, freq='D'),
            'low': [100, 95, 95, 95, 100]  # Middle 95s have equal neighbors
        })

        # When: Identify swing lows
        swing_lows = detector._identify_swing_lows(ohlcv)

        # Then: Should not find any swing lows (strict < required, not <=)
        assert len(swing_lows) == 0


class TestSwingPointClustering:
    """Test swing point clustering within tolerance."""

    def test_cluster_swing_points_single_cluster(self, detector):
        """Test that swing points within 1.5% tolerance form single cluster."""
        # Given: 3 swing points within 1.5% of each other
        swing_points = [
            (datetime(2025, 1, 1, tzinfo=UTC), Decimal('100.00')),
            (datetime(2025, 1, 5, tzinfo=UTC), Decimal('101.00')),  # 1% away
            (datetime(2025, 1, 10, tzinfo=UTC), Decimal('100.50'))  # 0.5% away
        ]

        # When: Cluster with 1.5% tolerance
        clusters = detector._cluster_swing_points(swing_points, Decimal('1.5'))

        # Then: Should create single cluster
        assert len(clusters) == 1
        assert len(clusters[0]) == 3

    def test_cluster_swing_points_multiple_clusters(self, detector):
        """Test that swing points >1.5% apart form separate clusters."""
        # Given: 2 groups of swing points >1.5% apart
        swing_points = [
            (datetime(2025, 1, 1, tzinfo=UTC), Decimal('100.00')),
            (datetime(2025, 1, 5, tzinfo=UTC), Decimal('101.00')),  # ~1% from 100
            (datetime(2025, 1, 10, tzinfo=UTC), Decimal('110.00')),  # ~9% from 100
            (datetime(2025, 1, 15, tzinfo=UTC), Decimal('111.00'))  # ~1% from 110
        ]

        # When: Cluster with 1.5% tolerance
        clusters = detector._cluster_swing_points(swing_points, Decimal('1.5'))

        # Then: Should create 2 clusters
        assert len(clusters) == 2
        # First cluster around 100-101
        assert len(clusters[0]) == 2
        # Second cluster around 110-111
        assert len(clusters[1]) == 2

    def test_cluster_swing_points_empty_list(self, detector):
        """Test clustering with empty swing points list."""
        # Given: Empty list
        swing_points = []

        # When: Cluster
        clusters = detector._cluster_swing_points(swing_points, Decimal('1.5'))

        # Then: Should return empty list
        assert clusters == []


class TestZoneBuilding:
    """Test zone building from clusters."""

    def test_build_zones_filters_by_touch_threshold(self, detector):
        """Test that clusters with < touch_threshold touches are filtered out."""
        # Given: Cluster with only 2 touches, threshold = 3
        clusters = [
            [
                (datetime(2025, 1, 1, tzinfo=UTC), Decimal('100.00')),
                (datetime(2025, 1, 5, tzinfo=UTC), Decimal('101.00'))
            ]
        ]

        ohlcv = pd.DataFrame()  # Empty for now

        # When: Build zones with touch_threshold=3
        zones = detector._build_zones_from_clusters(
            clusters,
            ZoneType.SUPPORT,
            ohlcv,
            touch_threshold=3,
            timeframe=Timeframe.DAILY
        )

        # Then: Should be filtered out (2 < 3)
        assert len(zones) == 0

    def test_build_zones_creates_zone_with_sufficient_touches(self, detector):
        """Test that cluster with >= touch_threshold creates a Zone."""
        # Given: Cluster with 4 touches, threshold = 3
        clusters = [
            [
                (datetime(2025, 1, 1, tzinfo=UTC), Decimal('100.00')),
                (datetime(2025, 1, 5, tzinfo=UTC), Decimal('101.00')),
                (datetime(2025, 1, 10, tzinfo=UTC), Decimal('100.50')),
                (datetime(2025, 1, 15, tzinfo=UTC), Decimal('100.75'))
            ]
        ]

        ohlcv = pd.DataFrame()

        # When: Build zones with touch_threshold=3
        zones = detector._build_zones_from_clusters(
            clusters,
            ZoneType.RESISTANCE,
            ohlcv,
            touch_threshold=3,
            timeframe=Timeframe.DAILY
        )

        # Then: Should create 1 zone
        assert len(zones) == 1
        assert zones[0].touch_count == 4
        assert zones[0].zone_type == ZoneType.RESISTANCE
        assert zones[0].timeframe == Timeframe.DAILY

    def test_build_zones_calculates_price_level_as_median(self, detector):
        """Test that price_level is calculated as median of cluster prices."""
        # Given: Cluster with prices [100, 101, 102]
        clusters = [
            [
                (datetime(2025, 1, 1, tzinfo=UTC), Decimal('100.00')),
                (datetime(2025, 1, 5, tzinfo=UTC), Decimal('101.00')),
                (datetime(2025, 1, 10, tzinfo=UTC), Decimal('102.00'))
            ]
        ]

        ohlcv = pd.DataFrame()

        # When: Build zones
        zones = detector._build_zones_from_clusters(
            clusters,
            ZoneType.SUPPORT,
            ohlcv,
            touch_threshold=3,
            timeframe=Timeframe.DAILY
        )

        # Then: Price level should be median (101.00)
        assert len(zones) == 1
        assert zones[0].price_level == Decimal('101.00')

    def test_build_zones_sets_correct_first_and_last_dates(self, detector):
        """Test that first_touch_date and last_touch_date are correctly set."""
        # Given: Cluster with dates spanning Jan 1 to Jan 15
        date1 = datetime(2025, 1, 1, tzinfo=UTC)
        date2 = datetime(2025, 1, 5, tzinfo=UTC)
        date3 = datetime(2025, 1, 15, tzinfo=UTC)

        clusters = [
            [
                (date2, Decimal('100.00')),  # Middle date
                (date1, Decimal('101.00')),  # Earliest date
                (date3, Decimal('100.50'))   # Latest date
            ]
        ]

        ohlcv = pd.DataFrame()

        # When: Build zones
        zones = detector._build_zones_from_clusters(
            clusters,
            ZoneType.SUPPORT,
            ohlcv,
            touch_threshold=3,
            timeframe=Timeframe.DAILY
        )

        # Then: Dates should be min and max
        assert len(zones) == 1
        assert zones[0].first_touch_date == date1
        assert zones[0].last_touch_date == date3


class TestDetectZonesAPI:
    """Test main detect_zones API."""

    def test_detect_zones_validates_empty_symbol(self, detector):
        """Test that detect_zones raises ValueError for empty symbol."""
        with pytest.raises(ValueError, match="symbol must be non-empty"):
            detector.detect_zones("", days=60)

    def test_detect_zones_validates_negative_days(self, detector):
        """Test that detect_zones raises ValueError for negative days."""
        with pytest.raises(ValueError, match="days must be non-negative"):
            detector.detect_zones("AAPL", days=-10)

    def test_detect_zones_returns_empty_for_insufficient_days(self, detector):
        """Test that detect_zones returns empty list if days < min_days."""
        # When: Request detection with insufficient days (20 < 30 minimum)
        zones = detector.detect_zones("AAPL", days=20)

        # Then: Should return empty list with warning logged
        assert zones == []
