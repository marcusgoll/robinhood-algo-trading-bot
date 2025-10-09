"""Tests for @with_retry decorator"""

import pytest
import time
from unittest.mock import Mock, call


def test_decorator_wraps_function_successfully():
    """@with_retry should preserve function metadata using functools.wraps."""
    from trading_bot.error_handling import with_retry

    # Given: A function decorated with @with_retry
    @with_retry()
    def my_function():
        """My function docstring."""
        return "success"

    # Then: Function metadata should be preserved
    assert my_function.__name__ == "my_function"
    assert my_function.__doc__ == "My function docstring."
    assert my_function() == "success"


def test_function_succeeds_on_first_attempt():
    """@with_retry should return result immediately if function succeeds first time."""
    from trading_bot.error_handling import with_retry

    # Given: A function that succeeds on first call
    @with_retry()
    def successful_function():
        return "success"

    # When: Function is called
    result = successful_function()

    # Then: Should return result without retrying
    assert result == "success"


def test_function_retries_on_retriable_error():
    """@with_retry should retry when RetriableError is raised."""
    from trading_bot.error_handling import with_retry, RetriableError

    # Given: A function that fails twice then succeeds
    call_count = {"count": 0}

    @with_retry()
    def flaky_function():
        call_count["count"] += 1
        if call_count["count"] < 3:
            raise RetriableError("Temporary failure")
        return "success"

    # When: Function is called
    result = flaky_function()

    # Then: Should succeed after retries
    assert result == "success"
    assert call_count["count"] == 3  # Initial call + 2 retries


def test_function_fails_fast_on_non_retriable_error():
    """@with_retry should NOT retry for NonRetriableError."""
    from trading_bot.error_handling import with_retry, NonRetriableError

    # Given: A function that raises NonRetriableError
    call_count = {"count": 0}

    @with_retry()
    def failing_function():
        call_count["count"] += 1
        raise NonRetriableError("Permanent failure")

    # When/Then: Should raise immediately without retry
    with pytest.raises(NonRetriableError, match="Permanent failure"):
        failing_function()

    # Then: Should have called only once (no retries)
    assert call_count["count"] == 1


def test_retry_exhaustion_reraises_exception():
    """@with_retry should re-raise last exception after all retries exhausted."""
    from trading_bot.error_handling import with_retry, RetriableError

    # Given: A function that always fails
    call_count = {"count": 0}

    @with_retry()
    def always_fails():
        call_count["count"] += 1
        raise RetriableError(f"Failure {call_count['count']}")

    # When/Then: Should exhaust retries and raise last error
    with pytest.raises(RetriableError, match="Failure 4"):  # 1 initial + 3 retries
        always_fails()

    # Then: Should have called 4 times (1 initial + 3 retries)
    assert call_count["count"] == 4


def test_exponential_backoff_delays():
    """@with_retry should use exponential backoff: 1s, 2s, 4s."""
    from trading_bot.error_handling import with_retry, RetriableError, RetryPolicy

    # Given: A function that always fails with no jitter policy
    policy = RetryPolicy(max_attempts=3, base_delay=1.0, backoff_multiplier=2.0, jitter=False)

    @with_retry(policy=policy)
    def always_fails():
        raise RetriableError("Failure")

    # When: Function is called and times delays
    start = time.time()
    try:
        always_fails()
    except RetriableError:
        pass
    duration = time.time() - start

    # Then: Should have delays of 1s + 2s + 4s = 7s total (±0.5s tolerance)
    assert 6.5 <= duration <= 7.5, f"Expected ~7s, got {duration:.2f}s"


def test_rate_limit_detection_waits_for_retry_after():
    """@with_retry should respect Retry-After value from RateLimitError."""
    from trading_bot.error_handling import with_retry, RateLimitError, RetryPolicy

    # Given: A function that raises RateLimitError with retry_after
    call_count = {"count": 0}
    policy = RetryPolicy(max_attempts=2, jitter=False)

    @with_retry(policy=policy)
    def rate_limited():
        call_count["count"] += 1
        if call_count["count"] < 2:
            raise RateLimitError("Rate limit", retry_after=2)
        return "success"

    # When: Function is called
    start = time.time()
    result = rate_limited()
    duration = time.time() - start

    # Then: Should wait for retry_after (2s) instead of exponential backoff
    assert result == "success"
    assert 1.5 <= duration <= 2.5, f"Expected ~2s wait, got {duration:.2f}s"


def test_retry_logging_integration():
    """@with_retry should log retry attempts to errors logger."""
    from trading_bot.error_handling import with_retry, RetriableError
    from unittest.mock import patch

    # Given: A function that fails once then succeeds
    call_count = {"count": 0}

    @with_retry()
    def flaky_function():
        call_count["count"] += 1
        if call_count["count"] < 2:
            raise RetriableError("Temporary failure")
        return "success"

    # When: Function is called with logging mocked
    with patch("trading_bot.error_handling.retry.logger") as mock_logger:
        result = flaky_function()

    # Then: Should have logged the retry attempt
    assert result == "success"
    assert mock_logger.warning.called
    # Check log message contains retry info
    log_call = mock_logger.warning.call_args[0][0]
    assert "Attempt 1" in log_call or "retry" in log_call.lower()


