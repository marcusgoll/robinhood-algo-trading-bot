"""
Performance tracker service for aggregating trade metrics.
"""

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Optional

from ..dashboard.metrics_calculator import MetricsCalculator
from ..logging.query_helper import TradeQueryHelper
from .cache import load_index, needs_refresh, update_index
from .models import PerformanceSummary


class PerformanceTracker:
    """
    Orchestrates trade log aggregation, caching, and summary generation.

    Reuses TradeQueryHelper for JSONL ingestion and MetricsCalculator
    for core metric computations.
    """

    def __init__(
        self,
        log_dir: Path = Path("logs"),
        cache_dir: Path = Path("logs/performance")
    ) -> None:
        """
        Initialize the performance tracker.

        Args:
            log_dir: Directory containing trade JSONL files
            cache_dir: Directory for performance summaries and cache
        """
        self.query_helper = TradeQueryHelper(log_dir=log_dir)
        self.cache_dir = cache_dir
        self.cache_index_path = cache_dir / "performance-index.json"

        # In-memory cache for get_summary calls
        self._summary_cache: dict[str, PerformanceSummary] = {}

    def get_summary(
        self,
        window: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> PerformanceSummary:
        """
        Get performance summary for the specified window.

        Args:
            window: Time window ("daily", "weekly", "monthly")
            start_date: Optional start date (ISO format YYYY-MM-DD)
            end_date: Optional end date (ISO format YYYY-MM-DD)

        Returns:
            PerformanceSummary with aggregated metrics
        """
        # Generate cache key
        cache_key = f"{window}:{start_date}:{end_date}"

        # Check in-memory cache
        if cache_key in self._summary_cache:
            return self._summary_cache[cache_key]

        # Determine date range based on window
        if not start_date:
            start_date = self._get_default_start_date(window)
        if not end_date:
            end_date = datetime.now(UTC).date().isoformat()

        # Query trades for date range
        trades = self.query_helper.query_by_date_range(start_date, end_date)

        # Calculate metrics using MetricsCalculator
        if trades:
            # Get closed trades for metrics
            closed_trades = [t for t in trades if t.outcome in ["win", "loss", "breakeven"]]

            win_rate = MetricsCalculator.calculate_win_rate(trades)
            avg_rr = MetricsCalculator.calculate_avg_risk_reward(trades)
            streak_count, streak_type = MetricsCalculator.calculate_current_streak(trades)

            # Calculate P&L (no positions for historical data)
            realized_pl, unrealized_pl, total_pl = MetricsCalculator.calculate_total_pl(trades, [])

            # Calculate average profit/loss per trade
            wins = [t for t in closed_trades if t.outcome == "win"]
            losses = [t for t in closed_trades if t.outcome == "loss"]

            avg_profit = (
                sum(t.net_profit_loss for t in wins if t.net_profit_loss) / len(wins)
                if wins else Decimal("0")
            )
            avg_loss = (
                sum(t.net_profit_loss for t in losses if t.net_profit_loss) / len(losses)
                if losses else Decimal("0")
            )
        else:
            # No trades - return zeros
            win_rate = 0.0
            avg_rr = 0.0
            streak_count = 0
            streak_type = "none"
            realized_pl = Decimal("0")
            unrealized_pl = Decimal("0")
            avg_profit = Decimal("0")
            avg_loss = Decimal("0")

        # Build summary
        summary = PerformanceSummary(
            window=window,
            start_date=datetime.fromisoformat(start_date + "T00:00:00+00:00"),
            end_date=datetime.fromisoformat(end_date + "T23:59:59+00:00"),
            total_trades=len([t for t in trades if t.outcome in ["win", "loss", "breakeven"]]),
            total_wins=len([t for t in trades if t.outcome == "win"]),
            total_losses=len([t for t in trades if t.outcome == "loss"]),
            win_rate=Decimal(str(win_rate / 100)),  # Convert % to decimal
            current_streak=streak_count,
            streak_type=streak_type.lower() if streak_type != "NONE" else "none",
            avg_profit_per_win=avg_profit,
            avg_loss_per_loss=avg_loss,
            avg_risk_reward_ratio=Decimal(str(avg_rr)),
            realized_pnl=realized_pl,
            unrealized_pnl=unrealized_pl,
            alert_status="OK",  # Will be updated by AlertEvaluator
            generated_at=datetime.now(UTC),
        )

        # Cache result
        self._summary_cache[cache_key] = summary

        return summary

    def _get_default_start_date(self, window: str) -> str:
        """Get default start date based on window type."""
        today = datetime.now(UTC).date()

        if window == "daily":
            return today.isoformat()
        elif window == "weekly":
            # Last 7 days
            return (today - timedelta(days=7)).isoformat()
        elif window == "monthly":
            # Last 30 days
            return (today - timedelta(days=30)).isoformat()
        else:
            return today.isoformat()

    def serialize_summary(self, summary: PerformanceSummary) -> dict:
        """
        Serialize PerformanceSummary to JSON-compatible dict.

        Args:
            summary: PerformanceSummary to serialize

        Returns:
            Dictionary matching performance-summary.schema.json
        """
        return {
            "window": summary.window,
            "start_date": summary.start_date.isoformat(),
            "end_date": summary.end_date.isoformat(),
            "total_trades": summary.total_trades,
            "total_wins": summary.total_wins,
            "total_losses": summary.total_losses,
            "win_rate": str(summary.win_rate),
            "current_streak": summary.current_streak,
            "streak_type": summary.streak_type,
            "avg_profit_per_win": str(summary.avg_profit_per_win),
            "avg_loss_per_loss": str(summary.avg_loss_per_loss),
            "avg_risk_reward_ratio": str(summary.avg_risk_reward_ratio),
            "realized_pnl": str(summary.realized_pnl),
            "unrealized_pnl": str(summary.unrealized_pnl),
            "alert_status": summary.alert_status,
            "generated_at": summary.generated_at.isoformat(),
        }

    def export_markdown(self, summary: PerformanceSummary) -> str:
        """
        Export PerformanceSummary to Markdown format.

        Args:
            summary: PerformanceSummary to export

        Returns:
            Markdown-formatted string
        """
        md = f"""# Performance Summary - {summary.window.capitalize()}

## Overview

- **Window**: {summary.window}
- **Period**: {summary.start_date.date()} to {summary.end_date.date()}
- **Generated**: {summary.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}
- **Status**: {summary.alert_status}

## Metrics

| Metric | Value |
|--------|-------|
| Total Trades | {summary.total_trades} |
| Wins | {summary.total_wins} |
| Losses | {summary.total_losses} |
| Win Rate | {float(summary.win_rate) * 100:.2f}% |
| Current Streak | {summary.current_streak} {summary.streak_type} |
| Avg Profit (Win) | ${summary.avg_profit_per_win:.2f} |
| Avg Loss (Loss) | ${summary.avg_loss_per_loss:.2f} |
| Avg Risk:Reward | {summary.avg_risk_reward_ratio:.2f}:1 |
| Realized P&L | ${summary.realized_pnl:.2f} |
| Unrealized P&L | ${summary.unrealized_pnl:.2f} |

## Alerts

"""
        if summary.alert_status == "OK":
            md += "✅ All metrics within targets\n"
        else:
            md += f"⚠️ Alert Status: {summary.alert_status}\n"

        return md

    def export_to_files(
        self,
        summary: PerformanceSummary,
        export_json: bool = True,
        export_md: bool = True
    ) -> tuple[Optional[Path], Optional[Path]]:
        """
        Export summary to JSON and/or Markdown files.

        Args:
            summary: PerformanceSummary to export
            export_json: Export JSON file
            export_md: Export Markdown file

        Returns:
            Tuple of (json_path, md_path) or (None, None) if not exported
        """
        # Ensure directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        date_str = summary.start_date.date().isoformat()
        base_name = f"{summary.window}-summary-{date_str}"

        json_path = None
        md_path = None

        if export_json:
            json_path = self.cache_dir / f"{base_name}.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(self.serialize_summary(summary), f, indent=2)

        if export_md:
            md_path = self.cache_dir / f"{base_name}.md"
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(self.export_markdown(summary))

        return (json_path, md_path)
