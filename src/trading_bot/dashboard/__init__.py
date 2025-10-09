"""
CLI Dashboard Module for Trading Bot.

Provides real-time monitoring of account status, current positions, and performance metrics.
"""

from .dashboard import (
    load_targets,
    fetch_dashboard_state,
    run_dashboard_loop,
)
from .metrics_calculator import MetricsCalculator
from .models import (
    DashboardState,
    AccountStatus,
    PositionDisplay,
    PerformanceMetrics,
    DashboardTargets,
)

__all__ = [
    "DashboardState",
    "AccountStatus",
    "PositionDisplay",
    "PerformanceMetrics",
    "DashboardTargets",
    "MetricsCalculator",
    "load_targets",
    "fetch_dashboard_state",
    "run_dashboard_loop",
]
