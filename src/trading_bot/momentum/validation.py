"""
Input validation utilities for momentum detection.

Provides validation functions for stock symbols and other inputs to ensure
data quality and prevent invalid API calls.

Constitution v1.0.0:
- §Risk_Management: Input validation, fail fast
- §Data_Integrity: Strict symbol format validation

Feature: momentum-detection
Task: T056 - Input validation for all scan() methods
"""

import logging
import re
from typing import List

# Module logger
logger = logging.getLogger(__name__)

# Stock symbol regex pattern
# Valid: 1-5 uppercase letters (A-Z only)
# Examples: AAPL, GOOGL, TSLA, META, A
SYMBOL_PATTERN = re.compile(r"^[A-Z]{1,5}$")


def validate_symbols(symbols: List[str]) -> None:
    """
    Validate list of stock ticker symbols.

    Checks:
    - List is not empty
    - Each symbol matches ^[A-Z]{1,5}$ pattern (1-5 uppercase letters)

    Args:
        symbols: List of stock ticker symbols to validate

    Raises:
        ValueError: If symbols list is empty or contains invalid symbols

    Example:
        >>> validate_symbols(["AAPL", "GOOGL"])  # OK
        >>> validate_symbols(["aapl"])  # Raises: lowercase not allowed
        ValueError: Invalid symbol format: 'aapl' (must be 1-5 uppercase letters A-Z)
        >>> validate_symbols([])  # Raises: empty list
        ValueError: Symbols list cannot be empty
    """
    # Check if list is empty
    if not symbols:
        raise ValueError(
            "Symbols list cannot be empty. "
            "Provide at least one stock ticker symbol (e.g., ['AAPL'])"
        )

    # Validate each symbol
    invalid_symbols = []
    for symbol in symbols:
        # Check if symbol is a string
        if not isinstance(symbol, str):
            invalid_symbols.append((symbol, f"not a string (type: {type(symbol).__name__})"))
            continue

        # Check if symbol matches pattern
        if not SYMBOL_PATTERN.match(symbol):
            # Provide specific error message based on common issues
            if not symbol:
                invalid_symbols.append((symbol, "empty string"))
            elif symbol.islower():
                invalid_symbols.append((symbol, "must be uppercase"))
            elif len(symbol) > 5:
                invalid_symbols.append((symbol, f"too long ({len(symbol)} chars, max 5)"))
            elif not symbol.isalpha():
                invalid_symbols.append((symbol, "contains non-letter characters"))
            else:
                invalid_symbols.append((symbol, "invalid format"))

    # Raise error if any invalid symbols found
    if invalid_symbols:
        error_details = "; ".join([f"'{sym}': {reason}" for sym, reason in invalid_symbols])
        raise ValueError(
            f"Invalid symbol format detected: {error_details}. "
            f"Symbols must be 1-5 uppercase letters (A-Z) only."
        )

    logger.debug(f"Symbol validation passed for {len(symbols)} symbols: {symbols}")


def is_valid_symbol(symbol: str) -> bool:
    """
    Check if a single symbol is valid (non-raising version).

    Args:
        symbol: Stock ticker symbol to validate

    Returns:
        bool: True if symbol is valid, False otherwise

    Example:
        >>> is_valid_symbol("AAPL")
        True
        >>> is_valid_symbol("aapl")
        False
        >>> is_valid_symbol("TOOLONG")
        False
    """
    if not isinstance(symbol, str):
        return False

    return SYMBOL_PATTERN.match(symbol) is not None
