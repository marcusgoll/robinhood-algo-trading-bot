"""
Unit tests for Logging System

Tests Constitution v1.0.0 requirements:
- §Audit_Everything: Separate logs for trades, errors, and info
- §Data_Integrity: UTC timestamps on all logs
"""

import pytest
from pathlib import Path
import logging
import tempfile
import shutil
from datetime import datetime, timezone

from src.trading_bot.logger import (
    TradingLogger,
    UTCFormatter,
    setup_logging,
    get_logger,
    log_trade,
    log_error
)


class TestUTCFormatter:
    """Test UTC timestamp formatter."""

    def test_utc_formatter_creates_utc_timestamps(self) -> None:
        """Formatter should create UTC timestamps (§Data_Integrity)."""
        formatter = UTCFormatter("%(asctime)s", "%Y-%m-%d %H:%M:%S %Z")

        # Create a log record
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )

        # Format the time
        formatted_time = formatter.formatTime(record)

        # Should contain UTC indicator
        assert "UTC" in formatted_time or "+" in formatted_time

    def test_utc_formatter_with_custom_format(self) -> None:
        """Formatter should support custom date formats."""
        formatter = UTCFormatter("%(asctime)s", "%Y-%m-%d")

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None
        )

        formatted_time = formatter.formatTime(record)

        # Should match YYYY-MM-DD format
        assert len(formatted_time) == 10
        assert formatted_time.count("-") == 2


