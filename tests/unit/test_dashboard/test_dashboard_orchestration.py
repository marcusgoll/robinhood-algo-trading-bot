"""
Unit tests for dashboard orchestration module.

Tests T021-T023:
- T021: load_targets() configuration loader
- T022: fetch_dashboard_state() state aggregation
- T023: run_dashboard_loop() polling loop (integration test)

Constitution v1.0.0:
- §Error_Handling: Test graceful degradation on errors
- §Data_Integrity: Validate type conversions and data flow
"""

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from trading_bot.account.account_data import AccountBalance, Position
from trading_bot.dashboard.dashboard import (
    fetch_dashboard_state,
    load_targets,
)
from trading_bot.dashboard.models import DashboardTargets
from trading_bot.logging.trade_record import TradeRecord


class TestLoadTargets:
    """Tests for T021: load_targets() configuration loader."""

    def test_load_valid_config(self, tmp_path):
        """Test loading valid YAML configuration."""
        # Create valid config file
        config_path = tmp_path / "dashboard-targets.yaml"
        config_path.write_text("""
win_rate_target: 60.0
daily_pl_target: 500.0
trades_per_day_target: 10
max_drawdown_target: -200.0
avg_risk_reward_target: 2.0
""")

        # Load targets
        targets = load_targets(config_path)

        # Verify
        assert targets is not None
        assert targets.win_rate_target == 60.0
        assert targets.daily_pl_target == Decimal("500.0")
        assert targets.trades_per_day_target == 10
        assert targets.max_drawdown_target == Decimal("-200.0")
        assert targets.avg_risk_reward_target == 2.0

    def test_load_missing_file(self, tmp_path):
        """Test graceful handling of missing config file."""
        config_path = tmp_path / "nonexistent.yaml"

        # Load targets (should return None)
        targets = load_targets(config_path)

        # Verify graceful degradation
        assert targets is None

    def test_load_invalid_yaml(self, tmp_path):
        """Test graceful handling of invalid YAML syntax."""
        config_path = tmp_path / "invalid.yaml"
        config_path.write_text("invalid: yaml: syntax: [")

        # Load targets (should return None)
        targets = load_targets(config_path)

        # Verify graceful degradation
        assert targets is None

    def test_load_missing_required_field(self, tmp_path):
        """Test graceful handling of missing required fields."""
        config_path = tmp_path / "incomplete.yaml"
        config_path.write_text("""
win_rate_target: 60.0
daily_pl_target: 500.0
# Missing trades_per_day_target, max_drawdown_target, avg_risk_reward_target
""")

        # Load targets (should return None)
        targets = load_targets(config_path)

        # Verify graceful degradation
        assert targets is None

    def test_load_invalid_numeric_values(self, tmp_path):
        """Test graceful handling of invalid numeric values."""
        config_path = tmp_path / "invalid-values.yaml"
        config_path.write_text("""
win_rate_target: invalid
daily_pl_target: 500.0
trades_per_day_target: 10
max_drawdown_target: -200.0
avg_risk_reward_target: 2.0
""")

        # Load targets (should return None)
        targets = load_targets(config_path)

        # Verify graceful degradation
        assert targets is None


