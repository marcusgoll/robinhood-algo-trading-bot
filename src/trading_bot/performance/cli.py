"""
CLI entrypoint for performance tracking commands.
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from .alerts import AlertEvaluator
from .tracker import PerformanceTracker


def main(argv: Optional[List[str]] = None) -> int:
    """
    CLI entrypoint for performance tracking.

    Args:
        argv: Command line arguments (defaults to sys.argv[1:])

    Returns:
        Exit code (0=success, 2=alert breach)
    """
    parser = argparse.ArgumentParser(
        description="Performance tracking and analytics"
    )
    parser.add_argument(
        "--window",
        choices=["daily", "weekly", "monthly"],
        default="daily",
        help="Time window for summary",
    )
    parser.add_argument(
        "--start",
        help="Start date (ISO format YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end",
        help="End date (ISO format YYYY-MM-DD)",
    )
    parser.add_argument(
        "--export",
        action="store_true",
        help="Export summary to JSON/Markdown",
    )
    parser.add_argument(
        "--backfill",
        type=int,
        metavar="N",
        help="Rebuild summaries for last N days",
    )

    args = parser.parse_args(argv)

    tracker = PerformanceTracker()
    evaluator = AlertEvaluator()

    # Handle backfill mode
    if args.backfill:
        print(f"Backfilling summaries for last {args.backfill} days...")
        today = datetime.now().date()

        for i in range(args.backfill):
            date = today - timedelta(days=i)
            date_str = date.isoformat()

            # Generate summary for each day
            summary = tracker.get_summary(
                window="daily",
                start_date=date_str,
                end_date=date_str
            )

            # Export if requested
            if args.export:
                tracker.export_to_files(summary)

            print(f"  ✓ {date_str}: {summary.total_trades} trades, "
                  f"{float(summary.win_rate) * 100:.1f}% win rate")

        return 0

    # Normal mode: single summary
    summary = tracker.get_summary(
        window=args.window,
        start_date=args.start,
        end_date=args.end
    )

    # Evaluate alerts
    alerts = evaluator.evaluate(summary)

    # Display summary
    print(f"\n=== Performance Summary ({summary.window}) ===")
    print(f"Period: {summary.start_date.date()} to {summary.end_date.date()}")
    print(f"\nMetrics:")
    print(f"  Total Trades: {summary.total_trades}")
    print(f"  Wins: {summary.total_wins}")
    print(f"  Losses: {summary.total_losses}")
    print(f"  Win Rate: {float(summary.win_rate) * 100:.2f}%")
    print(f"  Current Streak: {summary.current_streak} {summary.streak_type}")
    print(f"  Avg Profit (Win): ${summary.avg_profit_per_win:.2f}")
    print(f"  Avg Loss (Loss): ${summary.avg_loss_per_loss:.2f}")
    print(f"  Avg R:R: {summary.avg_risk_reward_ratio:.2f}:1")
    print(f"  Realized P&L: ${summary.realized_pnl:.2f}")
    print(f"  Unrealized P&L: ${summary.unrealized_pnl:.2f}")

    # Display alerts
    if alerts:
        print(f"\n⚠️  Alerts ({len(alerts)}):")
        for alert in alerts:
            print(f"  - {alert.metric}: {alert.actual} (target: {alert.target})")
    else:
        print(f"\n✅ All metrics within targets")

    # Export if requested
    if args.export:
        json_path, md_path = tracker.export_to_files(summary)
        print(f"\nExported:")
        if json_path:
            print(f"  JSON: {json_path}")
        if md_path:
            print(f"  Markdown: {md_path}")

    # Return exit code (2 if alerts exist)
    return 2 if alerts else 0


if __name__ == "__main__":
    sys.exit(main())
