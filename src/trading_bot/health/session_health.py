"""Session health monitoring service."""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from threading import Lock, Timer
from types import SimpleNamespace
from typing import Any, Optional

from trading_bot.auth import AuthenticationError, RobinhoodAuth
from trading_bot.error_handling import RetryPolicy, circuit_breaker, with_retry
from trading_bot.utils.security import mask_username

from .health_logger import HealthCheckLogger

try:
    from robin_stocks.robinhood import profiles
except ImportError:  # pragma: no cover - dependency missing in some environments
    profiles = SimpleNamespace()  # type: ignore[assignment]


@dataclass(frozen=True)
class HealthCheckResult:
    """Result of a single health check execution."""

    success: bool
    timestamp: datetime
    latency_ms: int
    error_message: str | None = None
    reauth_triggered: bool = False


@dataclass
class SessionHealthStatus:
    """Aggregated session health metrics."""

    is_healthy: bool
    session_start_time: datetime
    session_uptime_seconds: int
    last_health_check: datetime | None
    health_check_count: int
    reauth_count: int
    consecutive_failures: int


class _TransientHealthCheckError(Exception):
    """Internal sentinel exception used for retry logic."""


class SessionHealthMonitor:
    """
    Monitor responsible for keeping the Robinhood session alive.

    Periodically probes the account endpoint, triggers re-authentication on
    failure, and surfaces metrics for dashboards and operators.
    """

    def __init__(
        self,
        *,
        auth: RobinhoodAuth,
        logger: HealthCheckLogger | None = None,
        cache_ttl_seconds: float = 10.0,
        interval_seconds: float = 300.0,
    ) -> None:
        if not isinstance(auth, RobinhoodAuth):
            raise TypeError("auth must be an instance of RobinhoodAuth")

        self._auth = auth
        self._logger = logger or HealthCheckLogger()
        self._cache_ttl_seconds = max(cache_ttl_seconds, 0.0)
        self._interval_seconds = interval_seconds if interval_seconds > 0 else 300.0

        now = datetime.now(UTC)
        self._status = SessionHealthStatus(
            is_healthy=False,
            session_start_time=now,
            session_uptime_seconds=0,
            last_health_check=None,
            health_check_count=0,
            reauth_count=0,
            consecutive_failures=0,
        )

        self._timer: Timer | None = None
        self._lock = Lock()
        self._last_result: HealthCheckResult | None = None
        self._last_result_monotonic: float | None = None
        self._masked_username = mask_username(self._auth.auth_config.username)

        # Pre-construct retry policy for transient errors
        self._retry_policy = RetryPolicy(
            max_attempts=2,  # total attempts = 3
            base_delay=1.0,
            backoff_multiplier=2.0,
            jitter=False,
            retriable_exceptions=(_TransientHealthCheckError,),
        )

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def check_health(self, *, context: str = "periodic") -> HealthCheckResult:
        """
        Execute a health check, optionally using cached results when fresh.
        """
        cached = self._get_cached_result()
        if cached is not None:
            return cached

        start_perf = time.perf_counter()
        timestamp = datetime.now(UTC)

        try:
            self._perform_probe()
        except AuthenticationError as exc:
            return self._handle_authentication_failure(
                exc=exc,
                context=context,
                timestamp=timestamp,
                start_perf=start_perf,
            )
        except _TransientHealthCheckError as exc:
            root_exc = exc.__cause__ or exc
            return self._handle_failure(
                exc=root_exc,
                context=context,
                timestamp=timestamp,
                start_perf=start_perf,
                reauth_attempted=False,
            )

        return self._handle_success(
            context=context,
            timestamp=timestamp,
            start_perf=start_perf,
            reauth_triggered=False,
        )

    def start_periodic_checks(self) -> None:
        """Begin scheduling periodic health checks."""
        with self._lock:
            if self._timer is not None:
                return
            self._timer = Timer(self._interval_seconds, self._run_periodic_check)
            self._timer.daemon = True
            self._timer.start()

    def stop_periodic_checks(self) -> None:
        """Cancel any scheduled periodic health checks."""
        with self._lock:
            if self._timer is None:
                return
            self._timer.cancel()
            self._timer = None

    def get_session_status(self) -> SessionHealthStatus:
        """Return a snapshot of current session metrics."""
        with self._lock:
            status_copy = SessionHealthStatus(**asdict(self._status))

        uptime_seconds = int(
            max((datetime.now(UTC) - status_copy.session_start_time).total_seconds(), 0)
        )
        status_copy.session_uptime_seconds = uptime_seconds
        return status_copy

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _get_cached_result(self) -> HealthCheckResult | None:
        if self._cache_ttl_seconds == 0:
            return None

        with self._lock:
            if self._last_result is None or self._last_result_monotonic is None:
                return None

            age = time.monotonic() - self._last_result_monotonic
            if age < self._cache_ttl_seconds:
                return self._last_result

        return None

    def _perform_probe(self) -> dict[str, Any]:
        """Call Robinhood API with retry support."""

        def _call_profile() -> dict[str, Any]:
            if not hasattr(profiles, "load_account_profile"):
                raise AuthenticationError("robin_stocks library not available")
            return profiles.load_account_profile()

        def _call_profile_wrapped() -> dict[str, Any]:
            try:
                return _call_profile()
            except AuthenticationError:
                raise
            except Exception as exc:  # noqa: BLE001
                raise _TransientHealthCheckError(str(exc)) from exc

        wrapped = with_retry(policy=self._retry_policy)(_call_profile_wrapped)
        return wrapped()

    def _handle_success(
        self,
        *,
        context: str,
        timestamp: datetime,
        start_perf: float,
        reauth_triggered: bool,
    ) -> HealthCheckResult:
        latency_ms = int((time.perf_counter() - start_perf) * 1000)
        result = HealthCheckResult(
            success=True,
            timestamp=timestamp,
            latency_ms=latency_ms,
            error_message=None,
            reauth_triggered=reauth_triggered,
        )

        with self._lock:
            self._status.is_healthy = True
            self._status.health_check_count += 1
            self._status.consecutive_failures = 0
            self._status.last_health_check = timestamp
            if reauth_triggered:
                self._status.reauth_count += 1

            self._last_result = result
            self._last_result_monotonic = time.monotonic()
            status_snapshot = SessionHealthStatus(**asdict(self._status))

        self._logger.log_health_check_executed(result=result, context=context)
        self._logger.log_health_check_passed(status=status_snapshot)
        self._logger.log_session_metrics_snapshot(status=status_snapshot)
        return result

    def _handle_failure(
        self,
        *,
        exc: Exception,
        context: str,
        timestamp: datetime,
        start_perf: float,
        reauth_attempted: bool,
    ) -> HealthCheckResult:
        latency_ms = int((time.perf_counter() - start_perf) * 1000)
        result = HealthCheckResult(
            success=False,
            timestamp=timestamp,
            latency_ms=latency_ms,
            error_message=str(exc),
            reauth_triggered=reauth_attempted,
        )

        with self._lock:
            self._status.is_healthy = False
            self._status.health_check_count += 1
            self._status.consecutive_failures += 1
            self._status.last_health_check = timestamp

            self._last_result = result
            self._last_result_monotonic = time.monotonic()
            status_snapshot = SessionHealthStatus(**asdict(self._status))

        self._logger.log_health_check_executed(result=result, context=context)
        self._logger.log_health_check_failed(result=result)
        self._logger.log_session_metrics_snapshot(status=status_snapshot)
        circuit_breaker.record_failure()
        return result

    def _handle_authentication_failure(
        self,
        *,
        exc: AuthenticationError,
        context: str,
        timestamp: datetime,
        start_perf: float,
    ) -> HealthCheckResult:
        self._logger.log_reauth_triggered(session_identifier=self._masked_username)

        try:
            self._auth.login()
        except AuthenticationError as reauth_exc:
            self._logger.log_reauth_failed(error=str(reauth_exc))
            return self._handle_failure(
                exc=reauth_exc,
                context=context,
                timestamp=timestamp,
                start_perf=start_perf,
                reauth_attempted=True,
            )

        reauth_latency_ms = int((time.perf_counter() - start_perf) * 1000)
        self._logger.log_reauth_success(duration_ms=reauth_latency_ms)

        try:
            self._perform_probe()
        except AuthenticationError as reauth_second_exc:
            self._logger.log_reauth_failed(error=str(reauth_second_exc))
            return self._handle_failure(
                exc=reauth_second_exc,
                context=context,
                timestamp=timestamp,
                start_perf=start_perf,
                reauth_attempted=True,
            )
        except _TransientHealthCheckError as transient_exc:
            root_exc = transient_exc.__cause__ or transient_exc
            return self._handle_failure(
                exc=root_exc,
                context=context,
                timestamp=timestamp,
                start_perf=start_perf,
                reauth_attempted=True,
            )

        return self._handle_success(
            context=context,
            timestamp=timestamp,
            start_perf=start_perf,
            reauth_triggered=True,
        )

    def _run_periodic_check(self) -> None:
        try:
            self.check_health(context="periodic")
        finally:
            with self._lock:
                if self._timer is None:
                    return
                self._timer = Timer(self._interval_seconds, self._run_periodic_check)
                self._timer.daemon = True
                self._timer.start()
