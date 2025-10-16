"""Unit tests for SessionHealthMonitor.

Tests cover:
- Initialization with validation (T005)
- Health check success (T006)
- Reauth on 401 failure (T007)
- @with_retry decorator usage (T008)
- Circuit breaker integration (T009)
- Periodic check scheduling (T010)
- Timer cancellation (T011)
- Session status metrics (T012)
- Health check logging (T013)
- Latency performance (T014)
- Result caching (T015)
- Thread safety (T016)
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pytest

from trading_bot.auth.robinhood_auth import RobinhoodAuth
from trading_bot.health.health_logger import HealthCheckLogger
from trading_bot.health.session_health import (
    HealthCheckResult,
    SessionHealthMonitor,
    SessionHealthStatus,
)


class TestSessionHealthMonitorInitialization:
    """Tests for SessionHealthMonitor initialization (T005)."""

    def test_session_health_monitor_initialization(self):
        """Test SessionHealthMonitor initializes with valid auth.

        From: spec.md FR-001
        Task: T005
        """
        # Arrange
        mock_auth = Mock(spec=RobinhoodAuth)

        # Act - This will fail because SessionHealthMonitor class doesn't exist yet
        monitor = SessionHealthMonitor(mock_auth)

        # Assert
        assert monitor is not None
        status = monitor.get_session_status()
        assert status.is_healthy is False
        assert status.health_check_count == 0
        assert status.reauth_count == 0

    def test_session_health_monitor_rejects_invalid_auth(self):
        """Test SessionHealthMonitor raises TypeError for non-RobinhoodAuth.

        From: spec.md FR-001
        Task: T005
        """
        # Arrange
        invalid_auth = "not_an_auth_object"

        # Act & Assert - Should raise TypeError
        with pytest.raises(TypeError, match="RobinhoodAuth"):
            SessionHealthMonitor(invalid_auth)


class TestHealthCheckSuccess:
    """Tests for successful health check execution (T006, T008, T014)."""

    @patch("robin_stocks.robinhood.profiles.load_account_profile")
    def test_check_health_success_with_valid_session(self, mock_load_profile):
        """Test check_health() succeeds with valid session.

        From: spec.md FR-001, FR-002, FR-011
        Task: T006
        """
        # Arrange
        mock_auth = Mock(spec=RobinhoodAuth)
        mock_load_profile.return_value = {"username": "test_user"}
        monitor = SessionHealthMonitor(mock_auth)

        # Act
        result = monitor.check_health()

        # Assert
        assert result.success is True
        assert result.latency_ms < 2000  # NFR-001 performance target
        assert result.reauth_triggered is False

        status = monitor.get_session_status()
        assert status.is_healthy is True
        assert status.health_check_count == 1
        assert status.consecutive_failures == 0
