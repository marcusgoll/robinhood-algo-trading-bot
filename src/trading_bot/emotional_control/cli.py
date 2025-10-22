"""
Emotional Control CLI Commands

Command-line interface for monitoring and managing emotional control state.

Constitution v1.0.0:
- §Audit_Everything: CLI provides transparency into state transitions
- §Safety_First: Manual reset requires explicit confirmation

Feature: emotional-control-me
Tasks: T018-T020 - CLI commands (status, reset, events)
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from src.trading_bot.emotional_control.config import EmotionalControlConfig
from src.trading_bot.emotional_control.tracker import EmotionalControl


def status(config_path: Optional[str] = None) -> None:
    """Display current emotional control state (T018).

    Shows:
    - Current state (ACTIVE/INACTIVE)
    - Trigger reason (if active)
    - Consecutive win/loss counters
    - Position size multiplier
    - Last state update timestamp

    Args:
        config_path: Optional path to config file (defaults to .env)

    Example:
        >>> python -m src.trading_bot.emotional_control.cli status
        Emotional Control Status
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        State: ACTIVE (⚠️  Position Sizing Reduced)
        Trigger: SINGLE_LOSS (3.5% loss on 2025-10-22 09:15:23 UTC)
        Position Multiplier: 0.25 (25% of normal size)
        Consecutive Losses: 1
        Consecutive Wins: 0
        Last Updated: 2025-10-22 09:15:23 UTC
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        Recovery: Requires 3 consecutive wins OR manual reset
    """
    # Load config
    config = EmotionalControlConfig.from_env() if config_path is None else EmotionalControlConfig.default()

    # Load tracker (reads state from file)
    tracker = EmotionalControl(config)

    # Get state
    state = tracker._state
    multiplier = tracker.get_position_multiplier()

    # Color codes (ANSI)
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RESET = "\033[0m"

    # Determine color based on state
    state_color = YELLOW if state.is_active else GREEN
    state_text = "ACTIVE" if state.is_active else "INACTIVE"
    state_label = f"{state_color}{state_text}{RESET}"

    # Print status
    print()
    print("Emotional Control Status")
    print("━" * 60)
    print(f"State: {state_label}", end="")

    if state.is_active:
        print(" (⚠️  Position Sizing Reduced)")
        print(f"Trigger: {state.trigger_reason} ({state.activated_at.strftime('%Y-%m-%d %H:%M:%S UTC')})")
        if state.loss_amount:
            loss_pct = (abs(state.loss_amount) / state.account_balance_at_activation) * 100
            print(f"Loss Amount: ${abs(state.loss_amount):,.2f} ({loss_pct:.2f}% of account)")
    else:
        print(" (✅ Normal Position Sizing)")
        print("Trigger: None")

    print(f"Position Multiplier: {multiplier} ({float(multiplier * 100):.0f}% of normal size)")
    print(f"Consecutive Losses: {state.consecutive_losses}")
    print(f"Consecutive Wins: {state.consecutive_wins}")
    print(f"Last Updated: {state.last_updated.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("━" * 60)

    if state.is_active:
        wins_needed = config.recovery_win_threshold - state.consecutive_wins
        print(f"Recovery: Requires {wins_needed} more consecutive wins OR manual reset")
    else:
        print("Recovery: Not needed (emotional control inactive)")

    print()


def reset(admin_id: str, reason: str, force: bool = False) -> None:
    """Manually reset emotional control to INACTIVE state (T019).

    Requires admin confirmation (unless --force flag provided).

    Args:
        admin_id: Admin identifier for audit trail
        reason: Reason for manual reset (logged to events)
        force: Skip confirmation prompt if True

    Example:
        >>> python -m src.trading_bot.emotional_control.cli reset --admin-id trader1 --reason "Strategy change"
        Confirm reset? (yes/no): yes
        ✅ Emotional control reset to INACTIVE
        Position multiplier restored to 1.00 (100% normal size)
    """
    # Validate arguments
    if not admin_id or not admin_id.strip():
        print("❌ Error: admin_id is required", file=sys.stderr)
        sys.exit(1)

    if not reason or not reason.strip():
        print("❌ Error: reason is required", file=sys.stderr)
        sys.exit(1)

    # Load config and tracker
    config = EmotionalControlConfig.from_env()
    tracker = EmotionalControl(config)

    # Check current state
    if not tracker._state.is_active:
        print("ℹ️  Emotional control already INACTIVE (no reset needed)")
        return

    # Confirmation prompt (unless --force)
    if not force:
        print()
        print("⚠️  Manual Reset Confirmation")
        print("━" * 60)
        print(f"Current State: ACTIVE (position sizing at {float(config.position_size_multiplier_active * 100):.0f}%)")
        print(f"Admin: {admin_id}")
        print(f"Reason: {reason}")
        print("━" * 60)
        print()

        response = input("Confirm reset to INACTIVE? (yes/no): ").strip().lower()

        if response not in ["yes", "y"]:
            print("Reset cancelled.")
            return

    # Execute reset
    try:
        tracker.reset_manual(admin_id=admin_id, reset_reason=reason, confirm=True)
        print()
        print("✅ Emotional control reset to INACTIVE")
        print("Position multiplier restored to 1.00 (100% normal size)")
        print(f"Reset logged to events with admin_id: {admin_id}")
        print()
    except ValueError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


def events(days: int = 7, limit: Optional[int] = None) -> None:
    """Display recent emotional control events from JSONL logs (T020).

    Args:
        days: Number of days of history to display (default: 7)
        limit: Maximum number of events to display (default: no limit)

    Example:
        >>> python -m src.trading_bot.emotional_control.cli events --days 7
        Emotional Control Events (Last 7 Days)
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        2025-10-22 09:15:23 UTC | ACTIVATED      | SINGLE_LOSS    | Multiplier: 0.25
        2025-10-21 14:32:10 UTC | DEACTIVATED    | PROFITABLE_... | Multiplier: 1.00
        2025-10-21 08:45:00 UTC | ACTIVATED      | STREAK_LOSS    | Multiplier: 0.25
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        Total: 3 events
    """
    # Load config
    config = EmotionalControlConfig.from_env()
    log_dir = config.event_log_dir

    # Calculate date range
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)

    # Collect events from JSONL files (daily rotation)
    events_list = []

    for day_offset in range(days + 1):  # Include today
        current_date = end_date - timedelta(days=day_offset)
        log_file = log_dir / f"events-{current_date.strftime('%Y-%m-%d')}.jsonl"

        if not log_file.exists():
            continue

        # Read JSONL file
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    event = json.loads(line)
                    event_time = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))

                    # Filter by date range
                    if start_date <= event_time <= end_date:
                        events_list.append(event)

        except (IOError, json.JSONDecodeError) as e:
            print(f"⚠️  Warning: Could not read {log_file.name}: {e}", file=sys.stderr)
            continue

    # Sort by timestamp (newest first)
    events_list.sort(key=lambda e: e["timestamp"], reverse=True)

    # Apply limit
    if limit:
        events_list = events_list[:limit]

    # Display events
    print()
    print(f"Emotional Control Events (Last {days} Days)")
    print("━" * 80)

    if not events_list:
        print("No events found in the specified time period.")
    else:
        for event in events_list:
            timestamp = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
            event_type = event["event_type"].ljust(14)
            trigger = (event.get("trigger_reason") or "N/A").ljust(14)
            multiplier = event.get("position_size_multiplier", "N/A")

            print(f"{timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')} | {event_type} | {trigger} | Multiplier: {multiplier}")

    print("━" * 80)
    print(f"Total: {len(events_list)} events")
    print()


# CLI entry point for testing
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Emotional Control CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Status command
    parser_status = subparsers.add_parser("status", help="Display current state")
    parser_status.add_argument("--config", type=str, help="Path to config file")

    # Reset command
    parser_reset = subparsers.add_parser("reset", help="Manual reset to INACTIVE")
    parser_reset.add_argument("--admin-id", required=True, help="Admin identifier")
    parser_reset.add_argument("--reason", required=True, help="Reset reason")
    parser_reset.add_argument("--force", action="store_true", help="Skip confirmation")

    # Events command
    parser_events = subparsers.add_parser("events", help="Display recent events")
    parser_events.add_argument("--days", type=int, default=7, help="Days of history (default: 7)")
    parser_events.add_argument("--limit", type=int, help="Max events to display")

    args = parser.parse_args()

    if args.command == "status":
        status(config_path=args.config)
    elif args.command == "reset":
        reset(admin_id=args.admin_id, reason=args.reason, force=args.force)
    elif args.command == "events":
        events(days=args.days, limit=args.limit)
    else:
        parser.print_help()
