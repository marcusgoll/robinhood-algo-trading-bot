"""
Performance tracker service for aggregating trade metrics.
"""

from typing import Optional

from .models import PerformanceSummary


class PerformanceTracker:
    """
    Orchestrates trade log aggregation, caching, and summary generation.

    Reuses TradeQueryHelper for JSONL ingestion and MetricsCalculator
    for core metric computations.
    """

    def __init__(self) -> None:
        """Initialize the performance tracker."""
        pass

    def get_summary(
        self,
        window: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> PerformanceSummary:
        """
        Get performance summary for the specified window.

        Args:
            window: Time window ("daily", "weekly", "monthly")
            start_date: Optional start date (ISO format)
            end_date: Optional end date (ISO format)

        Returns:
            PerformanceSummary with aggregated metrics
        """
        raise NotImplementedError("To be implemented in GREEN phase")
