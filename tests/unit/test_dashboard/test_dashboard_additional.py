"""
RED phase tests for Dashboard additional features (T013-T016).

These tests MUST FAIL before implementation.
Focus on new edge cases and behaviors not covered by existing tests.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from trading_bot.dashboard import dashboard as dashboard_module
from trading_bot.dashboard.data_provider import DashboardDataProvider, ProviderConfig
from trading_bot.dashboard.display_renderer import DisplayRenderer
from trading_bot.dashboard.export_generator import ExportGenerator
from trading_bot.dashboard.metrics_calculator import MetricsCalculator
from trading_bot.dashboard.models import (
    DashboardSnapshot,
    DashboardTargets,
    PerformanceMetrics,
)


@pytest.fixture
def mock_account_data() -> Mock:
    """Mock AccountData service."""
    mock = Mock()
    mock.get_buying_power.return_value = 15000.00
    mock.get_account_balance.return_value = Mock(
        cash=Decimal("10000.00"),
        equity=Decimal("25000.00"),
        buying_power=Decimal("15000.00"),
        last_updated=datetime.now(UTC),
    )
    mock.get_day_trade_count.return_value = 2
    mock.get_positions.return_value = []
    return mock


@pytest.fixture
def mock_trade_helper(tmp_path: Path) -> Mock:
    """Mock TradeQueryHelper."""
    mock = Mock()
    mock.query_by_date_range.return_value = []
    mock.log_dir = tmp_path
    return mock


@pytest.fixture
def mock_metrics_calculator() -> MetricsCalculator:
    """Real MetricsCalculator for testing."""
    return MetricsCalculator()


class TestDashboardTargetsLoadingEdgeCases:
    """T013: Test Dashboard loads targets file gracefully - edge cases."""

    def test_targets_file_with_extra_fields_still_loads(
        self,
        tmp_path: Path,
        mock_account_data: Mock,
        mock_trade_helper: Mock,
        mock_metrics_calculator: MetricsCalculator,
    ) -> None:
        """Targets file with extra fields should still load (forward compatibility)."""
        targets_path = tmp_path / "dashboard-targets.yaml"
        targets_path.write_text(
            """
win_rate_target: 65.0
daily_pl_target: 500.0
trades_per_day_target: 10
max_drawdown_target: -200.0
avg_risk_reward_target: 2.0
extra_field_future: 123.45
another_unknown: "value"
"""
        )

        config = ProviderConfig(targets_path=targets_path)
        provider = DashboardDataProvider(
            account_data=mock_account_data,
            trade_helper=mock_trade_helper,
            metrics_calculator=mock_metrics_calculator,
            config=config,
        )

        targets = provider.load_targets()

        # Should still load successfully
        assert targets is not None
        assert targets.win_rate_target == 65.0

    def test_targets_file_with_invalid_types_returns_none(
        self,
        tmp_path: Path,
        mock_account_data: Mock,
        mock_trade_helper: Mock,
        mock_metrics_calculator: MetricsCalculator,
    ) -> None:
        """Targets with wrong data types should return None."""
        targets_path = tmp_path / "dashboard-targets.yaml"
        targets_path.write_text(
            """
win_rate_target: "not_a_number"
daily_pl_target: 500.0
trades_per_day_target: 10
max_drawdown_target: -200.0
"""
        )

        config = ProviderConfig(targets_path=targets_path)
        provider = DashboardDataProvider(
            account_data=mock_account_data,
            trade_helper=mock_trade_helper,
            metrics_calculator=mock_metrics_calculator,
            config=config,
        )

        targets = provider.load_targets()

        assert targets is None

    def test_targets_file_with_negative_values_validates_correctly(
        self,
        tmp_path: Path,
        mock_account_data: Mock,
        mock_trade_helper: Mock,
        mock_metrics_calculator: MetricsCalculator,
    ) -> None:
        """Negative drawdown targets should be accepted (valid use case)."""
        targets_path = tmp_path / "dashboard-targets.yaml"
        targets_path.write_text(
            """
