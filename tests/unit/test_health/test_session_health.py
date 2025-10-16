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
from unittest.mock import Mock, patch, MagicMock, call

import pytest

from trading_bot.auth.robinhood_auth import RobinhoodAuth
from trading_bot.error_handling.exceptions import RetriableError
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

        # Act
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

    @patch("robin_stocks.robinhood.profiles.load_account_profile")
    def test_health_check_latency_under_target(self, mock_load_profile):
        """Test health check latency meets performance targets.

        From: spec.md NFR-001
        Task: T014
        """
        # Arrange
        mock_auth = Mock(spec=RobinhoodAuth)

        # Simulate realistic API delay (100ms)
        def delayed_response():
            time.sleep(0.1)
            return {"username": "test_user"}

        mock_load_profile.side_effect = delayed_response
        monitor = SessionHealthMonitor(mock_auth)

        # Act
        result = monitor.check_health()

        # Assert
        assert result.success is True
        assert result.latency_ms < 2000  # P95 target from NFR-001
        assert result.latency_ms >= 100  # At least the simulated delay


class TestHealthCheckReauth:
    """Tests for reauth triggering (T007)."""

    @patch("robin_stocks.robinhood.profiles.load_account_profile")
    def test_check_health_failure_triggers_reauth(self, mock_load_profile):
        """Test check_health() fails with 401 and triggers reauth.

        From: spec.md FR-003
        Task: T007
        """
        # Arrange
        mock_auth = Mock(spec=RobinhoodAuth)

        # First call raises 401, second call (after reauth) succeeds
        mock_load_profile.side_effect = [
            Exception("401 Unauthorized"),
            {"username": "test_user"},
        ]

        # Mock login to succeed
        mock_auth.login.return_value = True

        monitor = SessionHealthMonitor(mock_auth)

        # Act
        result = monitor.check_health()

        # Assert
        assert result.success is True  # Success after reauth
        assert result.reauth_triggered is True

        # Verify login was called once
        mock_auth.login.assert_called_once()

        status = monitor.get_session_status()
        assert status.reauth_count == 1


class TestHealthCheckRetry:
    """Tests for @with_retry decorator (T008)."""

    @patch("robin_stocks.robinhood.profiles.load_account_profile")
    def test_check_health_uses_retry_decorator(self, mock_load_profile):
        """Test check_health() uses @with_retry decorator.

        From: spec.md FR-004, plan.md [RESEARCH DECISIONS]
        Task: T008
        """
        # Arrange
        mock_auth = Mock(spec=RobinhoodAuth)

        # First 2 calls raise retriable network error, third succeeds
        mock_load_profile.side_effect = [
            RetriableError("Network timeout"),
            RetriableError("Network timeout"),
            {"username": "test_user"},
        ]

        monitor = SessionHealthMonitor(mock_auth)

        # Clear cache to ensure fresh check
        monitor._last_check_time = 0.0

        # Act
        result = monitor.check_health()

        # Assert
        assert result.success is True  # Success after retries
        # Verify load_account_profile was called 3 times (2 failures + 1 success)
        assert mock_load_profile.call_count == 3


class TestCircuitBreakerIntegration:
    """Tests for circuit breaker integration (T009)."""

    @patch("robin_stocks.robinhood.profiles.load_account_profile")
    @patch("trading_bot.health.session_health.circuit_breaker")
    def test_check_health_trips_circuit_breaker_on_persistent_failure(
        self, mock_circuit_breaker, mock_load_profile
    ):
        """Test check_health() trips circuit breaker after retry exhaustion.

        From: spec.md FR-005, NFR-008
        Task: T009
        """
        # Arrange
        mock_auth = Mock(spec=RobinhoodAuth)

        # All calls fail
        mock_load_profile.side_effect = Exception("Network error")

        # Reauth also fails
        mock_auth.login.side_effect = Exception("Auth failed")

        monitor = SessionHealthMonitor(mock_auth)

        # Act
        result = monitor.check_health()

        # Assert
        assert result.success is False

        # Verify circuit breaker recorded failures
        assert mock_circuit_breaker.record_failure.called

        status = monitor.get_session_status()
        assert status.consecutive_failures >= 1


class TestPeriodicChecks:
    """Tests for periodic health check scheduling (T010, T011)."""

    @patch("threading.Timer")
    def test_start_periodic_checks_schedules_timer(self, mock_timer_class):
        """Test start_periodic_checks() schedules timer every 5 minutes.

        From: spec.md FR-006, plan.md [RESEARCH DECISIONS]
        Task: T010
        """
        # Arrange
        mock_auth = Mock(spec=RobinhoodAuth)
        mock_timer = Mock()
        mock_timer_class.return_value = mock_timer

        monitor = SessionHealthMonitor(mock_auth)

        # Act
        monitor.start_periodic_checks()

        # Assert
        # Verify Timer created with 300 second interval (5 minutes)
        mock_timer_class.assert_called_once()
        args, kwargs = mock_timer_class.call_args
        assert args[0] == 300.0  # 5 minutes

        # Verify timer was started
        mock_timer.start.assert_called_once()

    @patch("threading.Timer")
    def test_stop_periodic_checks_cancels_timer(self, mock_timer_class):
        """Test stop_periodic_checks() cancels running timer.

        From: spec.md edge case handling
        Task: T011
        """
        # Arrange
        mock_auth = Mock(spec=RobinhoodAuth)
        mock_timer = Mock()
        mock_timer_class.return_value = mock_timer

        monitor = SessionHealthMonitor(mock_auth)

        # Start periodic checks first
        monitor.start_periodic_checks()

        # Act
        monitor.stop_periodic_checks()

        # Assert
        # Verify timer was cancelled
        mock_timer.cancel.assert_called_once()


