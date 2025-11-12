#!/usr/bin/env python3
"""Cancel all open crypto orders in Alpaca paper trading account."""

import os
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient

# Load environment variables
load_dotenv()

api_key = os.getenv("ALPACA_API_KEY")
secret_key = os.getenv("ALPACA_SECRET_KEY")

# Initialize trading client (paper=True)
client = TradingClient(api_key=api_key, secret_key=secret_key, paper=True)

# Cancel all open orders
try:
    cancel_response = client.cancel_orders()
    print(f"[OK] Cancelled all open orders")
    print(f"Response: {cancel_response}")
except Exception as e:
    print(f"[ERROR] Failed to cancel orders: {e}")

# List remaining orders
try:
    orders = client.get_orders()
    if orders:
        print(f"\n[INFO] Remaining orders: {len(orders)}")
        for order in orders:
            print(f"  - {order.symbol}: {order.id} ({order.status})")
    else:
        print("\n[OK] No open orders")
except Exception as e:
    print(f"[ERROR] Failed to list orders: {e}")
