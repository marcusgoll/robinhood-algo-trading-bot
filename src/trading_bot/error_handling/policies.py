"""
Retry policy configuration.

Defines retry behavior for the @with_retry decorator:
- max_attempts: Number of retry attempts (not including initial call)
- base_delay: Base delay in seconds for exponential backoff
- backoff_multiplier: Multiplier for exponential backoff
- jitter: Add ±10% randomness to delays
- retriable_exceptions: Tuple of exception types that trigger retry
"""

from dataclasses import dataclass
from typing import Tuple, Type


@dataclass
class RetryPolicy:
    """
    Configuration dataclass for retry behavior.

    Attributes:
        max_attempts: Maximum number of retry attempts (default: 3)
        base_delay: Base delay in seconds for exponential backoff (default: 1.0)
        backoff_multiplier: Multiplier for exponential backoff (default: 2.0)
        jitter: Add ±10% randomness to prevent thundering herd (default: True)
        retriable_exceptions: Tuple of exception types that should trigger retry

    Example:
        custom_policy = RetryPolicy(
            max_attempts=5,
            base_delay=2.0,
            backoff_multiplier=3.0,
            jitter=False
        )

    Validation:
        - max_attempts must be > 0
        - base_delay must be > 0
        - backoff_multiplier must be >= 1.0
    """

    max_attempts: int = 3
    base_delay: float = 1.0
    backoff_multiplier: float = 2.0
    jitter: bool = True
    retriable_exceptions: Tuple[Type[Exception], ...] | None = None

    def __post_init__(self) -> None:
        """Validate policy configuration after initialization."""
        # Import here to avoid circular dependency
        from .exceptions import RetriableError

        # Set default retriable_exceptions if not provided
        if self.retriable_exceptions is None:
            self.retriable_exceptions = (RetriableError,)

        # Validate max_attempts
        if self.max_attempts <= 0:
            raise ValueError("max_attempts must be greater than 0")

        # Validate base_delay
        if self.base_delay <= 0:
            raise ValueError("base_delay must be greater than 0")

        # Validate backoff_multiplier
        if self.backoff_multiplier < 1.0:
            raise ValueError("backoff_multiplier must be >= 1.0")


# Predefined retry policies

DEFAULT_POLICY = RetryPolicy(
    max_attempts=3,
    base_delay=1.0,
    backoff_multiplier=2.0,
    jitter=True,
)
"""Default retry policy: 3 attempts, 1s/2s/4s delays (with jitter)"""

AGGRESSIVE_POLICY = RetryPolicy(
    max_attempts=5,
    base_delay=1.0,
    backoff_multiplier=2.0,
    jitter=True,
)
"""Aggressive retry policy: 5 attempts, 1s/2s/4s/8s/16s delays (with jitter)"""

CONSERVATIVE_POLICY = RetryPolicy(
    max_attempts=1,
    base_delay=1.0,
    backoff_multiplier=2.0,
    jitter=False,
)
"""Conservative retry policy: 1 attempt only (effectively no retry)"""
