"""
Unit tests for MomentumEngine composition root.

Tests:
- T050: MomentumEngine initialization
- T050: MomentumEngine.scan() execution with mocked detectors
- T050: Graceful degradation when detectors fail

Constitution v1.0.0:
- §Test_Coverage: 90% target (all public methods tested)
- §Risk_Management: Test error paths and edge cases
"""

import pytest
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from trading_bot.momentum import MomentumEngine, MomentumConfig
from trading_bot.momentum.schemas.momentum_signal import MomentumSignal, SignalType


@pytest.fixture
def mock_market_data_service():
    """Create mock MarketDataService."""
    mock = MagicMock()
    return mock


@pytest.fixture
def momentum_config():
    """Create test MomentumConfig."""
    return MomentumConfig(
        news_api_key="test-key",
        market_data_source="alpaca",
        min_catalyst_strength=5.0,
        min_premarket_change_pct=5.0,
        min_volume_ratio=200.0,
        pole_min_gain_pct=8.0,
        flag_range_pct_min=3.0,
        flag_range_pct_max=5.0
    )


@pytest.fixture
def momentum_engine(momentum_config, mock_market_data_service):
    """Create MomentumEngine instance with mocked dependencies."""
    return MomentumEngine(momentum_config, mock_market_data_service)


class TestMomentumEngineInitialization:
    """Test MomentumEngine initialization (T050)."""

    def test_initialization_creates_all_detectors(self, momentum_engine):
        """Test that MomentumEngine initializes all detector instances."""
        # Assert all detectors are created
        assert momentum_engine.catalyst_detector is not None
        assert momentum_engine.premarket_scanner is not None
        assert momentum_engine.bull_flag_detector is not None
        assert momentum_engine.ranker is not None

        # Assert config and logger are set
        assert momentum_engine.config is not None
        assert momentum_engine.market_data is not None
        assert momentum_engine.logger is not None

    def test_initialization_with_custom_logger(self, momentum_config, mock_market_data_service):
        """Test that MomentumEngine accepts custom logger."""
        from trading_bot.momentum.logging.momentum_logger import MomentumLogger

        custom_logger = MomentumLogger()
        engine = MomentumEngine(momentum_config, mock_market_data_service, custom_logger)

        assert engine.logger is custom_logger


