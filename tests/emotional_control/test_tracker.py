"""
Unit Tests for Emotional Control Tracker

Tests: T024-T028 - Core tracker logic, state persistence, triggers, multipliers

Constitution v1.0.0:
- §Testing_Requirements: ≥90% coverage, TDD workflow
- §Code_Quality: One behavior per test, descriptive names
"""

import json
import pytest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch, mock_open
from datetime import datetime, timezone

from src.trading_bot.emotional_control.tracker import EmotionalControl
from src.trading_bot.emotional_control.config import EmotionalControlConfig
from src.trading_bot.emotional_control.models import EmotionalControlState


class TestLoadStateFailSafe:
    """Unit tests for _load_state method with fail-safe recovery (T024)."""

    def test_load_state_creates_fresh_inactive_state_when_file_missing(self, tmp_path):
        """Test _load_state returns INACTIVE state when state file doesn't exist."""
        # Given: State file does not exist
        config = EmotionalControlConfig.default()
        state_file = tmp_path / "state.json"
        assert not state_file.exists()

        # When: Creating tracker (loads state)
        tracker = EmotionalControl(config, state_file=state_file, log_dir=tmp_path)

        # Then: State is INACTIVE (fresh start)
        assert tracker._state.is_active is False
        assert tracker._state.consecutive_losses == 0
        assert tracker._state.consecutive_wins == 0

    def test_load_state_returns_active_state_when_corruption_detected(self, tmp_path):
        """Test _load_state defaults to ACTIVE (fail-safe) when JSON corrupted."""
        # Given: State file with corrupted JSON
        config = EmotionalControlConfig.default()
        state_file = tmp_path / "state.json"
        state_file.write_text("{invalid json syntax}", encoding="utf-8")

        # When: Creating tracker (attempts to load corrupted state)
        tracker = EmotionalControl(config, state_file=state_file, log_dir=tmp_path)

        # Then: State is ACTIVE (fail-safe default per spec.md FR-013)
        assert tracker._state.is_active is True
        assert tracker._state.trigger_reason == "STREAK_LOSS"  # Fail-safe trigger

    def test_load_state_returns_active_state_when_required_fields_missing(self, tmp_path):
        """Test _load_state defaults to ACTIVE when JSON missing required fields."""
        # Given: State file with incomplete JSON (missing fields)
        config = EmotionalControlConfig.default()
        state_file = tmp_path / "state.json"
        incomplete_state = {"is_active": False}  # Missing required fields
        state_file.write_text(json.dumps(incomplete_state), encoding="utf-8")

        # When: Creating tracker (attempts to load incomplete state)
        tracker = EmotionalControl(config, state_file=state_file, log_dir=tmp_path)

        # Then: State is ACTIVE (fail-safe default)
        assert tracker._state.is_active is True
        assert tracker._state.trigger_reason == "STREAK_LOSS"  # Fail-safe trigger

    def test_load_state_successfully_loads_valid_inactive_state(self, tmp_path):
        """Test _load_state loads valid INACTIVE state from file."""
        # Given: State file with valid INACTIVE state
        config = EmotionalControlConfig.default()
        state_file = tmp_path / "state.json"
        valid_state = {
            "is_active": False,
            "activated_at": None,
            "trigger_reason": None,
            "account_balance_at_activation": None,
            "loss_amount": None,
            "consecutive_losses": 2,
            "consecutive_wins": 1,
            "last_updated": "2025-10-22T10:00:00Z",
        }
        state_file.write_text(json.dumps(valid_state), encoding="utf-8")

        # When: Creating tracker (loads valid state)
        tracker = EmotionalControl(config, state_file=state_file, log_dir=tmp_path)

        # Then: State loaded correctly
        assert tracker._state.is_active is False
        assert tracker._state.consecutive_losses == 2
        assert tracker._state.consecutive_wins == 1

    def test_load_state_successfully_loads_valid_active_state(self, tmp_path):
        """Test _load_state loads valid ACTIVE state from file."""
        # Given: State file with valid ACTIVE state
        config = EmotionalControlConfig.default()
        state_file = tmp_path / "state.json"
        valid_state = {
            "is_active": True,
            "activated_at": "2025-10-22T14:30:00Z",
            "trigger_reason": "SINGLE_LOSS",
            "account_balance_at_activation": "100000.00",
            "loss_amount": "3500.00",
            "consecutive_losses": 1,
            "consecutive_wins": 0,
            "last_updated": "2025-10-22T14:30:00Z",
        }
        state_file.write_text(json.dumps(valid_state), encoding="utf-8")

        # When: Creating tracker (loads valid state)
        tracker = EmotionalControl(config, state_file=state_file, log_dir=tmp_path)

        # Then: State loaded correctly
        assert tracker._state.is_active is True
        assert tracker._state.trigger_reason == "SINGLE_LOSS"
        assert tracker._state.loss_amount == Decimal("3500.00")
        assert tracker._state.consecutive_losses == 1


