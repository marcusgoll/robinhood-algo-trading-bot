"""Data models for sentiment analysis.

Dataclasses for sentiment data: SentimentPost, SentimentScore

All dataclasses include __post_init__ validation for data integrity.
Follows patterns from src/trading_bot/momentum/schemas/momentum_signal.py
"""

import re
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class SentimentPost:
    """
    Immutable social media post for sentiment analysis.

    Attributes:
        text: Post content text (must be non-empty)
        author: Post author username
        timestamp: When post was created (UTC timezone)
        source: Social media platform ('Twitter' or 'Reddit')
        symbol: Stock ticker symbol (1-5 uppercase letters)

    Raises:
        ValueError: If validation fails (empty text, invalid source, invalid symbol)
    """

    text: str
    author: str
    timestamp: datetime
    source: str
    symbol: str

    def __post_init__(self) -> None:
        """Validate sentiment post after initialization."""
        # Validate text is non-empty
        if not self.text or not self.text.strip():
            raise ValueError("Invalid SentimentPost: text must be non-empty")

        # Validate source is Twitter or Reddit
        if self.source not in ("Twitter", "Reddit"):
            raise ValueError(
                f"Invalid SentimentPost: source ({self.source}) "
                f"must be 'Twitter' or 'Reddit'"
            )

        # Validate timestamp is datetime object
        if not isinstance(self.timestamp, datetime):
            raise ValueError(
                f"Invalid SentimentPost: timestamp must be a datetime object, "
                f"got {type(self.timestamp).__name__}"
            )

        # Validate symbol format: 1-5 uppercase letters only
        if not re.match(r"^[A-Z]{1,5}$", self.symbol):
            raise ValueError(
                f"Invalid SentimentPost: symbol ({self.symbol}) "
                f"must be 1-5 uppercase characters (A-Z only)"
            )


@dataclass(frozen=True)
class SentimentScore:
    """
    Immutable aggregated sentiment score for a symbol.

    Attributes:
        symbol: Stock ticker symbol (1-5 uppercase letters)
        score: Sentiment score from -1.0 (bearish) to +1.0 (bullish)
        confidence: Model confidence score from 0.0 to 1.0
        post_count: Number of posts analyzed (must be >= 10)
        timestamp: When score was calculated (UTC timezone)

    Raises:
        ValueError: If validation fails (score out of range, confidence out of range,
                    post_count < 10, invalid symbol)
    """

    symbol: str
    score: float
    confidence: float
    post_count: int
    timestamp: datetime

    def __post_init__(self) -> None:
        """Validate sentiment score after initialization."""
        # Validate score range [-1.0, 1.0]
        if not (-1.0 <= self.score <= 1.0):
            raise ValueError(
                f"Invalid SentimentScore for {self.symbol}: score ({self.score}) "
                f"must be between -1.0 and 1.0"
            )

        # Validate confidence range [0.0, 1.0]
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(
                f"Invalid SentimentScore for {self.symbol}: confidence ({self.confidence}) "
                f"must be between 0.0 and 1.0"
            )

        # Validate post_count is positive
        # Note: Minimum 10 posts required for reliable aggregation, but enforced
        # at aggregator level (not dataclass level) to allow intermediate calculations
        if self.post_count < 0:
            raise ValueError(
                f"Invalid SentimentScore for {self.symbol}: post_count ({self.post_count}) "
                f"must be non-negative"
            )

        # Validate timestamp is datetime object
        if not isinstance(self.timestamp, datetime):
            raise ValueError(
                f"Invalid SentimentScore: timestamp must be a datetime object, "
                f"got {type(self.timestamp).__name__}"
            )

        # Validate symbol format: 1-5 uppercase letters only
        if not re.match(r"^[A-Z]{1,5}$", self.symbol):
            raise ValueError(
                f"Invalid SentimentScore: symbol ({self.symbol}) "
                f"must be 1-5 uppercase characters (A-Z only)"
            )
