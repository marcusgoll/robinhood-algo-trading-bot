"""
Main Entry Point for Trading Bot

Provides CLI interface for starting the trading bot with startup sequence.

Enforces Constitution v1.0.0:
- §Safety_First: Comprehensive startup validation before trading
- §Pre_Deploy: All systems checked before entering trading loop
- §Security: Credentials loaded from environment, never logged

Usage:
    python -m trading_bot --dry-run        # Validate startup without trading
    python -m trading_bot --json           # Machine-readable output
    python -m trading_bot                  # Normal startup and trading
"""

import argparse
import sys

# Configure UTF-8 output for Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Namespace with parsed arguments:
        - mode (str): Operation mode (trade, dashboard)
        - dry_run (bool): Run validation without entering trading loop
        - json (bool): Output status as JSON for machine parsing

    T037 [GREEN→T036]: Implementation for parse_arguments() test
    T026 [P]: Added dashboard subcommand support
    """
    parser = argparse.ArgumentParser(
        description="Robinhood Trading Bot - Automated trading system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --dry-run                         Validate startup without trading
  %(prog)s --json                            Machine-readable JSON output
  %(prog)s dashboard                         Launch CLI dashboard
  %(prog)s orchestrator --orchestrator-mode paper   LLM-enhanced trading (paper mode)
  %(prog)s orchestrator --orchestrator-mode live    LLM-enhanced trading (live mode)
  %(prog)s                                   Normal startup and trading
        """
    )
    parser.add_argument(
        "mode",
        nargs="?",
        default="trade",
        choices=["trade", "dashboard", "generate-watchlist", "orchestrator"],
        help="Operation mode: trade (default), dashboard, generate-watchlist, or orchestrator"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run startup validation without entering trading loop"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output status as JSON for machine parsing"
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Preview watchlist without saving (generate-watchlist mode only)"
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save generated watchlist to config.json (generate-watchlist mode only)"
    )
    parser.add_argument(
        "--sectors",
        type=str,
        help="Comma-separated sectors to include (e.g., 'technology,biopharmaceutical')"
    )
    parser.add_argument(
        "--orchestrator-mode",
        type=str,
        choices=["live", "paper", "backtest"],
        default="paper",
        help="Orchestrator operation mode: live, paper (default), or backtest"
    )
    return parser.parse_args()


