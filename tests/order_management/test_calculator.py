from decimal import Decimal

import pytest

from src.trading_bot.config import OrderManagementConfig
from src.trading_bot.order_management.calculator import (
    compute_limit_price,
    resolve_strategy_offsets,
    validate_order_request,
)
from src.trading_bot.order_management.exceptions import UnsupportedOrderTypeError
from src.trading_bot.order_management.models import OrderRequest


def test_compute_limit_price_bps_buy() -> None:
    config = OrderManagementConfig.default()
    order = OrderRequest(
        symbol="TSLA",
        side="BUY",
        quantity=50,
        reference_price=Decimal("250.30"),
        order_type="limit",
    )

    resolved = resolve_strategy_offsets(config, strategy_name=None)
    limit_price = compute_limit_price(order, resolved)

    assert limit_price == Decimal("249.93")


def test_compute_limit_price_absolute_sell_strategy_override() -> None:
    config = OrderManagementConfig.from_dict(
        {
            "offset_mode": "absolute",
            "buy_offset": 0.15,
            "sell_offset": 0.04,
            "strategy_overrides": {
                "exit-play": {
                    "sell_offset": 0.08,
                }
            },
        }
    )

    order = OrderRequest(
        symbol="AAPL",
        side="SELL",
        quantity=25,
        reference_price=Decimal("252.10"),
        order_type="limit",
    )

    resolved = resolve_strategy_offsets(config, strategy_name="exit-play")
    limit_price = compute_limit_price(order, resolved)

    assert limit_price == Decimal("252.18")


def test_compute_limit_price_respects_slippage_guard() -> None:
    config = OrderManagementConfig.from_dict(
        {
            "offset_mode": "bps",
            "buy_offset": 500,  # 5%
            "sell_offset": 500,
            "max_slippage_pct": 0.5,
        }
    )

    order = OrderRequest(
        symbol="NVDA",
        side="BUY",
        quantity=10,
        reference_price=Decimal("450.00"),
        order_type="limit",
    )

    resolved = resolve_strategy_offsets(config, None)

    with pytest.raises(ValueError, match="slippage"):
        compute_limit_price(order, resolved)


def test_compute_limit_price_invalid_reference() -> None:
    config = OrderManagementConfig.default()
    order = OrderRequest(
        symbol="TSLA",
        side="BUY",
        quantity=10,
        reference_price=Decimal("0"),
        order_type="limit",
    )

    resolved = resolve_strategy_offsets(config, None)

    with pytest.raises(ValueError, match="Reference price must be greater than zero"):
        compute_limit_price(order, resolved)


@pytest.mark.parametrize(
    "symbol",
    ["", "aapl1", "AAPL!"],
)
def test_validate_order_request_symbol(symbol: str) -> None:
    config = OrderManagementConfig.default()
    order = OrderRequest(
        symbol=symbol,
        side="BUY",
        quantity=1,
        reference_price=Decimal("10"),
        order_type="limit",
    )

    with pytest.raises(ValueError, match="symbol"):
        validate_order_request(order, config)


def test_validate_order_request_invalid_quantity() -> None:
    config = OrderManagementConfig.default()
    order = OrderRequest(
        symbol="AAPL",
        side="BUY",
        quantity=0,
        reference_price=Decimal("10"),
        order_type="limit",
    )

    with pytest.raises(ValueError, match="quantity"):
        validate_order_request(order, config)


def test_validate_order_request_invalid_reference_price() -> None:
    config = OrderManagementConfig.default()
    order = OrderRequest(
        symbol="AAPL",
        side="BUY",
        quantity=1,
        reference_price=Decimal("0"),
        order_type="limit",
    )

    with pytest.raises(ValueError, match="Reference price"):
        validate_order_request(order, config)


def test_validate_order_request_invalid_order_type() -> None:
    config = OrderManagementConfig.default()
    order = OrderRequest(
        symbol="AAPL",
        side="BUY",
        quantity=1,
        reference_price=Decimal("10"),
        order_type="market",
    )

    with pytest.raises(UnsupportedOrderTypeError):
        validate_order_request(order, config)


def test_enforce_slippage_invalid_reference() -> None:
    from src.trading_bot.order_management.calculator import _enforce_slippage

    with pytest.raises(ValueError, match="positive for slippage"):
        _enforce_slippage(Decimal("0"), Decimal("1"), 0.5)


def test_compute_limit_price_negative_adjusted() -> None:
    config = OrderManagementConfig.from_dict(
        {
            "offset_mode": "absolute",
            "buy_offset": 10,
            "sell_offset": 0.0,
        }
    )

    order = OrderRequest(
        symbol="TSLA",
        side="BUY",
        quantity=1,
        reference_price=Decimal("5"),
        order_type="limit",
    )

    resolved = resolve_strategy_offsets(config, None)

    with pytest.raises(ValueError, match="Computed limit price must be positive"):
        compute_limit_price(order, resolved)
