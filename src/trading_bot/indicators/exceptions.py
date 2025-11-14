"""
Exceptions for Technical Indicators Module

Custom exceptions for indicator calculations and validation.

Pattern: src/trading_bot/error_handling/exceptions.py
"""


class InsufficientDataError(Exception):
    """
    Raised when insufficient historical data is available for indicator calculation.

    Constitution §Fail_Safe: Fail-fast when data requirements not met.

    Attributes:
        symbol: Stock ticker symbol
        required_bars: Minimum number of bars required
        available_bars: Number of bars available
    """

    def __init__(self, symbol: str, required_bars: int, available_bars: int) -> None:
        """
        Initialize InsufficientDataError.

        Args:
            symbol: Stock ticker symbol
            required_bars: Minimum number of bars required for calculation
            available_bars: Number of bars actually available

        Example:
            raise InsufficientDataError("AAPL", 10, 5)
            # Error: Insufficient data for AAPL: 5 bars available, 10 required
        """
        self.symbol = symbol
        self.required_bars = required_bars
        self.available_bars = available_bars
        super().__init__(
            f"Insufficient data for {symbol}: {available_bars} bars available, {required_bars} required"
        )
