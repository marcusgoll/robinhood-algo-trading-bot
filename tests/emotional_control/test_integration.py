"""
Integration Tests for Emotional Control with RiskManager

Tests: T029 - End-to-end integration with position sizing

Constitution v1.0.0:
- §Testing_Requirements: Integration tests verify cross-component behavior
"""

import pytest
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock

from src.trading_bot.emotional_control.tracker import EmotionalControl
from src.trading_bot.emotional_control.config import EmotionalControlConfig


class TestRiskManagerIntegration:
    """Integration tests with RiskManager (T029)."""

    def test_position_multiplier_applied_to_risk_manager_calculation(self, tmp_path):
        """Test emotional control multiplier reduces position size in RiskManager (AC-015)."""
        # Given: Emotional control in ACTIVE state
        config = EmotionalControlConfig.default()
        tracker = EmotionalControl(config, state_file=tmp_path / "state.json", log_dir=tmp_path)

        # Trigger activation
        tracker.update_state(Decimal("-3000"), Decimal("100000"), is_win=False)
        assert tracker._state.is_active is True

        # When: Getting multiplier for position sizing
        multiplier = tracker.get_position_multiplier()

        # Then: Multiplier is 0.25 (25% reduction)
        assert multiplier == Decimal("0.25")

        # Simulate RiskManager applying multiplier
        base_position_size = 100  # shares
        reduced_size = int(Decimal(base_position_size) * multiplier)
        assert reduced_size == 25  # 25% of 100

    def test_full_workflow_activation_to_recovery(self, tmp_path):
        """Test complete workflow: activation → position reduction → recovery."""
        # Given: Emotional control starting INACTIVE
        config = EmotionalControlConfig.default()
        tracker = EmotionalControl(config, state_file=tmp_path / "state.json", log_dir=tmp_path)

        # Phase 1: Activation (3% loss)
        tracker.update_state(Decimal("-3000"), Decimal("100000"), is_win=False)
        assert tracker._state.is_active is True
        assert tracker.get_position_multiplier() == Decimal("0.25")

        # Phase 2: Position sizing reduced (simulated)
        base_size = 100
        active_size = int(Decimal(base_size) * tracker.get_position_multiplier())
        assert active_size == 25

        # Phase 3: Recovery (3 consecutive wins)
        tracker.update_state(Decimal("500"), Decimal("97000"), is_win=True)
        tracker.update_state(Decimal("500"), Decimal("97500"), is_win=True)
        tracker.update_state(Decimal("500"), Decimal("98000"), is_win=True)

        # Phase 4: Position sizing restored
        assert tracker._state.is_active is False
        assert tracker.get_position_multiplier() == Decimal("1.00")
        restored_size = int(Decimal(base_size) * tracker.get_position_multiplier())
        assert restored_size == 100
