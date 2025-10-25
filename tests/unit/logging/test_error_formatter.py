"""
Unit tests for error formatter

T023: Test error formatter creates semantic errors from exceptions

Coverage target: ≥80%

Test cases:
- test_format_exception_creates_semantic_error
- test_format_retriable_error
- test_format_non_retriable_error
- test_format_generic_exception
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock

from src.trading_bot.logging.error_formatter import format_exception
from src.trading_bot.logging.semantic_error import SemanticError, ErrorSeverity


def test_format_exception_creates_semantic_error():
    """
    T023: Test that format_exception converts Exception to SemanticError with all fields.

    Validates that all semantic fields are populated:
    - error_code
    - error_type
    - message
    - severity
    - cause
    - impact
    - remediation
    - context
    - timestamp
    """
    # Given: A generic exception
    try:
        raise ValueError("Invalid configuration value")
    except Exception as exc:
        # When: Format exception
        semantic_error = format_exception(exc)

        # Then: Verify all required fields
        assert isinstance(semantic_error, SemanticError)
        assert semantic_error.error_code is not None
        assert semantic_error.error_type == "ValueError"
        assert "Invalid configuration value" in semantic_error.message
        assert semantic_error.severity in ["critical", "error", "warning", "info"]
        assert semantic_error.cause is not None
        assert semantic_error.impact is not None
        assert semantic_error.remediation is not None
        assert isinstance(semantic_error.context, dict)
        assert isinstance(semantic_error.timestamp, datetime)


def test_format_retriable_error():
    """Test formatting RetriableError with retry context."""
    # TODO: Implement after RetriableError class is defined
    # This would test:
    # - Severity should be "warning" (retriable)
    # - Remediation should suggest "Will retry automatically"
    # - Context should include retry_count
    pytest.skip("RetriableError class not yet defined")


def test_format_non_retriable_error():
    """Test formatting NonRetriableError with critical severity."""
    # TODO: Implement after NonRetriableError class is defined
    # This would test:
    # - Severity should be "error" or "critical"
    # - Remediation should suggest manual intervention
    # - Impact should describe business consequences
    pytest.skip("NonRetriableError class not yet defined")


def test_format_generic_exception():
    """Test formatting generic Exception with sensible defaults."""
    # Given: A generic exception with no custom fields
    try:
        1 / 0
    except Exception as exc:
        # When: Format exception
        semantic_error = format_exception(exc)

        # Then: Verify sensible defaults
        assert semantic_error.error_type == "ZeroDivisionError"
        assert "division by zero" in semantic_error.message.lower()
        assert semantic_error.severity in ["error", "critical"]
        assert len(semantic_error.error_code) > 0


def test_format_exception_includes_traceback_in_context():
    """Test that traceback is included in context for debugging."""
    # Given: An exception with a traceback
    try:
        nested_function_that_fails()
    except Exception as exc:
        # When: Format exception
        semantic_error = format_exception(exc)

        # Then: Context should include traceback
        assert "traceback" in semantic_error.context
        assert isinstance(semantic_error.context["traceback"], str)
        assert len(semantic_error.context["traceback"]) > 0


def nested_function_that_fails():
    """Helper function to create nested traceback."""
    raise RuntimeError("Nested failure for testing")


def test_format_exception_extracts_error_code():
    """Test that error_code is generated consistently."""
    # Given: Two identical exceptions
    try:
        raise ValueError("Test error")
    except Exception as exc1:
        try:
            raise ValueError("Test error")
        except Exception as exc2:
            # When: Format both
            error1 = format_exception(exc1)
            error2 = format_exception(exc2)

            # Then: Error codes should follow consistent pattern
            assert error1.error_code.startswith("ERR-")
            assert error2.error_code.startswith("ERR-")
            # Note: Codes might differ due to timestamp/traceback


def test_format_exception_handles_nested_exceptions():
    """Test formatting exceptions with __cause__ chain."""
    # Given: Nested exception chain
    try:
        try:
            raise ValueError("Root cause")
        except ValueError as root:
            raise RuntimeError("Wrapper error") from root
    except Exception as exc:
        # When: Format exception
        semantic_error = format_exception(exc)

        # Then: Cause should reference root error
        assert "ValueError" in semantic_error.cause or "Root cause" in semantic_error.cause


# TODO: Add more test cases
# - Test custom exception classes with semantic fields
# - Test error severity mapping rules
# - Test impact and remediation extraction
# - Test context enrichment with environment data