class TestSessionStatus:
    """Tests for session status metrics (T012)."""

    @patch("robin_stocks.robinhood.profiles.load_account_profile")
    def test_get_session_status_returns_metrics(self, mock_load_profile):
        """Test get_session_status() returns current metrics.

        From: spec.md FR-008, FR-010
        Task: T012
        """
        # Arrange
        mock_auth = Mock(spec=RobinhoodAuth)

        # Setup for one failure with reauth
        mock_load_profile.side_effect = [
            {"username": "test_user"},  # First check succeeds
            {"username": "test_user"},  # Second check succeeds
            Exception("401 Unauthorized"),  # Third check fails
            {"username": "test_user"},  # Fourth check after reauth
        ]

        mock_auth.login.return_value = True

        monitor = SessionHealthMonitor(mock_auth)

        # Act - Run 3 health checks (2 success, 1 failure with reauth)
        # Clear cache before each check to avoid caching
        monitor._last_check_time = 0.0
        monitor.check_health()

        time.sleep(0.1)  # Small delay to ensure different timestamps
        monitor._last_check_time = 0.0
        monitor.check_health()

        time.sleep(0.1)
        monitor._last_check_time = 0.0
        monitor.check_health()  # This one triggers reauth

        status = monitor.get_session_status()

        # Assert
        assert status.health_check_count == 3
        assert status.reauth_count == 1
        assert status.session_uptime_seconds >= 0
        assert status.last_health_check is not None


class TestHealthCheckLogging:
    """Tests for health check logging (T013)."""

    @patch("robin_stocks.robinhood.profiles.load_account_profile")
    @patch.object(HealthCheckLogger, "log_health_check_executed")
    @patch.object(HealthCheckLogger, "log_health_check_passed")
    def test_health_check_logs_events(
        self, mock_log_passed, mock_log_executed, mock_load_profile
    ):
        """Test health check logs all events to HealthCheckLogger.

        From: spec.md FR-009, NFR-005, NFR-006
        Task: T013
        """
        # Arrange
        mock_auth = Mock(spec=RobinhoodAuth)
        mock_load_profile.return_value = {"username": "test_user"}

        monitor = SessionHealthMonitor(mock_auth)

        # Act
        result = monitor.check_health()

        # Assert
        # Verify log methods were called
        mock_log_executed.assert_called_once()
        mock_log_passed.assert_called_once()

        # Verify log_health_check_executed was called with HealthCheckResult
        args, kwargs = mock_log_executed.call_args
        assert isinstance(args[0], HealthCheckResult)


class TestResultCaching:
    """Tests for health check result caching (T015)."""

    @patch("robin_stocks.robinhood.profiles.load_account_profile")
    def test_health_check_caches_result(self, mock_load_profile):
        """Test health check caches result for 10 seconds.

        From: plan.md [PERFORMANCE TARGETS]
        Task: T015
        """
        # Arrange
        mock_auth = Mock(spec=RobinhoodAuth)
        mock_load_profile.return_value = {"username": "test_user"}

        monitor = SessionHealthMonitor(mock_auth)

        # Act - First call hits API
        result1 = monitor.check_health()

        # Second call within 10 seconds should return cached result
        result2 = monitor.check_health()

        # Assert
        # Verify load_account_profile was only called once (first call)
        assert mock_load_profile.call_count == 1

        # Both results should be the same object (cached)
        assert result1 is result2

        # Act - Wait for cache to expire and call again
        time.sleep(10.1)
        result3 = monitor.check_health()

        # Assert - Should have called API again after cache expiry
        assert mock_load_profile.call_count == 2


class TestThreadSafety:
    """Tests for thread safety (T016)."""

    @patch("robin_stocks.robinhood.profiles.load_account_profile")
    def test_concurrent_health_checks_thread_safe(self, mock_load_profile):
        """Test thread safety for concurrent health checks.

        From: plan.md [SCHEMA] (threading.Lock usage)
        Task: T016
        """
        # Arrange
        mock_auth = Mock(spec=RobinhoodAuth)
        mock_load_profile.return_value = {"username": "test_user"}

        monitor = SessionHealthMonitor(mock_auth)

        # Act - Start 5 concurrent threads calling check_health()
        with ThreadPoolExecutor(max_workers=5) as executor:
            # Clear cache to ensure all threads execute
            monitor._last_check_time = 0.0

            futures = [executor.submit(monitor.check_health) for _ in range(5)]
            results = [f.result() for f in futures]

        # Assert
        # All threads should complete successfully
        assert all(r.success for r in results)

        status = monitor.get_session_status()

        # health_check_count should be accurate (no race condition)
        # May be less than 5 due to caching, but should be consistent
        assert status.health_check_count >= 1


class TestNetworkTimeout:
    """Tests for network timeout handling (T033)."""

    @patch("robin_stocks.robinhood.profiles.load_account_profile")
    @patch("trading_bot.health.session_health.circuit_breaker")
    def test_health_check_handles_network_timeout(
        self, mock_circuit_breaker, mock_load_profile
    ):
        """Test health check handles network timeouts gracefully.

        From: spec.md FR-012, edge cases
        Task: T033
        """
        # Arrange
        mock_auth = Mock(spec=RobinhoodAuth)

        # Simulate network timeout for all attempts
        mock_load_profile.side_effect = Exception("Network timeout")

        monitor = SessionHealthMonitor(mock_auth)

        # Act
        result = monitor.check_health()

        # Assert
        assert result.success is False
        assert result.error_message is not None

        # Verify circuit breaker was notified
        assert mock_circuit_breaker.record_failure.called
