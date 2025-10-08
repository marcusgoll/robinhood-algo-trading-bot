"""
Simple test script to verify configuration loading.

Usage:
    python test_config.py
"""

from src.trading_bot.config import Config


def main() -> None:
    """Test configuration loading from .env and config.json."""
    print("=" * 60)
    print("Testing Configuration Loading")
    print("=" * 60)
    print()

    try:
        # Load configuration
        print("Loading configuration...")
        config = Config.from_env_and_json()

        print("✅ Configuration loaded successfully!")
        print()

        # Validate configuration
        print("Validating configuration...")
        config.validate()
        print("✅ Configuration is valid!")
        print()

        # Display configuration (hide sensitive data)
        print("-" * 60)
        print("Configuration Summary")
        print("-" * 60)
        print()

        print("Credentials:")
        print(f"  Username: {config.robinhood_username[:3]}***")
        print(f"  Password: {'*' * 8}")
        print(f"  MFA Secret: {'SET' if config.robinhood_mfa_secret else 'NOT SET'}")
        print(f"  Device Token: {'SET' if config.robinhood_device_token else 'NOT SET'}")
        print()

        print("Trading Mode:")
        print(f"  Paper Trading: {config.paper_trading}")
        print()

        print("Trading Hours:")
        print(f"  Start: {config.trading_start_time} {config.trading_timezone}")
        print(f"  End: {config.trading_end_time} {config.trading_timezone}")
        print()

        print("Risk Management:")
        print(f"  Max Position %: {config.max_position_pct}%")
        print(f"  Max Daily Loss %: {config.max_daily_loss_pct}%")
        print(f"  Max Consecutive Losses: {config.max_consecutive_losses}")
        print(f"  Position Size (shares): {config.position_size_shares}")
        print(f"  Stop Loss %: {config.stop_loss_pct}%")
        print(f"  Risk:Reward Ratio: 1:{config.risk_reward_ratio}")
        print()

        print("Phase Progression:")
        print(f"  Current Phase: {config.current_phase}")
        print(f"  Max Trades/Day: {config.max_trades_per_day}")
        print()

        print("Paths:")
        print(f"  Data: {config.data_dir}")
        print(f"  Logs: {config.logs_dir}")
        print(f"  Backtests: {config.backtest_dir}")
        print(f"  Config File: {config.config_file}")
        print()

        # Ensure directories
        config.ensure_directories()
        print("✅ Directories created/verified")
        print()

        print("=" * 60)
        print("Configuration Test: PASSED ✅")
        print("=" * 60)

    except ValueError as e:
        print(f"❌ Configuration Error: {e}")
        print()
        print("Make sure you have:")
        print("  1. Created .env file from .env.example")
        print("  2. Set ROBINHOOD_USERNAME and ROBINHOOD_PASSWORD in .env")
        print("  3. (Optional) Created config.json from config.example.json")
        return

    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        return


if __name__ == "__main__":
    main()
