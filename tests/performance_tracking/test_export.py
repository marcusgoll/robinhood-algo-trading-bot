"""
Tests for export generation.

Test T014 - RED phase
"""

import pytest
from datetime import datetime
from decimal import Decimal

from trading_bot.performance.models import PerformanceSummary


class TestMarkdownExport:
    """T014: Markdown export formatting for summaries."""

    def test_markdown_export_structure(self):
        """
        Markdown export includes proper sections and formatting.

        Expected behavior (RED phase):
        - Overview section
        - Metrics table
        - Alerts section
        - Proper Markdown formatting
        """
        summary = PerformanceSummary(
            window="daily",
            start_date=datetime(2025, 10, 15, 0, 0, 0),
            end_date=datetime(2025, 10, 15, 23, 59, 59),
            total_trades=12,
            total_wins=8,
            total_losses=4,
            win_rate=Decimal("0.6667"),
            current_streak=3,
            streak_type="win",
            avg_profit_per_win=Decimal("125.50"),
            avg_loss_per_loss=Decimal("-45.25"),
            avg_risk_reward_ratio=Decimal("2.77"),
            realized_pnl=Decimal("823.00"),
            unrealized_pnl=Decimal("0.00"),
            alert_status="OK",
            generated_at=datetime(2025, 10, 15, 16, 0, 0),
        )

        # Function to be implemented in GREEN phase
        from trading_bot.performance.tracker import PerformanceTracker

        tracker = PerformanceTracker()
        markdown = tracker.export_markdown(summary)

        # Verify structure
        assert "## Overview" in markdown
        assert "## Metrics" in markdown
        assert "|" in markdown  # Table formatting
        assert "Win Rate" in markdown
        assert "66.67%" in markdown

        pytest.fail("T014: RED phase - test should fail until GREEN implementation")
