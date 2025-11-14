#!/usr/bin/env python3
"""Test Alpaca paper trading buy and sell functionality."""

import os
import time
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.data.historical import CryptoHistoricalDataClient
from alpaca.data.requests import CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta

# Initialize clients
api_key = os.getenv('ALPACA_API_KEY')
secret_key = os.getenv('ALPACA_SECRET_KEY')

trading_client = TradingClient(api_key=api_key, secret_key=secret_key, paper=True)
data_client = CryptoHistoricalDataClient(api_key=api_key, secret_key=secret_key)

print("=" * 60)
print("ALPACA PAPER TRADING TEST")
print("=" * 60)

# Get account info
print("\n=== Account Info ===")
account = trading_client.get_account()
print(f"Buying Power: ${float(account.buying_power):,.2f}")
print(f"Cash: ${float(account.cash):,.2f}")
print(f"Portfolio Value: ${float(account.portfolio_value):,.2f}")

# Get current positions
print("\n=== Current Positions ===")
positions = trading_client.get_all_positions()
if positions:
    for pos in positions:
        pnl_pct = float(pos.unrealized_plpc) * 100
        print(f"{pos.symbol}: {pos.qty} @ ${float(pos.avg_entry_price):.4f} | "
              f"Current: ${float(pos.current_price):.4f} | "
              f"P&L: ${float(pos.unrealized_pl):.2f} ({pnl_pct:.2f}%)")
else:
    print("No positions")

# Get recent orders
print("\n=== Recent Orders (Last 10) ===")
try:
    from alpaca.trading.requests import GetOrdersRequest
    from alpaca.trading.enums import QueryOrderStatus

    order_request = GetOrdersRequest(
        status=QueryOrderStatus.ALL,
        limit=10
    )
    orders = trading_client.get_orders(filter=order_request)
    if orders:
        for order in orders[:10]:
            filled_info = f"Filled: {order.filled_qty}" if order.filled_qty else ""
            print(f"{order.symbol} {order.side} {order.qty} @ {order.type} | "
                  f"Status: {order.status} | {filled_info} | ID: {order.id}")
    else:
        print("No recent orders")
except Exception as e:
    print(f"Could not fetch orders: {e}")
    orders = []

# Test: Place a small BUY order for BTC
print("\n" + "=" * 60)
print("TEST 1: Placing BUY order for BTCUSD")
print("=" * 60)

try:
    # Get current BTC price
    request_params = CryptoBarsRequest(
        symbol_or_symbols=["BTC/USD"],
        timeframe=TimeFrame.Minute,
        start=datetime.now() - timedelta(minutes=5)
    )
    bars = data_client.get_crypto_bars(request_params)
    latest_bar = bars.df.iloc[-1]
    current_price = float(latest_bar['close'])

    print(f"Current BTC/USD price: ${current_price:,.2f}")

    # Place small limit order at current ask price
    quantity = 0.0001  # Very small amount (~$10)
    limit_price = current_price * 1.001  # Slightly above to ensure fill

    buy_order = LimitOrderRequest(
        symbol="BTC/USD",
        qty=quantity,
        limit_price=limit_price,
        side=OrderSide.BUY,
        time_in_force=TimeInForce.GTC
    )

    print(f"Placing BUY order: {quantity} BTC @ ${limit_price:,.2f} (GTC)")
    buy_response = trading_client.submit_order(buy_order)

    print(f"✅ Order placed successfully!")
    print(f"   Order ID: {buy_response.id}")
    print(f"   Status: {buy_response.status}")
    print(f"   Side: {buy_response.side}")
    print(f"   Qty: {buy_response.qty}")
    print(f"   Limit Price: ${buy_response.limit_price}")

    # Wait and check order status
    print("\nWaiting 5 seconds to check order status...")
    time.sleep(5)

    order_status = trading_client.get_order_by_id(buy_response.id)
    print(f"Order status after 5s: {order_status.status}")
    if order_status.filled_qty:
        print(f"Filled quantity: {order_status.filled_qty}")

    # Test: Place SELL order to close position
    if order_status.status == "filled" and order_status.filled_qty:
        print("\n" + "=" * 60)
        print("TEST 2: Placing SELL order to close position")
        print("=" * 60)

        filled_qty = float(order_status.filled_qty)
        sell_limit = current_price * 0.999  # Slightly below to ensure fill

        sell_order = LimitOrderRequest(
            symbol="BTC/USD",
            qty=filled_qty,
            limit_price=sell_limit,
            side=OrderSide.SELL,
            time_in_force=TimeInForce.IOC  # Immediate or cancel
        )

        print(f"Placing SELL order: {filled_qty} BTC @ ${sell_limit:,.2f} (IOC)")
        sell_response = trading_client.submit_order(sell_order)

        print(f"✅ SELL order placed successfully!")
        print(f"   Order ID: {sell_response.id}")
        print(f"   Status: {sell_response.status}")

        time.sleep(3)

        sell_status = trading_client.get_order_by_id(sell_response.id)
        print(f"SELL order status: {sell_status.status}")

    else:
        print(f"\n⚠️ BUY order not filled (status: {order_status.status}), skipping SELL test")
        print("   This is normal for limit orders in paper trading")

except Exception as e:
    print(f"❌ Error during test: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
