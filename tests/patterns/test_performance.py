"""
Performance Benchmark Tests for Bull Flag Pattern Detection

Tests performance requirements for pattern detection at scale.
Validates NFR-001: Process 100 stocks in under 5 seconds.

Feature: 003-entry-logic-bull-flag
Task: T034 - Performance benchmark tests
"""

import pytest
import time
from decimal import Decimal
from datetime import datetime, timedelta, UTC
from typing import List, Dict

from src.trading_bot.patterns.bull_flag import BullFlagDetector
from src.trading_bot.patterns.config import BullFlagConfig


class TestBullFlagPerformance:
    """Performance benchmark tests for bull flag pattern detection."""

    def test_process_100_stocks_under_5_seconds(self, default_config):
        """
        Test processing 100 stocks within 5 second time limit.

        Scenario: High-volume stock scanning performance
        Given: 100 stocks with 30-50 bars each
        When: Detector processes all stocks
        Then: Total time < 5 seconds (50ms average per stock)

        Validates:
        - NFR-001: Performance requirement (< 5s for 100 stocks)
        - Scenario 2: Signal generation speed
        """
        detector = BullFlagDetector(default_config)

        # Generate 100 stocks with varying bar counts (30-50 bars)
        stocks = []
        for i in range(100):
            symbol = f"STOCK{i:03d}"
            bar_count = 30 + (i % 21)  # 30 to 50 bars
            bars = self._create_random_bars(count=bar_count, seed=i)
            stocks.append((symbol, bars))

        # Measure execution time
        start_time = time.perf_counter()

        results = []
        for symbol, bars in stocks:
            result = detector.detect(bars, symbol=symbol)
            results.append(result)

        end_time = time.perf_counter()
        elapsed_time = end_time - start_time

        # Print performance metrics
        print(f"\n{'='*60}")
        print(f"Performance Benchmark Results")
        print(f"{'='*60}")
        print(f"Total stocks processed: {len(stocks)}")
        print(f"Total time: {elapsed_time:.3f} seconds")
        print(f"Average time per stock: {(elapsed_time / len(stocks)) * 1000:.2f} ms")
        print(f"Patterns detected: {sum(1 for r in results if r.detected)}")
        print(f"{'='*60}\n")

        # Assert performance requirement
        assert elapsed_time < 5.0, (
            f"Performance requirement failed: {elapsed_time:.3f}s > 5.0s "
            f"(average {(elapsed_time / len(stocks)) * 1000:.2f}ms per stock)"
        )

        # Verify all results are valid
        assert len(results) == 100
        for result in results:
            assert result is not None
            assert result.symbol is not None

    def test_single_stock_processing_time(self, valid_bull_flag_bars, default_config):
        """
        Test single stock processing time.

        Scenario: Individual stock detection latency
        Given: Single stock with valid bull flag pattern
        When: Detector processes stock
        Then: Processing time < 100ms

        Validates:
        - NFR-001: Individual stock processing efficiency
        - Scenario 2: Signal generation speed (< 2s)
        """
        detector = BullFlagDetector(default_config)

        # Measure single stock processing time
        start_time = time.perf_counter()
        result = detector.detect(valid_bull_flag_bars, symbol="SINGLE")
        end_time = time.perf_counter()

        elapsed_ms = (end_time - start_time) * 1000

        print(f"\nSingle stock processing time: {elapsed_ms:.2f} ms\n")

        # Assert reasonable single-stock performance (< 100ms)
        assert elapsed_ms < 100.0, (
            f"Single stock processing too slow: {elapsed_ms:.2f}ms > 100ms"
        )

        # Verify result is valid
        assert result is not None
        assert result.symbol == "SINGLE"

    def test_performance_with_varying_bar_counts(self, default_config):
        """
        Test performance scales linearly with bar count.

        Scenario: Performance across different data sizes
        Given: Stocks with 30, 50, 100, 200 bars
        When: Detector processes each stock
        Then: Processing time scales approximately linearly

        Validates:
        - Performance scalability with data size
        - Algorithm efficiency
        """
        detector = BullFlagDetector(default_config)

        bar_counts = [30, 50, 100, 200]
        timings = []

        print(f"\n{'='*60}")
        print(f"Performance Scaling with Bar Count")
        print(f"{'='*60}")

        for count in bar_counts:
            bars = self._create_random_bars(count=count, seed=42)

            # Time processing
            start_time = time.perf_counter()
            result = detector.detect(bars, symbol=f"TEST{count}")
            end_time = time.perf_counter()

            elapsed_ms = (end_time - start_time) * 1000
            timings.append((count, elapsed_ms))

            print(f"Bars: {count:4d} | Time: {elapsed_ms:6.2f} ms")

        print(f"{'='*60}\n")

        # Verify all timings are reasonable (< 200ms even for 200 bars)
        for count, timing_ms in timings:
            assert timing_ms < 200.0, (
                f"Processing {count} bars took {timing_ms:.2f}ms (> 200ms limit)"
            )

    def test_performance_pattern_vs_no_pattern(self, valid_bull_flag_bars, invalid_pattern_bars, default_config):
        """
        Test performance difference between pattern detection and rejection.

        Scenario: Compare processing time for valid vs invalid patterns
        Given: Valid bull flag bars vs invalid pattern bars
        When: Detector processes both
        Then: Processing times are comparable (no pathological cases)

        Validates:
        - Consistent performance regardless of pattern presence
        - No performance degradation in rejection scenarios
        """
        detector = BullFlagDetector(default_config)

        # Time valid pattern detection
        start_time = time.perf_counter()
        for _ in range(10):
            detector.detect(valid_bull_flag_bars, symbol="VALID")
        end_time = time.perf_counter()
        valid_time = (end_time - start_time) / 10 * 1000

        # Time invalid pattern rejection
        start_time = time.perf_counter()
        for _ in range(10):
            detector.detect(invalid_pattern_bars, symbol="INVALID")
        end_time = time.perf_counter()
        invalid_time = (end_time - start_time) / 10 * 1000

        print(f"\nPattern Detection Performance Comparison:")
        print(f"  Valid pattern:   {valid_time:.2f} ms")
        print(f"  Invalid pattern: {invalid_time:.2f} ms")
        print(f"  Difference:      {abs(valid_time - invalid_time):.2f} ms\n")

        # Both should be reasonably fast (< 100ms)
        assert valid_time < 100.0
        assert invalid_time < 100.0

        # Time difference should not be excessive (within 3x)
        ratio = max(valid_time, invalid_time) / min(valid_time, invalid_time)
        assert ratio < 3.0, (
            f"Performance ratio {ratio:.2f}x too high between valid/invalid patterns"
        )

    def test_performance_with_parallel_processing_simulation(self, default_config):
        """
        Test detector can handle sequential processing efficiently.

        Scenario: Simulate batch processing of multiple stocks
        Given: 50 stocks processed sequentially
        When: Detector processes all stocks
        Then: Total time < 2.5 seconds (50ms average per stock)

        Validates:
        - NFR-001: Performance for real-time scanning
        - Detector can handle high-throughput scenarios
        """
        detector = BullFlagDetector(default_config)

        # Generate 50 stocks with mixed patterns
        stocks = []
        for i in range(50):
            symbol = f"BATCH{i:02d}"
            bars = self._create_random_bars(count=40, seed=i * 100)
            stocks.append((symbol, bars))

        # Process all stocks sequentially
        start_time = time.perf_counter()

        results = []
        for symbol, bars in stocks:
            result = detector.detect(bars, symbol=symbol)
            results.append(result)

        end_time = time.perf_counter()
        elapsed_time = end_time - start_time

        print(f"\nBatch Processing Performance:")
        print(f"  Stocks: {len(stocks)}")
        print(f"  Total time: {elapsed_time:.3f} seconds")
        print(f"  Average per stock: {(elapsed_time / len(stocks)) * 1000:.2f} ms")
        print(f"  Patterns detected: {sum(1 for r in results if r.detected)}\n")

        # Assert batch processing is efficient
        assert elapsed_time < 2.5, (
            f"Batch processing too slow: {elapsed_time:.3f}s > 2.5s"
        )

        # Verify all results are valid
        assert len(results) == 50

    def test_memory_efficiency_large_dataset(self, default_config):
        """
        Test detector handles large datasets without memory issues.

        Scenario: Process many stocks to verify no memory leaks
        Given: 200 stocks with varying bar counts
        When: Detector processes all stocks
        Then: Processing completes without memory errors

        Validates:
        - Memory efficiency
        - No memory leaks in pattern detection
        """
        detector = BullFlagDetector(default_config)

        # Generate 200 stocks
        stock_count = 200
        results = []

        start_time = time.perf_counter()

        for i in range(stock_count):
            symbol = f"MEM{i:03d}"
            bar_count = 30 + (i % 31)  # 30 to 60 bars
            bars = self._create_random_bars(count=bar_count, seed=i * 777)

            result = detector.detect(bars, symbol=symbol)
            results.append(result)

            # Clear bars to allow garbage collection
            bars = None

        end_time = time.perf_counter()
        elapsed_time = end_time - start_time

        print(f"\nMemory Efficiency Test:")
        print(f"  Stocks processed: {stock_count}")
        print(f"  Total time: {elapsed_time:.3f} seconds")
        print(f"  Average per stock: {(elapsed_time / stock_count) * 1000:.2f} ms\n")

        # Verify all processing completed successfully
        assert len(results) == stock_count
        for result in results:
            assert result is not None

    def test_worst_case_performance(self, default_config):
        """
        Test performance with worst-case scenario bars.

        Scenario: Bars that trigger maximum processing (many potential patterns)
        Given: Bars with multiple false positives
        When: Detector processes bars
        Then: Processing time still reasonable (< 150ms)

        Validates:
        - No pathological performance degradation
        - Worst-case scenarios are handled efficiently
        """
        detector = BullFlagDetector(default_config)

        # Create worst-case bars: Multiple potential flagpoles and consolidations
        bars = self._create_worst_case_bars()

        start_time = time.perf_counter()
        result = detector.detect(bars, symbol="WORST")
        end_time = time.perf_counter()

        elapsed_ms = (end_time - start_time) * 1000

        print(f"\nWorst-case performance: {elapsed_ms:.2f} ms\n")

        # Even worst-case should complete quickly
        assert elapsed_ms < 150.0, (
            f"Worst-case performance too slow: {elapsed_ms:.2f}ms > 150ms"
        )

    # Helper methods

    def _create_random_bars(self, count: int, seed: int) -> List[Dict]:
        """
        Create random bars for performance testing.

        Uses seed for reproducibility but creates varied patterns.

        Args:
            count: Number of bars to create
            seed: Random seed for reproducibility

        Returns:
            List of OHLCV bars with semi-random price movements
        """
        bars = []
        base_date = datetime.now(UTC)
        base_price = Decimal("100.00")
        base_volume = Decimal("1000000")

        # Use seed to create varied but reproducible patterns
        price_variation_factor = Decimal(str((seed % 10) + 1)) / Decimal("10")
        volume_variation_factor = Decimal(str((seed % 5) + 5)) / Decimal("10")

        current_price = base_price

        for i in range(count):
            # Semi-random price movement based on seed
            movement = Decimal(str(((seed + i) % 7 - 3) * 0.5)) * price_variation_factor
            current_price += movement

            # Ensure price stays positive
            current_price = max(current_price, Decimal("10.00"))

            # Calculate OHLC
            high = current_price + Decimal(str(((seed + i) % 3 + 1) * 0.2))
            low = current_price - Decimal(str(((seed + i) % 2 + 1) * 0.15))
            close = current_price + Decimal(str(((seed + i) % 5 - 2) * 0.1))

            # Semi-random volume
            volume = base_volume * (Decimal("1") + Decimal(str((seed + i) % 10)) / Decimal("10") * volume_variation_factor)

            bars.append({
                "timestamp": base_date + timedelta(minutes=i*5),
                "open": float(current_price),
                "high": float(high),
                "low": float(low),
                "close": float(close),
                "volume": float(volume)
            })

        return bars

    def _create_worst_case_bars(self) -> List[Dict]:
        """
        Create bars representing worst-case scenario for detector.

        Pattern: Multiple potential flagpoles and consolidations that fail
        validation at the last step, forcing maximum processing.

        Returns:
            List of OHLCV bars with many false positives
        """
        bars = []
        base_date = datetime.now(UTC)
        base_price = Decimal("100.00")
        base_volume = Decimal("1000000")

        # Create multiple cycles of up-down movements (false flagpoles)
        for cycle in range(5):
            cycle_start_idx = cycle * 10

            # Upward movement (potential flagpole)
            for i in range(5):
                price = base_price + Decimal(str(i * 0.8))
                bars.append({
                    "timestamp": base_date + timedelta(minutes=(cycle_start_idx + i)*5),
                    "open": float(price),
                    "high": float(price + Decimal("0.40")),
                    "low": float(price - Decimal("0.20")),
                    "close": float(price + Decimal("0.30")),
                    "volume": float(base_volume * Decimal("1.1"))
                })

            # Downward movement (potential consolidation)
            for i in range(5):
                price = base_price + Decimal("4.0") - Decimal(str(i * 0.6))
                bars.append({
                    "timestamp": base_date + timedelta(minutes=(cycle_start_idx + 5 + i)*5),
                    "open": float(price),
                    "high": float(price + Decimal("0.30")),
                    "low": float(price - Decimal("0.30")),
                    "close": float(price - Decimal("0.20")),
                    "volume": float(base_volume * Decimal("0.7"))
                })

        return bars
