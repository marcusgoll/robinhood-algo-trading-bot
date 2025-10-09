"""
Rich-based rendering for CLI dashboard displays.

Provides DisplayRenderer class for formatting dashboard components with
color-coded P&L, target comparisons, and structured layouts.
"""

from datetime import datetime
from decimal import Decimal

from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from trading_bot.dashboard.models import (
    AccountStatus,
    DashboardState,
    DashboardTargets,
    PerformanceMetrics,
    PositionDisplay,
)


class DisplayRenderer:
    """Renders dashboard components using rich library."""

    def render_account_status(
        self, account: AccountStatus, market_status: str
    ) -> Panel:
        """
        Render account status panel with market state.

        Args:
            account: Account snapshot with balances and metadata
            market_status: Current market state ("OPEN" or "CLOSED")

        Returns:
            Panel containing formatted account information
        """
        market_color = "green" if market_status == "OPEN" else "yellow"
        market_text = Text(f"Market: {market_status}", style=market_color)

        content = Text()
        content.append(f"Account Balance: ${self._format_currency(account.account_balance)}\n")
        content.append(f"Cash Balance:    ${self._format_currency(account.cash_balance)}\n")
        content.append(f"Buying Power:    ${self._format_currency(account.buying_power)}\n")
        content.append(f"Day Trades:      {account.day_trade_count}\n")
        content.append(f"Last Updated:    {self._format_datetime(account.last_updated)}\n\n")
        content.append(market_text)

        return Panel(content, title="Account Status", border_style="blue")

    def render_positions_table(self, positions: list[PositionDisplay]) -> Table:
        """
        Render positions table with P&L color coding.

        Args:
            positions: List of position displays with calculated P&L

        Returns:
            Table showing all positions or empty state message
        """
        table = Table(title="Open Positions", show_header=True, header_style="bold cyan")
        table.add_column("Symbol", style="white", no_wrap=True)
        table.add_column("Qty", justify="right")
        table.add_column("Entry", justify="right")
        table.add_column("Current", justify="right")
        table.add_column("Unrealized P&L", justify="right")
        table.add_column("P&L %", justify="right")

        if not positions:
            # Create single-row table with "No open positions" message
            table.add_row(
                "[dim]No open positions[/dim]",
                "-",
                "-",
                "-",
                "-",
                "-",
            )
            return table

        for pos in positions:
            pl_color = self._get_pl_color(pos.unrealized_pl)
            pl_pct_color = self._get_pl_color(pos.unrealized_pl_pct)

            table.add_row(
                pos.symbol,
                str(pos.quantity),
                f"${self._format_currency(pos.entry_price)}",
                f"${self._format_currency(pos.current_price)}",
                f"[{pl_color}]${self._format_currency(pos.unrealized_pl)}[/{pl_color}]",
                f"[{pl_pct_color}]{self._format_percentage(pos.unrealized_pl_pct)}[/{pl_pct_color}]",
            )

        return table

    def render_performance_metrics(
        self, metrics: PerformanceMetrics, targets: DashboardTargets | None
    ) -> Panel:
        """
        Render performance metrics panel with target comparisons.

        Args:
            metrics: Aggregated trading performance data
            targets: Optional performance targets for comparison

        Returns:
            Panel with color-coded metrics and target indicators
        """
        content = Text()

        # Win rate with target comparison
        win_rate_text = f"Win Rate:         {self._format_percentage(metrics.win_rate)}"
        if targets:
            meets_target = metrics.win_rate >= targets.win_rate_target
            indicator = "✓" if meets_target else "✗"
            indicator_color = "green" if meets_target else "red"
            content.append(
                f"{win_rate_text} [{indicator_color}]{indicator}[/{indicator_color}] "
                f"(target: {self._format_percentage(targets.win_rate_target)})\n"
            )
        else:
            content.append(f"{win_rate_text}\n")

        # Risk/Reward ratio with target comparison
        rr_text = f"Avg Risk/Reward:  {metrics.avg_risk_reward:.2f}"
        if targets:
            meets_target = metrics.avg_risk_reward >= targets.avg_risk_reward_target
            indicator = "✓" if meets_target else "✗"
            indicator_color = "green" if meets_target else "red"
            content.append(
                f"{rr_text} [{indicator_color}]{indicator}[/{indicator_color}] "
                f"(target: {targets.avg_risk_reward_target:.2f})\n"
            )
        else:
            content.append(f"{rr_text}\n")

        # Total P&L with target comparison
        total_pl_color = self._get_pl_color(metrics.total_pl)
        total_pl_text = f"Total P&L:        ${self._format_currency(metrics.total_pl)}"
        if targets:
            meets_target = metrics.total_pl >= targets.daily_pl_target
            indicator = "✓" if meets_target else "✗"
            indicator_color = "green" if meets_target else "red"
            content.append(
                f"[{total_pl_color}]{total_pl_text}[/{total_pl_color}] "
                f"[{indicator_color}]{indicator}[/{indicator_color}] "
                f"(target: ${self._format_currency(targets.daily_pl_target)})\n"
            )
        else:
            content.append(f"[{total_pl_color}]{total_pl_text}[/{total_pl_color}]\n")

        # Realized and unrealized P&L
        realized_color = self._get_pl_color(metrics.total_realized_pl)
        unrealized_color = self._get_pl_color(metrics.total_unrealized_pl)
        content.append(
            f"  Realized:       [{realized_color}]${self._format_currency(metrics.total_realized_pl)}[/{realized_color}]\n"
        )
        content.append(
            f"  Unrealized:     [{unrealized_color}]${self._format_currency(metrics.total_unrealized_pl)}[/{unrealized_color}]\n"
        )

        # Streak
        streak_color = (
            "green" if metrics.streak_type == "WIN" else "red" if metrics.streak_type == "LOSS" else "yellow"
        )
        streak_text = (
            f"Current Streak:   [{streak_color}]{metrics.current_streak} {metrics.streak_type}[/{streak_color}]\n"
        )
        content.append(streak_text)

        # Trades today with target comparison
        trades_text = f"Trades Today:     {metrics.trades_today}"
        if targets:
            meets_target = metrics.trades_today >= targets.trades_per_day_target
            indicator = "✓" if meets_target else "✗"
            indicator_color = "green" if meets_target else "red"
            content.append(
                f"{trades_text} [{indicator_color}]{indicator}[/{indicator_color}] "
                f"(target: {targets.trades_per_day_target})\n"
            )
        else:
            content.append(f"{trades_text}\n")

        # Session count
        content.append(f"Sessions:         {metrics.session_count}")

        return Panel(content, title="Performance Metrics", border_style="magenta")

    def render_full_dashboard(self, state: DashboardState) -> Layout:
        """
        Render complete dashboard layout.

        Args:
            state: Complete dashboard state with all components

        Returns:
            Layout with account status, positions, and performance metrics
        """
        layout = Layout()

        # Create header with timestamp
        header = Panel(
            Text(
                f"Trading Dashboard - {self._format_datetime(state.timestamp)}",
                justify="center",
            ),
            style="bold white on blue",
        )

        # Render components
        account_panel = self.render_account_status(
            state.account_status, state.market_status
        )
        positions_table = self.render_positions_table(state.positions)
        metrics_panel = self.render_performance_metrics(
            state.performance_metrics, state.targets
        )

        # Build layout structure
        layout.split_column(
            Layout(header, size=3, name="header"),
            Layout(name="body"),
        )

        layout["body"].split_row(
            Layout(account_panel, name="account"),
            Layout(name="main"),
        )

        layout["main"].split_column(
            Layout(positions_table, name="positions"),
            Layout(metrics_panel, name="metrics"),
        )

        return layout

    @staticmethod
    def _format_currency(value: Decimal) -> str:
        """Format decimal as currency string: X,XXX.XX"""
        return f"{value:,.2f}"

    @staticmethod
    def _format_percentage(value: float | Decimal) -> str:
        """Format decimal/float as percentage string: XX.XX%"""
        return f"{float(value):.2f}%"

    @staticmethod
    def _format_datetime(dt: datetime) -> str:
        """Format datetime for display."""
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _get_pl_color(value: Decimal | float) -> str:
        """
        Determine color for P&L value.

        Args:
            value: P&L value to color-code

        Returns:
            Color name: "green" for positive, "red" for negative, "yellow" for zero
        """
        numeric_value = float(value)
        if numeric_value > 0:
            return "green"
        elif numeric_value < 0:
            return "red"
        else:
            return "yellow"
