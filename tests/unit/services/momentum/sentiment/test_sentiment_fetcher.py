"""
Unit tests for SentimentFetcher service.

Tests:
- T008: SentimentFetcher initializes Twitter/Reddit clients
- T009: fetch_twitter_posts returns SentimentPost list
- T010: fetch_reddit_posts returns SentimentPost list
- T011: fetch_all combines Twitter and Reddit posts

Feature: sentiment-analysis-integration
Tasks: T008-T011 [RED] - Write tests for SentimentFetcher
"""

import pytest
from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from typing import List

from src.trading_bot.momentum.sentiment.sentiment_fetcher import SentimentFetcher
from src.trading_bot.momentum.sentiment.models import SentimentPost
from src.trading_bot.momentum.config import MomentumConfig


class TestSentimentFetcherInit:
    """Test suite for SentimentFetcher.__init__() method."""

    @patch("src.trading_bot.momentum.sentiment.sentiment_fetcher.tweepy")
    @patch("src.trading_bot.momentum.sentiment.sentiment_fetcher.praw")
    def test_init_creates_twitter_client(self, mock_praw, mock_tweepy):
        """Test that __init__ initializes Twitter client with bearer token."""
        # Given: Valid Twitter credentials in config
        config = MomentumConfig(
            twitter_bearer_token="test_bearer_token",
            reddit_client_id="test_reddit_id",
            reddit_client_secret="test_reddit_secret",
            reddit_user_agent="test_user_agent"
        )

        # When: Creating SentimentFetcher
        fetcher = SentimentFetcher(config=config)

        # Then: Twitter client initialized with bearer token
        mock_tweepy.Client.assert_called_once_with(bearer_token="test_bearer_token")
        assert fetcher.twitter_client is not None

    @patch("src.trading_bot.momentum.sentiment.sentiment_fetcher.tweepy")
    @patch("src.trading_bot.momentum.sentiment.sentiment_fetcher.praw")
    def test_init_creates_reddit_client(self, mock_praw, mock_tweepy):
        """Test that __init__ initializes Reddit client with credentials."""
        # Given: Valid Reddit credentials in config
        config = MomentumConfig(
            twitter_bearer_token="test_bearer_token",
            reddit_client_id="test_reddit_id",
            reddit_client_secret="test_reddit_secret",
            reddit_user_agent="test_user_agent"
        )

        # When: Creating SentimentFetcher
        fetcher = SentimentFetcher(config=config)

        # Then: Reddit client initialized with credentials
        mock_praw.Reddit.assert_called_once_with(
            client_id="test_reddit_id",
            client_secret="test_reddit_secret",
            user_agent="test_user_agent"
        )
        assert fetcher.reddit_client is not None


