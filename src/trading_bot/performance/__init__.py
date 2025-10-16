"""
Performance tracking and analytics package.

Provides aggregated trade metrics, rolling windows, alerts, and exports
for daily/weekly/monthly performance analysis.
"""

from .models import AlertEvent, PerformanceSummary

__all__ = [
    "PerformanceSummary",
    "AlertEvent",
]