class TestPersistStateAtomicWrites:
    """Unit tests for _persist_state method with atomic writes (T025)."""

    def test_persist_state_writes_inactive_state_to_file(self, tmp_path):
        """Test _persist_state writes INACTIVE state to JSON file."""
        # Given: Tracker with INACTIVE state
        config = EmotionalControlConfig.default()
        state_file = tmp_path / "state.json"
        tracker = EmotionalControl(config, state_file=state_file, log_dir=tmp_path)
        tracker._state.consecutive_losses = 2

        # When: Persisting state
        tracker._persist_state()

        # Then: State file created with correct data
        assert state_file.exists()
        with open(state_file, "r", encoding="utf-8") as f:
            saved_state = json.load(f)
        assert saved_state["is_active"] is False
        assert saved_state["consecutive_losses"] == 2

    def test_persist_state_writes_active_state_to_file(self, tmp_path):
        """Test _persist_state writes ACTIVE state with all fields."""
        # Given: Tracker with ACTIVE state
        config = EmotionalControlConfig.default()
        state_file = tmp_path / "state.json"
        tracker = EmotionalControl(config, state_file=state_file, log_dir=tmp_path)

        # Manually activate state
        tracker._state = EmotionalControlState(
            is_active=True,
            activated_at="2025-10-22T14:30:00Z",
            trigger_reason="SINGLE_LOSS",
            account_balance_at_activation=Decimal("100000"),
            loss_amount=Decimal("3500"),
            consecutive_losses=1,
            consecutive_wins=0,
            last_updated="2025-10-22T14:30:00Z",
        )

        # When: Persisting state
        tracker._persist_state()

        # Then: State file has ACTIVE state with all fields
        with open(state_file, "r", encoding="utf-8") as f:
            saved_state = json.load(f)
        assert saved_state["is_active"] is True
        assert saved_state["trigger_reason"] == "SINGLE_LOSS"
        assert saved_state["loss_amount"] == "3500"

    def test_persist_state_uses_atomic_write_pattern(self, tmp_path):
        """Test _persist_state uses temp file + rename for atomic writes."""
        # Given: Tracker ready to persist
        config = EmotionalControlConfig.default()
        state_file = tmp_path / "state.json"
        tracker = EmotionalControl(config, state_file=state_file, log_dir=tmp_path)

        # When: Persisting state
        tracker._persist_state()

        # Then: Temp file should not exist (renamed to final file)
        temp_file = tmp_path / "state.json.tmp"
        assert not temp_file.exists()
        assert state_file.exists()

    def test_persist_state_overwrites_existing_file(self, tmp_path):
        """Test _persist_state overwrites existing state file with new data."""
        # Given: Existing state file with old data
        config = EmotionalControlConfig.default()
        state_file = tmp_path / "state.json"
        state_file.write_text('{"is_active": true}', encoding="utf-8")

        tracker = EmotionalControl(config, state_file=state_file, log_dir=tmp_path)
        tracker._state.consecutive_wins = 3

        # When: Persisting new state
        tracker._persist_state()

        # Then: File overwritten with new state
        with open(state_file, "r", encoding="utf-8") as f:
            saved_state = json.load(f)
        assert saved_state["consecutive_wins"] == 3


