"""
Integration tests for Momentum API routes.

Tests FastAPI endpoints with TestClient:
- GET /api/v1/momentum/signals - Query historical signals
- POST /api/v1/momentum/scan - Trigger momentum scans
- GET /api/v1/momentum/scans/{scan_id} - Poll scan status

CR-002: Achieve >90% coverage for routes module (170 lines untested)
"""

import asyncio
import json
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.trading_bot.momentum.routes import scan_router, signals_router
from src.trading_bot.momentum.routes.scan import _scan_results


@pytest.fixture
def app():
    """Create FastAPI app with momentum routes."""
    app = FastAPI()
    app.include_router(signals_router)
    app.include_router(scan_router)
    return app


@pytest.fixture
def client(app):
    """Create TestClient for API testing."""
    return TestClient(app)


@pytest.fixture
def sample_signals_log(tmp_path):
    """Create sample JSONL signal logs for testing."""
    log_dir = tmp_path / "logs" / "momentum"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Create sample signals across two days
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    yesterday = (datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%d")

    signals = [
        # Today's signals
        {
            "event_type": "signal_detected",
            "signal_id": str(uuid.uuid4()),
            "symbol": "AAPL",
            "signal_type": "catalyst",
            "strength": 85.5,
            "detected_at": datetime.now(UTC).isoformat(),
            "details": {"news_count": 5, "sentiment": "positive"}
        },
        {
            "event_type": "signal_detected",
            "signal_id": str(uuid.uuid4()),
            "symbol": "GOOGL",
            "signal_type": "premarket",
            "strength": 72.3,
            "detected_at": (datetime.now(UTC) - timedelta(hours=2)).isoformat(),
            "details": {"volume_ratio": 3.5, "price_change": 0.045}
        },
        {
            "event_type": "signal_detected",
            "signal_id": str(uuid.uuid4()),
            "symbol": "TSLA",
            "signal_type": "pattern",
            "strength": 90.1,
            "detected_at": (datetime.now(UTC) - timedelta(hours=1)).isoformat(),
            "details": {"pattern_type": "bull_flag", "breakout_price": 250.50}
        },
        {
            "event_type": "signal_detected",
            "signal_id": str(uuid.uuid4()),
            "symbol": "MSFT",
            "signal_type": "catalyst",
            "strength": 45.8,
            "detected_at": (datetime.now(UTC) - timedelta(hours=3)).isoformat(),
            "details": {"news_count": 2, "sentiment": "neutral"}
        },
        # Yesterday's signals
        {
            "event_type": "signal_detected",
            "signal_id": str(uuid.uuid4()),
            "symbol": "NVDA",
            "signal_type": "pattern",
            "strength": 78.9,
            "detected_at": (datetime.now(UTC) - timedelta(days=1)).isoformat(),
            "details": {"pattern_type": "bull_flag", "breakout_price": 500.00}
        },
        # Non-signal events (should be ignored)
        {
            "event_type": "scan_started",
            "symbols": ["AAPL", "GOOGL"],
            "timestamp": datetime.now(UTC).isoformat()
        }
    ]

    # Write today's log
    today_log = log_dir / f"{today}.jsonl"
    with today_log.open("w") as f:
        for signal in signals[:4] + [signals[5]]:  # Today's signals + non-signal event
            f.write(json.dumps(signal) + "\n")

    # Write yesterday's log
    yesterday_log = log_dir / f"{yesterday}.jsonl"
    with yesterday_log.open("w") as f:
        f.write(json.dumps(signals[4]) + "\n")

    return log_dir


@pytest.fixture
def mock_momentum_engine():
    """Mock MomentumEngine for scan testing."""
    engine = Mock()
    engine.scan = AsyncMock(return_value=[
        Mock(
            symbol="AAPL",
            signal_type=Mock(value="catalyst"),
            strength=85.5,
            detected_at=datetime.now(UTC),
            details={"news_count": 5}
        ),
        Mock(
            symbol="GOOGL",
            signal_type=Mock(value="premarket"),
            strength=72.3,
            detected_at=datetime.now(UTC),
            details={"volume_ratio": 3.5}
        )
    ])
    return engine


@pytest.fixture(autouse=True)
def cleanup_scan_results():
    """Clear scan results before and after each test."""
    _scan_results.clear()
    yield
    _scan_results.clear()


class TestSignalsQueryEndpoint:
    """Integration tests for GET /api/v1/momentum/signals."""

    @patch("src.trading_bot.momentum.routes.signals.Path")
    def test_query_signals_no_filters(self, mock_path_class, client, sample_signals_log):
        """T-API-001: Query all signals without filters returns all results."""
        # Set log directory to sample data
        mock_path_class.return_value = sample_signals_log

        response = client.get("/api/v1/momentum/signals")

        assert response.status_code == 200
        data = response.json()

        # Should return all 5 signal_detected events
        assert data["total"] == 5
        assert data["count"] == 5
        assert data["has_more"] is False
        assert len(data["signals"]) == 5

        # Signals should be sorted by strength (descending) by default
        assert data["signals"][0]["symbol"] == "TSLA"  # 90.1
        assert data["signals"][0]["strength"] == 90.1

    @patch("src.trading_bot.momentum.routes.signals.Path")
    def test_query_signals_filter_by_symbols(self, mock_path_class, client, sample_signals_log):
        """T-API-002: Filter signals by symbol list."""
        mock_path_class.return_value = sample_signals_log

        response = client.get("/api/v1/momentum/signals?symbols=AAPL,GOOGL")

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 2
        assert data["count"] == 2
        symbols = [s["symbol"] for s in data["signals"]]
        assert "AAPL" in symbols
        assert "GOOGL" in symbols
        assert "TSLA" not in symbols

    @patch("src.trading_bot.momentum.routes.signals.Path")
    def test_query_signals_filter_by_signal_type(self, mock_path_class, client, sample_signals_log):
        """T-API-003: Filter signals by signal type."""
        mock_path_class.return_value = sample_signals_log

        response = client.get("/api/v1/momentum/signals?signal_type=catalyst")

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 2  # AAPL and MSFT
        assert all(s["signal_type"] == "catalyst" for s in data["signals"])

    @patch("src.trading_bot.momentum.routes.signals.Path")
    def test_query_signals_filter_by_min_strength(self, mock_path_class, client, sample_signals_log):
        """T-API-004: Filter signals by minimum strength threshold."""
        mock_path_class.return_value = sample_signals_log

        response = client.get("/api/v1/momentum/signals?min_strength=75.0")

        assert response.status_code == 200
        data = response.json()

        # Should only include TSLA (90.1), AAPL (85.5), NVDA (78.9)
        assert data["total"] == 3
        assert all(s["strength"] >= 75.0 for s in data["signals"])

    @patch("src.trading_bot.momentum.routes.signals.Path")
    def test_query_signals_pagination(self, mock_path_class, client, sample_signals_log):
        """T-API-005: Pagination with limit and offset works correctly."""
        mock_path_class.return_value = sample_signals_log

        # First page (limit=2, offset=0)
        response1 = client.get("/api/v1/momentum/signals?limit=2&offset=0")
        data1 = response1.json()

        assert data1["count"] == 2
        assert data1["total"] == 5
        assert data1["has_more"] is True

        # Second page (limit=2, offset=2)
        response2 = client.get("/api/v1/momentum/signals?limit=2&offset=2")
        data2 = response2.json()

        assert data2["count"] == 2
        assert data2["total"] == 5
        assert data2["has_more"] is True

        # Third page (limit=2, offset=4)
        response3 = client.get("/api/v1/momentum/signals?limit=2&offset=4")
        data3 = response3.json()

        assert data3["count"] == 1  # Only 1 signal left
        assert data3["total"] == 5
        assert data3["has_more"] is False

    @patch("src.trading_bot.momentum.routes.signals.Path")
    def test_query_signals_sorting(self, mock_path_class, client, sample_signals_log):
        """T-API-006: Sorting by different fields works correctly."""
        mock_path_class.return_value = sample_signals_log

        # Sort by symbol (ascending)
        response = client.get("/api/v1/momentum/signals?sort_by=symbol")
        data = response.json()

        symbols = [s["symbol"] for s in data["signals"]]
        assert symbols == sorted(symbols)  # Alphabetical order

        # Sort by detected_at (most recent first)
        response = client.get("/api/v1/momentum/signals?sort_by=detected_at")
        data = response.json()

        # First signal should be most recent
        assert data["signals"][0]["symbol"] == "AAPL"  # Most recent in our sample

    @patch("src.trading_bot.momentum.routes.signals.Path")
    def test_query_signals_time_range_filter(self, mock_path_class, client, sample_signals_log):
        """T-API-007: Filter signals by time range."""
        mock_path_class.return_value = sample_signals_log

        # Test with valid ISO format timestamp (no 'Z' suffix issues)
        # Using a date far in the past to include all signals
        start_time = "2020-01-01T00:00:00+00:00"

        response = client.get(f"/api/v1/momentum/signals?start_time={start_time}")
        data = response.json()

        # Should include all signals since start_time is in the past
        assert data["total"] == 5
        assert data["count"] == 5

    def test_query_signals_invalid_params(self, client):
        """T-API-008: Invalid parameters are handled gracefully."""
        # Min strength out of range (should be clamped by FastAPI validation)
        response = client.get("/api/v1/momentum/signals?min_strength=150.0")
        assert response.status_code == 422  # Validation error

        # Invalid limit (should be validated by FastAPI)
        response = client.get("/api/v1/momentum/signals?limit=1000")
        assert response.status_code == 422

    @patch("src.trading_bot.momentum.routes.signals.Path")
    def test_query_signals_empty_results(self, mock_path_class, client, tmp_path):
        """T-API-009: Empty results when no signals match filters."""
        # Create empty log directory
        empty_log_dir = tmp_path / "logs" / "momentum"
        empty_log_dir.mkdir(parents=True, exist_ok=True)
        mock_path_class.return_value = empty_log_dir

        response = client.get("/api/v1/momentum/signals")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["count"] == 0
        assert data["has_more"] is False
        assert data["signals"] == []

    @patch("src.trading_bot.momentum.routes.signals.Path")
    def test_query_signals_no_log_directory(self, mock_path_class, client, tmp_path):
        """T-API-010: Graceful handling when log directory doesn't exist."""
        # Point to non-existent directory
        non_existent = tmp_path / "logs" / "momentum" / "nonexistent"
        mock_path_class.return_value = non_existent

        response = client.get("/api/v1/momentum/signals")

        # Should return empty results gracefully
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0


class TestScanTriggerEndpoint:
    """Integration tests for POST /api/v1/momentum/scan."""

    @patch("trading_bot.momentum.routes.scan.MomentumEngine")
    @patch("trading_bot.momentum.routes.scan.MomentumConfig")
    def test_trigger_scan_success(self, mock_config, mock_engine_class, client):
        """T-API-011: Successfully trigger scan and receive scan_id."""
        # Mock MomentumEngine to avoid real initialization
        mock_engine = Mock()
        mock_engine.scan = AsyncMock(return_value=[])
        mock_engine_class.return_value = mock_engine
        mock_config.from_env.return_value = Mock()

        payload = {
            "symbols": ["AAPL", "GOOGL", "TSLA"],
            "scan_types": ["catalyst", "premarket"]
        }

        response = client.post("/api/v1/momentum/scan", json=payload)

        assert response.status_code == 202  # Accepted
        data = response.json()

        assert "scan_id" in data
        assert data["status"] == "queued"
        assert "3 symbols" in data["message"]

        # Verify scan_id is valid UUID
        try:
            uuid.UUID(data["scan_id"])
        except ValueError:
            pytest.fail("scan_id is not a valid UUID")

    def test_trigger_scan_empty_symbols(self, client):
        """T-API-012: Reject scan with empty symbols list."""
        payload = {"symbols": []}

        response = client.post("/api/v1/momentum/scan", json=payload)

        assert response.status_code == 422  # Validation error (Pydantic min_items=1)

    def test_trigger_scan_too_many_symbols(self, client):
        """T-API-013: Reject scan with too many symbols (>100)."""
        payload = {"symbols": [f"SYM{i}" for i in range(101)]}

        response = client.post("/api/v1/momentum/scan", json=payload)

        assert response.status_code == 422  # Validation error (Pydantic max_items=100)

    def test_trigger_scan_invalid_scan_types(self, client):
        """T-API-014: Reject scan with invalid scan_types."""
        payload = {
            "symbols": ["AAPL"],
            "scan_types": ["invalid_type"]
        }

        response = client.post("/api/v1/momentum/scan", json=payload)

        assert response.status_code == 400  # Bad request
        assert "Invalid scan_types" in response.json()["detail"]

    @patch("trading_bot.momentum.routes.scan.MomentumEngine")
    @patch("trading_bot.momentum.routes.scan.MomentumConfig")
    def test_trigger_scan_default_scan_types(self, mock_config, mock_engine_class, client):
        """T-API-015: Default scan_types includes all types when not specified."""
        mock_engine = Mock()
        mock_engine.scan = AsyncMock(return_value=[])
        mock_engine_class.return_value = mock_engine
        mock_config.from_env.return_value = Mock()

        payload = {"symbols": ["AAPL"]}  # No scan_types specified

        response = client.post("/api/v1/momentum/scan", json=payload)

        assert response.status_code == 202
        data = response.json()

        # Background task should use all scan types
        scan_id = data["scan_id"]
        # Wait briefly for background task to start
        import time
        time.sleep(0.1)

        # Verify scan_types defaulted to all types
        assert scan_id in _scan_results
        assert set(_scan_results[scan_id]["scan_types"]) == {"catalyst", "premarket", "pattern"}


class TestScanStatusEndpoint:
    """Integration tests for GET /api/v1/momentum/scans/{scan_id}."""

    def test_get_scan_status_not_found(self, client):
        """T-API-016: 404 error when scan_id doesn't exist."""
        fake_scan_id = str(uuid.uuid4())

        response = client.get(f"/api/v1/momentum/scans/{fake_scan_id}")

        assert response.status_code == 404
        assert f"Scan {fake_scan_id} not found" in response.json()["detail"]

    def test_get_scan_status_queued(self, client):
        """T-API-017: Poll scan status in queued state."""
        # Manually create a scan in queued state (without triggering background task)
        scan_id = str(uuid.uuid4())
        _scan_results[scan_id] = {
            "scan_id": scan_id,
            "status": "queued",
            "created_at": datetime.now(UTC).isoformat(),
            "completed_at": None,
            "symbols": ["AAPL"],
            "scan_types": ["catalyst"],
            "signal_count": 0,
            "signals": [],
            "error": None
        }

        # Poll status
        response = client.get(f"/api/v1/momentum/scans/{scan_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["scan_id"] == scan_id
        assert data["status"] == "queued"
        assert data["symbols"] == ["AAPL"]
        assert data["signal_count"] == 0
        assert data["signals"] == []
        assert data["completed_at"] is None

    def test_get_scan_status_completed(self, client):
        """T-API-018: Poll scan status after completion returns signals."""
        # Manually create a completed scan
        scan_id = str(uuid.uuid4())
        _scan_results[scan_id] = {
            "scan_id": scan_id,
            "status": "completed",
            "created_at": datetime.now(UTC).isoformat(),
            "completed_at": datetime.now(UTC).isoformat(),
            "symbols": ["AAPL"],
            "scan_types": ["catalyst"],
            "signal_count": 1,
            "signals": [{
                "symbol": "AAPL",
                "signal_type": "catalyst",
                "strength": 85.5,
                "detected_at": datetime.now(UTC).isoformat(),
                "details": {"test": True}
            }],
            "error": None
        }

        # Poll status
        response = client.get(f"/api/v1/momentum/scans/{scan_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "completed"
        assert data["signal_count"] == 1
        assert len(data["signals"]) == 1
        assert data["signals"][0]["symbol"] == "AAPL"
        assert data["signals"][0]["strength"] == 85.5
        assert data["completed_at"] is not None


class TestBackgroundScanExecution:
    """Integration tests for background scan task execution."""

    @patch("src.trading_bot.momentum.routes.scan.MomentumEngine")
    @patch("src.trading_bot.momentum.routes.scan.MomentumConfig")
    def test_background_scan_updates_status(self, mock_config, mock_engine_class, client):
        """T-API-019: Background task updates scan status correctly."""
        mock_engine = Mock()
        mock_engine.scan = AsyncMock(return_value=[])
        mock_engine_class.return_value = mock_engine
        mock_config.from_env.return_value = Mock()

        # Trigger scan
        payload = {"symbols": ["AAPL", "GOOGL"]}
        response = client.post("/api/v1/momentum/scan", json=payload)
        scan_id = response.json()["scan_id"]

        # Scan should be created in _scan_results
        assert scan_id in _scan_results
        assert _scan_results[scan_id]["symbols"] == ["AAPL", "GOOGL"]

        # Wait for background task
        import time
        time.sleep(0.5)

        # Status should be completed after background task finishes
        assert _scan_results[scan_id]["status"] == "completed"
        assert _scan_results[scan_id]["completed_at"] is not None

    @patch("src.trading_bot.momentum.routes.scan.MomentumEngine")
    @patch("src.trading_bot.momentum.routes.scan.MomentumConfig")
    def test_background_scan_error_handling(self, mock_config, mock_engine_class, client):
        """T-API-020: Background task handles scan failures gracefully."""
        # Mock engine to raise error
        mock_engine = Mock()
        mock_engine.scan = AsyncMock(side_effect=Exception("Market data unavailable"))
        mock_engine_class.return_value = mock_engine
        mock_config.from_env.return_value = Mock()

        # Trigger scan
        payload = {"symbols": ["AAPL"]}
        response = client.post("/api/v1/momentum/scan", json=payload)
        scan_id = response.json()["scan_id"]

        # Wait for background task to fail
        import time
        time.sleep(0.5)

        # Status should be failed with error message
        assert _scan_results[scan_id]["status"] == "failed"
        assert "Market data unavailable" in _scan_results[scan_id]["error"]
        assert _scan_results[scan_id]["signal_count"] == 0

        # GET endpoint should return error details
        response = client.get(f"/api/v1/momentum/scans/{scan_id}")
        data = response.json()

        assert data["status"] == "failed"
        assert data["error"] is not None
        assert "Market data unavailable" in data["error"]
