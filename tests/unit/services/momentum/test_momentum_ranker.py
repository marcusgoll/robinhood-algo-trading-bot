"""
Unit Tests for MomentumRanker Service

Tests for signal ranking and composite scoring logic.
Pattern: TDD approach - tests written before implementation.
"""

import pytest
from datetime import datetime, UTC
from src.trading_bot.momentum.schemas.momentum_signal import (
    MomentumSignal,
    SignalType,
)
from src.trading_bot.momentum.momentum_ranker import MomentumRanker
from src.trading_bot.momentum.logging.momentum_logger import MomentumLogger
from pathlib import Path


class TestMomentumRankerScoreComposite:
    """Tests for MomentumRanker.score_composite() method."""

    def test_score_composite_calculates_weighted_average_all_signals(self, momentum_logger):
        """
        Given catalyst=80, premarket=60, pattern=90
        When score_composite is called
        Then returns 0.25*80 + 0.35*60 + 0.40*90 = 77.0
        """
        # Arrange
        ranker = MomentumRanker(momentum_logger=momentum_logger)
        catalyst_score = 80.0
        premarket_score = 60.0
        pattern_score = 90.0

        # Act
        result = ranker.score_composite(catalyst_score, premarket_score, pattern_score)

        # Assert
        expected = 0.25 * 80.0 + 0.35 * 60.0 + 0.40 * 90.0  # = 20 + 21 + 36 = 77.0
        assert result == pytest.approx(expected, rel=1e-9), \
            f"Expected composite score {expected}, got {result}"

    def test_score_composite_handles_only_catalyst_signal(self, momentum_logger):
        """
        Given catalyst=80, premarket=0, pattern=0
        When score_composite is called
        Then returns 0.25*80 = 20.0
        """
        # Arrange
        ranker = MomentumRanker(momentum_logger=momentum_logger)
        catalyst_score = 80.0
        premarket_score = 0.0
        pattern_score = 0.0

        # Act
        result = ranker.score_composite(catalyst_score, premarket_score, pattern_score)

        # Assert
        expected = 0.25 * 80.0  # = 20.0
        assert result == pytest.approx(expected, rel=1e-9), \
            f"Expected composite score {expected}, got {result}"

    def test_score_composite_handles_only_premarket_signal(self, momentum_logger):
        """
        Given catalyst=0, premarket=70, pattern=0
        When score_composite is called
        Then returns 0.35*70 = 24.5
        """
        # Arrange
        ranker = MomentumRanker(momentum_logger=momentum_logger)
        catalyst_score = 0.0
        premarket_score = 70.0
        pattern_score = 0.0

        # Act
        result = ranker.score_composite(catalyst_score, premarket_score, pattern_score)

        # Assert
        expected = 0.35 * 70.0  # = 24.5
        assert result == pytest.approx(expected, rel=1e-9), \
            f"Expected composite score {expected}, got {result}"

    def test_score_composite_handles_only_pattern_signal(self, momentum_logger):
        """
        Given catalyst=0, premarket=0, pattern=85
        When score_composite is called
        Then returns 0.40*85 = 34.0
        """
        # Arrange
        ranker = MomentumRanker(momentum_logger=momentum_logger)
        catalyst_score = 0.0
        premarket_score = 0.0
        pattern_score = 85.0

        # Act
        result = ranker.score_composite(catalyst_score, premarket_score, pattern_score)

        # Assert
        expected = 0.40 * 85.0  # = 34.0
        assert result == pytest.approx(expected, rel=1e-9), \
            f"Expected composite score {expected}, got {result}"

    def test_score_composite_clamps_to_100_when_over_max(self, momentum_logger):
        """
        Given catalyst=100, premarket=100, pattern=100 (sum > 100)
        When score_composite is called
        Then returns 100.0 (clamped to max)
        """
        # Arrange
        ranker = MomentumRanker(momentum_logger=momentum_logger)
        catalyst_score = 100.0
        premarket_score = 100.0
        pattern_score = 100.0

        # Act
        result = ranker.score_composite(catalyst_score, premarket_score, pattern_score)

        # Assert
        expected = 0.25 * 100.0 + 0.35 * 100.0 + 0.40 * 100.0  # = 100.0
        assert result == pytest.approx(expected, rel=1e-9)
        assert result <= 100.0, f"Composite score {result} exceeds max 100.0"

    def test_score_composite_handles_zero_all_signals(self, momentum_logger):
        """
        Given catalyst=0, premarket=0, pattern=0
        When score_composite is called
        Then returns 0.0
        """
        # Arrange
        ranker = MomentumRanker(momentum_logger=momentum_logger)

        # Act
        result = ranker.score_composite(0.0, 0.0, 0.0)

        # Assert
        assert result == 0.0, f"Expected 0.0 for all-zero scores, got {result}"


