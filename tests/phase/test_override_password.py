"""Tests for override password verification (FR-007, NFR-003).

Critical Issue #1: Missing override password implementation.
"""
import os
import pytest
from decimal import Decimal
from datetime import date, datetime, timezone

from trading_bot.phase.models import Phase, PhaseOverrideError
from trading_bot.phase.manager import PhaseManager
from trading_bot.config import Config


class TestPhaseOverridePassword:
    """Test override password verification."""

    def test_advance_phase_with_force_requires_password(self, phase_manager, monkeypatch):
        """Force advancement must require override password."""
        # Set override password in environment
        monkeypatch.setenv("PHASE_OVERRIDE_PASSWORD", "secure123")

        # Attempt force advancement without password should fail
        with pytest.raises(PhaseOverrideError, match="Override password required"):
            phase_manager.advance_phase(Phase.PROOF_OF_CONCEPT, force=True)

    def test_advance_phase_with_correct_password_succeeds(self, phase_manager, monkeypatch):
        """Force advancement with correct password should succeed."""
        # Set override password in environment
        monkeypatch.setenv("PHASE_OVERRIDE_PASSWORD", "secure123")

        # Force advancement with correct password should succeed
        transition = phase_manager.advance_phase(
            Phase.PROOF_OF_CONCEPT,
            force=True,
            override_password="secure123"
        )

        assert transition.to_phase == Phase.PROOF_OF_CONCEPT
        assert transition.validation_passed is False  # Force bypassed validation

    def test_advance_phase_with_incorrect_password_fails(self, phase_manager, monkeypatch):
        """Force advancement with incorrect password should fail."""
        # Set override password in environment
        monkeypatch.setenv("PHASE_OVERRIDE_PASSWORD", "secure123")

        # Attempt force advancement with wrong password
        with pytest.raises(PhaseOverrideError, match="Invalid override password"):
            phase_manager.advance_phase(
                Phase.PROOF_OF_CONCEPT,
                force=True,
                override_password="wrongpassword"
            )

    def test_advance_phase_without_env_password_configured_fails(self, phase_manager, monkeypatch):
        """Force advancement when PHASE_OVERRIDE_PASSWORD not set should fail."""
        # Remove env var
        monkeypatch.delenv("PHASE_OVERRIDE_PASSWORD", raising=False)

        # Attempt force advancement
        with pytest.raises(PhaseOverrideError, match="Override password not configured"):
            phase_manager.advance_phase(
                Phase.PROOF_OF_CONCEPT,
                force=True,
                override_password="anypassword"
            )

    def test_normal_advancement_does_not_require_password(self, phase_manager_with_metrics):
        """Normal advancement (force=False) should not require password."""
        # Normal advancement with criteria met should work without password
        manager = phase_manager_with_metrics

        transition = manager.advance_phase(Phase.PROOF_OF_CONCEPT, force=False)

        assert transition.to_phase == Phase.PROOF_OF_CONCEPT
        assert transition.validation_passed is True

    def test_override_attempt_logged_on_success(
        self, phase_manager, tmp_path, monkeypatch
    ):
        """Successful override should be logged to phase-overrides.jsonl."""
        import json

        # Set override password
        monkeypatch.setenv("PHASE_OVERRIDE_PASSWORD", "secure123")

        # Configure history logger to write to temp directory
        override_log = tmp_path / "phase-overrides.jsonl"
        phase_manager.history_logger.override_log = override_log

        # Force advancement with correct password
        phase_manager.advance_phase(
            Phase.PROOF_OF_CONCEPT,
            force=True,
            override_password="secure123"
        )

        # Verify override logged
        assert override_log.exists()

        with open(override_log, 'r') as f:
            record = json.loads(f.readline())

        assert record["action"] == "force_advance"
        assert record["blocked"] is False
        assert "proof" in record["reason"]  # to_phase included in reason

    def test_override_attempt_logged_on_failure(
        self, phase_manager, tmp_path, monkeypatch
    ):
        """Failed override should be logged to phase-overrides.jsonl."""
        import json

        # Set override password
        monkeypatch.setenv("PHASE_OVERRIDE_PASSWORD", "secure123")

        # Configure history logger to write to temp directory
        override_log = tmp_path / "phase-overrides.jsonl"
        phase_manager.history_logger.override_log = override_log

        # Attempt force advancement with wrong password
        with pytest.raises(PhaseOverrideError):
            phase_manager.advance_phase(
                Phase.PROOF_OF_CONCEPT,
                force=True,
                override_password="wrongpassword"
            )

        # Verify failed attempt logged
        assert override_log.exists()

        with open(override_log, 'r') as f:
            record = json.loads(f.readline())

        assert record["action"] == "force_advance"
        assert record["blocked"] is True
        assert "Invalid override password" in record["reason"]

    def test_override_password_never_logged(
        self, phase_manager, tmp_path, monkeypatch
    ):
        """Override password should NEVER appear in logs (security)."""
        import json

        # Set override password
        monkeypatch.setenv("PHASE_OVERRIDE_PASSWORD", "secure123")

        # Configure history logger
        override_log = tmp_path / "phase-overrides.jsonl"
        phase_manager.history_logger.override_log = override_log

        # Force advancement
        phase_manager.advance_phase(
            Phase.PROOF_OF_CONCEPT,
            force=True,
            override_password="secure123"
        )

        # Read log file and verify password not present
        with open(override_log, 'r') as f:
            log_contents = f.read()

        assert "secure123" not in log_contents
        assert "override_password" not in log_contents

    def test_empty_password_rejected(self, phase_manager, monkeypatch):
        """Empty override password should be rejected."""
        monkeypatch.setenv("PHASE_OVERRIDE_PASSWORD", "secure123")

        with pytest.raises(PhaseOverrideError, match="Invalid override password"):
            phase_manager.advance_phase(
                Phase.PROOF_OF_CONCEPT,
                force=True,
                override_password=""
            )

    def test_none_password_rejected(self, phase_manager, monkeypatch):
        """None override password should be rejected."""
        monkeypatch.setenv("PHASE_OVERRIDE_PASSWORD", "secure123")

        with pytest.raises(PhaseOverrideError, match="Override password required"):
            phase_manager.advance_phase(
                Phase.PROOF_OF_CONCEPT,
                force=True,
                override_password=None
            )

    def test_override_preserves_metrics_snapshot(
        self, phase_manager, monkeypatch
    ):
        """Override should still capture metrics snapshot for audit."""
        monkeypatch.setenv("PHASE_OVERRIDE_PASSWORD", "secure123")

        transition = phase_manager.advance_phase(
            Phase.PROOF_OF_CONCEPT,
            force=True,
            override_password="secure123"
        )

        # Even though validation was bypassed, metrics snapshot should be captured
        assert transition.metrics_snapshot is not None
        assert isinstance(transition.metrics_snapshot, dict)


