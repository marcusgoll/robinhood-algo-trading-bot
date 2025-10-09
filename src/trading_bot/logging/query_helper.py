"""
Trade Query Helper

Provides high-performance querying and analytics for logged trade data.

Constitution v1.0.0:
- §Audit_Everything: Query and analyze logged trade data
- §Data_Integrity: Accurate filtering and aggregation
- NFR-005: <500ms query performance for 1000 trades

Feature: trade-logging
Tasks: T026-T029 [GREEN] - Implement TradeQueryHelper with streaming queries
"""

from pathlib import Path
from datetime import datetime, date
from typing import Optional, Generator
import json
from decimal import Decimal

from .trade_record import TradeRecord


class TradeQueryHelper:
    """Query and analyze trade logs with high performance.

    Provides efficient querying of JSONL trade logs with:
    - Date range filtering
    - Symbol filtering
    - Win rate calculation
    - Streaming I/O for large datasets

    Performance: <500ms for 1000 trades (NFR-005)
    """

    def __init__(self, log_dir: Path = Path("logs")) -> None:
        """Initialize TradeQueryHelper.

        Args:
            log_dir: Directory containing trade log files (default: "logs")
        """
        self.log_dir = Path(log_dir)

    def _read_jsonl_stream(self, file_path: Path) -> Generator[TradeRecord, None, None]:
        """Stream JSONL file line by line (memory efficient).

        Uses generator pattern to avoid loading entire file into memory.
        Critical for performance at scale (NFR-005).

        Args:
            file_path: Path to JSONL file

        Yields:
            TradeRecord: Parsed trade record from each line
        """
        if not file_path.exists():
            return

        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:  # Skip empty lines
                    continue

                try:
                    trade_dict = json.loads(line)

                    # Convert string prices back to Decimal
                    for field in ['price', 'total_value', 'stop_loss', 'target',
                                'profit_loss', 'slippage', 'commission', 'net_profit_loss']:
                        if field in trade_dict and trade_dict[field] is not None:
                            trade_dict[field] = Decimal(trade_dict[field])

                    yield TradeRecord(**trade_dict)
                except (json.JSONDecodeError, TypeError, ValueError) as e:
                    # Skip malformed lines (defensive programming)
                    continue

    def query_by_date_range(
        self,
        start_date: str,
        end_date: str
    ) -> list[TradeRecord]:
        """Query trades within a date range.

        Reads JSONL files for the specified date range and returns all trades
        where the timestamp falls within [start_date, end_date] inclusive.

        Args:
            start_date: Start date in "YYYY-MM-DD" format (inclusive)
            end_date: End date in "YYYY-MM-DD" format (inclusive)

        Returns:
            list[TradeRecord]: Trades within the date range, sorted by timestamp

        Example:
            >>> helper = TradeQueryHelper(log_dir=Path("logs"))
            >>> trades = helper.query_by_date_range("2025-01-09", "2025-01-10")
            >>> len(trades)
            2
        """
        # Parse date strings
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()

        results: list[TradeRecord] = []

        # Iterate through all JSONL files in log directory
        log_files = sorted(self.log_dir.glob("*.jsonl"))

        for log_file in log_files:
            # Stream trades from file
            for trade in self._read_jsonl_stream(log_file):
                # Parse timestamp and filter by date range
                trade_datetime = datetime.fromisoformat(trade.timestamp)
                trade_date = trade_datetime.date()

                if start <= trade_date <= end:
                    results.append(trade)

        return results

    def query_by_symbol(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> list[TradeRecord]:
        """Query trades for a specific symbol.

        Filters trades by symbol, optionally within a date range.

        Args:
            symbol: Stock ticker symbol (e.g., "AAPL")
            start_date: Optional start date in "YYYY-MM-DD" format
            end_date: Optional end date in "YYYY-MM-DD" format

        Returns:
            list[TradeRecord]: Trades matching the symbol filter

        Example:
            >>> helper = TradeQueryHelper(log_dir=Path("logs"))
            >>> aapl_trades = helper.query_by_symbol("AAPL")
            >>> all(t.symbol == "AAPL" for t in aapl_trades)
            True
        """
        # If date range provided, use it to narrow search
        if start_date and end_date:
            all_trades = self.query_by_date_range(start_date, end_date)
        else:
            # Otherwise, read all JSONL files
            all_trades = []
            log_files = sorted(self.log_dir.glob("*.jsonl"))

            for log_file in log_files:
                all_trades.extend(self._read_jsonl_stream(log_file))

        # Filter by symbol
        return [trade for trade in all_trades if trade.symbol == symbol]

    def calculate_win_rate(self, trades: Optional[list[TradeRecord]] = None) -> float:
        """Calculate win rate from closed trades.

        Win rate = (wins / total_closed_trades) * 100

        Closed trades have outcome in: ["win", "loss", "breakeven"]
        Open trades (outcome="open") are excluded from calculation.

        Args:
            trades: Optional list of trades to analyze. If None, reads all trades.

        Returns:
            float: Win rate percentage (0-100)

        Example:
            >>> # 3 wins, 2 losses, 1 breakeven = 3/6 = 50%
            >>> helper = TradeQueryHelper(log_dir=Path("logs"))
            >>> win_rate = helper.calculate_win_rate()
            >>> win_rate
            50.0
        """
        # If no trades provided, read all trades from log directory
        if trades is None:
            trades = []
            log_files = sorted(self.log_dir.glob("*.jsonl"))

            for log_file in log_files:
                trades.extend(self._read_jsonl_stream(log_file))

        # Filter for closed trades only
        closed_trades = [
            trade for trade in trades
            if trade.outcome in ["win", "loss", "breakeven"]
        ]

        # Handle edge case: no closed trades
        if len(closed_trades) == 0:
            return 0.0

        # Count wins
        wins = sum(1 for trade in closed_trades if trade.outcome == "win")

        # Calculate win rate
        win_rate = (wins / len(closed_trades)) * 100

        return float(win_rate)
