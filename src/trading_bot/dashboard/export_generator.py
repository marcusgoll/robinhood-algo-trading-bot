"""
Export generator for dashboard state.

Provides JSON and Markdown export functionality with proper serialization
of Decimal and datetime types.
"""

import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from src.trading_bot.dashboard.models import DashboardState


class ExportGenerator:
    """Generates JSON and Markdown exports of dashboard state."""

    def __init__(self) -> None:
        """Initialize export generator."""
        pass

    def export_to_json(self, state: DashboardState, filepath: Path) -> None:
        """
        Export dashboard state to JSON file.

        Args:
            state: Dashboard state to export
            filepath: Path to write JSON file

        Raises:
            IOError: If file cannot be written
        """
        # Ensure parent directory exists
        filepath.parent.mkdir(parents=True, exist_ok=True)

        # Convert state to serializable dict
        data = self._serialize_state(state)

        # Write JSON file with indentation
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def export_to_markdown(self, state: DashboardState, filepath: Path) -> None:
        """
        Export dashboard state to Markdown file.

        Args:
            state: Dashboard state to export
            filepath: Path to write Markdown file

        Raises:
            IOError: If file cannot be written
        """
        # Ensure parent directory exists
        filepath.parent.mkdir(parents=True, exist_ok=True)

        # Generate markdown content
        markdown = self._generate_markdown(state)

        # Write markdown file
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(markdown)

    def generate_exports(self, state: DashboardState) -> tuple[Path, Path]:
        """
        Generate both JSON and Markdown exports with date-based filenames.

        Args:
            state: Dashboard state to export

        Returns:
            Tuple of (json_path, markdown_path)

        Raises:
            IOError: If files cannot be written
        """
        # Create date-based filename
        date_str = datetime.now().strftime("%Y-%m-%d")
        logs_dir = Path("logs")

        json_path = logs_dir / f"dashboard-export-{date_str}.json"
        markdown_path = logs_dir / f"dashboard-export-{date_str}.md"

        # Generate both exports
        self.export_to_json(state, json_path)
        self.export_to_markdown(state, markdown_path)

        return json_path, markdown_path

    def _serialize_state(self, state: DashboardState) -> dict[str, Any]:
        """
        Convert DashboardState to JSON-serializable dict.

        Args:
            state: Dashboard state to serialize

        Returns:
            Serializable dictionary
        """
        return {
            "timestamp": state.timestamp.isoformat(),
            "market_status": state.market_status,
            "account_status": {
                "buying_power": float(state.account_status.buying_power),
                "account_balance": float(state.account_status.account_balance),
                "cash_balance": float(state.account_status.cash_balance),
                "day_trade_count": state.account_status.day_trade_count,
                "last_updated": state.account_status.last_updated.isoformat(),
            },
            "positions": [
                {
                    "symbol": pos.symbol,
                    "quantity": pos.quantity,
                    "entry_price": float(pos.entry_price),
                    "current_price": float(pos.current_price),
                    "unrealized_pl": float(pos.unrealized_pl),
                    "unrealized_pl_pct": float(pos.unrealized_pl_pct),
                }
                for pos in state.positions
            ],
            "performance_metrics": {
                "win_rate": state.performance_metrics.win_rate,
                "avg_risk_reward": state.performance_metrics.avg_risk_reward,
                "total_realized_pl": float(state.performance_metrics.total_realized_pl),
                "total_unrealized_pl": float(
                    state.performance_metrics.total_unrealized_pl
                ),
                "total_pl": float(state.performance_metrics.total_pl),
                "current_streak": state.performance_metrics.current_streak,
                "streak_type": state.performance_metrics.streak_type,
                "trades_today": state.performance_metrics.trades_today,
                "session_count": state.performance_metrics.session_count,
            },
            "targets": (
                {
                    "win_rate_target": state.targets.win_rate_target,
                    "daily_pl_target": float(state.targets.daily_pl_target),
                    "trades_per_day_target": state.targets.trades_per_day_target,
                    "max_drawdown_target": float(state.targets.max_drawdown_target),
                    "avg_risk_reward_target": state.targets.avg_risk_reward_target,
                }
                if state.targets
                else None
            ),
        }

    def _generate_markdown(self, state: DashboardState) -> str:
        """
        Generate Markdown report from dashboard state.

        Args:
            state: Dashboard state to format

        Returns:
            Formatted markdown string
        """
        lines = []

        # Header
        lines.append("# Trading Dashboard Export")
        lines.append("")
        lines.append(f"**Generated:** {state.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Market Status:** {state.market_status}")
        lines.append("")

        # Account Status
        lines.append("## Account Status")
        lines.append("")
        lines.append(
            f"- **Buying Power:** ${state.account_status.buying_power:,.2f}"
        )
        lines.append(
            f"- **Account Balance:** ${state.account_status.account_balance:,.2f}"
        )
        lines.append(f"- **Cash Balance:** ${state.account_status.cash_balance:,.2f}")
        lines.append(f"- **Day Trade Count:** {state.account_status.day_trade_count}")
        lines.append(
            f"- **Last Updated:** {state.account_status.last_updated.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        lines.append("")

        # Positions
        lines.append("## Positions")
        lines.append("")
        if state.positions:
            lines.append("| Symbol | Quantity | Entry Price | Current Price | P&L | P&L % |")
            lines.append("|--------|----------|-------------|---------------|-----|-------|")
            for pos in state.positions:
                pl_sign = "+" if pos.unrealized_pl >= 0 else ""
                lines.append(
                    f"| {pos.symbol} | {pos.quantity} | ${pos.entry_price:.2f} | "
                    f"${pos.current_price:.2f} | {pl_sign}${pos.unrealized_pl:.2f} | "
                    f"{pl_sign}{pos.unrealized_pl_pct:.2f}% |"
                )
        else:
            lines.append("*No open positions*")
        lines.append("")

        # Performance Metrics
        lines.append("## Performance Metrics")
        lines.append("")
        metrics = state.performance_metrics
        lines.append(f"- **Win Rate:** {metrics.win_rate:.2f}%")
        lines.append(f"- **Average Risk/Reward:** {metrics.avg_risk_reward:.2f}")
        lines.append(f"- **Total Realized P&L:** ${metrics.total_realized_pl:,.2f}")
        lines.append(
            f"- **Total Unrealized P&L:** ${metrics.total_unrealized_pl:,.2f}"
        )
        lines.append(f"- **Total P&L:** ${metrics.total_pl:,.2f}")
        lines.append(
            f"- **Current Streak:** {metrics.current_streak} ({metrics.streak_type})"
        )
        lines.append(f"- **Trades Today:** {metrics.trades_today}")
        lines.append(f"- **Session Count:** {metrics.session_count}")
        lines.append("")

        # Targets (if available)
        if state.targets:
            lines.append("## Performance Targets")
            lines.append("")
            targets = state.targets

            # Win rate comparison
            win_rate_diff = metrics.win_rate - targets.win_rate_target
            win_rate_status = "✓" if win_rate_diff >= 0 else "✗"
            lines.append(
                f"- **Win Rate:** {metrics.win_rate:.2f}% vs {targets.win_rate_target:.2f}% "
                f"({win_rate_diff:+.2f}%) {win_rate_status}"
            )

            # Risk/reward comparison
            rr_diff = metrics.avg_risk_reward - targets.avg_risk_reward_target
            rr_status = "✓" if rr_diff >= 0 else "✗"
            lines.append(
                f"- **Avg Risk/Reward:** {metrics.avg_risk_reward:.2f} vs "
                f"{targets.avg_risk_reward_target:.2f} ({rr_diff:+.2f}) {rr_status}"
            )

            # Daily P&L comparison
            pl_diff = metrics.total_pl - targets.daily_pl_target
            pl_status = "✓" if pl_diff >= 0 else "✗"
            lines.append(
                f"- **Total P&L:** ${metrics.total_pl:,.2f} vs ${targets.daily_pl_target:,.2f} "
                f"(${pl_diff:+,.2f}) {pl_status}"
            )

            # Trades per day comparison
            trades_diff = metrics.trades_today - targets.trades_per_day_target
            trades_status = "✓" if metrics.trades_today >= targets.trades_per_day_target else "✗"
            lines.append(
                f"- **Trades Today:** {metrics.trades_today} vs {targets.trades_per_day_target} "
                f"({trades_diff:+d}) {trades_status}"
            )

            lines.append("")

        # Footer
        lines.append("---")
        lines.append("")
        lines.append("*Generated by Trading Bot Dashboard*")

        return "\n".join(lines)
