"""
Integration test: Export generates valid files.

T031 - Tests full export flow from DashboardSnapshot to files.
Verifies JSON and Markdown file generation with proper formatting.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from trading_bot.dashboard.export_generator import ExportGenerator
from trading_bot.dashboard.models import (
    AccountStatus,
    DashboardSnapshot,
    DashboardTargets,
    PerformanceMetrics,
    PositionDisplay,
)


@pytest.fixture
def sample_snapshot():
    """Create a sample dashboard snapshot for export testing."""
    generated_at = datetime.now(UTC)

    account_status = AccountStatus(
        buying_power=Decimal("60000.00"),
        account_balance=Decimal("25000.00"),
        cash_balance=Decimal("15000.00"),
        day_trade_count=2,
        last_updated=generated_at,
    )

    positions = [
        PositionDisplay(
            symbol="AAPL",
            quantity=100,
            entry_price=Decimal("150.00"),
            current_price=Decimal("155.25"),
            unrealized_pl=Decimal("525.00"),
            unrealized_pl_pct=Decimal("3.50"),
            last_updated=generated_at,
        ),
        PositionDisplay(
            symbol="TSLA",
            quantity=50,
            entry_price=Decimal("250.00"),
            current_price=Decimal("245.50"),
            unrealized_pl=Decimal("-225.00"),
            unrealized_pl_pct=Decimal("-1.80"),
            last_updated=generated_at,
        ),
    ]

    metrics = PerformanceMetrics(
        win_rate=75.0,
        avg_risk_reward=2.8,
        total_realized_pl=Decimal("1250.50"),
        total_unrealized_pl=Decimal("300.00"),
        total_pl=Decimal("1550.50"),
        current_streak=3,
        streak_type="WIN",
        trades_today=8,
        session_count=2,
        max_drawdown=Decimal("-150.00"),
    )

    targets = DashboardTargets(
        win_rate_target=70.0,
        daily_pl_target=Decimal("500.00"),
        trades_per_day_target=5,
        max_drawdown_target=Decimal("-200.00"),
        avg_risk_reward_target=2.5,
    )

    return DashboardSnapshot(
        account_status=account_status,
        positions=positions,
        performance_metrics=metrics,
        targets=targets,
        market_status="OPEN",
        generated_at=generated_at,
        data_age_seconds=5.2,
        is_data_stale=False,
        warnings=["Sample warning for testing"],
    )


@pytest.fixture
def exporter():
    """Create ExportGenerator instance."""
    return ExportGenerator()


class TestExportIntegration:
    """Integration tests for dashboard export functionality."""

    def test_json_export_creates_valid_file(self, exporter, sample_snapshot, tmp_path):
        """
        T031.1 - Verify JSON export creates valid, parseable file.

        Tests that JSON file is created with correct structure,
        valid JSON syntax, and proper Decimal serialization.
        """
        json_path = tmp_path / "dashboard-export-test.json"

        # Export to JSON
        exporter.export_to_json(sample_snapshot, json_path)

        # Verify file was created
        assert json_path.exists()
        assert json_path.stat().st_size > 0

        # Verify JSON is valid and parseable
        with json_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        # Verify top-level structure
        assert "generated_at" in data
        assert "market_status" in data
        assert "account_status" in data
        assert "positions" in data
        assert "performance_metrics" in data
        assert "targets" in data
        assert "warnings" in data

        # Verify account status
        assert data["account_status"]["buying_power"] == "60000.00"
        assert data["account_status"]["account_balance"] == "25000.00"
        assert data["account_status"]["cash_balance"] == "15000.00"
        assert data["account_status"]["day_trade_count"] == 2

        # Verify positions
        assert len(data["positions"]) == 2
        assert data["positions"][0]["symbol"] == "AAPL"
        assert data["positions"][0]["unrealized_pl"] == "525.00"
        assert data["positions"][1]["symbol"] == "TSLA"
        assert data["positions"][1]["unrealized_pl"] == "-225.00"

        # Verify performance metrics
        metrics = data["performance_metrics"]
        assert metrics["win_rate"] == 75.0
        assert metrics["avg_risk_reward"] == 2.8
        assert metrics["total_pl"] == "1550.50"
        assert metrics["trades_today"] == 8
        assert metrics["current_streak"] == 3
        assert metrics["streak_type"] == "WIN"

        # Verify targets
        targets = data["targets"]
        assert targets["win_rate_target"] == 70.0
        assert targets["daily_pl_target"] == "500.00"

        # Verify warnings
        assert len(data["warnings"]) == 1
        assert "Sample warning" in data["warnings"][0]

    def test_markdown_export_creates_formatted_file(
        self, exporter, sample_snapshot, tmp_path
    ):
        """
        T031.2 - Verify Markdown export creates properly formatted file.

        Tests that Markdown file contains all expected sections,
        proper table formatting, and readable content.
        """
        md_path = tmp_path / "dashboard-export-test.md"

        # Export to Markdown
        exporter.export_to_markdown(sample_snapshot, md_path)

        # Verify file was created
        assert md_path.exists()
        assert md_path.stat().st_size > 0

        # Read and verify content
        content = md_path.read_text(encoding="utf-8")

        # Verify main sections exist
        assert "# Trading Dashboard Export" in content
        assert "## Account Status" in content
        assert "## Positions" in content
        assert "## Performance Metrics" in content
        assert "## Performance Targets" in content
        assert "## Warnings" in content

        # Verify account status details
        assert "$25,000.00" in content  # Account balance
        assert "$60,000.00" in content  # Buying power
        assert "Day Trade Count:** 2" in content

        # Verify positions table
        assert "| Symbol |" in content  # Table header
        assert "| AAPL |" in content
        assert "| TSLA |" in content
        assert "+$525.00" in content  # AAPL profit
        assert "-$225.00" in content  # TSLA loss

        # Verify performance metrics
        assert "Win Rate:** 75.00%" in content
        assert "Total P&L:** $1,550.50" in content
        assert "Current Streak:** 3 (WIN)" in content
        assert "Trades Today:** 8" in content

        # Verify target comparisons with indicators (ASCII-safe)
        assert ">" in content or "<" in content or "✓" in content or "✗" in content

        # Verify warnings section
        assert "Sample warning" in content

        # Verify footer
        assert "Generated by Trading Bot Dashboard" in content

    def test_markdown_table_formatting(self, exporter, sample_snapshot, tmp_path):
        """
        T031.3 - Verify Markdown table is properly formatted.

        Tests that positions table has correct number of columns,
        proper alignment, and valid Markdown syntax.
        """
        md_path = tmp_path / "dashboard-export-test.md"
        exporter.export_to_markdown(sample_snapshot, md_path)

        content = md_path.read_text(encoding="utf-8")

        # Find positions table
        lines = content.split("\n")
        table_start = None
        for i, line in enumerate(lines):
            if "| Symbol |" in line:
                table_start = i
                break

        assert table_start is not None, "Positions table not found"

        # Verify table structure
        header_line = lines[table_start]
        separator_line = lines[table_start + 1]
        data_line_1 = lines[table_start + 2]
        data_line_2 = lines[table_start + 3]

        # Count columns (should be 7: Symbol, Quantity, Entry, Current, P&L, P&L%, Updated)
        assert header_line.count("|") == 8  # 7 columns + 2 edge pipes
        assert separator_line.count("|") == 8
        assert separator_line.count("-") > 0  # Has separators

        # Verify data rows have same number of columns
        assert data_line_1.count("|") == 8
        assert data_line_2.count("|") == 8

    def test_generate_exports_creates_both_files(
        self, exporter, sample_snapshot, tmp_path
    ):
        """
        T031.4 - Verify generate_exports creates both JSON and Markdown files.

        Tests that the convenience method creates both files with
        correct filenames including date.
        """
        # Temporarily change to tmp_path as working directory
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Generate exports
            json_path, md_path = exporter.generate_exports(sample_snapshot)

            # Verify both paths returned
            assert json_path is not None
            assert md_path is not None

            # Verify files exist
            assert json_path.exists()
            assert md_path.exists()

            # Verify filenames include date
            date_str = sample_snapshot.generated_at.strftime("%Y-%m-%d")
            assert date_str in json_path.name
            assert date_str in md_path.name

            # Verify file extensions
            assert json_path.suffix == ".json"
            assert md_path.suffix == ".md"

            # Verify files are in logs/ directory
            assert json_path.parent.name == "logs"
            assert md_path.parent.name == "logs"

        finally:
            os.chdir(original_cwd)

    def test_export_without_targets(self, exporter, sample_snapshot, tmp_path):
        """
        T031.5 - Verify exports work correctly when targets are None.

        Tests that dashboard can export without performance targets
        configured.
        """
        # Remove targets from snapshot
        snapshot_no_targets = DashboardSnapshot(
            account_status=sample_snapshot.account_status,
            positions=sample_snapshot.positions,
            performance_metrics=sample_snapshot.performance_metrics,
            targets=None,  # No targets
            market_status=sample_snapshot.market_status,
            generated_at=sample_snapshot.generated_at,
            data_age_seconds=sample_snapshot.data_age_seconds,
            is_data_stale=sample_snapshot.is_data_stale,
            warnings=sample_snapshot.warnings,
        )

        json_path = tmp_path / "export-no-targets.json"
        md_path = tmp_path / "export-no-targets.md"

        # Should not raise exceptions
        exporter.export_to_json(snapshot_no_targets, json_path)
        exporter.export_to_markdown(snapshot_no_targets, md_path)

        # Verify JSON has null targets
        with json_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["targets"] is None

        # Verify Markdown doesn't have targets section
        content = md_path.read_text(encoding="utf-8")
        assert "## Performance Targets" not in content

    def test_export_with_empty_positions(self, exporter, sample_snapshot, tmp_path):
        """
        T031.6 - Verify exports handle empty positions list correctly.

        Tests that exports work when there are no open positions.
        """
        # Create snapshot with no positions
        snapshot_no_positions = DashboardSnapshot(
            account_status=sample_snapshot.account_status,
            positions=[],  # No positions
            performance_metrics=sample_snapshot.performance_metrics,
            targets=sample_snapshot.targets,
            market_status=sample_snapshot.market_status,
            generated_at=sample_snapshot.generated_at,
            data_age_seconds=sample_snapshot.data_age_seconds,
            is_data_stale=sample_snapshot.is_data_stale,
            warnings=sample_snapshot.warnings,
        )

        json_path = tmp_path / "export-no-positions.json"
        md_path = tmp_path / "export-no-positions.md"

        # Should not raise exceptions
        exporter.export_to_json(snapshot_no_positions, json_path)
        exporter.export_to_markdown(snapshot_no_positions, md_path)

        # Verify JSON has empty positions array
        with json_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["positions"] == []

        # Verify Markdown shows "No positions" message
        content = md_path.read_text(encoding="utf-8")
        assert "*No open positions*" in content

    def test_decimal_precision_preserved(self, exporter, sample_snapshot, tmp_path):
        """
        T031.7 - Verify Decimal precision is preserved in exports.

        Tests that monetary values maintain proper precision
        in both JSON and Markdown exports.
        """
        json_path = tmp_path / "export-precision.json"
        md_path = tmp_path / "export-precision.md"

        exporter.export_to_json(sample_snapshot, json_path)
        exporter.export_to_markdown(sample_snapshot, md_path)

        # Verify JSON preserves precision
        with json_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["performance_metrics"]["total_pl"] == "1550.50"
        assert data["performance_metrics"]["total_realized_pl"] == "1250.50"

        # Verify Markdown formats with 2 decimal places
        content = md_path.read_text(encoding="utf-8")
        assert "$1,550.50" in content
        assert "$1,250.50" in content

    def test_iso8601_timestamps(self, exporter, sample_snapshot, tmp_path):
        """
        T031.8 - Verify timestamps are in ISO 8601 format.

        Tests that all timestamps in exports use ISO 8601 format.
        """
        json_path = tmp_path / "export-timestamps.json"
        exporter.export_to_json(sample_snapshot, json_path)

        with json_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        # Verify ISO 8601 format (contains 'T' and timezone info)
        assert "T" in data["generated_at"]
        assert "T" in data["account_status"]["last_updated"]
        assert "T" in data["positions"][0]["last_updated"]

        # Verify parseable as datetime
        from datetime import datetime

        dt = datetime.fromisoformat(data["generated_at"])
        assert dt is not None

    def test_file_cleanup_after_assertions(self, exporter, sample_snapshot, tmp_path):
        """
        T031.9 - Verify test files can be cleaned up after assertions.

        Tests that temporary files can be removed without issues,
        demonstrating proper file handling.
        """
        json_path = tmp_path / "cleanup-test.json"
        md_path = tmp_path / "cleanup-test.md"

        # Create files
        exporter.export_to_json(sample_snapshot, json_path)
        exporter.export_to_markdown(sample_snapshot, md_path)

        assert json_path.exists()
        assert md_path.exists()

        # Clean up (tmp_path fixture handles this automatically,
        # but we test explicit deletion)
        json_path.unlink()
        md_path.unlink()

        assert not json_path.exists()
        assert not md_path.exists()
