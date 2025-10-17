"""
Unit Tests for Pattern Detection Result Dataclasses

Tests the dataclass models used for bull flag pattern detection results:
- FlagpoleData: Flagpole phase characteristics
- ConsolidationData: Consolidation phase characteristics
- BullFlagResult: Complete pattern detection result

Feature: 003-entry-logic-bull-flag
Task: T009 - Write unit tests for result dataclasses
Pattern Reference: tests/indicators/test_calculators.py
"""

import pytest
from decimal import Decimal
from datetime import datetime, UTC, timedelta

from src.trading_bot.patterns.models import (
    FlagpoleData,
    ConsolidationData,
    BullFlagResult
)


class TestFlagpoleData:
    """Tests for FlagpoleData dataclass."""

    def test_flagpole_data_creation(self):
        """Test FlagpoleData instantiation with valid values.

        Given: Valid FlagpoleData parameters
        When: Creating a FlagpoleData instance
        Then: Object is created with correct field values
        """
        # Given: Valid flagpole parameters
        start_idx = 0
        end_idx = 8
        gain_pct = Decimal("8.5")
        high_price = Decimal("189.88")
        start_price = Decimal("175.00")
        avg_volume = Decimal("2000000")

        # When: Creating FlagpoleData instance
        open_price = Decimal("175.50")
        flagpole = FlagpoleData(
            start_idx=start_idx,
            end_idx=end_idx,
            gain_pct=gain_pct,
            high_price=high_price,
            start_price=start_price,
            open_price=open_price,
            avg_volume=avg_volume
        )

        # Then: All fields are set correctly
        assert flagpole.start_idx == start_idx
        assert flagpole.end_idx == end_idx
        assert flagpole.gain_pct == gain_pct
        assert flagpole.high_price == high_price
        assert flagpole.start_price == start_price
        assert flagpole.open_price == open_price
        assert flagpole.avg_volume == avg_volume

    def test_flagpole_decimal_precision(self):
        """Test FlagpoleData maintains Decimal precision for financial values.

        Given: gain_pct as Decimal with specific precision
        When: Creating and reading back FlagpoleData
        Then: Decimal precision is maintained exactly
        """
        # Given: Precise decimal values
        gain_pct = Decimal("5.5")
        high_price = Decimal("180.5555")
        start_price = Decimal("171.2345")
        avg_volume = Decimal("1234567.89")

        # When: Creating FlagpoleData with precise decimals
        open_price = Decimal("171.5000")
        flagpole = FlagpoleData(
            start_idx=0,
            end_idx=5,
            gain_pct=gain_pct,
            high_price=high_price,
            start_price=start_price,
            open_price=open_price,
            avg_volume=avg_volume
        )

        # Then: Decimal precision is maintained
        assert flagpole.gain_pct == Decimal("5.5")
        assert flagpole.high_price == Decimal("180.5555")
        assert flagpole.start_price == Decimal("171.2345")
        assert flagpole.open_price == Decimal("171.5000")
        assert flagpole.avg_volume == Decimal("1234567.89")

        # Verify types are Decimal, not float
        assert isinstance(flagpole.gain_pct, Decimal)
        assert isinstance(flagpole.high_price, Decimal)
        assert isinstance(flagpole.start_price, Decimal)
        assert isinstance(flagpole.open_price, Decimal)
        assert isinstance(flagpole.avg_volume, Decimal)

    def test_flagpole_data_with_minimum_values(self):
        """Test FlagpoleData with minimum acceptable values.

        Given: Minimum valid flagpole parameters (3 bars, 5% gain)
        When: Creating FlagpoleData
        Then: Instance created successfully
        """
        # Given: Minimum valid values
        flagpole = FlagpoleData(
            start_idx=0,
            end_idx=3,  # Minimum 3 bars
            gain_pct=Decimal("5.0"),  # Minimum 5% gain
            high_price=Decimal("105.00"),
            start_price=Decimal("100.00"),
            open_price=Decimal("100.00"),
            avg_volume=Decimal("1")  # Minimum volume
        )

        # Then: Object created successfully
        assert flagpole.start_idx == 0
        assert flagpole.end_idx == 3
        assert flagpole.gain_pct == Decimal("5.0")

    def test_flagpole_data_with_maximum_values(self):
        """Test FlagpoleData with large realistic values.

        Given: Large but realistic flagpole parameters
        When: Creating FlagpoleData
        Then: Instance handles large values correctly
        """
        # Given: Large realistic values
        flagpole = FlagpoleData(
            start_idx=100,
            end_idx=115,  # 15 bars (typical max)
            gain_pct=Decimal("25.5"),  # Strong gain
            high_price=Decimal("999.99"),
            start_price=Decimal("750.00"),
            open_price=Decimal("750.00"),
            avg_volume=Decimal("50000000")  # High volume
        )

        # Then: Object created with large values
        assert flagpole.end_idx == 115
        assert flagpole.gain_pct == Decimal("25.5")
        assert flagpole.avg_volume == Decimal("50000000")

    def test_flagpole_data_equality(self):
        """Test FlagpoleData equality comparison.

        Given: Two FlagpoleData instances with identical values
        When: Comparing them with ==
        Then: They are equal (dataclass auto-generates __eq__)
        """
        # Given: Two identical FlagpoleData instances
        flagpole1 = FlagpoleData(
            start_idx=0,
            end_idx=8,
            gain_pct=Decimal("8.5"),
            high_price=Decimal("189.88"),
            start_price=Decimal("175.00"),
            open_price=Decimal("175.00"),
            avg_volume=Decimal("2000000")
        )

        flagpole2 = FlagpoleData(
            start_idx=0,
            end_idx=8,
            gain_pct=Decimal("8.5"),
            high_price=Decimal("189.88"),
            start_price=Decimal("175.00"),
            open_price=Decimal("175.00"),
            avg_volume=Decimal("2000000")
        )

        # Then: They are equal
        assert flagpole1 == flagpole2

    def test_flagpole_data_inequality(self):
        """Test FlagpoleData inequality when values differ.

        Given: Two FlagpoleData instances with different values
        When: Comparing them with ==
        Then: They are not equal
        """
        # Given: Two different FlagpoleData instances
        flagpole1 = FlagpoleData(
            start_idx=0,
            end_idx=8,
            gain_pct=Decimal("8.5"),
            high_price=Decimal("189.88"),
            start_price=Decimal("175.00"),
            open_price=Decimal("175.00"),
            avg_volume=Decimal("2000000")
        )

        flagpole2 = FlagpoleData(
            start_idx=0,
            end_idx=8,
            gain_pct=Decimal("9.0"),  # Different gain
            high_price=Decimal("189.88"),
            start_price=Decimal("175.00"),
            open_price=Decimal("175.00"),
            avg_volume=Decimal("2000000")
        )

        # Then: They are not equal
        assert flagpole1 != flagpole2


