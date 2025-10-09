"""
Unit tests for startup sequence components.

Tests:
- StartupStep dataclass
- StartupOrchestrator initialization
- Individual startup steps
"""

import pytest
from src.trading_bot.startup import StartupStep


class TestStartupStep:
    """Tests for StartupStep dataclass."""

    def test_startup_step_dataclass(self):
        """Test StartupStep dataclass tracks step status."""
        # Given: Create StartupStep with name, status
        step = StartupStep(
            name="Loading config",
            status="running"
        )

        # When: Access attributes
        # Then: Assert all attributes correct
        assert step.name == "Loading config"
        assert step.status == "running"
        assert step.error_message is None
        assert step.duration_seconds == 0.0

        # Test with error
        step_failed = StartupStep(
            name="Validation",
            status="failed",
            error_message="Missing credentials",
            duration_seconds=1.5
        )
        assert step_failed.status == "failed"
        assert step_failed.error_message == "Missing credentials"
        assert step_failed.duration_seconds == 1.5