def main() -> int:
    """Main entry point for trading bot.

    Orchestrates:
    1. Parse command-line arguments
    2. Load configuration from environment and config.json
    3. Run startup sequence (validation, initialization)
    4. Enter trading loop (unless --dry-run)

    Returns:
        Exit code:
        - 0: Success
        - 1: Configuration error
        - 2: Validation error
        - 3: Initialization failure
        - 130: Interrupted by user (Ctrl+C)

    T039 [GREEN→T038]: Implementation for main() test
    """
    try:
        args = parse_arguments()

        # Handle dashboard mode
        if args.mode == "dashboard":
            from .dashboard.__main__ import main as dashboard_main
            return dashboard_main()

        # Handle generate-watchlist mode
        if args.mode == "generate-watchlist":
            from .cli.generate_watchlist import generate_watchlist_command
            return generate_watchlist_command(args)

        # Handle orchestrator mode
        if args.mode == "orchestrator":
            import threading
            from .config import Config
            from .orchestrator import TradingOrchestrator

            # Try to import crypto orchestrator (may not be available if crypto classes missing)
            try:
                from .orchestrator.crypto_orchestrator import CryptoOrchestrator, HAS_CRYPTO
            except ImportError:
                CryptoOrchestrator = None
                HAS_CRYPTO = False

            print(f"\nStarting LLM-enhanced trading orchestrator in {args.orchestrator_mode} mode...")

            # Load configuration
            config = Config.from_env_and_json()

            # Initialize stock orchestrator without authentication (paper trading uses Alpaca data API only)
            # TODO: For live trading, integrate Alpaca TradingClient here:
            #   from alpaca.trading.client import TradingClient
            #   trading_client = TradingClient(api_key=..., secret_key=..., paper=True/False)
            stock_orchestrator = TradingOrchestrator(
                config=config,
                auth=None,  # No auth needed for paper mode
                mode=args.orchestrator_mode
            )

            print(f"\nStock Orchestrator initialized. Mode: {args.orchestrator_mode}")
            print("Daily budget: $5.00")
            print("Scheduled workflows:")
            print("  - 6:30am EST: Pre-market screening")
            print("  - 9:30am EST: Market open execution")
            print("  - 10:00am, 11:00am, 2:00pm EST: Intraday monitoring")
            print("  - 4:00pm EST: End-of-day review")
            print("  - Friday 4:05pm EST: Weekly review")

            # Initialize crypto orchestrator if enabled and available
            crypto_orchestrator = None
            crypto_thread = None

            if config.crypto.enabled and HAS_CRYPTO and CryptoOrchestrator is not None:
                print(f"\nCrypto trading enabled. Initializing 24/7 crypto orchestrator...")
                crypto_orchestrator = CryptoOrchestrator(
                    crypto_config=config.crypto,
                    claude_manager=stock_orchestrator.claude_manager,  # Share LLM manager
                    mode=config.crypto.mode
                )

                # Start crypto orchestrator in background thread
                crypto_thread = threading.Thread(
                    target=crypto_orchestrator.run_loop,
                    daemon=True,
                    name="CryptoOrchestrator"
                )
                crypto_thread.start()
                print(f"Crypto Orchestrator running in background (24/7)")
            elif config.crypto.enabled and not HAS_CRYPTO:
                print(f"\nCrypto trading enabled in config but crypto classes not available (crypto module incomplete)")
            else:
                print(f"\nCrypto trading disabled")

            print("\nPress Ctrl+C to stop\n")

            try:
                # Run stock orchestrator in main thread
                stock_orchestrator.run_loop()
                return 0
            except KeyboardInterrupt:
                print("\n\nOrchestrators stopped by user")
                stock_orchestrator.stop()
                if crypto_orchestrator:
                    crypto_orchestrator.stop()
                return 130
            except Exception as e:
                print(f"\n\nOrchestrator error: {e}")
                import traceback
                traceback.print_exc()
                stock_orchestrator.stop()
                if crypto_orchestrator:
                    crypto_orchestrator.stop()
                return 3

        # Load configuration
        from .config import Config
        config = Config.from_env_and_json()

        # Run startup sequence
        from .startup import StartupOrchestrator
        orchestrator = StartupOrchestrator(
            config=config,
            dry_run=args.dry_run,
            json_output=args.json
        )
        result = orchestrator.run()

        # Handle result
        if result.status == "ready":
            if args.dry_run:
                return 0  # Success - dry run complete

            # Enter trading loop
            if hasattr(orchestrator, 'bot') and orchestrator.bot:
                try:
                    import asyncio

                    orchestrator.bot.start()

                    # Run async trading loop with heartbeat and momentum scanning
                    print("\n🤖 Bot running with heartbeat and momentum scanning... Press Ctrl+C to stop")
                    asyncio.run(orchestrator.bot.run_trading_loop())

                except KeyboardInterrupt:
                    print("\n\n⚠️  Trading interrupted by user")
                    orchestrator.bot.stop()
                    return 130
                except Exception as e:
                    print(f"\n❌ Trading error: {e}")
                    import traceback
                    traceback.print_exc()
                    orchestrator.bot.stop()
                    return 3
            else:
                print("\n❌ Bot not initialized")
                return 3
        else:
            # Startup blocked
            if not args.json:
                print("\n❌ Startup failed:")
                for error in result.errors:
                    print(f"  - {error}")

            # Determine exit code based on first error
            if result.errors:
                error_msg = result.errors[0].lower()
                if "configuration" in error_msg or "credentials" in error_msg:
                    return 1  # Configuration error
                elif "validation" in error_msg or "phase-mode" in error_msg or "phase" in error_msg or "cannot use live" in error_msg:
                    return 2  # Validation error
                else:
                    return 3  # Initialization failure
            return 3  # Unknown error

    except KeyboardInterrupt:
        print("\n\n⚠️  Startup interrupted by user")
        return 130  # Standard exit code for SIGINT

    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
