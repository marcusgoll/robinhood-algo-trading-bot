"""Session health monitor unit tests."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from src.trading_bot.auth import AuthenticationError, RobinhoodAuth


def _build_auth_mock() -> MagicMock:
    """Create a RobinhoodAuth mock with base configuration."""
    auth_mock = MagicMock(spec=RobinhoodAuth)
    auth_mock.auth_config = MagicMock()
    auth_mock.auth_config.username = "operator@example.com"
    auth_mock.login.return_value = True
    return auth_mock


class NoopLogger:
    """Logger stub used where thread-safe no-op logging is sufficient."""

    def log_health_check_executed(self, *_, **__) -> None:
        return

    def log_health_check_passed(self, *_, **__) -> None:
        return

    def log_health_check_failed(self, *_, **__) -> None:
        return

    def log_reauth_triggered(self, *_, **__) -> None:
        return

    def log_reauth_success(self, *_, **__) -> None:
        return

    def log_reauth_failed(self, *_, **__) -> None:
        return

    def log_session_metrics_snapshot(self, *_, **__) -> None:
        return


@pytest.fixture
def auth_mock() -> MagicMock:
    return _build_auth_mock()


@pytest.fixture
def logger_mock() -> MagicMock:
    from src.trading_bot.health.health_logger import HealthCheckLogger

    return MagicMock(spec=HealthCheckLogger)


@pytest.fixture
def monitor(auth_mock: MagicMock, logger_mock: MagicMock):
    from src.trading_bot.health.session_health import SessionHealthMonitor

    return SessionHealthMonitor(auth=auth_mock, logger=logger_mock, cache_ttl_seconds=0.0)


def test_session_health_monitor_initialization(auth_mock: MagicMock, logger_mock: MagicMock) -> None:
    from src.trading_bot.health import SessionHealthMonitor, SessionHealthStatus

    monitor = SessionHealthMonitor(auth=auth_mock, logger=logger_mock)
    status = monitor.get_session_status()

    assert isinstance(status, SessionHealthStatus)
    assert status.is_healthy is False
    assert status.health_check_count == 0
    assert status.reauth_count == 0
    assert status.last_health_check is None

    with pytest.raises(TypeError):
        SessionHealthMonitor(auth=object())  # type: ignore[arg-type]


@patch("src.trading_bot.health.session_health.profiles.load_account_profile", return_value={"account": "123"})
def test_check_health_success_with_valid_session(load_profile: MagicMock, monitor, logger_mock: MagicMock) -> None:
    result = monitor.check_health(context="manual")

    assert result.success is True
    assert result.reauth_triggered is False
    assert result.latency_ms < 2000
    assert load_profile.call_count == 1

    status = monitor.get_session_status()
    assert status.is_healthy is True
    assert status.health_check_count == 1
    assert status.consecutive_failures == 0
    assert status.last_health_check is not None

    logger_mock.log_health_check_executed.assert_called_once()
    logger_mock.log_health_check_passed.assert_called_once()
    logger_mock.log_health_check_failed.assert_not_called()


@patch("src.trading_bot.health.session_health.profiles.load_account_profile")
def test_check_health_failure_triggers_reauth(load_profile: MagicMock, auth_mock: MagicMock, logger_mock: MagicMock) -> None:
    from src.trading_bot.health.session_health import SessionHealthMonitor

    load_profile.side_effect = [AuthenticationError("401"), {"account": "recovered"}]
    monitor = SessionHealthMonitor(auth=auth_mock, logger=logger_mock, cache_ttl_seconds=0.0)

    result = monitor.check_health(context="pre-trade")

    assert result.success is True
    assert result.reauth_triggered is True
    assert auth_mock.login.call_count == 1

    status = monitor.get_session_status()
    assert status.reauth_count == 1
    assert status.health_check_count == 1
    assert status.is_healthy is True

    logger_mock.log_reauth_triggered.assert_called_once()
    logger_mock.log_reauth_success.assert_called_once()


@patch("src.trading_bot.health.session_health.time.sleep")
@patch("src.trading_bot.health.session_health.profiles.load_account_profile")
def test_check_health_uses_retry(load_profile: MagicMock, sleep_mock: MagicMock, monitor) -> None:
    load_profile.side_effect = [TimeoutError("t1"), TimeoutError("t2"), {"account": "ok"}]

    result = monitor.check_health(context="periodic")

    assert result.success is True
    assert load_profile.call_count == 3
    assert sleep_mock.call_count == 2
    sleep_intervals = [sleep_call.args[0] for sleep_call in sleep_mock.call_args_list]
    assert pytest.approx(sleep_intervals[0], rel=0.1) == 1.0
    assert pytest.approx(sleep_intervals[1], rel=0.1) == 2.0


@patch("src.trading_bot.health.session_health.circuit_breaker")
@patch("src.trading_bot.health.session_health.profiles.load_account_profile")
def test_check_health_trips_circuit_breaker(load_profile: MagicMock, circuit_breaker_mock: MagicMock, auth_mock: MagicMock, logger_mock: MagicMock) -> None:
    from src.trading_bot.health.session_health import SessionHealthMonitor

    load_profile.side_effect = AuthenticationError("invalid session")
    auth_mock.login.side_effect = AuthenticationError("reauth failed")

    monitor = SessionHealthMonitor(auth=auth_mock, logger=logger_mock, cache_ttl_seconds=0.0)
    result = monitor.check_health()

    assert result.success is False
    assert result.reauth_triggered is True
    circuit_breaker_mock.record_failure.assert_called()

    status = monitor.get_session_status()
    assert status.is_healthy is False
    assert status.consecutive_failures >= 1

    logger_mock.log_reauth_failed.assert_called_once()


@patch("src.trading_bot.health.session_health.Timer")
def test_start_periodic_checks_schedules_timer(timer_cls: MagicMock, monitor) -> None:
    timer_instance = MagicMock()
    timer_cls.return_value = timer_instance

    monitor.start_periodic_checks()

    timer_cls.assert_called_once()
    args, _ = timer_cls.call_args
    assert pytest.approx(args[0], rel=0.01) == 300.0
    timer_instance.start.assert_called_once()


@patch("src.trading_bot.health.session_health.Timer")
def test_stop_periodic_checks_cancels_timer(timer_cls: MagicMock, monitor) -> None:
    timer_instance = MagicMock()
    timer_cls.return_value = timer_instance

    monitor.start_periodic_checks()
    monitor.stop_periodic_checks()

    timer_instance.cancel.assert_called_once()


@patch(
    "src.trading_bot.health.session_health.profiles.load_account_profile",
    side_effect=[AuthenticationError("401"), {"account": "ok"}, {"account": "ok"}],
)
def test_get_session_status_returns_metrics(load_profile: MagicMock, auth_mock: MagicMock, logger_mock: MagicMock) -> None:
    from src.trading_bot.health.session_health import SessionHealthMonitor

    monitor = SessionHealthMonitor(auth=auth_mock, logger=logger_mock, cache_ttl_seconds=0.0)
    monitor._status.session_start_time = datetime.now(UTC) - timedelta(seconds=42)  # type: ignore[attr-defined]

    monitor.check_health()
    monitor.check_health()
    monitor.check_health()

    status = monitor.get_session_status()
    assert status.health_check_count == 3
    assert status.reauth_count == 1
    assert status.session_uptime_seconds >= 42
    assert status.last_health_check is not None


@patch("src.trading_bot.health.session_health.profiles.load_account_profile", return_value={"account": "123"})
def test_health_check_logging_calls(load_profile: MagicMock, monitor, logger_mock: MagicMock) -> None:
    monitor.check_health(context="manual")

    logger_mock.log_health_check_executed.assert_called_once()
    assert logger_mock.log_health_check_executed.call_args.kwargs.get("context") == "manual"
    logger_mock.log_health_check_passed.assert_called_once()
    logger_mock.log_session_metrics_snapshot.assert_called_once()


@patch("src.trading_bot.health.session_health.profiles.load_account_profile", return_value={"account": "123"})
def test_health_check_caches_result(load_profile: MagicMock, auth_mock: MagicMock, logger_mock: MagicMock) -> None:
    from src.trading_bot.health.session_health import SessionHealthMonitor

    monitor = SessionHealthMonitor(auth=auth_mock, logger=logger_mock)

    first = monitor.check_health()
    second = monitor.check_health()
    assert second is first  # Cached result reuse

    assert monitor._last_result_monotonic is not None  # type: ignore[attr-defined]
    monitor._last_result_monotonic -= monitor._cache_ttl_seconds + 1  # type: ignore[attr-defined]

    third = monitor.check_health()

    assert load_profile.call_count >= 2
    assert third is not first  # Cache invalidated after TTL adjustment
    assert first.success and second.success and third.success


@patch("src.trading_bot.health.session_health.profiles.load_account_profile", return_value={"account": "123"})
def test_concurrent_health_checks_thread_safe(load_profile: MagicMock, auth_mock: MagicMock) -> None:
    from src.trading_bot.health.session_health import SessionHealthMonitor

    monitor = SessionHealthMonitor(auth=auth_mock, logger=NoopLogger(), cache_ttl_seconds=0.0)

    def _run(_: int) -> bool:
        return monitor.check_health(context="parallel").success

    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(_run, range(5)))

    assert all(results)
    assert load_profile.call_count == 5

    status = monitor.get_session_status()
    assert status.health_check_count == 5
    assert status.consecutive_failures == 0
