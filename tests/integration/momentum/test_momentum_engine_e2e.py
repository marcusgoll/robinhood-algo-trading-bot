"""
E2E Integration Test for Momentum Detection Engine.

Tests the complete workflow of MomentumEngine.scan() with all 3 detectors:
- CatalystDetector (news-driven signals)
- PreMarketScanner (pre-market movers)
- BullFlagDetector (chart pattern signals)

Feature: momentum-detection
Task: T066 - E2E test for complete momentum scan workflow
"""

import pytest
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch
from zoneinfo import ZoneInfo
import pandas as pd

from src.trading_bot.momentum.momentum_ranker import MomentumRanker
from src.trading_bot.momentum.catalyst_detector import CatalystDetector
from src.trading_bot.momentum.premarket_scanner import PreMarketScanner
from src.trading_bot.momentum.bull_flag_detector import BullFlagDetector
from src.trading_bot.momentum.config import MomentumConfig
from src.trading_bot.momentum.logging.momentum_logger import MomentumLogger
from src.trading_bot.momentum.schemas.momentum_signal import MomentumSignal, SignalType
from src.trading_bot.market_data.data_models import Quote


@pytest.mark.asyncio
async def test_momentum_engine_complete_scan_workflow():
    """
    T066 [RED]: Test complete momentum engine workflow with all 3 detectors.

    Test Scenario:
    - Symbol A (AAPL): Catalyst signal (80) + PreMarket signal (60) + Pattern signal (90)
      - Expected composite: 0.25*80 + 0.35*60 + 0.40*90 = 77.0
    - Symbol B (GOOGL): Catalyst signal (75) + Pattern signal (85)
      - Expected composite: 0.25*75 + 0 + 0.40*85 = 52.75
    - Symbol C (TSLA): PreMarket signal only (70)
      - Expected composite: 0 + 0.35*70 + 0 = 24.5

    GIVEN: MomentumRanker with all 3 detectors initialized
    WHEN: scan(["AAPL", "GOOGL", "TSLA"]) called
    THEN:
      - All 3 detectors execute
      - Signals collected from all detectors
      - Signals ranked by composite score
      - Final list sorted correctly (AAPL > GOOGL > TSLA)
      - All required fields present in output

    Coverage:
    - Full integration of all 3 detectors
    - Signal aggregation and deduplication
    - Composite score calculation
    - Ranking and sorting
    """
    # GIVEN: Mock dependencies
    mock_config = MomentumConfig(
        news_api_key="test-api-key",  # Enable catalyst detector
        min_catalyst_strength=50.0,
        min_premarket_change_pct=5.0,
        min_volume_ratio=200.0,
        pole_min_gain_pct=8.0,
        flag_range_pct_min=3.0,
        flag_range_pct_max=5.0,
    )
    mock_logger = Mock(spec=MomentumLogger)
    mock_market_data_service = Mock()

    # GIVEN: Mock time to be in pre-market window (8:00 AM EST = 13:00 UTC on Thursday)
    premarket_time_utc = datetime(2025, 10, 16, 13, 0, 0, tzinfo=UTC)
    EST_TZ = ZoneInfo("America/New_York")

    # ============================================
    # Mock CatalystDetector responses
    # ============================================
    async def mock_catalyst_scan(symbols):
        """Mock catalyst detector returning signals for AAPL and GOOGL."""
        signals = []
        if "AAPL" in symbols:
            signals.append(MomentumSignal(
                symbol="AAPL",
                signal_type=SignalType.CATALYST,
                strength=80.0,
                detected_at=premarket_time_utc,
                details={
                    "headline": "Apple announces Q4 earnings beat",
                    "catalyst_type": "earnings",
                    "published_at": premarket_time_utc.isoformat(),
                    "source": "Bloomberg",
                },
            ))
        if "GOOGL" in symbols:
            signals.append(MomentumSignal(
                symbol="GOOGL",
                signal_type=SignalType.CATALYST,
                strength=75.0,
                detected_at=premarket_time_utc,
                details={
                    "headline": "Google announces new AI product",
                    "catalyst_type": "product",
                    "published_at": premarket_time_utc.isoformat(),
                    "source": "TechCrunch",
                },
            ))
        return signals

    # ============================================
    # Mock PreMarketScanner responses
    # ============================================
    async def mock_premarket_scan(symbols):
        """Mock pre-market scanner returning signals for AAPL and TSLA."""
        signals = []
        if "AAPL" in symbols:
            signals.append(MomentumSignal(
                symbol="AAPL",
                signal_type=SignalType.PREMARKET,
                strength=60.0,
                detected_at=premarket_time_utc,
                details={
                    "change_pct": 8.5,
                    "volume_ratio": 3.2,
                    "current_price": 175.50,
                    "previous_close": 161.81,
                    "timestamp_utc": premarket_time_utc.isoformat(),
                    "timestamp_est": premarket_time_utc.astimezone(EST_TZ).strftime("%Y-%m-%d %H:%M:%S %Z"),
                },
            ))
        if "TSLA" in symbols:
            signals.append(MomentumSignal(
                symbol="TSLA",
                signal_type=SignalType.PREMARKET,
                strength=70.0,
                detected_at=premarket_time_utc,
                details={
                    "change_pct": 10.2,
                    "volume_ratio": 4.0,
                    "current_price": 265.00,
                    "previous_close": 240.43,
                    "timestamp_utc": premarket_time_utc.isoformat(),
                    "timestamp_est": premarket_time_utc.astimezone(EST_TZ).strftime("%Y-%m-%d %H:%M:%S %Z"),
                },
            ))
        return signals

    # ============================================
    # Mock BullFlagDetector responses
    # ============================================
    async def mock_pattern_scan(symbols):
        """Mock bull flag detector returning signals for AAPL and GOOGL."""
        signals = []
        if "AAPL" in symbols:
            signals.append(MomentumSignal(
                symbol="AAPL",
                signal_type=SignalType.PATTERN,
                strength=90.0,
                detected_at=premarket_time_utc,
                details={
                    "pattern_type": "bull_flag",
                    "pole_gain_pct": 15.0,
                    "flag_range_pct": 3.5,
                    "breakout_price": 173.50,
                    "price_target": 190.00,
                    "pattern_valid": True,
                },
            ))
        if "GOOGL" in symbols:
            signals.append(MomentumSignal(
                symbol="GOOGL",
                signal_type=SignalType.PATTERN,
                strength=85.0,
                detected_at=premarket_time_utc,
                details={
                    "pattern_type": "bull_flag",
                    "pole_gain_pct": 12.0,
                    "flag_range_pct": 4.0,
                    "breakout_price": 145.00,
                    "price_target": 160.00,
                    "pattern_valid": True,
                },
            ))
        return signals

    # GIVEN: Initialize detectors with mocked scan methods
    catalyst_detector = CatalystDetector(config=mock_config, momentum_logger=mock_logger)
    catalyst_detector.scan = mock_catalyst_scan

    premarket_scanner = PreMarketScanner(
        config=mock_config,
        market_data_service=mock_market_data_service,
        momentum_logger=mock_logger,
    )
    premarket_scanner.scan = mock_premarket_scan

    bull_flag_detector = BullFlagDetector(
        config=mock_config,
        market_data_service=mock_market_data_service,
        momentum_logger=mock_logger,
    )
    bull_flag_detector.scan = mock_pattern_scan

    # GIVEN: Initialize MomentumRanker with all detectors
    ranker = MomentumRanker(
        catalyst_detector=catalyst_detector,
        premarket_scanner=premarket_scanner,
        bull_flag_detector=bull_flag_detector,
        momentum_logger=mock_logger,
    )

    # WHEN: Scan symbols with all detectors
    symbols = ["AAPL", "GOOGL", "TSLA"]
    ranked_signals = await ranker.scan_and_rank(symbols)

    # THEN: Verify all signals collected
    assert len(ranked_signals) == 3, f"Expected 3 ranked signals, got {len(ranked_signals)}"

    # THEN: Verify signals are sorted by composite score (descending)
    symbol_order = [signal.symbol for signal in ranked_signals]
    assert symbol_order == ["AAPL", "GOOGL", "TSLA"], f"Expected ['AAPL', 'GOOGL', 'TSLA'], got {symbol_order}"

    # THEN: Verify AAPL composite score (80*0.25 + 60*0.35 + 90*0.40 = 77.0)
    aapl_signal = ranked_signals[0]
    assert aapl_signal.symbol == "AAPL"
    expected_aapl_composite = 0.25 * 80.0 + 0.35 * 60.0 + 0.40 * 90.0  # 77.0
    assert abs(aapl_signal.strength - expected_aapl_composite) < 0.1, (
        f"Expected AAPL composite score ~{expected_aapl_composite}, got {aapl_signal.strength}"
    )
    assert aapl_signal.signal_type == SignalType.COMPOSITE
    assert "catalyst" in aapl_signal.details
    assert "premarket" in aapl_signal.details
    assert "pattern" in aapl_signal.details

    # THEN: Verify GOOGL composite score (75*0.25 + 0 + 85*0.40 = 52.75)
    googl_signal = ranked_signals[1]
    assert googl_signal.symbol == "GOOGL"
    expected_googl_composite = 0.25 * 75.0 + 0.40 * 85.0  # 52.75
    assert abs(googl_signal.strength - expected_googl_composite) < 0.1, (
        f"Expected GOOGL composite score ~{expected_googl_composite}, got {googl_signal.strength}"
    )
    assert googl_signal.signal_type == SignalType.COMPOSITE
    assert "catalyst" in googl_signal.details
    assert "premarket" not in googl_signal.details  # No premarket signal
    assert "pattern" in googl_signal.details

    # THEN: Verify TSLA composite score (0 + 70*0.35 + 0 = 24.5)
    tsla_signal = ranked_signals[2]
    assert tsla_signal.symbol == "TSLA"
    expected_tsla_composite = 0.35 * 70.0  # 24.5
    assert abs(tsla_signal.strength - expected_tsla_composite) < 0.1, (
        f"Expected TSLA composite score ~{expected_tsla_composite}, got {tsla_signal.strength}"
    )
    assert tsla_signal.signal_type == SignalType.COMPOSITE
    assert "catalyst" not in tsla_signal.details  # No catalyst signal
    assert "premarket" in tsla_signal.details
    assert "pattern" not in tsla_signal.details  # No pattern signal

    # THEN: Verify all signals have required fields
    for signal in ranked_signals:
        assert isinstance(signal.symbol, str)
        assert isinstance(signal.signal_type, SignalType)
        assert isinstance(signal.strength, float)
        assert isinstance(signal.detected_at, datetime)
        assert isinstance(signal.details, dict)
        assert signal.detected_at == premarket_time_utc