class TestFetchTwitterPosts:
    """Test suite for SentimentFetcher.fetch_twitter_posts() method."""

    @patch("src.trading_bot.momentum.sentiment.sentiment_fetcher.tweepy")
    @patch("src.trading_bot.momentum.sentiment.sentiment_fetcher.praw")
    def test_fetch_twitter_posts_returns_sentiment_post_list(self, mock_praw, mock_tweepy):
        """Test that fetch_twitter_posts returns list of SentimentPost objects."""
        # Given: Mocked Twitter API response
        config = MomentumConfig(
            twitter_bearer_token="test_bearer_token",
            reddit_client_id="test_reddit_id",
            reddit_client_secret="test_reddit_secret",
            reddit_user_agent="test_user_agent"
        )

        # Mock tweet data
        mock_tweet = MagicMock()
        mock_tweet.text = "AAPL to the moon! Great earnings!"
        mock_tweet.author_id = "user123"
        mock_tweet.created_at = datetime.now(UTC)
        mock_tweet.id = "123456"

        mock_response = MagicMock()
        mock_response.data = [mock_tweet]

        mock_twitter_client = MagicMock()
        mock_twitter_client.search_recent_tweets.return_value = mock_response
        mock_tweepy.Client.return_value = mock_twitter_client

        fetcher = SentimentFetcher(config=config)

        # When: Fetching Twitter posts for AAPL
        posts = fetcher.fetch_twitter_posts(symbol="AAPL", minutes=30)

        # Then: Returns list of SentimentPost objects
        assert isinstance(posts, list)
        assert len(posts) == 1
        assert isinstance(posts[0], SentimentPost)
        assert posts[0].symbol == "AAPL"
        assert posts[0].source == "Twitter"
        assert "AAPL" in posts[0].text or "earnings" in posts[0].text

    @patch("src.trading_bot.momentum.sentiment.sentiment_fetcher.tweepy")
    @patch("src.trading_bot.momentum.sentiment.sentiment_fetcher.praw")
    def test_fetch_twitter_posts_filters_by_time_window(self, mock_praw, mock_tweepy):
        """Test that fetch_twitter_posts only returns posts from last 30 minutes."""
        # Given: Tweets with different timestamps
        config = MomentumConfig(
            twitter_bearer_token="test_bearer_token",
            reddit_client_id="test_reddit_id",
            reddit_client_secret="test_reddit_secret",
            reddit_user_agent="test_user_agent"
        )

        now = datetime.now(UTC)

        # Recent tweet (15 minutes ago)
        mock_recent_tweet = MagicMock()
        mock_recent_tweet.text = "Recent AAPL tweet"
        mock_recent_tweet.author_id = "user1"
        mock_recent_tweet.created_at = now - timedelta(minutes=15)
        mock_recent_tweet.id = "1"

        # Old tweet (45 minutes ago - should be filtered)
        mock_old_tweet = MagicMock()
        mock_old_tweet.text = "Old AAPL tweet"
        mock_old_tweet.author_id = "user2"
        mock_old_tweet.created_at = now - timedelta(minutes=45)
        mock_old_tweet.id = "2"

        mock_response = MagicMock()
        mock_response.data = [mock_recent_tweet, mock_old_tweet]

        mock_twitter_client = MagicMock()
        mock_twitter_client.search_recent_tweets.return_value = mock_response
        mock_tweepy.Client.return_value = mock_twitter_client

        fetcher = SentimentFetcher(config=config)

        # When: Fetching with 30-minute window
        posts = fetcher.fetch_twitter_posts(symbol="AAPL", minutes=30)

        # Then: Only recent tweet returned
        assert len(posts) == 1
        assert posts[0].text == "Recent AAPL tweet"

    @patch("src.trading_bot.momentum.sentiment.sentiment_fetcher.tweepy")
    @patch("src.trading_bot.momentum.sentiment.sentiment_fetcher.praw")
    def test_fetch_twitter_posts_handles_empty_response(self, mock_praw, mock_tweepy):
        """Test graceful handling when Twitter API returns no tweets."""
        # Given: Empty Twitter API response
        config = MomentumConfig(
            twitter_bearer_token="test_bearer_token",
            reddit_client_id="test_reddit_id",
            reddit_client_secret="test_reddit_secret",
            reddit_user_agent="test_user_agent"
        )

        mock_response = MagicMock()
        mock_response.data = None

        mock_twitter_client = MagicMock()
        mock_twitter_client.search_recent_tweets.return_value = mock_response
        mock_tweepy.Client.return_value = mock_twitter_client

        fetcher = SentimentFetcher(config=config)

        # When: Fetching posts
        posts = fetcher.fetch_twitter_posts(symbol="AAPL", minutes=30)

        # Then: Returns empty list (not None or error)
        assert posts == []


class TestFetchRedditPosts:
    """Test suite for SentimentFetcher.fetch_reddit_posts() method."""

    @patch("src.trading_bot.momentum.sentiment.sentiment_fetcher.tweepy")
    @patch("src.trading_bot.momentum.sentiment.sentiment_fetcher.praw")
    def test_fetch_reddit_posts_returns_sentiment_post_list(self, mock_praw, mock_tweepy):
        """Test that fetch_reddit_posts returns list of SentimentPost objects."""
        # Given: Mocked Reddit API response
        config = MomentumConfig(
            twitter_bearer_token="test_bearer_token",
            reddit_client_id="test_reddit_id",
            reddit_client_secret="test_reddit_secret",
            reddit_user_agent="test_user_agent"
        )

        # Mock Reddit submission
        mock_submission = MagicMock()
        mock_submission.title = "AAPL earnings beat expectations"
        mock_submission.selftext = "Just announced Q4 earnings"
        mock_submission.author.name = "trader123"
        mock_submission.created_utc = datetime.now(UTC).timestamp()
        mock_submission.id = "abc123"

        mock_subreddit = MagicMock()
        mock_subreddit.search.return_value = [mock_submission]

        mock_reddit_client = MagicMock()
        mock_reddit_client.subreddit.return_value = mock_subreddit
        mock_praw.Reddit.return_value = mock_reddit_client

        fetcher = SentimentFetcher(config=config)

        # When: Fetching Reddit posts for AAPL
        posts = fetcher.fetch_reddit_posts(symbol="AAPL", minutes=30)

        # Then: Returns list of SentimentPost objects
        assert isinstance(posts, list)
        assert len(posts) == 1
        assert isinstance(posts[0], SentimentPost)
        assert posts[0].symbol == "AAPL"
        assert posts[0].source == "Reddit"
        assert "AAPL" in posts[0].text or "earnings" in posts[0].text

    @patch("src.trading_bot.momentum.sentiment.sentiment_fetcher.tweepy")
    @patch("src.trading_bot.momentum.sentiment.sentiment_fetcher.praw")
    def test_fetch_reddit_posts_filters_by_time_window(self, mock_praw, mock_tweepy):
        """Test that fetch_reddit_posts only returns posts from last 30 minutes."""
        # Given: Reddit submissions with different timestamps
        config = MomentumConfig(
            twitter_bearer_token="test_bearer_token",
            reddit_client_id="test_reddit_id",
            reddit_client_secret="test_reddit_secret",
            reddit_user_agent="test_user_agent"
        )

        now = datetime.now(UTC)

        # Recent submission (10 minutes ago)
        mock_recent = MagicMock()
        mock_recent.title = "Recent AAPL post"
        mock_recent.selftext = ""
        mock_recent.author.name = "user1"
        mock_recent.created_utc = (now - timedelta(minutes=10)).timestamp()

        # Old submission (60 minutes ago - should be filtered)
        mock_old = MagicMock()
        mock_old.title = "Old AAPL post"
        mock_old.selftext = ""
        mock_old.author.name = "user2"
        mock_old.created_utc = (now - timedelta(minutes=60)).timestamp()

        mock_subreddit = MagicMock()
        mock_subreddit.search.return_value = [mock_recent, mock_old]

        mock_reddit_client = MagicMock()
        mock_reddit_client.subreddit.return_value = mock_subreddit
        mock_praw.Reddit.return_value = mock_reddit_client

        fetcher = SentimentFetcher(config=config)

        # When: Fetching with 30-minute window
        posts = fetcher.fetch_reddit_posts(symbol="AAPL", minutes=30)

        # Then: Only recent post returned
        assert len(posts) == 1
        assert posts[0].text == "Recent AAPL post"


