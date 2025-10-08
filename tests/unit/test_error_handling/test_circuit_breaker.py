"""Tests for CircuitBreaker (graceful shutdown logic)"""

import pytest
import time


def test_circuit_breaker_records_failures():
    """CircuitBreaker should record failure timestamps in sliding window."""
    from trading_bot.error_handling import circuit_breaker

    # Given: Circuit breaker with clean state
    circuit_breaker._failures.clear()

    # When: Failures are recorded
    circuit_breaker.record_failure()
    circuit_breaker.record_failure()
    circuit_breaker.record_failure()

    # Then: Should have 3 failures recorded
    assert len(circuit_breaker._failures) == 3


def test_circuit_breaker_trips_at_threshold():
    """CircuitBreaker should trip when failures reach threshold (5 in 60s)."""
    from trading_bot.error_handling import circuit_breaker

    # Given: Circuit breaker with clean state
    circuit_breaker._failures.clear()

    # When: 4 failures recorded (below threshold)
    for _ in range(4):
        circuit_breaker.record_failure()

    # Then: Should NOT trip
    assert circuit_breaker.should_trip() is False

    # When: 5th failure recorded (at threshold)
    circuit_breaker.record_failure()

    # Then: Should trip
    assert circuit_breaker.should_trip() is True


def test_circuit_breaker_resets_on_success():
    """CircuitBreaker should clear failures on successful operation."""
    from trading_bot.error_handling import circuit_breaker

    # Given: Circuit breaker with failures
    circuit_breaker._failures.clear()
    for _ in range(3):
        circuit_breaker.record_failure()

    # When: Success is recorded
    circuit_breaker.record_success()

    # Then: Failures should be cleared
    assert len(circuit_breaker._failures) == 0
    assert circuit_breaker.should_trip() is False


def test_circuit_breaker_sliding_window_expiry():
    """CircuitBreaker should only count failures within 60s window."""
    from trading_bot.error_handling import circuit_breaker

    # Given: Circuit breaker with clean state
    circuit_breaker._failures.clear()

    # When: Old failures recorded (simulate by manipulating timestamps)
    # Record 5 failures but make them old
    import time
    old_time = time.time() - 65  # 65 seconds ago (outside 60s window)
    for _ in range(5):
        circuit_breaker._failures.append(old_time)

    # Then: Should NOT trip (failures expired)
    assert circuit_breaker.should_trip() is False

    # When: New failure added
    circuit_breaker.record_failure()

    # Then: Should still NOT trip (only 1 failure in window)
    assert circuit_breaker.should_trip() is False
