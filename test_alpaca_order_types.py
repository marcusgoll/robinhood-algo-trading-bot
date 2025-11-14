#!/usr/bin/env python3
"""Test different Alpaca order types for crypto paper trading."""

import os
import time
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

# Initialize client
api_key = os.getenv('ALPACA_API_KEY')
secret_key = os.getenv('ALPACA_SECRET_KEY')

trading_client = TradingClient(api_key=api_key, secret_key=secret_key, paper=True)

print("=" * 70)
print("TESTING ALPACA CRYPTO ORDER TYPES FOR PAPER TRADING")
print("=" * 70)

# Test 1: Market Order with notional (dollar amount)
print("\n" + "=" * 70)
print("TEST 1: Market Order with Notional Amount ($10)")
print("=" * 70)

try:
    market_order = MarketOrderRequest(
        symbol="BTC/USD",
        notional=10.0,  # $10 worth
        side=OrderSide.BUY,
        time_in_force=TimeInForce.DAY
    )

    print(f"Placing MARKET order: $10 BTC/USD (DAY)")
    response1 = trading_client.submit_order(market_order)

    print(f"✅ Order placed!")
    print(f"   ID: {response1.id}")
    print(f"   Status: {response1.status}")
    print(f"   Notional: ${response1.notional}")

    time.sleep(3)

    status1 = trading_client.get_order_by_id(response1.id)
    print(f"Status after 3s: {status1.status}")
    if status1.filled_qty:
        print(f"✅ FILLED! Qty: {status1.filled_qty}")
    else:
        print(f"❌ NOT FILLED (Qty: {status1.filled_qty})")

except Exception as e:
    print(f"❌ Error: {e}")

# Test 2: Market Order with IOC
print("\n" + "=" * 70)
print("TEST 2: Market Order with Notional + IOC (Immediate or Cancel)")
print("=" * 70)

try:
    market_ioc = MarketOrderRequest(
        symbol="ETH/USD",
        notional=10.0,
        side=OrderSide.BUY,
        time_in_force=TimeInForce.IOC  # Immediate or Cancel
    )

    print(f"Placing MARKET order: $10 ETH/USD (IOC)")
    response2 = trading_client.submit_order(market_ioc)

    print(f"✅ Order placed!")
    print(f"   ID: {response2.id}")
    print(f"   Status: {response2.status}")

    time.sleep(3)

    status2 = trading_client.get_order_by_id(response2.id)
    print(f"Status after 3s: {status2.status}")
    if status2.filled_qty:
        print(f"✅ FILLED! Qty: {status2.filled_qty}")
    else:
        print(f"❌ NOT FILLED - Status: {status2.status}")

except Exception as e:
    print(f"❌ Error: {e}")

# Test 3: Market Order with FOK (Fill or Kill)
print("\n" + "=" * 70)
print("TEST 3: Market Order with Notional + FOK (Fill or Kill)")
print("=" * 70)

try:
    market_fok = MarketOrderRequest(
        symbol="LINK/USD",
        notional=10.0,
        side=OrderSide.BUY,
        time_in_force=TimeInForce.FOK  # Fill or Kill
    )

    print(f"Placing MARKET order: $10 LINK/USD (FOK)")
    response3 = trading_client.submit_order(market_fok)

    print(f"✅ Order placed!")
    print(f"   ID: {response3.id}")
    print(f"   Status: {response3.status}")

    time.sleep(3)

    status3 = trading_client.get_order_by_id(response3.id)
    print(f"Status after 3s: {status3.status}")
    if status3.filled_qty:
        print(f"✅ FILLED! Qty: {status3.filled_qty}")
    else:
        print(f"❌ NOT FILLED - Status: {status3.status}")

except Exception as e:
    print(f"❌ Error: {e}")

# Check final positions
print("\n" + "=" * 70)
print("FINAL CHECK: Positions Created")
print("=" * 70)

positions = trading_client.get_all_positions()
if positions:
    for pos in positions:
        print(f"✅ {pos.symbol}: {pos.qty} shares @ ${float(pos.avg_entry_price):.4f}")
else:
    print("❌ No positions created")

print("\n" + "=" * 70)
print("RECOMMENDATION")
print("=" * 70)
print("Use whichever order type created actual filled positions above.")
print("For crypto paper trading, market orders with notional+DAY or notional+IOC")
print("typically work better than limit orders which stay in NEW status indefinitely.")
print("=" * 70)
