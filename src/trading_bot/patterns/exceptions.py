"""
Exceptions for Pattern Detection Module

Custom exceptions for pattern detection and configuration validation.

Pattern: src/trading_bot/indicators/exceptions.py
"""


class PatternNotFoundError(Exception):
    """
    Raised when pattern detection fails to find a valid bull flag pattern.

    Constitution §Fail_Safe: Fail-fast when pattern requirements not met.

    Attributes:
        symbol: Stock ticker symbol
        reason: Descriptive reason why pattern was not found
    """

    def __init__(self, symbol: str, reason: str) -> None:
        """
        Initialize PatternNotFoundError.

        Args:
            symbol: Stock ticker symbol
            reason: Descriptive reason why pattern detection failed

        Example:
            raise PatternNotFoundError("AAPL", "No consolidation phase detected")
            # Error: Bull flag pattern not found for AAPL: No consolidation phase detected
        """
        self.symbol = symbol
        self.reason = reason
        super().__init__(
            f"Bull flag pattern not found for {symbol}: {reason}"
        )


class InvalidConfigurationError(Exception):
    """
    Raised when BullFlagConfig has invalid parameter values.

    Constitution §Fail_Safe: Validate configuration before pattern detection.

    Attributes:
        parameter: Name of the invalid parameter
        value: The invalid value provided
        constraint: Description of the constraint violated
    """

    def __init__(self, parameter: str, value: float, constraint: str) -> None:
        """
        Initialize InvalidConfigurationError.

        Args:
            parameter: Name of the configuration parameter that is invalid
            value: The invalid value that was provided
            constraint: Description of what constraint was violated

        Example:
            raise InvalidConfigurationError(
                "min_flagpole_pct", -0.05, "must be positive (> 0)"
            )
            # Error: Invalid configuration for min_flagpole_pct=-0.05: must be positive (> 0)
        """
        self.parameter = parameter
        self.value = value
        self.constraint = constraint
        super().__init__(
            f"Invalid configuration for {parameter}={value}: {constraint}"
        )
