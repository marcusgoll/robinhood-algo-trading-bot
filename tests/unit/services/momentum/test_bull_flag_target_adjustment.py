"""
Unit tests for BullFlagDetector target adjustment with zone detection.

Tests:
- T010: _adjust_target_for_zones returns zone-adjusted target when resistance closer
- T011: _adjust_target_for_zones returns original target when no zone within 5%
- T012: _adjust_target_for_zones measures zone detection performance <50ms

Feature: zone-bull-flag-integration (024)
User Story: US1 - Zone-adjusted profit targets
"""

import pytest
import logging
from decimal import Decimal
from datetime import datetime, UTC
from unittest.mock import Mock, patch
import time

from src.trading_bot.momentum.bull_flag_detector import BullFlagDetector

logger = logging.getLogger(__name__)
from src.trading_bot.momentum.config import MomentumConfig
from src.trading_bot.momentum.schemas.momentum_signal import TargetCalculation
from src.trading_bot.support_resistance.zone_detector import ZoneDetector
from src.trading_bot.support_resistance.models import Zone, ZoneType, Timeframe
from src.trading_bot.market_data.market_data_service import MarketDataService


@pytest.fixture
def mock_market_data_service():
    """Create a mock MarketDataService for testing."""
    return Mock(spec=MarketDataService)


@pytest.fixture
def mock_zone_detector():
    """Create a mock ZoneDetector for testing."""
    return Mock(spec=ZoneDetector)


@pytest.fixture
def momentum_config():
    """Create a test MomentumConfig."""
    return MomentumConfig(
        pole_min_gain_pct=8.0,
        flag_range_pct_min=3.0,
        flag_range_pct_max=5.0,
    )


@pytest.fixture
def bull_flag_detector(momentum_config, mock_market_data_service, mock_zone_detector):
    """Create a BullFlagDetector instance with mocked dependencies."""
    detector = BullFlagDetector(
        config=momentum_config,
        market_data_service=mock_market_data_service,
        zone_detector=mock_zone_detector
    )
    return detector


