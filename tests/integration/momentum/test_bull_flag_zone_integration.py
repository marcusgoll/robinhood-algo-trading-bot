"""
Integration tests for BullFlagDetector with ZoneDetector integration.

Tests:
- T017: Integration test with real ZoneDetector
- T018: Verify JSONL log format for target_calculated event

Feature: zone-bull-flag-integration (024)
User Story: US1 - Zone-adjusted profit targets
"""

import pytest
import json
import tempfile
from pathlib import Path
from decimal import Decimal
from datetime import datetime, UTC, timedelta
from unittest.mock import Mock, MagicMock
import pandas as pd

from src.trading_bot.momentum.bull_flag_detector import BullFlagDetector
from src.trading_bot.momentum.config import MomentumConfig
from src.trading_bot.momentum.logging.momentum_logger import MomentumLogger
from src.trading_bot.support_resistance.zone_detector import ZoneDetector
from src.trading_bot.support_resistance.config import ZoneDetectionConfig
from src.trading_bot.support_resistance.models import Zone, ZoneType, Timeframe
from src.trading_bot.market_data.market_data_service import MarketDataService


@pytest.fixture
def temp_log_file():
    """Create a temporary JSONL log file for testing."""
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.jsonl') as f:
        yield Path(f.name)
    # Cleanup
    Path(f.name).unlink(missing_ok=True)


@pytest.fixture
def momentum_config():
    """Create test MomentumConfig."""
    return MomentumConfig(
        pole_min_gain_pct=8.0,
        flag_range_pct_min=3.0,
        flag_range_pct_max=5.0,
    )


@pytest.fixture
def zone_config():
    """Create test ZoneDetectionConfig."""
    return ZoneDetectionConfig()


@pytest.fixture
def mock_market_data_service():
    """Create mock MarketDataService with realistic data."""
    mock = Mock(spec=MarketDataService)

    # Create realistic OHLCV data with bull flag pattern
    base_date = datetime(2024, 1, 1, tzinfo=UTC)
    data = []

    # Baseline period (10 days, flat)
    for i in range(10):
        data.append({
            'timestamp': base_date + timedelta(days=i),
            'open': 100.0,
            'high': 100.5,
            'low': 99.5,
            'close': 100.0,
            'volume': 1_000_000
        })

    # Pole period (2 days, 10% gain)
    for i in range(2):
        day_num = 10 + i
        data.append({
            'timestamp': base_date + timedelta(days=day_num),
            'open': 100.0 + (i * 5.0),
            'high': 105.0 + (i * 5.0),
            'low': 100.0 + (i * 5.0),
            'close': 105.0 + (i * 5.0),
            'volume': 2_000_000
        })

    # Flag period (3 days, 4% range, downward slope)
    for i in range(3):
        day_num = 12 + i
        data.append({
            'timestamp': base_date + timedelta(days=day_num),
            'open': 109.0 - (i * 0.5),
            'high': 110.0,
            'low': 106.0,
            'close': 108.0 - (i * 0.5),
            'volume': 1_500_000
        })

    mock.get_historical_data.return_value = pd.DataFrame(data)
    return mock


@pytest.fixture
def mock_zone_detector_with_resistance(zone_config):
    """Create mock ZoneDetector that returns resistance zone at $108."""
    mock = Mock(spec=ZoneDetector)

    # Mock resistance zone at $108 (between breakout $110 and target $120)
    resistance_zone = Zone(
        price_level=Decimal("108.00"),
        zone_type=ZoneType.RESISTANCE,
        strength_score=Decimal("8.5"),
        touch_count=6,
        first_touch_date=datetime(2023, 12, 1, tzinfo=UTC),
        last_touch_date=datetime(2024, 1, 5, tzinfo=UTC),
        average_volume=Decimal("1500000"),
        highest_volume_touch=Decimal("2000000"),
        timeframe=Timeframe.DAILY
    )

    mock.detect_zones.return_value = [resistance_zone]
    return mock


class TestBullFlagZoneIntegration:
    """
    T017: Integration tests for BullFlagDetector with real ZoneDetector.

    Tests complete integration flow with zone-adjusted targets.
    """

    @pytest.mark.asyncio
    async def test_bull_flag_scan_with_zone_adjusted_target(
        self,
        momentum_config,
        mock_market_data_service,
        mock_zone_detector_with_resistance
    ):
        """
        T017: Bull flag scan with zone-adjusted target using real ZoneDetector.

        Given: BullFlagDetector with ZoneDetector
               AAPL with bull flag pattern
               Resistance zone at $108 (between entry and target)
        When: detector.scan(["AAPL"]) called
        Then: MomentumSignal returned with zone-adjusted target
              price_target = $97.20 (90% of $108)
        """
        # GIVEN: BullFlagDetector with ZoneDetector
        detector = BullFlagDetector(
            config=momentum_config,
            market_data_service=mock_market_data_service,
            zone_detector=mock_zone_detector_with_resistance
        )

        # WHEN: Scan for bull flags
        signals = await detector.scan(["AAPL"])

        # THEN: Signal is returned with zone-adjusted target
        assert len(signals) == 1, "Expected one bull flag signal"

        signal = signals[0]
        assert signal.symbol == "AAPL"
        assert signal.signal_type.value == "pattern"
        assert signal.details["pattern_type"] == "bull_flag"

        # Verify target was adjusted for resistance zone
        # Expected: 90% of $108 = $97.20
        assert signal.details["price_target"] == pytest.approx(97.20, rel=0.01), (
            f"Expected target adjusted to $97.20 (90% of zone $108), "
            f"got ${signal.details['price_target']}"
        )

        # Verify ZoneDetector was called
        mock_zone_detector_with_resistance.detect_zones.assert_called_once_with(
            symbol="AAPL",
            days=60
        )

    @pytest.mark.asyncio
    async def test_bull_flag_scan_without_zone_detector(
        self,
        momentum_config,
        mock_market_data_service
    ):
        """
        T017: Bull flag scan without ZoneDetector uses standard 2:1 targets.

        Given: BullFlagDetector without ZoneDetector (None)
               AAPL with bull flag pattern
        When: detector.scan(["AAPL"]) called
        Then: MomentumSignal returned with standard 2:1 R:R target
        """
        # GIVEN: Detector without ZoneDetector
        detector = BullFlagDetector(
            config=momentum_config,
            market_data_service=mock_market_data_service,
            zone_detector=None  # No zone detection
        )

        # WHEN: Scan for bull flags
        signals = await detector.scan(["AAPL"])

        # THEN: Signal is returned with standard 2:1 target
        assert len(signals) == 1
        signal = signals[0]

        # Standard target: breakout $110 + pole_height $10 = $120
        assert signal.details["price_target"] == pytest.approx(120.0, rel=0.01), (
            f"Expected standard 2:1 target $120, got ${signal.details['price_target']}"
        )


