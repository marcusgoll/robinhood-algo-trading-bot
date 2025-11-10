#!/usr/bin/env python3
"""
Sync trading bot watchlist to Alpaca for frontend visibility.
"""
import os
import sys
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import CreateWatchlistRequest

# Screened symbols from latest run (removed PWCDF - inactive/not tradable)
SYMBOLS = [
    "BNTX", "FHLC", "HCA", "NVZMY", "JAZZ", "GIB", "NHC", "INCY", "TRMB", "BAESY",
    "ADBE", "HOLX", "MOH", "ZTS", "ITRI", "WST", "MKTX", "VEEV", "DGX", "ICUI",
    "HCSG", "IDYA", "EXTR", "NABZY", "BWA", "GLPG", "SRPT", "BKD", "TAK", "GDS",
    "FLGT", "LOB", "PHG", "FONR", "AVNS", "CC", "EJPRY", "DNLI", "EGAN",
    "SEDG", "MGIC", "CHT", "EQNR", "CSWC"
]

WATCHLIST_NAME = "TradingBot-Active"


def main():
    """Sync watchlist to Alpaca."""
    api_key = os.getenv("ALPACA_API_KEY")
    secret_key = os.getenv("ALPACA_SECRET_KEY")

    if not api_key or not secret_key:
        print("❌ ALPACA_API_KEY and ALPACA_SECRET_KEY required")
        sys.exit(1)

    client = TradingClient(api_key, secret_key, paper=True)

    # Delete existing bot watchlists
    watchlists = client.get_watchlists()
    for wl in watchlists:
        if "TradingBot" in wl.name or "tradingbot" in wl.name.lower():
            try:
                client.delete_watchlist(wl.id)
                print(f"🗑️  Deleted old watchlist: {wl.name}")
            except Exception as e:
                print(f"⚠️  Could not delete {wl.name}: {e}")

    # Create new watchlist
    try:
        request = CreateWatchlistRequest(
            name=WATCHLIST_NAME,
            symbols=SYMBOLS
        )
        watchlist = client.create_watchlist(request)

        print(f"✅ Created Alpaca watchlist: {watchlist.name}")
        print(f"📊 Total symbols: {len(SYMBOLS)}")
        print(f"🆔 Watchlist ID: {watchlist.id}")
        print(f"\n📋 Symbols:")
        for i in range(0, len(SYMBOLS), 10):
            print(f"   {', '.join(SYMBOLS[i:i+10])}")

    except Exception as e:
        print(f"❌ Error creating watchlist: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
