"""
OpenAI API Client

Wrapper around OpenAI Python SDK with:
- Rate limiting (respect API limits)
- Response caching (minimize costs)
- Budget tracking (alert at 80%)
- Retry logic with exponential backoff
- Graceful degradation on errors

Constitution v1.0.0 - §Security: API keys from environment only
"""

import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from .cache import LLMCache
from .rate_limiter import RateLimiter, RateLimitConfig

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """LLM configuration from environment."""

    api_key: str
    model: str = "gpt-4o-mini"
    max_tokens: int = 500
    temperature: float = 0.7
    budget_monthly: float = 100.00
    cache_ttl: int = 3600
    redis_url: Optional[str] = None

    @classmethod
    def from_env(cls) -> "LLMConfig":
        """Load configuration from environment variables."""
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        return cls(
            api_key=api_key,
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            max_tokens=int(os.getenv("OPENAI_MAX_TOKENS_PER_REQUEST", "500")),
            temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.7")),
            budget_monthly=float(os.getenv("OPENAI_BUDGET_MONTHLY", "100.00")),
            cache_ttl=int(os.getenv("LLM_CACHE_TTL", "3600")),
            redis_url=os.getenv("REDIS_URL"),
        )


class OpenAIClient:
    """
    OpenAI API client with rate limiting, caching, and budget tracking.

    Usage:
        client = OpenAIClient()
        response = client.complete(
            prompt="Analyze this trade signal: AAPL bull flag @ $150",
            max_tokens=300
        )
    """

    # Pricing (per 1M tokens)
    PRICING = {
        "gpt-4o-mini": {"input": 0.150, "output": 0.600},
        "gpt-4o": {"input": 5.00, "output": 15.00},
    }

    def __init__(self, config: Optional[LLMConfig] = None):
        """
        Initialize OpenAI client.

        Args:
            config: LLM configuration (loads from env if None)
        """
        self.config = config or LLMConfig.from_env()

        # Initialize OpenAI client
        self.client = OpenAI(api_key=self.config.api_key)

        # Initialize rate limiter
        rate_config = RateLimitConfig(model=self.config.model)
        self.rate_limiter = RateLimiter(rate_config)

        # Initialize cache
        self.cache = LLMCache(
            ttl_seconds=self.config.cache_ttl,
            redis_url=self.config.redis_url
        )

        # Budget tracking
        self.total_cost = 0.0
        self.request_count = 0

        logger.info(
            f"OpenAI client initialized: model={self.config.model}, "
            f"budget=${self.config.budget_monthly:.2f}/month"
        )

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate cost for API call.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Cost in USD
        """
        pricing = self.PRICING.get(self.config.model, self.PRICING["gpt-4o-mini"])
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost

    def _check_budget(self, estimated_cost: float) -> bool:
        """
        Check if request would exceed budget.

        Args:
            estimated_cost: Estimated cost for request

        Returns:
            True if within budget, False otherwise
        """
        if self.total_cost + estimated_cost > self.config.budget_monthly:
            logger.error(
                f"Budget exceeded: ${self.total_cost:.2f} + ${estimated_cost:.2f} "
                f"> ${self.config.budget_monthly:.2f}"
            )
            return False

        # Warn at 80%
        usage_pct = ((self.total_cost + estimated_cost) / self.config.budget_monthly) * 100
        if usage_pct >= 80 and (self.total_cost / self.config.budget_monthly) * 100 < 80:
            logger.warning(
                f"⚠️  LLM budget at {usage_pct:.1f}%: "
                f"${self.total_cost:.2f} / ${self.config.budget_monthly:.2f}"
            )

        return True

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def complete(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        use_cache: bool = True,
    ) -> dict:
        """
        Get completion from OpenAI API.

        Args:
            prompt: The prompt text
            max_tokens: Max tokens for response (default: config.max_tokens)
            temperature: Sampling temperature (default: config.temperature)
            use_cache: Use cached responses if available (default: True)

        Returns:
            Dict with:
                - content: Response text
                - tokens_used: Total tokens consumed
                - cost: Cost in USD
                - cached: Whether response was cached

        Raises:
            ValueError: If budget exceeded or rate limited
            Exception: On API errors (after retries)
        """
        max_tokens = max_tokens or self.config.max_tokens
        temperature = temperature if temperature is not None else self.config.temperature

        # Check cache first
        if use_cache:
            cached = self.cache.get(
                prompt=prompt,
                model=self.config.model,
                max_tokens=max_tokens,
                temperature=temperature
            )
            if cached:
                logger.debug("Using cached LLM response")
                return {**cached, "cached": True}

        # Estimate tokens for rate limiting
        input_tokens = self.rate_limiter.count_tokens(prompt)
        estimated_total_tokens = input_tokens + max_tokens

        # Check rate limits
        if not self.rate_limiter.wait_if_needed(estimated_total_tokens, max_wait_seconds=30):
            raise ValueError("Rate limit timeout - try again later")

        # Estimate cost
        estimated_cost = self._calculate_cost(input_tokens, max_tokens)
        if not self._check_budget(estimated_cost):
            raise ValueError(f"Budget exceeded: ${self.total_cost:.2f} / ${self.config.budget_monthly:.2f}")

        # Make API call
        try:
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
            )

            # Extract response
            content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens
            actual_cost = self._calculate_cost(
                response.usage.prompt_tokens,
                response.usage.completion_tokens
            )

            # Update tracking
            self.rate_limiter.record_usage(tokens_used)
            self.total_cost += actual_cost
            self.request_count += 1

            result = {
                "content": content,
                "tokens_used": tokens_used,
                "cost": actual_cost,
                "cached": False,
            }

            # Cache response
            if use_cache:
                self.cache.set(
                    prompt=prompt,
                    model=self.config.model,
                    response=result,
                    max_tokens=max_tokens,
                    temperature=temperature
                )

            logger.info(
                f"LLM request #{self.request_count}: {tokens_used} tokens, "
                f"${actual_cost:.4f} (total: ${self.total_cost:.2f})"
            )

            return result

        except Exception as e:
            logger.error(f"OpenAI API error: {e}", exc_info=True)
            raise

    def get_stats(self) -> dict:
        """
        Get client statistics.

        Returns:
            Dict with usage stats
        """
        usage = self.rate_limiter.get_current_usage()
        cache_stats = self.cache.get_stats()

        return {
            "total_cost": self.total_cost,
            "budget_remaining": self.config.budget_monthly - self.total_cost,
            "budget_used_pct": (self.total_cost / self.config.budget_monthly) * 100,
            "request_count": self.request_count,
            "rate_limit_usage": usage,
            "cache_stats": cache_stats,
        }