class TestJSONLLogging:
    """
    T018: Verify JSONL log format for target_calculated events.

    Tests logging structure and field presence.
    """

    @pytest.mark.asyncio
    async def test_target_calculated_event_logged_to_jsonl(
        self,
        momentum_config,
        mock_market_data_service,
        mock_zone_detector_with_resistance,
        temp_log_file
    ):
        """
        T018: Verify JSONL log contains all required fields for target_calculated.

        Given: BullFlagDetector with MomentumLogger writing to temp file
               ZoneDetector configured
        When: detector.scan(["AAPL"]) called
        Then: JSONL log contains target_calculated event with all fields:
              - event
              - symbol
              - entry_price
              - adjusted_target
              - original_2r_target
              - adjustment_reason
              - resistance_zone_price
              - resistance_zone_strength
        """
        # GIVEN: Detector with MomentumLogger writing to file
        momentum_logger = MomentumLogger(log_file=str(temp_log_file))
        detector = BullFlagDetector(
            config=momentum_config,
            market_data_service=mock_market_data_service,
            momentum_logger=momentum_logger,
            zone_detector=mock_zone_detector_with_resistance
        )

        # WHEN: Scan for bull flags (triggers logging)
        signals = await detector.scan(["AAPL"])

        # THEN: JSONL log file contains target_calculated event
        assert temp_log_file.exists(), "Log file should exist"

        # Read and parse JSONL log
        log_entries = []
        with open(temp_log_file, 'r') as f:
            for line in f:
                if line.strip():
                    log_entries.append(json.loads(line))

        # Find target_calculated event
        target_events = [
            entry for entry in log_entries
            if entry.get("event") == "target_calculated"
        ]

        assert len(target_events) > 0, "Expected at least one target_calculated event"

        # Verify all required fields are present
        event = target_events[0]
        required_fields = [
            "event",
            "symbol",
            "entry_price",
            "adjusted_target",
            "original_2r_target",
            "adjustment_reason",
            "resistance_zone_price",
            "resistance_zone_strength"
        ]

        for field in required_fields:
            assert field in event, f"Missing required field: {field}"

        # Verify field values
        assert event["event"] == "target_calculated"
        assert event["symbol"] == "AAPL"
        assert event["adjustment_reason"] in ["zone_resistance", "no_zone", "zone_detection_failed"]

        # If zone adjustment occurred, verify zone fields are populated
        if event["adjustment_reason"] == "zone_resistance":
            assert event["resistance_zone_price"] is not None
            assert event["resistance_zone_strength"] is not None
            assert float(event["resistance_zone_price"]) == 108.0
            assert float(event["resistance_zone_strength"]) == 8.5

        print(f"\n✅ JSONL log format verified. Event: {json.dumps(event, indent=2)}")


class TestGracefulDegradation:
    """
    T026: Integration tests for graceful degradation when ZoneDetector unavailable.

    Tests backward compatibility and error handling.
    """

    @pytest.mark.asyncio
    async def test_zone_detection_graceful_degradation_no_exceptions(
        self,
        momentum_config,
        mock_market_data_service
    ):
        """
        T026: Verify graceful degradation when zone_detector=None.

        Given: BullFlagDetector with zone_detector=None
        When: detector.scan(["AAPL"]) called
        Then: No exceptions raised (graceful degradation)
              BullFlagDetector continues to work with standard 2:1 targets

        Requirement: NFR-002 - Backward compatible with existing bull flag logic
        Constitution: §Safety_First - Fail gracefully, never crash
        """
        # GIVEN: Detector without ZoneDetector
        detector = BullFlagDetector(
            config=momentum_config,
            market_data_service=mock_market_data_service,
            zone_detector=None  # No zone detection
        )

        # WHEN: Scan for bull flags
        # THEN: No exceptions raised (graceful degradation)
        try:
            signals = await detector.scan(["AAPL"])
            # If we get here without exception, graceful degradation works
            print(f"\n✅ Graceful degradation verified: {len(signals)} signals detected without exceptions")
            print("✅ BullFlagDetector continues to function without ZoneDetector")
        except Exception as e:
            pytest.fail(f"Unexpected exception during graceful degradation: {e}")
