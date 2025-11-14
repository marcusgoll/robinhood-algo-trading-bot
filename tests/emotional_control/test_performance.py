"""
Performance Tests for Emotional Control

Tests: T030 - Performance benchmarks for NFR validation

Constitution v1.0.0:
- §Testing_Requirements: Performance tests verify NFR targets
"""

import time
import pytest
from decimal import Decimal
from statistics import quantiles

from src.trading_bot.emotional_control.tracker import EmotionalControl
from src.trading_bot.emotional_control.config import EmotionalControlConfig


class TestPerformance:
    """Performance benchmarks for EmotionalControl (T030)."""

    def test_update_state_executes_under_10ms_p95(self, tmp_path):
        """Test update_state() P95 latency <10ms (AC-018, NFR-001)."""
        # Given: Emotional control tracker
        config = EmotionalControlConfig.default()
        tracker = EmotionalControl(config, state_file=tmp_path / "state.json", log_dir=tmp_path)

        # When: Running 100 iterations
        latencies = []
        for i in range(100):
            start = time.perf_counter()
            tracker.update_state(
                trade_pnl=Decimal("-100"),
                account_balance=Decimal("100000"),
                is_win=(i % 2 == 0),  # Alternate wins/losses
            )
            end = time.perf_counter()
            latencies.append((end - start) * 1000)  # Convert to ms

        # Calculate P95 latency
        p95_latency = quantiles(latencies, n=20)[18]  # 95th percentile

        # Then: P95 latency < 10ms
        assert p95_latency < 10.0, f"P95 latency {p95_latency:.2f}ms exceeds 10ms target"

    def test_get_position_multiplier_executes_under_1ms(self, tmp_path):
        """Test get_position_multiplier() executes in <1ms (in-memory lookup)."""
        # Given: Emotional control tracker
        config = EmotionalControlConfig.default()
        tracker = EmotionalControl(config, state_file=tmp_path / "state.json", log_dir=tmp_path)

        # When: Running 1000 iterations (in-memory lookups)
        latencies = []
        for _ in range(1000):
            start = time.perf_counter()
            _ = tracker.get_position_multiplier()
            end = time.perf_counter()
            latencies.append((end - start) * 1000)  # Convert to ms

        # Calculate average latency
        avg_latency = sum(latencies) / len(latencies)

        # Then: Average latency < 1ms
        assert avg_latency < 1.0, f"Average latency {avg_latency:.4f}ms exceeds 1ms target"
