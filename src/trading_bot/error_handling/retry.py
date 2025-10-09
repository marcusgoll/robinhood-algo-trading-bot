"""
Retry decorator with exponential backoff.

Provides @with_retry decorator for adding retry logic to functions.
Supports:
- Exponential backoff with jitter
- Configurable retry policies
- Rate limit detection (HTTP 429)
- Retry/exhausted callbacks
- Logging integration
"""

import logging
import random
import time
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from .circuit_breaker import circuit_breaker
from .exceptions import RateLimitError
from .policies import DEFAULT_POLICY, RetryPolicy

# Module logger
logger = logging.getLogger(__name__)

T = TypeVar("T")


def with_retry(
    policy: RetryPolicy | None = None,
    on_retry: Callable[[Exception, int], None] | None = None,
    on_exhausted: Callable[[Exception], None] | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to add exponential backoff retry logic to a function.

    Args:
        policy: RetryPolicy configuration (default: DEFAULT_POLICY)
        on_retry: Callback called on each retry: on_retry(exception, attempt_number)
        on_exhausted: Callback called when all retries exhausted: on_exhausted(exception)

    Returns:
        Decorated function with retry logic

    Raises:
        Re-raises last exception after all retries exhausted

    Example:
        @with_retry()
        def fetch_data():
            # May raise RetriableError
            return api.get("/data")

        @with_retry(policy=AGGRESSIVE_POLICY)
        def critical_operation():
            # Retries 5 times instead of default 3
            return api.post("/critical")

    Performance: <100ms overhead per retry attempt
    """
    # Use default policy if none provided
    if policy is None:
        policy = DEFAULT_POLICY

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)  # Preserve function metadata
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Exception | None = None

            # Ensure retriable_exceptions is not None (should be set by __post_init__)
            if policy.retriable_exceptions is None:  # noqa: S101
                raise ValueError("retriable_exceptions must be set in RetryPolicy")

            # max_attempts is number of retries, so total calls = max_attempts + 1
            for attempt in range(policy.max_attempts + 1):
                try:
                    # Call the original function
                    result = func(*args, **kwargs)

                    # Record success with circuit breaker
                    circuit_breaker.record_success()

                    return result

                except Exception as e:
                    last_exception = e

                    # Check if this exception type should be retried
                    should_retry = isinstance(e, policy.retriable_exceptions)

                    if not should_retry:
                        # Non-retriable error - raise immediately
                        raise

                    # Record failure with circuit breaker (only for retriable errors)
                    circuit_breaker.record_failure()

                    # Check if we have more attempts left
                    if attempt < policy.max_attempts:
                        # Calculate delay
                        delay: float
                        if isinstance(e, RateLimitError) and hasattr(e, "retry_after"):
                            # Use retry_after from RateLimitError
                            delay = float(e.retry_after)
                        else:
                            # Exponential backoff: base_delay * (multiplier ^ attempt)
                            delay = policy.base_delay * (policy.backoff_multiplier ** attempt)

                            # Add jitter (±10% randomness)
                            if policy.jitter:
                                jitter_amount = delay * 0.1
                                delay += random.uniform(-jitter_amount, jitter_amount)  # noqa: S311

                        # Log retry attempt
                        logger.warning(
                            f"Attempt {attempt + 1}/{policy.max_attempts + 1} failed: {e}. "
                            f"Retrying in {delay:.2f}s..."
                        )

                        # Call on_retry callback if provided
                        if on_retry:
                            on_retry(e, attempt + 1)

                        # Sleep before retry
                        time.sleep(delay)
                    else:
                        # All retries exhausted
                        logger.error(
                            f"All {policy.max_attempts + 1} attempts failed. "
                            f"Last error: {e}"
                        )

                        # Call on_exhausted callback if provided
                        if on_exhausted:
                            on_exhausted(e)

            # Re-raise last exception with chaining
            if last_exception:
                raise last_exception

            # This should never happen (last_exception should always be set if we get here)
            raise RuntimeError("Unexpected: no exception was raised during retry attempts")

        return wrapper

    return decorator
