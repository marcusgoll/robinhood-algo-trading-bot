#!/usr/bin/env python3
"""
Verify Alpaca watchlist status and debug frontend visibility issues.
"""
import os
import sys
from alpaca.trading.client import TradingClient

def main():
    """Verify watchlist and diagnose frontend issues."""
    api_key = os.getenv("ALPACA_API_KEY")
    secret_key = os.getenv("ALPACA_SECRET_KEY")

    if not api_key or not secret_key:
        print("❌ ALPACA_API_KEY and ALPACA_SECRET_KEY required")
        sys.exit(1)

    print(f"🔑 Using API Key: {api_key[:10]}...")
    print(f"🌐 Endpoint: https://paper-api.alpaca.markets\n")

    client = TradingClient(api_key, secret_key, paper=True)

    # Get all watchlists
    print("=" * 60)
    print("📋 ALL WATCHLISTS")
    print("=" * 60)

    watchlists = client.get_watchlists()
    print(f"Total watchlists found: {len(watchlists)}\n")

    if not watchlists:
        print("❌ No watchlists found!")
        sys.exit(1)

    for wl in watchlists:
        print(f"\n📁 Watchlist: {wl.name}")
        print(f"   ID: {wl.id}")
        print(f"   Created: {wl.created_at}")
        print(f"   Updated: {wl.updated_at}")

        # Get detailed watchlist info
        try:
            detailed_wl = client.get_watchlist_by_id(wl.id)
            assets = detailed_wl.assets if hasattr(detailed_wl, 'assets') else []
            symbols = [asset.symbol for asset in assets] if assets else []

            print(f"   Assets: {len(symbols)} symbols")

            if symbols:
                print(f"   Symbols: {', '.join(symbols[:10])}")
                if len(symbols) > 10:
                    print(f"            ... and {len(symbols) - 10} more")
            else:
                print(f"   ⚠️  WARNING: Watchlist has NO assets!")

        except Exception as e:
            print(f"   ❌ Error getting details: {e}")

    # Get account info
    print("\n" + "=" * 60)
    print("👤 ACCOUNT INFO")
    print("=" * 60)

    try:
        account = client.get_account()
        print(f"Account ID: {account.id}")
        print(f"Account Number: {account.account_number}")
        print(f"Status: {account.status}")
        print(f"Trading Blocked: {account.trading_blocked}")
        print(f"Pattern Day Trader: {account.pattern_day_trader}")
    except Exception as e:
        print(f"❌ Error getting account: {e}")

if __name__ == "__main__":
    main()
