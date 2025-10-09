"""
Unit tests for StructuredTradeLogger (TDD RED Phase)

Tests Constitution v1.0.0 requirements:
- §Audit_Everything: JSONL-based trade logging
- §Data_Integrity: Atomic writes, no data corruption
- NFR-003: <5ms write latency per log_trade() call

Feature: trade-logging
Tasks: T014-T017 [RED] - Write failing tests (StructuredTradeLogger not implemented yet)
"""

import pytest
from pathlib import Path
import tempfile
import shutil
import time
import threading
import json
from datetime import datetime

# This import will FAIL - StructuredTradeLogger doesn't exist yet (RED phase)
from src.trading_bot.logging.structured_logger import StructuredTradeLogger

from tests.fixtures.trade_fixtures import sample_buy_trade


class TestStructuredTradeLogger:
    """Test StructuredTradeLogger functionality (TDD RED phase)."""

    def setup_method(self) -> None:
        """Create temporary log directory for each test."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.logs_dir = self.temp_dir / "logs" / "trades"

    def teardown_method(self) -> None:
        """Clean up temporary log directory after each test."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_logger_creates_daily_jsonl_file(self) -> None:
        """T014 [RED]: Logger should create daily JSONL file on first log_trade() call.

        GIVEN: StructuredTradeLogger instance pointing to logs/trades/
        WHEN: log_trade() called with sample_buy_trade
        THEN: File created at logs/trades/YYYY-MM-DD.jsonl

        Expected to FAIL: StructuredTradeLogger not implemented yet
        """
        # GIVEN: Logger instance
        logger = StructuredTradeLogger(log_dir=self.logs_dir)

        # WHEN: Log a trade
        trade = sample_buy_trade()
        logger.log_trade(trade)

        # THEN: Daily JSONL file should exist
        today = datetime.now().strftime("%Y-%m-%d")
        expected_file = self.logs_dir / f"{today}.jsonl"

        assert expected_file.exists(), f"Expected log file not found: {expected_file}"
        assert expected_file.is_file(), "Expected a file, not a directory"

    def test_logger_appends_to_existing_file(self) -> None:
        """T015 [RED]: Logger should append to existing file, not overwrite.

        GIVEN: StructuredTradeLogger instance
        WHEN: log_trade() called twice with different trades
        THEN: File contains 2 lines (one per trade)

        Expected to FAIL: StructuredTradeLogger not implemented yet
        """
        # GIVEN: Logger instance
        logger = StructuredTradeLogger(log_dir=self.logs_dir)

        # WHEN: Log two trades
        trade1 = sample_buy_trade()
        trade2 = sample_buy_trade()
        logger.log_trade(trade1)
        logger.log_trade(trade2)

        # THEN: File should contain 2 lines
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.logs_dir / f"{today}.jsonl"

        assert log_file.exists(), "Log file should exist"

        lines = log_file.read_text().strip().split('\n')
        assert len(lines) == 2, f"Expected 2 lines in log file, got {len(lines)}"

        # Verify both lines are valid JSON
        for i, line in enumerate(lines):
            try:
                data = json.loads(line)
                assert "symbol" in data, f"Line {i+1} missing 'symbol' field"
                assert "action" in data, f"Line {i+1} missing 'action' field"
            except json.JSONDecodeError as e:
                pytest.fail(f"Line {i+1} is not valid JSON: {e}")

    def test_logger_handles_concurrent_writes(self) -> None:
        """T016 [RED]: Logger should handle concurrent writes without corruption.

        GIVEN: StructuredTradeLogger instance
        WHEN: 10 threads write simultaneously
        THEN: All 10 records present in file, no data corruption

        Expected to FAIL: StructuredTradeLogger not implemented yet
        """
        # GIVEN: Logger instance
        logger = StructuredTradeLogger(log_dir=self.logs_dir)

        # WHEN: 10 threads write concurrently
        num_threads = 10
        threads = []

        def write_trade():
            """Thread worker function."""
            trade = sample_buy_trade()
            logger.log_trade(trade)

        for _ in range(num_threads):
            thread = threading.Thread(target=write_trade)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # THEN: All 10 records should be present
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.logs_dir / f"{today}.jsonl"

        assert log_file.exists(), "Log file should exist"

        lines = log_file.read_text().strip().split('\n')
        assert len(lines) == num_threads, f"Expected {num_threads} lines, got {len(lines)}"

        # Verify all lines are valid JSON (no corruption)
        for i, line in enumerate(lines):
            try:
                data = json.loads(line)
                assert "symbol" in data, f"Line {i+1} corrupted: missing 'symbol' field"
            except json.JSONDecodeError as e:
                pytest.fail(f"Line {i+1} corrupted: {e}")

    def test_logger_write_performance(self) -> None:
        """T017 [RED]: Logger should complete log_trade() in <5ms average.

        GIVEN: StructuredTradeLogger instance
        WHEN: log_trade() called 100 times
        THEN: Average latency <5ms per call (NFR-003)

        Expected to FAIL: StructuredTradeLogger not implemented yet
        """
        # GIVEN: Logger instance
        logger = StructuredTradeLogger(log_dir=self.logs_dir)

        # WHEN: Time 100 log_trade() calls
        num_calls = 100
        trade = sample_buy_trade()

        start_time = time.perf_counter()
        for _ in range(num_calls):
            logger.log_trade(trade)
        end_time = time.perf_counter()

        # THEN: Average latency should be <5ms
        total_time = end_time - start_time
        average_latency = (total_time / num_calls) * 1000  # Convert to milliseconds

        # NFR-003: <5ms average write latency
        assert average_latency < 5.0, (
            f"Average latency {average_latency:.2f}ms exceeds 5ms threshold (NFR-003)"
        )

        # Verify all records were written
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.logs_dir / f"{today}.jsonl"

        assert log_file.exists(), "Log file should exist"
        lines = log_file.read_text().strip().split('\n')
        assert len(lines) == num_calls, f"Expected {num_calls} lines, got {len(lines)}"
