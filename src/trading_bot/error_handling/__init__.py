"""
Error Handling Framework

Centralized retry logic, error classification, and circuit breaker.

Constitution v1.0.0:
- §Risk_Management: Exponential backoff for API failures
- §Safety_First: Circuit breaker prevents cascade failures
- §Audit_Everything: All retry attempts logged
"""

from .exceptions import NonRetriableError, RateLimitError, RetriableError
from .policies import AGGRESSIVE_POLICY, CONSERVATIVE_POLICY, DEFAULT_POLICY, RetryPolicy
from .retry import with_retry
from .circuit_breaker import circuit_breaker

__all__ = [
    "RetriableError",
    "NonRetriableError",
    "RateLimitError",
    "RetryPolicy",
    "DEFAULT_POLICY",
    "AGGRESSIVE_POLICY",
    "CONSERVATIVE_POLICY",
    "with_retry",
    "circuit_breaker",
]
