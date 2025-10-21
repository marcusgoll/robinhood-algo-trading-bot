"""Tests for PhaseManager orchestration service.

TDD RED phase: Write failing tests for PhaseManager.
- validate_transition() tests
- advance_phase() tests
- Error handling tests

Based on specs/022-pos-scale-progress/contracts/phase-api.yaml
Tasks: T040-T041
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from trading_bot.phase.models import Phase, PhaseTransition
from trading_bot.phase.validators import ValidationResult
from trading_bot.phase.manager import PhaseManager, PhaseValidationError
from trading_bot.config import Config


class TestPhaseManagerValidateTransition:
    """Test PhaseManager.validate_transition() method."""

    def test_experience_to_poc_criteria_met(self):
        """Should return can_advance=True when criteria met."""
        # Arrange
        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="experience"
        )
        manager = PhaseManager(config)

        # Mock metrics (will be passed from PerformanceTracker in real impl)
        manager._metrics = {
            "session_count": 20,
            "win_rate": Decimal("0.60"),
            "avg_rr": Decimal("1.5")
        }

        # Act
        result = manager.validate_transition(Phase.PROOF_OF_CONCEPT)

        # Assert
        assert result.can_advance is True
        assert result.criteria_met["session_count"] is True
        assert result.criteria_met["win_rate"] is True
        assert result.criteria_met["avg_rr"] is True
        assert len(result.missing_requirements) == 0

    def test_experience_to_poc_criteria_not_met(self):
        """Should return can_advance=False when criteria not met."""
        # Arrange
        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="experience"
        )
        manager = PhaseManager(config)

        # Mock metrics - only 15 sessions (need 20)
        manager._metrics = {
            "session_count": 15,
            "win_rate": Decimal("0.58"),
            "avg_rr": Decimal("1.4")
        }

        # Act
        result = manager.validate_transition(Phase.PROOF_OF_CONCEPT)

        # Assert
        assert result.can_advance is False
        assert "session_count" in result.missing_requirements
        assert "win_rate" in result.missing_requirements
        assert "avg_rr" in result.missing_requirements

    def test_poc_to_trial_criteria_met(self):
        """Should validate PoC → Trial transition with all criteria met."""
        # Arrange
        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="proof"
        )
        manager = PhaseManager(config)

        manager._metrics = {
            "session_count": 30,
            "trade_count": 50,
            "win_rate": Decimal("0.65"),
            "avg_rr": Decimal("1.8")
        }

        # Act
        result = manager.validate_transition(Phase.REAL_MONEY_TRIAL)

        # Assert
        assert result.can_advance is True
        assert all(result.criteria_met.values())

    def test_trial_to_scaling_criteria_met(self):
        """Should validate Trial → Scaling transition with all criteria met."""
        # Arrange
        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="trial"
        )
        manager = PhaseManager(config)

        manager._metrics = {
            "session_count": 60,
            "trade_count": 100,
            "win_rate": Decimal("0.70"),
            "avg_rr": Decimal("2.0"),
            "max_drawdown": Decimal("0.04")
        }

        # Act
        result = manager.validate_transition(Phase.SCALING)

        # Assert
        assert result.can_advance is True
        assert all(result.criteria_met.values())

    def test_non_sequential_transition_raises_error(self):
        """Should raise ValueError for non-sequential phase transition."""
        # Arrange
        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="experience"
        )
        manager = PhaseManager(config)

        # Act & Assert
        with pytest.raises(ValueError, match="Non-sequential transition"):
            manager.validate_transition(Phase.SCALING)

    def test_invalid_validator_raises_error(self):
        """Should raise ValueError if no validator exists for transition."""
        # Arrange
        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="scaling"
        )
        manager = PhaseManager(config)

        # Act & Assert - trying to go backwards (non-sequential)
        # This will hit the sequential check first before checking for validator
        with pytest.raises(ValueError, match="Non-sequential transition"):
            manager.validate_transition(Phase.EXPERIENCE)


class TestPhaseManagerAdvancePhase:
    """Test PhaseManager.advance_phase() method."""

    def test_advance_with_validation_pass(self):
        """Should advance phase when validation passes."""
        # Arrange
        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="experience"
        )
        manager = PhaseManager(config)

        manager._metrics = {
            "session_count": 20,
            "win_rate": Decimal("0.60"),
            "avg_rr": Decimal("1.5")
        }

        # Act
        transition = manager.advance_phase(Phase.PROOF_OF_CONCEPT)

        # Assert
        assert isinstance(transition, PhaseTransition)
        assert transition.from_phase == Phase.EXPERIENCE
        assert transition.to_phase == Phase.PROOF_OF_CONCEPT
        assert transition.validation_passed is True
        assert transition.trigger == "auto"
        assert UUID(transition.transition_id)  # Valid UUID
        assert isinstance(transition.timestamp, datetime)

        # Config should be updated
        assert config.current_phase == "proof"

    def test_advance_with_validation_fail_raises_error(self):
        """Should raise PhaseValidationError when validation fails."""
        # Arrange
        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="experience"
        )
        manager = PhaseManager(config)

        manager._metrics = {
            "session_count": 10,  # Not enough sessions
            "win_rate": Decimal("0.50"),
            "avg_rr": Decimal("1.2")
        }

        # Act & Assert
        with pytest.raises(PhaseValidationError) as exc_info:
            manager.advance_phase(Phase.PROOF_OF_CONCEPT)

        # Check error details
        error = exc_info.value
        assert error.result.can_advance is False
        assert len(error.result.missing_requirements) > 0
        assert "Phase validation failed" in str(error)

    def test_advance_with_force_bypasses_validation(self):
        """Should bypass validation when force=True."""
        # Arrange
        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="experience"
        )
        manager = PhaseManager(config)

        # Bad metrics that would fail validation
        manager._metrics = {
            "session_count": 5,
            "win_rate": Decimal("0.40"),
            "avg_rr": Decimal("1.0")
        }

        # Act
        transition = manager.advance_phase(Phase.PROOF_OF_CONCEPT, force=True)

        # Assert
        assert transition.validation_passed is True  # Force passed
        assert transition.trigger == "manual"
        assert transition.override_password_used is True
        assert config.current_phase == "proof"

    def test_advance_phase_creates_transition_record(self):
        """Should create complete PhaseTransition record."""
        # Arrange
        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="proof"
        )
        manager = PhaseManager(config)

        manager._metrics = {
            "session_count": 30,
            "trade_count": 50,
            "win_rate": Decimal("0.65"),
            "avg_rr": Decimal("1.8")
        }

        # Act
        transition = manager.advance_phase(Phase.REAL_MONEY_TRIAL)

        # Assert - verify all transition fields
        assert transition.transition_id is not None
        assert transition.timestamp.tzinfo == timezone.utc
        assert transition.from_phase == Phase.PROOF_OF_CONCEPT
        assert transition.to_phase == Phase.REAL_MONEY_TRIAL
        assert transition.trigger == "auto"
        assert transition.validation_passed is True
        assert isinstance(transition.metrics_snapshot, dict)

    def test_advance_phase_non_sequential_fails(self):
        """Should fail for non-sequential phase advancement."""
        # Arrange
        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="experience"
        )
        manager = PhaseManager(config)

        # Act & Assert
        with pytest.raises(ValueError, match="Non-sequential transition"):
            manager.advance_phase(Phase.SCALING)


class TestPhaseValidationError:
    """Test PhaseValidationError exception."""

    def test_error_message_includes_missing_requirements(self):
        """Should format error message with missing requirements."""
        # Arrange
        result = ValidationResult(
            can_advance=False,
            criteria_met={
                "session_count": False,
                "win_rate": False,
                "avg_rr": True
            },
            missing_requirements=["session_count", "win_rate"],
            metrics_summary={}
        )

        # Act
        error = PhaseValidationError(result)

        # Assert
        assert "Phase validation failed" in str(error)
        assert "session_count" in str(error)
        assert "win_rate" in str(error)
        assert error.result == result