class TestFetchDashboardState:
    """Tests for T022: fetch_dashboard_state() state aggregation."""

    def test_fetch_complete_state(self):
        """Test fetching complete dashboard state with all data."""
        # Mock AccountData
        account_data = MagicMock()
        account_data.get_account_balance.return_value = AccountBalance(
            cash=Decimal("10000.00"),
            equity=Decimal("15000.00"),
            buying_power=Decimal("20000.00"),
            last_updated=datetime.now(timezone.utc)
        )
        account_data.get_buying_power.return_value = 20000.00
        account_data.get_day_trade_count.return_value = 2
        account_data.get_positions.return_value = [
            Position(
                symbol="AAPL",
                quantity=100,
                average_buy_price=Decimal("150.00"),
                current_price=Decimal("155.00"),
                last_updated=datetime.now(timezone.utc)
            )
        ]

        # Mock TradeQueryHelper
        trade_helper = MagicMock()
        trade_helper.query_by_date_range.return_value = [
            TradeRecord(
                timestamp=datetime.now(timezone.utc).isoformat(),
                symbol="AAPL",
                action="BUY",
                quantity=100,
                price=Decimal("150.00"),
                total_value=Decimal("15000.00"),
                order_id="test-order-1",
                execution_mode="PAPER",
                account_id=None,
                strategy_name="test-strategy",
                entry_type="breakout",
                stop_loss=Decimal("148.00"),
                target=Decimal("154.00"),
                decision_reasoning="Test trade",
                indicators_used=["VWAP"],
                risk_reward_ratio=2.0,
                outcome="open",
                profit_loss=None,
                hold_duration_seconds=None,
                exit_timestamp=None,
                exit_reasoning=None,
                slippage=None,
                commission=None,
                net_profit_loss=None,
                session_id="test-session",
                bot_version="1.0.0",
                config_hash="abc123"
            )
        ]

        # Mock targets
        targets = DashboardTargets(
            win_rate_target=60.0,
            daily_pl_target=Decimal("500.0"),
            trades_per_day_target=10,
            max_drawdown_target=Decimal("-200.0"),
            avg_risk_reward_target=2.0
        )

        # Fetch dashboard state
        with patch('trading_bot.dashboard.dashboard.is_market_open', return_value=True):
            state = fetch_dashboard_state(account_data, trade_helper, targets)

        # Verify account status
        assert state.account_status.buying_power == Decimal("20000.00")
        assert state.account_status.account_balance == Decimal("15000.00")
        assert state.account_status.cash_balance == Decimal("10000.00")
        assert state.account_status.day_trade_count == 2

        # Verify positions
        assert len(state.positions) == 1
        assert state.positions[0].symbol == "AAPL"
        assert state.positions[0].quantity == 100
        assert state.positions[0].entry_price == Decimal("150.00")
        assert state.positions[0].current_price == Decimal("155.00")

        # Verify market status
        assert state.market_status == "OPEN"

        # Verify targets
        assert state.targets == targets

    def test_fetch_state_empty_positions(self):
        """Test fetching dashboard state with no positions."""
        # Mock AccountData with no positions
        account_data = MagicMock()
        account_data.get_account_balance.return_value = AccountBalance(
            cash=Decimal("10000.00"),
            equity=Decimal("10000.00"),
            buying_power=Decimal("10000.00"),
            last_updated=datetime.now(timezone.utc)
        )
        account_data.get_buying_power.return_value = 10000.00
        account_data.get_day_trade_count.return_value = 0
        account_data.get_positions.return_value = []

        # Mock TradeQueryHelper with no trades
        trade_helper = MagicMock()
        trade_helper.query_by_date_range.return_value = []

        # Fetch dashboard state
        with patch('trading_bot.dashboard.dashboard.is_market_open', return_value=False):
            state = fetch_dashboard_state(account_data, trade_helper, None)

        # Verify empty positions
        assert len(state.positions) == 0

        # Verify market status
        assert state.market_status == "CLOSED"

        # Verify metrics with no data
        assert state.performance_metrics.win_rate == 0.0
        assert state.performance_metrics.trades_today == 0

    def test_fetch_state_without_targets(self):
        """Test fetching dashboard state without performance targets."""
        # Mock AccountData
        account_data = MagicMock()
        account_data.get_account_balance.return_value = AccountBalance(
            cash=Decimal("10000.00"),
            equity=Decimal("10000.00"),
            buying_power=Decimal("10000.00"),
            last_updated=datetime.now(timezone.utc)
        )
        account_data.get_buying_power.return_value = 10000.00
        account_data.get_day_trade_count.return_value = 0
        account_data.get_positions.return_value = []

        # Mock TradeQueryHelper
        trade_helper = MagicMock()
        trade_helper.query_by_date_range.return_value = []

        # Fetch dashboard state without targets
        with patch('trading_bot.dashboard.dashboard.is_market_open', return_value=False):
            state = fetch_dashboard_state(account_data, trade_helper, None)

        # Verify no targets
        assert state.targets is None


# Note: T023 (run_dashboard_loop) requires integration testing with
# keyboard input and rich.live.Live, which is best done manually or
# with end-to-end testing framework.
