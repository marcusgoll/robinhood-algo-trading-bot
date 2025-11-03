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
  %(prog)s --dry-run        Validate startup without trading
  %(prog)s --json           Machine-readable JSON output
  %(prog)s dashboard        Launch CLI dashboard
  %(prog)s                  Normal startup and trading
        """
    )
    parser.add_argument(
        "mode",
        nargs="?",
        default="trade",
        choices=["trade", "dashboard", "generate-watchlist"],
        help="Operation mode: trade (default), dashboard, or generate-watchlist"
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
