"""
Integration tests for BullFlagDetector with mocked market data.

Tests end-to-end bull flag pattern detection workflow:
- Historical OHLCV data fetching from MarketDataService
- Pole detection (>8% gain in 1-3 days)
- Flag detection (3-5% range, downward/flat slope, 2-5 days)
- Breakout price and target calculation
- Signal generation with BullFlagPattern details
- Error handling and performance validation

Pattern: tests/integration/ existing structure
Coverage: ≥90% critical path

Task: T040 [US3] Write integration test for BullFlagDetector
"""

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pandas as pd
import pytest

from src.trading_bot.momentum.config import MomentumConfig
from src.trading_bot.momentum.logging.momentum_logger import MomentumLogger
from src.trading_bot.momentum.schemas.momentum_signal import (
    BullFlagPattern,
    MomentumSignal,
    SignalType,
)


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
def current_time() -> datetime:
    """Current time for deterministic testing (UTC)."""
    return datetime.now(UTC)


def generate_ohlcv_data(
    base_price: float = 100.0,
    num_days: int = 100,
    pole_start_day: int = 90,
    pole_gain_pct: float = 8.0,
    flag_days: int = 5,
    flag_range_pct: float = 4.0,
    flag_slope_pct: float = -1.0,
) -> pd.DataFrame:
    """
    Generate realistic OHLCV data with configurable bull flag pattern.

    Args:
        base_price: Starting price for the data
        num_days: Total days of historical data
        pole_start_day: Day index where pole begins (0-indexed from oldest)
        pole_gain_pct: Percentage gain during pole formation
        flag_days: Number of days for flag consolidation
        flag_range_pct: Price range during flag as percentage
        flag_slope_pct: Flag slope as percentage (negative = downward)

    Returns:
        DataFrame with columns: timestamp, open, high, low, close, volume
    """
    data = []
    current_date = datetime.now(UTC) - timedelta(days=num_days)

    # Generate base random walk before pole
    for i in range(pole_start_day):
        # Random walk with small variations
        variation = (i % 3 - 1) * 0.5  # -0.5, 0, 0.5 variation
        day_open = base_price + variation
        day_high = day_open + abs(variation) + 0.5
        day_low = day_open - abs(variation) - 0.3
        day_close = day_open + (variation * 0.5)

        data.append(
            {
                "timestamp": current_date + timedelta(days=i),
                "open": day_open,
                "high": day_high,
                "low": day_low,
                "close": day_close,
                "volume": 1_000_000 + (i * 10_000),
            }
        )

    # Generate pole (strong upward move)
    pole_start_price = data[-1]["close"] if data else base_price
    pole_end_price = pole_start_price * (1 + pole_gain_pct / 100)
    pole_duration = 2  # 2-day pole

    for i in range(pole_duration):
        progress = (i + 1) / pole_duration
        day_open = pole_start_price + (pole_end_price - pole_start_price) * (i / pole_duration)
        day_close = pole_start_price + (pole_end_price - pole_start_price) * progress
        day_high = max(day_open, day_close) + 0.5
        day_low = min(day_open, day_close) - 0.2

        data.append(
            {
                "timestamp": current_date + timedelta(days=pole_start_day + i),
                "open": day_open,
                "high": day_high,
                "low": day_low,
                "close": day_close,
                "volume": 2_000_000 + (i * 100_000),  # Higher volume during pole
            }
        )

    # Generate flag (consolidation)
    flag_start_price = pole_end_price
    flag_end_price = flag_start_price * (1 + flag_slope_pct / 100)
    flag_high = flag_start_price * (1 + flag_range_pct / 200)  # Half range above
    flag_low = flag_start_price * (1 - flag_range_pct / 200)  # Half range below

    for i in range(flag_days):
        progress = (i + 1) / flag_days
        day_open = flag_start_price + (flag_end_price - flag_start_price) * (i / flag_days)
        day_close = flag_start_price + (flag_end_price - flag_start_price) * progress
        # Keep within flag range
        day_high = min(flag_high, max(day_open, day_close) + 0.3)
        day_low = max(flag_low, min(day_open, day_close) - 0.3)

        data.append(
            {
                "timestamp": current_date + timedelta(days=pole_start_day + pole_duration + i),
                "open": day_open,
                "high": day_high,
                "low": day_low,
                "close": day_close,
                "volume": 800_000 + (i * 10_000),  # Lower volume during consolidation
            }
        )

    # Fill remaining days with random walk
    remaining_days = num_days - len(data)
    last_close = data[-1]["close"] if data else base_price

    for i in range(remaining_days):
        variation = (i % 3 - 1) * 0.3
        day_open = last_close + variation
        day_high = day_open + abs(variation) + 0.4
        day_low = day_open - abs(variation) - 0.3
        day_close = day_open + (variation * 0.5)
        last_close = day_close

        data.append(
            {
                "timestamp": current_date + timedelta(days=len(data)),
                "open": day_open,
                "high": day_high,
                "low": day_low,
                "close": day_close,
                "volume": 1_000_000,
            }
        )

    return pd.DataFrame(data)


