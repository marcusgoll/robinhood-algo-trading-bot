"""Unit tests for dashboard data provider, rendering, and exports."""

from __future__ import annotations

import itertools
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

import json
import pytest
from rich.console import Console
from rich.text import Text

import trading_bot.dashboard.dashboard as dashboard
from trading_bot.account.account_data import AccountBalance, Position
from trading_bot.dashboard.data_provider import DashboardDataProvider, ProviderConfig
from trading_bot.dashboard.display_renderer import DisplayRenderer
from trading_bot.dashboard.export_generator import ExportGenerator
from trading_bot.dashboard.metrics_calculator import MetricsCalculator
from trading_bot.dashboard.models import (
    AccountStatus,
    DashboardSnapshot,
    DashboardTargets,
    PerformanceMetrics,
    PositionDisplay,
)
from trading_bot.dashboard.dashboard import log_dashboard_event
from trading_bot.logging.trade_record import TradeRecord


@pytest.fixture
def metrics_calculator() -> MetricsCalculator:
    return MetricsCalculator()


def _make_snapshot(
    *,
    generated_at: datetime,
    stale: bool = False,
    warnings: list[str] | None = None,
    targets: DashboardTargets | None = None,
) -> DashboardSnapshot:
    """Helper to build a dashboard snapshot with sensible defaults."""
    account = AccountStatus(
        buying_power=Decimal("15000.00"),
        account_balance=Decimal("20000.00"),
        cash_balance=Decimal("5000.00"),
        day_trade_count=1,
        last_updated=generated_at if not stale else generated_at - timedelta(seconds=120),
    )
    positions = [
        PositionDisplay(
            symbol="AAPL",
            quantity=25,
            entry_price=Decimal("150.00"),
            current_price=Decimal("151.50"),
            unrealized_pl=Decimal("37.50"),
            unrealized_pl_pct=Decimal("1.00"),
            last_updated=generated_at,
        )
    ]
    metrics = PerformanceMetrics(
        win_rate=65.0,
        avg_risk_reward=1.8,
        total_realized_pl=Decimal("320.00"),
        total_unrealized_pl=Decimal("37.50"),
        total_pl=Decimal("357.50"),
        current_streak=2,
        streak_type="WIN",
        trades_today=3,
        session_count=9,
        max_drawdown=Decimal("-120.00"),
    )
    return DashboardSnapshot(
        account_status=account,
        positions=positions,
        performance_metrics=metrics,
        targets=targets,
        market_status="OPEN",
        generated_at=generated_at,
        data_age_seconds=0 if not stale else 120,
        is_data_stale=stale,
        warnings=warnings or [],
    )


