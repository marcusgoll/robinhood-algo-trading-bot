"""
Rich-based rendering for the CLI dashboard.

Formats dashboard data into panels, tables, and layout structures with
color-coded metrics, target comparisons, and warnings. Designed to consume
the shared `DashboardSnapshot` payload produced by DashboardDataProvider
so the UI layer stays thin and reusable.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from decimal import Decimal

from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .models import (
    AccountStatus,
    DashboardSnapshot,
    DashboardTargets,
    PerformanceMetrics,
    PositionDisplay,
)


class DisplayRenderer:
    """Renders dashboard components using the rich library."""

    # ------------------------------------------------------------------ #
    # Public rendering API
    # ------------------------------------------------------------------ #
    def render_full_dashboard(self, snapshot: DashboardSnapshot) -> Layout:
        """
        Render the complete dashboard layout for a snapshot of data.

        Args:
            snapshot: DashboardSnapshot from DashboardDataProvider.

        Returns:
            Rich Layout object ready for Live.update().
        """
        layout = Layout()

        header = self._render_header(snapshot)
        warnings_panel = self._render_warnings(snapshot.warnings)
        account_panel = self.render_account_status(snapshot.account_status, snapshot)
        positions_table = self.render_positions_table(snapshot.positions)
        metrics_panel = self.render_performance_metrics(
            snapshot.performance_metrics, snapshot.targets
        )

        # Layout structure: header [+ warnings], then body split into account + main column.
        if warnings_panel is not None:
            layout.split_column(
                Layout(header, size=3, name="header"),
                Layout(warnings_panel, size=3, name="warnings"),
                Layout(name="body"),
            )
        else:
            layout.split_column(
                Layout(header, size=3, name="header"),
                Layout(name="body"),
            )

        layout["body"].split_row(
            Layout(account_panel, size=38, name="account"),
            Layout(name="main"),
        )

        layout["main"].split_column(
            Layout(positions_table, ratio=2, name="positions"),
            Layout(metrics_panel, ratio=1, name="metrics"),
        )

        return layout

    def render_account_status(
        self,
        account: AccountStatus,
        snapshot: DashboardSnapshot,
    ) -> Panel:
        """
        Render account status panel with market and staleness indicators.

        Args:
            account: AccountStatus dataclass.
            snapshot: DashboardSnapshot for context (market status, staleness).
        """
        market_color = "green" if snapshot.market_status == "OPEN" else "yellow"
        data_age = int(snapshot.data_age_seconds)

        content = Text()
        content.append(f"Account Balance: ${self._format_currency(account.account_balance)}\n")
        content.append(f"Cash Balance:    ${self._format_currency(account.cash_balance)}\n")
        content.append(f"Buying Power:    ${self._format_currency(account.buying_power)}\n")
        content.append(f"Day Trades:      {account.day_trade_count}\n")
        content.append(
            f"Last Updated:    {self._format_datetime(account.last_updated)} "
            f"(age {data_age}s)\n"
        )
        content.append(f"Market Status:   ", style="bold")
        content.append(f"{snapshot.market_status}\n", style=market_color + " bold")

        if snapshot.is_data_stale:
            content.append(
                f"\n⚠️  Data may be stale (>{self._format_seconds(snapshot.data_age_seconds)})",
                style="yellow",
            )

        return Panel(
            content,
            title="Account Status",
            border_style="blue",
        )

    def render_positions_table(self, positions: Iterable[PositionDisplay]) -> Table:
        """Render positions table with P&L color coding."""
        table = Table(title="Open Positions", show_header=True, header_style="bold cyan")
        table.add_column("Symbol", style="white", no_wrap=True)
        table.add_column("Qty", justify="right")
        table.add_column("Entry", justify="right")
        table.add_column("Current", justify="right")
        table.add_column("Unrealized P&L", justify="right")
        table.add_column("P&L %", justify="right")
        table.add_column("Updated", justify="right")

        positions_list = list(positions)

        if not positions_list:
            table.add_row(
                "[dim]No open positions[/dim]",
                "-",
                "-",
                "-",
                "-",
                "-",
                "-",
            )
            return table

        for pos in positions_list:
            pl_color = self._get_pl_color(pos.unrealized_pl)
            pl_pct_color = self._get_pl_color(pos.unrealized_pl_pct)

            table.add_row(
                pos.symbol,
                str(pos.quantity),
                f"${self._format_currency(pos.entry_price)}",
                f"${self._format_currency(pos.current_price)}",
                f"[{pl_color}]${self._format_currency(pos.unrealized_pl)}[/{pl_color}]",
                f"[{pl_pct_color}]{self._format_percentage(pos.unrealized_pl_pct)}[/{pl_pct_color}]",
                self._format_time_short(pos.last_updated),
            )

        return table

    def render_performance_metrics(
        self,
        metrics: PerformanceMetrics,
        targets: DashboardTargets | None,
    ) -> Panel:
        """Render performance metrics panel with target comparisons."""
        content = Text()

        # Win rate
        content.append(self._metric_with_target(
            label="Win Rate",
            actual=f"{metrics.win_rate:.2f}%",
            meets=self._meets_target(metrics.win_rate, targets.win_rate_target) if targets else None,
            target=f"{targets.win_rate_target:.2f}%" if targets else None,
        ))

        # Avg Risk/Reward
        avg_rr_target = targets.avg_risk_reward_target if targets else None
        content.append(self._metric_with_target(
            label="Avg Risk/Reward",
            actual=f"{metrics.avg_risk_reward:.2f}",
            meets=self._meets_target(metrics.avg_risk_reward, avg_rr_target) if avg_rr_target is not None else None,
            target=f"{avg_rr_target:.2f}" if avg_rr_target is not None else None,
        ))

        # Total P&L
        total_pl_color = self._get_pl_color(metrics.total_pl)
        total_pl_text = f"${self._format_currency(metrics.total_pl)}"
        meets_total = None
        target_total = None
        if targets:
            meets_total = metrics.total_pl >= targets.daily_pl_target
            target_total = f"${self._format_currency(targets.daily_pl_target)}"
        content.append(
            self._metric_with_target(
                label="Total P&L",
                actual=total_pl_text,
                actual_style=total_pl_color,
                meets=meets_total,
                target=target_total,
            )
        )

        # Realized / Unrealized breakdown
        content.append("  • Realized: ")
        content.append(f"${self._format_currency(metrics.total_realized_pl)}",
                      style=self._get_pl_color(metrics.total_realized_pl))
        content.append("\n")

        content.append("  • Unrealized: ")
        content.append(f"${self._format_currency(metrics.total_unrealized_pl)}",
                      style=self._get_pl_color(metrics.total_unrealized_pl))
        content.append("\n")

        # Max drawdown
        drawdown_color = self._get_pl_color(metrics.max_drawdown)
        drawdown_text = f"${self._format_currency(metrics.max_drawdown)}"
        meets_drawdown = None
        target_drawdown = None
        if targets:
            meets_drawdown = metrics.max_drawdown >= targets.max_drawdown_target
            target_drawdown = f"${self._format_currency(targets.max_drawdown_target)}"
        content.append(
            self._metric_with_target(
                label="Max Drawdown",
                actual=drawdown_text,
                actual_style=drawdown_color,
                meets=meets_drawdown,
                target=target_drawdown,
            )
        )

        # Streak / Trades / Sessions
        streak_color = self._streak_color(metrics.streak_type)
        content.append("Current Streak: ")
        content.append(f"{metrics.current_streak} {metrics.streak_type}", style=streak_color)
        content.append("\n")

        trades_meets = None
        trades_target = None
        if targets:
            trades_meets = metrics.trades_today >= targets.trades_per_day_target
            trades_target = str(targets.trades_per_day_target)
        content.append(
            self._metric_with_target(
                label="Trades Today",
                actual=str(metrics.trades_today),
                meets=trades_meets,
                target=trades_target,
            )
        )

        content.append(f"Session Count: {metrics.session_count}")

        return Panel(content, title="Performance Metrics", border_style="magenta")

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _render_header(self, snapshot: DashboardSnapshot) -> Panel:
        """Render dashboard header banner."""
        timestamp = self._format_datetime(snapshot.generated_at)
        header_text = Text.assemble(
            ("Trading Dashboard", "bold white"),
            ("  •  ", "dim"),
            (timestamp, "white"),
            ("  •  ", "dim"),
            (f"Market {snapshot.market_status}", "green bold" if snapshot.market_status == "OPEN" else "yellow bold"),
        )

        return Panel(
            header_text,
            style="bold white on blue",
        )

    def _render_warnings(self, warnings: list[str]) -> Panel | None:
        """Render warnings panel if any warnings exist."""
        if not warnings:
            return None

        content = Text()
        for warning in warnings:
            content.append(f"• {warning}\n", style="yellow")

        return Panel(
            content,
            title="Warnings",
            border_style="yellow",
        )

    def _metric_with_target(
        self,
        *,
        label: str,
        actual: str,
        actual_style: str | None = None,
        meets: bool | None,
        target: str | None,
    ) -> Text:
        """Format metric line with optional target comparison."""
        line = Text()
        line.append(f"{label}: ")
        line.append(actual, style=actual_style)

        if target is not None and meets is not None:
            indicator = "✓" if meets else "✗"
            indicator_color = "green" if meets else "red"
            line.append(" ")
            line.append(indicator, style=indicator_color)
            line.append(f" (target: {target})")

        line.append("\n")
        return line

    @staticmethod
    def _get_pl_color(value: Decimal | float) -> str:
        """Determine color for P&L values."""
        numeric_value = float(value)
        if numeric_value > 0:
            return "green"
        if numeric_value < 0:
            return "red"
        return "yellow"

    @staticmethod
    def _streak_color(streak_type: str) -> str:
        """Color used for streak indicator."""
        if streak_type == "WIN":
            return "green"
        if streak_type == "LOSS":
            return "red"
        return "yellow"

    @staticmethod
    def _format_currency(value: Decimal) -> str:
        """Format Decimal as currency with thousands separator."""
        return f"{value:,.2f}"

    @staticmethod
    def _format_percentage(value: Decimal | float) -> str:
        """Format numeric value as percentage string."""
        return f"{float(value):.2f}%"

    @staticmethod
    def _format_datetime(dt: datetime) -> str:
        """Format datetime for human-readable display."""
        return dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _format_time_short(dt: datetime) -> str:
        """Compact time formatter for table cells."""
        return dt.astimezone().strftime("%H:%M:%S")

    @staticmethod
    def _format_seconds(seconds: float) -> str:
        """Human-friendly seconds formatter (e.g., 75s, 2m5s)."""
        total = int(seconds)
        minutes, secs = divmod(total, 60)
        if minutes == 0:
            return f"{secs}s"
        return f"{minutes}m{secs:02d}s"

    @staticmethod
    def _meets_target(actual: float, target: float | None) -> bool | None:
        """Return True/False if target provided, else None."""
        if target is None:
            return None
        return actual >= target
