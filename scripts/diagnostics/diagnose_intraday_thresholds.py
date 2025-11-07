#!/usr/bin/env python3
"""Diagnostic script to find optimal label thresholds for 5-minute intraday data.

Tests different return thresholds and reports class distributions.
"""

import os
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit


def test_threshold(returns, threshold):
    """Test a specific threshold and return class distribution."""
    labels = np.zeros(len(returns), dtype=np.int64)
    labels[returns > threshold] = 0  # BUY
    labels[(returns >= -threshold) & (returns <= threshold)] = 1  # HOLD
    labels[returns < -threshold] = 2  # SELL

    buy_pct = np.mean(labels == 0) * 100
    hold_pct = np.mean(labels == 1) * 100
    sell_pct = np.mean(labels == 2) * 100

    return buy_pct, hold_pct, sell_pct


def main():
    # Get Alpaca credentials
    API_KEY = os.getenv("ALPACA_API_KEY")
    API_SECRET = os.getenv("ALPACA_SECRET_KEY")

    if not API_KEY or not API_SECRET:
        print("ERROR: ALPACA_API_KEY and ALPACA_SECRET_KEY must be set")
        return 1

    print("=" * 80)
    print("INTRADAY THRESHOLD DIAGNOSTIC")
    print("=" * 80)
    print()

    # Fetch 3 months of 5-minute data
    print("Fetching 3 months of SPY 5-minute data from Alpaca...")
    client = StockHistoricalDataClient(API_KEY, API_SECRET)

    end = datetime.now()
    start = end - timedelta(days=90)

    request = StockBarsRequest(
        symbol_or_symbols="SPY",
        timeframe=TimeFrame(5, TimeFrameUnit.Minute),
        start=start,
        end=end
    )

    bars = client.get_stock_bars(request)
    spy_bars = bars["SPY"]

    # Convert to DataFrame
    data = pd.DataFrame({
        "close": [bar.close for bar in spy_bars],
    })

    print(f"[OK] Fetched {len(data)} bars\n")

    # Calculate next-bar returns
    close = data["close"].values
    returns = np.zeros(len(close))
    for i in range(len(close) - 1):
        returns[i] = (close[i + 1] - close[i]) / close[i]
    returns[-1] = 0

    # Calculate return statistics
    print("Return Statistics:")
    print(f"  Mean:   {np.mean(returns)*100:.4f}%")
    print(f"  Median: {np.median(returns)*100:.4f}%")
    print(f"  Std:    {np.std(returns)*100:.4f}%")
    print(f"  Min:    {np.min(returns)*100:.4f}%")
    print(f"  Max:    {np.max(returns)*100:.4f}%")
    print()

    print("Percentiles:")
    percentiles = [1, 5, 10, 25, 50, 75, 90, 95, 99]
    for p in percentiles:
        val = np.percentile(returns, p)
        print(f"  {p:2d}th: {val*100:+.4f}%")
    print()

    # Test different thresholds
    print("=" * 80)
    print("THRESHOLD TESTING")
    print("=" * 80)
    print(f"{'Threshold':>10s}  {'BUY %':>8s}  {'HOLD %':>8s}  {'SELL %':>8s}  {'Balance Score':>14s}")
    print("-" * 80)

    # Test thresholds from 0.01% to 0.20%
    thresholds = [0.0001, 0.0002, 0.0003, 0.0004, 0.0005, 0.0007, 0.001, 0.0012, 0.0015, 0.002]

    best_threshold = None
    best_score = float('inf')

    for thresh in thresholds:
        buy, hold, sell = test_threshold(returns, thresh)

        # Balance score: how far from ideal 33-33-33 distribution
        # Lower is better (0 = perfect balance)
        balance_score = abs(buy - 33.33) + abs(hold - 33.33) + abs(sell - 33.33)

        marker = ""
        if balance_score < best_score:
            best_score = balance_score
            best_threshold = thresh
            marker = " <-- BEST"

        print(f"±{thresh*100:>7.3f}%  {buy:>7.2f}%  {hold:>7.2f}%  {sell:>7.2f}%  {balance_score:>13.2f}{marker}")

    print()
    print("=" * 80)
    print(f"RECOMMENDATION: Use ±{best_threshold*100:.3f}% threshold")
    print(f"  This minimizes class imbalance (balance score: {best_score:.2f})")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
