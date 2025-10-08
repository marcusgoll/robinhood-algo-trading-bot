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