class TestFetchAll:
    """Test suite for SentimentFetcher.fetch_all() method."""

    @patch("src.trading_bot.momentum.sentiment.sentiment_fetcher.tweepy")
    @patch("src.trading_bot.momentum.sentiment.sentiment_fetcher.praw")
    def test_fetch_all_combines_twitter_and_reddit(self, mock_praw, mock_tweepy):
        """Test that fetch_all combines posts from both sources."""
        # Given: Mocked responses from both APIs
        config = MomentumConfig(
            twitter_bearer_token="test_bearer_token",
            reddit_client_id="test_reddit_id",
            reddit_client_secret="test_reddit_secret",
            reddit_user_agent="test_user_agent"
        )

        now = datetime.now(UTC)

        # Mock Twitter tweet
        mock_tweet = MagicMock()
        mock_tweet.text = "Twitter AAPL post"
        mock_tweet.author_id = "twitter_user"
        mock_tweet.created_at = now
        mock_tweet.id = "tweet1"

        mock_twitter_response = MagicMock()
        mock_twitter_response.data = [mock_tweet]

        mock_twitter_client = MagicMock()
        mock_twitter_client.search_recent_tweets.return_value = mock_twitter_response
        mock_tweepy.Client.return_value = mock_twitter_client

        # Mock Reddit submission
        mock_submission = MagicMock()
        mock_submission.title = "Reddit AAPL post"
        mock_submission.selftext = ""
        mock_submission.author.name = "reddit_user"
        mock_submission.created_utc = now.timestamp()

        mock_subreddit = MagicMock()
        mock_subreddit.search.return_value = [mock_submission]

        mock_reddit_client = MagicMock()
        mock_reddit_client.subreddit.return_value = mock_subreddit
        mock_praw.Reddit.return_value = mock_reddit_client

        fetcher = SentimentFetcher(config=config)

        # When: Fetching all posts
        posts = fetcher.fetch_all(symbol="AAPL", minutes=30)

        # Then: Returns combined list from both sources
        assert len(posts) == 2
        sources = [post.source for post in posts]
        assert "Twitter" in sources
        assert "Reddit" in sources

    @patch("src.trading_bot.momentum.sentiment.sentiment_fetcher.tweepy")
    @patch("src.trading_bot.momentum.sentiment.sentiment_fetcher.praw")
    def test_fetch_all_continues_on_twitter_failure(self, mock_praw, mock_tweepy):
        """Test graceful degradation when Twitter API fails."""
        # Given: Twitter fails, Reddit succeeds
        config = MomentumConfig(
            twitter_bearer_token="test_bearer_token",
            reddit_client_id="test_reddit_id",
            reddit_client_secret="test_reddit_secret",
            reddit_user_agent="test_user_agent"
        )

        # Twitter raises exception
        mock_twitter_client = MagicMock()
        mock_twitter_client.search_recent_tweets.side_effect = Exception("API rate limit")
        mock_tweepy.Client.return_value = mock_twitter_client

        # Reddit succeeds
        now = datetime.now(UTC)
        mock_submission = MagicMock()
        mock_submission.title = "Reddit AAPL post"
        mock_submission.selftext = ""
        mock_submission.author.name = "reddit_user"
        mock_submission.created_utc = now.timestamp()

        mock_subreddit = MagicMock()
        mock_subreddit.search.return_value = [mock_submission]

        mock_reddit_client = MagicMock()
        mock_reddit_client.subreddit.return_value = mock_subreddit
        mock_praw.Reddit.return_value = mock_reddit_client

        fetcher = SentimentFetcher(config=config)

        # When: Fetching all posts (Twitter fails)
        posts = fetcher.fetch_all(symbol="AAPL", minutes=30)

        # Then: Returns Reddit posts only (graceful degradation)
        assert len(posts) == 1
        assert posts[0].source == "Reddit"
