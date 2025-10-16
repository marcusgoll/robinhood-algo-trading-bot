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

        # Will fail - not implemented yet
        summary = tracker.get_summary(window="daily", start_date="2025-10-15")

        assert summary.window == "daily"
        assert summary.total_trades > 0
        assert summary.win_rate == Decimal("0.6667")  # 8 wins, 4 losses
        pytest.fail("T005: RED phase - test should fail until GREEN implementation")


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

        # Mock file stats to verify selective reading
        mock_query = mocker.patch("trading_bot.logging.query_helper.TradeQueryHelper")

        summary = tracker.get_summary(window="weekly", start_date="2025-10-08")

        # Should read from cache, not all 7 files
        assert mock_query.call_count < 7
        pytest.fail("T006: RED phase - test should fail until GREEN implementation")


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

        assert "missing" in caplog.text.lower() or "partial" in caplog.text.lower()
        # Summary should still be generated
        assert summary is not None
        pytest.fail("T007: RED phase - test should fail until GREEN implementation")


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

        # Mock the query helper
        mock_query = mocker.patch(
            "trading_bot.performance.tracker.TradeQueryHelper"
        )

        # First call
        summary1 = tracker.get_summary(window="daily", start_date="2025-10-15")

        # Second call (should use cache)
        summary2 = tracker.get_summary(window="daily", start_date="2025-10-15")

        # Should only read files once
        assert mock_query.call_count == 1
        assert summary1 == summary2
        pytest.fail("T012: RED phase - test should fail until GREEN implementation")
