"""Session health monitoring for Robinhood trading bot.

This module provides the core SessionHealthMonitor service that proactively
checks API session health every 5 minutes and triggers automatic reauth when needed.

Usage:
    from trading_bot.health import SessionHealthMonitor
    from trading_bot.auth import RobinhoodAuth

    auth = RobinhoodAuth(config)
    health_monitor = SessionHealthMonitor(auth)

    # Start periodic health checks (every 5 minutes)
    health_monitor.start_periodic_checks()

    # Check health before critical operations
    result = health_monitor.check_health(context="pre_trade")
    if not result.success:
        logger.error("Health check failed, aborting trade")
        return

    # Get current session metrics
    status = health_monitor.get_session_status()
    print(f"Session uptime: {status.session_uptime_seconds}s")
    print(f"Health checks: {status.health_check_count}")
    print(f"Reauth count: {status.reauth_count}")

    # Stop periodic checks on shutdown
    health_monitor.stop_periodic_checks()
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, replace
from datetime import UTC, datetime

import robin_stocks.robinhood.profiles  # type: ignore[import-untyped]

from trading_bot.auth.robinhood_auth import RobinhoodAuth
from trading_bot.error_handling.circuit_breaker import circuit_breaker
from trading_bot.error_handling.retry import with_retry
from trading_bot.health.health_logger import HealthCheckLogger

__all__ = ["SessionHealthStatus", "HealthCheckResult", "SessionHealthMonitor"]

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SessionHealthStatus:
    """Current health status of the trading session.

    Tracks session metrics including uptime, health check execution,
    and reauth activity.

    Attributes:
        is_healthy: Whether the session is currently healthy
        session_start_time: When the session started
        session_uptime_seconds: Total session uptime in seconds
        last_health_check: Timestamp of the last health check
        health_check_count: Total number of health checks executed
        reauth_count: Number of times reauth was triggered
        consecutive_failures: Number of consecutive health check failures
    """

    is_healthy: bool
    session_start_time: datetime
    session_uptime_seconds: int
    last_health_check: datetime
    health_check_count: int
    reauth_count: int
    consecutive_failures: int


@dataclass(frozen=True)
class HealthCheckResult:
    """Result of a single health check execution.

    Records the outcome, timing, and context of a health check attempt.

    Attributes:
        success: Whether the health check passed
        timestamp: When the health check was executed
        latency_ms: Time taken to execute the health check
        error_message: Error message if health check failed (None if success)
        reauth_triggered: Whether automatic reauth was triggered
    """

    success: bool
    timestamp: datetime
    latency_ms: int
    error_message: str | None
    reauth_triggered: bool


class SessionHealthMonitor:
    """Session health monitor for Robinhood trading bot.

    Proactively monitors API session health and triggers automatic reauth
    when authentication failures are detected.

    Features:
    - Periodic health checks every 5 minutes
    - 10-second result caching
    - Automatic reauth on 401/403 errors
    - Thread-safe state management
    - Circuit breaker integration
    - Structured JSONL logging

    Attributes:
        _auth: RobinhoodAuth instance for authentication
        _status: Current session health status
        _timer: Threading timer for periodic checks
        _lock: Lock for thread-safe state mutations
        _logger: HealthCheckLogger for structured logging
        _last_result: Cached health check result
        _last_check_time: Timestamp of last check for caching
    """

    def __init__(self, auth: RobinhoodAuth) -> None:
        """Initialize SessionHealthMonitor.

        Args:
            auth: RobinhoodAuth instance for session management

        Raises:
            TypeError: If auth is not a RobinhoodAuth instance
        """
        # Validate auth parameter
        if not isinstance(auth, RobinhoodAuth):
            raise TypeError("auth must be a RobinhoodAuth instance")

        self._auth = auth

        # Initialize status with defaults
        now = datetime.now(UTC)
        self._status = SessionHealthStatus(
            is_healthy=False,
            session_start_time=now,
            session_uptime_seconds=0,
            last_health_check=now,
            health_check_count=0,
            reauth_count=0,
            consecutive_failures=0,
        )

        # Threading components
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()

        # Logger
        self._logger = HealthCheckLogger()

        # Caching
        self._last_result: HealthCheckResult | None = None
        self._last_check_time: float = 0.0

    def check_health(self, context: str = "periodic") -> HealthCheckResult:
        """Execute health check by probing API.

        Checks session validity by calling a lightweight Robinhood API endpoint.
        Automatically triggers reauth if session is invalid (401/403).
        Results are cached for 10 seconds to reduce API load.

        Args:
            context: Context of health check (e.g., "periodic", "pre_trade")

        Returns:
            HealthCheckResult with check outcome and metrics
        """
        # Check cache (10 second window)
        now = time.time()
        if self._last_result and (now - self._last_check_time) < 10.0:
            return self._last_result

        # Start timing
        start_time = time.time()

        # Probe API with retry logic
        try:
            self._probe_api()
            end_time = time.time()
            latency_ms = int((end_time - start_time) * 1000)

            # Create success result
            result = HealthCheckResult(
                success=True,
                timestamp=datetime.now(UTC),
                latency_ms=latency_ms,
                error_message=None,
                reauth_triggered=False,
            )

            # Update status
            with self._lock:
                self._status = replace(
                    self._status,
                    is_healthy=True,
                    last_health_check=datetime.now(UTC),
                    health_check_count=self._status.health_check_count + 1,
                    consecutive_failures=0,
                )

            # Log success
            self._logger.log_health_check_executed(result, context)
            self._logger.log_health_check_passed(self._status)

            # Cache result
            self._last_result = result
            self._last_check_time = now

            return result

        except Exception as e:
            # Check if auth error (401/403)
            is_auth_error = (
                "401" in str(e) or
                "403" in str(e) or
                "authentication" in str(e).lower() or
                "unauthorized" in str(e).lower()
            )

            if is_auth_error:
                # Attempt reauth
                reauth_success = self._attempt_reauth()

                end_time = time.time()
                latency_ms = int((end_time - start_time) * 1000)

                if reauth_success:
                    # Reauth succeeded, return success
                    result = HealthCheckResult(
                        success=True,
                        timestamp=datetime.now(UTC),
                        latency_ms=latency_ms,
                        error_message=None,
                        reauth_triggered=True,
                    )

                    with self._lock:
                        self._status = replace(
                            self._status,
                            is_healthy=True,
                            last_health_check=datetime.now(UTC),
                            health_check_count=self._status.health_check_count + 1,
                            consecutive_failures=0,
                            reauth_count=self._status.reauth_count + 1,
                        )

                    self._logger.log_health_check_executed(result, context)
                    self._logger.log_health_check_passed(self._status)

                    # Cache result
                    self._last_result = result
                    self._last_check_time = now

                    return result

            # Health check failed
            end_time = time.time()
            latency_ms = int((end_time - start_time) * 1000)

            result = HealthCheckResult(
                success=False,
                timestamp=datetime.now(UTC),
                latency_ms=latency_ms,
                error_message=str(e),
                reauth_triggered=is_auth_error,
            )

            # Update status
            with self._lock:
                self._status = replace(
                    self._status,
                    is_healthy=False,
                    last_health_check=datetime.now(UTC),
                    health_check_count=self._status.health_check_count + 1,
                    consecutive_failures=self._status.consecutive_failures + 1,
                )

            # Log failure
            self._logger.log_health_check_executed(result, context)
            self._logger.log_health_check_failed(result)

            # Record circuit breaker failure
            circuit_breaker.record_failure()

            # Cache result
            self._last_result = result
            self._last_check_time = now

            return result

    @with_retry()
    def _probe_api(self) -> bool:
        """Probe API to check session health.

        Makes a lightweight API call to verify session is valid.
        Decorated with @with_retry for automatic retry with exponential backoff.

        Returns:
            True if API call succeeds

        Raises:
            Exception: If API call fails after retries
        """
        # Use lightweight profile API call
        result = robin_stocks.robinhood.profiles.load_account_profile()

        # Verify we got a valid response
        if not result:
            raise Exception("API returned empty response")

        return True

    def _attempt_reauth(self) -> bool:
        """Attempt to reauth after health check failure.

        Returns:
            True if reauth succeeded, False otherwise
        """
        try:
            # Log reauth triggered
            session_id = str(int(time.time()))
            self._logger.log_reauth_triggered(session_id)

            # Time the reauth
            start_time = time.time()

            # Attempt login
            self._auth.login()

            end_time = time.time()
            duration_ms = int((end_time - start_time) * 1000)

            # Log success
            self._logger.log_reauth_success(duration_ms)

            return True

        except Exception as e:
            # Log failure
            self._logger.log_reauth_failed(str(e))
            return False

    def start_periodic_checks(self) -> None:
        """Start periodic health checks every 5 minutes (300 seconds).

        Schedules a self-repeating timer that calls check_health()
        periodically. Thread-safe.
        """
        with self._lock:
            # Cancel existing timer if any
            if self._timer is not None:
                self._timer.cancel()

            # Create and start new timer
            self._timer = threading.Timer(300.0, self._run_periodic_check)
            self._timer.start()

    def _run_periodic_check(self) -> None:
        """Internal method to run periodic check and reschedule.

        Called by timer. Executes health check and schedules next check.
        """
        # Run health check
        self.check_health(context="periodic")

        # Schedule next check (self-repeating)
        with self._lock:
            self._timer = threading.Timer(300.0, self._run_periodic_check)
            self._timer.start()

    def stop_periodic_checks(self) -> None:
        """Stop periodic health checks.

        Cancels the running timer safely. Thread-safe.
        """
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None

    def get_session_status(self) -> SessionHealthStatus:
        """Get current session health status.

        Returns a copy of the current status with updated uptime.

        Returns:
            SessionHealthStatus with current metrics
        """
        with self._lock:
            # Calculate current uptime
            now = datetime.now(UTC)
            uptime_seconds = int((now - self._status.session_start_time).total_seconds())

            # Return updated copy
            return replace(
                self._status,
                session_uptime_seconds=uptime_seconds,
            )
