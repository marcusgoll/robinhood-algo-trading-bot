"""
Unit tests for TargetCalculation dataclass.

Tests:
- T005: TargetCalculation validates adjusted_target > 0
- T006: TargetCalculation validates original_2r_target > 0
- T007: TargetCalculation is immutable (frozen=True)
- T008: TargetCalculation validates adjustment_reason enum

Feature: zone-bull-flag-integration
Tasks: T005 [RED] - Write test for adjusted_target validation
       T006 [RED] - Write test for original_2r_target validation
       T007 [RED] - Write test for immutability
       T008 [RED] - Write test for adjustment_reason enum validation
"""

import pytest
from decimal import Decimal
from dataclasses import FrozenInstanceError

from src.trading_bot.momentum.schemas.momentum_signal import TargetCalculation


class TestTargetCalculationValidation:
    """Test TargetCalculation validation rules."""

    def test_adjusted_target_validation_negative_value_raises_error(self):
        """
        T005: TargetCalculation validates adjusted_target > 0.

        Given: adjusted_target = Decimal("-10.50")
        When: TargetCalculation instantiated
        Then: ValueError raised with message "adjusted_target must be > 0"
        """
        with pytest.raises(ValueError) as exc_info:
            TargetCalculation(
                adjusted_target=Decimal("-10.50"),
                original_2r_target=Decimal("156.00"),
                adjustment_reason="zone_resistance",
                resistance_zone_price=Decimal("155.00"),
                resistance_zone_strength=7.5
            )

        error_message = str(exc_info.value)
        assert "adjusted_target" in error_message and "must be > 0" in error_message

    def test_adjusted_target_validation_zero_value_raises_error(self):
        """
        T005: TargetCalculation validates adjusted_target > 0 (edge case: zero).

        Given: adjusted_target = Decimal("0.00")
        When: TargetCalculation instantiated
        Then: ValueError raised with message "adjusted_target must be > 0"
        """
        with pytest.raises(ValueError) as exc_info:
            TargetCalculation(
                adjusted_target=Decimal("0.00"),
                original_2r_target=Decimal("156.00"),
                adjustment_reason="zone_resistance",
                resistance_zone_price=Decimal("155.00"),
                resistance_zone_strength=7.5
            )

        error_message = str(exc_info.value)
        assert "adjusted_target" in error_message and "must be > 0" in error_message

    def test_original_2r_target_validation_zero_value_raises_error(self):
        """
        T006: TargetCalculation validates original_2r_target > 0.

        Given: original_2r_target = Decimal("0.00")
        When: TargetCalculation instantiated
        Then: ValueError raised with message "original_2r_target must be > 0"
        """
        with pytest.raises(ValueError) as exc_info:
            TargetCalculation(
                adjusted_target=Decimal("139.50"),
                original_2r_target=Decimal("0.00"),
                adjustment_reason="zone_resistance",
                resistance_zone_price=Decimal("155.00"),
                resistance_zone_strength=7.5
            )

        error_message = str(exc_info.value)
        assert "original_2r_target" in error_message and "must be > 0" in error_message

    def test_original_2r_target_validation_negative_value_raises_error(self):
        """
        T006: TargetCalculation validates original_2r_target > 0 (edge case: negative).

        Given: original_2r_target = Decimal("-100.00")
        When: TargetCalculation instantiated
        Then: ValueError raised with message "original_2r_target must be > 0"
        """
        with pytest.raises(ValueError) as exc_info:
            TargetCalculation(
                adjusted_target=Decimal("139.50"),
                original_2r_target=Decimal("-100.00"),
                adjustment_reason="zone_resistance",
                resistance_zone_price=Decimal("155.00"),
                resistance_zone_strength=7.5
            )

        error_message = str(exc_info.value)
        assert "original_2r_target" in error_message and "must be > 0" in error_message


class TestTargetCalculationImmutability:
    """Test TargetCalculation immutability (frozen=True)."""

    def test_immutability_frozen_instance_error_on_modification(self):
        """
        T007: TargetCalculation is immutable (frozen=True).

        Given: valid TargetCalculation instance
        When: Attempt to modify adjusted_target field
        Then: FrozenInstanceError raised
        """
        target_calc = TargetCalculation(
            adjusted_target=Decimal("139.50"),
            original_2r_target=Decimal("156.00"),
            adjustment_reason="zone_resistance",
            resistance_zone_price=Decimal("155.00"),
            resistance_zone_strength=7.5
        )

        with pytest.raises(FrozenInstanceError):
            target_calc.adjusted_target = Decimal("200.00")

    def test_immutability_frozen_instance_error_on_reason_modification(self):
        """
        T007: TargetCalculation is immutable (frozen=True) - additional field test.

        Given: valid TargetCalculation instance
        When: Attempt to modify adjustment_reason field
        Then: FrozenInstanceError raised
        """
        target_calc = TargetCalculation(
            adjusted_target=Decimal("139.50"),
            original_2r_target=Decimal("156.00"),
            adjustment_reason="zone_resistance",
            resistance_zone_price=Decimal("155.00"),
            resistance_zone_strength=7.5
        )

        with pytest.raises(FrozenInstanceError):
            target_calc.adjustment_reason = "no_zone"


