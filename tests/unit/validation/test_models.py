"""
Tests for multi-timeframe validation models (TimeframeIndicators, TimeframeValidationResult, ValidationStatus).

TDD approach: Write failing tests before implementation.
"""

import pytest
from datetime import datetime
from decimal import Decimal
from dataclasses import FrozenInstanceError

from src.trading_bot.validation.models import (
    ValidationStatus,
    TimeframeIndicators,
    TimeframeValidationResult
)


class TestTimeframeIndicators:
    """Tests for TimeframeIndicators dataclass."""

    def test_timeframe_indicators_immutable(self):
        """Test: TimeframeIndicators is frozen and cannot be modified after creation.

        Given: A TimeframeIndicators instance
        When: Attempting to modify a field
        Then: FrozenInstanceError is raised
        """
        # Given
        indicators = TimeframeIndicators(
            timeframe="DAILY",
            price=Decimal("150.00"),
            ema_20=Decimal("148.50"),
            macd_line=Decimal("0.52"),
            macd_positive=True,
            price_above_ema=True,
            bar_count=60,
            timestamp=datetime(2024, 10, 28, 12, 0, 0)
        )

        # When/Then
        with pytest.raises(FrozenInstanceError):
            indicators.price = Decimal("151.00")

    def test_timeframe_indicators_creation(self):
        """Test: TimeframeIndicators can be created with all required fields.

        Given: Valid indicator data
        When: Creating TimeframeIndicators instance
        Then: Instance created with correct values
        """
        # Given
        timestamp = datetime(2024, 10, 28, 12, 0, 0)

        # When
        indicators = TimeframeIndicators(
            timeframe="4H",
            price=Decimal("150.00"),
            ema_20=Decimal("148.50"),
            macd_line=Decimal("0.52"),
            macd_positive=True,
            price_above_ema=True,
            bar_count=72,
            timestamp=timestamp
        )

        # Then
        assert indicators.timeframe == "4H"
        assert indicators.price == Decimal("150.00")
        assert indicators.ema_20 == Decimal("148.50")
        assert indicators.macd_line == Decimal("0.52")
        assert indicators.macd_positive is True
        assert indicators.price_above_ema is True
        assert indicators.bar_count == 72
        assert indicators.timestamp == timestamp


class TestValidationStatus:
    """Tests for ValidationStatus enum."""

    def test_validation_result_status_transitions(self):
        """Test: ValidationStatus enum has correct values (PASS, BLOCK, DEGRADED).

        Given: ValidationStatus enum
        When: Accessing enum values
        Then: All expected values are present
        """
        # Given/When/Then
        assert ValidationStatus.PASS.value == "PASS"
        assert ValidationStatus.BLOCK.value == "BLOCK"
        assert ValidationStatus.DEGRADED.value == "DEGRADED"

        # Verify all members
        assert len(ValidationStatus) == 3


class TestTimeframeValidationResult:
    """Tests for TimeframeValidationResult dataclass."""

    def test_scoring_logic_0_to_1_range(self):
        """Test: aggregate_score validation enforces range [0.0, 1.0].

        Given: TimeframeValidationResult with score outside range
        When: Creating instance
        Then: ValueError is raised with descriptive message
        """
        # Given
        indicators = TimeframeIndicators(
            timeframe="DAILY",
            price=Decimal("150.00"),
            ema_20=Decimal("148.50"),
            macd_line=Decimal("0.52"),
            macd_positive=True,
            price_above_ema=True,
            bar_count=60,
            timestamp=datetime(2024, 10, 28, 12, 0, 0)
        )

        # When/Then: Score > 1.0
        with pytest.raises(ValueError, match="aggregate_score must be in range"):
            TimeframeValidationResult(
                status=ValidationStatus.PASS,
                aggregate_score=Decimal("1.5"),  # Invalid: > 1.0
                daily_score=Decimal("1.0"),
                daily_indicators=indicators,
                symbol="AAPL",
                timestamp=datetime.now()
            )

        # When/Then: Score < 0.0
        with pytest.raises(ValueError, match="aggregate_score must be in range"):
            TimeframeValidationResult(
                status=ValidationStatus.BLOCK,
                aggregate_score=Decimal("-0.1"),  # Invalid: < 0.0
                daily_score=Decimal("0.0"),
                daily_indicators=indicators,
                symbol="AAPL",
                timestamp=datetime.now()
            )

    def test_validation_result_immutable(self):
        """Test: TimeframeValidationResult is frozen and cannot be modified.

        Given: A TimeframeValidationResult instance
        When: Attempting to modify a field
        Then: FrozenInstanceError is raised
        """
        # Given
        indicators = TimeframeIndicators(
            timeframe="DAILY",
            price=Decimal("150.00"),
            ema_20=Decimal("148.50"),
            macd_line=Decimal("0.52"),
            macd_positive=True,
            price_above_ema=True,
            bar_count=60,
            timestamp=datetime(2024, 10, 28, 12, 0, 0)
        )

        result = TimeframeValidationResult(
            status=ValidationStatus.PASS,
            aggregate_score=Decimal("0.8"),
            daily_score=Decimal("1.0"),
            daily_indicators=indicators,
            symbol="AAPL",
            timestamp=datetime.now()
        )

        # When/Then
        with pytest.raises(FrozenInstanceError):
            result.aggregate_score = Decimal("0.9")

    def test_validation_result_valid_score_range(self):
        """Test: Valid aggregate_score values [0.0, 1.0] are accepted.

        Given: Valid scores within range
        When: Creating TimeframeValidationResult
        Then: Instance created successfully
        """
        # Given
        indicators = TimeframeIndicators(
            timeframe="DAILY",
            price=Decimal("150.00"),
            ema_20=Decimal("148.50"),
            macd_line=Decimal("0.52"),
            macd_positive=True,
            price_above_ema=True,
            bar_count=60,
            timestamp=datetime(2024, 10, 28, 12, 0, 0)
        )

        # When/Then: Score = 0.0
        result_min = TimeframeValidationResult(
            status=ValidationStatus.BLOCK,
            aggregate_score=Decimal("0.0"),
            daily_score=Decimal("0.0"),
            daily_indicators=indicators,
            symbol="AAPL",
            timestamp=datetime.now()
        )
        assert result_min.aggregate_score == Decimal("0.0")

        # When/Then: Score = 1.0
        result_max = TimeframeValidationResult(
            status=ValidationStatus.PASS,
            aggregate_score=Decimal("1.0"),
            daily_score=Decimal("1.0"),
            daily_indicators=indicators,
            symbol="AAPL",
            timestamp=datetime.now()
        )
        assert result_max.aggregate_score == Decimal("1.0")

        # When/Then: Score = 0.6
        result_mid = TimeframeValidationResult(
            status=ValidationStatus.PASS,
            aggregate_score=Decimal("0.6"),
            daily_score=Decimal("1.0"),
            daily_indicators=indicators,
            symbol="AAPL",
            timestamp=datetime.now()
        )
        assert result_mid.aggregate_score == Decimal("0.6")
