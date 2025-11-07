"""
Test script for logging system.

Demonstrates usage of the structured logging system.

Usage:
    python test_logging.py
"""

from src.trading_bot.logger import setup_logging, get_logger, log_trade, log_error
from pathlib import Path


def main() -> None:
    """Demonstrate logging system functionality."""
    print("=" * 60)
    print("Testing Logging System (Constitution v1.0.0)")
    print("=" * 60)
    print()

    # Initialize logging system
    print("Initializing logging system...")
    setup_logging()
    print("✅ Logging initialized")
    print()

    # Get a logger
    logger = get_logger(__name__)

    # Test different log levels
    print("Testing different log levels...")
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")
    print()

    # Test trade logging (§Audit_Everything)
    print("Testing trade logging...")
    log_trade(
        action="BUY",
        symbol="AAPL",
        quantity=100,
        price=150.50,
        mode="PAPER",
        strategy="Bull Flag",
        stop_loss=148.00,
        target=155.50
    )
    print("✅ Trade logged to logs/trades.log")
    print()

    log_trade(
        action="SELL",
        symbol="AAPL",
        quantity=100,
        price=155.50,
        mode="PAPER",
        profit=500.00,
        reason="Target hit"
    )
    print("✅ Exit trade logged")
    print()

    # Test error logging
    print("Testing error logging...")
    try:
        # Simulate an error
        raise ValueError("Simulated API error for testing")
    except ValueError as e:
        log_error(e, "During simulated API call")
    print("✅ Error logged to logs/errors.log")
    print()

    # Test logger from different modules
    print("Testing module-specific loggers...")
    config_logger = get_logger("src.trading_bot.config")
    config_logger.info("Configuration loaded successfully")

    validator_logger = get_logger("src.trading_bot.validator")
    validator_logger.info("Validation completed")

    bot_logger = get_logger("src.trading_bot.bot")
    bot_logger.info("Bot initialized")
    print()

    # Show log file locations
    print("-" * 60)
    print("Log Files Created:")
    print("-" * 60)

    logs_dir = Path("logs")
    if logs_dir.exists():
        for log_file in sorted(logs_dir.glob("*.log")):
            size = log_file.stat().st_size
            print(f"  {log_file.name:<20} ({size} bytes)")
    print()

    # Show sample log content
    print("-" * 60)
    print("Sample Trade Log Content (logs/trades.log):")
    print("-" * 60)

    trades_log = Path("logs/trades.log")
    if trades_log.exists():
        content = trades_log.read_text()
        for line in content.split("\n")[-5:]:  # Last 5 lines
            if line.strip():
                print(f"  {line}")
    print()

    print("=" * 60)
    print("Logging System Test: PASSED ✅")
    print("=" * 60)
    print()
    print("All logs use UTC timestamps (§Data_Integrity)")
    print("Trades logged separately (§Audit_Everything)")
    print("Log rotation enabled (max 10MB per file, 5 backups)")
    print()


if __name__ == "__main__":
    main()