@pytest.mark.asyncio
async def test_momentum_engine_handles_no_signals():
    """
    T066: Test momentum engine handles case when no detectors find signals.

    GIVEN: All detectors return empty lists
    WHEN: scan_and_rank() called
    THEN: Returns empty list (no errors)
    """
    # GIVEN: Mock config and logger
    mock_config = MomentumConfig(news_api_key="test-key")
    mock_logger = Mock(spec=MomentumLogger)
    mock_market_data = Mock()

    # GIVEN: Mock detectors returning empty results
    async def empty_scan(symbols):
        return []

    catalyst_detector = CatalystDetector(config=mock_config, momentum_logger=mock_logger)
    catalyst_detector.scan = empty_scan

    premarket_scanner = PreMarketScanner(
        config=mock_config,
        market_data_service=mock_market_data,
        momentum_logger=mock_logger,
    )
    premarket_scanner.scan = empty_scan

    bull_flag_detector = BullFlagDetector(
        config=mock_config,
        market_data_service=mock_market_data,
        momentum_logger=mock_logger,
    )
    bull_flag_detector.scan = empty_scan

    # GIVEN: Initialize ranker
    ranker = MomentumRanker(
        catalyst_detector=catalyst_detector,
        premarket_scanner=premarket_scanner,
        bull_flag_detector=bull_flag_detector,
        momentum_logger=mock_logger,
    )

    # WHEN: Scan symbols
    ranked_signals = await ranker.scan_and_rank(["AAPL", "GOOGL"])

    # THEN: Returns empty list
    assert ranked_signals == [], f"Expected empty list, got {ranked_signals}"


