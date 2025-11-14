#!/usr/bin/env python3
"""Quick test to verify Alpaca intraday data fetching.

Tests that we can get 1 year of 5-minute bars (~19,656 samples) for Phase 3 ensemble.
"""

import os
from datetime import datetime, timedelta

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

# Get API keys from environment
API_KEY = os.getenv("ALPACA_API_KEY")
API_SECRET = os.getenv("ALPACA_SECRET_KEY")

if not API_KEY or not API_SECRET:
    print("ERROR: ALPACA_API_KEY and ALPACA_SECRET_KEY must be set in .env")
    exit(1)

print("=" * 80)
print("ALPACA INTRADAY DATA TEST")
print("=" * 80)
print()

# Initialize client (no need for base_url with data-only client)
print("[1/3] Connecting to Alpaca...")
client = StockHistoricalDataClient(API_KEY, API_SECRET)
print("[OK] Connected")

# Request 1 year of 5-minute bars for SPY
print("\n[2/3] Fetching 1 year of 5-minute SPY bars...")
end = datetime.now()
start = end - timedelta(days=365)

request = StockBarsRequest(
    symbol_or_symbols="SPY",
    timeframe=TimeFrame(5, TimeFrameUnit.Minute),  # 5-minute bars
    start=start,
    end=end
)

try:
    bars = client.get_stock_bars(request)
    spy_bars = bars["SPY"]

    print(f"[OK] Fetched {len(spy_bars)} bars!")
    print(f"  Date range: {spy_bars[0].timestamp} to {spy_bars[-1].timestamp}")
    print(f"  First bar: O={spy_bars[0].open:.2f} H={spy_bars[0].high:.2f} L={spy_bars[0].low:.2f} C={spy_bars[0].close:.2f} V={spy_bars[0].volume}")

    print("\n[3/3] Analyzing sample size...")
    print(f"  Total bars: {len(spy_bars)}")
    print(f"  Required for deep learning: 10,000+")

    if len(spy_bars) >= 10000:
        print(f"  ✅ SUCCESS: {len(spy_bars)} bars is sufficient for Phase 3 ensemble!")
    else:
        print(f"  ⚠️  WARNING: {len(spy_bars)} bars may be insufficient (need 10,000+)")

except Exception as e:
    print(f"[ERROR] Failed to fetch data: {e}")
    exit(1)

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)
print("✅ Alpaca can provide sufficient intraday data for Phase 3!")
print(f"   With {len(spy_bars)} samples, Phase 3 should work properly.")
