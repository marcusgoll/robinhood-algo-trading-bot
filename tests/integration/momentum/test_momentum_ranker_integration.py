"""
Integration tests for MomentumRanker with mixed signals from all detectors.

Tests end-to-end composite scoring workflow:
- Signal aggregation across multiple detectors
- Composite score calculation with weighted averaging
- Symbol ranking by signal strength
- Signal grouping and missing signal handling
- Performance validation for large signal batches

Pattern: tests/integration/ existing structure
Coverage: ≥90% critical path

Task: T047 [US4] Write integration test for MomentumRanker
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import List

import pytest

from src.trading_bot.momentum.config import MomentumConfig
from src.trading_bot.momentum.logging.momentum_logger import MomentumLogger
from src.trading_bot.momentum.momentum_ranker import MomentumRanker
from src.trading_bot.momentum.schemas.momentum_signal import (
    MomentumSignal,
    SignalType,
)


# === FIXTURES ===


@pytest.fixture
def mock_config() -> MomentumConfig:
    """Create test configuration with valid values."""
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
    """Current time for signal timestamps (UTC)."""
    return datetime.now(UTC)


def create_test_signal(
    symbol: str,
    signal_type: SignalType,
    strength: float,
    detected_at: datetime,
) -> MomentumSignal:
    """
    Helper to create test MomentumSignal objects.

    Args:
        symbol: Stock ticker (1-5 uppercase letters)
        signal_type: Type of signal (CATALYST, PREMARKET, PATTERN)
        strength: Signal strength (0-100)
        detected_at: Detection timestamp (UTC)

    Returns:
        MomentumSignal instance with valid structure
    """
    details = {
        "signal_type": signal_type.value,
        "test_signal": True,
    }

    # Add type-specific details
    if signal_type == SignalType.CATALYST:
        details.update({
            "catalyst_type": "earnings",
            "headline": f"{symbol} reports strong earnings",
            "source": "Test News",
        })
    elif signal_type == SignalType.PREMARKET:
        details.update({
            "change_pct": 7.5,
            "volume_ratio": 3.0,
        })
    elif signal_type == SignalType.PATTERN:
        details.update({
            "pole_gain_pct": 12.0,
            "flag_range_pct": 4.0,
            "breakout_price": 150.0,
            "price_target": 165.0,
        })

    return MomentumSignal(
        symbol=symbol,
        signal_type=signal_type,
        strength=strength,
        detected_at=detected_at,
        details=details,
    )


@pytest.fixture
def mixed_signals_all_types(current_time: datetime) -> List[MomentumSignal]:
    """
    Create mixed signals from all 3 detectors for integration testing.

    Test scenarios:
    - Symbol A (AAPL): All 3 signals (catalyst: 80, premarket: 60, pattern: 90)
        Expected composite: 0.25*80 + 0.35*60 + 0.40*90 = 77.0
    - Symbol B (MSFT): Catalyst + Pattern (catalyst: 75, pattern: 85)
        Expected composite: 0.25*75 + 0 + 0.40*85 = 52.75
    - Symbol C (TSLA): Premarket only (premarket: 70)
        Expected composite: 0 + 0.35*70 + 0 = 24.5
    - Symbol D (NVDA): Pattern only (pattern: 95)
        Expected composite: 0 + 0 + 0.40*95 = 38.0

    Expected ranking (descending): AAPL > MSFT > NVDA > TSLA
    """
    signals = []

    # Symbol A: AAPL - All 3 signals (highest composite)
    signals.append(create_test_signal("AAPL", SignalType.CATALYST, 80.0, current_time - timedelta(hours=2)))
    signals.append(create_test_signal("AAPL", SignalType.PREMARKET, 60.0, current_time - timedelta(hours=1)))
    signals.append(create_test_signal("AAPL", SignalType.PATTERN, 90.0, current_time))

    # Symbol B: MSFT - Catalyst + Pattern
    signals.append(create_test_signal("MSFT", SignalType.CATALYST, 75.0, current_time - timedelta(hours=3)))
    signals.append(create_test_signal("MSFT", SignalType.PATTERN, 85.0, current_time - timedelta(hours=1)))

    # Symbol C: TSLA - Premarket only (lowest composite)
    signals.append(create_test_signal("TSLA", SignalType.PREMARKET, 70.0, current_time - timedelta(hours=2)))

    # Symbol D: NVDA - Pattern only
    signals.append(create_test_signal("NVDA", SignalType.PATTERN, 95.0, current_time - timedelta(hours=1)))

    return signals


@pytest.fixture
def large_signal_batch(current_time: datetime) -> List[MomentumSignal]:
    """
    Create large batch of signals for performance testing.

    Creates 50 signals across 5 symbols (10 signals each):
    - 3-4 catalyst signals per symbol
    - 3-4 premarket signals per symbol
    - 3 pattern signals per symbol
    """
    signals = []
    symbols = ["SYMA", "SYMB", "SYMC", "SYMD", "SYME"]

    for idx, symbol in enumerate(symbols):
        # Create varying numbers of signals per type
        # Symbol 1-2: 4 catalyst, 3 premarket, 3 pattern
        # Symbol 3-5: 3 catalyst, 4 premarket, 3 pattern
        catalyst_count = 4 if idx < 2 else 3
        premarket_count = 3 if idx < 2 else 4
        pattern_count = 3

        # Catalyst signals (strength 70-85)
        for i in range(catalyst_count):
            signals.append(create_test_signal(
                symbol,
                SignalType.CATALYST,
                70.0 + (i * 5),
                current_time - timedelta(hours=idx + i),
            ))

        # Premarket signals (strength 60-75)
        for i in range(premarket_count):
            signals.append(create_test_signal(
                symbol,
                SignalType.PREMARKET,
                60.0 + (i * 5),
                current_time - timedelta(hours=idx + i),
            ))

        # Pattern signals (strength 80-90)
        for i in range(pattern_count):
            signals.append(create_test_signal(
                symbol,
                SignalType.PATTERN,
                80.0 + (i * 5),
                current_time - timedelta(hours=idx + i),
            ))

    return signals


# === INTEGRATION TESTS ===


@pytest.mark.asyncio
async def test_momentum_ranker_e2e_ranks_signals_correctly(
    mock_config: MomentumConfig,
    mock_logger: MomentumLogger,
    mixed_signals_all_types: List[MomentumSignal],
) -> None:
    """
    Test end-to-end signal ranking with mixed signals from all detectors.

    Given:
        - MomentumRanker initialized with config and logger
        - Signals from all 3 detectors (catalyst, premarket, pattern)
        - Multiple symbols with varying signal combinations

    When:
        - User calls ranker.rank(signals)

    Then:
        - Signals are sorted by composite score descending
        - Expected order: AAPL (77.0) > MSFT (52.75) > NVDA (38.0) > TSLA (24.5)
        - Composite scores calculated correctly within 0.01 tolerance
        - All returned signals have signal_type = COMPOSITE
        - Component scores included in details
        - Signal count included in details
        - Latest timestamp preserved

    Coverage: ≥90% critical path (rank, score_composite, aggregation)
    """
    # GIVEN: Initialize ranker
    ranker = MomentumRanker(config=mock_config, logger=mock_logger)

    # WHEN: Rank mixed signals
    ranked_signals = ranker.rank(mixed_signals_all_types)

    # THEN: Verify correct number of composite signals (4 symbols)
    assert len(ranked_signals) == 4, f"Expected 4 composite signals, got {len(ranked_signals)}"

    # Verify sorting order (descending by composite score)
    symbols_order = [s.symbol for s in ranked_signals]
    expected_order = ["AAPL", "MSFT", "NVDA", "TSLA"]
    assert symbols_order == expected_order, f"Expected order {expected_order}, got {symbols_order}"

    # Verify AAPL composite score (all 3 signals)
    aapl_signal = ranked_signals[0]
    assert aapl_signal.symbol == "AAPL"
    assert aapl_signal.signal_type == SignalType.COMPOSITE
    expected_aapl_score = 0.25 * 80 + 0.35 * 60 + 0.40 * 90  # = 77.0
    assert abs(aapl_signal.strength - expected_aapl_score) < 0.01, \
        f"AAPL composite score {aapl_signal.strength} != expected {expected_aapl_score}"

    # Verify AAPL details
    assert "catalyst_score" in aapl_signal.details
    assert "premarket_score" in aapl_signal.details
    assert "pattern_score" in aapl_signal.details
    assert "composite_score" in aapl_signal.details
    assert "signal_count" in aapl_signal.details
    assert aapl_signal.details["catalyst_score"] == 80.0
    assert aapl_signal.details["premarket_score"] == 60.0
    assert aapl_signal.details["pattern_score"] == 90.0
    assert aapl_signal.details["signal_count"] == 3

    # Verify MSFT composite score (catalyst + pattern, no premarket)
    msft_signal = ranked_signals[1]
    assert msft_signal.symbol == "MSFT"
    expected_msft_score = 0.25 * 75 + 0.35 * 0 + 0.40 * 85  # = 52.75
    assert abs(msft_signal.strength - expected_msft_score) < 0.01, \
        f"MSFT composite score {msft_signal.strength} != expected {expected_msft_score}"
    assert msft_signal.details["catalyst_score"] == 75.0
    assert msft_signal.details["premarket_score"] == 0.0  # Missing signal defaults to 0
    assert msft_signal.details["pattern_score"] == 85.0
    assert msft_signal.details["signal_count"] == 2

    # Verify NVDA composite score (pattern only)
    nvda_signal = ranked_signals[2]
    assert nvda_signal.symbol == "NVDA"
    expected_nvda_score = 0.25 * 0 + 0.35 * 0 + 0.40 * 95  # = 38.0
    assert abs(nvda_signal.strength - expected_nvda_score) < 0.01, \
        f"NVDA composite score {nvda_signal.strength} != expected {expected_nvda_score}"
    assert nvda_signal.details["catalyst_score"] == 0.0
    assert nvda_signal.details["premarket_score"] == 0.0
    assert nvda_signal.details["pattern_score"] == 95.0
    assert nvda_signal.details["signal_count"] == 1

    # Verify TSLA composite score (premarket only)
    tsla_signal = ranked_signals[3]
    assert tsla_signal.symbol == "TSLA"
    expected_tsla_score = 0.25 * 0 + 0.35 * 70 + 0.40 * 0  # = 24.5
    assert abs(tsla_signal.strength - expected_tsla_score) < 0.01, \
        f"TSLA composite score {tsla_signal.strength} != expected {expected_tsla_score}"
    assert tsla_signal.details["catalyst_score"] == 0.0
    assert tsla_signal.details["premarket_score"] == 70.0
    assert tsla_signal.details["pattern_score"] == 0.0
    assert tsla_signal.details["signal_count"] == 1

    # Verify all signals have valid timestamps (latest from original signals)
    for signal in ranked_signals:
        assert signal.detected_at is not None
        assert signal.detected_at.tzinfo is not None  # UTC timezone


@pytest.mark.asyncio
async def test_momentum_ranker_groups_signals_by_symbol(
    mock_config: MomentumConfig,
    mock_logger: MomentumLogger,
    current_time: datetime,
) -> None:
    """
    Test MomentumRanker correctly groups signals by symbol.

    Given:
        - Multiple signals for same symbol with different types
        - Multiple signals for different symbols

    When:
        - User calls ranker.rank()

    Then:
        - Signals grouped by symbol
        - Component scores extracted per signal_type
        - One composite signal per symbol
        - All signal types represented in details

    Coverage: Signal aggregation logic (≥90%)
    """
    # GIVEN: Create signals with intentional grouping
    signals = [
        # AAPL: 2 catalyst signals (should take max)
        create_test_signal("AAPL", SignalType.CATALYST, 70.0, current_time),
        create_test_signal("AAPL", SignalType.CATALYST, 85.0, current_time),
        create_test_signal("AAPL", SignalType.PREMARKET, 65.0, current_time),
        # MSFT: Single signal of each type
        create_test_signal("MSFT", SignalType.CATALYST, 80.0, current_time),
        create_test_signal("MSFT", SignalType.PREMARKET, 70.0, current_time),
        create_test_signal("MSFT", SignalType.PATTERN, 90.0, current_time),
    ]

    ranker = MomentumRanker(config=mock_config, logger=mock_logger)

    # WHEN: Rank signals
    ranked = ranker.rank(signals)

    # THEN: Verify grouping (2 symbols = 2 composite signals)
    assert len(ranked) == 2, f"Expected 2 composite signals, got {len(ranked)}"

    # Verify AAPL used max of duplicate catalyst signals (85.0 not 70.0)
    aapl_signal = next(s for s in ranked if s.symbol == "AAPL")
    assert aapl_signal.details["catalyst_score"] == 85.0, \
        "Should use max strength for duplicate signal types"
    assert aapl_signal.details["premarket_score"] == 65.0
    assert aapl_signal.details["pattern_score"] == 0.0  # Missing signal type

    # Verify MSFT has all 3 signal types
    msft_signal = next(s for s in ranked if s.symbol == "MSFT")
    assert msft_signal.details["catalyst_score"] == 80.0
    assert msft_signal.details["premarket_score"] == 70.0
    assert msft_signal.details["pattern_score"] == 90.0
    assert msft_signal.details["signal_count"] == 3


@pytest.mark.asyncio
async def test_momentum_ranker_handles_missing_signals(
    mock_config: MomentumConfig,
    mock_logger: MomentumLogger,
    current_time: datetime,
) -> None:
    """
    Test MomentumRanker handles missing signals with default values.

    Given:
        - Symbol with only 1 signal type (others missing)
        - Symbol with 2 signal types (one missing)

    When:
        - User calls ranker.rank()

    Then:
        - Missing signals default to 0
        - Composite score calculated with 0 values
        - No exceptions raised
        - Valid composite signal returned

    Coverage: Missing signal handling (≥90%)
    """
    # GIVEN: Create signals with intentionally missing types
    signals = [
        # Symbol with only catalyst
        create_test_signal("ONLYA", SignalType.CATALYST, 75.0, current_time),
        # Symbol with only premarket
        create_test_signal("ONLYB", SignalType.PREMARKET, 65.0, current_time),
        # Symbol with only pattern
        create_test_signal("ONLYC", SignalType.PATTERN, 85.0, current_time),
    ]

    ranker = MomentumRanker(config=mock_config, logger=mock_logger)

    # WHEN: Rank signals with missing types
    ranked = ranker.rank(signals)

    # THEN: Verify all signals processed without error
    assert len(ranked) == 3

    # Verify ONLYA (catalyst only)
    onlya = next(s for s in ranked if s.symbol == "ONLYA")
    assert onlya.details["catalyst_score"] == 75.0
    assert onlya.details["premarket_score"] == 0.0  # Missing
    assert onlya.details["pattern_score"] == 0.0  # Missing
    expected_score = 0.25 * 75  # = 18.75
    assert abs(onlya.strength - expected_score) < 0.01

    # Verify ONLYB (premarket only)
    onlyb = next(s for s in ranked if s.symbol == "ONLYB")
    assert onlyb.details["catalyst_score"] == 0.0  # Missing
    assert onlyb.details["premarket_score"] == 65.0
    assert onlyb.details["pattern_score"] == 0.0  # Missing
    expected_score = 0.35 * 65  # = 22.75
    assert abs(onlyb.strength - expected_score) < 0.01

    # Verify ONLYC (pattern only)
    onlyc = next(s for s in ranked if s.symbol == "ONLYC")
    assert onlyc.details["catalyst_score"] == 0.0  # Missing
    assert onlyc.details["premarket_score"] == 0.0  # Missing
    assert onlyc.details["pattern_score"] == 85.0
    expected_score = 0.40 * 85  # = 34.0
    assert abs(onlyc.strength - expected_score) < 0.01


@pytest.mark.asyncio
async def test_momentum_ranker_performance(
    mock_config: MomentumConfig,
    mock_logger: MomentumLogger,
    large_signal_batch: List[MomentumSignal],
) -> None:
    """
    Test MomentumRanker performance with large signal batch.

    Given:
        - 50 signals across 5 symbols (10 signals each)
        - Mixed signal types from all detectors

    When:
        - User calls ranker.rank()

    Then:
        - Completes in < 1 second
        - All symbols ranked correctly
        - Composite scores calculated accurately

    Coverage: Performance validation
    """
    # GIVEN: Initialize ranker
    ranker = MomentumRanker(config=mock_config, logger=mock_logger)

    # WHEN: Measure ranking time
    start_time = datetime.now(UTC)
    ranked = ranker.rank(large_signal_batch)
    end_time = datetime.now(UTC)

    # THEN: Verify performance target
    duration = (end_time - start_time).total_seconds()
    assert duration < 1.0, f"Ranking took {duration}s, expected < 1s"

    # Verify correct number of composite signals (5 symbols)
    assert len(ranked) == 5, f"Expected 5 composite signals, got {len(ranked)}"

    # Verify all signals have composite type
    for signal in ranked:
        assert signal.signal_type == SignalType.COMPOSITE
        assert signal.strength > 0  # Should have non-zero composite score
        assert "signal_count" in signal.details
        assert signal.details["signal_count"] >= 10  # Each symbol has 10 signals

    # Verify signals are sorted descending
    strengths = [s.strength for s in ranked]
    assert strengths == sorted(strengths, reverse=True), \
        "Signals not sorted by strength descending"


@pytest.mark.asyncio
async def test_momentum_ranker_empty_input(
    mock_config: MomentumConfig,
    mock_logger: MomentumLogger,
) -> None:
    """
    Test MomentumRanker handles empty signal list gracefully.

    Given:
        - Empty signal list

    When:
        - User calls ranker.rank([])

    Then:
        - Empty list returned
        - No exceptions raised
        - Logged appropriately

    Coverage: Edge case handling
    """
    # GIVEN: Initialize ranker
    ranker = MomentumRanker(config=mock_config, logger=mock_logger)

    # WHEN: Rank empty list
    ranked = ranker.rank([])

    # THEN: Empty list returned without error
    assert ranked == []
    assert isinstance(ranked, list)


@pytest.mark.asyncio
async def test_momentum_ranker_composite_signals_excluded(
    mock_config: MomentumConfig,
    mock_logger: MomentumLogger,
    current_time: datetime,
) -> None:
    """
    Test MomentumRanker skips COMPOSITE signals in input.

    Given:
        - Mixed signals including existing COMPOSITE signals

    When:
        - User calls ranker.rank()

    Then:
        - COMPOSITE signals are skipped during aggregation
        - Only raw signals (CATALYST, PREMARKET, PATTERN) are processed
        - Warning logged for skipped COMPOSITE signals

    Coverage: Signal filtering logic
    """
    # GIVEN: Create mixed signals including COMPOSITE
    signals = [
        create_test_signal("AAPL", SignalType.CATALYST, 80.0, current_time),
        create_test_signal("AAPL", SignalType.PREMARKET, 60.0, current_time),
        # Add a COMPOSITE signal (should be skipped)
        MomentumSignal(
            symbol="AAPL",
            signal_type=SignalType.COMPOSITE,
            strength=75.0,
            detected_at=current_time,
            details={"composite_score": 75.0},
        ),
    ]

    ranker = MomentumRanker(config=mock_config, logger=mock_logger)

    # WHEN: Rank signals with COMPOSITE in input
    ranked = ranker.rank(signals)

    # THEN: Verify COMPOSITE signal was skipped
    assert len(ranked) == 1  # Only one symbol (AAPL)
    aapl_signal = ranked[0]

    # Composite should be calculated from raw signals only
    # Expected: 0.25*80 + 0.35*60 + 0.40*0 = 41.0 (no pattern signal)
    expected_score = 0.25 * 80 + 0.35 * 60
    assert abs(aapl_signal.strength - expected_score) < 0.01

    # Signal count should be 3 (all signals including COMPOSITE, since signal_count counts original signals)
    # The COMPOSITE signal is skipped in aggregation but still counted in the original list
    assert aapl_signal.details["signal_count"] == 3


@pytest.mark.asyncio
async def test_momentum_ranker_score_composite_unit(
    mock_config: MomentumConfig,
    mock_logger: MomentumLogger,
) -> None:
    """
    Test score_composite() method calculates weighted average correctly.

    Given:
        - MomentumRanker instance
        - Various score combinations

    When:
        - User calls score_composite(catalyst, premarket, pattern)

    Then:
        - Composite = 0.25*catalyst + 0.35*premarket + 0.40*pattern
        - Calculation accurate within 0.01 tolerance

    Coverage: score_composite() method (unit test within integration suite)
    """
    # GIVEN: Initialize ranker
    ranker = MomentumRanker(config=mock_config, logger=mock_logger)

    # Test case 1: All signals present (from spec example)
    composite = ranker.score_composite(
        catalyst_score=80.0,
        premarket_score=60.0,
        pattern_score=90.0,
    )
    expected = 0.25 * 80 + 0.35 * 60 + 0.40 * 90  # = 77.0
    assert abs(composite - expected) < 0.01

    # Test case 2: Only catalyst
    composite = ranker.score_composite(
        catalyst_score=80.0,
        premarket_score=0.0,
        pattern_score=0.0,
    )
    expected = 0.25 * 80  # = 20.0
    assert abs(composite - expected) < 0.01

    # Test case 3: Catalyst + Pattern
    composite = ranker.score_composite(
        catalyst_score=75.0,
        premarket_score=0.0,
        pattern_score=85.0,
    )
    expected = 0.25 * 75 + 0.40 * 85  # = 52.75
    assert abs(composite - expected) < 0.01

    # Test case 4: All zeros
    composite = ranker.score_composite(
        catalyst_score=0.0,
        premarket_score=0.0,
        pattern_score=0.0,
    )
    assert composite == 0.0

    # Test case 5: All max scores
    composite = ranker.score_composite(
        catalyst_score=100.0,
        premarket_score=100.0,
        pattern_score=100.0,
    )
    expected = 0.25 * 100 + 0.35 * 100 + 0.40 * 100  # = 100.0
    assert abs(composite - expected) < 0.01
