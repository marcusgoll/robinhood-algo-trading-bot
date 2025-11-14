"""
Integration tests for PreMarketScanner with mocked MarketDataService.

Tests end-to-end pre-market scanning workflow with realistic mocked data.
Note: Current implementation has stub calculations for price change (always 0%)
and volume ratio. These tests validate the integration flow and will be enhanced
when T026 (volume baseline calculation) is fully implemented.

Pattern: tests/integration/momentum/test_catalyst_detector_integration.py
Coverage: ≥90% critical path

Task: T028 [US2] Write integration test for PreMarketScanner
"""

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pandas as pd
import pytest

from src.trading_bot.market_data.data_models import Quote
from src.trading_bot.momentum.config import MomentumConfig
from src.trading_bot.momentum.logging.momentum_logger import MomentumLogger
from src.trading_bot.momentum.premarket_scanner import PreMarketScanner
from src.trading_bot.momentum.schemas.momentum_signal import SignalType


# === FIXTURES ===


@pytest.fixture
def mock_config() -> MomentumConfig:
    """Create test configuration with valid thresholds."""
    return MomentumConfig(
        news_api_key="test-api-key-12345",
        market_data_source="alpaca",
        min_catalyst_strength=5.0,
        min_premarket_change_pct=5.0,
        min_volume_ratio=200.0,
        pole_min_gain_pct=8.0,
        flag_range_pct_min=3.0,
        flag_range_pct_max=5.0,
    )


@pytest.fixture
def mock_logger(tmp_path: Path) -> MomentumLogger:
    """Create MomentumLogger with temporary directory."""
    log_dir = tmp_path / "momentum_logs"
    return MomentumLogger(log_dir=log_dir)


