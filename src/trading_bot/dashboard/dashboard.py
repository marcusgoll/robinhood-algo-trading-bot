"""Dashboard orchestration loop built on DashboardDataProvider."""

from __future__ import annotations

import json
import logging
import queue
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.live import Live

from ..account.account_data import AccountData
from ..logging.query_helper import TradeQueryHelper
from .data_provider import DashboardDataProvider
from .display_renderer import DisplayRenderer
from .export_generator import ExportGenerator
from .metrics_calculator import MetricsCalculator
from .models import DashboardSnapshot, DashboardTargets

logger = logging.getLogger(__name__)

USAGE_LOG_PATH = Path("logs/dashboard-usage.jsonl")
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

    def poll(self) -> Optional[str]:
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


def log_dashboard_event(event: str, **payload: object) -> None:
    """Append structured dashboard events to logs/dashboard-usage.jsonl."""
    try:
        USAGE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "event": event,
            **payload,
        }
        with USAGE_LOG_PATH.open("a", encoding="utf-8") as handle:
            json.dump(entry, handle)
            handle.write("\n")
    except Exception as exc:  # pragma: no cover - logging should not break dashboard
        logger.warning(
            "Failed to write dashboard event %s: %s", event, exc, exc_info=True
        )


def run_dashboard_loop(
    data_provider: DashboardDataProvider,
    renderer: DisplayRenderer,
    exporter: ExportGenerator,
    *,
    refresh_interval: float = REFRESH_INTERVAL_SECONDS,
    targets: DashboardTargets | None = None,
    auth = None,  # RobinhoodAuth instance for re-authentication
    console: Optional[Console] = None,
) -> None:
    """Run live dashboard with simple command controls."""

    console = console or Console()
    console.print("[bold green]Trading dashboard started[/bold green]")
    console.print(
        "[dim]"
        "Controls: type R/E/H/Q then press Enter • "
        "Refreshed automatically every 5s[/dim]\n"
    )

    log_dashboard_event("dashboard.launched")

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
                console.print("[yellow]Session expired - re-authenticating...[/yellow]")
                try:
                    auth.login()
                    logger.info("Re-authentication successful, retrying refresh")
                    console.print("[green]Re-authentication successful[/green]")
                    # Retry the refresh after re-authentication
                    new_snapshot = data_provider.get_snapshot(targets)
                    layout = renderer.render_full_dashboard(new_snapshot)
                    live.update(layout)
                    snapshot = new_snapshot
                    last_refresh = time.monotonic()
                    force_refresh = False
                    log_dashboard_event("dashboard.reauth_success")
                except Exception as reauth_exc:
                    logger.error("Re-authentication failed: %s", reauth_exc, exc_info=True)
                    console.print(f"[red]Re-authentication failed: {reauth_exc}[/red]")
                    log_dashboard_event("dashboard.reauth_failed", error=str(reauth_exc))
            else:
                logger.error("Dashboard refresh failed: %s", exc, exc_info=True)
                console.print(f"[red]Error refreshing dashboard: {exc}[/red]")

    def export_snapshot() -> None:
        if snapshot is None:
            console.print("[yellow]Cannot export yet — no data loaded[/yellow]")
            return

        try:
            json_path, md_path = exporter.generate_exports(snapshot)
            console.print(
                "[green]Exported dashboard summary[/green]\n"
                f"  JSON: {json_path}\n"
                f"  Markdown: {md_path}\n"
            )
            log_dashboard_event(
                "dashboard.exported",
                json_path=str(json_path),
                markdown_path=str(md_path),
            )
        except Exception as exc:  # pragma: no cover - runtime resilience
            logger.error("Dashboard export failed: %s", exc, exc_info=True)
            console.print(f"[red]Export failed: {exc}[/red]")

    def show_help() -> None:
        console.print(
            "\n[bold cyan]Dashboard Controls[/bold cyan]\n"
            "  R — Manual refresh (bypass timer)\n"
            "  E — Export JSON + Markdown summary to logs/\n"
            "  Q — Quit dashboard\n"
            "  H — Show this help\n"
        )

    try:
        with Live(console=console, refresh_per_second=4) as live:
            while not should_quit:
                # Handle queued commands
                command = command_reader.poll()
                if command:
                    char = command[0]
                    if char == "Q":
                        should_quit = True
                        console.print("[yellow]Quit requested (Q)[/yellow]")
                    elif char == "R":
                        force_refresh = True
                        console.print("[cyan]Manual refresh queued (R)[/cyan]")
                    elif char == "E":
                        export_snapshot()
                    elif char == "H":
                        show_help()

                now = time.monotonic()
                if force_refresh or (now - last_refresh) >= refresh_interval:
                    refresh(manual=force_refresh)

                time.sleep(0.1)

    except KeyboardInterrupt:
        console.print("\n[yellow]Dashboard interrupted (Ctrl+C)[/yellow]")
        log_dashboard_event("dashboard.interrupted")
    finally:
        command_reader.stop()
        console.print("[bold green]Dashboard stopped[/bold green]")
        log_dashboard_event("dashboard.exited")


def main(
    account_data: AccountData,
    trade_helper: TradeQueryHelper,
    *,
    auth = None,  # RobinhoodAuth instance for re-authentication
    console: Optional[Console] = None,
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