class TestTargetCalculationAdjustmentReasonValidation:
    """Test TargetCalculation adjustment_reason enum validation."""

    def test_adjustment_reason_validation_invalid_reason_raises_error(self):
        """
        T008: TargetCalculation validates adjustment_reason enum.

        Given: adjustment_reason = "invalid_reason"
        When: TargetCalculation instantiated
        Then: ValueError raised with message listing valid reasons
        """
        with pytest.raises(ValueError) as exc_info:
            TargetCalculation(
                adjusted_target=Decimal("139.50"),
                original_2r_target=Decimal("156.00"),
                adjustment_reason="invalid_reason",
                resistance_zone_price=Decimal("155.00"),
                resistance_zone_strength=7.5
            )

        error_message = str(exc_info.value)
        assert "adjustment_reason" in error_message
        # Should list valid reasons
        assert "zone_resistance" in error_message or "valid reasons" in error_message.lower()

    def test_adjustment_reason_validation_empty_string_raises_error(self):
        """
        T008: TargetCalculation validates adjustment_reason enum (edge case: empty string).

        Given: adjustment_reason = ""
        When: TargetCalculation instantiated
        Then: ValueError raised
        """
        with pytest.raises(ValueError) as exc_info:
            TargetCalculation(
                adjusted_target=Decimal("139.50"),
                original_2r_target=Decimal("156.00"),
                adjustment_reason="",
                resistance_zone_price=Decimal("155.00"),
                resistance_zone_strength=7.5
            )

        assert "adjustment_reason" in str(exc_info.value)

    def test_adjustment_reason_validation_all_valid_reasons_accepted(self):
        """
        T008: TargetCalculation accepts all valid adjustment_reason values.

        Given: Valid adjustment_reason values from spec
        When: TargetCalculation instantiated with each valid reason
        Then: No exception raised
        """
        valid_reasons = ["zone_resistance", "no_zone", "zone_detection_failed"]

        for reason in valid_reasons:
            # Should not raise any exception
            target_calc = TargetCalculation(
                adjusted_target=Decimal("139.50"),
                original_2r_target=Decimal("156.00"),
                adjustment_reason=reason,
                resistance_zone_price=Decimal("155.00") if reason == "zone_resistance" else None,
                resistance_zone_strength=7.5 if reason == "zone_resistance" else None
            )
            assert target_calc.adjustment_reason == reason


class TestTargetCalculationValidInstances:
    """Test valid TargetCalculation instances can be created."""

    def test_valid_instance_creation_with_zone_resistance(self):
        """
        Test that valid TargetCalculation with zone_resistance can be created.

        Given: All valid field values with zone resistance
        When: TargetCalculation instantiated
        Then: Instance created successfully with correct values
        """
        target_calc = TargetCalculation(
            adjusted_target=Decimal("139.50"),
            original_2r_target=Decimal("156.00"),
            adjustment_reason="zone_resistance",
            resistance_zone_price=Decimal("155.00"),
            resistance_zone_strength=7.5
        )

        assert target_calc.adjusted_target == Decimal("139.50")
        assert target_calc.original_2r_target == Decimal("156.00")
        assert target_calc.adjustment_reason == "zone_resistance"
        assert target_calc.resistance_zone_price == Decimal("155.00")
        assert target_calc.resistance_zone_strength == 7.5

    def test_valid_instance_creation_with_no_zone(self):
        """
        Test that valid TargetCalculation with no_zone can be created.

        Given: Valid field values with no zone detected
        When: TargetCalculation instantiated
        Then: Instance created successfully with None zone values
        """
        target_calc = TargetCalculation(
            adjusted_target=Decimal("156.00"),
            original_2r_target=Decimal("156.00"),
            adjustment_reason="no_zone",
            resistance_zone_price=None,
            resistance_zone_strength=None
        )

        assert target_calc.adjusted_target == Decimal("156.00")
        assert target_calc.original_2r_target == Decimal("156.00")
        assert target_calc.adjustment_reason == "no_zone"
        assert target_calc.resistance_zone_price is None
        assert target_calc.resistance_zone_strength is None
