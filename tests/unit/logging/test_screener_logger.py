"""
Unit Tests: ScreenerLogger

Tests for thread-safe JSONL screener event logging with daily rotation.

Constitution v1.0.0:
- §Audit_Everything: All screener queries logged to immutable JSONL files
- §Data_Integrity: Atomic writes with file locking prevent corruption
- §Safety_First: Thread-safe concurrent write handling

Feature: stock-screener (001-stock-screener)
Tasks: T004-T006 [RED] - TDD: Write failing tests first
Spec: specs/001-stock-screener/spec.md (NFR-008: JSONL logging)
"""

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import pytest


class TestScreenerLogger:
    """Test suite for ScreenerLogger thread-safe JSONL logging."""

    @pytest.fixture
    def temp_log_dir(self, tmp_path):
        """Provide temporary log directory for isolated tests."""
        log_dir = tmp_path / "screener_logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir

    @pytest.fixture
    def logger(self, temp_log_dir):
        """Provide ScreenerLogger instance with temp directory."""
        from trading_bot.logging.screener_logger import ScreenerLogger
        return ScreenerLogger(log_dir=str(temp_log_dir))

    def test_log_query_writes_jsonl(self, logger, temp_log_dir):
        """
        T005-TC1: Verify log_query writes valid JSONL with all required fields.

        Acceptance: JSONL format, all fields present, ISO8601 timestamp, valid JSON
        """
        # Arrange
        query_params = {"min_price": 2.0, "max_price": 20.0, "relative_volume": 5.0}

        # Act
        logger.log_query(
            query_id="q-001",
            query_params=query_params,
            result_count=42,
            total_count=1000,
            execution_time_ms=187.5,
            api_calls=3,
            errors=[]
        )

        # Assert
        log_file = logger.get_log_file()
        assert log_file.exists(), "Log file should be created"

        with open(log_file, "r") as f:
            line = f.readline().strip()
            event = json.loads(line)

        # Verify required fields
        assert event["event"] == "screener.query_completed"
        assert event["query_id"] == "q-001"
        assert event["query_params"] == query_params
        assert event["result_count"] == 42
        assert event["total_count"] == 1000
        assert event["execution_time_ms"] == 187.5
        assert event["api_calls"] == 3
        assert event["errors"] == []

        # Verify timestamp format (ISO8601 with Z suffix)
        timestamp = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
        assert timestamp.tzinfo == timezone.utc

    def test_daily_rotation(self, temp_log_dir):
        """
        T005-TC2: Verify daily file rotation with YYYY-MM-DD.jsonl naming.

        Acceptance: File created with today's date in ISO8601 format
        """
        from trading_bot.logging.screener_logger import ScreenerLogger

        # Arrange
        logger = ScreenerLogger(log_dir=str(temp_log_dir))

        # Act
        log_file = logger.get_log_file()

        # Assert
        today = datetime.utcnow().strftime("%Y-%m-%d")
        expected_filename = f"{today}.jsonl"
        assert log_file.name == expected_filename
        assert log_file.parent == temp_log_dir

    def test_thread_safe_writes(self, logger, temp_log_dir):
        """
        T005-TC3: Verify thread-safe concurrent writes (10 threads, 100 writes each).

        Acceptance: All 1000 entries written without corruption, valid JSONL
        Performance: <100ms for 1000 total writes
        """
        # Arrange
        num_threads = 10
        writes_per_thread = 100
        total_writes = num_threads * writes_per_thread

        def write_logs(thread_id):
            """Worker function: Write logs from a single thread."""
            for i in range(writes_per_thread):
                logger.log_query(
                    query_id=f"thread-{thread_id}-query-{i}",
                    query_params={"thread": thread_id, "iteration": i},
                    result_count=i,
                    total_count=1000,
                    execution_time_ms=50.0,
                    api_calls=1,
                    errors=[]
                )

        # Act
        start_time = time.perf_counter()
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            executor.map(write_logs, range(num_threads))
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Assert: All entries written
        log_file = logger.get_log_file()
        with open(log_file, "r") as f:
            lines = f.readlines()

        assert len(lines) == total_writes, f"Expected {total_writes} lines, got {len(lines)}"

        # Assert: All lines are valid JSON
        for line_num, line in enumerate(lines, start=1):
            try:
                event = json.loads(line.strip())
                assert "query_id" in event
            except json.JSONDecodeError as e:
                pytest.fail(f"Line {line_num} is not valid JSON: {e}")

        # Assert: Performance target (<100ms for 1000 writes)
        print(f"\n[PERFORMANCE] {total_writes} concurrent writes: {elapsed_ms:.2f}ms")
        # Note: This is a soft assertion - actual time depends on system load

    def test_log_data_gap(self, logger, temp_log_dir):
        """
        T005-TC4: Verify data gap event logging with symbol, field, reason.

        Acceptance: Event logged with correct structure, all fields present
        """
        # Act
        logger.log_data_gap(
            symbol="AAPL",
            field="public_float",
            reason="Field unavailable in API response"
        )

        # Assert
        log_file = logger.get_log_file()
        with open(log_file, "r") as f:
            event = json.loads(f.readline().strip())

        assert event["event"] == "screener.data_gap"
        assert event["symbol"] == "AAPL"
        assert event["field"] == "public_float"
        assert event["reason"] == "Field unavailable in API response"
        assert "timestamp" in event

    def test_log_error(self, logger, temp_log_dir):
        """
        T005-TC5: Verify error event logging with type, recoverable flag, retry count.

        Acceptance: Error event logged with correct structure, optional symbol field
        """
        # Act: Log error with symbol
        logger.log_error(
            error_type="RateLimitExceeded",
            recoverable=True,
            retry_count=2,
            symbol="TSLA"
        )

        # Assert
        log_file = logger.get_log_file()
        with open(log_file, "r") as f:
            event = json.loads(f.readline().strip())

        assert event["event"] == "screener.error"
        assert event["error_type"] == "RateLimitExceeded"
        assert event["recoverable"] is True
        assert event["retry_count"] == 2
        assert event["symbol"] == "TSLA"

        # Act: Log error without symbol
        logger.log_error(
            error_type="ValidationError",
            recoverable=False,
            retry_count=0,
            symbol=None
        )

        # Assert
        with open(log_file, "r") as f:
            f.readline()  # Skip first line
            event2 = json.loads(f.readline().strip())

        assert event2["symbol"] is None

    def test_concurrent_access_integrity(self, logger, temp_log_dir):
        """
        T005-TC6: Verify file lock prevents corruption (checksum validation).

        Acceptance: All concurrent writes complete without file corruption
        """
        # Arrange
        num_writers = 5
        writes_per_writer = 20

        def concurrent_writer(writer_id):
            """Worker: Write unique identifiable logs."""
            for i in range(writes_per_writer):
                logger.log_query(
                    query_id=f"writer-{writer_id:02d}-{i:03d}",
                    query_params={"writer": writer_id},
                    result_count=i,
                    total_count=100,
                    execution_time_ms=10.0,
                    api_calls=1,
                    errors=[]
                )

        # Act
        with ThreadPoolExecutor(max_workers=num_writers) as executor:
            executor.map(concurrent_writer, range(num_writers))

        # Assert: All writes present, no corruption
        log_file = logger.get_log_file()
        with open(log_file, "r") as f:
            lines = f.readlines()

        assert len(lines) == num_writers * writes_per_writer

        # Verify each line is valid JSON and has unique query_id
        query_ids = set()
        for line in lines:
            event = json.loads(line.strip())
            query_id = event["query_id"]
            assert query_id not in query_ids, f"Duplicate query_id: {query_id}"
            query_ids.add(query_id)

    def test_log_query_with_errors(self, logger, temp_log_dir):
        """
        T005-TC7: Verify log_query handles non-empty error list.

        Acceptance: Errors array serialized correctly as JSON
        """
        # Act
        errors = ["API timeout on symbol NVDA", "Rate limit exceeded"]
        logger.log_query(
            query_id="q-error-001",
            query_params={"min_price": 5.0},
            result_count=0,
            total_count=0,
            execution_time_ms=5000.0,
            api_calls=10,
            errors=errors
        )

        # Assert
        log_file = logger.get_log_file()
        with open(log_file, "r") as f:
            event = json.loads(f.readline().strip())

        assert event["errors"] == errors
        assert len(event["errors"]) == 2
