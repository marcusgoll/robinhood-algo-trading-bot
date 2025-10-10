from decimal import Decimal
from unittest import mock

import pytest

from src.trading_bot.config import OrderManagementConfig
from src.trading_bot.order_management.calculator import resolve_strategy_offsets
from src.trading_bot.order_management.exceptions import (
    OrderCancellationError,
    OrderStatusError,
    OrderSubmissionError,
)
from src.trading_bot.order_management.gateways import (
    cancel_all_equity_orders,
    fetch_order_status,
    submit_limit_buy,
    submit_limit_sell,
)
from src.trading_bot.order_management.models import OrderRequest, OrderStatus


@pytest.fixture
def config() -> OrderManagementConfig:
    return OrderManagementConfig.default()


@pytest.fixture
def order_request() -> OrderRequest:
    return OrderRequest(
        symbol="TSLA",
        side="BUY",
        quantity=10,
        reference_price=Decimal("250.30"),
    )


@pytest.fixture
def offsets(config: OrderManagementConfig):
    return resolve_strategy_offsets(config, None)


@mock.patch("src.trading_bot.order_management.gateways._robin_stocks")
def test_submit_limit_buy_returns_order_id(mock_robin, order_request, offsets):
    mock_robin.orders.order_buy_limit.return_value = {"id": "123", "state": "confirmed"}

    envelope = submit_limit_buy(order_request, offsets, execution_mode="LIVE")

    assert envelope.order_id == "123"
    assert envelope.limit_price == Decimal("249.93")
    mock_robin.orders.order_buy_limit.assert_called_once()


@mock.patch("src.trading_bot.order_management.gateways._robin_stocks")
def test_submit_limit_sell_translates_errors(mock_robin, config):
    request = OrderRequest(
        symbol="TSLA",
        side="SELL",
        quantity=5,
        reference_price=Decimal("250.30"),
    )
    offsets = resolve_strategy_offsets(config, None)
    mock_robin.orders.order_sell_limit.side_effect = Exception("insufficient_funds")

    with pytest.raises(OrderSubmissionError, match="insufficient_funds"):
        submit_limit_sell(request, offsets, execution_mode="LIVE")


@mock.patch("src.trading_bot.order_management.gateways._robin_stocks")
def test_submit_limit_buy_retries_on_transient_error(
    mock_robin,
    order_request,
    offsets,
    monkeypatch,
):
    attempts = [
        Exception("transient failure"),
        {"id": "789", "state": "confirmed"},
    ]

    def _side_effect(*_, **__):
        result = attempts.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    mock_robin.orders.order_buy_limit.side_effect = _side_effect
    monkeypatch.setattr(
        "src.trading_bot.error_handling.retry.time.sleep",
        lambda *_args, **_kwargs: None,
    )

    envelope = submit_limit_buy(order_request, offsets, execution_mode="LIVE")

    assert envelope.order_id == "789"
    assert mock_robin.orders.order_buy_limit.call_count == 2


def test_submit_limit_buy_requires_broker(monkeypatch, order_request, offsets):
    import src.trading_bot.order_management.gateways as gateways

    monkeypatch.setattr(gateways, "_robin_stocks", None)

    with pytest.raises(OrderSubmissionError, match="robin_stocks library is not available"):
        gateways.submit_limit_buy(order_request, offsets, execution_mode="LIVE")

    monkeypatch.setattr(gateways, "_robin_stocks", mock.Mock())


@mock.patch("src.trading_bot.order_management.gateways._robin_stocks")
def test_submit_limit_buy_missing_order_id(mock_robin, order_request, offsets):
    mock_robin.orders.order_buy_limit.return_value = {"status": "ok"}

    with pytest.raises(OrderSubmissionError, match="missing order id"):
        submit_limit_buy(order_request, offsets, execution_mode="LIVE")


@mock.patch("src.trading_bot.order_management.gateways._robin_stocks")
def test_cancel_all_equity_orders_handles_partial_failure(mock_robin):
    mock_robin.orders.get_all_open_stock_orders.return_value = [
        {"id": "111", "state": "confirmed"},
        {"id": "222", "state": "confirmed"},
    ]
    mock_robin.orders.cancel_stock_order.side_effect = [True, Exception("fail")]

    with pytest.raises(OrderCancellationError, match="222"):
        cancel_all_equity_orders()


@mock.patch("src.trading_bot.order_management.gateways._robin_stocks")
def test_cancel_all_equity_orders_returns_cancelled_ids(mock_robin):
    mock_robin.orders.get_all_open_stock_orders.return_value = [
        {"id": "111", "state": "confirmed"},
    ]
    mock_robin.orders.cancel_stock_order.return_value = True

    result = cancel_all_equity_orders()
    assert result == ["111"]


@mock.patch("src.trading_bot.order_management.gateways._robin_stocks")
def test_cancel_all_equity_orders_fetch_failure(mock_robin):
    mock_robin.orders.get_all_open_stock_orders.side_effect = Exception("network")

    with pytest.raises(OrderCancellationError, match="network"):
        cancel_all_equity_orders()


@mock.patch("src.trading_bot.order_management.gateways._robin_stocks")
def test_fetch_order_status_returns_normalized_status(mock_robin):
    mock_robin.orders.get_stock_order_info.return_value = {
        "id": "abc",
        "state": "filled",
        "symbol": "TSLA",
        "side": "buy",
        "quantity": "10",
        "cumulative_quantity": "10",
        "average_price": "250.25",
        "last_transaction_at": "2025-02-01T10:00:00Z",
    }

    status = fetch_order_status("abc")

    assert isinstance(status, OrderStatus)
    assert status.filled_quantity == 10
    assert status.average_fill_price == Decimal("250.25")
    assert status.state == "filled"


@mock.patch("src.trading_bot.order_management.gateways._robin_stocks")
def test_fetch_order_status_raises_for_missing_payload(mock_robin):
    mock_robin.orders.get_stock_order_info.return_value = None

    with pytest.raises(OrderStatusError):
        fetch_order_status("missing")


@mock.patch("src.trading_bot.order_management.gateways._robin_stocks")
def test_fetch_order_status_propagates_exception(mock_robin):
    mock_robin.orders.get_stock_order_info.side_effect = Exception("boom")

    with pytest.raises(OrderStatusError, match="boom"):
        fetch_order_status("abc")


def test_parse_timestamp_invalid_format():
    from src.trading_bot.order_management.gateways import _parse_timestamp

    with pytest.raises(OrderStatusError):
        _parse_timestamp("not-a-timestamp")
