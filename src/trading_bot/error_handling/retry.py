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

import time
import random
import logging
from functools import wraps
from typing import Any, Callable, Optional, TypeVar

from .policies import RetryPolicy, DEFAULT_POLICY
from .exceptions import RateLimitError

# Module logger
logger = logging.getLogger(__name__)

T = TypeVar("T")


def with_retry(
    policy: Optional[RetryPolicy] = None,
    on_retry: Optional[Callable[[Exception, int], None]] = None,
    on_exhausted: Optional[Callable[[Exception], None]] = None,
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

            # max_attempts is number of retries, so total calls = max_attempts + 1
            for attempt in range(policy.max_attempts + 1):
                try:
                    # Call the original function
                    result = func(*args, **kwargs)
                    return result

                except Exception as e:
                    last_exception = e

                    # Check if this exception type should be retried
                    should_retry = isinstance(e, policy.retriable_exceptions)

                    if not should_retry:
                        # Non-retriable error - raise immediately
                        raise

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
                                delay += random.uniform(-jitter_amount, jitter_amount)

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

        return wrapper

    return decorator