class TestAdjustTargetForZones:
    """
    T010-T012: Test suite for _adjust_target_for_zones() method.

    Tests zone-adjusted target calculation with various scenarios:
    1. Resistance zone closer than 2:1 target → adjust to 90% of zone
    2. No resistance zone within 5% → keep original 2:1 target
    3. Zone detection performance < 50ms

    Coverage target: 100% (all branches)
    """

    def test_adjust_target_returns_zone_adjusted_when_resistance_closer(
        self, bull_flag_detector, mock_zone_detector
    ):
        """
        T010 [RED]: Zone-adjusted target when resistance is closer than 2:1 target.

        Given: Bull flag entry at $150.00
               2:1 R:R target at $156.00
               Resistance zone at $155.00 (strength=7)
        When: _adjust_target_for_zones() called
        Then: Returns TargetCalculation with:
              - adjusted_target = $139.50 (90% of $155.00)
              - original_2r_target = $156.00
              - adjustment_reason = "zone_resistance"
              - resistance_zone_price = $155.00
              - resistance_zone_strength = 7
        """
        # GIVEN: Entry price, original target, and resistance zone
        entry_price = Decimal("150.00")
        original_target = Decimal("156.00")
        symbol = "AAPL"

        # Mock zone at $155.00 (between entry $150 and target $156)
        resistance_zone = Zone(
            price_level=Decimal("155.00"),
            zone_type=ZoneType.RESISTANCE,
            strength_score=Decimal("7.0"),
            touch_count=5,
            first_touch_date=datetime(2024, 1, 1, tzinfo=UTC),
            last_touch_date=datetime(2024, 1, 15, tzinfo=UTC),
            average_volume=Decimal("1000000"),
            highest_volume_touch=Decimal("1500000"),
            timeframe=Timeframe.DAILY
        )

        # Mock ZoneDetector.detect_zones() to return the resistance zone
        mock_zone_detector.detect_zones.return_value = [resistance_zone]

        # WHEN: _adjust_target_for_zones() is called
        result = bull_flag_detector._adjust_target_for_zones(
            symbol=symbol,
            entry_price=entry_price,
            original_target=original_target
        )

        # THEN: Target is adjusted to 90% of resistance zone
        assert isinstance(result, TargetCalculation)
        assert result.adjusted_target == Decimal("139.50")  # 155.00 * 0.90
        assert result.original_2r_target == original_target
        assert result.adjustment_reason == "zone_resistance"
        assert result.resistance_zone_price == Decimal("155.00")
        assert result.resistance_zone_strength == Decimal("7.0")

        # Verify ZoneDetector was called with correct parameters
        mock_zone_detector.detect_zones.assert_called_once_with(
            symbol=symbol,
            days=60
        )

    def test_adjust_target_returns_original_when_no_zone_within_range(
        self, bull_flag_detector, mock_zone_detector
    ):
        """
        T011 [RED]: Original target when no resistance zone within 5%.

        Given: Bull flag entry at $150.00
               2:1 R:R target at $156.00
               No resistance zones within $150 * 1.05 = $157.50
        When: _adjust_target_for_zones() called
        Then: Returns TargetCalculation with:
              - adjusted_target = $156.00 (unchanged)
              - original_2r_target = $156.00
              - adjustment_reason = "no_zone"
              - resistance_zone_price = None
              - resistance_zone_strength = None
        """
        # GIVEN: Entry price, original target, and no nearby zones
        entry_price = Decimal("150.00")
        original_target = Decimal("156.00")
        symbol = "AAPL"

        # Mock zone at $160.00 (beyond 5% search range of $157.50)
        far_resistance_zone = Zone(
            price_level=Decimal("160.00"),
            zone_type=ZoneType.RESISTANCE,
            strength_score=Decimal("8.0"),
            touch_count=6,
            first_touch_date=datetime(2024, 1, 1, tzinfo=UTC),
            last_touch_date=datetime(2024, 1, 15, tzinfo=UTC),
            average_volume=Decimal("1000000"),
            highest_volume_touch=Decimal("1500000"),
            timeframe=Timeframe.DAILY
        )

        # Mock ZoneDetector.detect_zones() to return zone outside range
        mock_zone_detector.detect_zones.return_value = [far_resistance_zone]

        # WHEN: _adjust_target_for_zones() is called
        result = bull_flag_detector._adjust_target_for_zones(
            symbol=symbol,
            entry_price=entry_price,
            original_target=original_target
        )

        # THEN: Target is unchanged (no zone within range)
        assert isinstance(result, TargetCalculation)
        assert result.adjusted_target == original_target  # $156.00 unchanged
        assert result.original_2r_target == original_target
        assert result.adjustment_reason == "no_zone"
        assert result.resistance_zone_price is None
        assert result.resistance_zone_strength is None

    def test_adjust_target_performance_under_50ms(
        self, bull_flag_detector, mock_zone_detector
    ):
        """
        T012 [RED]: Zone detection completes in <50ms P95.

        Given: Bull flag entry at $150.00
               2:1 R:R target at $156.00
               Mocked ZoneDetector with 30ms simulated delay
        When: _adjust_target_for_zones() called
        Then: Execution completes in <50ms

        Performance requirement: NFR-001 (zone detection <50ms P95)
        """
        # GIVEN: Entry price and original target
        entry_price = Decimal("150.00")
        original_target = Decimal("156.00")
        symbol = "AAPL"

        # Mock zone detection with realistic 30ms delay
        def mock_detect_zones_with_delay(*args, **kwargs):
            time.sleep(0.030)  # 30ms delay
            return [
                Zone(
                    price_level=Decimal("155.00"),
                    zone_type=ZoneType.RESISTANCE,
                    strength_score=Decimal("7.0"),
                    touch_count=5,
                    first_touch_date=datetime(2024, 1, 1, tzinfo=UTC),
                    last_touch_date=datetime(2024, 1, 15, tzinfo=UTC),
                    average_volume=Decimal("1000000"),
                    highest_volume_touch=Decimal("1500000"),
                    timeframe=Timeframe.DAILY
                )
            ]

        mock_zone_detector.detect_zones.side_effect = mock_detect_zones_with_delay

        # WHEN: _adjust_target_for_zones() is called and timed
        start_time = time.perf_counter()
        result = bull_flag_detector._adjust_target_for_zones(
            symbol=symbol,
            entry_price=entry_price,
            original_target=original_target
        )
        end_time = time.perf_counter()

        # THEN: Execution completes in <50ms
        execution_time_ms = (end_time - start_time) * 1000
        assert execution_time_ms < 50.0, (
            f"Zone detection took {execution_time_ms:.2f}ms, "
            f"must be <50ms (NFR-001)"
        )

        # Verify result is valid
        assert isinstance(result, TargetCalculation)
        assert result.adjusted_target == Decimal("139.50")  # 155.00 * 0.90

    def test_adjust_target_handles_zone_detector_none(
        self, momentum_config, mock_market_data_service
    ):
        """
        T020 [RED]: Graceful degradation when zone_detector is None.

        Given: BullFlagDetector initialized without zone_detector
        When: _adjust_target_for_zones() called
        Then: Returns TargetCalculation with:
              - adjusted_target = original_target (unchanged)
              - adjustment_reason = "zone_detection_failed"
              - resistance_zone_price = None
              - resistance_zone_strength = None

        Note: This test is for US3 (graceful degradation) but included here
        for completeness of _adjust_target_for_zones() coverage.
        """
        # GIVEN: Detector without zone_detector
        detector = BullFlagDetector(
            config=momentum_config,
            market_data_service=mock_market_data_service,
            zone_detector=None  # No zone detector
        )

        entry_price = Decimal("150.00")
        original_target = Decimal("156.00")
        symbol = "AAPL"

        # WHEN: _adjust_target_for_zones() is called
        result = detector._adjust_target_for_zones(
            symbol=symbol,
            entry_price=entry_price,
            original_target=original_target
        )

        # THEN: Target is unchanged, reason is zone_detection_failed
        assert isinstance(result, TargetCalculation)
        assert result.adjusted_target == original_target
        assert result.original_2r_target == original_target
        assert result.adjustment_reason == "zone_detection_failed"
        assert result.resistance_zone_price is None
        assert result.resistance_zone_strength is None

    def test_adjust_target_catches_zone_detector_exceptions(
        self, bull_flag_detector, mock_zone_detector
    ):
        """
        T021 [RED]: Exception handling when ZoneDetector raises errors.

        Given: Mock ZoneDetector that raises ValueError
        When: _adjust_target_for_zones() called
        Then: Returns TargetCalculation with:
              - adjusted_target = original_target (unchanged)
              - adjustment_reason = "zone_detection_failed"
              - resistance_zone_price = None
              - resistance_zone_strength = None
              - Exception is caught, not raised (graceful degradation)

        Safety: Per Constitution §Safety_First - fail gracefully, never crash
        """
        # GIVEN: Entry price and original target
        entry_price = Decimal("150.00")
        original_target = Decimal("156.00")
        symbol = "AAPL"

        # Mock ZoneDetector.detect_zones() to raise ValueError
        mock_zone_detector.detect_zones.side_effect = ValueError("API timeout")

        # WHEN: _adjust_target_for_zones() is called
        result = bull_flag_detector._adjust_target_for_zones(
            symbol=symbol,
            entry_price=entry_price,
            original_target=original_target
        )

        # THEN: Exception is caught, fallback to original target
        assert isinstance(result, TargetCalculation)
        assert result.adjusted_target == original_target  # $156.00 unchanged
        assert result.original_2r_target == original_target
        assert result.adjustment_reason == "zone_detection_failed"
        assert result.resistance_zone_price is None
        assert result.resistance_zone_strength is None

        # Verify ZoneDetector was called (exception occurred during call)
        mock_zone_detector.detect_zones.assert_called_once_with(
            symbol=symbol,
            days=60
        )

    def test_adjust_target_handles_zone_detection_timeout(
        self, bull_flag_detector, mock_zone_detector
    ):
        """
        T022 [RED]: Timeout handling when zone detection takes >50ms.

        Given: Mock ZoneDetector that delays 60ms
        When: _adjust_target_for_zones() called
        Then: Returns TargetCalculation with:
              - adjusted_target = original_target (unchanged)
              - adjustment_reason = "zone_detection_timeout"
              - resistance_zone_price = None
              - resistance_zone_strength = None
              - Timeout warning logged to MomentumLogger

        Performance: Per NFR-001 - zone detection must complete in <50ms P95
        """
        # GIVEN: Entry price and original target
        entry_price = Decimal("150.00")
        original_target = Decimal("156.00")
        symbol = "AAPL"

        # Mock zone detection with 60ms delay (exceeds 50ms threshold)
        def mock_detect_zones_slow(*args, **kwargs):
            time.sleep(0.060)  # 60ms delay
            return [
                Zone(
                    price_level=Decimal("155.00"),
                    zone_type=ZoneType.RESISTANCE,
                    strength_score=Decimal("7.0"),
                    touch_count=5,
                    first_touch_date=datetime(2024, 1, 1, tzinfo=UTC),
                    last_touch_date=datetime(2024, 1, 15, tzinfo=UTC),
                    average_volume=Decimal("1000000"),
                    highest_volume_touch=Decimal("1500000"),
                    timeframe=Timeframe.DAILY
                )
            ]

        mock_zone_detector.detect_zones.side_effect = mock_detect_zones_slow

        # WHEN: _adjust_target_for_zones() is called
        result = bull_flag_detector._adjust_target_for_zones(
            symbol=symbol,
            entry_price=entry_price,
            original_target=original_target
        )

        # THEN: Timeout detected, fallback to original target
        assert isinstance(result, TargetCalculation)
        assert result.adjusted_target == original_target  # $156.00 unchanged
        assert result.original_2r_target == original_target
        assert result.adjustment_reason == "zone_detection_timeout"
        assert result.resistance_zone_price is None
        assert result.resistance_zone_strength is None


