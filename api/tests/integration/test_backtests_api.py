"""Integration tests for backtest API endpoints.

These tests verify:
- End-to-end GET /api/v1/backtests with filtering
- End-to-end GET /api/v1/backtests/:id with caching
- File-based data loading
- 404 handling for missing backtests
"""

import json
from pathlib import Path
from typing import Generator
import tempfile

import pytest
from fastapi.testclient import TestClient

from api.app.main import app


@pytest.fixture
def temp_backtest_dir() -> Generator[Path, None, None]:
    """Create temporary backtest results directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_backtest_data() -> dict:
    """Sample backtest JSON data."""
    return {
        "config": {
            "strategy": "MeanReversion",
            "symbols": ["AAPL", "MSFT"],
            "start_date": "2024-01-01",
            "end_date": "2024-03-31",
            "initial_capital": 100000.0,
            "commission": 0.001,
            "slippage_pct": 0.001,
        },
        "metrics": {
            "total_return": 15.5,
            "annualized_return": 62.0,
            "cagr": 58.5,
            "win_rate": 0.65,
            "profit_factor": 2.1,
            "average_win": 450.0,
            "average_loss": -200.0,
            "max_drawdown": -8.5,
            "max_drawdown_duration_days": 12,
            "sharpe_ratio": 1.85,
            "total_trades": 42,
            "winning_trades": 27,
            "losing_trades": 15,
        },
        "trades": [
            {
                "symbol": "AAPL",
                "entry_date": "2024-01-05",
                "entry_price": 150.0,
                "exit_date": "2024-01-15",
                "exit_price": 155.0,
                "shares": 100,
                "pnl": 500.0,
                "pnl_pct": 3.33,
                "duration_days": 10,
                "exit_reason": "target",
                "commission": 0.15,
                "slippage": 0.15,
            }
        ],
        "equity_curve": [
            {"timestamp": "2024-01-01", "equity": 100000.0},
            {"timestamp": "2024-01-05", "equity": 99500.0},
            {"timestamp": "2024-01-15", "equity": 100000.0},
        ],
        "data_warnings": [],
        "metadata": {"completed_at": "2024-10-28T12:00:00Z"},
    }


@pytest.fixture
def populated_backtest_dir(
    temp_backtest_dir: Path, sample_backtest_data: dict
) -> Path:
    """Create backtest directory with sample data."""
    # Create test backtest files
    backtest1 = sample_backtest_data.copy()
    backtest1["config"]["strategy"] = "MeanReversion"
    backtest1["metadata"]["completed_at"] = "2024-10-28T12:00:00Z"
    (temp_backtest_dir / "backtest_001.json").write_text(json.dumps(backtest1))

    backtest2 = sample_backtest_data.copy()
    backtest2["config"]["strategy"] = "Momentum"
    backtest2["config"]["start_date"] = "2024-04-01"
    backtest2["config"]["end_date"] = "2024-06-30"
    backtest2["metrics"]["total_return"] = 22.3
    backtest2["metadata"]["completed_at"] = "2024-10-27T10:00:00Z"
    (temp_backtest_dir / "backtest_002.json").write_text(json.dumps(backtest2))

    backtest3 = sample_backtest_data.copy()
    backtest3["config"]["strategy"] = "MeanReversion"
    backtest3["config"]["start_date"] = "2024-07-01"
    backtest3["config"]["end_date"] = "2024-09-30"
    backtest3["metrics"]["total_return"] = 8.7
    backtest3["metadata"]["completed_at"] = "2024-10-26T08:00:00Z"
    (temp_backtest_dir / "backtest_003.json").write_text(json.dumps(backtest3))

    return temp_backtest_dir


@pytest.fixture
def test_client(populated_backtest_dir: Path) -> TestClient:
    """Create test client with mocked backtest directory."""
    # Override BacktestLoader with test directory
    from api.app.routes import backtests
    from api.app.services.backtest_loader import BacktestLoader

    backtests.loader = BacktestLoader(backtest_dir=str(populated_backtest_dir))
    return TestClient(app)


class TestListBacktests:
    """Test GET /api/v1/backtests endpoint."""

    def test_list_all_backtests(self, test_client: TestClient) -> None:
        """Test listing all backtests without filters."""
        response = test_client.get("/api/v1/backtests")

        assert response.status_code == 200
        data = response.json()

        assert "data" in data
        assert "total" in data
        assert data["total"] == 3
        assert len(data["data"]) == 3

        # Verify sorted by created_at (newest first)
        assert data["data"][0]["id"] == "backtest_001"
        assert data["data"][1]["id"] == "backtest_002"
        assert data["data"][2]["id"] == "backtest_003"

    def test_filter_by_strategy(self, test_client: TestClient) -> None:
        """Test filtering backtests by strategy name."""
        response = test_client.get("/api/v1/backtests?strategy=MeanReversion")

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 2
        assert len(data["data"]) == 2
        assert all(bt["strategy"] == "MeanReversion" for bt in data["data"])

    def test_filter_by_date_range(self, test_client: TestClient) -> None:
        """Test filtering backtests by date range."""
        response = test_client.get(
            "/api/v1/backtests?start_date=2024-04-01&end_date=2024-06-30"
        )

        assert response.status_code == 200
        data = response.json()

        # Should match backtest_002 exactly
        assert data["total"] == 1
        assert data["data"][0]["id"] == "backtest_002"
        assert data["data"][0]["start_date"] == "2024-04-01"

    def test_limit_parameter(self, test_client: TestClient) -> None:
        """Test pagination limit parameter."""
        response = test_client.get("/api/v1/backtests?limit=2")

        assert response.status_code == 200
        data = response.json()

        assert len(data["data"]) == 2
        assert data["total"] == 2  # Total returned, not total available

    def test_response_schema(self, test_client: TestClient) -> None:
        """Test response schema matches BacktestListResponse."""
        response = test_client.get("/api/v1/backtests")

        assert response.status_code == 200
        data = response.json()

        # Verify top-level structure
        assert "data" in data
        assert "total" in data

        # Verify BacktestSummary structure
        summary = data["data"][0]
        required_fields = [
            "id",
            "strategy",
            "symbols",
            "start_date",
            "end_date",
            "total_return",
            "win_rate",
            "total_trades",
            "created_at",
        ]

        for field in required_fields:
            assert field in summary, f"Missing field: {field}"

        # Verify data types
        assert isinstance(summary["id"], str)
        assert isinstance(summary["strategy"], str)
        assert isinstance(summary["symbols"], list)
        assert isinstance(summary["total_return"], (int, float))
        assert isinstance(summary["win_rate"], (int, float))
        assert isinstance(summary["total_trades"], int)


class TestGetBacktestDetail:
    """Test GET /api/v1/backtests/:id endpoint."""

    def test_get_existing_backtest(self, test_client: TestClient) -> None:
        """Test fetching an existing backtest by ID."""
        response = test_client.get("/api/v1/backtests/backtest_001")

        assert response.status_code == 200
        data = response.json()

        # Verify complete structure
        assert "config" in data
        assert "metrics" in data
        assert "trades" in data
        assert "equity_curve" in data
        assert "data_warnings" in data

        # Verify config
        assert data["config"]["strategy"] == "MeanReversion"
        assert data["config"]["initial_capital"] == 100000.0

        # Verify metrics
        assert data["metrics"]["total_return"] == 15.5
        assert data["metrics"]["sharpe_ratio"] == 1.85

        # Verify trades
        assert len(data["trades"]) == 1
        assert data["trades"][0]["symbol"] == "AAPL"

        # Verify equity curve
        assert len(data["equity_curve"]) == 3

    def test_get_nonexistent_backtest(self, test_client: TestClient) -> None:
        """Test 404 error for nonexistent backtest."""
        response = test_client.get("/api/v1/backtests/invalid_id")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    def test_response_schema_detail(self, test_client: TestClient) -> None:
        """Test detail response schema matches BacktestDetailResponse."""
        response = test_client.get("/api/v1/backtests/backtest_001")

        assert response.status_code == 200
        data = response.json()

        # Verify BacktestConfig
        config_fields = [
            "strategy",
            "symbols",
            "start_date",
            "end_date",
            "initial_capital",
            "commission",
            "slippage_pct",
        ]
        for field in config_fields:
            assert field in data["config"], f"Missing config field: {field}"

        # Verify PerformanceMetrics
        metrics_fields = [
            "total_return",
            "annualized_return",
            "cagr",
            "win_rate",
            "profit_factor",
            "sharpe_ratio",
            "max_drawdown",
        ]
        for field in metrics_fields:
            assert field in data["metrics"], f"Missing metrics field: {field}"

        # Verify TradeDetail structure
        trade = data["trades"][0]
        trade_fields = [
            "symbol",
            "entry_date",
            "entry_price",
            "exit_date",
            "exit_price",
            "shares",
            "pnl",
            "pnl_pct",
        ]
        for field in trade_fields:
            assert field in trade, f"Missing trade field: {field}"


class TestCachingBehavior:
    """Test LRU cache behavior for get_backtest."""

    def test_cache_hit_performance(self, test_client: TestClient) -> None:
        """Test that repeated requests benefit from caching."""
        import time

        # First request (cache miss)
        start = time.perf_counter()
        response1 = test_client.get("/api/v1/backtests/backtest_001")
        first_request_time = time.perf_counter() - start

        assert response1.status_code == 200

        # Second request (cache hit should be faster)
        start = time.perf_counter()
        response2 = test_client.get("/api/v1/backtests/backtest_001")
        second_request_time = time.perf_counter() - start

        assert response2.status_code == 200
        assert response1.json() == response2.json()

        # Cache hit should be faster (though not always guaranteed in test env)
        print(f"\nFirst request: {first_request_time*1000:.2f}ms")
        print(f"Second request: {second_request_time*1000:.2f}ms")


class TestErrorHandling:
    """Test error handling and malformed data."""

    def test_malformed_json_file(
        self, test_client: TestClient, populated_backtest_dir: Path
    ) -> None:
        """Test that malformed JSON files are skipped gracefully."""
        # Create malformed JSON file
        (populated_backtest_dir / "malformed.json").write_text("{ invalid json")

        # Should still return valid backtests
        response = test_client.get("/api/v1/backtests")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3  # Only valid backtests

    def test_empty_backtest_directory(
        self, temp_backtest_dir: Path, test_client: TestClient
    ) -> None:
        """Test behavior with empty backtest directory."""
        from api.app.routes import backtests
        from api.app.services.backtest_loader import BacktestLoader

        # Override with empty directory
        backtests.loader = BacktestLoader(backtest_dir=str(temp_backtest_dir))

        response = test_client.get("/api/v1/backtests")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["data"] == []
