"""CLI entry point for `python -m trading_bot.dashboard`."""

from __future__ import annotations

import sys
from pathlib import Path

from rich.console import Console

from ..account.account_data import AccountData
from ..auth import AlpacaAuth
from ..config import Config
from ..logger import get_logger
from ..logging.query_helper import TradeQueryHelper
from .dashboard import main as run_dashboard

logger = get_logger(__name__)


def main() -> int:
    """Authenticate, initialise services, and launch the dashboard loop."""
    console = Console()

    try:
        config = Config.from_env_and_json()

        auth = AlpacaAuth(config=config)
        logger.info("Authenticating with Alpaca")
        auth.login()
        logger.info("Alpaca authentication successful")

        account_data = AccountData(auth=auth)
        trade_helper = TradeQueryHelper(log_dir=Path("logs"))

        run_dashboard(
            account_data=account_data,
            trade_helper=trade_helper,
            auth=auth,  # Pass auth for re-authentication on session expiry
            console=console,
        )

        return 0

    except KeyboardInterrupt:
        logger.info("dashboard.interrupted", extra={"event": "dashboard.interrupted"})
        console.print("\n[yellow]Dashboard interrupted by user[/yellow]")
        return 130

    except Exception as exc:  # pragma: no cover - runtime errors handled gracefully
        logger.error(
            "dashboard.error",
            extra={
                "event": "dashboard.error",
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            },
            exc_info=True,
        )
        console.print(f"\n[red]Dashboard failed: {exc}[/red]")
        return 1


if __name__ == "__main__":
    sys.exit(main())