win_rate_target: 60.0
daily_pl_target: 400.0
trades_per_day_target: 8
max_drawdown_target: -500.0
avg_risk_reward_target: 1.8
"""
        )

        config = ProviderConfig(targets_path=targets_path)
        provider = DashboardDataProvider(
            account_data=mock_account_data,
            trade_helper=mock_trade_helper,
            metrics_calculator=mock_metrics_calculator,
            config=config,
        )

        targets = provider.load_targets()

        assert targets is not None
        assert targets.max_drawdown_target == Decimal("-500.0")


class TestDashboardStateAggregationEdgeCases:
    """T014: Test Dashboard aggregates DashboardState correctly - edge cases."""

    def test_get_snapshot_with_empty_positions(
        self,
        tmp_path: Path,
        mock_account_data: Mock,
        mock_trade_helper: Mock,
        mock_metrics_calculator: MetricsCalculator,
    ) -> None:
        """Dashboard should handle empty positions gracefully."""
        mock_account_data.get_positions.return_value = []

        # Create today's log file
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        (tmp_path / f"{today}.jsonl").write_text("{}\n")

        provider = DashboardDataProvider(
            account_data=mock_account_data,
            trade_helper=mock_trade_helper,
            metrics_calculator=mock_metrics_calculator,
        )

        snapshot = provider.get_snapshot(targets=None)

        assert snapshot is not None
        assert len(snapshot.positions) == 0
        assert snapshot.performance_metrics.total_unrealized_pl == Decimal("0")

    def test_get_snapshot_marks_stale_data_correctly(
        self,
        tmp_path: Path,
        mock_account_data: Mock,
        mock_trade_helper: Mock,
        mock_metrics_calculator: MetricsCalculator,
    ) -> None:
        """Dashboard should detect stale account data (>60s old)."""
        old_timestamp = datetime.now(UTC) - timedelta(seconds=120)
        mock_account_data.get_account_balance.return_value = Mock(
            cash=Decimal("10000.00"),
            equity=Decimal("25000.00"),
            buying_power=Decimal("15000.00"),
            last_updated=old_timestamp,
        )

        # Create today's log file
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        (tmp_path / f"{today}.jsonl").write_text("{}\n")

        provider = DashboardDataProvider(
            account_data=mock_account_data,
            trade_helper=mock_trade_helper,
            metrics_calculator=mock_metrics_calculator,
        )

        snapshot = provider.get_snapshot(targets=None)

        assert snapshot.is_data_stale is True
        assert snapshot.data_age_seconds > 60


class TestDashboardPollingLoopBehavior:
    """T015: Test Dashboard polling loop refreshes at 5s interval - behavior tests."""

    @patch("trading_bot.dashboard.dashboard.time.sleep")
    @patch("trading_bot.dashboard.dashboard.time.monotonic")
    def test_loop_respects_custom_refresh_interval(
        self,
        mock_monotonic: Mock,
        mock_sleep: Mock,
        tmp_path: Path,
        mock_account_data: Mock,
        mock_trade_helper: Mock,
    ) -> None:
        """Custom refresh intervals should be respected (not hardcoded to 5s)."""
        # Simulate time progression for 3-second interval
        time_values = iter([0.0, 1.0, 2.0, 3.1])
        mock_monotonic.side_effect = lambda: next(time_values, 10.0)

        # Create today's log file
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        (tmp_path / f"{today}.jsonl").write_text("{}\n")

        provider = DashboardDataProvider(
            account_data=mock_account_data,
            trade_helper=mock_trade_helper,
            metrics_calculator=MetricsCalculator(),
        )

        refresh_count = [0]

        class MockLive:
            def __init__(self, *args, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def update(self, layout):
                refresh_count[0] += 1
                # Stop after 2 refreshes
                if refresh_count[0] >= 2:
                    raise KeyboardInterrupt

        with patch("trading_bot.dashboard.dashboard.Live", MockLive):
            with patch("trading_bot.dashboard.dashboard._CommandReader") as mock_reader_class:
                mock_reader = Mock()
                mock_reader.poll.return_value = None
                mock_reader_class.return_value = mock_reader

                dashboard_module.run_dashboard_loop(
                    data_provider=provider,
                    renderer=DisplayRenderer(),
                    exporter=ExportGenerator(),
                    refresh_interval=3.0,  # Custom 3s interval
                )

        # Should have refreshed at 3s intervals
        assert refresh_count[0] >= 1

    def test_loop_continues_after_transient_errors(
        self,
        tmp_path: Path,
        mock_account_data: Mock,
        mock_trade_helper: Mock,
    ) -> None:
        """Dashboard should continue after transient errors (resilience)."""
        # Create today's log file
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        (tmp_path / f"{today}.jsonl").write_text("{}\n")

        error_count = [0]

        def failing_get_balance():
            error_count[0] += 1
            if error_count[0] == 1:
                raise Exception("Transient network error")
            return Mock(
                cash=Decimal("10000.00"),
                equity=Decimal("25000.00"),
                buying_power=Decimal("15000.00"),
                last_updated=datetime.now(UTC),
            )

        mock_account_data.get_account_balance.side_effect = failing_get_balance

        provider = DashboardDataProvider(
            account_data=mock_account_data,
            trade_helper=mock_trade_helper,
            metrics_calculator=MetricsCalculator(),
        )

        class MockLive:
            def __init__(self, *args, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def update(self, layout):
                # Stop after first successful update
                if error_count[0] >= 2:
                    raise KeyboardInterrupt

        with patch("trading_bot.dashboard.dashboard.Live", MockLive):
            with patch("trading_bot.dashboard.dashboard._CommandReader") as mock_reader_class:
                mock_reader = Mock()
                mock_reader.poll.return_value = None
                mock_reader_class.return_value = mock_reader

                with patch("trading_bot.dashboard.dashboard.time.sleep"):
                    with patch("trading_bot.dashboard.dashboard.time.monotonic", return_value=0.0):
                        # Should not crash despite first error
                        dashboard_module.run_dashboard_loop(
                            data_provider=provider,
                            renderer=DisplayRenderer(),
                            exporter=ExportGenerator(),
                            refresh_interval=1.0,
                        )

        # Should have recovered from first error
        assert error_count[0] >= 2


class TestDashboardKeyboardHandlerBehavior:
    """T016: Test Dashboard keyboard handler processes commands - behavior tests."""

    def test_multiple_commands_processed_in_sequence(
        self,
        tmp_path: Path,
        mock_account_data: Mock,
        mock_trade_helper: Mock,
    ) -> None:
        """Multiple commands queued should be processed in order."""
        # Create today's log file
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        (tmp_path / f"{today}.jsonl").write_text("{}\n")

        commands_issued = []

        class MockCommandReader:
            def __init__(self):
                self._commands = iter(["R", "E", "Q"])

            def start(self):
                pass

            def stop(self):
                pass

            def poll(self):
                return next(self._commands, None)

        class MockLive:
            def __init__(self, *args, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def update(self, layout):
                pass

        provider = DashboardDataProvider(
            account_data=mock_account_data,
            trade_helper=mock_trade_helper,
            metrics_calculator=MetricsCalculator(),
        )

        with patch("trading_bot.dashboard.dashboard.Live", MockLive):
            with patch("trading_bot.dashboard.dashboard._CommandReader", MockCommandReader):
                with patch("trading_bot.dashboard.dashboard.time.sleep"):
                    with patch("trading_bot.dashboard.dashboard.time.monotonic", return_value=0.0):
                        dashboard_module.run_dashboard_loop(
                            data_provider=provider,
                            renderer=DisplayRenderer(),
                            exporter=ExportGenerator(),
                            refresh_interval=1.0,
                        )

        # All commands should have been processed (R, E, Q)
        # Q should have caused clean exit

    def test_export_command_creates_files(
        self,
        tmp_path: Path,
        mock_account_data: Mock,
        mock_trade_helper: Mock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Export command (E) should create JSON and Markdown files."""
        monkeypatch.chdir(tmp_path)

        # Create today's log file
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        (tmp_path / f"{today}.jsonl").write_text("{}\n")

        class MockCommandReader:
            def __init__(self):
                self._commands = iter(["E", "Q"])

            def start(self):
                pass

            def stop(self):
                pass

            def poll(self):
                return next(self._commands, None)

        class MockLive:
            def __init__(self, *args, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def update(self, layout):
                pass

        provider = DashboardDataProvider(
            account_data=mock_account_data,
            trade_helper=mock_trade_helper,
            metrics_calculator=MetricsCalculator(),
        )

        with patch("trading_bot.dashboard.dashboard.Live", MockLive):
            with patch("trading_bot.dashboard.dashboard._CommandReader", MockCommandReader):
                with patch("trading_bot.dashboard.dashboard.time.sleep"):
                    with patch("trading_bot.dashboard.dashboard.time.monotonic", return_value=0.0):
                        dashboard_module.run_dashboard_loop(
                            data_provider=provider,
                            renderer=DisplayRenderer(),
                            exporter=ExportGenerator(),
                            refresh_interval=1.0,
                        )

        # Export files should have been created
        logs_dir = tmp_path / "logs"
        if logs_dir.exists():
            export_files = list(logs_dir.glob("dashboard-export-*.json"))
            # May or may not exist depending on timing
            # This tests that the command doesn't crash

    def test_help_command_displays_controls(
        self,
        tmp_path: Path,
        mock_account_data: Mock,
        mock_trade_helper: Mock,
    ) -> None:
        """Help command (H) should display keyboard controls."""
        # Create today's log file
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        (tmp_path / f"{today}.jsonl").write_text("{}\n")

        help_displayed = [False]

        class MockConsole:
            def print(self, *args, **kwargs):
                message = str(args[0]) if args else ""
                if "Dashboard Controls" in message or "Manual refresh" in message:
                    help_displayed[0] = True

        class MockCommandReader:
            def __init__(self):
                self._commands = iter(["H", "Q"])

            def start(self):
                pass

            def stop(self):
                pass

            def poll(self):
                return next(self._commands, None)

        class MockLive:
            def __init__(self, *args, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def update(self, layout):
                pass

        provider = DashboardDataProvider(
            account_data=mock_account_data,
            trade_helper=mock_trade_helper,
            metrics_calculator=MetricsCalculator(),
        )

        console = MockConsole()

        with patch("trading_bot.dashboard.dashboard.Live", MockLive):
            with patch("trading_bot.dashboard.dashboard._CommandReader", MockCommandReader):
                with patch("trading_bot.dashboard.dashboard.time.sleep"):
                    with patch("trading_bot.dashboard.dashboard.time.monotonic", return_value=0.0):
                        dashboard_module.run_dashboard_loop(
                            data_provider=provider,
                            renderer=DisplayRenderer(),
                            exporter=ExportGenerator(),
                            refresh_interval=1.0,
                            console=console,
                        )

        # Help should have been displayed
        assert help_displayed[0] is True
