#!/usr/bin/env python3
"""Test quantity-based market orders for Alpaca crypto paper trading."""

import os
import time
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

# Initialize client
api_key = os.getenv('ALPACA_API_KEY')
secret_key = os.getenv('ALPACA_SECRET_KEY')

trading_client = TradingClient(api_key=api_key, secret_key=secret_key, paper=True)

print("=" * 70)
print("TESTING QTY-BASED MARKET ORDERS FOR CRYPTO")
print("=" * 70)

# Test: Market Order with quantity + GTC
print("\n" + "=" * 70)
print("TEST: Market Order with Quantity + GTC")
print("=" * 70)

try:
    # Small quantity of BTC (~$10 worth at $100k = 0.0001 BTC)
    market_order = MarketOrderRequest(
        symbol="BTC/USD",
        qty=0.0001,
        side=OrderSide.BUY,
        time_in_force=TimeInForce.GTC
    )

    print(f"Placing MARKET order: 0.0001 BTC/USD (GTC)")
    response = trading_client.submit_order(market_order)

    print(f"✅ Order placed!")
    print(f"   ID: {response.id}")
    print(f"   Status: {response.status}")
    print(f"   Qty: {response.qty}")
    print(f"   Side: {response.side}")

    # Wait and check status
    for i in range(1, 4):
        time.sleep(2)
        status = trading_client.get_order_by_id(response.id)
        print(f"\nCheck #{i} (after {i*2}s):")
        print(f"   Status: {status.status}")
        print(f"   Filled Qty: {status.filled_qty}")

        if status.status == "filled":
            print(f"\n✅✅✅ ORDER FILLED! ✅✅✅")
            print(f"   Filled Qty: {status.filled_qty}")
            print(f"   Filled Avg Price: ${status.filled_avg_price}")
            break
        elif status.status in ["canceled", "expired", "rejected"]:
            print(f"\n❌ Order {status.status}")
            break

    # Final check
    print("\n" + "=" * 70)
    print("Final Position Check")
    print("=" * 70)

    positions = trading_client.get_all_positions()
    btc_position = [p for p in positions if "BTC" in p.symbol]

    if btc_position:
        pos = btc_position[0]
        print(f"✅ BTC Position Created!")
        print(f"   Symbol: {pos.symbol}")
        print(f"   Qty: {pos.qty}")
        print(f"   Avg Entry: ${float(pos.avg_entry_price):,.2f}")
        print(f"   Current Price: ${float(pos.current_price):,.2f}")

        # Try to sell it
        print("\n" + "=" * 70)
        print("TEST: Selling the position")
        print("=" * 70)

        sell_order = MarketOrderRequest(
            symbol=pos.symbol,
            qty=float(pos.qty),
            side=OrderSide.SELL,
            time_in_force=TimeInForce.GTC
        )

        print(f"Placing SELL order: {pos.qty} {pos.symbol} (GTC)")
        sell_response = trading_client.submit_order(sell_order)

        print(f"✅ SELL order placed!")
        print(f"   ID: {sell_response.id}")
        print(f"   Status: {sell_response.status}")

        time.sleep(4)

        sell_status = trading_client.get_order_by_id(sell_response.id)
        print(f"\nSELL order final status: {sell_status.status}")
        if sell_status.filled_qty:
            print(f"✅ SOLD! Qty: {sell_status.filled_qty}")
        else:
            print(f"❌ Not filled yet")

    else:
        print("❌ No BTC position created")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("TEST COMPLETE")
print("=" * 70)
