"""
Test script to debug Alpaca and Yahoo Finance data fetching.

This script tests the HistoricalDataManager directly to identify
why data fetching is failing in the backtest harness.
"""

import os
import sys
from datetime import UTC, datetime

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from trading_bot.backtest.historical_data_manager import HistoricalDataManager


def test_alpaca_direct():
    """Test Alpaca API directly."""
    print("=" * 60)
    print("TEST 1: Alpaca API Direct")
    print("=" * 60)

    api_key = os.getenv('ALPACA_API_KEY')
    api_secret = os.getenv('ALPACA_SECRET_KEY')

    print(f"API Key present: {bool(api_key)}")
    print(f"API Secret present: {bool(api_secret)}")

    if not api_key or not api_secret:
        print("ERROR: Alpaca API credentials not found in environment!")
        return False

    try:
        from alpaca.data.enums import Adjustment
        from alpaca.data.historical import StockHistoricalDataClient
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame

        print("\n1. Creating Alpaca client...")
        client = StockHistoricalDataClient(api_key=api_key, secret_key=api_secret)
        print("   ✓ Client created successfully")

        print("\n2. Creating request for AAPL (2024-01-01 to 2024-01-31)...")
        request = StockBarsRequest(
            symbol_or_symbols="AAPL",
            timeframe=TimeFrame.Day,
            start=datetime(2024, 1, 1, tzinfo=UTC),
            end=datetime(2024, 1, 31, tzinfo=UTC),
            adjustment=Adjustment.ALL
        )
        print("   ✓ Request created")

        print("\n3. Fetching bars from Alpaca...")
        bars_response = client.get_stock_bars(request)
        print(f"   ✓ Response received: {type(bars_response)}")

        print("\n4. Extracting bars...")
        if "AAPL" in bars_response:
            bars = bars_response["AAPL"]
            print(f"   ✓ Got {len(bars)} bars for AAPL")

            # Print first 3 bars
            print("\n   First 3 bars:")
            for i, bar in enumerate(list(bars)[:3]):
                print(f"     {i+1}. {bar.timestamp.date()} - Close: ${bar.close:.2f}, Volume: {bar.volume:,}")

            return True
        else:
            print("   ✗ AAPL not in response!")
            print(f"   Keys in response: {list(bars_response.keys())}")
            return False

    except Exception as e:
        print(f"   ✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_yahoo_direct():
    """Test Yahoo Finance API directly."""
    print("\n" + "=" * 60)
    print("TEST 2: Yahoo Finance API Direct")
    print("=" * 60)

    try:
        import yfinance as yf

        print("\n1. Fetching AAPL from Yahoo Finance (2024-01-01 to 2024-01-31)...")
        df = yf.download(
            "AAPL",
            start=datetime(2024, 1, 1),
            end=datetime(2024, 1, 31),
            auto_adjust=True,
            progress=False
        )

        if df.empty:
            print("   ✗ No data returned!")
            return False

        print(f"   ✓ Got {len(df)} rows")
        print("\n   First 3 rows:")
        print(df.head(3))

        return True

    except Exception as e:
        print(f"   ✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_historical_data_manager():
    """Test HistoricalDataManager integration."""
    print("\n" + "=" * 60)
    print("TEST 3: HistoricalDataManager Integration")
    print("=" * 60)

    try:
        print("\n1. Initializing HistoricalDataManager...")
        manager = HistoricalDataManager(
            api_key=os.getenv('ALPACA_API_KEY'),
            api_secret=os.getenv('ALPACA_SECRET_KEY'),
            cache_dir=".test_cache",
            cache_enabled=False  # Disable cache for testing
        )
        print("   ✓ Manager initialized")

        print("\n2. Fetching AAPL data (2024-01-01 to 2024-01-31)...")
        bars = manager.fetch_data(
            symbol="AAPL",
            start_date=datetime(2024, 1, 1, tzinfo=UTC),
            end_date=datetime(2024, 1, 31, tzinfo=UTC)
        )

        print(f"   ✓ Got {len(bars)} bars")
        print("\n   First 3 bars:")
        for i, bar in enumerate(bars[:3]):
            print(f"     {i+1}. {bar.timestamp.date()} - Close: ${float(bar.close):.2f}, Volume: {bar.volume:,}")

        return True

    except Exception as e:
        print(f"   ✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "#" * 60)
    print("# TESTING DATA FETCHING")
    print("#" * 60)

    # Load .env file
    from dotenv import load_dotenv
    load_dotenv()

    # Run tests
    alpaca_ok = test_alpaca_direct()
    yahoo_ok = test_yahoo_direct()
    manager_ok = test_historical_data_manager()

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Alpaca API Direct:               {'✓ PASS' if alpaca_ok else '✗ FAIL'}")
    print(f"Yahoo Finance API Direct:        {'✓ PASS' if yahoo_ok else '✗ FAIL'}")
    print(f"HistoricalDataManager Integration: {'✓ PASS' if manager_ok else '✗ FAIL'}")

    if alpaca_ok and yahoo_ok and manager_ok:
        print("\n✓ All tests passed! Data fetching is working correctly.")
        return 0
    else:
        print("\n✗ Some tests failed. See errors above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
