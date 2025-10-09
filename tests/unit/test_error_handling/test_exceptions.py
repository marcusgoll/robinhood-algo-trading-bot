"""Tests for error_handling exception classes"""

import pytest


def test_retriable_error_can_be_raised_and_caught():
    """RetriableError should be raisable and catchable as an exception."""
    from trading_bot.error_handling import RetriableError

    # Given: A function that raises RetriableError
    def raises_retriable():
        raise RetriableError("Network timeout")

    # When/Then: Error can be caught
    with pytest.raises(RetriableError) as exc_info:
        raises_retriable()

    # Then: Error message is preserved
    assert str(exc_info.value) == "Network timeout"
    assert isinstance(exc_info.value, Exception)


def test_non_retriable_error_can_be_raised_and_caught():
    """NonRetriableError should be raisable and catchable as an exception."""
    from trading_bot.error_handling import NonRetriableError

    # Given: A function that raises NonRetriableError
    def raises_non_retriable():
        raise NonRetriableError("Bad request - invalid parameters")

    # When/Then: Error can be caught
    with pytest.raises(NonRetriableError) as exc_info:
        raises_non_retriable()

    # Then: Error message is preserved
    assert str(exc_info.value) == "Bad request - invalid parameters"
    assert isinstance(exc_info.value, Exception)


def test_rate_limit_error_stores_retry_after_value():
    """RateLimitError should store retry_after value from HTTP 429."""
    from trading_bot.error_handling import RateLimitError

    # Given: Rate limit error with retry_after value
    error = RateLimitError("Rate limit exceeded", retry_after=60)

    # Then: retry_after value is accessible
    assert error.retry_after == 60
    assert str(error) == "Rate limit exceeded"


def test_rate_limit_error_inherits_from_retriable():
    """RateLimitError should inherit from RetriableError for retry logic."""
    from trading_bot.error_handling import RateLimitError, RetriableError

    # Given: A RateLimitError instance
    error = RateLimitError("Rate limit", retry_after=30)

    # Then: It should be an instance of RetriableError
    assert isinstance(error, RetriableError)
    assert isinstance(error, Exception)


def test_existing_custom_errors_can_inherit_from_framework():
    """Existing custom errors should be able to inherit from framework base classes."""
    from trading_bot.error_handling import RetriableError, NonRetriableError

    # Given: Custom error classes that inherit from framework
    class CustomRetriableError(RetriableError):
        """Custom error for retriable scenarios"""
        pass

    class CustomNonRetriableError(NonRetriableError):
        """Custom error for non-retriable scenarios"""
        pass

    # When: Errors are raised
    retriable_error = CustomRetriableError("Temporary failure")
    non_retriable_error = CustomNonRetriableError("Permanent failure")

    # Then: They inherit correctly
    assert isinstance(retriable_error, RetriableError)
    assert isinstance(non_retriable_error, NonRetriableError)
    assert str(retriable_error) == "Temporary failure"
    assert str(non_retriable_error) == "Permanent failure"
