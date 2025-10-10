"""Structured logging utilities for session health monitoring."""

from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - type checking only
    from .session_health import HealthCheckResult, SessionHealthStatus


class HealthCheckLogger:
    """
    Append-only JSONL logger for health check events.

    Events are written to ``logs/health/health-checks.jsonl`` so operators can
    audit session activity, re-authentication attempts, and performance
    characteristics over time.
    """

    def __init__(self, log_dir: Path | None = None) -> None:
        self._log_dir = log_dir or Path("logs/health")
        self._log_path = self._log_dir / "health-checks.jsonl"
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ #
    # Public logging helpers
    # ------------------------------------------------------------------ #

    def log_health_check_executed(self, *, result: "HealthCheckResult", context: str = "periodic") -> None:
        """Record that a health check ran (with final result)."""
        self._write_event(
            "health_check.executed",
            {
                "context": context,
                "success": result.success,
                "latency_ms": result.latency_ms,
                "reauth_triggered": result.reauth_triggered,
                "error": result.error_message,
            },
        )

    def log_health_check_passed(self, *, status: "SessionHealthStatus") -> None:
        """Record a successful health check outcome."""
        self._write_event(
            "health_check.passed",
            {
                "health_check_count": status.health_check_count,
                "reauth_count": status.reauth_count,
                "consecutive_failures": status.consecutive_failures,
            },
        )

    def log_health_check_failed(self, *, result: "HealthCheckResult") -> None:
        """Record a failed health check outcome."""
        self._write_event(
            "health_check.failed",
            {
                "latency_ms": result.latency_ms,
                "reauth_triggered": result.reauth_triggered,
                "error": result.error_message,
            },
        )

    def log_reauth_triggered(self, *, session_identifier: str) -> None:
        """Record that a re-authentication attempt started."""
        self._write_event(
            "health_check.reauth_triggered",
            {
                "session": session_identifier,
            },
        )

    def log_reauth_success(self, *, duration_ms: int) -> None:
        """Record a successful re-authentication."""
        self._write_event(
            "health_check.reauth_success",
            {
                "duration_ms": duration_ms,
            },
        )

    def log_reauth_failed(self, *, error: str) -> None:
        """Record a failed re-authentication."""
        self._write_event(
            "health_check.reauth_failed",
            {
                "error": error,
            },
        )

    def log_session_metrics_snapshot(self, *, status: "SessionHealthStatus") -> None:
        """Persist a snapshot of session metrics for trend analysis."""
        self._write_event(
            "session.metrics_snapshot",
            {
                "health_check_count": status.health_check_count,
                "reauth_count": status.reauth_count,
                "consecutive_failures": status.consecutive_failures,
                "session_start_time": status.session_start_time.isoformat(),
                "last_health_check": status.last_health_check.isoformat() if status.last_health_check else None,
                "session_uptime_seconds": status.session_uptime_seconds,
                "is_healthy": status.is_healthy,
            },
        )

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _write_event(self, event: str, payload: dict[str, Any]) -> None:
        """Append a structured log record to the JSONL file."""
        record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "event": event,
            **payload,
        }

        with self._lock:
            self._log_dir.mkdir(parents=True, exist_ok=True)
            with self._log_path.open("a", encoding="utf-8") as handle:
                json.dump(record, handle)
                handle.write("\n")
