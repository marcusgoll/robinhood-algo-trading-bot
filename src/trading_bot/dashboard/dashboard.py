"""Dashboard orchestration loop built on DashboardDataProvider."""

from __future__ import annotations

import logging
import queue
import threading
import time
import uuid
from typing import Any

from rich.console import Console
from rich.live import Live

from ..account.account_data import AccountData
from ..logger import log_dashboard_event
from ..logging.query_helper import TradeQueryHelper
from .data_provider import DashboardDataProvider
from .display_renderer import DisplayRenderer
from .export_generator import ExportGenerator
from .metrics_calculator import MetricsCalculator
from .models import DashboardSnapshot, DashboardTargets

logger = logging.getLogger(__name__)

REFRESH_INTERVAL_SECONDS = 5.0


class _CommandReader:
    """Background thread that reads newline-terminated commands from stdin."""

    def __init__(self) -> None:
        self._queue: queue.Queue[str] = queue.Queue()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def poll(self) -> str | None:
        """Return the next command if available (uppercase, stripped)."""
        try:
            return self._queue.get_nowait()
        except queue.Empty:
            return None

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                raw = input()
            except EOFError:
                break
            except KeyboardInterrupt:
                # Bubble quit request to main loop.
                self._queue.put("Q")
                break

            if raw is None:
                continue

            command = raw.strip()
            if command:
                self._queue.put(command.upper())


def run_dashboard_loop(
    data_provider: DashboardDataProvider,
    renderer: DisplayRenderer,
    exporter: ExportGenerator,
    *,
    refresh_interval: float = REFRESH_INTERVAL_SECONDS,
    targets: DashboardTargets | None = None,
    auth: Any = None,  # RobinhoodAuth instance for re-authentication
    console: Console | None = None,
) -> None:
    """Run live dashboard with simple command controls."""

    # Generate unique session ID for correlating events
    session_id = str(uuid.uuid4())

    active_console = console or Console()
    active_console.print("[bold green]Trading dashboard started[/bold green]")
    active_console.print(
        "[dim]"
        "Controls: type R/E/H/Q then press Enter • "
        "Refreshed automatically every 5s[/dim]\n"
    )

    log_dashboard_event("dashboard.launched", session_id=session_id)

    should_quit = False
    force_refresh = True  # Trigger immediate first refresh
    last_refresh = 0.0
    snapshot: DashboardSnapshot | None = None

    command_reader = _CommandReader()
    command_reader.start()

    def refresh(manual: bool) -> None:
        nonlocal snapshot, last_refresh, force_refresh
        try:
            new_snapshot = data_provider.get_snapshot(targets)
            layout = renderer.render_full_dashboard(new_snapshot)
            live.update(layout)

            snapshot = new_snapshot
            last_refresh = time.monotonic()
            force_refresh = False

            log_dashboard_event(
                "dashboard.refreshed",
                session_id=session_id,
                manual=manual,
                data_age_seconds=round(snapshot.data_age_seconds, 2),
                is_data_stale=snapshot.is_data_stale,
                warnings=len(snapshot.warnings),
            )
        except Exception as exc:  # pragma: no cover - runtime resilience
            # Check if this is a session expiry error
            error_msg = str(exc).lower()
            if "can only be called when logged in" in error_msg and auth is not None:
                logger.warning("Session expired, attempting re-authentication...")
                active_console.print("[yellow]Session expired - re-authenticating...[/yellow]")
                try:
                    # Logout first to clear stale pickle cache, then login fresh
                    auth.logout()
                    auth.login()
                    logger.info("Re-authentication successful, retrying refresh")
                    active_console.print("[green]Re-authentication successful[/green]")
                    # Retry the refresh after re-authentication
                    new_snapshot = data_provider.get_snapshot(targets)
                    layout = renderer.render_full_dashboard(new_snapshot)
                    live.update(layout)
                    snapshot = new_snapshot
                    last_refresh = time.monotonic()
                    force_refresh = False
                    log_dashboard_event("dashboard.reauth_success", session_id=session_id)
                except Exception as reauth_exc:
                    logger.error("Re-authentication failed: %s", reauth_exc, exc_info=True)
                    active_console.print(f"[red]Re-authentication failed: {reauth_exc}[/red]")
                    log_dashboard_event("dashboard.reauth_failed", session_id=session_id, error=str(reauth_exc))
            else:
                logger.error("Dashboard refresh failed: %s", exc, exc_info=True)
                active_console.print(f"[red]Error refreshing dashboard: {exc}[/red]")

    def export_snapshot() -> None:
        if snapshot is None:
            active_console.print("[yellow]Cannot export yet — no data loaded[/yellow]")
            return

        try:
            json_path, md_path = exporter.generate_exports(snapshot)
            active_console.print(
                "[green]Exported dashboard summary[/green]\n"
                f"  JSON: {json_path}\n"
                f"  Markdown: {md_path}\n"
            )
            log_dashboard_event(
                "dashboard.exported",
                session_id=session_id,
                json_path=str(json_path),
                markdown_path=str(md_path),
            )
        except Exception as exc:  # pragma: no cover - runtime resilience
            logger.error("Dashboard export failed: %s", exc, exc_info=True)
            active_console.print(f"[red]Export failed: {exc}[/red]")

    def show_help() -> None:
        active_console.print(
            "\n[bold cyan]Dashboard Controls[/bold cyan]\n"
            "  R — Manual refresh (bypass timer)\n"
            "  E — Export JSON + Markdown summary to logs/\n"
            "  Q — Quit dashboard\n"
            "  H — Show this help\n"
        )

    try:
        with Live(console=active_console, refresh_per_second=4) as live:
            while not should_quit:
                # Handle queued commands
                command = command_reader.poll()
                if command:
                    char = command[0]
                    if char == "Q":
                        should_quit = True
                        active_console.print("[yellow]Quit requested (Q)[/yellow]")
                    elif char == "R":
                        force_refresh = True
                        active_console.print("[cyan]Manual refresh queued (R)[/cyan]")
                    elif char == "E":
                        export_snapshot()
                    elif char == "H":
                        show_help()

                now = time.monotonic()
                if force_refresh or (now - last_refresh) >= refresh_interval:
                    refresh(manual=force_refresh)

                time.sleep(0.1)

    except KeyboardInterrupt:
        active_console.print("\n[yellow]Dashboard interrupted (Ctrl+C)[/yellow]")
        log_dashboard_event("dashboard.interrupted", session_id=session_id)
    finally:
        command_reader.stop()
        active_console.print("[bold green]Dashboard stopped[/bold green]")
        log_dashboard_event("dashboard.exited", session_id=session_id)


def main(
    account_data: AccountData,
    trade_helper: TradeQueryHelper,
    *,
    auth: Any = None,  # RobinhoodAuth instance for re-authentication
    console: Console | None = None,
) -> None:
    """Entry point invoked from __main__ after authentication."""

    provider = DashboardDataProvider(
        account_data=account_data,
        trade_helper=trade_helper,
        metrics_calculator=MetricsCalculator(),
    )

    targets = provider.load_targets()
    if targets:
        logger.info("Dashboard targets loaded")

    renderer = DisplayRenderer()
    exporter = ExportGenerator()

    run_dashboard_loop(
        data_provider=provider,
        renderer=renderer,
        exporter=exporter,
        targets=targets,
        auth=auth,  # Pass auth for session expiry handling
        console=console,
    )
