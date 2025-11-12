#!/usr/bin/env python3
"""Check Alpaca paper trading account status."""

import os
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient

# Load environment variables
load_dotenv()

api_key = os.getenv("ALPACA_API_KEY")
secret_key = os.getenv("ALPACA_SECRET_KEY")

# Initialize trading client (paper=True)
client = TradingClient(api_key=api_key, secret_key=secret_key, paper=True)

# List all orders
print("=" * 60)
print("ALL ORDERS")
print("=" * 60)
try:
    orders = client.get_orders()
    if orders:
        for i, order in enumerate(orders[:10]):  # Show last 10
            print(f"\nSymbol: {order.symbol}")
            print(f"  Order ID: {order.id}")
            print(f"  Status: {order.status}")
            print(f"  Side: {order.side}")
            print(f"  Type: {order.type}")
            print(f"  Qty: {order.qty}")
            print(f"  Filled: {order.filled_qty}/{order.qty if order.qty else 'N/A'}")
            if order.limit_price:
                print(f"  Limit Price: ${float(order.limit_price):.4f}")
            print(f"  TIF: {order.time_in_force}")
    else:
        print("No orders")
except Exception as e:
    print(f"[ERROR] {e}")

# List all positions
print("\n" + "=" * 60)
print("POSITIONS")
print("=" * 60)
try:
    positions = client.get_all_positions()
    if positions:
        for pos in positions:
            pnl = float(pos.unrealized_pl)
            pnl_pct = float(pos.unrealized_plpc) * 100
            print(f"\nSymbol: {pos.symbol}")
            print(f"  Qty: {pos.qty}")
            print(f"  Avg Entry: ${float(pos.avg_entry_price):.4f}")
            print(f"  Current: ${float(pos.current_price):.4f}")
            print(f"  P&L: ${pnl:.2f} ({pnl_pct:+.2f}%)")
            print(f"  Market Value: ${float(pos.market_value):.2f}")
    else:
        print("No positions")
except Exception as e:
    print(f"[ERROR] {e}")

# Account info
print("\n" + "=" * 60)
print("ACCOUNT")
print("=" * 60)
try:
    account = client.get_account()
    print(f"Cash: ${float(account.cash):.2f}")
    print(f"Portfolio Value: ${float(account.portfolio_value):.2f}")
    print(f"Buying Power: ${float(account.buying_power):.2f}")
    print(f"Equity: ${float(account.equity):.2f}")
except Exception as e:
    print(f"[ERROR] {e}")