class TestTargetCalculationPerformance:
    """
    T030: Performance validation for total target calculation.

    Tests:
    - Total target calculation <100ms P95 (NFR-001)

    Coverage target: Performance validation for zone-adjusted targets
    """

    def test_total_target_calculation_performance_p95_under_100ms(
        self, bull_flag_detector, mock_zone_detector
    ):
        """
        T030 [RED]: Total target calculation completes in <100ms P95.

        Given: BullFlagDetector with real ZoneDetector
        When: _adjust_target_for_zones() called 100 times
        Then: P95 execution time <100ms

        Performance requirement: NFR-001 (total calculation <100ms P95)
        """
        # GIVEN: Entry price and original target
        entry_price = Decimal("150.00")
        original_target = Decimal("156.00")
        symbol = "AAPL"

        # Mock zone detection with realistic data
        resistance_zone = Zone(
            price_level=Decimal("155.00"),
            zone_type=ZoneType.RESISTANCE,
            strength_score=Decimal("7.0"),
            touch_count=5,
            first_touch_date=datetime(2024, 1, 1, tzinfo=UTC),
            last_touch_date=datetime(2024, 1, 15, tzinfo=UTC),
            average_volume=Decimal("1000000"),
            highest_volume_touch=Decimal("1500000"),
            timeframe=Timeframe.DAILY
        )
        mock_zone_detector.detect_zones.return_value = [resistance_zone]

        # WHEN: _adjust_target_for_zones() is called 100 times
        execution_times = []
        for _ in range(100):
            start_time = time.perf_counter()
            bull_flag_detector._adjust_target_for_zones(
                symbol=symbol,
                entry_price=entry_price,
                original_target=original_target
            )
            end_time = time.perf_counter()
            execution_times.append((end_time - start_time) * 1000)  # Convert to ms

        # THEN: P95 execution time <100ms
        execution_times.sort()
        p95_index = int(len(execution_times) * 0.95)
        p95_time = execution_times[p95_index]

        assert p95_time < 100.0, (
            f"P95 target calculation took {p95_time:.2f}ms, "
            f"must be <100ms (NFR-001)"
        )

        # Log performance summary
        avg_time = sum(execution_times) / len(execution_times)
        min_time = min(execution_times)
        max_time = max(execution_times)
        logger.debug(
            f"Target calculation performance (100 iterations): "
            f"min={min_time:.2f}ms, avg={avg_time:.2f}ms, "
            f"p95={p95_time:.2f}ms, max={max_time:.2f}ms"
        )
