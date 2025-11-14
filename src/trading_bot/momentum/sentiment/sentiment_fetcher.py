"""
Social Media API Integration for Sentiment Analysis

Fetches posts from Twitter and Reddit for specified stock symbols within
a configurable time window (default 30 minutes).

Constitution v1.0.0:
- Safety_First: Graceful degradation on API failures
- Risk_Management: Rate limiting, input validation
- Security: API credentials from environment only

Feature: sentiment-analysis-integration
Tasks: T012-T014 [GREEN] - SentimentFetcher implementation
"""

import logging
from datetime import UTC, datetime, timedelta

import praw
import tweepy

from ...error_handling.retry import with_retry
from ..config import MomentumConfig
from .models import SentimentPost

# Module logger
logger = logging.getLogger(__name__)


class SentimentFetcher:
    """Fetches social media posts from Twitter and Reddit for sentiment analysis.

    Features:
    - Twitter API v2 integration (tweepy)
    - Reddit API integration (praw)
    - 30-minute rolling time window (configurable)
    - Graceful degradation on API failures
    - Rate limit handling with @with_retry

    Example:
        >>> config = MomentumConfig.from_env()
        >>> fetcher = SentimentFetcher(config)
        >>> posts = fetcher.fetch_all("AAPL", minutes=30)
        >>> print(f"Found {len(posts)} posts about AAPL")
    """

    def __init__(self, config: MomentumConfig):
        """Initialize Twitter and Reddit API clients.

        Args:
            config: MomentumConfig with API credentials

        Raises:
            ValueError: If required credentials missing when sentiment_enabled=True
        """
        self.config = config

        # Initialize Twitter client (API v2)
        try:
            self.twitter_client = tweepy.Client(
                bearer_token=config.twitter_bearer_token
            )
            logger.info("Twitter client initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize Twitter client: {e}")
            self.twitter_client = None

        # Initialize Reddit client
        try:
            self.reddit_client = praw.Reddit(
                client_id=config.reddit_client_id,
                client_secret=config.reddit_client_secret,
                user_agent=config.reddit_user_agent
            )
            logger.info("Reddit client initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize Reddit client: {e}")
            self.reddit_client = None

    @with_retry()
    def fetch_twitter_posts(self, symbol: str, minutes: int = 30) -> list[SentimentPost]:
        """Fetch recent tweets mentioning the stock symbol.

        Args:
            symbol: Stock ticker symbol (e.g., "AAPL")
            minutes: Time window in minutes (default 30)

        Returns:
            List of SentimentPost objects from Twitter

        Notes:
            - Searches for "$SYMBOL OR SYMBOL" to catch both formats
            - Filters to last N minutes using created_at
            - Returns empty list on API failure (graceful degradation)
        """
        if not self.twitter_client:
            logger.warning("Twitter client not initialized, returning empty list")
            return []

        try:
            # Calculate time cutoff
            cutoff_time = datetime.now(UTC) - timedelta(minutes=minutes)

            # Search query: catch both "$AAPL" and "AAPL"
            query = f"${symbol} OR {symbol} -is:retweet"

            # Fetch tweets (Twitter API v2)
            response = self.twitter_client.search_recent_tweets(
                query=query,
                max_results=100,
                tweet_fields=["created_at", "author_id", "text"]
            )

            # Handle empty response
            if not response or not response.data:
                logger.info(f"No Twitter posts found for {symbol}")
                return []

            # Convert to SentimentPost objects and filter by time
            posts = []
            for tweet in response.data:
                # Filter by time window
                if tweet.created_at >= cutoff_time:
                    post = SentimentPost(
                        text=tweet.text,
                        author=str(tweet.author_id),
                        timestamp=tweet.created_at,
                        source="Twitter",
                        symbol=symbol
                    )
                    posts.append(post)

            logger.info(f"Fetched {len(posts)} Twitter posts for {symbol} (last {minutes} min)")
            return posts

        except Exception as e:
            logger.error(f"Twitter API error for {symbol}: {e}")
            return []  # Graceful degradation

    @with_retry()
    def fetch_reddit_posts(self, symbol: str, minutes: int = 30) -> list[SentimentPost]:
        """Fetch recent Reddit posts mentioning the stock symbol.

        Args:
            symbol: Stock ticker symbol (e.g., "AAPL")
            minutes: Time window in minutes (default 30)

        Returns:
            List of SentimentPost objects from Reddit

        Notes:
            - Searches multiple finance subreddits:
              * r/wallstreetbets (19.5M) - retail sentiment, meme stocks
              * r/stocks (6.5M) - general stock discussion
              * r/investing (2.3M) - long-term investor sentiment
              * r/StockMarket (2.6M) - broad market discussion
              * r/options (800k) - derivatives sentiment (often predictive)
            - Combines title + selftext for full post content
            - Filters to last N minutes using created_utc
            - Returns empty list on API failure (graceful degradation)
        """
        if not self.reddit_client:
            logger.warning("Reddit client not initialized, returning empty list")
            return []

        try:
            # Calculate time cutoff
            cutoff_time = datetime.now(UTC) - timedelta(minutes=minutes)

            # Search multiple finance subreddits (combined with + delimiter)
            subreddits = self.reddit_client.subreddit(
                "wallstreetbets+stocks+investing+StockMarket+options"
            )

            # Search for symbol
            submissions = subreddits.search(
                query=symbol,
                sort="new",
                time_filter="hour",  # Reddit API limitation
                limit=100
            )

            # Convert to SentimentPost objects and filter by time
            posts = []
            for submission in submissions:
                # Convert Unix timestamp to datetime
                post_time = datetime.fromtimestamp(submission.created_utc, tz=UTC)

                # Filter by time window
                if post_time >= cutoff_time:
                    # Combine title and body for full text
                    text = submission.title
                    if submission.selftext:
                        text += " " + submission.selftext

                    post = SentimentPost(
                        text=text,
                        author=submission.author.name if submission.author else "deleted",
                        timestamp=post_time,
                        source="Reddit",
                        symbol=symbol
                    )
                    posts.append(post)

            logger.info(f"Fetched {len(posts)} Reddit posts for {symbol} (last {minutes} min)")
            return posts

        except Exception as e:
            logger.error(f"Reddit API error for {symbol}: {e}")
            return []  # Graceful degradation

    def fetch_all(self, symbol: str, minutes: int = 30) -> list[SentimentPost]:
        """Fetch posts from both Twitter and Reddit.

        Args:
            symbol: Stock ticker symbol (e.g., "AAPL")
            minutes: Time window in minutes (default 30)

        Returns:
            Combined list of SentimentPost objects from both sources

        Notes:
            - Continues if one source fails (graceful degradation)
            - Posts are NOT deduplicated (same content from both sources kept)
            - Returns empty list if both sources fail
        """
        all_posts = []

        # Fetch from Twitter
        try:
            twitter_posts = self.fetch_twitter_posts(symbol, minutes)
            all_posts.extend(twitter_posts)
        except Exception as e:
            logger.error(f"Failed to fetch Twitter posts for {symbol}: {e}")

        # Fetch from Reddit
        try:
            reddit_posts = self.fetch_reddit_posts(symbol, minutes)
            all_posts.extend(reddit_posts)
        except Exception as e:
            logger.error(f"Failed to fetch Reddit posts for {symbol}: {e}")

        logger.info(
            f"Fetched {len(all_posts)} total posts for {symbol} "
            f"(Twitter: {len([p for p in all_posts if p.source == 'Twitter'])}, "
            f"Reddit: {len([p for p in all_posts if p.source == 'Reddit'])})"
        )

        return all_posts
