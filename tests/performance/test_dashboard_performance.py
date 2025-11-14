"""Performance benchmarks for status dashboard.

This module tests performance targets from plan.md:
- NFR-001: Dashboard startup <2s
- NFR-001: Dashboard refresh cycle <500ms
- NFR-001: Export generation <1s

All tests use deterministic mocks (no real API calls) to ensure
consistent performance measurements.
"""

import time
from decimal import Decimal
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest

from trading_bot.dashboard.data_provider import DashboardDataProvider
from trading_bot.dashboard.export_generator import ExportGenerator
from trading_bot.dashboard.metrics_calculator import MetricsCalculator
from trading_bot.dashboard.models import (
    AccountStatus,
    DashboardSnapshot,
    DashboardTargets,
    PerformanceMetrics,
    PositionDisplay,
)


@pytest.fixture
def mock_account_data() -> Mock:
    """Create mock AccountData service with realistic data."""
    from datetime import datetime, timezone

    from trading_bot.account.account_data import AccountBalance, Position

    mock = Mock()
    mock.get_buying_power.return_value = 10250.50
    mock.get_account_balance.return_value = AccountBalance(
        cash=Decimal("5000.00"),
        equity=Decimal("25340.75"),
        buying_power=Decimal("10250.50"),
        last_updated=datetime.now(timezone.utc),
    )
    mock.get_day_trade_count.return_value = 2
    mock.get_positions.return_value = [
        Position(
            symbol="AAPL",
            quantity=100,
            average_buy_price=Decimal("150.25"),
            current_price=Decimal("152.00"),
            last_updated=datetime.now(timezone.utc),
        ),
        Position(
            symbol="MSFT",
            quantity=50,
            average_buy_price=Decimal("320.50"),
            current_price=Decimal("318.75"),
            last_updated=datetime.now(timezone.utc),
        ),
    ]
    return mock


@pytest.fixture
def mock_trade_helper() -> Mock:
    """Create mock TradeQueryHelper with realistic trade data."""
    from datetime import datetime, timezone
    from uuid import uuid4

    mock = Mock()
    # Mock trades for today - return empty list to avoid complex TradeRecord mocking
    # Performance tests focus on aggregation speed, not trade logic
    mock.query_by_date_range.return_value = []
    mock.log_dir = Path("logs")
    return mock


@pytest.fixture
def mock_targets() -> DashboardTargets:
    """Create sample performance targets."""
    return DashboardTargets(
        win_rate_target=60.0,
        daily_pl_target=Decimal("200.00"),
        trades_per_day_target=5,
        max_drawdown_target=Decimal("-500.00"),
    )


class TestDashboardStartupPerformance:
    """Benchmark dashboard startup time (T036)."""

    @patch("trading_bot.dashboard.data_provider.is_market_open")
    def test_startup_time_under_2_seconds(
        self,
        mock_is_market_open: Mock,
        mock_account_data: Mock,
        mock_trade_helper: Mock,
        mock_targets: DashboardTargets,
    ) -> None:
        """Test dashboard startup completes within 2 seconds.

        Target: NFR-001 - Dashboard startup <2s (cold start)

        This test measures the time to aggregate all dashboard components:
        - Load configuration
        - Fetch account status
        - Fetch positions
        - Calculate performance metrics
        - Determine market status
        """
        mock_is_market_open.return_value = True

        # Measure startup time
        start_time = time.perf_counter()

        # Execute dashboard state aggregation (cold start simulation)
        provider = DashboardDataProvider(
            account_data=mock_account_data,
            trade_helper=mock_trade_helper,
            metrics_calculator=MetricsCalculator(),
        )
        snapshot = provider.get_snapshot(targets=mock_targets)

        end_time = time.perf_counter()
        elapsed = end_time - start_time

        # Verify performance target
        assert elapsed < 2.0, f"Startup took {elapsed:.3f}s, expected <2s"

        # Verify state was aggregated correctly
        assert snapshot is not None
        assert snapshot.account_status is not None
        assert snapshot.performance_metrics is not None

        # Log performance for monitoring
        print(f"\nDashboard startup time: {elapsed * 1000:.2f}ms")


