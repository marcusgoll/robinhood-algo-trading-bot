"""
Unit Tests: MomentumLogger

Tests for momentum signal logging functionality with JSONL format validation.

Task: T007 [GREEN] - Create MomentumLogger wrapper
Coverage Target: ≥90% per spec.md NFR-006
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from threading import Thread
from typing import Any

import pytest

from src.trading_bot.momentum.logging.momentum_logger import MomentumLogger


class TestMomentumLoggerInitialization:
    """Test suite for MomentumLogger initialization."""

    def test_creates_logger_with_default_directory(self, tmp_path: Path) -> None:
        """Logger initializes with default logs/momentum directory."""
        # Given: Default log directory
        log_dir = tmp_path / "logs" / "momentum"

        # When: Logger created with default directory
        logger = MomentumLogger(log_dir=log_dir)

        # Then: Logger instance created successfully
        assert logger is not None
        assert logger._base_logger is not None

    def test_creates_logger_with_custom_directory(self, tmp_path: Path) -> None:
        """Logger initializes with custom directory path."""
        # Given: Custom log directory
        custom_dir = tmp_path / "custom" / "momentum"

        # When: Logger created with custom directory
        logger = MomentumLogger(log_dir=custom_dir)

        # Then: Logger uses custom directory
        assert logger is not None
        assert logger._base_logger.log_dir == custom_dir


class TestLogSignal:
    """Test suite for log_signal() method."""

    def test_logs_catalyst_signal_with_required_fields(self, tmp_path: Path) -> None:
        """Signal with required fields logged successfully to JSONL."""
        # Given: Logger and catalyst signal
        log_dir = tmp_path / "logs"
        logger = MomentumLogger(log_dir=log_dir)

        signal = {
            "signal_type": "catalyst",
            "symbol": "AAPL",
            "strength": 85.5,
            "catalyst_type": "earnings"
        }

        # When: Signal logged
        logger.log_signal(signal)

        # Then: JSONL file created with correct content
        log_file = log_dir / f"{datetime.now(UTC).strftime('%Y-%m-%d')}.jsonl"
        assert log_file.exists()

        # Verify JSONL format (one line, valid JSON)
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            assert len(lines) == 1  # Exactly one log entry

            # Parse JSON to verify structure
            log_entry = json.loads(lines[0])
            assert log_entry["event_type"] == "signal_detected"
            assert log_entry["signal_type"] == "catalyst"
            assert log_entry["symbol"] == "AAPL"
            assert log_entry["strength"] == 85.5
            assert "timestamp" in log_entry  # UTC timestamp added

    def test_logs_premarket_signal_with_metadata(self, tmp_path: Path) -> None:
        """Pre-market signal with metadata merged into log entry."""
        # Given: Logger, pre-market signal, and metadata
        logger = MomentumLogger(log_dir=tmp_path)

        signal = {
            "signal_type": "premarket_mover",
            "symbol": "GOOGL",
            "strength": 75.0,
            "price_change_pct": 5.2,
            "volume_ratio": 2.5
        }

        metadata = {
            "scan_id": "abc123",
            "detector_version": "1.0.0"
        }

        # When: Signal logged with metadata
        logger.log_signal(signal, metadata)

        # Then: Metadata merged into log entry
        log_file = tmp_path / f"{datetime.now(UTC).strftime('%Y-%m-%d')}.jsonl"
        with open(log_file, 'r', encoding='utf-8') as f:
            log_entry = json.loads(f.readline())
            assert log_entry["scan_id"] == "abc123"
            assert log_entry["detector_version"] == "1.0.0"

    def test_logs_bull_flag_signal_without_metadata(self, tmp_path: Path) -> None:
        """Bull flag signal logged without optional metadata."""
        # Given: Logger and bull flag signal
        logger = MomentumLogger(log_dir=tmp_path)

        signal = {
            "signal_type": "bull_flag",
            "symbol": "TSLA",
            "strength": 90.0,
            "breakout_price": 250.00,
            "price_target": 290.00
        }

        # When: Signal logged without metadata
        logger.log_signal(signal)

        # Then: Log entry created with signal data only
        log_file = tmp_path / f"{datetime.now(UTC).strftime('%Y-%m-%d')}.jsonl"
        with open(log_file, 'r', encoding='utf-8') as f:
            log_entry = json.loads(f.readline())
            assert log_entry["signal_type"] == "bull_flag"
            assert log_entry["breakout_price"] == 250.00

    def test_includes_utc_timestamp_in_iso_format(self, tmp_path: Path) -> None:
        """Timestamp added in ISO 8601 UTC format."""
        # Given: Logger and signal
        logger = MomentumLogger(log_dir=tmp_path)
        signal = {"signal_type": "catalyst", "symbol": "AAPL", "strength": 80.0}

        # When: Signal logged
        logger.log_signal(signal)

        # Then: Timestamp in ISO 8601 format with 'Z' suffix
        log_file = tmp_path / f"{datetime.now(UTC).strftime('%Y-%m-%d')}.jsonl"
        with open(log_file, 'r', encoding='utf-8') as f:
            log_entry = json.loads(f.readline())
            timestamp = log_entry["timestamp"]

            # Verify ISO 8601 format (can parse as datetime)
            parsed_ts = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            assert parsed_ts.tzinfo is not None  # Timezone aware

    def test_graceful_degradation_on_write_error(self, tmp_path: Path, monkeypatch, capsys) -> None:
        """Logger continues on write error, logs to stderr."""
        # Given: Logger with mocked base logger that raises error
        logger = MomentumLogger(log_dir=tmp_path)
        signal = {"signal_type": "catalyst", "symbol": "AAPL", "strength": 80.0}

        # Mock base logger to raise error
        def mock_log_trade(entry):
            raise OSError("Simulated disk full error")

        monkeypatch.setattr(logger._base_logger, "log_trade", mock_log_trade)

        # When: Attempting to log signal
        logger.log_signal(signal)

        # Then: Error logged to stderr, no exception raised
        captured = capsys.readouterr()
        assert "ERROR: Failed to log momentum signal" in captured.err


class TestLogScanEvent:
    """Test suite for log_scan_event() method."""

    def test_logs_scan_started_event(self, tmp_path: Path) -> None:
        """Scan started event logged with metadata."""
        # Given: Logger and scan start metadata
        logger = MomentumLogger(log_dir=tmp_path)

        metadata = {
            "scan_id": "scan123",
            "symbols": ["AAPL", "GOOGL"],
            "scan_types": ["catalyst", "premarket"]
        }

        # When: Scan started event logged
        logger.log_scan_event("scan_started", metadata)

        # Then: Event logged with correct structure
        log_file = tmp_path / f"{datetime.now(UTC).strftime('%Y-%m-%d')}.jsonl"
        with open(log_file, 'r', encoding='utf-8') as f:
            log_entry = json.loads(f.readline())
            assert log_entry["event_type"] == "scan_started"
            assert log_entry["metadata"]["scan_id"] == "scan123"
            assert log_entry["metadata"]["symbols"] == ["AAPL", "GOOGL"]

    def test_logs_scan_completed_event(self, tmp_path: Path) -> None:
        """Scan completed event logged with results."""
        # Given: Logger and scan completion metadata
        logger = MomentumLogger(log_dir=tmp_path)

        metadata = {
            "scan_id": "scan123",
            "signals_found": 5,
            "duration_ms": 245,
            "errors": 0
        }

        # When: Scan completed event logged
        logger.log_scan_event("scan_completed", metadata)

        # Then: Event logged with results
        log_file = tmp_path / f"{datetime.now(UTC).strftime('%Y-%m-%d')}.jsonl"
        with open(log_file, 'r', encoding='utf-8') as f:
            log_entry = json.loads(f.readline())
            assert log_entry["event_type"] == "scan_completed"
            assert log_entry["metadata"]["signals_found"] == 5

    def test_logs_detector_finished_event(self, tmp_path: Path) -> None:
        """Detector finished event logged for individual detector."""
        # Given: Logger and detector completion metadata
        logger = MomentumLogger(log_dir=tmp_path)

        metadata = {
            "detector": "CatalystDetector",
            "signals_found": 2,
            "execution_time_ms": 120
        }

        # When: Detector finished event logged
        logger.log_scan_event("detector_finished", metadata)

        # Then: Event logged with detector info
        log_file = tmp_path / f"{datetime.now(UTC).strftime('%Y-%m-%d')}.jsonl"
        with open(log_file, 'r', encoding='utf-8') as f:
            log_entry = json.loads(f.readline())
            assert log_entry["event_type"] == "detector_finished"
            assert log_entry["metadata"]["detector"] == "CatalystDetector"

    def test_graceful_degradation_on_write_error(self, tmp_path: Path, monkeypatch, capsys) -> None:
        """Logger continues on scan event write error."""
        # Given: Logger with mocked base logger that raises error
        logger = MomentumLogger(log_dir=tmp_path)

        # Mock base logger to raise error
        def mock_log_trade(entry):
            raise OSError("Simulated disk full error")

        monkeypatch.setattr(logger._base_logger, "log_trade", mock_log_trade)

        # When: Attempting to log scan event
        logger.log_scan_event("scan_started", {"scan_id": "123"})

        # Then: Error logged to stderr, no exception raised
        captured = capsys.readouterr()
        assert "ERROR: Failed to log scan event" in captured.err


class TestLogError:
    """Test suite for log_error() method."""

    def test_logs_api_error_with_context(self, tmp_path: Path) -> None:
        """API error logged with full context."""
        # Given: Logger and exception
        logger = MomentumLogger(log_dir=tmp_path)

        error = ConnectionError("News API timeout")
        context = {
            "detector": "CatalystDetector",
            "symbol": "AAPL",
            "retry_attempt": 3
        }

        # When: Error logged
        logger.log_error(error, context)

        # Then: Error logged with type, message, and context
        log_file = tmp_path / f"{datetime.now(UTC).strftime('%Y-%m-%d')}.jsonl"
        with open(log_file, 'r', encoding='utf-8') as f:
            log_entry = json.loads(f.readline())
            assert log_entry["event_type"] == "error"
            assert log_entry["error_type"] == "ConnectionError"
            assert log_entry["message"] == "News API timeout"
            assert log_entry["context"]["detector"] == "CatalystDetector"

    def test_logs_value_error_with_symbol_context(self, tmp_path: Path) -> None:
        """ValueError logged with symbol context."""
        # Given: Logger and validation error
        logger = MomentumLogger(log_dir=tmp_path)

        error = ValueError("Invalid symbol format")
        context = {"symbol": "INVALID!", "validator": "PreMarketScanner"}

        # When: Error logged
        logger.log_error(error, context)

        # Then: Error logged with validation context
        log_file = tmp_path / f"{datetime.now(UTC).strftime('%Y-%m-%d')}.jsonl"
        with open(log_file, 'r', encoding='utf-8') as f:
            log_entry = json.loads(f.readline())
            assert log_entry["error_type"] == "ValueError"
            assert log_entry["context"]["symbol"] == "INVALID!"

    def test_graceful_degradation_on_write_error(self, tmp_path: Path, monkeypatch, capsys) -> None:
        """Logger continues on error logging failure."""
        # Given: Logger with mocked base logger that raises error
        logger = MomentumLogger(log_dir=tmp_path)
        error = RuntimeError("Test error")

        # Mock base logger to raise error
        def mock_log_trade(entry):
            raise OSError("Simulated disk full error")

        monkeypatch.setattr(logger._base_logger, "log_trade", mock_log_trade)

        # When: Attempting to log error
        logger.log_error(error, {"test": "context"})

        # Then: Error logged to stderr, no exception raised
        captured = capsys.readouterr()
        assert "ERROR: Failed to log error event" in captured.err


class TestFormatSignalForLog:
    """Test suite for _format_signal_for_log() helper method."""

    def test_adds_timestamp_and_event_type(self, tmp_path: Path) -> None:
        """Helper adds timestamp and event_type to signal."""
        # Given: Logger and signal
        logger = MomentumLogger(log_dir=tmp_path)
        signal = {"signal_type": "catalyst", "symbol": "AAPL", "strength": 80.0}

        # When: Formatting signal for log
        log_entry = logger._format_signal_for_log(signal, None)

        # Then: Timestamp and event_type added
        assert "timestamp" in log_entry
        assert log_entry["event_type"] == "signal_detected"

    def test_preserves_all_signal_fields(self, tmp_path: Path) -> None:
        """Helper preserves all original signal fields."""
        # Given: Logger and signal with multiple fields
        logger = MomentumLogger(log_dir=tmp_path)
        signal = {
            "signal_type": "bull_flag",
            "symbol": "TSLA",
            "strength": 90.0,
            "breakout_price": 250.00,
            "price_target": 290.00
        }

        # When: Formatting signal
        log_entry = logger._format_signal_for_log(signal, None)

        # Then: All signal fields present in log entry
        assert log_entry["signal_type"] == "bull_flag"
        assert log_entry["symbol"] == "TSLA"
        assert log_entry["strength"] == 90.0
        assert log_entry["breakout_price"] == 250.00
        assert log_entry["price_target"] == 290.00

    def test_merges_metadata_into_log_entry(self, tmp_path: Path) -> None:
        """Helper merges metadata dict into log entry."""
        # Given: Logger, signal, and metadata
        logger = MomentumLogger(log_dir=tmp_path)
        signal = {"signal_type": "catalyst", "symbol": "AAPL", "strength": 80.0}
        metadata = {"scan_id": "abc123", "detector_version": "1.0.0"}

        # When: Formatting signal with metadata
        log_entry = logger._format_signal_for_log(signal, metadata)

        # Then: Metadata fields added to log entry
        assert log_entry["scan_id"] == "abc123"
        assert log_entry["detector_version"] == "1.0.0"

    def test_handles_none_metadata_gracefully(self, tmp_path: Path) -> None:
        """Helper handles None metadata without error."""
        # Given: Logger and signal with None metadata
        logger = MomentumLogger(log_dir=tmp_path)
        signal = {"signal_type": "catalyst", "symbol": "AAPL", "strength": 80.0}

        # When: Formatting signal with None metadata
        log_entry = logger._format_signal_for_log(signal, None)

        # Then: Log entry created without metadata
        assert log_entry["signal_type"] == "catalyst"
        assert "timestamp" in log_entry


class TestThreadSafety:
    """Test suite for thread-safe logging behavior."""

    def test_concurrent_signal_logging_no_corruption(self, tmp_path: Path) -> None:
        """Multiple threads logging signals concurrently without corruption."""
        # Given: Logger and multiple signals
        logger = MomentumLogger(log_dir=tmp_path)

        signals = [
            {"signal_type": "catalyst", "symbol": "AAPL", "strength": 80.0},
            {"signal_type": "premarket_mover", "symbol": "GOOGL", "strength": 75.0},
            {"signal_type": "bull_flag", "symbol": "TSLA", "strength": 90.0},
            {"signal_type": "catalyst", "symbol": "MSFT", "strength": 85.0},
            {"signal_type": "premarket_mover", "symbol": "AMZN", "strength": 70.0}
        ]

        # When: Logging signals from multiple threads
        threads = []
        for signal in signals:
            thread = Thread(target=logger.log_signal, args=(signal,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Then: All signals logged without corruption
        log_file = tmp_path / f"{datetime.now(UTC).strftime('%Y-%m-%d')}.jsonl"
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            assert len(lines) == 5  # All 5 signals logged

            # Verify each line is valid JSON
            for line in lines:
                log_entry = json.loads(line)
                assert "signal_type" in log_entry
                assert "symbol" in log_entry


class TestJSONLFormat:
    """Test suite for JSONL format validation."""

    def test_log_file_is_valid_jsonl_format(self, tmp_path: Path) -> None:
        """Log file follows JSONL format (one JSON per line)."""
        # Given: Logger and multiple log entries
        logger = MomentumLogger(log_dir=tmp_path)

        logger.log_signal({"signal_type": "catalyst", "symbol": "AAPL", "strength": 80.0})
        logger.log_scan_event("scan_started", {"scan_id": "123"})
        logger.log_error(RuntimeError("Test error"), {"context": "test"})

        # Then: File is valid JSONL (each line parseable as JSON)
        log_file = tmp_path / f"{datetime.now(UTC).strftime('%Y-%m-%d')}.jsonl"
        with open(log_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, start=1):
                try:
                    log_entry = json.loads(line)
                    assert isinstance(log_entry, dict)
                except json.JSONDecodeError:
                    pytest.fail(f"Line {line_num} is not valid JSON: {line}")

    def test_log_entries_do_not_contain_newlines(self, tmp_path: Path) -> None:
        """Log entries serialized without internal newlines."""
        # Given: Logger and signal
        logger = MomentumLogger(log_dir=tmp_path)
        signal = {"signal_type": "catalyst", "symbol": "AAPL", "strength": 80.0}

        # When: Signal logged
        logger.log_signal(signal)

        # Then: Log file has exactly one line per entry (no internal newlines)
        log_file = tmp_path / f"{datetime.now(UTC).strftime('%Y-%m-%d')}.jsonl"
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
            # Should have 1 log entry + 1 trailing newline = 2 lines total
            assert len([line for line in lines if line]) == 1  # One non-empty line
