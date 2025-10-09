"""
Exception classes for error handling framework.

Defines error hierarchy for retry decision logic:
- RetriableError: Errors that should trigger retry (network, 5xx, 429)
- NonRetriableError: Errors that should fail fast (4xx client errors)
- RateLimitError: Specific retriable error for HTTP 429 rate limiting
"""


class RetriableError(Exception):
    """
    Base exception for errors that should trigger retry logic.

    Use cases:
    - Network errors (connection timeout, DNS failure)
    - Temporary server errors (5xx status codes)
    - Rate limiting (HTTP 429)
    - Transient database errors

    Example:
        raise RetriableError("Network timeout - connection failed")
    """

    pass


class NonRetriableError(Exception):
    """
    Base exception for errors that should fail fast (no retry).

    Use cases:
    - Client errors (4xx status codes except 429)
    - Validation errors (bad input)
    - Authentication failures (401, 403)
    - Resource not found (404)

    Example:
        raise NonRetriableError("Bad request - invalid parameters")
    """

    pass


class RateLimitError(RetriableError):
    """
    Specific exception for HTTP 429 rate limiting.

    Inherits from RetriableError to trigger retry logic.
    Stores retry_after value from Retry-After header.

    Args:
        message: Error message
        retry_after: Seconds to wait before retry (from Retry-After header)

    Example:
        raise RateLimitError("Rate limit exceeded", retry_after=60)
    """

    def __init__(self, message: str, retry_after: int = 60):
        super().__init__(message)
        self.retry_after = retry_after
