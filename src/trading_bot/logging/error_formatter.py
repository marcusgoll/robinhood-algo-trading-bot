"""Error formatter for converting exceptions to semantic error format.

This module provides utilities for converting Python exceptions into structured
SemanticError objects with LLM-friendly context (cause, impact, remediation).
"""

import traceback
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from .semantic_error import SemanticError


def format_exception(
    exc: Exception,
    context: Optional[Dict[str, Any]] = None
) -> SemanticError:
    """Convert an exception to a SemanticError with LLM-friendly fields.

    Args:
        exc: The exception to format
        context: Additional context dict (e.g., symbol, position_id)

    Returns:
        SemanticError with cause, impact, and remediation fields populated

    Examples:
        >>> from trading_bot.error_handling.exceptions import CircuitBreakerError
        >>> exc = CircuitBreakerError("Daily loss limit exceeded")
        >>> semantic_error = format_exception(exc, {"daily_loss": -5.2})
        >>> semantic_error.error_code
        'ERR_CIRCUIT_BREAKER_TRIGGERED'
    """
    exc_type_name = type(exc).__name__
    exc_message = str(exc)

    # Extract error code from exception class name
    error_code = _generate_error_code(exc_type_name)

    # Determine if retriable based on exception type
    error_type = _classify_error_type(exc)

    # Generate semantic fields based on exception type
    cause = _extract_cause(exc, exc_message)
    impact = _extract_impact(exc_type_name)
    remediation = _extract_remediation(exc_type_name, error_type)

    # Combine context with traceback info
    full_context = context or {}
    full_context["traceback"] = traceback.format_exc().split("\n")[-3:-1]  # Last 2 lines

    return SemanticError(
        error_code=error_code,
        error_type=error_type,
        message=exc_message,
        cause=cause,
        impact=impact,
        remediation=remediation,
        context=full_context,
        timestamp=datetime.now(timezone.utc),
    )


def _generate_error_code(exc_type_name: str) -> str:
    """Generate error code from exception type name.

    Args:
        exc_type_name: Exception class name (e.g., "CircuitBreakerError")

    Returns:
        Error code (e.g., "ERR_CIRCUIT_BREAKER")
    """
    # Remove "Error" suffix and convert to UPPER_SNAKE_CASE
    code = exc_type_name.replace("Error", "").replace("Exception", "")
    # Convert CamelCase to UPPER_SNAKE_CASE
    import re
    code = re.sub(r'(?<!^)(?=[A-Z])', '_', code).upper()
    return f"ERR_{code}"


def _classify_error_type(exc: Exception) -> str:
    """Classify error as retriable or non-retriable.

    Args:
        exc: The exception to classify

    Returns:
        "RetriableError", "NonRetriableError", or "ValidationError"
    """
    exc_type_name = type(exc).__name__

    # Retriable errors (network, rate limit, temporary)
    retriable_patterns = [
        "Timeout", "Network", "Connection", "RateLimit",
        "ServiceUnavailable", "TooManyRequests"
    ]
    if any(pattern in exc_type_name for pattern in retriable_patterns):
        return "RetriableError"

    # Validation errors
    if "Validation" in exc_type_name or "ValueError" in exc_type_name:
        return "ValidationError"

    # Circuit breaker and risk errors
    if "CircuitBreaker" in exc_type_name or "RiskLimit" in exc_type_name:
        return "RiskControlError"

    # Default to non-retriable
    return "NonRetriableError"


def _extract_cause(exc: Exception, exc_message: str) -> str:
    """Extract root cause explanation from exception.

    Args:
        exc: The exception
        exc_message: Exception message

    Returns:
        Human-readable cause explanation
    """
    exc_type_name = type(exc).__name__

    # Map exception types to cause explanations
    cause_map = {
        "CircuitBreaker": "Risk limits exceeded (daily loss or consecutive losses)",
        "Timeout": "Operation exceeded maximum wait time",
        "Network": "Network connectivity issue or API unavailable",
        "Validation": "Input data failed validation rules",
        "RateLimit": "API rate limit exceeded",
        "NotFound": "Requested resource does not exist",
        "Unauthorized": "Authentication failed or insufficient permissions",
    }

    # Find matching pattern
    for pattern, cause in cause_map.items():
        if pattern in exc_type_name:
            return f"{cause}. Details: {exc_message}"

    # Default cause
    return f"Exception raised: {exc_message}"


def _extract_impact(exc_type_name: str) -> str:
    """Extract impact description from exception type.

    Args:
        exc_type_name: Exception class name

    Returns:
        Impact description (what this affects)
    """
    impact_map = {
        "CircuitBreaker": "Trading halted until manual reset or time window passes",
        "Timeout": "Operation failed, may need retry",
        "Network": "API operations unavailable, bot degraded or halted",
        "Validation": "Request rejected, no action taken",
        "RateLimit": "API access throttled, operations delayed",
        "NotFound": "Requested resource unavailable",
        "Unauthorized": "API access denied",
    }

    for pattern, impact in impact_map.items():
        if pattern in exc_type_name:
            return impact

    return "Unknown impact, requires investigation"


def _extract_remediation(exc_type_name: str, error_type: str) -> str:
    """Extract remediation steps from exception type.

    Args:
        exc_type_name: Exception class name
        error_type: Classified error type (retriable/non-retriable)

    Returns:
        Suggested remediation steps
    """
    remediation_map = {
        "CircuitBreaker": "Review trading strategy, adjust risk limits, or manually reset circuit breaker after investigation",
        "Timeout": "Retry operation with exponential backoff (max 3 retries)",
        "Network": "Check network connectivity, verify API endpoint status, retry after 30s",
        "Validation": "Fix input data according to validation rules, check schema documentation",
        "RateLimit": "Wait for rate limit window to reset (check Retry-After header), reduce request frequency",
        "NotFound": "Verify resource ID, check if resource was deleted",
        "Unauthorized": "Verify API credentials, check token expiration, refresh authentication",
    }

    for pattern, remediation in remediation_map.items():
        if pattern in exc_type_name:
            return remediation

    # Default based on error type
    if error_type == "RetriableError":
        return "Retry operation with exponential backoff"

    return "Investigate error details, check logs for root cause"
