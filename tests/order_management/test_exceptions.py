import pytest

from src.trading_bot.order_management.exceptions import (
    OrderError,
    UnsupportedOrderTypeError,
)
from src.trading_bot.order_management.manager import ensure_limit_order_type


def test_unsupported_order_type_error_inherits_order_error() -> None:
    err = UnsupportedOrderTypeError("stop")
    assert isinstance(err, OrderError)


def test_ensure_limit_order_type_rejects_stop_orders() -> None:
    with pytest.raises(UnsupportedOrderTypeError):
        ensure_limit_order_type("stop")


def test_ensure_limit_order_type_accepts_limit_orders() -> None:
    # Should not raise
    ensure_limit_order_type("limit")
