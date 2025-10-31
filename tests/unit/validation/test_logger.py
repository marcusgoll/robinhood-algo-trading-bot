"""Unit tests for TimeframeValidationLogger.

Tests JSONL logging with daily file rotation for validation events.
"""

import pytest
import json
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from unittest.mock import patch, MagicMock
from src.trading_bot.validation.logger import TimeframeValidationLogger
from src.trading_bot.validation.models import (
    TimeframeValidationResult,
    ValidationStatus,
    TimeframeIndicators
)


class TestTimeframeValidationLogger:
    """Test JSONL logging functionality."""

    @pytest.fixture
    def temp_log_dir(self, tmp_path):
        """Create temporary log directory."""
        log_dir = tmp_path / "timeframe-validation"
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir

    @pytest.fixture
    def logger(self, temp_log_dir):
        """Create logger with temporary directory."""
        return TimeframeValidationLogger(log_dir=temp_log_dir)

    @pytest.fixture
    def sample_result(self):
        """Create sample validation result for testing."""
        daily_indicators = TimeframeIndicators(
            timeframe="DAILY",
            price=Decimal("150.00"),
            ema_20=Decimal("145.00"),
            macd_line=Decimal("2.50"),
            macd_positive=True,
            price_above_ema=True,
            bar_count=60,
            timestamp=datetime.now()
        )

        return TimeframeValidationResult(
            status=ValidationStatus.PASS,
            aggregate_score=Decimal("1.0"),
            daily_score=Decimal("1.0"),
            h4_score=None,
            daily_indicators=daily_indicators,
            h4_indicators=None,
            reasons=[],
            timestamp=datetime.now(),
            symbol="AAPL"
        )

    def test_logger_writes_to_daily_file(self, logger, sample_result, temp_log_dir):
        """
        T020: Call logger.log_validation_event(result) → verify file created
        at logs/timeframe-validation/YYYY-MM-DD.jsonl

        Given: TimeframeValidationLogger with temp directory
        When: Log validation event
        Then: Daily JSONL file created with correct naming
        """
        # Mock datetime to fixed date
        fixed_date = datetime(2024, 10, 28, 12, 0, 0)
        with patch('src.trading_bot.validation.logger.datetime') as mock_datetime:
            mock_datetime.now.return_value = fixed_date
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            # Log event
            logger.log_validation_event(sample_result)

            # Verify file created with correct name
            expected_file = temp_log_dir / "2024-10-28.jsonl"
            assert expected_file.exists()

            # Verify file contains JSON line
            with open(expected_file, 'r') as f:
                lines = f.readlines()
                assert len(lines) == 1
                
                # Parse JSON and verify structure
                event = json.loads(lines[0])
                assert event["event"] == "timeframe_validation"
                assert event["symbol"] == "AAPL"
                assert "timestamp" in event

    def test_logger_includes_all_indicator_values(self, logger, sample_result, temp_log_dir):
        """
        T021: Log event → verify JSON contains daily_macd, daily_ema_20,
        price_vs_ema, reasons

        Given: Sample validation result with indicators
        When: Log event
        Then: JSON contains all required indicator fields
        """
        # Log event
        logger.log_validation_event(sample_result)

        # Read log file
        log_files = list(temp_log_dir.glob("*.jsonl"))
        assert len(log_files) == 1

        with open(log_files[0], 'r') as f:
            event = json.loads(f.readline())

            # Verify all indicator values present
            assert "daily_macd" in event
            assert event["daily_macd"] == "2.50"  # Decimal serialized as string
            
            assert "daily_ema_20" in event
            assert event["daily_ema_20"] == "145.00"
            
            assert "daily_price_vs_ema" in event
            assert event["daily_price_vs_ema"] is True
            
            assert "reasons" in event
            assert isinstance(event["reasons"], list)
            
            assert "decision" in event
            assert event["decision"] == "PASS"
            
            assert "aggregate_score" in event
            assert event["aggregate_score"] == "1.0"

    def test_degraded_mode_logs_high_severity(self, logger, temp_log_dir):
        """
        T031: Log DEGRADED result → verify event contains severity="HIGH",
        degraded_mode=true

        Given: Validation result with DEGRADED status
        When: Log event
        Then: JSON contains severity=HIGH and degraded_mode=true
        """
        # Create degraded result
        degraded_result = TimeframeValidationResult(
            status=ValidationStatus.DEGRADED,
            aggregate_score=Decimal("0.0"),
            daily_score=Decimal("0.0"),
            h4_score=None,
            daily_indicators=None,
            h4_indicators=None,
            reasons=["Daily data unavailable after 3 retries"],
            timestamp=datetime.now(),
            symbol="AAPL"
        )

        # Log event
        logger.log_validation_event(degraded_result)

        # Read and verify
        log_files = list(temp_log_dir.glob("*.jsonl"))
        with open(log_files[0], 'r') as f:
            event = json.loads(f.readline())

            assert event["severity"] == "HIGH"
            assert event["degraded_mode"] is True
            assert event["decision"] == "DEGRADED"
            assert "Daily data unavailable" in event["reasons"][0]

    def test_logger_appends_to_existing_file(self, logger, sample_result, temp_log_dir):
        """
        Verify multiple log calls append to same daily file.

        Given: Logger with existing file
        When: Log multiple events
        Then: All events appended to single file
        """
        # Log 3 events
        logger.log_validation_event(sample_result)
        logger.log_validation_event(sample_result)
        logger.log_validation_event(sample_result)

        # Verify single file with 3 lines
        log_files = list(temp_log_dir.glob("*.jsonl"))
        assert len(log_files) == 1

        with open(log_files[0], 'r') as f:
            lines = f.readlines()
            assert len(lines) == 3

            # All lines are valid JSON
            for line in lines:
                event = json.loads(line)
                assert event["event"] == "timeframe_validation"
