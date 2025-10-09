"""
Allow running the trading bot as a module: python -m trading_bot

This provides an alternative entry point to running main.py directly.

Usage:
    python -m trading_bot --dry-run
    python -m trading_bot --json
    python -m trading_bot

T040 [P]: Parallel task - Add __main__.py for python -m invocation
"""

from .main import main
import sys

if __name__ == "__main__":
    sys.exit(main())