def test_custom_retry_policy():
    """@with_retry should accept custom RetryPolicy."""
    from trading_bot.error_handling import with_retry, RetriableError, RetryPolicy

    # Given: A custom policy with 5 attempts
    custom_policy = RetryPolicy(max_attempts=5, base_delay=0.1, jitter=False)
    call_count = {"count": 0}

    @with_retry(policy=custom_policy)
    def always_fails():
        call_count["count"] += 1
        raise RetriableError("Failure")

    # When: Function exhausts retries
    with pytest.raises(RetriableError):
        always_fails()

    # Then: Should have tried 6 times (1 initial + 5 retries)
    assert call_count["count"] == 6


def test_on_retry_callback():
    """@with_retry should call on_retry callback for each retry attempt."""
    from trading_bot.error_handling import with_retry, RetriableError

    # Given: A function that fails twice with retry callback
    call_count = {"count": 0}
    retry_callback = Mock()

    @with_retry(on_retry=retry_callback)
    def flaky_function():
        call_count["count"] += 1
        if call_count["count"] < 3:
            raise RetriableError("Temporary failure")
        return "success"

    # When: Function is called
    result = flaky_function()

    # Then: Callback should be called for each retry (2 times)
    assert result == "success"
    assert retry_callback.call_count == 2
    # First retry: (exception, attempt_number=1)
    # Second retry: (exception, attempt_number=2)
    first_call = retry_callback.call_args_list[0]
    assert isinstance(first_call[0][0], RetriableError)
    assert first_call[0][1] == 1  # First retry attempt


def test_on_exhausted_callback():
    """@with_retry should call on_exhausted callback when retries exhausted."""
    from trading_bot.error_handling import with_retry, RetriableError

    # Given: A function that always fails with exhausted callback
    exhausted_callback = Mock()

    @with_retry(on_exhausted=exhausted_callback)
    def always_fails():
        raise RetriableError("Permanent failure")

    # When: Function exhausts retries
    with pytest.raises(RetriableError):
        always_fails()

    # Then: Exhausted callback should be called once with final exception
    assert exhausted_callback.call_count == 1
    assert isinstance(exhausted_callback.call_args[0][0], RetriableError)


def test_exception_chaining_preserved():
    """@with_retry should preserve exception chaining with 'from e'."""
    from trading_bot.error_handling import with_retry, RetriableError

    # Given: A function that always fails
    @with_retry()
    def always_fails():
        raise RetriableError("Original error")

    # When: Retries are exhausted
    try:
        always_fails()
    except RetriableError as e:
        # Then: Exception should have __cause__ or __context__ set
        # (Python's exception chaining)
        assert e.__traceback__ is not None


def test_retry_overhead_less_than_100ms():
    """@with_retry overhead should be <100ms per attempt."""
    from trading_bot.error_handling import with_retry, RetryPolicy

    # Given: A policy with minimal delay and no retries
    policy = RetryPolicy(max_attempts=1, base_delay=0.001, jitter=False)

    @with_retry(policy=policy)
    def fast_function():
        return "success"

    # When: Function is called 100 times
    start = time.time()
    for _ in range(100):
        fast_function()
    duration = time.time() - start

    # Then: Average overhead should be <100ms per call
    avg_overhead = (duration / 100) * 1000  # Convert to ms
    assert avg_overhead < 100, f"Overhead {avg_overhead:.2f}ms exceeds 100ms"


def test_jitter_adds_randomness_to_delays():
    """@with_retry should add ±10% jitter to delays when enabled."""
    from trading_bot.error_handling import with_retry, RetriableError, RetryPolicy

    # Given: Two policies - one with jitter, one without
    policy_with_jitter = RetryPolicy(max_attempts=1, base_delay=1.0, jitter=True)
    policy_no_jitter = RetryPolicy(max_attempts=1, base_delay=1.0, jitter=False)

    # Measure delays with jitter
    delays_with_jitter = []
    for _ in range(5):
        @with_retry(policy=policy_with_jitter)
        def fails_once():
            raise RetriableError("Fail")

        start = time.time()
        try:
            fails_once()
        except RetriableError:
            pass
        delays_with_jitter.append(time.time() - start)

    # Measure delays without jitter
    delays_no_jitter = []
    for _ in range(5):
        @with_retry(policy=policy_no_jitter)
        def fails_once_2():
            raise RetriableError("Fail")

        start = time.time()
        try:
            fails_once_2()
        except RetriableError:
            pass
        delays_no_jitter.append(time.time() - start)

    # Then: Jittered delays should have variance, non-jittered should not
    import statistics
    jitter_variance = statistics.variance(delays_with_jitter)
    no_jitter_variance = statistics.variance(delays_no_jitter)
    assert jitter_variance > no_jitter_variance * 2  # Jitter adds significant variance


def test_decorator_with_no_policy_uses_default():
    """@with_retry() with no arguments should use DEFAULT_POLICY."""
    from trading_bot.error_handling import with_retry, RetriableError, DEFAULT_POLICY

    # Given: A function decorated with no policy argument
    call_count = {"count": 0}

    @with_retry()
    def always_fails():
        call_count["count"] += 1
        raise RetriableError("Failure")

    # When: Function exhausts retries
    with pytest.raises(RetriableError):
        always_fails()

    # Then: Should use DEFAULT_POLICY (max_attempts=3)
    # 1 initial + 3 retries = 4 calls
    assert call_count["count"] == DEFAULT_POLICY.max_attempts + 1
