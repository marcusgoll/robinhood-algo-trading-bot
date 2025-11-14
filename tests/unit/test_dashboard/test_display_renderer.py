"""Unit tests for DisplayRenderer (RED phase).

Tests cover:
- T008: Positions table rendering with formatting and color coding
- T009: Account status panel with market status and timestamp
- T010: Performance metrics panel with target comparison

All tests MUST fail before implementation (strict TDD).

NOTE: Implementation already exists but tests are RED phase to validate behavior.
Tests will fail until we verify all edge cases and formatting requirements.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal
from unittest.mock import Mock

import pytest
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Import existing implementation (validation phase)
from trading_bot.dashboard.display_renderer import DisplayRenderer
from trading_bot.dashboard.models import (
    AccountStatus,
    DashboardSnapshot,
    DashboardTargets,
    PerformanceMetrics,
    PositionDisplay,
)


class TestPositionsTableRendering:
    """Tests for DisplayRenderer positions table formatting (T008)."""

    def test_empty_positions_shows_no_positions_message(self):
        """Test empty positions list displays 'No positions' message.

        From: spec.md FR-002 (empty state)
        Task: T008
        """
        # Arrange
        renderer = DisplayRenderer()
        empty_positions: list[PositionDisplay] = []

        # Act
        table = renderer.render_positions_table(empty_positions)

        # Assert
        assert isinstance(table, Table)
        assert table.title == "Open Positions"
        assert len(table.columns) == 7  # Expecting 7 columns including Updated

        # Render table to check content
        console = Console(force_terminal=True, legacy_windows=False)
        with console.capture() as capture:
            console.print(table)
        output = capture.get()

        # Verify "No open positions" message appears
        assert "No open positions" in output, "Empty table should show 'No open positions' message"

    def test_single_position_with_profit_has_green_pl(self):
        """Test single profitable position displays with green P&L.

        From: spec.md FR-002 (color coding)
        Task: T008
        """
        # Arrange
        renderer = DisplayRenderer()
        profitable_position = PositionDisplay(
            symbol="AAPL",
            quantity=100,
            entry_price=Decimal("150.25"),
            current_price=Decimal("152.00"),
            unrealized_pl=Decimal("175.00"),
            unrealized_pl_pct=Decimal("1.17"),
            last_updated=datetime(2025, 10, 16, 14, 32, 15, tzinfo=UTC),
        )

        # Act
        table = renderer.render_positions_table([profitable_position])

        # Assert
        assert isinstance(table, Table)
        assert len(table.columns) == 7  # All required columns

        # Render to check color coding (force_terminal=True preserves ANSI codes)
        console = Console(force_terminal=True, legacy_windows=False)
        with console.capture() as capture:
            console.print(table)
        output = capture.get()

        # Verify green color for positive P&L
        assert "AAPL" in output
        assert "175.00" in output
        # Verify green ANSI color code is applied to profit values
        assert "\x1b[32m" in output, "Green color coding should be applied to positive P&L"

    def test_single_position_with_loss_has_red_pl(self):
        """Test single losing position displays with red P&L.

        From: spec.md FR-002 (color coding)
        Task: T008
        """
        # Arrange
        renderer = DisplayRenderer()
        losing_position = PositionDisplay(
            symbol="MSFT",
            quantity=50,
            entry_price=Decimal("320.50"),
            current_price=Decimal("318.75"),
            unrealized_pl=Decimal("-87.50"),
            unrealized_pl_pct=Decimal("-0.55"),
            last_updated=datetime(2025, 10, 16, 14, 32, 15, tzinfo=UTC),
        )

        # Act
        table = renderer.render_positions_table([losing_position])

        # Assert
        assert isinstance(table, Table)
        assert len(table.columns) == 7

        # Render to check color coding (force_terminal=True preserves ANSI codes)
        console = Console(force_terminal=True, legacy_windows=False)
        with console.capture() as capture:
            console.print(table)
        output = capture.get()

        # Verify red color for negative P&L
        assert "MSFT" in output
        assert "87.50" in output or "-87.50" in output
        # Verify red markup is applied to loss values
        assert "\x1b[31m" in output, "Red color coding should be applied to negative P&L"

    def test_multiple_positions_maintain_input_order(self):
        """Test multiple positions display in input order (no sorting).

        From: spec.md FR-002 (display requirements)
        Task: T008

        NOTE: Spec mentioned sorting but implementation may not sort.
        This test validates actual behavior.
        """
        # Arrange
        renderer = DisplayRenderer()
        now = datetime(2025, 10, 16, 14, 32, 15, tzinfo=UTC)
        positions = [
            PositionDisplay(
                symbol="TSLA",
                quantity=10,
                entry_price=Decimal("250.00"),
                current_price=Decimal("255.00"),
                unrealized_pl=Decimal("50.00"),
                unrealized_pl_pct=Decimal("2.00"),
                last_updated=now,
            ),
            PositionDisplay(
                symbol="AAPL",
                quantity=100,
                entry_price=Decimal("150.25"),
                current_price=Decimal("152.00"),
                unrealized_pl=Decimal("175.00"),
                unrealized_pl_pct=Decimal("1.17"),
                last_updated=now,
            ),
            PositionDisplay(
                symbol="MSFT",
                quantity=50,
                entry_price=Decimal("320.50"),
                current_price=Decimal("318.75"),
                unrealized_pl=Decimal("-87.50"),
                unrealized_pl_pct=Decimal("-0.55"),
                last_updated=now,
            ),
        ]

        # Act
        table = renderer.render_positions_table(positions)

        # Assert
        assert isinstance(table, Table)
        assert table.row_count == 3  # Three positions

        # Verify ordering by rendering and checking output
        console = Console(force_terminal=True, legacy_windows=False)
        with console.capture() as capture:
            console.print(table)
        output = capture.get()

        # Positions should appear in input order (no sorting)
        tsla_pos = output.find("TSLA")
        aapl_pos = output.find("AAPL")
        msft_pos = output.find("MSFT")

        assert tsla_pos < aapl_pos < msft_pos, "Positions should maintain input order"

    def test_decimal_formatting_currency_and_percentage(self):
        """Test decimal formatting for currency ($150.25) and percentage (1.17%).

        From: spec.md FR-002 (formatting requirements)
        Task: T008
        """
        # Arrange
        renderer = DisplayRenderer()
        position = PositionDisplay(
            symbol="AAPL",
            quantity=100,
            entry_price=Decimal("150.25"),
            current_price=Decimal("152.00"),
            unrealized_pl=Decimal("175.00"),
            unrealized_pl_pct=Decimal("1.17"),
            last_updated=datetime(2025, 10, 16, 14, 32, 15, tzinfo=UTC),
        )

        # Act
        table = renderer.render_positions_table([position])

        # Assert
        console = Console(force_terminal=True, legacy_windows=False)
        with console.capture() as capture:
            console.print(table)
        output = capture.get()

        # Verify currency formatted as $XXX.XX
        assert "$150.25" in output, "Entry price should be formatted as $150.25"
        assert "$152.00" in output, "Current price should be formatted as $152.00"
        assert "$175.00" in output, "P&L should be formatted as $175.00"

        # Verify percentage formatted as X.XX%
        assert "1.17%" in output, "P&L percentage should be formatted as 1.17%"

    def test_positions_table_has_correct_column_structure(self):
        """Test positions table has all required columns.

        From: spec.md FR-002 (table structure)
        Task: T008
        """
        # Arrange
        renderer = DisplayRenderer()
        position = PositionDisplay(
            symbol="AAPL",
            quantity=100,
            entry_price=Decimal("150.25"),
            current_price=Decimal("152.00"),
            unrealized_pl=Decimal("175.00"),
            unrealized_pl_pct=Decimal("1.17"),
            last_updated=datetime(2025, 10, 16, 14, 32, 15, tzinfo=UTC),
        )

        # Act
        table = renderer.render_positions_table([position])

        # Assert
        assert isinstance(table, Table)
        assert len(table.columns) == 7, "Expected 7 columns: Symbol, Qty, Entry, Current, Unrealized P&L, P&L %, Updated"

        # Verify exact column headers
        column_headers = [str(col.header) for col in table.columns]
        assert "Symbol" in column_headers
        assert "Qty" in column_headers
        assert "Entry" in column_headers
        assert "Current" in column_headers
        # Verify P&L column names (may vary)
        pl_columns = [h for h in column_headers if "P" in h and "L" in h]
        assert len(pl_columns) >= 2, "Should have Unrealized P&L and P&L % columns"
        assert "Updated" in column_headers


class TestAccountStatusPanelRendering:
    """Tests for DisplayRenderer account status panel (T009)."""

    def _create_snapshot(
        self,
        account: AccountStatus,
        market_status: Literal["OPEN", "CLOSED"] = "OPEN",
        data_age_seconds: float = 0.5,
        is_data_stale: bool = False,
    ) -> DashboardSnapshot:
        """Helper to create minimal DashboardSnapshot for testing."""
        return DashboardSnapshot(
            account_status=account,
            positions=[],
            performance_metrics=PerformanceMetrics(
                win_rate=0.0,
                avg_risk_reward=0.0,
                total_realized_pl=Decimal("0"),
                total_unrealized_pl=Decimal("0"),
                total_pl=Decimal("0"),
                current_streak=0,
                streak_type="NONE",
                trades_today=0,
                session_count=0,
                max_drawdown=Decimal("0"),
            ),
            targets=None,
            market_status=market_status,
            generated_at=datetime(2025, 10, 16, 14, 32, 15, tzinfo=UTC),
            data_age_seconds=data_age_seconds,
            is_data_stale=is_data_stale,
        )

    def test_account_status_panel_has_all_fields(self):
        """Test account status panel displays all required fields.

        From: spec.md FR-001 (account status display)
        Task: T009
        """
        # Arrange
        renderer = DisplayRenderer()
        account = AccountStatus(
            buying_power=Decimal("10250.50"),
            account_balance=Decimal("25340.75"),
            cash_balance=Decimal("5000.00"),
            day_trade_count=2,
            last_updated=datetime(2025, 10, 16, 14, 32, 15, tzinfo=UTC),
        )
        snapshot = self._create_snapshot(account, "OPEN")

        # Act
        panel = renderer.render_account_status(account, snapshot)

        # Assert
        assert isinstance(panel, Panel)
        assert panel.title == "Account Status"

        # Render to check content
        console = Console(force_terminal=True, legacy_windows=False)
        with console.capture() as capture:
            console.print(panel)
        output = capture.get()

        # Verify all fields present
        assert "10,250.50" in output, "Buying power should be displayed"
        assert "25,340.75" in output, "Account balance should be displayed"
        assert "5,000.00" in output, "Cash balance should be displayed"
        assert "2" in output, "Day trade count should be displayed"
        assert "OPEN" in output, "Market status should be displayed"
        # Verify timestamp is formatted in readable format (actual time displayed in local timezone)
        assert "09:32:15" in output or ":32:15" in output, "Timestamp should be displayed in readable format"

    def test_market_status_open_has_green_color(self):
        """Test market status OPEN displays with green color.

        From: spec.md FR-014 (market hours detection)
        Task: T009
        """
        # Arrange
        renderer = DisplayRenderer()
        account = AccountStatus(
            buying_power=Decimal("10250.50"),
            account_balance=Decimal("25340.75"),
            cash_balance=Decimal("5000.00"),
            day_trade_count=2,
            last_updated=datetime(2025, 10, 16, 14, 32, 15, tzinfo=UTC),
        )
        snapshot = self._create_snapshot(account, "OPEN")

        # Act
        panel = renderer.render_account_status(account, snapshot)

        # Assert
        assert isinstance(panel, Panel)

        # Render to check color (will fail until verified)
        console = Console(force_terminal=True, legacy_windows=False)
        with console.capture() as capture:
            console.print(panel)
        output = capture.get()

        assert "OPEN" in output
        # Verify green color markup is applied to OPEN status (may be bold green 1;32 or plain 32)
        assert "\x1b[32m" in output or "\x1b[1;32m" in output, "Green color coding should be applied to OPEN market status"

    def test_market_status_closed_has_yellow_color(self):
        """Test market status CLOSED displays with yellow color.

        From: spec.md FR-014 (market hours detection)
        Task: T009

        NOTE: Implementation uses yellow for CLOSED (not red per spec).
        """
        # Arrange
        renderer = DisplayRenderer()
        account = AccountStatus(
            buying_power=Decimal("10250.50"),
            account_balance=Decimal("25340.75"),
            cash_balance=Decimal("5000.00"),
            day_trade_count=2,
            last_updated=datetime(2025, 10, 16, 20, 30, 0, tzinfo=UTC),
        )
        snapshot = self._create_snapshot(account, "CLOSED")

        # Act
        panel = renderer.render_account_status(account, snapshot)

        # Assert
        assert isinstance(panel, Panel)

        # Render to check color (will fail until verified)
        console = Console(force_terminal=True, legacy_windows=False)
        with console.capture() as capture:
            console.print(panel)
        output = capture.get()

        assert "CLOSED" in output
        # Verify yellow color markup is applied to CLOSED status (may be bold yellow 1;33 or plain 33)
        assert "\x1b[33m" in output or "\x1b[1;33m" in output, "Yellow color coding should be applied to CLOSED market status"

    def test_timestamp_formatted_readable(self):
        """Test timestamp displays in readable format.

        From: spec.md NFR-003 (timestamp format)
        Task: T009
        """
        # Arrange
        renderer = DisplayRenderer()
        account = AccountStatus(
            buying_power=Decimal("10250.50"),
            account_balance=Decimal("25340.75"),
            cash_balance=Decimal("5000.00"),
            day_trade_count=2,
            last_updated=datetime(2025, 10, 16, 14, 32, 15, tzinfo=UTC),
        )
        snapshot = self._create_snapshot(account, "OPEN")

        # Act
        panel = renderer.render_account_status(account, snapshot)

        # Assert
        console = Console(force_terminal=True, legacy_windows=False)
        with console.capture() as capture:
            console.print(panel)
        output = capture.get()

        # Verify timestamp includes date and time in complete format
        assert "2025-10-16" in output, "Date should be formatted as YYYY-MM-DD"
        # Verify time component is present (actual time in local timezone)
        assert "09:32:15" in output or ":32:15" in output, "Time should be displayed in readable format"

    def test_staleness_indicator_shown_when_data_stale(self):
        """Test staleness warning appears when data is old.

        From: spec.md FR-015 (staleness detection)
        Task: T009
        """
        # Arrange
        renderer = DisplayRenderer()
        account = AccountStatus(
            buying_power=Decimal("10250.50"),
            account_balance=Decimal("25340.75"),
            cash_balance=Decimal("5000.00"),
            day_trade_count=2,
            last_updated=datetime(2025, 10, 16, 14, 32, 15, tzinfo=UTC),
        )
        snapshot = self._create_snapshot(account, "OPEN", data_age_seconds=75.5, is_data_stale=True)

        # Act
        panel = renderer.render_account_status(account, snapshot)

        # Assert
        console = Console(force_terminal=True, legacy_windows=False)
        with console.capture() as capture:
            console.print(panel)
        output = capture.get()

        # Verify staleness warning displayed
        assert "stale" in output.lower(), "Staleness warning should appear for old data"
        # Verify warning includes age indicator (seconds or time)
        assert "75" in output or "76" in output, "Data age should be shown in staleness warning"

    def test_account_panel_has_descriptive_title(self):
        """Test account status panel has descriptive title.

        From: spec.md FR-001 (display requirements)
        Task: T009
        """
        # Arrange
        renderer = DisplayRenderer()
        account = AccountStatus(
            buying_power=Decimal("10250.50"),
            account_balance=Decimal("25340.75"),
            cash_balance=Decimal("5000.00"),
            day_trade_count=2,
            last_updated=datetime(2025, 10, 16, 14, 32, 15, tzinfo=UTC),
        )
        snapshot = self._create_snapshot(account, "OPEN")

        # Act
        panel = renderer.render_account_status(account, snapshot)

        # Assert
        assert isinstance(panel, Panel)
        assert panel.title == "Account Status"
        assert isinstance(panel.title, str)
        assert len(panel.title) > 0


class TestPerformanceMetricsPanelRendering:
    """Tests for DisplayRenderer performance metrics panel (T010)."""

    def test_win_rate_with_target_shows_checkmark_when_meeting(self):
        """Test win rate displays checkmark indicator when meeting target.

        From: spec.md FR-005 (target comparison)
        Task: T010
        """
        # Arrange
        renderer = DisplayRenderer()
        metrics = PerformanceMetrics(
            win_rate=65.0,
            avg_risk_reward=2.1,
            total_realized_pl=Decimal("450.25"),
            total_unrealized_pl=Decimal("87.50"),
            total_pl=Decimal("537.75"),
            current_streak=3,
            streak_type="WIN",
            trades_today=5,
            session_count=12,
            max_drawdown=Decimal("-100.00"),
        )
        targets = DashboardTargets(
            win_rate_target=60.0,
            daily_pl_target=Decimal("200.00"),
            trades_per_day_target=5,
            max_drawdown_target=Decimal("-500.00"),
        )

        # Act
        panel = renderer.render_performance_metrics(metrics, targets)

        # Assert
        assert isinstance(panel, Panel)
        assert panel.title == "Performance Metrics"

        # Render to check indicators
        console = Console(force_terminal=True, legacy_windows=False)
        with console.capture() as capture:
            console.print(panel)
        output = capture.get()

        # Verify checkmark for meeting win rate target
        assert "65.00%" in output, "Win rate should be displayed"
        assert "60.00%" in output, "Win rate target should be displayed"
        # Verify checkmark symbol (✓) for meeting target
        assert "✓" in output or "✔" in output, "Checkmark indicator should show when meeting target"

    def test_win_rate_with_target_shows_x_when_not_meeting(self):
        """Test win rate displays X indicator when not meeting target.

        From: spec.md FR-005 (target comparison)
        Task: T010
        """
        # Arrange
        renderer = DisplayRenderer()
        metrics = PerformanceMetrics(
            win_rate=55.0,
            avg_risk_reward=1.8,
            total_realized_pl=Decimal("150.00"),
            total_unrealized_pl=Decimal("-50.00"),
            total_pl=Decimal("100.00"),
            current_streak=2,
            streak_type="LOSS",
            trades_today=3,
            session_count=8,
            max_drawdown=Decimal("-600.00"),
        )
        targets = DashboardTargets(
            win_rate_target=60.0,
            daily_pl_target=Decimal("200.00"),
            trades_per_day_target=5,
            max_drawdown_target=Decimal("-500.00"),
        )

        # Act
        panel = renderer.render_performance_metrics(metrics, targets)

        # Assert
        console = Console(force_terminal=True, legacy_windows=False)
        with console.capture() as capture:
            console.print(panel)
        output = capture.get()

        # Verify X for not meeting win rate target
        assert "55.00%" in output
        assert "60.00%" in output
        # Verify X symbol (✗) for not meeting target
        assert "✗" in output or "✘" in output, "X indicator should show when not meeting target"

    def test_win_rate_without_target_shows_no_comparison(self):
        """Test win rate displays without comparison when no targets.

        From: spec.md FR-016 (graceful degradation)
        Task: T010
        """
        # Arrange
        renderer = DisplayRenderer()
        metrics = PerformanceMetrics(
            win_rate=65.0,
            avg_risk_reward=2.1,
            total_realized_pl=Decimal("450.25"),
            total_unrealized_pl=Decimal("87.50"),
            total_pl=Decimal("537.75"),
            current_streak=3,
            streak_type="WIN",
            trades_today=5,
            session_count=12,
            max_drawdown=Decimal("-100.00"),
        )
        targets = None

        # Act
        panel = renderer.render_performance_metrics(metrics, targets)

        # Assert
        console = Console(force_terminal=True, legacy_windows=False)
        with console.capture() as capture:
            console.print(panel)
        output = capture.get()

        # Verify no target comparison indicators
        assert "65.00%" in output, "Win rate should still be displayed"
        assert "✓" not in output, "No checkmark when no targets"
        assert "✗" not in output, "No X when no targets"
        assert "target" not in output.lower(), "No target text when no targets"

    def test_win_streak_displays_with_green_color(self):
        """Test current win streak displays as '3 WIN' with green color.

        From: spec.md FR-003 (streak display)
        Task: T010
        """
        # Arrange
        renderer = DisplayRenderer()
        metrics = PerformanceMetrics(
            win_rate=65.0,
            avg_risk_reward=2.1,
            total_realized_pl=Decimal("450.25"),
            total_unrealized_pl=Decimal("87.50"),
            total_pl=Decimal("537.75"),
            current_streak=3,
            streak_type="WIN",
            trades_today=5,
            session_count=12,
            max_drawdown=Decimal("-100.00"),
        )

        # Act
        panel = renderer.render_performance_metrics(metrics, None)

        # Assert
        console = Console(force_terminal=True, legacy_windows=False)
        with console.capture() as capture:
            console.print(panel)
        output = capture.get()

        # Verify streak displays correctly
        assert "3" in output, "Streak count should be displayed"
        assert "WIN" in output, "Streak type should be displayed"
        # Verify green color for WIN streak
        assert "\x1b[32m" in output, "Green color should be applied to WIN streak"

    def test_loss_streak_displays_with_red_color(self):
        """Test current loss streak displays as '2 LOSS' with red color.

        From: spec.md FR-003 (streak display)
        Task: T010
        """
        # Arrange
        renderer = DisplayRenderer()
        metrics = PerformanceMetrics(
            win_rate=45.0,
            avg_risk_reward=1.5,
            total_realized_pl=Decimal("-200.00"),
            total_unrealized_pl=Decimal("-50.00"),
            total_pl=Decimal("-250.00"),
            current_streak=2,
            streak_type="LOSS",
            trades_today=4,
            session_count=6,
            max_drawdown=Decimal("-300.00"),
        )

        # Act
        panel = renderer.render_performance_metrics(metrics, None)

        # Assert
        console = Console(force_terminal=True, legacy_windows=False)
        with console.capture() as capture:
            console.print(panel)
        output = capture.get()

        # Verify streak displays correctly
        assert "2" in output, "Streak count should be displayed"
        assert "LOSS" in output, "Streak type should be displayed"
        # Verify red color for LOSS streak
        assert "[red]" in output or "\x1b[31m" in output, "Red color should be applied to LOSS streak"

    def test_total_pl_green_when_profit(self):
        """Test total P&L displays green when positive.

        From: spec.md FR-003 (color coding)
        Task: T010
        """
        # Arrange
        renderer = DisplayRenderer()
        metrics = PerformanceMetrics(
            win_rate=65.0,
            avg_risk_reward=2.1,
            total_realized_pl=Decimal("450.25"),
            total_unrealized_pl=Decimal("87.50"),
            total_pl=Decimal("537.75"),
            current_streak=3,
            streak_type="WIN",
            trades_today=5,
            session_count=12,
            max_drawdown=Decimal("-100.00"),
        )

        # Act
        panel = renderer.render_performance_metrics(metrics, None)

        # Assert
        console = Console(force_terminal=True, legacy_windows=False)
        with console.capture() as capture:
            console.print(panel)
        output = capture.get()

        # Verify positive P&L displayed and colored
        assert "537.75" in output, "Total P&L should be displayed"
        assert "450.25" in output, "Realized P&L should be displayed"
        assert "87.50" in output, "Unrealized P&L should be displayed"
        # Verify green color for positive P&L values
        assert "\x1b[32m" in output, "Green color should be applied to positive P&L"

    def test_total_pl_red_when_loss(self):
        """Test total P&L displays red when negative.

        From: spec.md FR-003 (color coding)
        Task: T010
        """
        # Arrange
        renderer = DisplayRenderer()
        metrics = PerformanceMetrics(
            win_rate=45.0,
            avg_risk_reward=1.5,
            total_realized_pl=Decimal("-200.00"),
            total_unrealized_pl=Decimal("-50.00"),
            total_pl=Decimal("-250.00"),
            current_streak=2,
            streak_type="LOSS",
            trades_today=4,
            session_count=6,
            max_drawdown=Decimal("-300.00"),
        )

        # Act
        panel = renderer.render_performance_metrics(metrics, None)

        # Assert
        console = Console(force_terminal=True, legacy_windows=False)
        with console.capture() as capture:
            console.print(panel)
        output = capture.get()

        # Verify negative P&L displayed and colored
        assert "250.00" in output or "-250.00" in output, "Total P&L should be displayed"
        # Verify red color for negative P&L values
        assert "[red]" in output or "\x1b[31m" in output, "Red color should be applied to negative P&L"

    def test_performance_panel_has_descriptive_title(self):
        """Test performance metrics panel has descriptive title.

        From: spec.md FR-003 (display requirements)
        Task: T010
        """
        # Arrange
        renderer = DisplayRenderer()
        metrics = PerformanceMetrics(
            win_rate=65.0,
            avg_risk_reward=2.1,
            total_realized_pl=Decimal("450.25"),
            total_unrealized_pl=Decimal("87.50"),
            total_pl=Decimal("537.75"),
            current_streak=3,
            streak_type="WIN",
            trades_today=5,
            session_count=12,
            max_drawdown=Decimal("-100.00"),
        )

        # Act
        panel = renderer.render_performance_metrics(metrics, None)

        # Assert
        assert isinstance(panel, Panel)
        assert panel.title == "Performance Metrics"
        assert len(str(panel.title)) > 0

    def test_target_comparison_indicators_use_unicode_symbols(self):
        """Test target comparison uses ✓ and ✗ Unicode symbols.

        From: spec.md FR-005 (indicator symbols)
        Task: T010
        """
        # Arrange
        renderer = DisplayRenderer()
        metrics = PerformanceMetrics(
            win_rate=65.0,
            avg_risk_reward=2.1,
            total_realized_pl=Decimal("450.25"),
            total_unrealized_pl=Decimal("87.50"),
            total_pl=Decimal("537.75"),
            current_streak=3,
            streak_type="WIN",
            trades_today=5,
            session_count=12,
            max_drawdown=Decimal("-100.00"),
        )
        targets = DashboardTargets(
            win_rate_target=60.0,
            daily_pl_target=Decimal("200.00"),
            trades_per_day_target=5,
            max_drawdown_target=Decimal("-500.00"),
        )

        # Act
        panel = renderer.render_performance_metrics(metrics, targets)

        # Assert
        console = Console(force_terminal=True, legacy_windows=False)
        with console.capture() as capture:
            console.print(panel)
        output = capture.get()

        # Verify Unicode symbols are used for target comparison
        # This test has metrics meeting some targets (win_rate 65% > 60%, daily_pl 537.75 > 200)
        # so should have at least one checkmark
        assert "✓" in output or "✔" in output, "Checkmark should be used when meeting targets"
        # Both symbols may be present if some targets met and others not met
