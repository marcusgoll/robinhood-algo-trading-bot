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


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Namespace with parsed arguments:
        - dry_run (bool): Run validation without entering trading loop
        - json (bool): Output status as JSON for machine parsing

    T037 [GREEN→T036]: Implementation for parse_arguments() test
    """
    parser = argparse.ArgumentParser(
        description="Robinhood Trading Bot - Automated trading system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --dry-run        Validate startup without trading
  %(prog)s --json           Machine-readable JSON output
  %(prog)s                  Normal startup and trading
        """
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
            # TODO: Enter trading loop here (future work)
            return 0
        else:
            # Startup blocked
            if not args.json:
                print(f"\n❌ Startup failed:")
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