class TestDashboardDataProviderLoadTargets:
    """Validate configuration loader behaviour."""

    def _provider(self, tmp_path: Path, metrics_calculator: MetricsCalculator) -> DashboardDataProvider:
        account_data = MagicMock()
        trade_helper = MagicMock()
        trade_helper.log_dir = tmp_path
        return DashboardDataProvider(
            account_data=account_data,
            trade_helper=trade_helper,
            metrics_calculator=metrics_calculator,
            config=ProviderConfig(targets_path=tmp_path / "dashboard-targets.yaml"),
        )

    def test_load_valid_config(self, tmp_path: Path, metrics_calculator: MetricsCalculator) -> None:
        config_path = tmp_path / "dashboard-targets.yaml"
        config_path.write_text(
            """
win_rate_target: 60.0
daily_pl_target: 500.0
trades_per_day_target: 5
max_drawdown_target: -250.0
avg_risk_reward_target: 2.0
"""
        )

        provider = self._provider(tmp_path, metrics_calculator)
        targets = provider.load_targets()

        assert targets is not None
        assert targets.win_rate_target == pytest.approx(60.0)
        assert targets.daily_pl_target == Decimal("500.0")
        assert targets.trades_per_day_target == 5
        assert targets.max_drawdown_target == Decimal("-250.0")
        assert targets.avg_risk_reward_target == pytest.approx(2.0)

    def test_load_missing_file_returns_none(self, tmp_path: Path, metrics_calculator: MetricsCalculator) -> None:
        provider = self._provider(tmp_path, metrics_calculator)
        assert provider.load_targets() is None

    def test_load_invalid_yaml(self, tmp_path: Path, metrics_calculator: MetricsCalculator) -> None:
        config_path = tmp_path / "dashboard-targets.yaml"
        config_path.write_text("invalid: yaml: [")
        provider = self._provider(tmp_path, metrics_calculator)
        assert provider.load_targets() is None

    def test_load_missing_required_fields(self, tmp_path: Path, metrics_calculator: MetricsCalculator) -> None:
        config_path = tmp_path / "dashboard-targets.yaml"
        config_path.write_text(
            """
win_rate_target: 55.0
daily_pl_target: 400.0
# trades_per_day_target missing
"""
        )
        provider = self._provider(tmp_path, metrics_calculator)
        assert provider.load_targets() is None

    def test_load_invalid_numeric_values(self, tmp_path: Path, metrics_calculator: MetricsCalculator) -> None:
        config_path = tmp_path / "dashboard-targets.yaml"
        config_path.write_text(
            """
win_rate_target: invalid
daily_pl_target: 500.0
trades_per_day_target: 10
max_drawdown_target: -200.0
avg_risk_reward_target: 2.0
"""
        )
        provider = self._provider(tmp_path, metrics_calculator)
        assert provider.load_targets() is None

    def test_load_targets_generic_exception(
        self,
        tmp_path: Path,
        metrics_calculator: MetricsCalculator,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        config_path = tmp_path / "dashboard-targets.yaml"
        config_path.write_text(
            """
win_rate_target: 60.0
daily_pl_target: 500.0
trades_per_day_target: 10
max_drawdown_target: -200.0
avg_risk_reward_target: 2.0
"""
        )
        provider = self._provider(tmp_path, metrics_calculator)

        class ExplodingTargets:
            def __init__(self, *args, **kwargs):
                raise RuntimeError("boom")

        monkeypatch.setattr(
            "trading_bot.dashboard.data_provider.DashboardTargets", ExplodingTargets
        )
        assert provider.load_targets() is None


class TestDashboardDataProviderSnapshot:
    """Ensure snapshot aggregation combines account, positions, and metrics."""

    def _sample_trade(self) -> TradeRecord:
        now_iso = datetime.now(UTC).isoformat()
        return TradeRecord(
            timestamp=now_iso,
            symbol="AAPL",
            action="SELL",
            quantity=50,
            price=Decimal("155.00"),
            total_value=Decimal("7750.00"),
            order_id="order-1",
            execution_mode="PAPER",
            account_id=None,
            strategy_name="test",
            entry_type="breakout",
            stop_loss=Decimal("150.00"),
            target=Decimal("160.00"),
            decision_reasoning="Test case",
            indicators_used=["VWAP"],
            risk_reward_ratio=2.0,
            outcome="win",
            profit_loss=Decimal("250.00"),
            hold_duration_seconds=360,
            exit_timestamp=now_iso,
            exit_reasoning="Target hit",
            slippage=Decimal("0"),
            commission=Decimal("0"),
            net_profit_loss=Decimal("250.00"),
            session_id="session-1",
            bot_version="1.0.0",
            config_hash="abc123",
        )

    def test_get_snapshot_aggregates_data(self, tmp_path: Path, metrics_calculator: MetricsCalculator) -> None:
        account_balance = AccountBalance(
            cash=Decimal("10000.00"),
            equity=Decimal("15000.00"),
            buying_power=Decimal("20000.00"),
            last_updated=datetime.now(UTC) - timedelta(seconds=10),
        )

        position = Position(
            symbol="AAPL",
            quantity=100,
            average_buy_price=Decimal("150.00"),
            current_price=Decimal("155.00"),
            last_updated=datetime.now(UTC),
        )

        account_data = MagicMock()
        account_data.get_account_balance.return_value = account_balance
        account_data.get_buying_power.return_value = 20000.0
        account_data.get_day_trade_count.return_value = 2
        account_data.get_positions.return_value = [position]

        trade_helper = MagicMock()
        trade_helper.log_dir = tmp_path
        trade_helper.query_by_date_range.return_value = [self._sample_trade()]

        # Create today's log file to avoid missing-log warning
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        (tmp_path / f"{today}.jsonl").write_text("{}\n")

        provider = DashboardDataProvider(
            account_data=account_data,
            trade_helper=trade_helper,
            metrics_calculator=metrics_calculator,
        )

        targets = DashboardTargets(
            win_rate_target=60.0,
            daily_pl_target=Decimal("500.0"),
            trades_per_day_target=5,
            max_drawdown_target=Decimal("-300.0"),
            avg_risk_reward_target=2.0,
        )

        snapshot = provider.get_snapshot(targets)

        assert snapshot.account_status.buying_power == Decimal("20000.0")
        assert snapshot.account_status.day_trade_count == 2
        assert len(snapshot.positions) == 1
        assert snapshot.positions[0].symbol == "AAPL"
        assert snapshot.performance_metrics.total_realized_pl == Decimal("250.00")
        assert snapshot.performance_metrics.max_drawdown <= Decimal("0")
        assert snapshot.market_status in {"OPEN", "CLOSED"}
        assert not snapshot.is_data_stale
        assert snapshot.targets == targets
        assert snapshot.warnings == []

    def test_snapshot_warns_when_log_missing(self, tmp_path: Path, metrics_calculator: MetricsCalculator) -> None:
        account_balance = AccountBalance(
            cash=Decimal("5000.00"),
            equity=Decimal("8000.00"),
            buying_power=Decimal("12000.00"),
            last_updated=datetime.now(UTC),
        )

        account_data = MagicMock()
        account_data.get_account_balance.return_value = account_balance
        account_data.get_buying_power.return_value = 12000.0
        account_data.get_day_trade_count.return_value = 0
        account_data.get_positions.return_value = []

        trade_helper = MagicMock()
        trade_helper.log_dir = tmp_path
        trade_helper.query_by_date_range.return_value = []

        provider = DashboardDataProvider(
            account_data=account_data,
            trade_helper=trade_helper,
            metrics_calculator=metrics_calculator,
        )

        snapshot = provider.get_snapshot(targets=None)

        assert snapshot.warnings
        assert any("Trade log" in warning for warning in snapshot.warnings)


class TestDisplayRenderer:
    """Smoke tests for Rich rendering of snapshot data."""

    @pytest.fixture
    def sample_snapshot(self) -> DashboardSnapshot:
        generated_at = datetime.now(UTC)
        targets = DashboardTargets(
            win_rate_target=70.0,
            daily_pl_target=Decimal("400.0"),
            trades_per_day_target=3,
            max_drawdown_target=Decimal("-200.0"),
            avg_risk_reward_target=2.0,
        )
        return _make_snapshot(
            generated_at=generated_at,
            stale=False,
            warnings=["Initial warning"],
            targets=targets,
        )

    def test_render_full_dashboard_returns_layout(self, sample_snapshot: DashboardSnapshot) -> None:
        renderer = DisplayRenderer()
        layout = renderer.render_full_dashboard(sample_snapshot)

        assert layout is not None
        assert {child.name for child in layout.children if child.name} >= {"body", "header"}

    def test_render_accounts_with_stale_indicator(self) -> None:
        generated_at = datetime.now(UTC)
        snapshot = _make_snapshot(
            generated_at=generated_at,
            stale=True,
            warnings=["Trade log missing"],
        )
        renderer = DisplayRenderer()
        layout = renderer.render_full_dashboard(snapshot)

        warnings_panel = layout["warnings"]
        rendered = warnings_panel.renderable.renderable
        assert isinstance(rendered, Text)
        assert "Trade log missing" in rendered.plain

        account_panel = layout["body"]["account"].renderable
        account_text = str(account_panel.renderable)
        assert "Data may be stale" in account_text


class TestExportGenerator:
    """Verify JSON and Markdown exports."""

    @pytest.fixture
    def snapshot(self) -> DashboardSnapshot:
        generated_at = datetime.now(UTC)
        targets = DashboardTargets(
            win_rate_target=60.0,
            daily_pl_target=Decimal("200.0"),
            trades_per_day_target=2,
            max_drawdown_target=Decimal("-150.0"),
            avg_risk_reward_target=1.5,
        )
        return _make_snapshot(
            generated_at=generated_at,
            stale=True,
            warnings=["Test warning"],
            targets=targets,
        )

    def test_export_to_json_and_markdown(
        self,
        tmp_path: Path,
        snapshot: DashboardSnapshot,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        generator = ExportGenerator()
        monkeypatch.chdir(tmp_path)

        json_path = tmp_path / "dashboard.json"
        md_path = tmp_path / "dashboard.md"

        generator.export_to_json(snapshot, json_path)
        generator.export_to_markdown(snapshot, md_path)

        json_data = json.loads(json_path.read_text())
        assert json_data["market_status"] == "OPEN"
        assert json_data["performance_metrics"]["total_pl"] == str(snapshot.performance_metrics.total_pl)

        md_content = md_path.read_text()
        assert "Trading Dashboard Export" in md_content
        assert "Test warning" in md_content
        assert "Max Drawdown" in md_content

    def test_generate_exports_creates_logs_directory(
        self,
        tmp_path: Path,
        snapshot: DashboardSnapshot,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        generator = ExportGenerator()
        monkeypatch.chdir(tmp_path)

        json_path, md_path = generator.generate_exports(snapshot)
        assert json_path.exists()
        assert md_path.exists()
        assert json.loads(json_path.read_text())["market_status"] == "OPEN"


def test_log_dashboard_event(tmp_path: Path) -> None:
    log_path = tmp_path / "usage.jsonl"

    log_dashboard_event("dashboard.test", log_path=log_path, foo="bar")
    contents = log_path.read_text().strip().splitlines()
    assert contents
    record = json.loads(contents[0])
    assert record["event"] == "dashboard.test"
    assert record["foo"] == "bar"


class TestCommandReader:
    """Targeted tests for the command reader helper."""

    def test_command_reader_collects_commands(self, monkeypatch: pytest.MonkeyPatch) -> None:
        inputs = iter(["r", None, "e", "H", "EOF"])

        def fake_input() -> str:
            value = next(inputs)
            if value is None:
                return None  # exercises the continue branch
            if value == "EOF":
                raise EOFError
            return value

        reader = dashboard._CommandReader()
        monkeypatch.setattr("builtins.input", fake_input)

        reader._run()

        assert reader.poll() == "R"
        assert reader.poll() == "E"
        assert reader.poll() == "H"
        assert reader.poll() is None

    def test_command_reader_start_stop(self) -> None:
        reader = dashboard._CommandReader()
        fake_thread = MagicMock()
        reader._thread = fake_thread

        reader.start()
        fake_thread.start.assert_called_once()

        assert not reader._stop.is_set()
        reader.stop()
        assert reader._stop.is_set()

    def test_command_reader_handles_keyboard_interrupt(self, monkeypatch: pytest.MonkeyPatch) -> None:
        states = iter(["keyboard", "eof"])

        def fake_input() -> str:
            state = next(states)
            if state == "keyboard":
                raise KeyboardInterrupt
            raise EOFError

        reader = dashboard._CommandReader()
        monkeypatch.setattr("builtins.input", fake_input)

        reader._run()

        assert reader.poll() == "Q"
        assert reader.poll() is None


def test_run_dashboard_loop_handles_commands(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    generated_at = datetime.now(UTC)
    targets = DashboardTargets(
        win_rate_target=55.0,
        daily_pl_target=Decimal("250.0"),
        trades_per_day_target=4,
        max_drawdown_target=Decimal("-180.0"),
        avg_risk_reward_target=1.6,
    )

    snapshots = [
        _make_snapshot(generated_at=generated_at, stale=False, warnings=[], targets=targets),
        _make_snapshot(
            generated_at=generated_at + timedelta(seconds=120),
            stale=True,
            warnings=["Stale data"],
            targets=targets,
        ),
    ]

    provider = MagicMock()
    provider.get_snapshot.side_effect = snapshots + [snapshots[-1]]

    updates: list = []

    class DummyLive:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def update(self, layout):
            updates.append(layout)

    messages: list[str] = []

    class DummyConsole(Console):
        def __init__(self) -> None:
            super().__init__(record=True, force_terminal=True)

        def print(self, *args, **kwargs):
            messages.append(" ".join(str(a) for a in args))

    commands = ["R", "E", "H", "Q"]

    class StubCommandReader:
        def __init__(self) -> None:
            self._iter = iter(commands)

        def start(self) -> None:
            pass

        def stop(self) -> None:
            pass

        def poll(self) -> str | None:
            return next(self._iter, None)

    monotonic_values = itertools.chain([0, 0, 5, 6, 7], itertools.repeat(7))

    monkeypatch.setattr(dashboard, "_CommandReader", StubCommandReader)
    monkeypatch.setattr(dashboard, "Live", DummyLive)
    monkeypatch.setattr(dashboard.time, "sleep", lambda _: None)
    monkeypatch.setattr(dashboard.time, "monotonic", lambda: next(monotonic_values))
    monkeypatch.setattr(dashboard, "log_dashboard_event", lambda *args, **kwargs: None)
    monkeypatch.chdir(tmp_path)

    exporter = ExportGenerator()
    renderer = DisplayRenderer()
    console = DummyConsole()

    dashboard.run_dashboard_loop(
        data_provider=provider,
        renderer=renderer,
        exporter=exporter,
        targets=targets,
        console=console,
        refresh_interval=1,
    )

    assert provider.get_snapshot.call_count >= 2
    assert any("Manual refresh" in m for m in messages)
    assert any("Exported dashboard summary" in m for m in messages)
    assert updates, "rendered layouts should be recorded"
    export_files = list(Path("logs").glob("dashboard-export-*.json"))
    assert export_files, "export JSON file should be created"


def test_run_dashboard_loop_handles_keyboard_interrupt(monkeypatch: pytest.MonkeyPatch) -> None:
    snapshot = _make_snapshot(generated_at=datetime.now(UTC))
    provider = MagicMock()
    provider.get_snapshot.return_value = snapshot

    class StubCommandReader:
        def __init__(self) -> None:
            self.stopped = False

        def start(self) -> None:
            pass

        def stop(self) -> None:
            self.stopped = True

        def poll(self) -> str | None:
            return None

    class RaisingLive:
        def __init__(self, *_, **__):
            pass

        def __enter__(self):
            raise KeyboardInterrupt

        def __exit__(self, exc_type, exc, tb):
            return False

    messages: list[str] = []

    class DummyConsole(Console):
        def __init__(self) -> None:
            super().__init__(record=True, force_terminal=True)

        def print(self, *args, **kwargs):
            messages.append(" ".join(str(a) for a in args))

    monkeypatch.setattr(dashboard, "_CommandReader", StubCommandReader)
    monkeypatch.setattr(dashboard, "Live", RaisingLive)
    monkeypatch.setattr(dashboard, "log_dashboard_event", lambda *a, **k: None)

    dashboard.run_dashboard_loop(
        data_provider=provider,
        renderer=DisplayRenderer(),
        exporter=ExportGenerator(),
        console=DummyConsole(),
    )

    assert any("interrupted" in msg.lower() for msg in messages)


def test_main_invokes_run_dashboard_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, object] = {}

    class FakeProvider:
        def __init__(self, account_data, trade_helper, metrics_calculator):
            self.account_data = account_data
            self.trade_helper = trade_helper
            self.metrics_calculator = metrics_calculator
            self.loaded = False

        def load_targets(self):
            self.loaded = True
            return "targets"

    monkeypatch.setattr(dashboard, "DashboardDataProvider", FakeProvider)
    monkeypatch.setattr(dashboard, "DisplayRenderer", lambda: "renderer")
    monkeypatch.setattr(dashboard, "ExportGenerator", lambda: "exporter")
    monkeypatch.setattr(
        dashboard,
        "run_dashboard_loop",
        lambda **kwargs: calls.update(kwargs),
    )

    console = Console(record=True, force_terminal=True)
    account_data = MagicMock()
    trade_helper = MagicMock()

    dashboard.main(account_data=account_data, trade_helper=trade_helper, console=console)

    assert isinstance(calls["data_provider"], FakeProvider)
    assert calls["renderer"] == "renderer"
    assert calls["exporter"] == "exporter"
    assert calls["targets"] == "targets"
    assert calls["console"] is console
    assert calls["data_provider"].loaded is True