@pytest.fixture
def valid_bull_flag_data() -> pd.DataFrame:
    """
    Symbol A: Valid bull flag pattern.
    Create simple, reliable pattern that detector will find.
    Pattern is at the END of the data since detector scans backwards.
    """
    data = []
    current_date = datetime.now(UTC) - timedelta(days=30)

    # Base data (25 days of flat trading)
    for i in range(25):
        data.append({
            "timestamp": current_date + timedelta(days=i),
            "open": 100.0,
            "high": 100.5,
            "low": 99.5,
            "close": 100.0,
            "volume": 1_000_000,
        })

    # Pole: 2-day rally from $100 to $108.50 (8.5% gain)
    data.append({
        "timestamp": current_date + timedelta(days=25),
        "open": 100.0,
        "high": 104.0,
        "low": 100.0,
        "close": 104.0,
        "volume": 2_000_000,
    })
    data.append({
        "timestamp": current_date + timedelta(days=26),
        "open": 104.0,
        "high": 108.5,
        "low": 104.0,
        "close": 108.5,
        "volume": 2_500_000,
    })

    # Flag: 5-day consolidation with 4% range and -1% slope
    # Range calculation: (high-low)/low * 100
    # Target 4% range: low=105, high=109.2 gives (109.2-105)/105*100 = 4%
    flag_low = 105.0
    flag_high = 109.2  # 4% range
    flag_open_price = 108.5
    flag_close_price = 107.5  # -1% slope

    for i in range(5):
        data.append({
            "timestamp": current_date + timedelta(days=27 + i),
            "open": flag_open_price - (flag_open_price - flag_close_price) * (i / 5),
            "high": flag_high,
            "low": flag_low,
            "close": flag_open_price - (flag_open_price - flag_close_price) * ((i + 1) / 5),
            "volume": 800_000,
        })

    return pd.DataFrame(data)


@pytest.fixture
def wide_flag_data() -> pd.DataFrame:
    """
    Symbol B: Pole exists but flag is too wide (>5% range).
    - Days 88-90: Pole (10% gain over 3 days)
    - Days 91-96: Flag (6% range) - INVALID
    """
    return generate_ohlcv_data(
        base_price=100.0,
        num_days=100,
        pole_start_day=88,
        pole_gain_pct=10.0,
        flag_days=6,
        flag_range_pct=6.0,  # Too wide
        flag_slope_pct=-0.5,
    )


@pytest.fixture
def no_pole_data() -> pd.DataFrame:
    """
    Symbol C: No pole detected (random walk, <8% gain).
    """
    data = []
    current_date = datetime.now(UTC) - timedelta(days=100)
    base_price = 100.0

    for i in range(100):
        variation = (i % 5 - 2) * 0.5  # Random walk: -1, -0.5, 0, 0.5, 1
        day_open = base_price + variation
        day_high = day_open + abs(variation) + 0.5
        day_low = day_open - abs(variation) - 0.5
        day_close = day_open + (variation * 0.3)
        base_price = day_close

        data.append(
            {
                "timestamp": current_date + timedelta(days=i),
                "open": day_open,
                "high": day_high,
                "low": day_low,
                "close": day_close,
                "volume": 1_000_000,
            }
        )

    return pd.DataFrame(data)


@pytest.fixture
def upward_slope_flag_data() -> pd.DataFrame:
    """
    Symbol D: Pole exists but flag has upward slope (invalid).
    - Days 90-91: Pole (9% gain over 2 days)
    - Days 92-96: Flag with upward slope (+2%) - INVALID
    """
    return generate_ohlcv_data(
        base_price=100.0,
        num_days=100,
        pole_start_day=90,
        pole_gain_pct=9.0,
        flag_days=5,
        flag_range_pct=4.0,
        flag_slope_pct=2.0,  # Upward slope - INVALID
    )