class TestConsolidationData:
    """Tests for ConsolidationData dataclass."""

    def test_consolidation_data_creation(self):
        """Test ConsolidationData instantiation with valid values.

        Given: Valid ConsolidationData parameters
        When: Creating a ConsolidationData instance
        Then: Object is created with correct field values
        """
        # Given: Valid consolidation parameters
        start_idx = 9
        end_idx = 15
        upper_boundary = Decimal("187.50")
        lower_boundary = Decimal("183.25")
        avg_volume = Decimal("1200000")

        # When: Creating ConsolidationData instance
        consolidation = ConsolidationData(
            start_idx=start_idx,
            end_idx=end_idx,
            upper_boundary=upper_boundary,
            lower_boundary=lower_boundary,
            avg_volume=avg_volume
        )

        # Then: All fields are set correctly
        assert consolidation.start_idx == start_idx
        assert consolidation.end_idx == end_idx
        assert consolidation.upper_boundary == upper_boundary
        assert consolidation.lower_boundary == lower_boundary
        assert consolidation.avg_volume == avg_volume

    def test_consolidation_decimal_precision(self):
        """Test ConsolidationData maintains Decimal precision.

        Given: Precise Decimal values for boundaries and volume
        When: Creating and reading back ConsolidationData
        Then: Decimal precision is maintained exactly
        """
        # Given: Precise decimal values
        upper_boundary = Decimal("187.5555")
        lower_boundary = Decimal("183.2512")
        avg_volume = Decimal("1234567.89")

        # When: Creating ConsolidationData with precise decimals
        consolidation = ConsolidationData(
            start_idx=9,
            end_idx=15,
            upper_boundary=upper_boundary,
            lower_boundary=lower_boundary,
            avg_volume=avg_volume
        )

        # Then: Decimal precision is maintained
        assert consolidation.upper_boundary == Decimal("187.5555")
        assert consolidation.lower_boundary == Decimal("183.2512")
        assert consolidation.avg_volume == Decimal("1234567.89")

        # Verify types are Decimal
        assert isinstance(consolidation.upper_boundary, Decimal)
        assert isinstance(consolidation.lower_boundary, Decimal)
        assert isinstance(consolidation.avg_volume, Decimal)

    def test_consolidation_data_boundaries_valid(self):
        """Test ConsolidationData with valid boundary relationship.

        Given: upper_boundary > lower_boundary (valid relationship)
        When: Creating ConsolidationData
        Then: Instance created successfully
        """
        # Given: Valid boundaries (upper > lower)
        consolidation = ConsolidationData(
            start_idx=10,
            end_idx=18,
            upper_boundary=Decimal("190.00"),
            lower_boundary=Decimal("185.00"),
            avg_volume=Decimal("1500000")
        )

        # Then: Boundaries are stored correctly
        assert consolidation.upper_boundary > consolidation.lower_boundary
        assert consolidation.upper_boundary == Decimal("190.00")
        assert consolidation.lower_boundary == Decimal("185.00")

    def test_consolidation_data_with_minimum_duration(self):
        """Test ConsolidationData with minimum duration (3 bars).

        Given: Minimum consolidation duration (3 bars)
        When: Creating ConsolidationData
        Then: Instance created successfully
        """
        # Given: Minimum 3-bar consolidation
        consolidation = ConsolidationData(
            start_idx=10,
            end_idx=13,  # 3 bars (minimum)
            upper_boundary=Decimal("188.00"),
            lower_boundary=Decimal("185.00"),
            avg_volume=Decimal("1000000")
        )

        # Then: Duration is 3 bars
        duration = consolidation.end_idx - consolidation.start_idx
        assert duration == 3

    def test_consolidation_data_with_maximum_duration(self):
        """Test ConsolidationData with maximum duration (10 bars).

        Given: Maximum consolidation duration (10 bars)
        When: Creating ConsolidationData
        Then: Instance created successfully
        """
        # Given: Maximum 10-bar consolidation
        consolidation = ConsolidationData(
            start_idx=10,
            end_idx=20,  # 10 bars (typical max)
            upper_boundary=Decimal("188.00"),
            lower_boundary=Decimal("185.00"),
            avg_volume=Decimal("1000000")
        )

        # Then: Duration is 10 bars
        duration = consolidation.end_idx - consolidation.start_idx
        assert duration == 10

    def test_consolidation_data_equality(self):
        """Test ConsolidationData equality comparison.

        Given: Two ConsolidationData instances with identical values
        When: Comparing them with ==
        Then: They are equal
        """
        # Given: Two identical instances
        consol1 = ConsolidationData(
            start_idx=9,
            end_idx=15,
            upper_boundary=Decimal("187.50"),
            lower_boundary=Decimal("183.25"),
            avg_volume=Decimal("1200000")
        )

        consol2 = ConsolidationData(
            start_idx=9,
            end_idx=15,
            upper_boundary=Decimal("187.50"),
            lower_boundary=Decimal("183.25"),
            avg_volume=Decimal("1200000")
        )

        # Then: They are equal
        assert consol1 == consol2

    def test_consolidation_data_with_tight_range(self):
        """Test ConsolidationData with tight boundary range.

        Given: Very tight consolidation range (tight flag)
        When: Creating ConsolidationData
        Then: Instance handles small differences correctly
        """
        # Given: Tight consolidation range (1% range)
        consolidation = ConsolidationData(
            start_idx=10,
            end_idx=15,
            upper_boundary=Decimal("100.50"),
            lower_boundary=Decimal("99.50"),  # 1% range
            avg_volume=Decimal("1000000")
        )

        # Then: Small range preserved with precision
        range_pct = ((consolidation.upper_boundary - consolidation.lower_boundary)
                     / consolidation.lower_boundary * Decimal("100"))
        assert range_pct < Decimal("2.0")  # Less than 2% range