class TestActivationTriggers:
    """Unit tests for activation trigger detection (T026)."""

    def test_single_loss_at_3_percent_activates_emotional_control(self, tmp_path):
        """Test single loss ≥3% triggers ACTIVE state (AC-001)."""
        # Given: Tracker in INACTIVE state
        config = EmotionalControlConfig.default()
        tracker = EmotionalControl(config, state_file=tmp_path / "state.json", log_dir=tmp_path)
        assert tracker._state.is_active is False

        # When: Trade with 3% loss ($3,000 loss on $100,000 account)
        tracker.update_state(
            trade_pnl=Decimal("-3000"),
            account_balance=Decimal("100000"),
            is_win=False,
        )

        # Then: Emotional control activated
        assert tracker._state.is_active is True
        assert tracker._state.trigger_reason == "SINGLE_LOSS"
        assert tracker._state.consecutive_losses == 1

    def test_single_loss_at_3_5_percent_activates_emotional_control(self, tmp_path):
        """Test single loss >3% triggers ACTIVE state."""
        # Given: Tracker in INACTIVE state
        config = EmotionalControlConfig.default()
        tracker = EmotionalControl(config, state_file=tmp_path / "state.json", log_dir=tmp_path)

        # When: Trade with 3.5% loss
        tracker.update_state(
            trade_pnl=Decimal("-3500"),
            account_balance=Decimal("100000"),
            is_win=False,
        )

        # Then: Emotional control activated
        assert tracker._state.is_active is True
        assert tracker._state.trigger_reason == "SINGLE_LOSS"

    def test_single_loss_under_3_percent_does_not_activate(self, tmp_path):
        """Test single loss <3% does not trigger activation (AC-002)."""
        # Given: Tracker in INACTIVE state
        config = EmotionalControlConfig.default()
        tracker = EmotionalControl(config, state_file=tmp_path / "state.json", log_dir=tmp_path)

        # When: Trade with 2.9% loss (below threshold)
        tracker.update_state(
            trade_pnl=Decimal("-2900"),
            account_balance=Decimal("100000"),
            is_win=False,
        )

        # Then: Emotional control remains INACTIVE
        assert tracker._state.is_active is False
        assert tracker._state.consecutive_losses == 1  # Loss counted but not activated

    def test_three_consecutive_losses_activates_emotional_control(self, tmp_path):
        """Test 3 consecutive losses trigger ACTIVE state (AC-003)."""
        # Given: Tracker in INACTIVE state
        config = EmotionalControlConfig.default()
        tracker = EmotionalControl(config, state_file=tmp_path / "state.json", log_dir=tmp_path)

        # When: 3 consecutive small losses (each <3%)
        tracker.update_state(Decimal("-1000"), Decimal("100000"), is_win=False)
        tracker.update_state(Decimal("-1000"), Decimal("99000"), is_win=False)
        tracker.update_state(Decimal("-1000"), Decimal("98000"), is_win=False)

        # Then: Emotional control activated after 3rd loss
        assert tracker._state.is_active is True
        assert tracker._state.trigger_reason == "STREAK_LOSS"
        assert tracker._state.consecutive_losses == 3

    def test_two_consecutive_losses_does_not_activate(self, tmp_path):
        """Test 2 consecutive losses do not trigger activation (AC-004)."""
        # Given: Tracker in INACTIVE state
        config = EmotionalControlConfig.default()
        tracker = EmotionalControl(config, state_file=tmp_path / "state.json", log_dir=tmp_path)

        # When: Only 2 consecutive losses
        tracker.update_state(Decimal("-1000"), Decimal("100000"), is_win=False)
        tracker.update_state(Decimal("-1000"), Decimal("99000"), is_win=False)

        # Then: Emotional control remains INACTIVE
        assert tracker._state.is_active is False
        assert tracker._state.consecutive_losses == 2

    def test_win_resets_consecutive_loss_counter(self, tmp_path):
        """Test winning trade resets consecutive loss counter."""
        # Given: Tracker with 2 consecutive losses
        config = EmotionalControlConfig.default()
        tracker = EmotionalControl(config, state_file=tmp_path / "state.json", log_dir=tmp_path)
        tracker.update_state(Decimal("-1000"), Decimal("100000"), is_win=False)
        tracker.update_state(Decimal("-1000"), Decimal("99000"), is_win=False)
        assert tracker._state.consecutive_losses == 2

        # When: Winning trade
        tracker.update_state(Decimal("500"), Decimal("98000"), is_win=True)

        # Then: Consecutive loss counter reset to 0
        assert tracker._state.consecutive_losses == 0
        assert tracker._state.consecutive_wins == 1


