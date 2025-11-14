"""
CLI dashboard package exports.

Provides reusable data provider, models, metrics calculator, and CLI entry points
for both the Rich terminal dashboard and forthcoming Textual TUI implementation.
"""

from .dashboard import main, run_dashboard_loop
from .data_provider import DashboardDataProvider, ProviderConfig
from .metrics_calculator import MetricsCalculator
from .models import (
    AccountStatus,
    DashboardSnapshot,
    DashboardTargets,
    PerformanceMetrics,
    PositionDisplay,
)

__all__ = [
    "AccountStatus",
    "PositionDisplay",
    "PerformanceMetrics",
    "DashboardTargets",
    "DashboardSnapshot",
    "DashboardDataProvider",
    "ProviderConfig",
    "MetricsCalculator",
    "run_dashboard_loop",
    "main",
]
