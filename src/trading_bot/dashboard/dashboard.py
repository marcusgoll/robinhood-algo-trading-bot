"""
Dashboard Orchestration Module

Coordinates dashboard state aggregation, configuration loading, and polling loop
with keyboard controls.

Constitution v1.0.0:
- §Error_Handling: Graceful degradation when targets missing or API fails
- §Data_Integrity: Proper type handling and UTC timestamps
- §Audit_Everything: Log all errors and state changes

Feature: status-dashboard
Tasks: T021-T023 - Dashboard orchestration with polling loop
"""

import logging
import time
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Literal

import yaml
from pynput import keyboard
from rich.console import Console
from rich.live import Live

from ..account.account_data import AccountData
from ..logging.query_helper import TradeQueryHelper
from ..utils.time_utils import is_market_open
from .display_renderer import DisplayRenderer
from .metrics_calculator import MetricsCalculator
from .models import (
    AccountStatus,
    DashboardState,
    DashboardTargets,
    PositionDisplay,
)

logger = logging.getLogger(__name__)


def load_targets(config_path: Path = Path("config/dashboard-targets.yaml")) -> DashboardTargets | None:
    """
    Load dashboard performance targets from YAML configuration.

    Reads and validates target configuration file with graceful degradation.
    Dashboard operates without targets if file missing or invalid.

    Args:
        config_path: Path to YAML config file with performance targets
            (default: config/dashboard-targets.yaml)

    Returns:
        DashboardTargets object if config valid, None otherwise.
        Returns None on any error (missing file, invalid YAML, missing fields).

    Examples:
        >>> targets = load_targets(Path("config/dashboard-targets.yaml"))
        >>> if targets:
        ...     print(f"Win rate target: {targets.win_rate_target}%")

    Configuration Format:
        ```yaml
        win_rate_target: 60.0          # Win rate percentage (e.g., 60.0 = 60%)
        daily_pl_target: 200.00        # Daily profit/loss target in dollars
        trades_per_day_target: 5       # Minimum trades per day
        max_drawdown_target: -100.00   # Maximum allowed drawdown (negative)
        avg_risk_reward_target: 2.0    # Average risk-reward ratio (e.g., 2.0 = 2:1)
        ```

    Error Handling:
        - Missing file: Logs warning once, returns None
        - Invalid YAML: Logs warning once, returns None
        - Missing required fields: Logs warning once, returns None
        - All errors result in graceful degradation (dashboard works without targets)

    Task: T021 [status-dashboard]
    Constitution: §Error_Handling (graceful degradation)
    """
    try:
        # Check if config file exists
        if not config_path.exists():
            logger.warning(
                f"Dashboard targets config not found: {config_path}. "
                "Dashboard will operate without target comparisons."
            )
            return None

        # Read and parse YAML
        with open(config_path, encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # Validate required fields
        required_fields = [
            'win_rate_target',
            'daily_pl_target',
            'trades_per_day_target',
            'max_drawdown_target',
            'avg_risk_reward_target'
        ]

        for field in required_fields:
            if field not in config:
                logger.warning(
                    f"Dashboard targets config missing required field '{field}'. "
                    "Dashboard will operate without target comparisons."
                )
                return None

        # Convert numeric values to appropriate types
        return DashboardTargets(
            win_rate_target=float(config['win_rate_target']),
            daily_pl_target=Decimal(str(config['daily_pl_target'])),
            trades_per_day_target=int(config['trades_per_day_target']),
            max_drawdown_target=Decimal(str(config['max_drawdown_target'])),
            avg_risk_reward_target=float(config['avg_risk_reward_target'])
        )

    except (yaml.YAMLError, ValueError, TypeError) as e:
        logger.warning(
            f"Failed to load dashboard targets config: {e}. "
            "Dashboard will operate without target comparisons."
        )
        return None


def fetch_dashboard_state(
    account_data: AccountData,
    trade_helper: TradeQueryHelper,
    targets: DashboardTargets | None
) -> DashboardState:
    """
    Aggregate complete dashboard state from account data and trade logs.

    Fetches account balances, positions, and today's trades to build complete
    dashboard state with performance metrics and market status.

    Args:
        account_data: AccountData service for fetching account information
        trade_helper: TradeQueryHelper for querying trade logs
        targets: Optional performance targets for comparison (can be None)

    Returns:
        DashboardState with all components populated (account, positions, metrics)

    Error Handling:
        - API failures: Logged and propagated (caller handles retry)
        - Empty positions: Returns empty list (not an error)
        - No trades today: Returns metrics with zero values

    Examples:
        >>> from trading_bot.account.account_data import AccountData
        >>> from trading_bot.logging.query_helper import TradeQueryHelper
        >>> account_data = AccountData(auth)
        >>> trade_helper = TradeQueryHelper(log_dir=Path("logs"))
        >>> targets = load_targets()
        >>> state = fetch_dashboard_state(account_data, trade_helper, targets)
        >>> print(f"Buying power: ${state.account_status.buying_power}")

    Task: T022 [status-dashboard]
    Constitution: §Data_Integrity (proper type conversions, UTC timestamps)
    """
    # Fetch account information
    account_balance_obj = account_data.get_account_balance()
    buying_power = Decimal(str(account_data.get_buying_power()))
    day_trade_count = account_data.get_day_trade_count()

    # Build AccountStatus
    account_status = AccountStatus(
        buying_power=buying_power,
        account_balance=account_balance_obj.equity,
        cash_balance=account_balance_obj.cash,
        day_trade_count=day_trade_count,
        last_updated=datetime.now(UTC)
    )

    # Fetch and convert positions
    positions = account_data.get_positions()
    position_displays: list[PositionDisplay] = []

    for pos in positions:
        position_display = PositionDisplay(
            symbol=pos.symbol,
            quantity=pos.quantity,
            entry_price=pos.average_buy_price,
            current_price=pos.current_price,
            unrealized_pl=pos.profit_loss,
            unrealized_pl_pct=pos.profit_loss_pct
        )
        position_displays.append(position_display)

    # Query today's trades
    today_str = datetime.now(UTC).strftime("%Y-%m-%d")
    trades_today = trade_helper.query_by_date_range(today_str, today_str)

    # Calculate performance metrics
    performance_metrics = MetricsCalculator.aggregate_metrics(
        trades=trades_today,
        positions=positions,
        session_count=0  # TODO: Track session count in future enhancement
    )

    # Determine market status
    market_open = is_market_open()
    market_status: Literal["OPEN", "CLOSED"] = "OPEN" if market_open else "CLOSED"

    # Build complete dashboard state
    return DashboardState(
        account_status=account_status,
        positions=position_displays,
        performance_metrics=performance_metrics,
        market_status=market_status,
        timestamp=datetime.now(UTC),
        targets=targets
    )


def run_dashboard_loop(
    account_data: AccountData,
    trade_helper: TradeQueryHelper,
    targets: DashboardTargets | None
) -> None:
    """
    Run interactive dashboard with 5-second polling and keyboard controls.

    Creates a live-updating terminal dashboard with automatic refresh every 5 seconds
    and keyboard controls for manual actions. Uses rich.live.Live for flicker-free
    updates and pynput for non-blocking keyboard input.

    Args:
        account_data: AccountData service for fetching account information
        trade_helper: TradeQueryHelper for querying trade logs
        targets: Optional performance targets for comparison (can be None)

    Keyboard Controls:
        R: Manual refresh (bypass 5s timer)
        E: Export daily summary (TODO: Implement in future)
        Q: Quit dashboard gracefully
        H: Show help overlay (TODO: Implement in future)

    Error Handling:
        - API errors: Logged, dashboard continues with stale data
        - Keyboard interrupt (Ctrl+C): Caught and exits gracefully
        - Display errors: Logged, retry on next refresh

    Examples:
        >>> from trading_bot.account.account_data import AccountData
        >>> from trading_bot.logging.query_helper import TradeQueryHelper
        >>> account_data = AccountData(auth)
        >>> trade_helper = TradeQueryHelper()
        >>> targets = load_targets()
        >>> run_dashboard_loop(account_data, trade_helper, targets)
        # Dashboard runs until Q pressed or Ctrl+C

    Architecture:
        - Uses rich.live.Live for flicker-free terminal updates
        - 5-second polling loop with sleep intervals
        - Non-blocking keyboard input via pynput
        - Graceful shutdown on keyboard interrupt

    Task: T023 [status-dashboard]
    Constitution: §Error_Handling (graceful degradation on API errors)
    """
    console = Console()
    renderer = DisplayRenderer()

    # State for keyboard controls
    should_quit = False
    force_refresh = False

    def on_press(key):
        """Handle keyboard input (non-blocking)."""
        nonlocal should_quit, force_refresh

        try:
            # Check for character keys
            if hasattr(key, 'char') and key.char:
                key_char = key.char.upper()

                if key_char == 'Q':
                    should_quit = True
                    logger.info("Dashboard quit requested (Q pressed)")
                elif key_char == 'R':
                    force_refresh = True
                    logger.info("Manual refresh requested (R pressed)")
                elif key_char == 'E':
                    console.print("[yellow]Export feature not yet implemented[/yellow]")
                    logger.info("Export requested (E pressed) - not yet implemented")
                elif key_char == 'H':
                    console.print(
                        "\n[bold cyan]Dashboard Keyboard Controls:[/bold cyan]\n"
                        "  R - Manual refresh (bypass 5s timer)\n"
                        "  E - Export daily summary (not yet implemented)\n"
                        "  Q - Quit dashboard\n"
                        "  H - Show this help\n"
                    )
                    logger.info("Help displayed (H pressed)")
        except AttributeError:
            pass  # Ignore special keys

    # Start keyboard listener in background thread
    listener = keyboard.Listener(on_press=on_press)
    listener.start()

    console.print("[bold green]Dashboard started[/bold green]")
    console.print("[dim]Press H for help, Q to quit[/dim]\n")

    try:
        with Live(console=console, refresh_per_second=1) as live:
            last_refresh_time = 0.0

            while not should_quit:
                current_time = time.time()

                # Refresh if 5 seconds elapsed or manual refresh requested
                if force_refresh or (current_time - last_refresh_time >= 5.0):
                    try:
                        # Show refreshing indicator
                        if force_refresh:
                            console.print("[cyan]Refreshing (manual)...[/cyan]")

                        # Fetch dashboard state
                        state = fetch_dashboard_state(account_data, trade_helper, targets)

                        # Render full dashboard
                        layout = renderer.render_full_dashboard(state)
                        live.update(layout)

                        # Update refresh time
                        last_refresh_time = current_time
                        force_refresh = False

                        logger.debug("Dashboard refreshed successfully")

                    except Exception as e:
                        logger.error(f"Dashboard refresh failed: {e}", exc_info=True)
                        console.print(f"[red]Error refreshing dashboard: {e}[/red]")
                        # Continue loop - dashboard will retry on next interval

                # Sleep briefly to avoid busy-waiting
                time.sleep(0.1)

    except KeyboardInterrupt:
        console.print("\n[yellow]Dashboard interrupted (Ctrl+C)[/yellow]")
        logger.info("Dashboard interrupted by user (Ctrl+C)")
    finally:
        # Clean up keyboard listener
        listener.stop()
        console.print("[bold green]Dashboard stopped[/bold green]")
        logger.info("Dashboard stopped")