@pytest.fixture
def phase_manager(tmp_path):
    """Create PhaseManager for testing."""
    from trading_bot.phase.history_logger import HistoryLogger

    # Create config with experience phase
    config = Config(
        robinhood_username="test",
        robinhood_password="test",
        current_phase="experience"
    )

    # Create history logger with temp directory
    logger = HistoryLogger(log_dir=tmp_path)

    # Create manager
    manager = PhaseManager(config=config)
    manager.history_logger = logger

    return manager


@pytest.fixture
def phase_manager_with_metrics(tmp_path, mocker):
    """Create PhaseManager with mocked metrics that meet criteria."""
    from trading_bot.phase.history_logger import HistoryLogger
    from trading_bot.phase.validators import ValidationResult

    # Create config
    config = Config(
        robinhood_username="test",
        robinhood_password="test",
        current_phase="experience"
    )

    # Create history logger
    logger = HistoryLogger(log_dir=tmp_path)

    # Create manager
    manager = PhaseManager(config=config)
    manager.history_logger = logger

    # Mock validate_transition to return success
    mock_result = ValidationResult(
        can_advance=True,
        criteria_met={"session_count": True, "win_rate": True, "avg_rr": True},
        missing_requirements=[],
        metrics_summary={"session_count": 25, "win_rate": "0.65", "avg_rr": "1.8"}
    )
    mocker.patch.object(manager, 'validate_transition', return_value=mock_result)

    return manager
