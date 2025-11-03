"""
Generate Watchlist CLI Command

Generates dynamic stock watchlists using screener + sector tags.

Usage:
    python -m trading_bot generate-watchlist --preview
    python -m trading_bot generate-watchlist --save
    python -m trading_bot generate-watchlist --sectors technology,biopharmaceutical --preview

Constitution v1.0.0:
- §Code_Quality: Type hints required
- §Data_Integrity: Validate all inputs
"""

import argparse
import json
import logging
import sys
from decimal import Decimal
from pathlib import Path

# Configure UTF-8 output for Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


def generate_watchlist_command(args: argparse.Namespace) -> int:
    """Execute generate-watchlist command.

    Args:
        args: Parsed command-line arguments with:
            - preview (bool): Show watchlist without saving
            - save (bool): Save watchlist to config.json
            - sectors (str): Comma-separated sectors (optional)
            - json (bool): Output as JSON

    Returns:
        Exit code (0=success, 1=error)
    """
    try:
        from trading_bot.schemas.watchlist_schemas import (
            TierCriteria,
            WatchlistConfig,
            WatchlistTier,
        )
        from trading_bot.services.screener_service import ScreenerService
        from trading_bot.services.watchlist_service import WatchlistService
        from trading_bot.screener_config import ScreenerConfig
        from trading_bot.market_data.market_data_service import MarketDataService
        from trading_bot.logging.screener_logger import ScreenerLogger
        from trading_bot.config import Config

        # Default sector-based configuration
        config = _build_default_config(args.sectors)

        # Initialize services
        screener_config = ScreenerConfig()
        bot_config = Config.from_env_and_json()
        market_data_service = MarketDataService(bot_config)
        screener_logger = ScreenerLogger(screener_config.LOG_DIR)
        screener_service = ScreenerService(market_data_service, screener_logger, screener_config)
        watchlist_service = WatchlistService(screener_service, config)

        # Generate watchlist
        print("\n🔍 Generating dynamic watchlist...\n")
        result = watchlist_service.generate_watchlist()

        # Display results
        if args.json:
            print(json.dumps(result.to_dict(), indent=2))
        else:
            _print_results(result)

        # Save to config.json if requested
        if args.save:
            _save_to_config(result, config)
            print("\n✅ Watchlist saved to config.json")
            print("   Restart bot to use new watchlist")

        return 0

    except Exception as e:
        logger.error(f"Watchlist generation failed: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        return 1


def _build_default_config(sectors_arg: str | None) -> "WatchlistConfig":
    """Build default watchlist configuration.

    Args:
        sectors_arg: Comma-separated sectors string (e.g., "technology,biopharmaceutical")

    Returns:
        WatchlistConfig with tier-based setup
    """
    from trading_bot.schemas.watchlist_schemas import (
        TierCriteria,
        WatchlistConfig,
        WatchlistTier,
    )

    # Parse sectors if provided
    if sectors_arg:
        sectors = [s.strip() for s in sectors_arg.split(",")]
        print(f"Using sectors: {', '.join(sectors)}\n")
    else:
        # Default sectors
        sectors = ["technology", "biopharmaceutical", "energy", "consumer-product"]
        print(f"Using default sectors: {', '.join(sectors)}\n")

    # Define tiers
    # Note: No min_daily_change filter - momentum scanner detects movers in real-time
    tier1 = WatchlistTier(
        name="mega_cap",
        enabled=True,
        sectors=sectors,
        criteria=TierCriteria(
            min_price=Decimal("50.0"),
            # Note: Volume filter disabled - requires market hours + fundamentals data
        ),
        max_symbols=20,
    )

    tier2 = WatchlistTier(
        name="large_cap",
        enabled=True,
        sectors=sectors,
        criteria=TierCriteria(
            min_price=Decimal("10.0"),
            max_price=Decimal("50.0"),
            # Note: Volume/float filters disabled - requires market hours + fundamentals data
        ),
        max_symbols=25,
    )

    tier3 = WatchlistTier(
        name="mid_cap",
        enabled=False,  # Start conservative
        sectors=["biopharmaceutical"],  # Only biotech for high volatility
        criteria=TierCriteria(
            min_price=Decimal("2.0"),
            max_price=Decimal("10.0"),
            relative_volume=5.0,
            min_daily_change=10.0,
            float_max=20,
        ),
        max_symbols=10,
    )

    # Fallback symbols (current hardcoded list)
    fallback = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "META",
        "TSLA", "NVDA", "AMD", "INTC", "NFLX",
        "DIS", "BA", "JPM", "V", "MA",
    ]

    return WatchlistConfig(
        mode="dynamic",
        auto_refresh=False,  # Manual for now
        refresh_schedule=None,
        tiers=[tier1, tier2, tier3],
        fallback_symbols=fallback,
    )


