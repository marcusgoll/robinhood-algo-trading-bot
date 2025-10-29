"""
Momentum Detection Configuration

Configuration dataclass for momentum and catalyst detection system.
Provides defaults from spec.md and environment variable loading.

Pattern: Follows MarketDataConfig pattern from market_data/data_models.py
"""

import os
from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class MomentumConfig:
    """
    Configuration for momentum detection service.

    All fields have sensible defaults from spec.md requirements.
    Use from_env() class method to load from environment variables.

    Attributes:
        news_api_key: API key for news data provider (NewsAPI, Finnhub, or Alpaca)
        alpaca_api_key: Alpaca API key for news data
        alpaca_secret_key: Alpaca API secret key for news data
        market_data_source: Source for market data ("alpaca", "polygon", or "iex")
        min_catalyst_strength: Minimum catalyst strength score (0-100)
        min_premarket_change_pct: Minimum pre-market price change % (FR-005)
        min_volume_ratio: Minimum volume ratio (current/avg) (FR-005)
        pole_min_gain_pct: Minimum pole gain % for bull flag pattern (FR-006)
        flag_range_pct_min: Minimum flag consolidation range % (FR-006)
        flag_range_pct_max: Maximum flag consolidation range % (FR-006)
        twitter_api_key: Twitter API key for sentiment analysis
        twitter_api_secret: Twitter API secret for sentiment analysis
        twitter_bearer_token: Twitter Bearer token for API v2 authentication
        reddit_client_id: Reddit API client ID
        reddit_client_secret: Reddit API client secret
        reddit_user_agent: Reddit API user agent string
        sentiment_threshold: Minimum sentiment score to trigger signal (0.0-1.0)
        sentiment_enabled: Enable/disable sentiment analysis feature

    Raises:
        ValueError: If validation fails in __post_init__
    """

    news_api_key: str = ""
    alpaca_api_key: str = ""
    alpaca_secret_key: str = ""
    market_data_source: str = "alpaca"
    min_catalyst_strength: float = 5.0
    min_premarket_change_pct: float = 5.0
    min_volume_ratio: float = 200.0
    pole_min_gain_pct: float = 8.0
    flag_range_pct_min: float = 3.0
    flag_range_pct_max: float = 5.0
    twitter_api_key: str = ""
    twitter_api_secret: str = ""
    twitter_bearer_token: str = ""
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = "TradingBot/1.0"
    sentiment_threshold: float = 0.6
    sentiment_enabled: bool = True

    VALID_DATA_SOURCES: ClassVar[set[str]] = {"alpaca", "polygon", "iex"}

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        # Validate all percentage values are positive
        percentage_fields = {
            "min_catalyst_strength": self.min_catalyst_strength,
            "min_premarket_change_pct": self.min_premarket_change_pct,
            "min_volume_ratio": self.min_volume_ratio,
            "pole_min_gain_pct": self.pole_min_gain_pct,
            "flag_range_pct_min": self.flag_range_pct_min,
            "flag_range_pct_max": self.flag_range_pct_max,
        }

        for field_name, value in percentage_fields.items():
            if value <= 0:
                raise ValueError(
                    f"Invalid MomentumConfig: {field_name} ({value}) must be positive"
                )

        # Validate market_data_source
        if self.market_data_source not in self.VALID_DATA_SOURCES:
            raise ValueError(
                f"Invalid MomentumConfig: market_data_source ({self.market_data_source}) "
                f"must be one of {self.VALID_DATA_SOURCES}"
            )

        # Validate flag range percentages are logical
        if self.flag_range_pct_min > self.flag_range_pct_max:
            raise ValueError(
                f"Invalid MomentumConfig: flag_range_pct_min ({self.flag_range_pct_min}) "
                f"must be <= flag_range_pct_max ({self.flag_range_pct_max})"
            )

        # Validate sentiment_threshold range [0.0, 1.0]
        if not (0.0 <= self.sentiment_threshold <= 1.0):
            raise ValueError(
                f"Invalid MomentumConfig: sentiment_threshold ({self.sentiment_threshold}) "
                f"must be between 0.0 and 1.0"
            )

    @classmethod
    def from_env(cls) -> "MomentumConfig":
        """
        Load configuration from environment variables.

        Environment Variables:
            NEWS_API_KEY: API key for news data provider
            ALPACA_API_KEY: Alpaca API key for news data
            ALPACA_SECRET_KEY: Alpaca API secret key for news data
            MARKET_DATA_SOURCE: Source for market data (default: "alpaca")
            TWITTER_API_KEY: Twitter API key for sentiment analysis
            TWITTER_API_SECRET: Twitter API secret for sentiment analysis
            TWITTER_BEARER_TOKEN: Twitter Bearer token for API v2
            REDDIT_CLIENT_ID: Reddit API client ID
            REDDIT_CLIENT_SECRET: Reddit API client secret
            REDDIT_USER_AGENT: Reddit API user agent string
            SENTIMENT_THRESHOLD: Minimum sentiment score (0.0-1.0, default: 0.6)
            SENTIMENT_ENABLED: Enable sentiment analysis (default: "true")

        Returns:
            MomentumConfig instance with values from environment or defaults

        Example:
            >>> config = MomentumConfig.from_env()
            >>> config.alpaca_api_key
            'your-api-key-from-env'
        """
        return cls(
            news_api_key=os.getenv("NEWS_API_KEY", ""),
            alpaca_api_key=os.getenv("ALPACA_API_KEY", ""),
            alpaca_secret_key=os.getenv("ALPACA_SECRET_KEY", ""),
            market_data_source=os.getenv("MARKET_DATA_SOURCE", "alpaca"),
            twitter_api_key=os.getenv("TWITTER_API_KEY", ""),
            twitter_api_secret=os.getenv("TWITTER_API_SECRET", ""),
            twitter_bearer_token=os.getenv("TWITTER_BEARER_TOKEN", ""),
            reddit_client_id=os.getenv("REDDIT_CLIENT_ID", ""),
            reddit_client_secret=os.getenv("REDDIT_CLIENT_SECRET", ""),
            reddit_user_agent=os.getenv("REDDIT_USER_AGENT", "TradingBot/1.0"),
            sentiment_threshold=float(os.getenv("SENTIMENT_THRESHOLD", "0.6")),
            sentiment_enabled=os.getenv("SENTIMENT_ENABLED", "true").lower() in ("true", "1", "yes"),
            # All other fields use class defaults
        )
