"""
Unit test: Dashboard logs usage events correctly.

T033 - Tests that dashboard logs usage events in JSONL format
with correct event structure and session tracking.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from trading_bot.logger import log_dashboard_event


class TestDashboardLogging:
    """Unit tests for dashboard event logging."""

    def test_dashboard_launched_event_logged(self, tmp_path, monkeypatch):
        """
        T033.1 - Verify dashboard.launched event is logged on startup.

        Tests that dashboard startup creates a properly formatted
        JSONL event with timestamp and event type.
        """
        # Set up temporary log path
        log_path = tmp_path / "dashboard-usage.jsonl"

        # Log launched event with custom log path
        log_dashboard_event("dashboard.launched", log_path=log_path)

        # Verify file was created
        assert log_path.exists()

        # Read and verify event
        with log_path.open("r", encoding="utf-8") as f:
            line = f.readline()
            event = json.loads(line)

        assert event["event"] == "dashboard.launched"
        assert "timestamp" in event
        assert "T" in event["timestamp"]  # ISO 8601 format

        # Verify timestamp is parseable
        dt = datetime.fromisoformat(event["timestamp"])
        assert dt is not None

    def test_dashboard_refreshed_event_with_metadata(self, tmp_path, monkeypatch):
        """
        T033.2 - Verify dashboard.refreshed event includes metadata.

        Tests that refresh events include manual flag, data age,
        staleness indicator, and warning count.
        """
        log_path = tmp_path / "dashboard-usage.jsonl"
        # Log refresh event with metadata
        log_dashboard_event("dashboard.refreshed", log_path=log_path,
            manual=True,
            data_age_seconds=5.2,
            is_data_stale=False,
            warnings=2,
        )

        # Read and verify event
        with log_path.open("r", encoding="utf-8") as f:
            line = f.readline()
            event = json.loads(line)

        assert event["event"] == "dashboard.refreshed"
        assert event["manual"] is True
        assert event["data_age_seconds"] == 5.2
        assert event["is_data_stale"] is False
        assert event["warnings"] == 2

    def test_dashboard_exported_event_with_paths(self, tmp_path, monkeypatch):
        """
        T033.3 - Verify dashboard.exported event includes file paths.

        Tests that export events log the paths of generated files.
        """
        log_path = tmp_path / "dashboard-usage.jsonl"
        # Log export event
        log_dashboard_event("dashboard.exported", log_path=log_path,
            json_path="logs/dashboard-export-2024-01-15.json",
            markdown_path="logs/dashboard-export-2024-01-15.md",
        )

        # Read and verify event
        with log_path.open("r", encoding="utf-8") as f:
            line = f.readline()
            event = json.loads(line)

        assert event["event"] == "dashboard.exported"
        assert "json_path" in event
        assert "markdown_path" in event
        assert event["json_path"].endswith(".json")
        assert event["markdown_path"].endswith(".md")

    def test_dashboard_exited_event_logged(self, tmp_path, monkeypatch):
        """
        T033.4 - Verify dashboard.exited event is logged on quit.

        Tests that dashboard shutdown creates exit event.
        """
        log_path = tmp_path / "dashboard-usage.jsonl"
        # Log exit event
        log_dashboard_event("dashboard.exited")

        # Read and verify event
        with log_path.open("r", encoding="utf-8") as f:
            line = f.readline()
            event = json.loads(line)

        assert event["event"] == "dashboard.exited"
        assert "timestamp" in event

    def test_dashboard_error_event_with_context(self, tmp_path, monkeypatch):
        """
        T033.5 - Verify error events include context information.

        Tests that error events log error type and message.
        """
        log_path = tmp_path / "dashboard-usage.jsonl"
        # Log error event
        log_dashboard_event("dashboard.error", log_path=log_path,
            error_type="APIException",
            error_message="Connection timeout",
            context="refresh_account_data",
        )

        # Read and verify event
        with log_path.open("r", encoding="utf-8") as f:
            line = f.readline()
            event = json.loads(line)

        assert event["event"] == "dashboard.error"
        assert event["error_type"] == "APIException"
        assert event["error_message"] == "Connection timeout"
        assert event["context"] == "refresh_account_data"

    def test_multiple_events_appended_to_log(self, tmp_path, monkeypatch):
        """
        T033.6 - Verify multiple events are appended in sequence.

        Tests that events accumulate in the log file (append mode).
        """
        log_path = tmp_path / "dashboard-usage.jsonl"
        # Log multiple events
        log_dashboard_event("dashboard.launched")
        log_dashboard_event("dashboard.refreshed", log_path=log_path, manual=False)
        log_dashboard_event("dashboard.exported", log_path=log_path, json_path="test.json")
        log_dashboard_event("dashboard.exited")

        # Read all events
        with log_path.open("r", encoding="utf-8") as f:
            events = [json.loads(line) for line in f]

        assert len(events) == 4
        assert events[0]["event"] == "dashboard.launched"
        assert events[1]["event"] == "dashboard.refreshed"
        assert events[2]["event"] == "dashboard.exported"
        assert events[3]["event"] == "dashboard.exited"

    def test_jsonl_format_each_line_valid_json(self, tmp_path, monkeypatch):
        """
        T033.7 - Verify JSONL format (each line is valid JSON).

        Tests that each line in the log file is independently
        parseable as JSON.
        """
        log_path = tmp_path / "dashboard-usage.jsonl"
        # Log several events
        for i in range(5):
            log_dashboard_event(f"test.event.{i}", sequence=i)

        # Verify each line is valid JSON
        with log_path.open("r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                try:
                    event = json.loads(line)
                    assert "event" in event
                    assert "timestamp" in event
                except json.JSONDecodeError as e:
                    pytest.fail(f"Line {line_num} is not valid JSON: {e}")

    def test_event_structure_consistency(self, tmp_path, monkeypatch):
        """
        T033.8 - Verify all events have consistent base structure.

        Tests that all events have required fields: timestamp, event.
        """
        log_path = tmp_path / "dashboard-usage.jsonl"
        # Log different event types
        log_dashboard_event("dashboard.launched")
        log_dashboard_event("dashboard.refreshed", log_path=log_path, manual=True)
        log_dashboard_event("dashboard.exported", log_path=log_path, json_path="test.json")
        log_dashboard_event("dashboard.interrupted")
        log_dashboard_event("dashboard.exited")

        # Verify all events have base structure
        with log_path.open("r", encoding="utf-8") as f:
            for line in f:
                event = json.loads(line)

                # Required fields
                assert "timestamp" in event, "Missing timestamp"
                assert "event" in event, "Missing event type"

                # Timestamp format
                assert isinstance(event["timestamp"], str)
                assert "T" in event["timestamp"]  # ISO 8601

                # Event type format
                assert isinstance(event["event"], str)
                assert "dashboard." in event["event"]

    def test_log_directory_created_automatically(self, tmp_path, monkeypatch):
        """
        T033.9 - Verify log directory is created if it doesn't exist.

        Tests that logging creates parent directories automatically.
        """
        log_path = tmp_path / "deep" / "nested" / "logs" / "dashboard-usage.jsonl"
        # Log event (should create directories)
        log_dashboard_event("dashboard.launched")

        # Verify file and parent directories were created
        assert log_path.exists()
        assert log_path.parent.exists()

    def test_logging_failure_does_not_crash_dashboard(
        self, tmp_path, monkeypatch, caplog
    ):
        """
        T033.10 - Verify logging failures don't crash dashboard.

        Tests that if logging fails (e.g., disk full, permissions),
        dashboard continues operating and logs warning.
        """
        # Set up path that will fail to write (read-only parent)
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()

        log_path = readonly_dir / "dashboard-usage.jsonl"
        # Make directory read-only
        import os
        import stat

        try:
            os.chmod(readonly_dir, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

            # Should not raise exception, just log warning
            log_dashboard_event("dashboard.launched")

            # Should have logged warning about failure
            assert any(
                "Failed to write dashboard event" in rec.message
                for rec in caplog.records
            )

        finally:
            # Restore permissions for cleanup
            try:
                os.chmod(
                    readonly_dir,
                    stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO,
                )
            except:
                pass  # Best effort

    def test_unicode_content_in_events(self, tmp_path, monkeypatch):
        """
        T033.11 - Verify events can contain Unicode characters.

        Tests that log handles Unicode symbols (e.g., ⚠️, ✓, ✗)
        correctly in event payloads.
        """
        log_path = tmp_path / "dashboard-usage.jsonl"
        # Log event with Unicode content
        log_dashboard_event("dashboard.warning", log_path=log_path,
            message="⚠️ Data may be stale",
            status="✗ Failed",
        )

        # Read and verify
        with log_path.open("r", encoding="utf-8") as f:
            line = f.readline()
            event = json.loads(line)

        assert "⚠️" in event["message"]
        assert "✗" in event["status"]

    def test_event_payload_serialization(self, tmp_path, monkeypatch):
        """
        T033.12 - Verify complex payload types are serialized correctly.

        Tests that different data types (int, float, bool, None, list, dict)
        are serialized correctly in event payloads.
        """
        log_path = tmp_path / "dashboard-usage.jsonl"
        # Log event with various types
        log_dashboard_event("dashboard.test", log_path=log_path,
            int_value=42,
            float_value=3.14159,
            bool_value=True,
            none_value=None,
            list_value=[1, 2, 3],
            dict_value={"key": "value"},
        )

        # Read and verify
        with log_path.open("r", encoding="utf-8") as f:
            line = f.readline()
            event = json.loads(line)

        assert event["int_value"] == 42
        assert event["float_value"] == 3.14159
        assert event["bool_value"] is True
        assert event["none_value"] is None
        assert event["list_value"] == [1, 2, 3]
        assert event["dict_value"] == {"key": "value"}
