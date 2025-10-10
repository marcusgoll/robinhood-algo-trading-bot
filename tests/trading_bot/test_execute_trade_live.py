from __future__ import annotations

from decimal import Decimal
from unittest import mock

import pytest

from src.trading_bot.bot import TradingBot
from src.trading_bot.config import Config, OrderManagementConfig
from src.trading_bot.order_management.exceptions import (
    OrderSubmissionError,
    UnsupportedOrderTypeError,
)
from src.trading_bot.order_management.models import OrderEnvelope
from src.trading_bot.safety_checks import SafetyResult


@pytest.fixture
def config() -> Config:
    cfg = Config(
        robinhood_username="user@example.com",
        robinhood_password="secret",
        paper_trading=False,
        trading_start_time="07:00",
        trading_end_time="10:00",
        trading_timezone="America/New_York",
        max_position_pct=5.0,
        max_daily_loss_pct=3.0,
        max_consecutive_losses=3,
        position_size_shares=100,
        stop_loss_pct=2.0,
        risk_reward_ratio=2.0,
        current_phase="experience",
        max_trades_per_day=999,
    )
    cfg.order_management = OrderManagementConfig.default()
    return cfg


@mock.patch("src.trading_bot.bot.OrderManager")
@mock.patch("src.trading_bot.bot.SessionHealthMonitor")
@mock.patch("src.trading_bot.bot.RobinhoodAuth")
@mock.patch("src.trading_bot.account.AccountData")
def test_execute_trade_live_delegates_to_order_manager(
    account_data_cls,
    auth_cls,
    health_cls,
    order_manager_cls,
    config,
) -> None:
    account_data_instance = mock.Mock()
    account_data_instance.get_buying_power.return_value = 10_000.0
    account_data_cls.return_value = account_data_instance

    order_manager_instance = mock.Mock()
    envelope = OrderEnvelope(
        order_id="abc-123",
        symbol="TSLA",
        side="BUY",
        quantity=5,
        limit_price=Decimal("249.93"),
        execution_mode="LIVE",
        submitted_at=mock.Mock(),
    )
    order_manager_instance.place_limit_order.return_value = envelope
    order_manager_cls.return_value = order_manager_instance

    bot = TradingBot(config=config, paper_trading=False)
    bot.is_running = True
    bot.safety_checks.validate_trade = mock.Mock(
        return_value=SafetyResult(is_safe=True)
    )

    bot.execute_trade(
        symbol="TSLA",
        action="buy",
        shares=5,
        price=Decimal("250.30"),
        reason="manual-entry",
    )

    order_manager_instance.place_limit_order.assert_called_once()
    args, kwargs = order_manager_instance.place_limit_order.call_args
    order_request = args[0]
    assert order_request.symbol == "TSLA"
    assert order_request.side == "BUY"
    assert kwargs["strategy_name"] == "manual"


@mock.patch("src.trading_bot.bot.OrderManager")
@mock.patch("src.trading_bot.bot.SessionHealthMonitor")
@mock.patch("src.trading_bot.bot.RobinhoodAuth")
@mock.patch("src.trading_bot.account.AccountData")
def test_execute_trade_live_handles_unsupported_order_type(
    account_data_cls,
    auth_cls,
    health_cls,
    order_manager_cls,
    config,
    caplog,
) -> None:
    account_data_instance = mock.Mock()
    account_data_instance.get_buying_power.return_value = 10_000.0
    account_data_cls.return_value = account_data_instance

    order_manager_instance = mock.Mock()
    order_manager_instance.place_limit_order.side_effect = UnsupportedOrderTypeError("market")
    order_manager_cls.return_value = order_manager_instance

    bot = TradingBot(config=config, paper_trading=False)
    bot.is_running = True
    bot.safety_checks.validate_trade = mock.Mock(
        return_value=SafetyResult(is_safe=True)
    )

    with caplog.at_level("INFO"):
        bot.execute_trade(
            symbol="TSLA",
            action="buy",
            shares=5,
            price=Decimal("250.30"),
            reason="manual-entry",
        )

    assert "Unsupported order type" in caplog.text


@mock.patch("src.trading_bot.bot.OrderManager")
@mock.patch("src.trading_bot.bot.SessionHealthMonitor")
@mock.patch("src.trading_bot.bot.RobinhoodAuth")
@mock.patch("src.trading_bot.account.AccountData")
def test_execute_trade_live_handles_submission_error(
    account_data_cls,
    auth_cls,
    health_cls,
    order_manager_cls,
    config,
    caplog,
) -> None:
    account_data_instance = mock.Mock()
    account_data_instance.get_buying_power.return_value = 10_000.0
    account_data_cls.return_value = account_data_instance

    order_manager_instance = mock.Mock()
    order_manager_instance.place_limit_order.side_effect = OrderSubmissionError(
        "broker unavailable"
    )
    order_manager_cls.return_value = order_manager_instance

    bot = TradingBot(config=config, paper_trading=False)
    bot.is_running = True
    bot.safety_checks.validate_trade = mock.Mock(
        return_value=SafetyResult(is_safe=True)
    )

    with caplog.at_level("ERROR"):
        bot.execute_trade(
            symbol="TSLA",
            action="buy",
            shares=5,
            price=Decimal("250.30"),
            reason="manual-entry",
        )

    assert "LIVE ORDER FAILED" in caplog.text
    order_manager_instance.place_limit_order.assert_called_once()


def test_cancel_all_open_orders_delegates_to_manager(config) -> None:
    bot = TradingBot(config=config, paper_trading=False)
    bot.order_manager = mock.Mock()

    bot.cancel_all_open_orders()

    bot.order_manager.cancel_all_open_orders.assert_called_once()


def test_cancel_all_open_orders_no_manager(config, caplog) -> None:
    bot = TradingBot(config=config, paper_trading=False)
    bot.order_manager = None

    with caplog.at_level("INFO"):
        bot.cancel_all_open_orders()

    assert "Order manager unavailable" in caplog.text