@pytest.mark.asyncio
async def test_momentum_engine_single_detector_signals():
    """
    T066: Test momentum engine with signals from only one detector.

    GIVEN: Only CatalystDetector returns signals
    WHEN: scan_and_rank() called
    THEN:
      - Composite signals created with only catalyst component
      - Signals ranked by catalyst strength alone
    """
    # GIVEN: Mock config and logger
    mock_config = MomentumConfig(news_api_key="test-key")
    mock_logger = Mock(spec=MomentumLogger)
    mock_market_data = Mock()
    premarket_time_utc = datetime(2025, 10, 16, 13, 0, 0, tzinfo=UTC)

    # GIVEN: Only catalyst detector returns signals
    async def catalyst_only_scan(symbols):
        return [
            MomentumSignal(
                symbol="AAPL",
                signal_type=SignalType.CATALYST,
                strength=85.0,
                detected_at=premarket_time_utc,
                details={"headline": "Breaking news", "catalyst_type": "earnings"},
            ),
        ]

    async def empty_scan(symbols):
        return []

    catalyst_detector = CatalystDetector(config=mock_config, momentum_logger=mock_logger)
    catalyst_detector.scan = catalyst_only_scan

    premarket_scanner = PreMarketScanner(
        config=mock_config,
        market_data_service=mock_market_data,
        momentum_logger=mock_logger,
    )
    premarket_scanner.scan = empty_scan

    bull_flag_detector = BullFlagDetector(
        config=mock_config,
        market_data_service=mock_market_data,
        momentum_logger=mock_logger,
    )
    bull_flag_detector.scan = empty_scan

    # GIVEN: Initialize ranker
    ranker = MomentumRanker(
        catalyst_detector=catalyst_detector,
        premarket_scanner=premarket_scanner,
        bull_flag_detector=bull_flag_detector,
        momentum_logger=mock_logger,
    )

    # WHEN: Scan symbols
    ranked_signals = await ranker.scan_and_rank(["AAPL"])

    # THEN: Returns 1 signal with composite score = 0.25 * 85.0 = 21.25
    assert len(ranked_signals) == 1
    signal = ranked_signals[0]
    assert signal.symbol == "AAPL"
    expected_composite = 0.25 * 85.0  # Only catalyst weight
    assert abs(signal.strength - expected_composite) < 0.1
    assert signal.signal_type == SignalType.COMPOSITE
    assert "catalyst" in signal.details
    assert "premarket" not in signal.details
    assert "pattern" not in signal.details
