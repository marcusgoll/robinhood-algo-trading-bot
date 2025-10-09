"""
Example: Running the Trading Dashboard

Demonstrates how to initialize and run the interactive dashboard with
account data, trade logging, and optional performance targets.

Usage:
    python -m examples.run_dashboard

Requirements:
    - Valid Robinhood authentication (login required)
    - Trade logs in logs/ directory
    - Optional: config/dashboard-targets.yaml for target comparisons
"""

from pathlib import Path

from trading_bot.auth.robinhood_auth import RobinhoodAuth
from trading_bot.account.account_data import AccountData
from trading_bot.logging.query_helper import TradeQueryHelper
from trading_bot.dashboard import load_targets, run_dashboard_loop
from trading_bot.logger import setup_logging


def main():
    """Run the interactive dashboard."""
    # Setup logging
    setup_logging()

    # Initialize authentication
    print("Authenticating with Robinhood...")
    auth = RobinhoodAuth()
    if not auth.login():
        print("Authentication failed. Exiting.")
        return

    print("Authentication successful!\n")

    # Initialize services
    account_data = AccountData(auth)
    trade_helper = TradeQueryHelper(log_dir=Path("logs"))

    # Load performance targets (optional)
    targets = load_targets(Path("config/dashboard-targets.yaml"))

    if targets:
        print(f"Loaded performance targets:")
        print(f"  - Win Rate Target: {targets.win_rate_target}%")
        print(f"  - Daily P&L Target: ${targets.daily_pl_target}")
        print(f"  - Trades Per Day Target: {targets.trades_per_day_target}")
        print(f"  - Avg Risk/Reward Target: {targets.avg_risk_reward_target}\n")
    else:
        print("No performance targets loaded (dashboard will run without targets)\n")

    # Run dashboard loop
    print("Starting dashboard...")
    print("Keyboard controls:")
    print("  R - Manual refresh")
    print("  E - Export daily summary (not yet implemented)")
    print("  Q - Quit dashboard")
    print("  H - Show help\n")

    run_dashboard_loop(account_data, trade_helper, targets)


if __name__ == "__main__":
    main()
