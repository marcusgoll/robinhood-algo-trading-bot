"""
Unit tests for ZoneLogger.

Tests thread-safe JSONL logging with daily file rotation for zone detection events.
"""

import json
import pytest
from datetime import datetime, UTC
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from src.trading_bot.support_resistance.zone_logger import ZoneLogger
from src.trading_bot.support_resistance.models import (
    Zone,
    ZoneType,
    Timeframe,
    ProximityAlert
)
from src.trading_bot.support_resistance.breakout_models import (
    BreakoutEvent,
    BreakoutStatus
)


class TestZoneLogger:
    """Test ZoneLogger JSONL logging and file rotation."""

    def test_logger_creates_log_directory(self):
        """Test ZoneLogger creates log directory if it doesn't exist."""
        with TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / "zones"
            assert not log_dir.exists()

            logger = ZoneLogger(log_dir=log_dir)

            assert log_dir.exists()
            assert log_dir.is_dir()

    def test_log_zone_detection_writes_valid_jsonl(self):
        """Test log_zone_detection writes valid JSONL to daily file."""
        with TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / "zones"
            logger = ZoneLogger(log_dir=log_dir)

            zones = [
                Zone(
                    price_level=Decimal("150.50"),
                    zone_type=ZoneType.SUPPORT,
                    strength_score=Decimal("5.0"),
                    touch_count=4,
                    first_touch_date=datetime(2025, 1, 1, tzinfo=UTC),
                    last_touch_date=datetime(2025, 1, 15, tzinfo=UTC),
                    average_volume=Decimal("1000000"),
                    highest_volume_touch=Decimal("1500000"),
                    timeframe=Timeframe.DAILY
                ),
                Zone(
                    price_level=Decimal("200.00"),
                    zone_type=ZoneType.RESISTANCE,
                    strength_score=Decimal("6.0"),
                    touch_count=5,
                    first_touch_date=datetime(2025, 1, 5, tzinfo=UTC),
                    last_touch_date=datetime(2025, 1, 18, tzinfo=UTC),
                    average_volume=Decimal("2000000"),
                    highest_volume_touch=Decimal("3000000"),
                    timeframe=Timeframe.DAILY
                )
            ]

            metadata = {
                "days_analyzed": 60,
                "touch_threshold": 3,
                "zones_found": 2,
                "timeframe": "daily"
            }

            logger.log_zone_detection("AAPL", zones, metadata)

            # Verify file was created
            log_files = list(log_dir.glob("*-zones.jsonl"))
            assert len(log_files) == 1

            # Read and parse JSONL
            with log_files[0].open("r") as f:
                line = f.readline()
                entry = json.loads(line)

            assert entry["event"] == "zone_detection"
            assert entry["symbol"] == "AAPL"
            assert entry["zones_count"] == 2
            assert len(entry["zones"]) == 2
            assert entry["metadata"]["days_analyzed"] == 60
            assert entry["zones"][0]["zone_id"] == "support_150.50_daily"
            assert entry["zones"][1]["zone_id"] == "resistance_200.00_daily"

    def test_log_proximity_alert_writes_valid_jsonl(self):
        """Test log_proximity_alert writes valid JSONL."""
        with TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / "zones"
            logger = ZoneLogger(log_dir=log_dir)

            alert = ProximityAlert(
                symbol="AAPL",
                zone_id="support_150.50_daily",
                current_price=Decimal("152.00"),
                zone_price=Decimal("150.50"),
                distance_percent=Decimal("0.99"),
                direction="approaching_support",
                timestamp=datetime(2025, 1, 20, 10, 30, 0, tzinfo=UTC)
            )

            logger.log_proximity_alert(alert)

            # Verify file was created
            log_files = list(log_dir.glob("*-zones.jsonl"))
            assert len(log_files) == 1

            # Read and parse JSONL
            with log_files[0].open("r") as f:
                line = f.readline()
                entry = json.loads(line)

            assert entry["event"] == "proximity_alert"
            assert entry["symbol"] == "AAPL"
            assert entry["zone_id"] == "support_150.50_daily"
            assert entry["current_price"] == "152.00"
            assert entry["distance_percent"] == "0.99"
            assert entry["direction"] == "approaching_support"

    def test_log_breakout_writes_valid_jsonl(self):
        """Test log_breakout writes valid JSONL."""
        with TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / "zones"
            logger = ZoneLogger(log_dir=log_dir)

            zone = Zone(
                price_level=Decimal("150.50"),
                zone_type=ZoneType.SUPPORT,
                strength_score=Decimal("5.0"),
                touch_count=4,
                first_touch_date=datetime(2025, 1, 1, tzinfo=UTC),
                last_touch_date=datetime(2025, 1, 15, tzinfo=UTC),
                average_volume=Decimal("1000000"),
                highest_volume_touch=Decimal("1500000"),
                timeframe=Timeframe.DAILY
            )

            breakout_metadata = {
                "breakout_price": "148.00",
                "breakout_volume": "5000000",
                "direction": "down",
                "strength": "strong",
                "previous_touches": 4
            }

            logger.log_breakout(zone, breakout_metadata)

            # Verify file was created
            log_files = list(log_dir.glob("*-zones.jsonl"))
            assert len(log_files) == 1

            # Read and parse JSONL
            with log_files[0].open("r") as f:
                line = f.readline()
                entry = json.loads(line)

            assert entry["event"] == "breakout"
            assert entry["zone"]["zone_id"] == "support_150.50_daily"
            assert entry["breakout_metadata"]["breakout_price"] == "148.00"
            assert entry["breakout_metadata"]["direction"] == "down"
            assert entry["breakout_metadata"]["strength"] == "strong"

    def test_multiple_events_append_to_same_file(self):
        """Test multiple log events append to the same daily file."""
        with TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / "zones"
            logger = ZoneLogger(log_dir=log_dir)

            # Log zone detection
            zones = [
                Zone(
                    price_level=Decimal("150.50"),
                    zone_type=ZoneType.SUPPORT,
                    strength_score=Decimal("5.0"),
                    touch_count=4,
                    first_touch_date=datetime(2025, 1, 1, tzinfo=UTC),
                    last_touch_date=datetime(2025, 1, 15, tzinfo=UTC),
                    average_volume=Decimal("1000000"),
                    highest_volume_touch=Decimal("1500000"),
                    timeframe=Timeframe.DAILY
                )
            ]
            logger.log_zone_detection("AAPL", zones, {"days_analyzed": 60})

            # Log proximity alert
            alert = ProximityAlert(
                symbol="AAPL",
                zone_id="support_150.50_daily",
                current_price=Decimal("152.00"),
                zone_price=Decimal("150.50"),
                distance_percent=Decimal("0.99"),
                direction="approaching_support",
                timestamp=datetime(2025, 1, 20, tzinfo=UTC)
            )
            logger.log_proximity_alert(alert)

            # Verify only one file was created
            log_files = list(log_dir.glob("*-zones.jsonl"))
            assert len(log_files) == 1

            # Verify both events are in the file
            with log_files[0].open("r") as f:
                lines = f.readlines()

            assert len(lines) == 2
            entry1 = json.loads(lines[0])
            entry2 = json.loads(lines[1])

            assert entry1["event"] == "zone_detection"
            assert entry2["event"] == "proximity_alert"

    def test_daily_file_path_format(self):
        """Test daily file path follows YYYY-MM-DD-zones.jsonl format."""
        with TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / "zones"
            logger = ZoneLogger(log_dir=log_dir)

            # Get the file path
            file_path = logger._get_daily_file_path()

            # Verify format
            assert file_path.parent == log_dir
            assert file_path.suffix == ".jsonl"
            assert "-zones.jsonl" in file_path.name

            # Verify date format (YYYY-MM-DD)
            date_part = file_path.stem.replace("-zones", "")
            assert len(date_part) == 10  # YYYY-MM-DD
            assert date_part.count("-") == 2

    def test_log_breakout_event_creates_jsonl_file(self):
        """Test log_breakout_event writes to breakouts-YYYY-MM-DD.jsonl file (T030)."""
        with TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / "zones"
            logger = ZoneLogger(log_dir=log_dir)

            # Create breakout event
            event = BreakoutEvent(
                event_id="evt_test123",
                zone_id="resistance_155.00_daily",
                timestamp=datetime(2025, 10, 21, 12, 0, 0, tzinfo=UTC),
                breakout_price=Decimal("155.00"),
                close_price=Decimal("156.60"),
                volume=Decimal("1500000"),
                volume_ratio=Decimal("1.4"),
                old_zone_type=ZoneType.RESISTANCE,
                new_zone_type=ZoneType.SUPPORT,
                status=BreakoutStatus.CONFIRMED,
                timeframe=Timeframe.DAILY
            )

            # Log event
            logger.log_breakout_event(event)

            # Verify file exists
            today = datetime.now(UTC).date().isoformat()
            file_path = log_dir / f"breakouts-{today}.jsonl"
            assert file_path.exists()

            # Verify contents
            with file_path.open("r") as f:
                line = f.readline()
                entry = json.loads(line)

            assert entry["event_id"] == "evt_test123"
            assert entry["zone_id"] == "resistance_155.00_daily"
            assert entry["breakout_price"] == "155.00"  # Decimal as string
            assert entry["old_zone_type"] == "resistance"  # lowercase
            assert entry["status"] == "confirmed"
            assert entry["timestamp"] == "2025-10-21T12:00:00+00:00"  # ISO format
