"""Structured logging for session health events.

Provides JSONL-formatted logging for health check events, reauth activity,
and session metrics snapshots.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from trading_bot.health.session_health import HealthCheckResult, SessionHealthStatus

__all__ = ["HealthCheckLogger"]


class HealthCheckLogger:
    """Structured JSONL logger for health check events.

    Writes health check events to logs/health_check.log in JSONL format
    for analysis and monitoring.

    Attributes:
        log_file_path: Path to the health check log file
    """

    def __init__(self, log_file_path: str = "logs/health_check.log") -> None:
        """Initialize health check logger.

        Args:
            log_file_path: Path to log file (default: logs/health_check.log)
        """
        self.log_file_path = Path(log_file_path)
        self.log_file_path.parent.mkdir(parents=True, exist_ok=True)

    def _write_event(self, event_data: dict[str, Any]) -> None:
        """Write a single event to the log file.

        Args:
            event_data: Dictionary containing event data
        """
        event_data["timestamp"] = datetime.now(UTC).isoformat()
        with self.log_file_path.open("a") as f:
            f.write(json.dumps(event_data) + "\n")

    def log_health_check_executed(
        self, result: HealthCheckResult, context: str = "periodic"
    ) -> None:
        """Log that a health check was executed.

        Args:
            result: Health check result
            context: Context of the health check (e.g., "periodic", "pre_trade")
        """
        self._write_event({
            "event": "health_check.executed",
            "success": result.success,
            "latency_ms": result.latency_ms,
            "context": context,
            "reauth_triggered": result.reauth_triggered,
        })

    def log_health_check_passed(self, status: SessionHealthStatus) -> None:
        """Log that a health check passed.

        Args:
            status: Current session health status
        """
        self._write_event({
            "event": "health_check.passed",
            "session_uptime": status.session_uptime_seconds,
            "is_healthy": status.is_healthy,
            "health_check_count": status.health_check_count,
        })

    def log_health_check_failed(self, result: HealthCheckResult) -> None:
        """Log that a health check failed.

        Args:
            result: Health check result with error details
        """
        self._write_event({
            "event": "health_check.failed",
            "error_message": result.error_message,
            "latency_ms": result.latency_ms,
        })

    def log_reauth_triggered(self, session_id: str) -> None:
        """Log that automatic reauth was triggered.

        Args:
            session_id: Current session identifier
        """
        self._write_event({
            "event": "health_check.reauth_triggered",
            "session_id": session_id,
        })

    def log_reauth_success(self, duration_ms: int) -> None:
        """Log that reauth completed successfully.

        Args:
            duration_ms: Time taken for reauth in milliseconds
        """
        self._write_event({
            "event": "health_check.reauth_success",
            "duration_ms": duration_ms,
        })

    def log_reauth_failed(self, error: str) -> None:
        """Log that reauth failed.

        Args:
            error: Error message describing the failure
        """
        self._write_event({
            "event": "health_check.reauth_failed",
            "error": error,
        })

    def log_session_metrics_snapshot(self, status: SessionHealthStatus) -> None:
        """Log a complete snapshot of session metrics.

        Args:
            status: Current session health status
        """
        self._write_event({
            "event": "session.metrics_snapshot",
            "is_healthy": status.is_healthy,
            "session_uptime_seconds": status.session_uptime_seconds,
            "health_check_count": status.health_check_count,
            "reauth_count": status.reauth_count,
            "consecutive_failures": status.consecutive_failures,
        })
