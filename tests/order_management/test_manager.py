from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from unittest import mock

import pytest

from src.trading_bot.config import OrderManagementConfig
from src.trading_bot.order_management.manager import OrderManager
from src.trading_bot.order_management.models import OrderEnvelope, OrderRequest


@pytest.fixture
def order_config() -> OrderManagementConfig:
    return OrderManagementConfig.default()


@pytest.fixture
def order_request() -> OrderRequest:
    return OrderRequest(
        symbol="TSLA",
        side="BUY",
        quantity=5,
        reference_price=Decimal("250.30"),
    )


@pytest.fixture
def order_log(tmp_path: Path) -> Path:
    return tmp_path / "orders.jsonl"


@pytest.fixture
def safety_checks() -> mock.Mock:
    safety = mock.Mock()
    safety.register_pending_order = mock.Mock()
    safety.clear_pending_order = mock.Mock()
    safety.clear_all_pending_orders = mock.Mock()
    return safety


@pytest.fixture
def account_data() -> mock.Mock:
    account = mock.Mock()
    account.invalidate_cache = mock.Mock()
    return account


@pytest.fixture
def manager(order_config, safety_checks, account_data, order_log) -> OrderManager:
    return OrderManager(
        config=order_config,
        safety_checks=safety_checks,
        account_data=account_data,
        session_id="session-123",
        bot_version="1.0.0",
        config_hash="deadbeef",
        order_log_path=order_log,
        execution_mode="LIVE",
    )


@mock.patch("src.trading_bot.order_management.manager.submit_limit_buy")
@mock.patch("src.trading_bot.order_management.manager.append_order_log")
def test_place_limit_order_records_pending(log_mock, submit_mock, manager, order_request, safety_checks):
    envelope = OrderEnvelope(
        order_id="abc",
        symbol="TSLA",
        side="BUY",
        quantity=5,
        limit_price=Decimal("249.93"),
        execution_mode="LIVE",
        submitted_at=mock.Mock(),
    )
    submit_mock.return_value = envelope

    result = manager.place_limit_order(order_request, strategy_name="alpha")

    assert result is envelope
    submit_mock.assert_called_once()
    safety_checks.register_pending_order.assert_called_once_with("TSLA", "BUY", "abc")
    log_mock.assert_called_once()


@mock.patch("src.trading_bot.order_management.manager.cancel_all_equity_orders")
@mock.patch("src.trading_bot.order_management.manager.append_order_log")
def test_cancel_all_clears_pending(log_mock, cancel_mock, manager, safety_checks, account_data, order_request):
    envelope = OrderEnvelope(
        order_id="abc",
        symbol="TSLA",
        side="BUY",
        quantity=5,
        limit_price=Decimal("249.93"),
        execution_mode="LIVE",
        submitted_at=mock.Mock(),
    )
    manager._register_tracking(envelope)
    cancel_mock.return_value = ["abc"]

    manager.cancel_all_open_orders()

    safety_checks.clear_pending_order.assert_called_once_with("TSLA")
    account_data.invalidate_cache.assert_any_call("buying_power")
    account_data.invalidate_cache.assert_any_call("positions")
    log_mock.assert_called()


@mock.patch("src.trading_bot.order_management.manager.fetch_order_status")
@mock.patch("src.trading_bot.order_management.manager.append_order_log")
def test_synchronize_updates_completed_orders(log_mock, fetch_mock, manager, safety_checks, account_data, order_request):
    envelope = OrderEnvelope(
        order_id="abc",
        symbol="TSLA",
        side="BUY",
        quantity=5,
        limit_price=Decimal("249.93"),
        execution_mode="LIVE",
        submitted_at=mock.Mock(),
    )
    manager._register_tracking(envelope)

    status = mock.Mock()
    status.state = "filled"
    status.order_id = "abc"
    status.symbol = "TSLA"
    fetch_mock.return_value = status

    manager.synchronize_open_orders()

    safety_checks.clear_pending_order.assert_called_once_with("TSLA")
    account_data.invalidate_cache.assert_any_call("buying_power")
    account_data.invalidate_cache.assert_any_call("positions")
    log_mock.assert_called()