class TestMomentumEngineScan:
    """Test MomentumEngine.scan() method (T050)."""

    @pytest.mark.asyncio
    async def test_scan_executes_all_detectors(self, momentum_engine):
        """Test that scan() executes all detectors in parallel."""
        # Mock detector scan methods
        catalyst_signal = MomentumSignal(
            symbol="AAPL",
            signal_type=SignalType.CATALYST,
            strength=80.0,
            detected_at=datetime.now(UTC),
            details={"catalyst_type": "earnings"}
        )

        premarket_signal = MomentumSignal(
            symbol="AAPL",
            signal_type=SignalType.PREMARKET,
            strength=70.0,
            detected_at=datetime.now(UTC),
            details={"change_pct": 6.5}
        )

        pattern_signal = MomentumSignal(
            symbol="AAPL",
            signal_type=SignalType.PATTERN,
            strength=85.0,
            detected_at=datetime.now(UTC),
            details={"pole_gain_pct": 10.0}
        )

        momentum_engine.catalyst_detector.scan = AsyncMock(return_value=[catalyst_signal])
        momentum_engine.premarket_scanner.scan = AsyncMock(return_value=[premarket_signal])
        momentum_engine.bull_flag_detector.scan = AsyncMock(return_value=[pattern_signal])

        # Mock ranker
        momentum_engine.ranker.rank = MagicMock(return_value=[
            MomentumSignal(
                symbol="AAPL",
                signal_type=SignalType.COMPOSITE,
                strength=78.5,
                detected_at=datetime.now(UTC),
                details={"composite_score": 78.5}
            )
        ])

        # Execute scan
        symbols = ["AAPL"]
        signals = await momentum_engine.scan(symbols)

        # Assert all detectors were called
        momentum_engine.catalyst_detector.scan.assert_called_once_with(symbols)
        momentum_engine.premarket_scanner.scan.assert_called_once_with(symbols)
        momentum_engine.bull_flag_detector.scan.assert_called_once_with(symbols)

        # Assert ranker was called with all signals
        momentum_engine.ranker.rank.assert_called_once()
        call_args = momentum_engine.ranker.rank.call_args[0][0]
        assert len(call_args) == 3  # 3 signals passed to ranker

        # Assert results
        assert len(signals) == 1
        assert signals[0].symbol == "AAPL"
        assert signals[0].signal_type == SignalType.COMPOSITE

    @pytest.mark.asyncio
    async def test_scan_empty_symbols(self, momentum_engine):
        """Test scan() with empty symbols list returns empty."""
        # Mock detectors to return empty lists
        momentum_engine.catalyst_detector.scan = AsyncMock(return_value=[])
        momentum_engine.premarket_scanner.scan = AsyncMock(return_value=[])
        momentum_engine.bull_flag_detector.scan = AsyncMock(return_value=[])
        momentum_engine.ranker.rank = MagicMock(return_value=[])

        signals = await momentum_engine.scan([])

        assert signals == []

    @pytest.mark.asyncio
    async def test_scan_graceful_degradation_on_detector_failure(self, momentum_engine):
        """Test that scan() continues when individual detectors fail (T050 graceful degradation)."""
        # Mock one detector to raise exception
        momentum_engine.catalyst_detector.scan = AsyncMock(
            side_effect=Exception("CatalystDetector API timeout")
        )

        # Other detectors return signals
        premarket_signal = MomentumSignal(
            symbol="AAPL",
            signal_type=SignalType.PREMARKET,
            strength=70.0,
            detected_at=datetime.now(UTC),
            details={"change_pct": 6.5}
        )

        momentum_engine.premarket_scanner.scan = AsyncMock(return_value=[premarket_signal])
        momentum_engine.bull_flag_detector.scan = AsyncMock(return_value=[])

        # Mock ranker
        momentum_engine.ranker.rank = MagicMock(return_value=[premarket_signal])

        # Execute scan (should not raise exception)
        symbols = ["AAPL"]
        signals = await momentum_engine.scan(symbols)

        # Assert premarket scanner was still called
        momentum_engine.premarket_scanner.scan.assert_called_once_with(symbols)

        # Assert results include premarket signal (catalyst failure was handled)
        assert len(signals) == 1
        assert signals[0].signal_type == SignalType.PREMARKET

    @pytest.mark.asyncio
    async def test_scan_handles_all_detectors_failing(self, momentum_engine):
        """Test scan() returns empty list when all detectors fail."""
        # Mock all detectors to raise exceptions
        momentum_engine.catalyst_detector.scan = AsyncMock(
            side_effect=Exception("CatalystDetector failed")
        )
        momentum_engine.premarket_scanner.scan = AsyncMock(
            side_effect=Exception("PreMarketScanner failed")
        )
        momentum_engine.bull_flag_detector.scan = AsyncMock(
            side_effect=Exception("BullFlagDetector failed")
        )

        # Mock ranker to return empty (no signals to rank)
        momentum_engine.ranker.rank = MagicMock(return_value=[])

        # Execute scan (should not raise exception)
        symbols = ["AAPL"]
        signals = await momentum_engine.scan(symbols)

        # Assert empty result (graceful degradation)
        assert signals == []

    @pytest.mark.asyncio
    async def test_scan_logs_scan_events(self, momentum_engine):
        """Test that scan() logs scan_started and scan_completed events."""
        # Mock detectors
        momentum_engine.catalyst_detector.scan = AsyncMock(return_value=[])
        momentum_engine.premarket_scanner.scan = AsyncMock(return_value=[])
        momentum_engine.bull_flag_detector.scan = AsyncMock(return_value=[])
        momentum_engine.ranker.rank = MagicMock(return_value=[])

        # Mock logger
        momentum_engine.logger.log_scan_event = MagicMock()

        # Execute scan
        await momentum_engine.scan(["AAPL"])

        # Assert log_scan_event was called for start and completion
        assert momentum_engine.logger.log_scan_event.call_count == 2

        # Check first call (scan_started)
        first_call = momentum_engine.logger.log_scan_event.call_args_list[0]
        assert first_call[0][0] == "scan_started"

        # Check second call (scan_completed)
        second_call = momentum_engine.logger.log_scan_event.call_args_list[1]
        assert second_call[0][0] == "scan_completed"


class TestMomentumEngineEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_scan_with_no_signals_detected(self, momentum_engine):
        """Test scan() when no signals are detected by any detector."""
        # Mock all detectors to return empty lists
        momentum_engine.catalyst_detector.scan = AsyncMock(return_value=[])
        momentum_engine.premarket_scanner.scan = AsyncMock(return_value=[])
        momentum_engine.bull_flag_detector.scan = AsyncMock(return_value=[])
        momentum_engine.ranker.rank = MagicMock(return_value=[])

        signals = await momentum_engine.scan(["AAPL", "GOOGL", "TSLA"])

        assert signals == []

    @pytest.mark.asyncio
    async def test_scan_handles_ranker_exception(self, momentum_engine):
        """Test that scan() handles ranker exceptions gracefully."""
        # Mock detectors to return signals
        momentum_engine.catalyst_detector.scan = AsyncMock(return_value=[
            MomentumSignal(
                symbol="AAPL",
                signal_type=SignalType.CATALYST,
                strength=80.0,
                detected_at=datetime.now(UTC),
                details={}
            )
        ])
        momentum_engine.premarket_scanner.scan = AsyncMock(return_value=[])
        momentum_engine.bull_flag_detector.scan = AsyncMock(return_value=[])

        # Mock ranker to raise exception
        momentum_engine.ranker.rank = MagicMock(
            side_effect=Exception("Ranker failed")
        )

        # Execute scan (should handle exception gracefully)
        # Note: Current implementation doesn't explicitly catch ranker exceptions,
        # but outer try-except should handle it
        signals = await momentum_engine.scan(["AAPL"])

        # Ranker exception should be caught by outer exception handler
        assert signals == []