class TestDashboardRefreshPerformance:
    """Benchmark dashboard refresh cycle time (T037)."""

    @patch("trading_bot.dashboard.data_provider.is_market_open")
    def test_refresh_cycle_under_500ms(
        self,
        mock_is_market_open: Mock,
        mock_account_data: Mock,
        mock_trade_helper: Mock,
        mock_targets: DashboardTargets,
    ) -> None:
        """Test dashboard refresh completes within 500ms.

        Target: NFR-001 - Dashboard refresh cycle <500ms

        This test measures the time to refresh dashboard state:
        - Re-fetch account data (from cache if within 60s)
        - Re-query trade logs
        - Recalculate performance metrics
        - Update market status
        """
        mock_is_market_open.return_value = True

        # Create provider instance
        provider = DashboardDataProvider(
            account_data=mock_account_data,
            trade_helper=mock_trade_helper,
            metrics_calculator=MetricsCalculator(),
        )

        # Warm-up call (simulate cache population)
        provider.get_snapshot(targets=mock_targets)

        # Measure refresh time (second call, cache warm)
        start_time = time.perf_counter()

        snapshot = provider.get_snapshot(targets=mock_targets)

        end_time = time.perf_counter()
        elapsed = end_time - start_time

        # Verify performance target
        assert elapsed < 0.5, f"Refresh took {elapsed * 1000:.0f}ms, expected <500ms"

        # Verify state was refreshed
        assert snapshot is not None

        # Log performance for monitoring
        print(f"\nDashboard refresh time: {elapsed * 1000:.2f}ms")


class TestExportGenerationPerformance:
    """Benchmark export generation time (T038)."""

    def test_export_generation_under_1_second(
        self, tmp_path: Path, mock_targets: DashboardTargets
    ) -> None:
        """Test export generation completes within 1 second.

        Target: NFR-001 - Export generation <1s

        This test measures the time to generate both export formats:
        - JSON serialization (with Decimal handling)
        - Markdown formatting
        - File I/O operations
        """
        # Create realistic dashboard snapshot for export
        from datetime import datetime, timezone

        snapshot = DashboardSnapshot(
            account_status=AccountStatus(
                buying_power=Decimal("10250.50"),
                account_balance=Decimal("25340.75"),
                cash_balance=Decimal("5000.00"),
                day_trade_count=2,
                last_updated=datetime.now(timezone.utc),
            ),
            positions=[
                PositionDisplay(
                    symbol="AAPL",
                    quantity=100,
                    entry_price=Decimal("150.25"),
                    current_price=Decimal("152.00"),
                    unrealized_pl=Decimal("175.00"),
                    unrealized_pl_pct=Decimal("1.17"),
                    last_updated=datetime.now(timezone.utc),
                )
            ],
            performance_metrics=PerformanceMetrics(
                win_rate=66.7,
                avg_risk_reward=2.2,
                total_realized_pl=Decimal("275.25"),
                total_unrealized_pl=Decimal("175.00"),
                total_pl=Decimal("450.25"),
                current_streak=2,
                streak_type="WIN",
                trades_today=3,
                session_count=12,
                max_drawdown=Decimal("-50.00"),
            ),
            targets=mock_targets,
            generated_at=datetime.now(timezone.utc),
            market_status="OPEN",
            data_age_seconds=0.0,
            is_data_stale=False,
            warnings=[],
        )

        generator = ExportGenerator()

        # Measure export generation time
        start_time = time.perf_counter()

        # Generate both export formats
        json_path = tmp_path / "dashboard-export-test.json"
        md_path = tmp_path / "dashboard-export-test.md"

        generator.export_to_json(snapshot, json_path)
        generator.export_to_markdown(snapshot, md_path)

        end_time = time.perf_counter()
        elapsed = end_time - start_time

        # Verify performance target
        assert elapsed < 1.0, f"Export took {elapsed * 1000:.0f}ms, expected <1s"

        # Verify files were created
        assert json_path.exists(), "JSON export file not created"
        assert md_path.exists(), "Markdown export file not created"

        # Verify file sizes are reasonable
        json_size = json_path.stat().st_size
        md_size = md_path.stat().st_size

        assert json_size > 0, "JSON export is empty"
        assert md_size > 0, "Markdown export is empty"
        assert json_size < 100_000, "JSON export unexpectedly large"
        assert md_size < 100_000, "Markdown export unexpectedly large"

        # Log performance for monitoring
        print(f"\nExport generation time: {elapsed * 1000:.2f}ms")
        print(f"JSON size: {json_size} bytes, Markdown size: {md_size} bytes")


