"""
Rate Limiter for OpenAI API

Implements token-based rate limiting to stay within OpenAI API limits:
- gpt-4o-mini: 10,000 TPM (tokens per minute)
- gpt-4o: 10,000 TPM

Tracks both tokens and requests, with sliding window algorithm.

Constitution v1.0.0 - §Resource_Management: Respect external API limits
"""

import logging
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import Lock
from typing import Optional

import tiktoken

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""

    max_tokens_per_minute: int = 10_000  # OpenAI default
    max_requests_per_minute: int = 500   # OpenAI default
    model: str = "gpt-4o-mini"


class RateLimiter:
    """
    Token-based rate limiter for OpenAI API calls.

    Uses sliding window algorithm to track usage over the last minute.
    Blocks requests if limits would be exceeded.
    """

    def __init__(self, config: Optional[RateLimitConfig] = None):
        """
        Initialize rate limiter.

        Args:
            config: Rate limit configuration (uses defaults if None)
        """
        self.config = config or RateLimitConfig()
        self.lock = Lock()

        # Track token usage: (timestamp, token_count)
        self.token_history: deque = deque()

        # Track request counts: (timestamp,)
        self.request_history: deque = deque()

        # Token encoder for counting
        try:
            self.encoding = tiktoken.encoding_for_model(self.config.model)
        except KeyError:
            # Fallback to cl100k_base for newer models
            self.encoding = tiktoken.get_encoding("cl100k_base")

        logger.info(
            f"RateLimiter initialized: {self.config.max_tokens_per_minute} TPM, "
            f"{self.config.max_requests_per_minute} RPM"
        )

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text string.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        return len(self.encoding.encode(text))

    def _clean_old_entries(self):
        """Remove entries older than 1 minute from history."""
        cutoff = time.time() - 60  # 1 minute ago

        # Clean token history
        while self.token_history and self.token_history[0][0] < cutoff:
            self.token_history.popleft()

        # Clean request history
        while self.request_history and self.request_history[0] < cutoff:
            self.request_history.popleft()

    def get_current_usage(self) -> dict:
        """
        Get current rate limit usage.

        Returns:
            Dict with tokens_used, requests_made, tokens_remaining, requests_remaining
        """
        with self.lock:
            self._clean_old_entries()

            tokens_used = sum(count for _, count in self.token_history)
            requests_made = len(self.request_history)

            return {
                "tokens_used": tokens_used,
                "tokens_remaining": self.config.max_tokens_per_minute - tokens_used,
                "requests_made": requests_made,
                "requests_remaining": self.config.max_requests_per_minute - requests_made,
                "tokens_limit": self.config.max_tokens_per_minute,
                "requests_limit": self.config.max_requests_per_minute,
            }

    def can_make_request(self, estimated_tokens: int) -> bool:
        """
        Check if request can be made without exceeding limits.

        Args:
            estimated_tokens: Estimated token count for request + response

        Returns:
            True if request can be made, False otherwise
        """
        with self.lock:
            self._clean_old_entries()

            current_tokens = sum(count for _, count in self.token_history)
            current_requests = len(self.request_history)

            token_ok = (current_tokens + estimated_tokens) <= self.config.max_tokens_per_minute
            request_ok = (current_requests + 1) <= self.config.max_requests_per_minute

            return token_ok and request_ok

    def wait_if_needed(self, estimated_tokens: int, max_wait_seconds: float = 30.0) -> bool:
        """
        Wait until request can be made, or timeout.

        Args:
            estimated_tokens: Estimated token count for request
            max_wait_seconds: Maximum time to wait (default 30s)

        Returns:
            True if can proceed, False if timed out
        """
        start_time = time.time()

        while not self.can_make_request(estimated_tokens):
            elapsed = time.time() - start_time

            if elapsed >= max_wait_seconds:
                logger.warning(
                    f"Rate limit timeout after {elapsed:.1f}s "
                    f"(needed {estimated_tokens} tokens)"
                )
                return False

            # Wait a bit before checking again
            time.sleep(0.5)

        return True

    def record_usage(self, tokens_used: int):
        """
        Record API usage.

        Args:
            tokens_used: Number of tokens consumed
        """
        with self.lock:
            now = time.time()
            self.token_history.append((now, tokens_used))
            self.request_history.append(now)
            self._clean_old_entries()

            usage = self.get_current_usage()
            logger.debug(
                f"API usage recorded: {tokens_used} tokens | "
                f"Current: {usage['tokens_used']}/{usage['tokens_limit']} tokens, "
                f"{usage['requests_made']}/{usage['requests_limit']} requests"
            )
