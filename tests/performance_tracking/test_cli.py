"""
Tests for CLI entrypoint.

Tests T010, T011 - RED phase
"""

import pytest
from pathlib import Path

from trading_bot.performance.cli import main


class TestCLIDailySummary:
    """T010: CLI --window daily generates summary & export files."""

    def test_cli_daily_summary_creates_files(self, tmp_path, monkeypatch):
        """
        CLI generates summary and export files.

        Expected behavior (RED phase):
        - Exit code 0
        - JSON file created in logs/performance/
        - Markdown file created
        - Console output includes summary
        """
        # Change to tmp directory for test isolation
        monkeypatch.chdir(tmp_path)

        exit_code = main(["--window", "daily", "--export"])

        assert exit_code == 0

        # Check for generated files
        perf_dir = tmp_path / "logs" / "performance"
        json_files = list(perf_dir.glob("daily-summary-*.json"))
        md_files = list(perf_dir.glob("daily-summary-*.md"))

        assert len(json_files) > 0
        assert len(md_files) > 0
        pytest.fail("T010: RED phase - test should fail until GREEN implementation")


class TestCLIBackfill:
    """T011: CLI --backfill 7 rebuilds missing summaries."""

    def test_cli_backfill_rebuilds_summaries(self, tmp_path, mocker):
        """
        CLI backfill mode rebuilds historical summaries.

        Expected behavior (RED phase):
        - Calls tracker for each day
        - Respects cache skip logic
        - Generates N summary files
        """
        mock_tracker = mocker.patch(
            "trading_bot.performance.cli.PerformanceTracker"
        )

        exit_code = main(["--window", "daily", "--backfill", "7"])

        assert exit_code == 0
        # Should call tracker for each of 7 days
        assert mock_tracker.return_value.get_summary.call_count == 7
        pytest.fail("T011: RED phase - test should fail until GREEN implementation")