class TestMomentumRankerRank:
    """Tests for MomentumRanker.rank() method."""

    def test_rank_aggregates_signals_by_symbol_and_sorts_descending(self, momentum_logger):
        """
        Given signals for AAPL (catalyst=80, premarket=60, pattern=90) and GOOGL (catalyst=50)
        When rank is called
        Then returns sorted signals with composite scores (AAPL > GOOGL)
        """
        # Arrange
        ranker = MomentumRanker(momentum_logger=momentum_logger)

        signals = [
            MomentumSignal(
                symbol="AAPL",
                signal_type=SignalType.CATALYST,
                strength=80.0,
                detected_at=datetime.now(UTC),
                details={"catalyst_type": "earnings"}
            ),
            MomentumSignal(
                symbol="AAPL",
                signal_type=SignalType.PREMARKET,
                strength=60.0,
                detected_at=datetime.now(UTC),
                details={"change_pct": 6.0}
            ),
            MomentumSignal(
                symbol="AAPL",
                signal_type=SignalType.PATTERN,
                strength=90.0,
                detected_at=datetime.now(UTC),
                details={"pattern_type": "bull_flag"}
            ),
            MomentumSignal(
                symbol="GOOGL",
                signal_type=SignalType.CATALYST,
                strength=50.0,
                detected_at=datetime.now(UTC),
                details={"catalyst_type": "analyst"}
            ),
        ]

        # Act
        ranked_signals = ranker.rank(signals)

        # Assert
        # AAPL composite: 0.25*80 + 0.35*60 + 0.40*90 = 77.0
        # GOOGL composite: 0.25*50 + 0.35*0 + 0.40*0 = 12.5
        assert len(ranked_signals) == 2, "Should return 2 ranked signals (one per symbol)"

        # First signal should be AAPL (higher composite score)
        assert ranked_signals[0].symbol == "AAPL"
        assert ranked_signals[0].signal_type == SignalType.COMPOSITE
        assert ranked_signals[0].strength == pytest.approx(77.0, rel=1e-9)

        # Second signal should be GOOGL
        assert ranked_signals[1].symbol == "GOOGL"
        assert ranked_signals[1].signal_type == SignalType.COMPOSITE
        assert ranked_signals[1].strength == pytest.approx(12.5, rel=1e-9)

    def test_rank_handles_missing_catalyst_signal_gracefully(self, momentum_logger):
        """
        Given AAPL with premarket=60 and pattern=90 (no catalyst)
        When rank is called
        Then uses 0 for catalyst_score, composite = 0.25*0 + 0.35*60 + 0.40*90 = 57.0
        """
        # Arrange
        ranker = MomentumRanker(momentum_logger=momentum_logger)

        signals = [
            MomentumSignal(
                symbol="AAPL",
                signal_type=SignalType.PREMARKET,
                strength=60.0,
                detected_at=datetime.now(UTC),
                details={"change_pct": 6.0}
            ),
            MomentumSignal(
                symbol="AAPL",
                signal_type=SignalType.PATTERN,
                strength=90.0,
                detected_at=datetime.now(UTC),
                details={"pattern_type": "bull_flag"}
            ),
        ]

        # Act
        ranked_signals = ranker.rank(signals)

        # Assert
        # Composite: 0.25*0 + 0.35*60 + 0.40*90 = 0 + 21 + 36 = 57.0
        assert len(ranked_signals) == 1
        assert ranked_signals[0].symbol == "AAPL"
        assert ranked_signals[0].strength == pytest.approx(57.0, rel=1e-9)

    def test_rank_handles_missing_premarket_signal_gracefully(self, momentum_logger):
        """
        Given AAPL with catalyst=80 and pattern=90 (no premarket)
        When rank is called
        Then uses 0 for premarket_score, composite = 0.25*80 + 0.35*0 + 0.40*90 = 56.0
        """
        # Arrange
        ranker = MomentumRanker(momentum_logger=momentum_logger)

        signals = [
            MomentumSignal(
                symbol="AAPL",
                signal_type=SignalType.CATALYST,
                strength=80.0,
                detected_at=datetime.now(UTC),
                details={"catalyst_type": "earnings"}
            ),
            MomentumSignal(
                symbol="AAPL",
                signal_type=SignalType.PATTERN,
                strength=90.0,
                detected_at=datetime.now(UTC),
                details={"pattern_type": "bull_flag"}
            ),
        ]

        # Act
        ranked_signals = ranker.rank(signals)

        # Assert
        # Composite: 0.25*80 + 0.35*0 + 0.40*90 = 20 + 0 + 36 = 56.0
        assert len(ranked_signals) == 1
        assert ranked_signals[0].symbol == "AAPL"
        assert ranked_signals[0].strength == pytest.approx(56.0, rel=1e-9)

    def test_rank_handles_missing_pattern_signal_gracefully(self, momentum_logger):
        """
        Given AAPL with catalyst=80 and premarket=60 (no pattern)
        When rank is called
        Then uses 0 for pattern_score, composite = 0.25*80 + 0.35*60 + 0.40*0 = 41.0
        """
        # Arrange
        ranker = MomentumRanker(momentum_logger=momentum_logger)

        signals = [
            MomentumSignal(
                symbol="AAPL",
                signal_type=SignalType.CATALYST,
                strength=80.0,
                detected_at=datetime.now(UTC),
                details={"catalyst_type": "earnings"}
            ),
            MomentumSignal(
                symbol="AAPL",
                signal_type=SignalType.PREMARKET,
                strength=60.0,
                detected_at=datetime.now(UTC),
                details={"change_pct": 6.0}
            ),
        ]

        # Act
        ranked_signals = ranker.rank(signals)

        # Assert
        # Composite: 0.25*80 + 0.35*60 + 0.40*0 = 20 + 21 + 0 = 41.0
        assert len(ranked_signals) == 1
        assert ranked_signals[0].symbol == "AAPL"
        assert ranked_signals[0].strength == pytest.approx(41.0, rel=1e-9)

    def test_rank_handles_empty_signals_list(self, momentum_logger):
        """
        Given empty signals list
        When rank is called
        Then returns empty list
        """
        # Arrange
        ranker = MomentumRanker(momentum_logger=momentum_logger)

        # Act
        ranked_signals = ranker.rank([])

        # Assert
        assert ranked_signals == []

    def test_rank_sorts_by_strength_descending(self, momentum_logger):
        """
        Given multiple symbols with different composite scores
        When rank is called
        Then returns signals sorted by strength descending
        """
        # Arrange
        ranker = MomentumRanker(momentum_logger=momentum_logger)

        signals = [
            # TSLA: composite = 0.25*50 + 0.35*50 + 0.40*50 = 50.0
            MomentumSignal(symbol="TSLA", signal_type=SignalType.CATALYST, strength=50.0, detected_at=datetime.now(UTC), details={}),
            MomentumSignal(symbol="TSLA", signal_type=SignalType.PREMARKET, strength=50.0, detected_at=datetime.now(UTC), details={}),
            MomentumSignal(symbol="TSLA", signal_type=SignalType.PATTERN, strength=50.0, detected_at=datetime.now(UTC), details={}),

            # AAPL: composite = 0.25*80 + 0.35*60 + 0.40*90 = 77.0
            MomentumSignal(symbol="AAPL", signal_type=SignalType.CATALYST, strength=80.0, detected_at=datetime.now(UTC), details={}),
            MomentumSignal(symbol="AAPL", signal_type=SignalType.PREMARKET, strength=60.0, detected_at=datetime.now(UTC), details={}),
            MomentumSignal(symbol="AAPL", signal_type=SignalType.PATTERN, strength=90.0, detected_at=datetime.now(UTC), details={}),

            # GOOGL: composite = 0.25*30 + 0.35*40 + 0.40*35 = 35.5
            MomentumSignal(symbol="GOOGL", signal_type=SignalType.CATALYST, strength=30.0, detected_at=datetime.now(UTC), details={}),
            MomentumSignal(symbol="GOOGL", signal_type=SignalType.PREMARKET, strength=40.0, detected_at=datetime.now(UTC), details={}),
            MomentumSignal(symbol="GOOGL", signal_type=SignalType.PATTERN, strength=35.0, detected_at=datetime.now(UTC), details={}),
        ]

        # Act
        ranked_signals = ranker.rank(signals)

        # Assert
        assert len(ranked_signals) == 3
        assert ranked_signals[0].symbol == "AAPL"  # 77.0
        assert ranked_signals[1].symbol == "TSLA"  # 50.0
        assert ranked_signals[2].symbol == "GOOGL"  # 35.5

    def test_rank_includes_component_scores_in_details(self, momentum_logger):
        """
        Given signals for AAPL
        When rank is called
        Then composite signal includes component signal details and composite score
        """
        # Arrange
        ranker = MomentumRanker(momentum_logger=momentum_logger)

        signals = [
            MomentumSignal(symbol="AAPL", signal_type=SignalType.CATALYST, strength=80.0, detected_at=datetime.now(UTC), details={"catalyst_type": "earnings"}),
            MomentumSignal(symbol="AAPL", signal_type=SignalType.PREMARKET, strength=60.0, detected_at=datetime.now(UTC), details={"change_pct": 6.0}),
            MomentumSignal(symbol="AAPL", signal_type=SignalType.PATTERN, strength=90.0, detected_at=datetime.now(UTC), details={"pattern_type": "bull_flag"}),
        ]

        # Act
        ranked_signals = ranker.rank(signals)

        # Assert
        assert len(ranked_signals) == 1
        details = ranked_signals[0].details
        assert details["composite_score"] == pytest.approx(77.0, rel=1e-9)
        assert details["signal_count"] == 3
        assert "catalyst" in details
        assert details["catalyst"]["catalyst_type"] == "earnings"
        assert "premarket" in details
        assert details["premarket"]["change_pct"] == 6.0
        assert "pattern" in details
        assert details["pattern"]["pattern_type"] == "bull_flag"


@pytest.fixture
def momentum_logger(tmp_path):
    """Fixture for MomentumLogger with temporary log directory."""
    log_dir = tmp_path / "logs" / "momentum"
    return MomentumLogger(log_dir=log_dir)
