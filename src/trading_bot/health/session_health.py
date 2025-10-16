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

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Optional

__all__ = ["SessionHealthStatus", "HealthCheckResult"]


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
    error_message: Optional[str]
    reauth_triggered: bool
