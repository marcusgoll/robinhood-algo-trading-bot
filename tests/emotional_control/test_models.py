"""
Unit Tests for Emotional Control Models

Tests: T021, T022 - EmotionalControlState and EmotionalControlEvent validation

Constitution v1.0.0:
- §Testing_Requirements: ≥90% coverage, TDD workflow
- §Code_Quality: One behavior per test, descriptive names
"""

import pytest
from decimal import Decimal
from src.trading_bot.emotional_control.models import (
    EmotionalControlState,
    EmotionalControlEvent,
)


class TestEmotionalControlState:
    """Unit tests for EmotionalControlState model (T021)."""

    def test_inactive_state_default_values(self):
        """Test INACTIVE state with default field values."""
        # Given: INACTIVE state with no activation context
        state = EmotionalControlState(
            is_active=False,
            activated_at=None,
            trigger_reason=None,
            account_balance_at_activation=None,
            loss_amount=None,
            consecutive_losses=0,
            consecutive_wins=0,
            last_updated="2025-10-22T10:00:00Z",
        )

        # Then: State is inactive with zero counters
        assert state.is_active is False
        assert state.activated_at is None
        assert state.trigger_reason is None
        assert state.consecutive_losses == 0
        assert state.consecutive_wins == 0

    def test_active_state_with_single_loss_trigger(self):
        """Test ACTIVE state triggered by single large loss."""
        # Given: ACTIVE state triggered by 3.5% loss
        state = EmotionalControlState(
            is_active=True,
            activated_at="2025-10-22T14:30:00Z",
            trigger_reason="SINGLE_LOSS",
            account_balance_at_activation=Decimal("100000"),
            loss_amount=Decimal("3500"),
            consecutive_losses=1,
            consecutive_wins=0,
            last_updated="2025-10-22T14:30:00Z",
        )

        # Then: State is active with single loss trigger
        assert state.is_active is True
        assert state.trigger_reason == "SINGLE_LOSS"
        assert state.loss_amount == Decimal("3500")
        assert state.consecutive_losses == 1

    def test_active_state_with_streak_loss_trigger(self):
        """Test ACTIVE state triggered by consecutive loss streak."""
        # Given: ACTIVE state triggered by 3 consecutive losses
        state = EmotionalControlState(
            is_active=True,
            activated_at="2025-10-22T14:30:00Z",
            trigger_reason="STREAK_LOSS",
            account_balance_at_activation=Decimal("100000"),
            loss_amount=None,
            consecutive_losses=3,
            consecutive_wins=0,
            last_updated="2025-10-22T14:30:00Z",
        )

        # Then: State is active with streak loss trigger
        assert state.is_active is True
        assert state.trigger_reason == "STREAK_LOSS"
        assert state.consecutive_losses == 3
        assert state.loss_amount is None

    def test_validation_fails_for_negative_consecutive_losses(self):
        """Test validation rejects negative consecutive loss count."""
        # Given: State with invalid negative consecutive_losses
        # When: Creating state with consecutive_losses < 0
        # Then: ValueError raised
        with pytest.raises(ValueError, match="Consecutive losses must be >= 0"):
            EmotionalControlState(
                is_active=False,
                activated_at=None,
                trigger_reason=None,
                account_balance_at_activation=None,
                loss_amount=None,
                consecutive_losses=-1,  # INVALID
                consecutive_wins=0,
                last_updated="2025-10-22T10:00:00Z",
            )

    def test_validation_fails_for_negative_consecutive_wins(self):
        """Test validation rejects negative consecutive win count."""
        # Given: State with invalid negative consecutive_wins
        # When: Creating state with consecutive_wins < 0
        # Then: ValueError raised
        with pytest.raises(ValueError, match="Consecutive wins must be >= 0"):
            EmotionalControlState(
                is_active=False,
                activated_at=None,
                trigger_reason=None,
                account_balance_at_activation=None,
                loss_amount=None,
                consecutive_losses=0,
                consecutive_wins=-1,  # INVALID
                last_updated="2025-10-22T10:00:00Z",
            )

    def test_validation_fails_for_active_state_without_activated_at(self):
        """Test validation requires activated_at for ACTIVE state."""
        # Given: ACTIVE state missing activation timestamp
        # When: Creating active state without activated_at
        # Then: ValueError raised
        with pytest.raises(ValueError, match="Active state must have activated_at"):
            EmotionalControlState(
                is_active=True,
                activated_at=None,  # INVALID for active state
                trigger_reason="SINGLE_LOSS",
                account_balance_at_activation=Decimal("100000"),
                loss_amount=Decimal("3000"),
                consecutive_losses=1,
                consecutive_wins=0,
                last_updated="2025-10-22T10:00:00Z",
            )

    def test_validation_fails_for_active_state_without_trigger_reason(self):
        """Test validation requires trigger_reason for ACTIVE state."""
        # Given: ACTIVE state missing trigger reason
        # When: Creating active state without trigger_reason
        # Then: ValueError raised
        with pytest.raises(ValueError, match="Active state must have trigger_reason"):
            EmotionalControlState(
                is_active=True,
                activated_at="2025-10-22T14:30:00Z",
                trigger_reason=None,  # INVALID for active state
                account_balance_at_activation=Decimal("100000"),
                loss_amount=Decimal("3000"),
                consecutive_losses=1,
                consecutive_wins=0,
                last_updated="2025-10-22T10:00:00Z",
            )

    def test_validation_fails_for_invalid_trigger_reason(self):
        """Test validation rejects invalid trigger_reason values."""
        # Given: ACTIVE state with invalid trigger reason
        # When: Creating active state with trigger_reason not in allowed list
        # Then: ValueError raised
        with pytest.raises(ValueError, match="Invalid trigger_reason"):
            EmotionalControlState(
                is_active=True,
                activated_at="2025-10-22T14:30:00Z",
                trigger_reason="INVALID_REASON",  # INVALID
                account_balance_at_activation=Decimal("100000"),
                loss_amount=Decimal("3000"),
                consecutive_losses=1,
                consecutive_wins=0,
                last_updated="2025-10-22T10:00:00Z",
            )