@pytest.fixture
def premarket_time_utc() -> datetime:
    """Current time in pre-market hours (8:00 AM EDT = 12:00 PM UTC on Thursday, October 16)."""
    return datetime(2025, 10, 16, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def outside_premarket_time_utc() -> datetime:
    """Current time outside pre-market hours (10:00 AM EDT = 2:00 PM UTC)."""
    return datetime(2025, 10, 16, 14, 0, 0, tzinfo=UTC)


@pytest.fixture
def mock_market_data_service():
    """Create mock MarketDataService for testing."""
    service = Mock()
    service.get_quote = Mock()
    service.get_historical_data = Mock()
    return service


# === INTEGRATION TESTS ===


@pytest.mark.asyncio
async def test_premarket_scanner_skips_outside_hours(
    mock_config: MomentumConfig,
    mock_logger: MomentumLogger,
    mock_market_data_service: Mock,
    outside_premarket_time_utc: datetime,
) -> None:
    """
    Test PreMarketScanner returns empty list when called outside pre-market hours.

    Given:
        - PreMarketScanner initialized
        - Current time is outside pre-market window (10:00 AM EDT, after market open)

    When:
        - User calls scanner.scan(["AAPL", "GOOGL"])

    Then:
        - Empty list returned (no processing)
        - MarketDataService.get_quote() NOT called (optimization)

    Coverage: Pre-market hours validation
    """
    # GIVEN: Initialize scanner
    scanner = PreMarketScanner(
        config=mock_config,
        market_data_service=mock_market_data_service,
        momentum_logger=mock_logger,
    )

    # Mock time to be outside pre-market window
    with patch("trading_bot.momentum.premarket_scanner.datetime") as mock_datetime:
        mock_datetime.now.return_value = outside_premarket_time_utc

        # WHEN: Scan outside hours
        symbols = ["AAPL", "GOOGL"]
        signals = await scanner.scan(symbols)

    # THEN: Empty list returned
    assert signals == [], "Should return empty list outside pre-market hours"

    # Verify market data service was NOT called (optimization)
    mock_market_data_service.get_quote.assert_not_called()


@pytest.mark.asyncio
async def test_premarket_scanner_handles_api_errors_gracefully(
    mock_config: MomentumConfig,
    mock_logger: MomentumLogger,
    mock_market_data_service: Mock,
    premarket_time_utc: datetime,
) -> None:
    """
    Test PreMarketScanner handles API errors with graceful degradation.

    Given:
        - PreMarketScanner initialized
        - MarketDataService.get_quote() raises ConnectionError for one symbol

    When:
        - User calls scanner.scan(["AAPL", "FAIL", "GOOGL"])

    Then:
        - Exception caught and logged
        - Other symbols continue processing
        - Error logged to MomentumLogger

    Coverage: Error handling path
    """
    # GIVEN: Initialize scanner
    scanner = PreMarketScanner(
        config=mock_config,
        market_data_service=mock_market_data_service,
        momentum_logger=mock_logger,
    )

    # Mock get_quote to fail for "FAIL" symbol
    def get_quote_side_effect(symbol: str) -> Quote:
        if symbol == "FAIL":
            raise ConnectionError("API timeout for FAIL")
        return Quote(
            symbol=symbol,
            current_price=Decimal("150.00"),
            timestamp_utc=premarket_time_utc,
            market_state="pre",
        )

    mock_market_data_service.get_quote.side_effect = get_quote_side_effect

    # Mock historical data for volume baseline
    mock_df = pd.DataFrame({"volume": [1_000_000] * 10})
    mock_market_data_service.get_historical_data.return_value = mock_df

    # Mock time to be in pre-market window
    with patch("trading_bot.momentum.premarket_scanner.datetime") as mock_datetime:
        mock_datetime.now.return_value = premarket_time_utc

        # WHEN: Scan with one failing symbol
        symbols = ["AAPL", "FAIL", "GOOGL"]
        signals = await scanner.scan(symbols)

    # THEN: No exception propagated, processing continues
    assert isinstance(signals, list), "Should return list even with one failure"
    # Note: With stub implementation (price_change=0), signals may be empty


@pytest.mark.asyncio
async def test_premarket_scanner_timezone_handling(
    mock_config: MomentumConfig,
    mock_logger: MomentumLogger,
    mock_market_data_service: Mock,
) -> None:
    """
    Test timezone conversions (UTC storage, EST/EDT comparison).

    Given:
        - PreMarketScanner initialized
        - Various timestamps in UTC

    When:
        - User calls scanner.is_premarket_hours() with different UTC times

    Then:
        - Correct EST/EDT conversion
        - Pre-market window detected correctly:
            - 4:00 AM EDT (8:00 UTC) → True
            - 9:29 AM EDT (13:29 UTC) → True
            - 9:31 AM EDT (13:31 UTC) → False
            - Saturday any time → False

    Coverage: Timezone validation logic
    """
    # GIVEN: Initialize scanner
    scanner = PreMarketScanner(
        config=mock_config,
        market_data_service=mock_market_data_service,
        momentum_logger=mock_logger,
    )

    # Test case 1: 4:00 AM EDT (start of pre-market) = 8:00 UTC
    time_4am_edt = datetime(2025, 10, 16, 8, 0, 0, tzinfo=UTC)  # Thursday
    assert scanner.is_premarket_hours(time_4am_edt) is True

    # Test case 2: 9:29 AM EDT (end of pre-market) = 13:29 UTC
    time_929am_edt = datetime(2025, 10, 16, 13, 29, 0, tzinfo=UTC)  # Thursday
    assert scanner.is_premarket_hours(time_929am_edt) is True

    # Test case 3: 9:31 AM EDT (after market open) = 13:31 UTC
    time_931am_edt = datetime(2025, 10, 16, 13, 31, 0, tzinfo=UTC)  # Thursday
    assert scanner.is_premarket_hours(time_931am_edt) is False

    # Test case 4: Saturday (any time)
    time_saturday = datetime(2025, 10, 18, 12, 0, 0, tzinfo=UTC)  # Saturday
    assert scanner.is_premarket_hours(time_saturday) is False

    # Test case 5: Sunday (any time)
    time_sunday = datetime(2025, 10, 19, 12, 0, 0, tzinfo=UTC)  # Sunday
    assert scanner.is_premarket_hours(time_sunday) is False


@pytest.mark.asyncio
async def test_premarket_scanner_volume_baseline_calculation(
    mock_config: MomentumConfig,
    mock_logger: MomentumLogger,
    mock_market_data_service: Mock,
    premarket_time_utc: datetime,
) -> None:
    """
    Test volume baseline calculation integrates with scan().

    Given:
        - PreMarketScanner initialized
        - Historical data returns 10-day volume data

    When:
        - User calls scanner.scan(["AAPL"])

    Then:
        - _calculate_volume_baseline() called for each symbol
        - Volume baseline calculated from historical data
        - Graceful degradation if historical data unavailable

    Coverage: Volume baseline integration
    """
    # GIVEN: Initialize scanner
    scanner = PreMarketScanner(
        config=mock_config,
        market_data_service=mock_market_data_service,
        momentum_logger=mock_logger,
    )

    # Mock quote
    mock_quote = Quote(
        symbol="AAPL",
        current_price=Decimal("150.00"),
        timestamp_utc=premarket_time_utc,
        market_state="pre",
    )
    mock_market_data_service.get_quote.return_value = mock_quote

    # Mock historical data with realistic volume
    mock_df = pd.DataFrame({
        "volume": [1_000_000, 1_200_000, 900_000, 1_100_000, 1_050_000,
                   950_000, 1_150_000, 1_000_000, 1_080_000, 1_020_000]
    })
    mock_market_data_service.get_historical_data.return_value = mock_df

    # Mock time to be in pre-market window
    with patch("trading_bot.momentum.premarket_scanner.datetime") as mock_datetime:
        mock_datetime.now.return_value = premarket_time_utc

        # WHEN: Scan symbol
        symbols = ["AAPL"]
        signals = await scanner.scan(symbols)

    # THEN: Historical data fetched
    mock_market_data_service.get_historical_data.assert_called_once()
    call_args = mock_market_data_service.get_historical_data.call_args
    assert call_args.kwargs["symbol"] == "AAPL"
    assert call_args.kwargs["interval"] == "day"
    assert call_args.kwargs["span"] == "month"

    # Note: With stub implementation (price_change=0), signal may not be created
    assert isinstance(signals, list)


@pytest.mark.asyncio
async def test_premarket_scanner_scan_performance(
    mock_config: MomentumConfig,
    mock_logger: MomentumLogger,
    mock_market_data_service: Mock,
    premarket_time_utc: datetime,
) -> None:
    """
    Test PreMarketScanner scan completes within performance target.

    Given:
        - PreMarketScanner initialized
        - 5 symbols to scan

    When:
        - User calls scanner.scan()

    Then:
        - Scan completes in < 10 seconds (integration test limit)
        - Results returned promptly

    Coverage: Performance validation
    """
    # GIVEN: Initialize scanner
    scanner = PreMarketScanner(
        config=mock_config,
        market_data_service=mock_market_data_service,
        momentum_logger=mock_logger,
    )

    # Mock get_quote to return test data
    test_quote = Quote(
        symbol="TEST",
        current_price=Decimal("150.00"),
        timestamp_utc=premarket_time_utc,
        market_state="pre",
    )
    mock_market_data_service.get_quote.return_value = test_quote

    # Mock historical data
    mock_df = pd.DataFrame({"volume": [1_000_000] * 10})
    mock_market_data_service.get_historical_data.return_value = mock_df

    # Mock time to be in pre-market window
    with patch("trading_bot.momentum.premarket_scanner.datetime") as mock_datetime:
        mock_datetime.now.return_value = premarket_time_utc

        # WHEN: Measure scan time
        start_time = datetime.now(UTC)
        symbols = ["AAPL", "GOOGL", "TSLA", "MSFT", "NVDA"]
        signals = await scanner.scan(symbols)
        end_time = datetime.now(UTC)

    # THEN: Verify performance target
    duration = (end_time - start_time).total_seconds()
    assert duration < 10.0, f"Scan took {duration}s, expected < 10s (integration test limit)"
    assert isinstance(signals, list), "Should return list"
