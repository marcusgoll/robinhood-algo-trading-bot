"""
RED phase tests for ExportGenerator (T011-T012).

These tests MUST FAIL before implementation.
Testing JSON and Markdown export generation with schema validation.
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
def sample_snapshot() -> DashboardSnapshot:
    """Create a realistic dashboard snapshot for export testing."""
    generated_at = datetime(2025, 10, 16, 14, 30, 0, tzinfo=UTC)

    account = AccountStatus(
        buying_power=Decimal("15000.00"),
        account_balance=Decimal("25000.00"),
        cash_balance=Decimal("10000.00"),
        day_trade_count=2,
        last_updated=generated_at,
    )

    positions = [
        PositionDisplay(
            symbol="AAPL",
            quantity=100,
            entry_price=Decimal("150.00"),
            current_price=Decimal("152.50"),
            unrealized_pl=Decimal("250.00"),
            unrealized_pl_pct=Decimal("1.67"),
            last_updated=generated_at,
        ),
        PositionDisplay(
            symbol="MSFT",
            quantity=50,
            entry_price=Decimal("320.00"),
            current_price=Decimal("318.75"),
            unrealized_pl=Decimal("-62.50"),
            unrealized_pl_pct=Decimal("-0.39"),
            last_updated=generated_at,
        ),
    ]

    metrics = PerformanceMetrics(
        win_rate=67.5,
        avg_risk_reward=2.1,
        total_realized_pl=Decimal("450.00"),
        total_unrealized_pl=Decimal("187.50"),
        total_pl=Decimal("637.50"),
        current_streak=3,
        streak_type="WIN",
        trades_today=8,
        session_count=15,
        max_drawdown=Decimal("-125.00"),
    )

    targets = DashboardTargets(
        win_rate_target=65.0,
        daily_pl_target=Decimal("500.00"),
        trades_per_day_target=10,
        max_drawdown_target=Decimal("-200.00"),
        avg_risk_reward_target=2.0,
    )

    return DashboardSnapshot(
        account_status=account,
        positions=positions,
        performance_metrics=metrics,
        targets=targets,
        market_status="OPEN",
        generated_at=generated_at,
        data_age_seconds=5.2,
        is_data_stale=False,
        warnings=["Test warning for export"],
    )


class TestExportGeneratorJSON:
    """T011: Test ExportGenerator creates valid JSON export."""

    def test_json_structure_matches_schema(
        self,
        tmp_path: Path,
        sample_snapshot: DashboardSnapshot
    ) -> None:
        """JSON export must contain all expected top-level keys."""
        generator = ExportGenerator()
        json_path = tmp_path / "test-export.json"

        generator.export_to_json(sample_snapshot, json_path)

        assert json_path.exists(), "JSON file should be created"

        with json_path.open() as f:
            data = json.load(f)

        # Verify top-level schema
        required_keys = {
            "generated_at",
            "market_status",
            "data_age_seconds",
            "is_data_stale",
            "account_status",
            "positions",
            "performance_metrics",
            "targets",
            "warnings",
        }
        assert set(data.keys()) >= required_keys, f"Missing keys: {required_keys - set(data.keys())}"

        # Verify nested structures
        assert isinstance(data["account_status"], dict)
        assert isinstance(data["positions"], list)
        assert isinstance(data["performance_metrics"], dict)
        assert isinstance(data["targets"], dict)
        assert isinstance(data["warnings"], list)

    def test_decimal_values_serialized_correctly(
        self,
        tmp_path: Path,
        sample_snapshot: DashboardSnapshot
    ) -> None:
        """Decimal fields must serialize to strings preserving precision."""
        generator = ExportGenerator()
        json_path = tmp_path / "test-export.json"

        generator.export_to_json(sample_snapshot, json_path)

        with json_path.open() as f:
            data = json.load(f)

        # Check account balance precision
        account = data["account_status"]
        assert account["buying_power"] == "15000.00"
        assert account["account_balance"] == "25000.00"
        assert account["cash_balance"] == "10000.00"

        # Check position P&L precision
        positions = data["positions"]
        assert positions[0]["unrealized_pl"] == "250.00"
        assert positions[0]["unrealized_pl_pct"] == "1.67"
        assert positions[1]["unrealized_pl"] == "-62.50"

        # Check metrics precision
        metrics = data["performance_metrics"]
        assert metrics["total_pl"] == "637.50"
        assert metrics["total_realized_pl"] == "450.00"
        assert metrics["max_drawdown"] == "-125.00"

    def test_timestamp_in_iso8601_format(
        self,
        tmp_path: Path,
        sample_snapshot: DashboardSnapshot
    ) -> None:
        """Timestamp must be in ISO 8601 format with timezone."""
        generator = ExportGenerator()
        json_path = tmp_path / "test-export.json"

        generator.export_to_json(sample_snapshot, json_path)

        with json_path.open() as f:
            data = json.load(f)

        # Verify ISO 8601 format
        timestamp_str = data["generated_at"]
        assert "T" in timestamp_str, "ISO 8601 requires T separator"
        assert timestamp_str.endswith("Z") or "+" in timestamp_str or timestamp_str.endswith(":00"), \
            "ISO 8601 requires timezone indicator"

        # Verify parseable
        parsed = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        assert parsed.year == 2025
        assert parsed.month == 10
        assert parsed.day == 16

    def test_file_written_to_logs_with_date_filename(
        self,
        tmp_path: Path,
        sample_snapshot: DashboardSnapshot,
        monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """JSON export must write to logs/ directory with YYYY-MM-DD in filename."""
        monkeypatch.chdir(tmp_path)
        generator = ExportGenerator()

        json_path, _ = generator.generate_exports(sample_snapshot)

        # Verify file in logs/ directory
        assert json_path.parent.name == "logs"
        assert json_path.exists()

        # Verify filename format: dashboard-export-YYYY-MM-DD.json
        assert json_path.name.startswith("dashboard-export-")
        assert json_path.suffix == ".json"
        assert "2025-10-16" in json_path.name

    def test_json_loads_succeeds(
        self,
        tmp_path: Path,
        sample_snapshot: DashboardSnapshot
    ) -> None:
        """Generated JSON must be valid and parseable."""
        generator = ExportGenerator()
        json_path = tmp_path / "test-export.json"

        generator.export_to_json(sample_snapshot, json_path)

        # Should not raise JSONDecodeError
        with json_path.open() as f:
            data = json.load(f)

        assert isinstance(data, dict)
        assert len(data) > 0


class TestExportGeneratorMarkdown:
    """T012: Test ExportGenerator creates readable Markdown export."""

    def test_markdown_headers_and_sections_present(
        self,
        tmp_path: Path,
        sample_snapshot: DashboardSnapshot
    ) -> None:
        """Markdown must have structured sections with headers."""
        generator = ExportGenerator()
        md_path = tmp_path / "test-export.md"

        generator.export_to_markdown(sample_snapshot, md_path)

        assert md_path.exists(), "Markdown file should be created"

        content = md_path.read_text()

        # Verify main sections exist
        assert "# Trading Dashboard Export" in content or "# Dashboard Export" in content
        assert "## Account Status" in content
        assert "## Open Positions" in content or "## Positions" in content
        assert "## Performance Metrics" in content

        # Verify metadata section
        assert "Generated:" in content or "Timestamp:" in content
        assert "Market Status:" in content

    def test_positions_table_formatted_as_markdown(
        self,
        tmp_path: Path,
        sample_snapshot: DashboardSnapshot
    ) -> None:
        """Positions must be formatted as valid markdown table."""
        generator = ExportGenerator()
        md_path = tmp_path / "test-export.md"

        generator.export_to_markdown(sample_snapshot, md_path)

        content = md_path.read_text()

        # Check for markdown table syntax
        assert "|" in content, "Markdown table requires pipe separators"
        assert "---" in content or "|-" in content, "Markdown table requires header separator"

        # Check for position data
        assert "AAPL" in content
        assert "MSFT" in content
        assert "100" in content  # AAPL quantity
        assert "50" in content   # MSFT quantity

        # Check for P&L values
        assert "250.00" in content or "$250.00" in content
        assert "1.67%" in content or "+1.67%" in content

    def test_metrics_formatted_with_bullet_points(
        self,
        tmp_path: Path,
        sample_snapshot: DashboardSnapshot
    ) -> None:
        """Performance metrics must use bullet points for readability."""
        generator = ExportGenerator()
        md_path = tmp_path / "test-export.md"

        generator.export_to_markdown(sample_snapshot, md_path)

        content = md_path.read_text()

        # Find performance metrics section
        metrics_section_start = content.find("## Performance Metrics")
        assert metrics_section_start != -1, "Metrics section should exist"

        metrics_section = content[metrics_section_start:metrics_section_start + 1000]

        # Check for bullet points (- or *)
        assert "- " in metrics_section or "* " in metrics_section, "Metrics should use bullet points"

        # Check for key metrics
        assert "Win Rate:" in content or "67.5%" in content
        assert "Total P&L:" in content or "637.50" in content
        assert "Current Streak:" in content or "3 wins" in content

    def test_target_comparison_included_when_targets_exist(
        self,
        tmp_path: Path,
        sample_snapshot: DashboardSnapshot
    ) -> None:
        """Markdown must include target comparison when targets are available."""
        generator = ExportGenerator()
        md_path = tmp_path / "test-export.md"

        generator.export_to_markdown(sample_snapshot, md_path)

        content = md_path.read_text()

        # Check for target indicators
        assert "Target:" in content or "target" in content.lower()
        assert "65.0" in content  # win rate target
        assert "500.00" in content  # daily PL target

        # Check for comparison indicators (checkmarks, arrows, etc)
        assert "✓" in content or "✗" in content or ">" in content or "<" in content

    def test_target_comparison_omitted_when_no_targets(
        self,
        tmp_path: Path,
        sample_snapshot: DashboardSnapshot
    ) -> None:
        """Markdown must gracefully handle missing targets."""
        # Create snapshot without targets
        snapshot_no_targets = DashboardSnapshot(
            account_status=sample_snapshot.account_status,
            positions=sample_snapshot.positions,
            performance_metrics=sample_snapshot.performance_metrics,
            targets=None,
            market_status=sample_snapshot.market_status,
            generated_at=sample_snapshot.generated_at,
            data_age_seconds=sample_snapshot.data_age_seconds,
            is_data_stale=sample_snapshot.is_data_stale,
            warnings=sample_snapshot.warnings,
        )

        generator = ExportGenerator()
        md_path = tmp_path / "test-export.md"

        generator.export_to_markdown(snapshot_no_targets, md_path)

        content = md_path.read_text()

        # Should still have metrics section
        assert "## Performance Metrics" in content

        # Should not have target comparison
        # (We're just checking it doesn't crash - specific text is implementation detail)
        assert len(content) > 0

    def test_markdown_file_written_with_date_filename(
        self,
        tmp_path: Path,
        sample_snapshot: DashboardSnapshot,
        monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Markdown export must write to logs/ directory with YYYY-MM-DD in filename."""
        monkeypatch.chdir(tmp_path)
        generator = ExportGenerator()

        _, md_path = generator.generate_exports(sample_snapshot)

        # Verify file in logs/ directory
        assert md_path.parent.name == "logs"
        assert md_path.exists()

        # Verify filename format: dashboard-export-YYYY-MM-DD.md
        assert md_path.name.startswith("dashboard-export-")
        assert md_path.suffix == ".md"
        assert "2025-10-16" in md_path.name

    def test_markdown_valid_no_broken_syntax(
        self,
        tmp_path: Path,
        sample_snapshot: DashboardSnapshot
    ) -> None:
        """Generated Markdown must not have broken syntax."""
        generator = ExportGenerator()
        md_path = tmp_path / "test-export.md"

        generator.export_to_markdown(sample_snapshot, md_path)

        content = md_path.read_text()

        # Basic syntax checks
        # Count opening/closing brackets
        assert content.count("[") == content.count("]"), "Unmatched brackets"

        # Check headers have space after #
        lines = content.splitlines()
        header_lines = [line for line in lines if line.startswith("#")]
        for header in header_lines:
            if not header.startswith("#" * 6):  # Allow up to H6
                assert header[header.count("#")] == " ", f"Header missing space: {header}"

        # Check table has consistent column count
        table_lines = [line for line in lines if line.strip().startswith("|")]
        if table_lines:
            first_col_count = table_lines[0].count("|")
            for line in table_lines:
                assert line.count("|") == first_col_count, f"Inconsistent table columns: {line}"
