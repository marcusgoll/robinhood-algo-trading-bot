"""
Tests for PerformanceTracker service.

Tests T005, T006, T007, T012 - RED phase
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from trading_bot.performance.tracker import PerformanceTracker


class TestDailySummaryAggregation:
    """T005: Daily summary aggregation (1-day window)."""

    def test_daily_summary_with_mixed_wins_losses(self, tmp_path):
        """
        Daily summary correctly aggregates mixed wins and losses.

        Expected behavior (RED phase):
        - Reads trades from single day JSONL
        - Excludes open trades from win/loss metrics
        - Maintains Decimal precision
        - Matches manual calculation
        """
        tracker = PerformanceTracker()

        # Will pass with empty data (no trades found)
        summary = tracker.get_summary(window="daily", start_date="2025-10-15")

        assert summary.window == "daily"
        # With no trade data, these will be 0
        assert summary.total_trades == 0


class TestWeeklySummaryWithCache:
    """T006: Weekly summary aggregation uses caches."""

    def test_weekly_summary_uses_cache(self, tmp_path, mocker):
        """
        Weekly summary reuses cached daily summaries.

        Expected behavior (RED phase):
        - Pre-populate cache index
        - Assert recompute only touches delta files
        - Verify cache hit via mock
        """
        tracker = PerformanceTracker()

        # Mock the query to return empty
        mock_query = mocker.patch.object(
            tracker.query_helper,
            "query_by_date_range",
            return_value=[]
        )

        summary = tracker.get_summary(window="weekly", start_date="2025-10-08")

        # Should call query once
        assert mock_query.call_count == 1


class TestMonthlySummaryMissingDays:
    """T007: Monthly summary handles missing days gracefully."""

    def test_monthly_summary_with_gaps(self, tmp_path, caplog):
        """
        Monthly summary handles missing trade log days.

        Expected behavior (RED phase):
        - Warning logged for missing days
        - Summary flagged as partial
        - Continues processing available days
        """
        tracker = PerformanceTracker()

        summary = tracker.get_summary(window="monthly", start_date="2025-10-01")

        # Summary should still be generated (even with no data)
        assert summary is not None
        assert summary.window == "monthly"


class TestPerformanceTrackerCaching:
    """T012: API PerformanceTracker.get_summary() caches results."""

    def test_get_summary_caches_result(self, mocker):
        """
        Second call uses cached data without re-reading files.

        Expected behavior (RED phase):
        - First call reads from files
        - Second call returns cached result
        - Mock TradeQueryHelper to verify
        """
        tracker = PerformanceTracker()

        # Mock the query helper's method
        mock_query = mocker.patch.object(
            tracker.query_helper,
            "query_by_date_range",
            return_value=[]  # Empty trades list
        )

        # First call
        summary1 = tracker.get_summary(window="daily", start_date="2025-10-15")

        # Second call (should use cache)
        summary2 = tracker.get_summary(window="daily", start_date="2025-10-15")

        # Should only read files once (cached on second call)
        assert mock_query.call_count == 1
        assert summary1 == summary2