class TestEmotionalControlEvent:
    """Unit tests for EmotionalControlEvent model (T022)."""

    def test_activation_event_with_single_loss(self):
        """Test ACTIVATION event for single large loss."""
        # Given: Activation event triggered by 3.5% loss
        event = EmotionalControlEvent(
            event_id="550e8400-e29b-41d4-a716-446655440000",
            timestamp="2025-10-22T14:30:00Z",
            event_type="ACTIVATION",
            trigger_reason="SINGLE_LOSS",
            account_balance=Decimal("100000"),
            loss_amount=Decimal("3500"),
            consecutive_losses=1,
            consecutive_wins=0,
            admin_id=None,
            reset_reason=None,
            position_size_multiplier=Decimal("0.25"),
        )

        # Then: Event has activation fields populated
        assert event.event_type == "ACTIVATION"
        assert event.trigger_reason == "SINGLE_LOSS"
        assert event.loss_amount == Decimal("3500")
        assert event.position_size_multiplier == Decimal("0.25")

    def test_recovery_event_with_profitable_streak(self):
        """Test RECOVERY event for profitable trading recovery."""
        # Given: Recovery event after 3 consecutive wins
        event = EmotionalControlEvent(
            event_id="550e8400-e29b-41d4-a716-446655440001",
            timestamp="2025-10-23T10:00:00Z",
            event_type="RECOVERY",
            trigger_reason="PROFITABLE_RECOVERY",
            account_balance=Decimal("102000"),
            loss_amount=None,
            consecutive_losses=0,
            consecutive_wins=3,
            admin_id=None,
            reset_reason=None,
            position_size_multiplier=Decimal("1.00"),
        )

        # Then: Event has recovery fields populated
        assert event.event_type == "RECOVERY"
        assert event.trigger_reason == "PROFITABLE_RECOVERY"
        assert event.consecutive_wins == 3
        assert event.position_size_multiplier == Decimal("1.00")

    def test_manual_reset_event_with_admin_context(self):
        """Test MANUAL_RESET event with admin audit trail."""
        # Given: Manual reset by admin with justification
        event = EmotionalControlEvent(
            event_id="550e8400-e29b-41d4-a716-446655440002",
            timestamp="2025-10-23T15:00:00Z",
            event_type="MANUAL_RESET",
            trigger_reason="MANUAL_RESET",
            account_balance=Decimal("101000"),
            loss_amount=None,
            consecutive_losses=1,
            consecutive_wins=0,
            admin_id="trader1",
            reset_reason="Strategy change - new system deployed",
            position_size_multiplier=Decimal("1.00"),
        )

        # Then: Event has admin context populated
        assert event.event_type == "MANUAL_RESET"
        assert event.admin_id == "trader1"
        assert event.reset_reason == "Strategy change - new system deployed"
        assert event.position_size_multiplier == Decimal("1.00")

    def test_factory_method_creates_event_with_auto_generated_id(self):
        """Test create() factory generates UUID and timestamp."""
        # Given: Factory invocation with required fields
        # When: Creating event via factory method
        event = EmotionalControlEvent.create(
            event_type="ACTIVATION",
            trigger_reason="SINGLE_LOSS",
            account_balance=Decimal("100000"),
            consecutive_losses=1,
            consecutive_wins=0,
            position_size_multiplier=Decimal("0.25"),
            loss_amount=Decimal("3000"),
        )

        # Then: Event has auto-generated ID and timestamp
        assert event.event_id is not None
        assert len(event.event_id) > 0  # UUID string
        assert event.timestamp is not None
        assert "T" in event.timestamp  # ISO 8601 format
        assert event.event_type == "ACTIVATION"

    def test_validation_fails_for_invalid_event_type(self):
        """Test validation rejects invalid event_type values."""
        # Given: Event with invalid event_type
        # When: Creating event with event_type not in allowed list
        # Then: ValueError raised
        with pytest.raises(ValueError, match="Invalid event_type"):
            EmotionalControlEvent(
                event_id="550e8400-e29b-41d4-a716-446655440000",
                timestamp="2025-10-22T14:30:00Z",
                event_type="INVALID_TYPE",  # INVALID
                trigger_reason="SINGLE_LOSS",
                account_balance=Decimal("100000"),
                loss_amount=Decimal("3000"),
                consecutive_losses=1,
                consecutive_wins=0,
                admin_id=None,
                reset_reason=None,
                position_size_multiplier=Decimal("0.25"),
            )

    def test_validation_fails_for_manual_reset_without_admin_id(self):
        """Test validation requires admin_id for MANUAL_RESET events."""
        # Given: MANUAL_RESET event missing admin_id
        # When: Creating manual reset event without admin_id
        # Then: ValueError raised
        with pytest.raises(ValueError, match="MANUAL_RESET event must have admin_id"):
            EmotionalControlEvent(
                event_id="550e8400-e29b-41d4-a716-446655440000",
                timestamp="2025-10-22T14:30:00Z",
                event_type="MANUAL_RESET",
                trigger_reason="MANUAL_RESET",
                account_balance=Decimal("100000"),
                loss_amount=None,
                consecutive_losses=0,
                consecutive_wins=0,
                admin_id=None,  # INVALID for MANUAL_RESET
                reset_reason="Test reset",
                position_size_multiplier=Decimal("1.00"),
            )

    def test_validation_fails_for_manual_reset_without_reason(self):
        """Test validation requires reset_reason for MANUAL_RESET events."""
        # Given: MANUAL_RESET event missing reset_reason
        # When: Creating manual reset event without reset_reason
        # Then: ValueError raised
        with pytest.raises(ValueError, match="MANUAL_RESET event must have reset_reason"):
            EmotionalControlEvent(
                event_id="550e8400-e29b-41d4-a716-446655440000",
                timestamp="2025-10-22T14:30:00Z",
                event_type="MANUAL_RESET",
                trigger_reason="MANUAL_RESET",
                account_balance=Decimal("100000"),
                loss_amount=None,
                consecutive_losses=0,
                consecutive_wins=0,
                admin_id="trader1",
                reset_reason=None,  # INVALID for MANUAL_RESET
                position_size_multiplier=Decimal("1.00"),
            )

    def test_validation_fails_for_invalid_position_multiplier(self):
        """Test validation rejects invalid position_size_multiplier values."""
        # Given: Event with invalid position multiplier
        # When: Creating event with multiplier not in [0.25, 1.00]
        # Then: ValueError raised
        with pytest.raises(ValueError, match="Invalid position_size_multiplier"):
            EmotionalControlEvent(
                event_id="550e8400-e29b-41d4-a716-446655440000",
                timestamp="2025-10-22T14:30:00Z",
                event_type="ACTIVATION",
                trigger_reason="SINGLE_LOSS",
                account_balance=Decimal("100000"),
                loss_amount=Decimal("3000"),
                consecutive_losses=1,
                consecutive_wins=0,
                admin_id=None,
                reset_reason=None,
                position_size_multiplier=Decimal("0.50"),  # INVALID (must be 0.25 or 1.00)
            )

    def test_validation_fails_for_negative_consecutive_losses(self):
        """Test validation rejects negative consecutive_losses."""
        # Given: Event with negative consecutive_losses
        # When: Creating event with consecutive_losses < 0
        # Then: ValueError raised
        with pytest.raises(ValueError, match="Consecutive losses must be >= 0"):
            EmotionalControlEvent(
                event_id="550e8400-e29b-41d4-a716-446655440000",
                timestamp="2025-10-22T14:30:00Z",
                event_type="ACTIVATION",
                trigger_reason="SINGLE_LOSS",
                account_balance=Decimal("100000"),
                loss_amount=Decimal("3000"),
                consecutive_losses=-1,  # INVALID
                consecutive_wins=0,
                admin_id=None,
                reset_reason=None,
                position_size_multiplier=Decimal("0.25"),
            )

    def test_validation_fails_for_negative_consecutive_wins(self):
        """Test validation rejects negative consecutive_wins."""
        # Given: Event with negative consecutive_wins
        # When: Creating event with consecutive_wins < 0
        # Then: ValueError raised
        with pytest.raises(ValueError, match="Consecutive wins must be >= 0"):
            EmotionalControlEvent(
                event_id="550e8400-e29b-41d4-a716-446655440000",
                timestamp="2025-10-22T14:30:00Z",
                event_type="RECOVERY",
                trigger_reason="PROFITABLE_RECOVERY",
                account_balance=Decimal("102000"),
                loss_amount=None,
                consecutive_losses=0,
                consecutive_wins=-1,  # INVALID
                admin_id=None,
                reset_reason=None,
                position_size_multiplier=Decimal("1.00"),
            )
