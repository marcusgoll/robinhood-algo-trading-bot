"""
Startup validation script.

Validates configuration before bot starts (Constitution v1.0.0 §Pre_Deploy).

Usage:
    python validate_startup.py
"""

from src.trading_bot.config import Config
from src.trading_bot.validator import ConfigValidator, ValidationError
import sys


def main() -> None:
    """Validate configuration on startup."""
    print()
    print("=" * 60)
    print("Pre-Deploy Validation (Constitution v1.0.0)")
    print("=" * 60)
    print()

    try:
        # Load configuration
        print("Loading configuration...")
        config = Config.from_env_and_json()
        print("✅ Configuration loaded")
        print()

        # Run validation
        print("Running validation checks...")
        validator = ConfigValidator(config)
        is_valid, errors, warnings = validator.validate_all(test_api=False)
        print()

        # Print report
        validator.print_report()

        # Exit with appropriate status
        if not is_valid:
            print("❌ Startup blocked: Fix errors before running bot")
            sys.exit(1)

        if warnings:
            print("⚠️  Warnings present, but startup allowed")
            sys.exit(0)

        print("✅ All checks passed - Ready to start bot!")
        sys.exit(0)

    except ValidationError as e:
        print(f"❌ Validation Error: {e}")
        sys.exit(1)

    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        print()
        print("Troubleshooting:")
        print("  1. Ensure .env file exists (copy .env.example)")
        print("  2. Set ROBINHOOD_USERNAME and ROBINHOOD_PASSWORD")
        print("  3. (Optional) Create config.json (copy config.example.json)")
        sys.exit(1)


if __name__ == "__main__":
    main()