class TestBullFlagResult:
    """Tests for BullFlagResult dataclass."""

    def test_bull_flag_result_creation(self):
        """Test BullFlagResult instantiation with complete data.

        Given: Complete BullFlagResult with all fields populated
        When: Creating a BullFlagResult instance
        Then: Object is created successfully with all fields
        """
        # Given: Complete pattern detection result
        symbol = "AAPL"
        timestamp = datetime.now(UTC)
        detected = True

        flagpole = FlagpoleData(
            start_idx=0,
            end_idx=8,
            gain_pct=Decimal("8.5"),
            high_price=Decimal("189.88"),
            start_price=Decimal("175.00"),
            open_price=Decimal("175.00"),
            avg_volume=Decimal("2000000")
        )

        consolidation = ConsolidationData(
            start_idx=9,
            end_idx=15,
            upper_boundary=Decimal("187.50"),
            lower_boundary=Decimal("183.25"),
            avg_volume=Decimal("1200000")
        )

        entry_price = Decimal("188.00")
        stop_loss = Decimal("182.33")
        target_price = Decimal("202.88")
        quality_score = 85
        risk_reward_ratio = Decimal("2.6")

        # When: Creating BullFlagResult
        result = BullFlagResult(
            symbol=symbol,
            timestamp=timestamp,
            detected=detected,
            flagpole=flagpole,
            consolidation=consolidation,
            entry_price=entry_price,
            stop_loss=stop_loss,
            target_price=target_price,
            quality_score=quality_score,
            risk_reward_ratio=risk_reward_ratio
        )

        # Then: All fields are set correctly
        assert result.symbol == symbol
        assert result.timestamp == timestamp
        assert result.detected is True
        assert result.flagpole == flagpole
        assert result.consolidation == consolidation
        assert result.entry_price == entry_price
        assert result.stop_loss == stop_loss
        assert result.target_price == target_price
        assert result.quality_score == quality_score
        assert result.risk_reward_ratio == risk_reward_ratio

    def test_bull_flag_result_no_pattern(self):
        """Test BullFlagResult when no pattern detected.

        Given: BullFlagResult with detected=False
        When: Creating instance with None for optional fields
        Then: Optional fields can be None (no pattern found)
        """
        # Given: No pattern detected
        symbol = "AAPL"
        timestamp = datetime.now(UTC)
        detected = False

        # When: Creating result with no pattern
        result = BullFlagResult(
            symbol=symbol,
            timestamp=timestamp,
            detected=detected,
            flagpole=None,
            consolidation=None,
            entry_price=None,
            stop_loss=None,
            target_price=None,
            quality_score=None,
            risk_reward_ratio=None
        )

        # Then: Pattern not detected, optional fields are None
        assert result.detected is False
        assert result.flagpole is None
        assert result.consolidation is None
        assert result.entry_price is None
        assert result.stop_loss is None
        assert result.target_price is None
        assert result.quality_score is None
        assert result.risk_reward_ratio is None

    def test_bull_flag_result_pattern_without_entry(self):
        """Test BullFlagResult with pattern but no valid entry signal.

        Given: Pattern detected but failed validation (no entry)
        When: Creating result with pattern but no entry/stop/target
        Then: Can have flagpole/consolidation without entry parameters
        """
        # Given: Pattern exists but no entry signal
        flagpole = FlagpoleData(
            start_idx=0,
            end_idx=8,
            gain_pct=Decimal("8.5"),
            high_price=Decimal("189.88"),
            start_price=Decimal("175.00"),
            open_price=Decimal("175.00"),
            avg_volume=Decimal("2000000")
        )

        consolidation = ConsolidationData(
            start_idx=9,
            end_idx=15,
            upper_boundary=Decimal("187.50"),
            lower_boundary=Decimal("183.25"),
            avg_volume=Decimal("1200000")
        )

        # When: Creating result with pattern but no entry
        result = BullFlagResult(
            symbol="AAPL",
            timestamp=datetime.now(UTC),
            detected=True,  # Pattern detected
            flagpole=flagpole,
            consolidation=consolidation,
            entry_price=None,  # But no entry signal
            stop_loss=None,
            target_price=None,
            quality_score=45,  # Low quality score
            risk_reward_ratio=None
        )

        # Then: Has pattern data but no entry parameters
        assert result.detected is True
        assert result.flagpole is not None
        assert result.consolidation is not None
        assert result.entry_price is None
        assert result.quality_score == 45

    def test_timestamp_handling(self):
        """Test BullFlagResult timestamp preservation.

        Given: Specific datetime for pattern detection
        When: Creating BullFlagResult with timestamp
        Then: Timestamp is preserved correctly with timezone
        """
        # Given: Specific timestamp with timezone
        detection_time = datetime(2025, 10, 17, 14, 30, 0, tzinfo=UTC)

        # When: Creating result with specific timestamp
        result = BullFlagResult(
            symbol="TSLA",
            timestamp=detection_time,
            detected=True,
            flagpole=None,
            consolidation=None,
            entry_price=None,
            stop_loss=None,
            target_price=None,
            quality_score=None,
            risk_reward_ratio=None
        )

        # Then: Timestamp preserved exactly
        assert result.timestamp == detection_time
        assert result.timestamp.year == 2025
        assert result.timestamp.month == 10
        assert result.timestamp.day == 17
        assert result.timestamp.hour == 14
        assert result.timestamp.tzinfo == UTC

    def test_timestamp_recent(self):
        """Test BullFlagResult with recent timestamp.

        Given: Current datetime for real-time detection
        When: Creating result with datetime.now(UTC)
        Then: Timestamp reflects current time
        """
        # Given: Current time
        before = datetime.now(UTC)

        # When: Creating result with current timestamp
        result = BullFlagResult(
            symbol="NVDA",
            timestamp=datetime.now(UTC),
            detected=False,
            flagpole=None,
            consolidation=None,
            entry_price=None,
            stop_loss=None,
            target_price=None,
            quality_score=None,
            risk_reward_ratio=None
        )

        after = datetime.now(UTC)

        # Then: Timestamp is between before and after (recent)
        assert before <= result.timestamp <= after

    def test_bull_flag_result_decimal_precision(self):
        """Test BullFlagResult maintains Decimal precision for prices.

        Given: Precise Decimal values for all price fields
        When: Creating BullFlagResult
        Then: Decimal precision maintained for financial calculations
        """
        # Given: Precise decimal values
        entry_price = Decimal("188.1234")
        stop_loss = Decimal("182.5678")
        target_price = Decimal("202.9876")
        risk_reward_ratio = Decimal("2.6543")

        # When: Creating result with precise decimals
        result = BullFlagResult(
            symbol="AAPL",
            timestamp=datetime.now(UTC),
            detected=True,
            flagpole=None,
            consolidation=None,
            entry_price=entry_price,
            stop_loss=stop_loss,
            target_price=target_price,
            quality_score=85,
            risk_reward_ratio=risk_reward_ratio
        )

        # Then: Decimal precision maintained
        assert result.entry_price == Decimal("188.1234")
        assert result.stop_loss == Decimal("182.5678")
        assert result.target_price == Decimal("202.9876")
        assert result.risk_reward_ratio == Decimal("2.6543")

        # Verify types are Decimal
        assert isinstance(result.entry_price, Decimal)
        assert isinstance(result.stop_loss, Decimal)
        assert isinstance(result.target_price, Decimal)
        assert isinstance(result.risk_reward_ratio, Decimal)

    def test_bull_flag_result_quality_score_range(self):
        """Test BullFlagResult with valid quality score range.

        Given: Quality scores at boundaries (0, 50, 100)
        When: Creating BullFlagResult instances
        Then: All valid scores accepted (0-100)
        """
        # Given/When/Then: Minimum score (0)
        result_min = BullFlagResult(
            symbol="TEST",
            timestamp=datetime.now(UTC),
            detected=True,
            flagpole=None,
            consolidation=None,
            entry_price=None,
            stop_loss=None,
            target_price=None,
            quality_score=0,  # Minimum
            risk_reward_ratio=None
        )
        assert result_min.quality_score == 0

        # Given/When/Then: Mid-range score (50)
        result_mid = BullFlagResult(
            symbol="TEST",
            timestamp=datetime.now(UTC),
            detected=True,
            flagpole=None,
            consolidation=None,
            entry_price=None,
            stop_loss=None,
            target_price=None,
            quality_score=50,  # Mid-range
            risk_reward_ratio=None
        )
        assert result_mid.quality_score == 50

        # Given/When/Then: Maximum score (100)
        result_max = BullFlagResult(
            symbol="TEST",
            timestamp=datetime.now(UTC),
            detected=True,
            flagpole=None,
            consolidation=None,
            entry_price=None,
            stop_loss=None,
            target_price=None,
            quality_score=100,  # Maximum
            risk_reward_ratio=None
        )
        assert result_max.quality_score == 100

    def test_bull_flag_result_risk_parameters_valid(self):
        """Test BullFlagResult with valid risk parameter relationships.

        Given: stop_loss < entry_price < target_price (valid setup)
        When: Creating BullFlagResult
        Then: Risk parameters follow correct relationship
        """
        # Given: Valid risk parameter relationship
        stop_loss = Decimal("180.00")
        entry_price = Decimal("190.00")
        target_price = Decimal("210.00")

        # When: Creating result with valid risk params
        result = BullFlagResult(
            symbol="AAPL",
            timestamp=datetime.now(UTC),
            detected=True,
            flagpole=None,
            consolidation=None,
            entry_price=entry_price,
            stop_loss=stop_loss,
            target_price=target_price,
            quality_score=85,
            risk_reward_ratio=Decimal("2.0")
        )

        # Then: Risk parameters follow correct order
        assert result.stop_loss < result.entry_price < result.target_price
        # Calculate risk/reward manually to verify
        risk = result.entry_price - result.stop_loss  # 10.00
        reward = result.target_price - result.entry_price  # 20.00
        calculated_rr = reward / risk  # 2.0
        assert calculated_rr == Decimal("2.0")

    def test_bull_flag_result_equality(self):
        """Test BullFlagResult equality comparison.

        Given: Two BullFlagResult instances with identical values
        When: Comparing them with ==
        Then: They are equal
        """
        # Given: Shared timestamp and components
        timestamp = datetime.now(UTC)
        flagpole = FlagpoleData(
            start_idx=0,
            end_idx=8,
            gain_pct=Decimal("8.5"),
            high_price=Decimal("189.88"),
            start_price=Decimal("175.00"),
            open_price=Decimal("175.00"),
            avg_volume=Decimal("2000000")
        )

        # When: Creating two identical results
        result1 = BullFlagResult(
            symbol="AAPL",
            timestamp=timestamp,
            detected=True,
            flagpole=flagpole,
            consolidation=None,
            entry_price=Decimal("188.00"),
            stop_loss=Decimal("182.33"),
            target_price=Decimal("202.88"),
            quality_score=85,
            risk_reward_ratio=Decimal("2.6")
        )

        result2 = BullFlagResult(
            symbol="AAPL",
            timestamp=timestamp,
            detected=True,
            flagpole=flagpole,
            consolidation=None,
            entry_price=Decimal("188.00"),
            stop_loss=Decimal("182.33"),
            target_price=Decimal("202.88"),
            quality_score=85,
            risk_reward_ratio=Decimal("2.6")
        )

        # Then: They are equal
        assert result1 == result2

    def test_bull_flag_result_with_multiple_symbols(self):
        """Test BullFlagResult with different stock symbols.

        Given: Various stock ticker symbols
        When: Creating BullFlagResult instances
        Then: Symbol field stores different tickers correctly
        """
        # Given/When: Different symbols
        symbols = ["AAPL", "TSLA", "NVDA", "MSFT", "GOOGL"]

        results = []
        for symbol in symbols:
            result = BullFlagResult(
                symbol=symbol,
                timestamp=datetime.now(UTC),
                detected=False,
                flagpole=None,
                consolidation=None,
                entry_price=None,
                stop_loss=None,
                target_price=None,
                quality_score=None,
                risk_reward_ratio=None
            )
            results.append(result)

        # Then: All symbols stored correctly
        for i, result in enumerate(results):
            assert result.symbol == symbols[i]