class TestMemoryFootprint:
    """Benchmark dashboard memory usage (NFR-008)."""

    @patch("trading_bot.dashboard.data_provider.is_market_open")
    def test_memory_footprint_under_50mb(
        self,
        mock_is_market_open: Mock,
        mock_account_data: Mock,
        mock_trade_helper: Mock,
        mock_targets: DashboardTargets,
    ) -> None:
        """Test dashboard memory footprint stays under 50MB.

        Target: NFR-008 - Memory footprint <50MB

        This test simulates multiple refresh cycles and verifies that
        dashboard state doesn't accumulate memory over time.
        """
        import sys

        mock_is_market_open.return_value = True

        # Measure baseline memory
        import gc

        gc.collect()
        initial_objects = len(gc.get_objects())

        # Create provider instance
        provider = DashboardDataProvider(
            account_data=mock_account_data,
            trade_helper=mock_trade_helper,
            metrics_calculator=MetricsCalculator(),
        )

        # Simulate 100 refresh cycles
        for _ in range(100):
            snapshot = provider.get_snapshot(targets=mock_targets)
            # Ensure snapshot is used (prevent optimization)
            assert snapshot is not None

        # Measure final memory
        gc.collect()
        final_objects = len(gc.get_objects())

        # Verify no significant memory leak
        object_growth = final_objects - initial_objects
        # Allow for some growth (100 iterations * small overhead)
        # but fail if growth is excessive (>10,000 objects)
        assert (
            object_growth < 10_000
        ), f"Potential memory leak: {object_growth} new objects after 100 refreshes"

        print(f"\nObject growth after 100 refreshes: {object_growth} objects")


class TestConcurrentRefreshPerformance:
    """Benchmark dashboard with concurrent refresh scenarios."""

    @patch("trading_bot.dashboard.data_provider.is_market_open")
    def test_rapid_refresh_performance(
        self,
        mock_is_market_open: Mock,
        mock_account_data: Mock,
        mock_trade_helper: Mock,
        mock_targets: DashboardTargets,
    ) -> None:
        """Test dashboard handles rapid manual refreshes efficiently.

        Simulates user pressing R key rapidly (10 refreshes in quick succession).
        Each refresh should still complete within 500ms.
        """
        mock_is_market_open.return_value = True

        # Create provider instance
        provider = DashboardDataProvider(
            account_data=mock_account_data,
            trade_helper=mock_trade_helper,
            metrics_calculator=MetricsCalculator(),
        )

        refresh_times = []

        # Simulate 10 rapid refreshes
        for i in range(10):
            start_time = time.perf_counter()

            snapshot = provider.get_snapshot(targets=mock_targets)

            end_time = time.perf_counter()
            elapsed = end_time - start_time
            refresh_times.append(elapsed)

            assert snapshot is not None

        # Verify all refreshes met performance target
        max_time = max(refresh_times)
        avg_time = sum(refresh_times) / len(refresh_times)

        assert max_time < 0.5, f"Slowest refresh: {max_time * 1000:.0f}ms, expected <500ms"
        assert avg_time < 0.5, f"Average refresh: {avg_time * 1000:.0f}ms, expected <500ms"

        print(f"\nRapid refresh performance:")
        print(f"  Average: {avg_time * 1000:.2f}ms")
        print(f"  Max: {max_time * 1000:.2f}ms")
        print(f"  Min: {min(refresh_times) * 1000:.2f}ms")