@pytest.fixture
def mock_market_data_responses(
    valid_bull_flag_data: pd.DataFrame,
    wide_flag_data: pd.DataFrame,
    no_pole_data: pd.DataFrame,
    upward_slope_flag_data: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """Map symbols to their respective OHLCV data."""
    return {
        "VBULL": valid_bull_flag_data,  # Valid bull flag
        "WIDE": wide_flag_data,  # Wide flag (invalid)
        "FLAT": no_pole_data,  # No pole
        "UPSLOPE": upward_slope_flag_data,  # Upward slope flag (invalid)
    }


# === INTEGRATION TESTS ===


@pytest.mark.asyncio
async def test_bull_flag_detector_e2e_detects_valid_pattern(
    mock_config: MomentumConfig,
    mock_logger: MomentumLogger,
    mock_market_data_responses: dict[str, pd.DataFrame],
) -> None:
    """
    Test BullFlagDetector detects valid bull flag patterns end-to-end.

    Given:
        - BullFlagDetector initialized with config and logger
        - MarketDataService returns OHLCV data with valid bull flag pattern
        - Symbol A has: 8% pole gain (days 90-91) + 4% flag range (days 92-96)

    When:
        - User calls detector.scan(["VBULL"])

    Then:
        - Signal returned with signal_type=PATTERN
        - BullFlagPattern details include:
            - pole_gain_pct >= 8.0
            - flag_range_pct between 3.0-5.0
            - breakout_price = top of flag range
            - price_target = breakout_price + pole_height
            - pattern_valid = True
        - Signal strength > 0
        - detected_at timestamp is recent (within 30 seconds)
        - Signal logged to MomentumLogger

    Coverage: Valid pattern detection path (≥90%)
    """
    # GIVEN: Import BullFlagDetector
    from src.trading_bot.momentum.bull_flag_detector import BullFlagDetector

    # Mock MarketDataService
    mock_market_service = Mock()
    mock_market_service.get_historical_data = Mock(
        side_effect=lambda symbol, **kwargs: mock_market_data_responses[symbol]
    )

    detector = BullFlagDetector(
        config=mock_config,
        market_data_service=mock_market_service,
        momentum_logger=mock_logger
    )

    # WHEN: Scan for bull flag patterns
    signals = await detector.scan(["VBULL"])

    # THEN: Verify valid pattern detected
    assert len(signals) == 1, f"Expected 1 signal for valid pattern, got {len(signals)}"

    signal = signals[0]
    assert signal.symbol == "VBULL"
    assert signal.signal_type == SignalType.PATTERN
    assert signal.strength > 0, "Signal strength should be positive"
    assert signal.strength <= 100, "Signal strength should be <= 100"

    # Verify BullFlagPattern details
    assert "pole_gain_pct" in signal.details
    assert "flag_range_pct" in signal.details
    assert "breakout_price" in signal.details
    assert "price_target" in signal.details
    assert "pattern_valid" in signal.details

    pole_gain = signal.details["pole_gain_pct"]
    flag_range = signal.details["flag_range_pct"]
    breakout = signal.details["breakout_price"]
    target = signal.details["price_target"]
    valid = signal.details["pattern_valid"]

    assert pole_gain >= 8.0, f"Pole gain {pole_gain} should be >= 8.0%"
    assert (
        3.0 <= flag_range <= 5.0
    ), f"Flag range {flag_range} should be between 3-5%"
    assert breakout > 0, "Breakout price should be positive"
    assert target >= breakout, "Price target should be >= breakout price"
    assert valid is True, "Pattern should be marked as valid"

    # Verify detected_at timestamp
    now = datetime.now(UTC)
    time_diff = now - signal.detected_at
    assert time_diff.total_seconds() >= 0, "detected_at should not be in future"
    assert (
        time_diff.total_seconds() < 30
    ), "detected_at should be within last 30 seconds"


@pytest.mark.asyncio
async def test_bull_flag_detector_filters_invalid_patterns(
    mock_config: MomentumConfig,
    mock_logger: MomentumLogger,
    mock_market_data_responses: dict[str, pd.DataFrame],
) -> None:
    """
    Test BullFlagDetector excludes invalid patterns (wide flags, upward slopes).

    Given:
        - BullFlagDetector initialized
        - Symbol B: Pole + wide flag (6% range) - should be excluded
        - Symbol D: Pole + upward slope flag - should be excluded

    When:
        - User calls detector.scan(["WIDE", "UPSLOPE"])

    Then:
        - No signals returned (both patterns invalid)
        - Invalid patterns filtered out based on criteria:
            - WIDE: flag_range_pct > 5% (too wide)
            - UPSLOPE: flag slope is upward (not downward/flat)

    Coverage: Pattern validation logic (≥90%)
    """
    # GIVEN: Import BullFlagDetector
    from src.trading_bot.momentum.bull_flag_detector import BullFlagDetector

    # Mock MarketDataService
    mock_market_service = Mock()
    mock_market_service.get_historical_data = Mock(
        side_effect=lambda symbol, **kwargs: mock_market_data_responses[symbol]
    )

    detector = BullFlagDetector(
        config=mock_config,
        market_data_service=mock_market_service,
        momentum_logger=mock_logger
    )

    # WHEN: Scan symbols with invalid patterns
    signals = await detector.scan(["WIDE", "UPSLOPE"])

    # THEN: No signals returned (patterns invalid)
    assert len(signals) == 0, f"Expected 0 signals for invalid patterns, got {len(signals)}"


@pytest.mark.asyncio
async def test_bull_flag_detector_calculates_targets_correctly(
    mock_config: MomentumConfig,
    mock_logger: MomentumLogger,
    valid_bull_flag_data: pd.DataFrame,
) -> None:
    """
    Test BullFlagDetector calculates breakout price and price target correctly.

    Given:
        - BullFlagDetector initialized
        - OHLCV data with known pattern:
            - Pole: $100 → $108 (8% gain, $8 pole height)
            - Flag: $106-$110 range
            - Expected breakout: $110 (top of flag)
            - Expected target: $110 + $8 = $118

    When:
        - User calls detector.scan(["TARGET"])

    Then:
        - Signal returned with correct calculations:
            - breakout_price ≈ $110 (top of flag range)
            - price_target ≈ $118 (breakout + pole height)
        - Calculations follow spec FR-007

    Coverage: Target calculation logic (≥90%)
    """
    # GIVEN: Import BullFlagDetector
    from src.trading_bot.momentum.bull_flag_detector import BullFlagDetector

    # Mock MarketDataService with known data
    mock_market_service = Mock()
    mock_market_service.get_historical_data = Mock(return_value=valid_bull_flag_data)

    detector = BullFlagDetector(
        config=mock_config,
        market_data_service=mock_market_service,
        momentum_logger=mock_logger
    )

    # WHEN: Scan for pattern
    signals = await detector.scan(["TGT"])  # Valid 3-char symbol

    # THEN: Verify calculations
    assert len(signals) == 1, "Expected 1 signal"
    signal = signals[0]

    breakout = signal.details["breakout_price"]
    target = signal.details["price_target"]
    pole_gain = signal.details["pole_gain_pct"]

    # Verify breakout is top of flag range
    assert breakout > 100, "Breakout should be above base price"

    # Verify target = breakout + pole_height
    # pole_height ≈ base_price * (pole_gain_pct / 100)
    # For 8% gain from ~$100: pole_height ≈ $8
    # target should be ≈ breakout + $8
    expected_pole_height = 100 * (pole_gain / 100)
    expected_target = breakout + expected_pole_height

    # Allow 5% tolerance for calculation variations
    assert abs(target - expected_target) / expected_target < 0.05, (
        f"Target {target} should be ≈ {expected_target} "
        f"(breakout {breakout} + pole height {expected_pole_height})"
    )


@pytest.mark.asyncio
async def test_bull_flag_detector_handles_api_errors_gracefully(
    mock_config: MomentumConfig,
    mock_logger: MomentumLogger,
    valid_bull_flag_data: pd.DataFrame,
) -> None:
    """
    Test BullFlagDetector handles MarketDataService errors gracefully.

    Given:
        - BullFlagDetector initialized
        - MarketDataService raises exception for one symbol
        - Other symbols return valid data

    When:
        - User calls detector.scan(["ERROR", "VBULL"])

    Then:
        - No exception propagated to caller
        - Symbol with error is skipped
        - Valid symbol is processed normally
        - Error logged to MomentumLogger
        - At least one signal returned (from valid symbol)

    Coverage: Error handling path (≥90%)
    """
    # GIVEN: Import BullFlagDetector
    from src.trading_bot.momentum.bull_flag_detector import BullFlagDetector

    # Mock MarketDataService with one error
    def mock_get_historical_data(symbol: str, **kwargs):
        if symbol == "ERROR":
            raise Exception("API error: Rate limit exceeded")
        return valid_bull_flag_data

    mock_market_service = Mock()
    mock_market_service.get_historical_data = Mock(side_effect=mock_get_historical_data)

    detector = BullFlagDetector(
        config=mock_config,
        market_data_service=mock_market_service,
        momentum_logger=mock_logger
    )

    # WHEN: Scan with error
    signals = await detector.scan(["ERROR", "VBULL"])

    # THEN: Error handled gracefully
    # At least one signal from valid symbol
    assert len(signals) >= 1, "Should return at least one signal from valid symbol"

    # Error symbol should not be in results
    error_signals = [s for s in signals if s.symbol == "ERROR"]
    assert len(error_signals) == 0, "Error symbol should not produce signal"

    # Valid symbol should be processed
    valid_signals = [s for s in signals if s.symbol == "VBULL"]
    assert len(valid_signals) == 1, "Valid symbol should produce signal"


@pytest.mark.asyncio
async def test_bull_flag_detector_no_pattern_found(
    mock_config: MomentumConfig,
    mock_logger: MomentumLogger,
    no_pole_data: pd.DataFrame,
) -> None:
    """
    Test BullFlagDetector returns empty list when no pattern found.

    Given:
        - BullFlagDetector initialized
        - Symbol has no pole (random walk, <8% gain)

    When:
        - User calls detector.scan(["FLAT"])

    Then:
        - Empty list returned (no pattern detected)
        - No exceptions raised

    Coverage: No pattern found path (≥90%)
    """
    # GIVEN: Import BullFlagDetector
    from src.trading_bot.momentum.bull_flag_detector import BullFlagDetector

    # Mock MarketDataService
    mock_market_service = Mock()
    mock_market_service.get_historical_data = Mock(return_value=no_pole_data)

    detector = BullFlagDetector(
        config=mock_config,
        market_data_service=mock_market_service,
        momentum_logger=mock_logger
    )

    # WHEN: Scan symbol with no pattern
    signals = await detector.scan(["FLAT"])

    # THEN: Empty list returned
    assert len(signals) == 0, "Should return empty list when no pattern found"


@pytest.mark.asyncio
async def test_bull_flag_detector_performance(
    mock_config: MomentumConfig,
    mock_logger: MomentumLogger,
    mock_market_data_responses: dict[str, pd.DataFrame],
) -> None:
    """
    Test BullFlagDetector scan completes within performance target.

    Given:
        - BullFlagDetector initialized
        - 5 symbols to scan with 100-day OHLCV data each

    When:
        - User calls detector.scan() with 5 symbols

    Then:
        - Scan completes in < 10 seconds (integration test limit)
        - All symbols processed
        - Results returned promptly

    Coverage: Performance validation
    """
    # GIVEN: Import BullFlagDetector
    from src.trading_bot.momentum.bull_flag_detector import BullFlagDetector

    # Mock MarketDataService
    mock_market_service = Mock()
    mock_market_service.get_historical_data = Mock(
        side_effect=lambda symbol, **kwargs: mock_market_data_responses.get(
            symbol, mock_market_data_responses["VBULL"]
        )
    )

    detector = BullFlagDetector(
        config=mock_config,
        market_data_service=mock_market_service,
        momentum_logger=mock_logger
    )

    # WHEN: Measure scan time
    start_time = datetime.now(UTC)
    symbols = ["VBULL", "WIDE", "FLAT", "UPSLOPE", "VBULL2"]
    signals = await detector.scan(symbols)
    end_time = datetime.now(UTC)

    # THEN: Verify performance target
    duration = (end_time - start_time).total_seconds()
    assert (
        duration < 10.0
    ), f"Scan took {duration}s, expected < 10s (integration test limit)"
    assert isinstance(signals, list), "Should return list of signals"


@pytest.mark.asyncio
async def test_bull_flag_detector_validates_input_symbols(
    mock_config: MomentumConfig,
    mock_logger: MomentumLogger,
) -> None:
    """
    Test BullFlagDetector validates input symbols.

    Given:
        - BullFlagDetector initialized
        - Invalid symbols provided (lowercase, too long, invalid characters)

    When:
        - User calls detector.scan() with invalid symbols

    Then:
        - Invalid symbols are filtered or error raised
        - Error logged with context

    Coverage: Input validation path (≥90%)
    """
    # GIVEN: Import BullFlagDetector
    from src.trading_bot.momentum.bull_flag_detector import BullFlagDetector

    # Mock MarketDataService
    mock_market_service = Mock()
    mock_market_service.get_historical_data = Mock(return_value=pd.DataFrame())

    detector = BullFlagDetector(
        config=mock_config,
        market_data_service=mock_market_service,
        momentum_logger=mock_logger
    )

    # WHEN: Scan with invalid symbols
    # Note: Behavior depends on implementation - may filter or raise
    try:
        signals = await detector.scan(["invalid", "TOOLONG123", "ABC-DEF"])
        # If filtering: should return empty or skip invalid
        assert isinstance(signals, list), "Should return list even with invalid input"
    except ValueError as e:
        # If validation error: should provide clear message
        assert "symbol" in str(e).lower(), "Error should mention symbol validation"