class TestRecoveryTriggers:
    """Unit tests for recovery trigger detection (T027)."""

    def test_three_consecutive_wins_deactivates_emotional_control(self, tmp_path):
        """Test 3 consecutive wins trigger recovery to INACTIVE (AC-008)."""
        # Given: Tracker in ACTIVE state
        config = EmotionalControlConfig.default()
        tracker = EmotionalControl(config, state_file=tmp_path / "state.json", log_dir=tmp_path)

        # Activate emotional control
        tracker.update_state(Decimal("-3000"), Decimal("100000"), is_win=False)
        assert tracker._state.is_active is True

        # When: 3 consecutive wins
        tracker.update_state(Decimal("500"), Decimal("97000"), is_win=True)
        tracker.update_state(Decimal("500"), Decimal("97500"), is_win=True)
        tracker.update_state(Decimal("500"), Decimal("98000"), is_win=True)

        # Then: Emotional control deactivated
        assert tracker._state.is_active is False
        assert tracker._state.consecutive_wins == 3

    def test_two_consecutive_wins_does_not_deactivate(self, tmp_path):
        """Test 2 consecutive wins do not trigger recovery (AC-009)."""
        # Given: Tracker in ACTIVE state
        config = EmotionalControlConfig.default()
        tracker = EmotionalControl(config, state_file=tmp_path / "state.json", log_dir=tmp_path)
        tracker.update_state(Decimal("-3000"), Decimal("100000"), is_win=False)

        # When: Only 2 consecutive wins
        tracker.update_state(Decimal("500"), Decimal("97000"), is_win=True)
        tracker.update_state(Decimal("500"), Decimal("97500"), is_win=True)

        # Then: Emotional control remains ACTIVE
        assert tracker._state.is_active is True
        assert tracker._state.consecutive_wins == 2

    def test_loss_resets_consecutive_win_counter(self, tmp_path):
        """Test losing trade resets consecutive win counter."""
        # Given: Tracker in ACTIVE state with 2 consecutive wins
        config = EmotionalControlConfig.default()
        tracker = EmotionalControl(config, state_file=tmp_path / "state.json", log_dir=tmp_path)
        tracker.update_state(Decimal("-3000"), Decimal("100000"), is_win=False)
        tracker.update_state(Decimal("500"), Decimal("97000"), is_win=True)
        tracker.update_state(Decimal("500"), Decimal("97500"), is_win=True)
        assert tracker._state.consecutive_wins == 2

        # When: Losing trade
        tracker.update_state(Decimal("-200"), Decimal("98000"), is_win=False)

        # Then: Consecutive win counter reset to 0
        assert tracker._state.consecutive_wins == 0
        assert tracker._state.consecutive_losses == 1

    def test_manual_reset_deactivates_emotional_control(self, tmp_path):
        """Test manual reset triggers recovery to INACTIVE (AC-010)."""
        # Given: Tracker in ACTIVE state
        config = EmotionalControlConfig.default()
        tracker = EmotionalControl(config, state_file=tmp_path / "state.json", log_dir=tmp_path)
        tracker.update_state(Decimal("-3000"), Decimal("100000"), is_win=False)
        assert tracker._state.is_active is True

        # When: Manual reset by admin
        tracker.reset_manual(admin_id="trader1", reset_reason="Strategy change", confirm=True)

        # Then: Emotional control deactivated
        assert tracker._state.is_active is False

    def test_manual_reset_requires_confirmation(self, tmp_path):
        """Test manual reset raises error if confirm=False (AC-011)."""
        # Given: Tracker in ACTIVE state
        config = EmotionalControlConfig.default()
        tracker = EmotionalControl(config, state_file=tmp_path / "state.json", log_dir=tmp_path)
        tracker.update_state(Decimal("-3000"), Decimal("100000"), is_win=False)

        # When: Manual reset without confirmation
        # Then: ValueError raised
        with pytest.raises(ValueError, match="Manual reset requires confirm=True"):
            tracker.reset_manual(admin_id="trader1", reset_reason="Test", confirm=False)


class TestPositionMultiplier:
    """Unit tests for position multiplier logic (T028)."""

    def test_get_position_multiplier_returns_0_25_when_active(self, tmp_path):
        """Test get_position_multiplier returns 0.25 when ACTIVE (AC-005)."""
        # Given: Tracker in ACTIVE state
        config = EmotionalControlConfig.default()
        tracker = EmotionalControl(config, state_file=tmp_path / "state.json", log_dir=tmp_path)
        tracker.update_state(Decimal("-3000"), Decimal("100000"), is_win=False)
        assert tracker._state.is_active is True

        # When: Getting position multiplier
        multiplier = tracker.get_position_multiplier()

        # Then: Returns 0.25 (25% of normal size)
        assert multiplier == Decimal("0.25")

    def test_get_position_multiplier_returns_1_00_when_inactive(self, tmp_path):
        """Test get_position_multiplier returns 1.00 when INACTIVE (AC-006)."""
        # Given: Tracker in INACTIVE state
        config = EmotionalControlConfig.default()
        tracker = EmotionalControl(config, state_file=tmp_path / "state.json", log_dir=tmp_path)
        assert tracker._state.is_active is False

        # When: Getting position multiplier
        multiplier = tracker.get_position_multiplier()

        # Then: Returns 1.00 (100% normal size)
        assert multiplier == Decimal("1.00")

    def test_get_position_multiplier_returns_decimal_type(self, tmp_path):
        """Test get_position_multiplier always returns Decimal (not float)."""
        # Given: Tracker in any state
        config = EmotionalControlConfig.default()
        tracker = EmotionalControl(config, state_file=tmp_path / "state.json", log_dir=tmp_path)

        # When: Getting position multiplier
        multiplier = tracker.get_position_multiplier()

        # Then: Type is Decimal (financial precision)
        assert isinstance(multiplier, Decimal)
