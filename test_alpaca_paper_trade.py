#!/usr/bin/env python3
"""
Test script to execute a real Alpaca paper trade order.
"""
import sys
import os
sys.path.insert(0, "/app/src")

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from datetime import datetime

print("=" * 60)
print("ALPACA PAPER TRADING TEST")
print("=" * 60)

# Get Alpaca credentials from environment
api_key = os.getenv('ALPACA_API_KEY')
api_secret = os.getenv('ALPACA_SECRET_KEY')

print(f"\nAPI Key present: {bool(api_key)}")
print(f"API Secret present: {bool(api_secret)}")

if not api_key or not api_secret:
    print("\n❌ ERROR: Alpaca API credentials not found!")
    sys.exit(1)

# Initialize Alpaca Trading Client in paper mode
print("\nInitializing Alpaca Trading Client (paper mode)...")
trading_client = TradingClient(api_key=api_key, secret_key=api_secret, paper=True)

print("✓ Trading client initialized")

# Get account info
print("\nFetching account info...")
account = trading_client.get_account()
print(f"✓ Account Status: {account.status}")
print(f"  Buying Power: ${float(account.buying_power):,.2f}")
print(f"  Cash: ${float(account.cash):,.2f}")
print(f"  Portfolio Value: ${float(account.portfolio_value):,.2f}")

# Prepare test order
symbol = "AAPL"
qty = 1  # Small test order: 1 share
order_type = "market"

print(f"\n{'=' * 60}")
print("SUBMITTING TEST ORDER")
print(f"{'=' * 60}")
print(f"  Symbol: {symbol}")
print(f"  Quantity: {qty} shares")
print(f"  Side: BUY")
print(f"  Type: {order_type.upper()}")
print(f"  Time in Force: DAY")

# Create market order request
order_data = MarketOrderRequest(
    symbol=symbol,
    qty=qty,
    side=OrderSide.BUY,
    time_in_force=TimeInForce.DAY
)

try:
    # Submit order
    print("\nSubmitting order to Alpaca...")
    order = trading_client.submit_order(order_data=order_data)

    print(f"\n{'=' * 60}")
    print("✓ ORDER SUBMITTED SUCCESSFULLY!")
    print(f"{'=' * 60}")
    print(f"  Order ID: {order.id}")
    print(f"  Symbol: {order.symbol}")
    print(f"  Quantity: {order.qty}")
    print(f"  Side: {order.side}")
    print(f"  Type: {order.type}")
    print(f"  Status: {order.status}")
    print(f"  Time in Force: {order.time_in_force}")
    print(f"  Submitted At: {order.submitted_at}")

    if order.filled_at:
        print(f"  Filled At: {order.filled_at}")
        print(f"  Filled Avg Price: ${float(order.filled_avg_price):,.2f}")

    print(f"\n{'=' * 60}")
    print("TEST COMPLETE - Paper trade executed on Alpaca!")
    print(f"{'=' * 60}")

except Exception as e:
    print(f"\n❌ ERROR submitting order: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# List recent orders
print("\nFetching recent orders...")
try:
    orders = trading_client.get_orders()
    print(f"✓ Total orders in account: {len(orders)}")
    if orders:
        print("\nMost recent orders:")
        for i, o in enumerate(orders[:5]):
            print(f"  {i+1}. {o.symbol} - {o.side} {o.qty} shares - Status: {o.status}")
except Exception as e:
    print(f"Warning: Could not fetch orders: {e}")

print("\n✓ All tests passed!")
