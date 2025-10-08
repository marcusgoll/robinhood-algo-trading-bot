"""
Circuit breaker for graceful shutdown on consecutive errors.

Tracks API failures in a sliding window and triggers shutdown
when error threshold is exceeded.

Configuration:
- Threshold: 5 errors
- Window: 60 seconds (sliding)

Constitution v1.0.0:
- §Safety_First: Circuit breaker prevents cascade failures
"""

import time
from collections import deque
from typing import Deque


class CircuitBreaker:
    """
    Circuit breaker to prevent cascade failures.

    Tracks consecutive errors in a sliding 60-second window.
    Triggers graceful shutdown when >= 5 errors occur within window.

    Thread-safe for single-threaded bot (no locks needed).

    Example:
        from trading_bot.error_handling import circuit_breaker

        def api_call():
            try:
                result = external_api.fetch()
                circuit_breaker.record_success()
                return result
            except Exception as e:
                circuit_breaker.record_failure()
                if circuit_breaker.should_trip():
                    logger.critical("Circuit breaker tripped - shutting down")
                    sys.exit(1)
                raise
    """

    def __init__(self, threshold: int = 5, window_seconds: int = 60):
        """
        Initialize circuit breaker.

        Args:
            threshold: Number of errors to trigger shutdown (default: 5)
            window_seconds: Time window in seconds (default: 60)
        """
        self.threshold = threshold
        self.window_seconds = window_seconds
        self._failures: Deque[float] = deque()

    def record_failure(self) -> None:
        """
        Record an API failure with current timestamp.

        Adds timestamp to sliding window for tracking.
        """
        self._failures.append(time.time())

    def record_success(self) -> None:
        """
        Record an API success.

        Clears all failures (resets circuit breaker on successful operation).
        """
        self._failures.clear()

    def should_trip(self) -> bool:
        """
        Check if circuit breaker should trip (trigger shutdown).

        Returns:
            True if >= threshold errors in window, False otherwise

        Implementation:
            - Filter out failures older than window_seconds
            - Count remaining failures
            - Trip if count >= threshold
        """
        # Get current time
        now = time.time()

        # Filter out expired failures (older than window)
        cutoff_time = now - self.window_seconds

        # Remove old failures from left side of deque
        while self._failures and self._failures[0] < cutoff_time:
            self._failures.popleft()

        # Check if remaining failures >= threshold
        return len(self._failures) >= self.threshold


# Singleton instance (module-level)
circuit_breaker = CircuitBreaker(threshold=5, window_seconds=60)
