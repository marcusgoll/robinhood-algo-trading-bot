"""
Dashboard Entry Point.

Provides CLI interface for launching the trading bot dashboard.

Usage:
    python -m trading_bot.dashboard

Task: T025 [P] - Dashboard entry point
"""

import sys
from pathlib import Path

from ..account.account_data import AccountData
from ..config import Config
from ..logger import get_logger
from ..logging.query_helper import TradeQueryHelper
from .dashboard import load_targets, run_dashboard_loop

logger = get_logger(__name__)


def main() -> int:
    """
    Main entry point for dashboard.

    Orchestrates:
    1. Initialize AccountData service
    2. Initialize TradeQueryHelper
    3. Load targets (optional)
    4. Log dashboard.launched event
    5. Run dashboard loop
    6. Log dashboard.exited event on quit

    Returns:
        Exit code:
        - 0: Success (clean exit)
        - 1: Configuration error
        - 2: Service initialization failure
        - 130: Interrupted by user (Ctrl+C)
    """
    try:
        # Load configuration
        config = Config.from_env_and_json()

        # Log dashboard launch
        logger.info(
            "dashboard.launched",
            extra={
                "event": "dashboard.launched",
                "config_loaded": True,
            },
        )

        # Initialize AccountData service
        account_data = AccountData(config=config)

        # Initialize TradeQueryHelper
        trade_helper = TradeQueryHelper(log_file=Path("logs/trades-structured.jsonl"))

        # Load targets (optional)
        targets = load_targets()

        # Run dashboard loop
        run_dashboard_loop(
            account_data=account_data, trade_helper=trade_helper, targets=targets
        )

        # Log dashboard exit
        logger.info(
            "dashboard.exited",
            extra={
                "event": "dashboard.exited",
                "exit_reason": "user_quit",
            },
        )

        return 0

    except KeyboardInterrupt:
        logger.info(
            "dashboard.interrupted",
            extra={
                "event": "dashboard.interrupted",
                "exit_reason": "keyboard_interrupt",
            },
        )
        print("\n\n⚠️  Dashboard interrupted by user")
        return 130

    except Exception as e:
        logger.error(
            "dashboard.error",
            extra={
                "event": "dashboard.error",
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
            exc_info=True,
        )
        print(f"\n❌ Dashboard error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
