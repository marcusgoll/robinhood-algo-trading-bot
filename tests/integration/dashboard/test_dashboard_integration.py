"""
Integration test: Full dashboard with live data.

T030 - Tests end-to-end dashboard launch with AccountData + TradeQueryHelper.
Mocks API responses to avoid live Robinhood calls in CI.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, Mock, patch

import pytest

from trading_bot.account.account_data import AccountBalance, Position
from trading_bot.dashboard.dashboard import run_dashboard_loop
from trading_bot.dashboard.data_provider import DashboardDataProvider
from trading_bot.dashboard.display_renderer import DisplayRenderer
from trading_bot.dashboard.export_generator import ExportGenerator
from trading_bot.dashboard.metrics_calculator import MetricsCalculator
from trading_bot.dashboard.models import DashboardTargets
from trading_bot.logging.trade_record import TradeRecord

if TYPE_CHECKING:
    from rich.console import Console


@pytest.fixture
def mock_account_data():
    """Mock AccountData service with realistic data."""
    account_data = Mock()

    # Mock account balance
    balance = AccountBalance(
        equity=Decimal("25000.00"),
        cash=Decimal("15000.00"),
        buying_power=Decimal("60000.00"),
        last_updated=datetime.now(UTC),
    )
    account_data.get_account_balance.return_value = balance
    account_data.get_buying_power.return_value = 60000.00
    account_data.get_day_trade_count.return_value = 2

    # Mock positions (Position class uses properties for P&L, so we only need basic fields)
    positions = [
        Position(
            symbol="AAPL",
            quantity=100,
            average_buy_price=Decimal("150.00"),
            current_price=Decimal("155.25"),
            last_updated=datetime.now(UTC),
        ),
        Position(
            symbol="TSLA",
            quantity=50,
            average_buy_price=Decimal("250.00"),
            current_price=Decimal("245.50"),
            last_updated=datetime.now(UTC),
        ),
    ]
    account_data.get_positions.return_value = positions

    return account_data


@pytest.fixture
def mock_trade_helper(tmp_path):
    """Mock TradeQueryHelper with realistic trade data."""
    trade_helper = Mock()
    trade_helper.log_dir = tmp_path / "logs"
    trade_helper.log_dir.mkdir(parents=True, exist_ok=True)

    # Create today's log file with sample trades
    now = datetime.now(UTC)
    today = now.strftime("%Y-%m-%d")
    log_file = trade_helper.log_dir / f"{today}.jsonl"

    # Create timestamps explicitly on today's date to avoid midnight boundary issues
    today_date = now.date()
    ts_2h_ago = datetime.combine(today_date, datetime.min.time()).replace(hour=10, minute=0, tzinfo=UTC).isoformat().replace('+00:00', 'Z')
    ts_1h_ago = datetime.combine(today_date, datetime.min.time()).replace(hour=11, minute=0, tzinfo=UTC).isoformat().replace('+00:00', 'Z')
    ts_30m_ago = datetime.combine(today_date, datetime.min.time()).replace(hour=11, minute=30, tzinfo=UTC).isoformat().replace('+00:00', 'Z')

    trades = [
        TradeRecord(
            timestamp=ts_2h_ago,
            symbol="AAPL",
            action="BUY",
            quantity=100,
            price=Decimal("150.00"),
            total_value=Decimal("15000.00"),
            order_id="order-001",
            execution_mode="PAPER",
            account_id=None,
            strategy_name="momentum",
            entry_type="breakout",
            stop_loss=Decimal("148.00"),
            target=Decimal("156.00"),
            decision_reasoning="Strong momentum breakout above resistance",
            indicators_used=["VWAP", "EMA-9"],
            risk_reward_ratio=3.0,
            outcome="open",
            profit_loss=None,
            hold_duration_seconds=None,
            exit_timestamp=None,
            exit_reasoning=None,
            slippage=None,
            commission=None,
            net_profit_loss=None,
            session_id="session-001",
            bot_version="1.0.0",
            config_hash="abc123",
        ),
        TradeRecord(
            timestamp=ts_1h_ago,
            symbol="AAPL",
            action="SELL",
            quantity=100,
            price=Decimal("155.25"),
            total_value=Decimal("15525.00"),
            order_id="order-002",
            execution_mode="PAPER",
            account_id=None,
            strategy_name="momentum",
            entry_type="breakout",
            stop_loss=Decimal("148.00"),
            target=Decimal("156.00"),
            decision_reasoning="Target reached",
            indicators_used=["VWAP", "EMA-9"],
            risk_reward_ratio=3.0,
            outcome="win",
            profit_loss=Decimal("525.00"),
            hold_duration_seconds=3600,
            exit_timestamp=ts_1h_ago,
            exit_reasoning="Target reached",
            slippage=Decimal("0.00"),
            commission=Decimal("0.00"),
            net_profit_loss=Decimal("525.00"),
            session_id="session-001",
            bot_version="1.0.0",
            config_hash="abc123",
        ),
        TradeRecord(
            timestamp=ts_30m_ago,
            symbol="TSLA",
            action="BUY",
            quantity=50,
            price=Decimal("250.00"),
            total_value=Decimal("12500.00"),
            order_id="order-003",
            execution_mode="PAPER",
            account_id=None,
            strategy_name="reversal",
            entry_type="reversal",
            stop_loss=Decimal("245.00"),
            target=Decimal("260.00"),
            decision_reasoning="Reversal pattern detected",
            indicators_used=["RSI", "MACD"],
            risk_reward_ratio=2.0,
            outcome="open",
            profit_loss=None,
            hold_duration_seconds=None,
            exit_timestamp=None,
            exit_reasoning=None,
            slippage=None,
            commission=None,
            net_profit_loss=None,
            session_id="session-002",
            bot_version="1.0.0",
            config_hash="abc123",
        ),
    ]

    # Write trades to log file
    with log_file.open("w", encoding="utf-8") as f:
        for trade in trades:
            f.write(json.dumps(trade.__dict__, default=str) + "\n")

    # Mock query_by_date_range to return trades
    trade_helper.query_by_date_range.return_value = trades

    return trade_helper


@pytest.fixture
def dashboard_targets():
    """Sample dashboard targets for testing."""
    return DashboardTargets(
        win_rate_target=70.0,
        daily_pl_target=Decimal("500.00"),
        trades_per_day_target=5,
        max_drawdown_target=Decimal("-200.00"),
        avg_risk_reward_target=2.5,
    )


@pytest.fixture
def data_provider(mock_account_data, mock_trade_helper):
    """Create DashboardDataProvider with mocked services."""
    return DashboardDataProvider(
        account_data=mock_account_data,
        trade_helper=mock_trade_helper,
        metrics_calculator=MetricsCalculator(),
    )


class TestDashboardIntegration:
    """Integration tests for full dashboard functionality."""

    def test_dashboard_aggregates_state_correctly(
        self, data_provider, dashboard_targets
    ):
        """
        T030.1 - Verify dashboard state aggregates correctly.

        Tests that DashboardDataProvider correctly combines:
        - Account status from AccountData
        - Positions with calculated P&L
        - Performance metrics from trade logs
        - Market status determination
        """
        snapshot = data_provider.get_snapshot(targets=dashboard_targets)

        # Verify account status
        assert snapshot.account_status.account_balance == Decimal("25000.00")
        assert snapshot.account_status.cash_balance == Decimal("15000.00")
        assert snapshot.account_status.buying_power == Decimal("60000.00")
        assert snapshot.account_status.day_trade_count == 2

        # Verify positions (sorted by unrealized P&L descending)
        assert len(snapshot.positions) == 2
        assert snapshot.positions[0].symbol == "AAPL"  # Higher P&L first
        assert snapshot.positions[0].unrealized_pl > Decimal("0")  # Profitable position
        assert snapshot.positions[1].symbol == "TSLA"
        assert snapshot.positions[1].unrealized_pl < Decimal("0")  # Loss position

        # Verify performance metrics
        assert snapshot.performance_metrics.trades_today == 3
        assert snapshot.performance_metrics.session_count == 2
        assert snapshot.performance_metrics.total_realized_pl > 0
        assert snapshot.performance_metrics.total_unrealized_pl == Decimal("300.00")

        # Verify market status is set
        assert snapshot.market_status in ["OPEN", "CLOSED"]

        # Verify metadata
        assert snapshot.generated_at is not None
        assert snapshot.data_age_seconds >= 0
        assert isinstance(snapshot.is_data_stale, bool)

        # Verify targets are included
        assert snapshot.targets == dashboard_targets

    def test_dashboard_renderer_produces_valid_output(
        self, data_provider, dashboard_targets
    ):
        """
        T030.2 - Verify DisplayRenderer produces valid output.

        Tests that renderer can create Rich layout from snapshot
        without crashing.
        """
        renderer = DisplayRenderer()
        snapshot = data_provider.get_snapshot(targets=dashboard_targets)

        # Should not raise any exceptions
        layout = renderer.render_full_dashboard(snapshot)

        # Verify layout is not None and has expected structure
        assert layout is not None
        assert hasattr(layout, "renderable")

    def test_dashboard_handles_no_positions(self, mock_account_data, mock_trade_helper):
        """
        T030.3 - Verify dashboard handles empty positions gracefully.

        Tests that dashboard displays correctly when there are no open positions.
        """
        # Mock empty positions
        mock_account_data.get_positions.return_value = []

        provider = DashboardDataProvider(
            account_data=mock_account_data,
            trade_helper=mock_trade_helper,
            metrics_calculator=MetricsCalculator(),
        )

        snapshot = provider.get_snapshot()

        assert len(snapshot.positions) == 0
        assert snapshot.performance_metrics.total_unrealized_pl == Decimal("0.00")

        # Renderer should still work
        renderer = DisplayRenderer()
        layout = renderer.render_full_dashboard(snapshot)
        assert layout is not None

    def test_dashboard_handles_no_trades(
        self, mock_account_data, mock_trade_helper, tmp_path
    ):
        """
        T030.4 - Verify dashboard handles missing trade logs gracefully.

        Tests that dashboard shows warning when trade logs are missing
        but continues to display account/position data.
        """
        # Mock no trades
        mock_trade_helper.query_by_date_range.return_value = []
        mock_trade_helper.log_dir = tmp_path / "empty_logs"
        mock_trade_helper.log_dir.mkdir(parents=True, exist_ok=True)

        provider = DashboardDataProvider(
            account_data=mock_account_data,
            trade_helper=mock_trade_helper,
            metrics_calculator=MetricsCalculator(),
        )

        snapshot = provider.get_snapshot()

        # Should have warning about missing trade log
        assert any("Trade log" in warning for warning in snapshot.warnings)

        # But should still have account and position data
        assert snapshot.account_status.account_balance == Decimal("25000.00")
        assert len(snapshot.positions) == 2

        # Metrics should show zero activity
        assert snapshot.performance_metrics.trades_today == 0
        assert snapshot.performance_metrics.win_rate == 0.0

    @patch("trading_bot.dashboard.dashboard.time.sleep")
    @patch("trading_bot.dashboard.dashboard._CommandReader")
    def test_dashboard_loop_runs_without_crash(
        self,
        mock_command_reader_class,
        mock_sleep,
        data_provider,
        dashboard_targets,
    ):
        """
        T030.5 - Verify dashboard polling loop runs without crashes.

        Tests that the dashboard loop can start, refresh, and exit cleanly.
        """
        # Mock command reader to simulate quit command after first refresh
        mock_reader = MagicMock()
        mock_reader.poll.side_effect = [None, "Q"]  # None first, then Q
        mock_command_reader_class.return_value = mock_reader

        # Mock sleep to avoid waiting
        mock_sleep.return_value = None

        renderer = DisplayRenderer()
        exporter = ExportGenerator()
        # Use MagicMock instead of Mock to allow all attribute access
        mock_console = MagicMock()

        # Should run and exit cleanly with Q command
        run_dashboard_loop(
            data_provider=data_provider,
            renderer=renderer,
            exporter=exporter,
            targets=dashboard_targets,
            refresh_interval=0.1,  # Fast refresh for testing
            console=mock_console,
        )

        # Verify console output (launched and stopped messages)
        assert mock_console.print.call_count >= 2

        # Verify command reader was started and stopped
        mock_reader.start.assert_called_once()
        mock_reader.stop.assert_called_once()

    def test_dashboard_data_freshness_tracking(
        self, mock_account_data, mock_trade_helper
    ):
        """
        T030.6 - Verify dashboard tracks data freshness correctly.

        Tests that data_age_seconds and is_data_stale are calculated properly.
        """
        # Set account data to be 65 seconds old (stale)
        old_time = datetime.now(UTC) - timedelta(seconds=65)
        balance = AccountBalance(
            equity=Decimal("25000.00"),
            cash=Decimal("15000.00"),
            buying_power=Decimal("60000.00"),
            last_updated=old_time,
        )
        mock_account_data.get_account_balance.return_value = balance

        provider = DashboardDataProvider(
            account_data=mock_account_data,
            trade_helper=mock_trade_helper,
            metrics_calculator=MetricsCalculator(),
        )

        snapshot = provider.get_snapshot()

        # Should be marked as stale (>60s old)
        assert snapshot.data_age_seconds >= 65
        assert snapshot.is_data_stale is True
        assert any("stale" in warning.lower() for warning in snapshot.warnings)

    def test_dashboard_metrics_calculation_accuracy(
        self, mock_account_data, mock_trade_helper
    ):
        """
        T030.7 - Verify metrics are calculated accurately from trade logs.

        Tests that performance metrics match expected calculations
        from the trade data.
        """
        provider = DashboardDataProvider(
            account_data=mock_account_data,
            trade_helper=mock_trade_helper,
            metrics_calculator=MetricsCalculator(),
        )

        snapshot = provider.get_snapshot()
        metrics = snapshot.performance_metrics

        # We have 3 trades: 1 completed (win), 2 open
        assert metrics.trades_today == 3
        assert metrics.session_count == 2

        # Win rate should be 100% (1 win, 0 losses)
        assert metrics.win_rate == 100.0

        # Total P&L should include realized + unrealized
        # Realized: $525 from AAPL sale
        # Unrealized: calculated from current positions
        assert metrics.total_realized_pl == Decimal("525.00")
        assert metrics.total_unrealized_pl > Decimal("0")  # Should be positive overall
        assert metrics.total_pl > metrics.total_realized_pl  # Total = realized + unrealized

        # Current streak should be 1 WIN
        assert metrics.current_streak == 1
        assert metrics.streak_type == "WIN"
