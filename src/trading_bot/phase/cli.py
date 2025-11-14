"""Phase progression CLI for export and validation.

Command-line interface for:
- Exporting phase history to CSV/JSON
- Validating phase transition readiness
- Displaying current phase status

Based on: specs/022-pos-scale-progress/spec.md FR-008
Tasks: T140-T150 (US6)
"""

import argparse
import csv
import json
from datetime import date
from pathlib import Path
from typing import Optional

from trading_bot.phase.history_logger import HistoryLogger, DecimalEncoder
from trading_bot.phase.manager import PhaseManager
from trading_bot.phase.models import Phase
from trading_bot.config import Config


def export_command(
    start_date: str,
    end_date: str,
    format: str,
    output: Optional[str] = None
) -> None:
    """Export phase history to CSV or JSON.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        format: Output format (csv or json)
        output: Output filename (default: auto-generated)

    Raises:
        ValueError: If format is not 'csv' or 'json'

    Side Effects:
        - Creates export file in current directory
        - Prints success message to stdout

    Example:
        >>> export_command("2025-10-01", "2025-10-31", "csv")
        # Creates: phase-history_2025-10-01_2025-10-31.csv
        ✅ Exported 5 transitions to phase-history_2025-10-01_2025-10-31.csv
    """
    logger = HistoryLogger()

    # Parse dates
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)

    # Query transitions
    transitions = logger.query_transitions(start, end)

    # Generate output filename if not provided
    if output is None:
        output = f"phase-history_{start_date}_{end_date}.{format}"

    if format == "csv":
        _export_csv(transitions, output)
    elif format == "json":
        _export_json(transitions, output)
    else:
        raise ValueError(f"Unsupported format: {format}")

    print(f"✅ Exported {len(transitions)} transitions to {output}")


def _export_csv(transitions, filename):
    """Export to CSV format.

    CSV Columns (FR-008):
    - Date
    - From Phase
    - To Phase
    - Trigger
    - Validation Passed
    - Session Count
    - Win Rate
    - Avg R:R

    Args:
        transitions: List of PhaseTransition objects
        filename: Output CSV filename

    Side Effects:
        - Creates CSV file at specified path
    """
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)

        # Header
        writer.writerow([
            "Date",
            "From Phase",
            "To Phase",
            "Trigger",
            "Validation Passed",
            "Session Count",
            "Win Rate",
            "Avg R:R"
        ])

        # Data rows
        for t in transitions:
            writer.writerow([
                t.timestamp.date().isoformat(),
                t.from_phase.value,
                t.to_phase.value,
                t.trigger,
                t.validation_passed,
                t.metrics_snapshot.get("session_count", ""),
                t.metrics_snapshot.get("win_rate", ""),
                t.metrics_snapshot.get("avg_rr", "")
            ])


def _export_json(transitions, filename):
    """Export to JSON format.

    JSON Structure:
    - Array of transition objects
    - Each object contains: date, phases, trigger, validation, metrics
    - Decimal values serialized as strings

    Args:
        transitions: List of PhaseTransition objects
        filename: Output JSON filename

    Side Effects:
        - Creates JSON file at specified path
    """
    data = [
        {
            "date": t.timestamp.date().isoformat(),
            "from_phase": t.from_phase.value,
            "to_phase": t.to_phase.value,
            "trigger": t.trigger,
            "validation_passed": t.validation_passed,
            "metrics_snapshot": t.metrics_snapshot
        }
        for t in transitions
    ]

    with open(filename, 'w') as f:
        json.dump(data, f, indent=2, cls=DecimalEncoder)


def validate_command(to_phase: str) -> int:
    """Validate phase transition readiness.

    Displays validation criteria status and returns appropriate exit code.

    Args:
        to_phase: Target phase name (e.g., "proof", "trial", "scaling")

    Returns:
        Exit code (0 if ready, 1 if not ready)

    Side Effects:
        - Prints validation results to stdout
        - Shows criteria status with checkmarks/crosses

    Example:
        >>> validate_command("proof")
        Phase Transition Validation: experience → proof
        ==================================================
        ✅ session_count: MET
        ✅ win_rate: MET
        ✅ avg_rr: MET

        ✅ READY to advance
        # Returns 0
    """
    config = Config.from_env_and_json()
    manager = PhaseManager(config)

    target_phase = Phase.from_string(to_phase)

    # Validate transition (uses mocked metrics in manager._metrics)
    result = manager.validate_transition(target_phase)

    print(f"Phase Transition Validation: {config.current_phase} → {to_phase}")
    print("=" * 50)

    for criterion, met in result.criteria_met.items():
        status = "✅" if met else "❌"
        print(f"{status} {criterion}: {'MET' if met else 'NOT MET'}")

    if result.can_advance:
        print("\n✅ READY to advance")
        return 0
    else:
        print(f"\n❌ NOT READY: {', '.join(result.missing_requirements)}")
        return 1


def status_command() -> None:
    """Display current phase status.

    Shows:
    - Current phase
    - Max trades per day
    - Additional phase configuration

    Side Effects:
        - Prints status information to stdout

    Example:
        >>> status_command()
        Phase Progression Status
        ==================================================
        Current Phase: proof
        Max Trades/Day: 3
    """
    config = Config.from_env_and_json()

    print("Phase Progression Status")
    print("=" * 50)
    print(f"Current Phase: {config.current_phase}")
    print(f"Max Trades/Day: {config.max_trades_per_day}")


def main():
    """CLI entry point for phase progression commands.

    Commands:
    - export: Export phase history to CSV/JSON
    - validate-transition: Validate readiness for phase transition
    - status: Display current phase status

    Usage:
        python -m trading_bot.phase export --start 2025-10-01 --end 2025-10-31
        python -m trading_bot.phase validate-transition --to proof
        python -m trading_bot.phase status
    """
    parser = argparse.ArgumentParser(description="Phase progression CLI")
    subparsers = parser.add_subparsers(dest="command")

    # Export command
    export_parser = subparsers.add_parser("export", help="Export phase history")
    export_parser.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    export_parser.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    export_parser.add_argument("--format", choices=["csv", "json"], default="csv")
    export_parser.add_argument("--output", help="Output filename")

    # Validate command
    validate_parser = subparsers.add_parser(
        "validate-transition",
        help="Validate transition readiness"
    )
    validate_parser.add_argument("--to", required=True, help="Target phase")

    # Status command
    status_parser = subparsers.add_parser("status", help="Show current phase status")

    args = parser.parse_args()

    if args.command == "export":
        export_command(args.start, args.end, args.format, args.output)
    elif args.command == "validate-transition":
        exit_code = validate_command(args.to)
        exit(exit_code)
    elif args.command == "status":
        status_command()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