def _print_results(result: "GeneratedWatchlist") -> None:
    """Print watchlist generation results in human-readable format.

    Args:
        result: GeneratedWatchlist with symbols and metadata
    """
    print("=" * 60)
    print("GENERATED WATCHLIST")
    print("=" * 60)
    print(f"\n📊 Total Symbols: {result.total_symbols}")
    print(f"⏱️  Generation Time: {result.execution_time_ms:.2f}ms")
    print(f"🕒 Generated At: {result.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")

    # Tier breakdown
    print("\n📈 Tier Breakdown:")
    for tier_name, count in result.tier_breakdown.items():
        print(f"  • {tier_name}: {count} symbols")

    # Warnings
    if result.has_warnings():
        print("\n⚠️  Warnings:")
        for warning in result.warnings:
            print(f"  • {warning}")

    # Symbols by tier
    print("\n📋 Symbols:")
    for tier_name in result.tier_breakdown:
        tier_symbols = [s for s in result.symbols]  # TODO: Track per-tier in result
        if tier_symbols:
            print(f"\n  {tier_name.upper()}:")
            # Print in columns
            for i in range(0, len(tier_symbols[:20]), 5):
                row = tier_symbols[i:i+5]
                print(f"    {', '.join(row)}")
            if len(tier_symbols) > 20:
                print(f"    ... and {len(tier_symbols) - 20} more")

    # Full list
    print(f"\n📝 Full List ({result.total_symbols} symbols):")
    symbols_str = ", ".join(result.symbols)
    # Wrap at 80 characters
    lines = []
    current_line = "  "
    for symbol in result.symbols:
        if len(current_line) + len(symbol) + 2 > 78:
            lines.append(current_line.rstrip(", "))
            current_line = "  "
        current_line += f"{symbol}, "
    if current_line.strip():
        lines.append(current_line.rstrip(", "))
    print("\n".join(lines))

    print("\n" + "=" * 60)


def _save_to_config(result: "GeneratedWatchlist", config: "WatchlistConfig") -> None:
    """Save generated watchlist to config.json.

    Args:
        result: GeneratedWatchlist with symbols
        config: WatchlistConfig used for generation

    Raises:
        IOError: If config.json cannot be written
    """
    config_path = Path("config.json")

    # Load existing config or create new
    if config_path.exists():
        with open(config_path, "r") as f:
            config_data = json.load(f)
    else:
        config_data = {}

    # Add momentum_scanning section
    config_data["momentum_scanning"] = {
        "mode": "dynamic",
        "generated_at": result.generated_at.isoformat(),
        "symbols": result.symbols,
        "tier_breakdown": result.tier_breakdown,
        "total_symbols": result.total_symbols,
        "execution_time_ms": result.execution_time_ms,
        "tiers": {
            tier.name: {
                "enabled": tier.enabled,
                "sectors": tier.sectors,
                "max_symbols": tier.max_symbols,
                "criteria": {
                    "min_price": str(tier.criteria.min_price) if tier.criteria.min_price else None,
                    "max_price": str(tier.criteria.max_price) if tier.criteria.max_price else None,
                    "relative_volume": tier.criteria.relative_volume,
                    "min_daily_change": tier.criteria.min_daily_change,
                    "float_max": tier.criteria.float_max,
                }
            }
            for tier in config.tiers
        },
        "fallback_symbols": config.fallback_symbols,
    }

    # Save with pretty formatting
    with open(config_path, "w") as f:
        json.dump(config_data, f, indent=2)

    logger.info(f"Saved watchlist to {config_path}")