class TestTradingLogger:
    """Test TradingLogger functionality."""

    def setup_method(self) -> None:
        """Create temporary log directory for each test."""
        self.temp_dir = Path(tempfile.mkdtemp())
        TradingLogger._initialized = False  # Reset initialization

    def teardown_method(self) -> None:
        """Clean up temporary log directory after each test."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_setup_creates_logs_directory(self) -> None:
        """setup() should create logs directory."""
        logs_dir = self.temp_dir / "logs"
        TradingLogger.setup(logs_dir)

        assert logs_dir.exists()
        assert logs_dir.is_dir()

    def test_setup_creates_log_files(self) -> None:
        """setup() should initialize when logs are written."""
        logs_dir = self.temp_dir / "logs"
        TradingLogger.setup(logs_dir)

        # Get loggers and log messages
        logger = TradingLogger.get_logger("test")
        logger.info("Test message")

        trades_logger = TradingLogger.get_trades_logger()
        trades_logger.info("Trade message")

        errors_logger = TradingLogger.get_errors_logger()
        errors_logger.error("Error message")

        # Log files should be created
        assert (logs_dir / "trading_bot.log").exists()
        assert (logs_dir / "trades.log").exists()
        assert (logs_dir / "errors.log").exists()

    def test_setup_is_idempotent(self) -> None:
        """setup() should be safe to call multiple times."""
        logs_dir = self.temp_dir / "logs"

        TradingLogger.setup(logs_dir)
        TradingLogger.setup(logs_dir)  # Should not raise
        TradingLogger.setup(logs_dir)  # Should not raise

        assert logs_dir.exists()

    def test_get_logger_returns_configured_logger(self) -> None:
        """get_logger() should return a properly configured logger."""
        logs_dir = self.temp_dir / "logs"
        TradingLogger.setup(logs_dir)

        logger = TradingLogger.get_logger("test_module")

        assert logger is not None
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_module"

    def test_get_logger_auto_initializes(self) -> None:
        """get_logger() should auto-initialize if not setup."""
        logger = TradingLogger.get_logger("test")

        assert logger is not None
        assert TradingLogger._initialized is True

    def test_get_trades_logger_returns_specialized_logger(self) -> None:
        """get_trades_logger() should return trades logger."""
        logs_dir = self.temp_dir / "logs"
        TradingLogger.setup(logs_dir)

        trades_logger = TradingLogger.get_trades_logger()

        assert trades_logger is not None
        assert trades_logger.name == "trading_bot.trades"

    def test_get_errors_logger_returns_specialized_logger(self) -> None:
        """get_errors_logger() should return errors logger."""
        logs_dir = self.temp_dir / "logs"
        TradingLogger.setup(logs_dir)

        errors_logger = TradingLogger.get_errors_logger()

        assert errors_logger is not None
        assert errors_logger.name == "trading_bot.errors"

    def test_trades_logger_writes_to_trades_log(self) -> None:
        """Trades logger should write to trades.log (§Audit_Everything)."""
        logs_dir = self.temp_dir / "logs"
        TradingLogger.setup(logs_dir)

        trades_logger = TradingLogger.get_trades_logger()
        trades_logger.info("BUY 100 AAPL @ 150.00 [PAPER]")

        trades_log = logs_dir / "trades.log"
        assert trades_log.exists()

        content = trades_log.read_text()
        assert "BUY 100 AAPL @ 150.00 [PAPER]" in content

    def test_errors_logger_writes_to_errors_log(self) -> None:
        """Errors logger should write to errors.log."""
        logs_dir = self.temp_dir / "logs"
        TradingLogger.setup(logs_dir)

        errors_logger = TradingLogger.get_errors_logger()
        errors_logger.error("Test error message")

        errors_log = logs_dir / "errors.log"
        assert errors_log.exists()

        content = errors_log.read_text()
        assert "Test error message" in content

    def test_main_logger_writes_to_main_log(self) -> None:
        """Main logger should write to trading_bot.log."""
        logs_dir = self.temp_dir / "logs"
        TradingLogger.setup(logs_dir)

        logger = TradingLogger.get_logger("test")
        logger.info("Test info message")

        main_log = logs_dir / "trading_bot.log"
        assert main_log.exists()

        content = main_log.read_text()
        assert "Test info message" in content

    def test_logs_include_utc_timestamps(self) -> None:
        """All logs should include UTC timestamps (§Data_Integrity)."""
        logs_dir = self.temp_dir / "logs"
        TradingLogger.setup(logs_dir)

        logger = TradingLogger.get_logger("test")
        logger.info("Test message")

        main_log = logs_dir / "trading_bot.log"
        content = main_log.read_text()

        # Should contain UTC indicator
        assert "UTC" in content

    def test_log_format_includes_required_fields(self) -> None:
        """Log format should include timestamp, level, name, and message."""
        logs_dir = self.temp_dir / "logs"
        TradingLogger.setup(logs_dir)

        logger = TradingLogger.get_logger("test_module")
        logger.warning("Test warning")

        main_log = logs_dir / "trading_bot.log"
        content = main_log.read_text()

        assert "WARNING" in content
        assert "test_module" in content
        assert "Test warning" in content


class TestConvenienceFunctions:
    """Test convenience functions."""

    def setup_method(self) -> None:
        """Create temporary log directory for each test."""
        self.temp_dir = Path(tempfile.mkdtemp())
        TradingLogger._initialized = False

    def teardown_method(self) -> None:
        """Clean up temporary log directory after each test."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_setup_logging_function(self) -> None:
        """setup_logging() should initialize logging system."""
        logs_dir = self.temp_dir / "logs"
        setup_logging(logs_dir)

        assert TradingLogger._initialized is True
        assert logs_dir.exists()

    def test_get_logger_function(self) -> None:
        """get_logger() function should return configured logger."""
        logs_dir = self.temp_dir / "logs"
        setup_logging(logs_dir)

        logger = get_logger("test_module")

        assert logger is not None
        assert logger.name == "test_module"

    def test_log_trade_function(self) -> None:
        """log_trade() should log trade to trades.log (§Audit_Everything)."""
        logs_dir = self.temp_dir / "logs"
        setup_logging(logs_dir)

        log_trade(
            action="BUY",
            symbol="AAPL",
            quantity=100,
            price=150.50,
            mode="PAPER"
        )

        trades_log = logs_dir / "trades.log"
        assert trades_log.exists()

        content = trades_log.read_text()
        assert "BUY" in content
        assert "AAPL" in content
        assert "100" in content
        assert "150.50" in content
        assert "PAPER" in content

    def test_log_trade_with_extra_details(self) -> None:
        """log_trade() should support additional trade details."""
        logs_dir = self.temp_dir / "logs"
        setup_logging(logs_dir)

        log_trade(
            action="SELL",
            symbol="TSLA",
            quantity=50,
            price=200.00,
            mode="LIVE",
            profit=500.00,
            reason="Target hit"
        )

        trades_log = logs_dir / "trades.log"
        content = trades_log.read_text()

        assert "SELL" in content
        assert "TSLA" in content
        assert "profit=500.0" in content
        assert "reason=Target hit" in content

    def test_log_error_function(self) -> None:
        """log_error() should log error with traceback."""
        logs_dir = self.temp_dir / "logs"
        setup_logging(logs_dir)

        try:
            raise ValueError("Test error")
        except ValueError as e:
            log_error(e, "During order placement")

        errors_log = logs_dir / "errors.log"
        assert errors_log.exists()

        content = errors_log.read_text()
        assert "ValueError" in content
        assert "Test error" in content
        assert "During order placement" in content

    def test_log_error_without_context(self) -> None:
        """log_error() should work without context."""
        logs_dir = self.temp_dir / "logs"
        setup_logging(logs_dir)

        try:
            raise RuntimeError("Test runtime error")
        except RuntimeError as e:
            log_error(e)

        errors_log = logs_dir / "errors.log"
        content = errors_log.read_text()

        assert "RuntimeError" in content
        assert "Test runtime error" in content
