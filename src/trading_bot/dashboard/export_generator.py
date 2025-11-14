"""Export generator for dashboard snapshots."""

from __future__ import annotations

import json
from datetime import UTC
from pathlib import Path
from typing import Any

from .models import DashboardSnapshot, PositionDisplay


class ExportGenerator:
    """Generates JSON and Markdown exports of dashboard snapshots."""

    def export_to_json(self, snapshot: DashboardSnapshot, filepath: Path) -> None:
        """Write snapshot to JSON file (ISO timestamps, Decimal-safe)."""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        data = self._serialize_snapshot(snapshot)
        with filepath.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)

    def export_to_markdown(self, snapshot: DashboardSnapshot, filepath: Path) -> None:
        """Write snapshot to Markdown report."""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        markdown = self._generate_markdown(snapshot)
        with filepath.open("w", encoding="utf-8") as handle:
            handle.write(markdown)

    def generate_exports(self, snapshot: DashboardSnapshot) -> tuple[Path, Path]:
        """Generate JSON and Markdown exports for the provided snapshot."""
        date_str = snapshot.generated_at.astimezone(UTC).strftime("%Y-%m-%d")
        logs_dir = Path("logs")
        json_path = logs_dir / f"dashboard-export-{date_str}.json"
        md_path = logs_dir / f"dashboard-export-{date_str}.md"

        self.export_to_json(snapshot, json_path)
        self.export_to_markdown(snapshot, md_path)

        return json_path, md_path

    # ------------------------------------------------------------------
    # Serialization helpers
    # ------------------------------------------------------------------
    def _serialize_snapshot(self, snapshot: DashboardSnapshot) -> dict[str, Any]:
        """Convert DashboardSnapshot into a JSON-serialisable dict."""
        return {
            "generated_at": snapshot.generated_at.isoformat(),
            "market_status": snapshot.market_status,
            "data_age_seconds": snapshot.data_age_seconds,
            "is_data_stale": snapshot.is_data_stale,
            "warnings": list(snapshot.warnings),
            "account_status": {
                "buying_power": str(snapshot.account_status.buying_power),
                "account_balance": str(snapshot.account_status.account_balance),
                "cash_balance": str(snapshot.account_status.cash_balance),
                "day_trade_count": snapshot.account_status.day_trade_count,
                "last_updated": snapshot.account_status.last_updated.isoformat(),
            },
            "positions": [self._serialize_position(pos) for pos in snapshot.positions],
            "performance_metrics": {
                "win_rate": snapshot.performance_metrics.win_rate,
                "avg_risk_reward": snapshot.performance_metrics.avg_risk_reward,
                "total_realized_pl": str(snapshot.performance_metrics.total_realized_pl),
                "total_unrealized_pl": str(snapshot.performance_metrics.total_unrealized_pl),
                "total_pl": str(snapshot.performance_metrics.total_pl),
                "current_streak": snapshot.performance_metrics.current_streak,
                "streak_type": snapshot.performance_metrics.streak_type,
                "trades_today": snapshot.performance_metrics.trades_today,
                "session_count": snapshot.performance_metrics.session_count,
                "max_drawdown": str(snapshot.performance_metrics.max_drawdown),
            },
            "targets": (
                {
                    "win_rate_target": snapshot.targets.win_rate_target,
                    "daily_pl_target": str(snapshot.targets.daily_pl_target),
                    "trades_per_day_target": snapshot.targets.trades_per_day_target,
                    "max_drawdown_target": str(snapshot.targets.max_drawdown_target),
                    "avg_risk_reward_target": snapshot.targets.avg_risk_reward_target,
                }
                if snapshot.targets
                else None
            ),
        }

    def _serialize_position(self, position: PositionDisplay) -> dict[str, Any]:
        """Serialize PositionDisplay with formatted decimals."""
        return {
            "symbol": position.symbol,
            "quantity": position.quantity,
            "entry_price": str(position.entry_price),
            "current_price": str(position.current_price),
            "unrealized_pl": str(position.unrealized_pl),
            "unrealized_pl_pct": str(position.unrealized_pl_pct),
            "last_updated": position.last_updated.isoformat(),
        }

    def _generate_markdown(self, snapshot: DashboardSnapshot) -> str:
        """Create Markdown summary for the snapshot."""
        lines: list[str] = []

        lines.append("# Trading Dashboard Export")
        lines.append("")
        lines.append(f"**Generated:** {snapshot.generated_at.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Market Status:** {snapshot.market_status}")
        lines.append(f"**Data Age:** {int(snapshot.data_age_seconds)}s")
        lines.append(f"**Data Stale:** {'Yes' if snapshot.is_data_stale else 'No'}")
        lines.append("")

        account = snapshot.account_status
        lines.append("## Account Status")
        lines.append("")
        lines.append(f"- **Buying Power:** ${account.buying_power:,.2f}")
        lines.append(f"- **Account Balance:** ${account.account_balance:,.2f}")
        lines.append(f"- **Cash Balance:** ${account.cash_balance:,.2f}")
        lines.append(f"- **Day Trade Count:** {account.day_trade_count}")
        lines.append(f"- **Last Updated:** {account.last_updated.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        lines.append("## Positions")
        lines.append("")
        positions = list(snapshot.positions)
        if positions:
            lines.append("| Symbol | Quantity | Entry Price | Current Price | P&L | P&L % | Updated |")
            lines.append("|--------|----------|-------------|---------------|-----|-------|---------|")
            for position in positions:
                # Format P&L with sign before dollar sign
                pl_val = float(position.unrealized_pl)
                pl_formatted = f"+${pl_val:.2f}" if pl_val >= 0 else f"-${abs(pl_val):.2f}"
                pct_val = float(position.unrealized_pl_pct)
                pct_formatted = f"+{pct_val:.2f}%" if pct_val >= 0 else f"{pct_val:.2f}%"
                lines.append(
                    f"| {position.symbol} | {position.quantity} | ${position.entry_price:.2f} | "
                    f"${position.current_price:.2f} | {pl_formatted} | "
                    f"{pct_formatted} | {position.last_updated.strftime('%H:%M:%S')} |"
                )
        else:
            lines.append("*No open positions*")
        lines.append("")

        metrics = snapshot.performance_metrics
        lines.append("## Performance Metrics")
        lines.append("")
        lines.append(f"- **Win Rate:** {metrics.win_rate:.2f}%")
        lines.append(f"- **Average Risk/Reward:** {metrics.avg_risk_reward:.2f}")
        lines.append(f"- **Total Realized P&L:** ${metrics.total_realized_pl:,.2f}")
        lines.append(f"- **Total Unrealized P&L:** ${metrics.total_unrealized_pl:,.2f}")
        lines.append(f"- **Total P&L:** ${metrics.total_pl:,.2f}")
        lines.append(f"- **Max Drawdown:** ${metrics.max_drawdown:,.2f}")
        lines.append(f"- **Current Streak:** {metrics.current_streak} ({metrics.streak_type})")
        lines.append(f"- **Trades Today:** {metrics.trades_today}")
        lines.append(f"- **Session Count:** {metrics.session_count}")
        lines.append("")

        if snapshot.targets:
            targets = snapshot.targets
            lines.append("## Performance Targets")
            lines.append("")

            win_diff = metrics.win_rate - targets.win_rate_target
            lines.append(
                f"- **Win Rate:** {metrics.win_rate:.2f}% vs {targets.win_rate_target:.2f}% "
                f"({win_diff:+.2f}%) {'>' if win_diff >= 0 else '<'}"
            )

            if targets.avg_risk_reward_target is not None:
                rr_diff = metrics.avg_risk_reward - targets.avg_risk_reward_target
                lines.append(
                    f"- **Avg Risk/Reward:** {metrics.avg_risk_reward:.2f} vs {targets.avg_risk_reward_target:.2f} "
                    f"({rr_diff:+.2f}) {'>' if rr_diff >= 0 else '<'}"
                )

            pl_diff = metrics.total_pl - targets.daily_pl_target
            lines.append(
                f"- **Total P&L:** ${metrics.total_pl:,.2f} vs ${targets.daily_pl_target:,.2f} "
                f"(${pl_diff:+,.2f}) {'>' if pl_diff >= 0 else '<'}"
            )

            trades_diff = metrics.trades_today - targets.trades_per_day_target
            lines.append(
                f"- **Trades Today:** {metrics.trades_today} vs {targets.trades_per_day_target} "
                f"({trades_diff:+d}) {'>' if trades_diff >= 0 else '<'}"
            )

            drawdown_diff = metrics.max_drawdown - targets.max_drawdown_target
            lines.append(
                f"- **Max Drawdown:** ${metrics.max_drawdown:,.2f} vs ${targets.max_drawdown_target:,.2f} "
                f"(${drawdown_diff:+,.2f}) {'>' if drawdown_diff >= 0 else '<'}"
            )

            lines.append("")

        if snapshot.warnings:
            lines.append("## Warnings")
            lines.append("")
            for warning in snapshot.warnings:
                lines.append(f"- {warning}")
            lines.append("")

        lines.append("---")
        lines.append("")
        lines.append("*Generated by Trading Bot Dashboard*")

        return "\n".join(lines)
