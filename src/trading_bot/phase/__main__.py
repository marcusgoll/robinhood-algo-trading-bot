"""Entry point for phase progression CLI.

Enables running the CLI as a module:
    python -m trading_bot.phase export --start 2025-10-01 --end 2025-10-31
    python -m trading_bot.phase validate-transition --to proof
    python -m trading_bot.phase status

Based on: specs/022-pos-scale-progress/spec.md FR-008
Tasks: T149
"""

from trading_bot.phase.cli import main

if __name__ == "__main__":
    main()
