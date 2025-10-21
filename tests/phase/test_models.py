"""
Unit Tests for Phase Enum and Related Models

Tests the Phase enum used for trading progression phases:
- Phase enum: Experience, Proof of Concept, Real Money Trial, Scaling

Feature: 022-pos-scale-progress
Task: T010 - Write FAILING tests for Phase enum (TDD RED phase)
Pattern Reference: tests/patterns/test_models.py
"""

import pytest

from src.trading_bot.phase.models import Phase  # This will fail initially - no models.py yet


class TestPhaseEnum:
    """Tests for Phase enum."""

    def test_phase_enum_values(self):
        """Test that all 4 phases are defined.

        Given: Phase enum should have 4 progression phases
        When: Accessing Phase enum values
        Then: All 4 phases (EXPERIENCE, PROOF_OF_CONCEPT, REAL_MONEY_TRIAL, SCALING) exist
        """
        # Given/When: Phase enum should have all 4 values
        # Then: All phases are defined
        assert Phase.EXPERIENCE
        assert Phase.PROOF_OF_CONCEPT
        assert Phase.REAL_MONEY_TRIAL
        assert Phase.SCALING

    def test_phase_string_conversion(self):
        """Test Phase enum to/from string conversion.

        Given: Phase enum values with string representations
        When: Converting to/from strings using .value and from_string()
        Then: String conversion works bidirectionally
        """
        # Given/When: Phase.EXPERIENCE has string value "experience"
        assert Phase.EXPERIENCE.value == "experience"
        assert Phase.from_string("experience") == Phase.EXPERIENCE

        # Given/When: Phase.PROOF_OF_CONCEPT has string value "proof"
        assert Phase.PROOF_OF_CONCEPT.value == "proof"
        assert Phase.from_string("proof") == Phase.PROOF_OF_CONCEPT

        # Given/When: Phase.REAL_MONEY_TRIAL has string value "trial"
        assert Phase.REAL_MONEY_TRIAL.value == "trial"
        assert Phase.from_string("trial") == Phase.REAL_MONEY_TRIAL

        # Given/When: Phase.SCALING has string value "scaling"
        assert Phase.SCALING.value == "scaling"
        assert Phase.from_string("scaling") == Phase.SCALING

    def test_invalid_phase_handling(self):
        """Test invalid phase name raises ValueError.

        Given: An invalid phase name string
        When: Attempting to convert with from_string()
        Then: ValueError is raised
        """
        # Given: Invalid phase name
        invalid_phase = "invalid_phase"

        # When/Then: from_string() raises ValueError
        with pytest.raises(ValueError):
            Phase.from_string(invalid_phase)

    def test_phase_enum_order(self):
        """Test phase enum values are ordered correctly.

        Given: Phase enum should follow progression order
        When: Iterating through Phase values
        Then: Phases appear in order: EXPERIENCE, PROOF_OF_CONCEPT, REAL_MONEY_TRIAL, SCALING
        """
        # Given: Phase enum values in list form
        phases = list(Phase)

        # Then: Phases are in progression order
        assert phases[0] == Phase.EXPERIENCE
        assert phases[1] == Phase.PROOF_OF_CONCEPT
        assert phases[2] == Phase.REAL_MONEY_TRIAL
        assert phases[3] == Phase.SCALING

    def test_phase_enum_count(self):
        """Test that Phase enum has exactly 4 values.

        Given: Phase enum for trading progression
        When: Counting enum members
        Then: Exactly 4 phases are defined
        """
        # Given: Phase enum members
        phases = list(Phase)

        # Then: Exactly 4 phases
        assert len(phases) == 4

    def test_phase_string_values_match_spec(self):
        """Test Phase string values match data-model.md specification.

        Given: Phase enum string values from spec (experience, proof, trial, scaling)
        When: Checking .value attributes
        Then: String values match specification exactly
        """
        # Given: Expected string values from spec
        expected_values = {"experience", "proof", "trial", "scaling"}

        # When: Getting actual enum values
        actual_values = {phase.value for phase in Phase}

        # Then: Values match specification
        assert actual_values == expected_values

    def test_phase_from_string_case_sensitive(self):
        """Test from_string() is case-sensitive.

        Given: Phase string values in different cases
        When: Converting with from_string()
        Then: Only lowercase values work (case-sensitive)
        """
        # Given: Valid lowercase phase
        assert Phase.from_string("experience") == Phase.EXPERIENCE

        # When/Then: Uppercase should raise ValueError
        with pytest.raises(ValueError):
            Phase.from_string("EXPERIENCE")

        # When/Then: Mixed case should raise ValueError
        with pytest.raises(ValueError):
            Phase.from_string("Experience")
