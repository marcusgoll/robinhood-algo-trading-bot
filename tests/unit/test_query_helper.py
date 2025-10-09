"""
Unit tests for TradeQueryHelper (TDD RED Phase)

Tests Constitution v1.0.0 requirements:
- §Audit_Everything: Query and analyze logged trade data
- §Data_Integrity: Accurate filtering and aggregation
- NFR-005: <500ms query performance for 1000 trades

Feature: trade-logging
Tasks: T022-T025 [RED] - Write failing tests (TradeQueryHelper not implemented yet)
"""

import pytest
from pathlib import Path
import tempfile
import shutil
import time
import json
from datetime import datetime, timezone, timedelta
from decimal import Decimal

# This import will FAIL - TradeQueryHelper doesn't exist yet (RED phase)
from src.trading_bot.logging.query_helper import TradeQueryHelper

from src.trading_bot.logging.structured_logger import StructuredTradeLogger
from src.trading_bot.logging.trade_record import TradeRecord
from tests.fixtures.trade_fixtures import (
    sample_trade_sequence,
    sample_multi_symbol_sequence,
    sample_buy_trade,
    sample_sell_trade,
    sample_loss_trade,
    sample_breakeven_trade
)


class TestTradeQueryHelper:
    """Test TradeQueryHelper functionality (TDD RED phase)."""

    def setup_method(self) -> None:
        """Create temporary log directory for each test."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.logs_dir = self.temp_dir / "logs"

    def teardown_method(self) -> None:
        """Clean up temporary log directory after each test."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def _create_trade_with_timestamp(
        self,
        base_trade: TradeRecord,
        timestamp: datetime
    ) -> TradeRecord:
        """Create a trade record with a specific timestamp.

        Args:
            base_trade: Base TradeRecord to copy from
            timestamp: Datetime to use for the trade

        Returns:
            TradeRecord with updated timestamp
        """
        trade_dict = base_trade.to_json()
        trade_dict['timestamp'] = timestamp.isoformat()

        # Convert string prices back to Decimal
        for field in ['price', 'total_value', 'stop_loss', 'target',
                     'profit_loss', 'slippage', 'commission', 'net_profit_loss']:
            if field in trade_dict and trade_dict[field] is not None:
                trade_dict[field] = Decimal(trade_dict[field])

        return TradeRecord(**trade_dict)

    def _write_trades_to_file(
        self,
        trades: list[TradeRecord],
        filename: str
    ) -> Path:
        """Write trades to a specific JSONL file.

        Args:
            trades: List of TradeRecord instances
            filename: Filename (e.g., "2025-01-09.jsonl")

        Returns:
            Path to created file
        """
        log_file = self.logs_dir / filename
        log_file.parent.mkdir(parents=True, exist_ok=True)

        with open(log_file, 'w', encoding='utf-8') as f:
            for trade in trades:
                f.write(trade.to_jsonl_line() + '\n')

        return log_file

    def test_query_by_date_range(self) -> None:
        """T022 [RED]: TradeQueryHelper should query trades by date range.

        GIVEN: JSONL files for multiple dates (Jan 9, 10, 11)
        WHEN: query_by_date_range(start="2025-01-09", end="2025-01-10")
        THEN: Returns only trades from Jan 9-10 (excludes Jan 11)

        Expected to FAIL: TradeQueryHelper not implemented yet
        """
        # GIVEN: Create trades for 3 different days
        base_time_jan9 = datetime(2025, 1, 9, 10, 0, 0, tzinfo=timezone.utc)
        base_time_jan10 = datetime(2025, 1, 10, 10, 0, 0, tzinfo=timezone.utc)
        base_time_jan11 = datetime(2025, 1, 11, 10, 0, 0, tzinfo=timezone.utc)

        # Create trades for each day
        jan9_trade = self._create_trade_with_timestamp(sample_buy_trade(), base_time_jan9)
        jan10_trade = self._create_trade_with_timestamp(sample_sell_trade(), base_time_jan10)
        jan11_trade = self._create_trade_with_timestamp(sample_loss_trade(), base_time_jan11)

        # Write to separate daily files
        self._write_trades_to_file([jan9_trade], "2025-01-09.jsonl")
        self._write_trades_to_file([jan10_trade], "2025-01-10.jsonl")
        self._write_trades_to_file([jan11_trade], "2025-01-11.jsonl")

        # WHEN: Query for Jan 9-10 range
        query_helper = TradeQueryHelper(log_dir=self.logs_dir)
        results = query_helper.query_by_date_range(
            start_date="2025-01-09",
            end_date="2025-01-10"
        )

        # THEN: Should return only Jan 9-10 trades (2 trades)
        assert len(results) == 2, f"Expected 2 trades from Jan 9-10, got {len(results)}"

        # Verify dates are within range
        for trade in results:
            trade_date = datetime.fromisoformat(trade.timestamp).date()
            assert trade_date >= datetime(2025, 1, 9).date(), \
                f"Trade date {trade_date} before start date"
            assert trade_date <= datetime(2025, 1, 10).date(), \
                f"Trade date {trade_date} after end date"

        # Verify Jan 11 trade is excluded
        trade_dates = [datetime.fromisoformat(t.timestamp).date() for t in results]
        assert datetime(2025, 1, 11).date() not in trade_dates, \
            "Jan 11 trade should be excluded"

    def test_query_by_symbol(self) -> None:
        """T023 [RED]: TradeQueryHelper should filter trades by symbol.

        GIVEN: JSONL file with trades for AAPL, TSLA, MSFT
        WHEN: query_by_symbol(symbol="AAPL")
        THEN: Returns only AAPL trades

        Expected to FAIL: TradeQueryHelper not implemented yet
        """
        # GIVEN: Create multi-symbol trades
        trades = sample_multi_symbol_sequence()

        # Write all trades to single file
        self._write_trades_to_file(trades, "2025-01-09.jsonl")

        # WHEN: Query for AAPL only
        query_helper = TradeQueryHelper(log_dir=self.logs_dir)
        results = query_helper.query_by_symbol(symbol="AAPL")

        # THEN: Should return only AAPL trades
        assert len(results) > 0, "Expected at least 1 AAPL trade"

        for trade in results:
            assert trade.symbol == "AAPL", \
                f"Expected AAPL trades only, got {trade.symbol}"

        # Verify other symbols are excluded
        all_symbols = {trade.symbol for trade in results}
        assert all_symbols == {"AAPL"}, \
            f"Expected only AAPL, got symbols: {all_symbols}"

    def test_calculate_win_rate(self) -> None:
        """T024 [RED]: TradeQueryHelper should calculate win rate correctly.

        GIVEN: Trades with outcomes: 3 wins, 2 losses, 1 breakeven, 2 open
        WHEN: calculate_win_rate() called
        THEN: Returns 50% (3 wins / 6 closed trades)

        Expected to FAIL: TradeQueryHelper not implemented yet
        """
        # GIVEN: Create trades with specific outcomes
        trades = []

        # 3 winning trades
        for i in range(3):
            win_trade = sample_sell_trade()  # Already has outcome="win"
            trades.append(win_trade)

        # 2 losing trades
        for i in range(2):
            loss_trade = sample_loss_trade()  # Already has outcome="loss"
            trades.append(loss_trade)

        # 1 breakeven trade
        breakeven_trade = sample_breakeven_trade()  # Already has outcome="breakeven"
        trades.append(breakeven_trade)

        # 2 open trades (should be excluded from win rate calculation)
        for i in range(2):
            open_trade = sample_buy_trade()  # Has outcome="open"
            trades.append(open_trade)

        # Write all trades to file
        self._write_trades_to_file(trades, "2025-01-09.jsonl")

        # WHEN: Calculate win rate
        query_helper = TradeQueryHelper(log_dir=self.logs_dir)
        win_rate = query_helper.calculate_win_rate()

        # THEN: Win rate = 3 wins / 6 closed trades = 50%
        expected_win_rate = 50.0  # (3 / 6) * 100
        assert abs(win_rate - expected_win_rate) < 0.01, \
            f"Expected win rate {expected_win_rate}%, got {win_rate}%"

        # Verify calculation logic
        # Total closed trades = 3 wins + 2 losses + 1 breakeven = 6
        # Win rate = (3 / 6) * 100 = 50%

    def test_query_performance_at_scale(self) -> None:
        """T025 [RED]: TradeQueryHelper should query 1000 trades in <500ms.

        GIVEN: JSONL file with 1000 trades
        WHEN: query_by_symbol() executed
        THEN: Query completes in <500ms (NFR-005)

        Expected to FAIL: TradeQueryHelper not implemented yet
        """
        # GIVEN: Generate 1000 trades
        num_trades = 1000
        trades = []

        # Create 500 AAPL trades and 500 TSLA trades
        for i in range(num_trades // 2):
            aapl_trade = sample_buy_trade()  # AAPL trade
            tsla_trade = sample_loss_trade()  # TSLA trade
            trades.extend([aapl_trade, tsla_trade])

        # Write all trades to single file
        self._write_trades_to_file(trades, "2025-01-09.jsonl")

        # WHEN: Time the query execution
        query_helper = TradeQueryHelper(log_dir=self.logs_dir)

        start_time = time.perf_counter()
        results = query_helper.query_by_symbol(symbol="AAPL")
        end_time = time.perf_counter()

        # Calculate query time in milliseconds
        query_time_ms = (end_time - start_time) * 1000

        # THEN: Query should complete in <500ms (NFR-005)
        assert query_time_ms < 500.0, \
            f"Query time {query_time_ms:.2f}ms exceeds 500ms threshold (NFR-005)"

        # Verify correct results
        assert len(results) == num_trades // 2, \
            f"Expected {num_trades // 2} AAPL trades, got {len(results)}"

        for trade in results:
            assert trade.symbol == "AAPL", \
                f"Expected AAPL trades only, got {trade.symbol}"
