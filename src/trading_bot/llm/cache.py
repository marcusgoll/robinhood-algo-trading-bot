"""
LLM Response Cache

Caches OpenAI API responses to minimize costs and API usage.
Supports both file-based (default) and Redis caching.

Cache key format: hash(prompt + model + temperature)
TTL: Configurable (default 1 hour)

Constitution v1.0.0 - §Cost_Optimization: Cache expensive operations
"""

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class LLMCache:
    """
    Cache for LLM API responses.

    Supports file-based caching (no dependencies) and optional Redis.
    """

    def __init__(
        self,
        ttl_seconds: int = 3600,
        cache_dir: Optional[str] = None,
        redis_url: Optional[str] = None,
    ):
        """
        Initialize cache.

        Args:
            ttl_seconds: Time-to-live for cache entries (default 1 hour)
            cache_dir: Directory for file-based cache (default: logs/llm_cache)
            redis_url: Redis URL for distributed caching (optional)
        """
        self.ttl_seconds = ttl_seconds
        self.cache_dir = Path(cache_dir or "logs/llm_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Try to initialize Redis if URL provided
        self.redis_client = None
        if redis_url:
            try:
                import redis
                self.redis_client = redis.from_url(redis_url)
                self.redis_client.ping()
                logger.info(f"Redis cache initialized: {redis_url}")
            except Exception as e:
                logger.warning(f"Redis initialization failed, using file cache: {e}")

        logger.info(
            f"LLM cache initialized: TTL={ttl_seconds}s, "
            f"backend={'Redis' if self.redis_client else 'File'}"
        )

    def _generate_key(self, prompt: str, model: str, **kwargs) -> str:
        """
        Generate cache key from prompt and parameters.

        Args:
            prompt: The prompt text
            model: Model name
            **kwargs: Additional parameters (temperature, etc.)

        Returns:
            SHA256 hash as hex string
        """
        # Create deterministic key from all parameters
        key_data = {
            "prompt": prompt,
            "model": model,
            **kwargs,
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()

    def get(self, prompt: str, model: str, **kwargs) -> Optional[dict]:
        """
        Get cached response.

        Args:
            prompt: The prompt text
            model: Model name
            **kwargs: Additional parameters

        Returns:
            Cached response dict or None if not found/expired
        """
        key = self._generate_key(prompt, model, **kwargs)

        try:
            # Try Redis first
            if self.redis_client:
                cached = self.redis_client.get(f"llm:{key}")
                if cached:
                    response = json.loads(cached)
                    logger.debug(f"Cache HIT (Redis): {key[:16]}...")
                    return response

            # Fall back to file cache
            cache_file = self.cache_dir / f"{key}.json"
            if cache_file.exists():
                # Check if expired
                age = time.time() - cache_file.stat().st_mtime
                if age < self.ttl_seconds:
                    with open(cache_file, "r") as f:
                        response = json.load(f)
                    logger.debug(f"Cache HIT (File): {key[:16]}... (age: {age:.0f}s)")
                    return response
                else:
                    # Expired, delete
                    cache_file.unlink()
                    logger.debug(f"Cache EXPIRED: {key[:16]}... (age: {age:.0f}s)")

        except Exception as e:
            logger.warning(f"Cache read error: {e}")

        logger.debug(f"Cache MISS: {key[:16]}...")
        return None

    def set(self, prompt: str, model: str, response: dict, **kwargs):
        """
        Store response in cache.

        Args:
            prompt: The prompt text
            model: Model name
            response: API response to cache
            **kwargs: Additional parameters
        """
        key = self._generate_key(prompt, model, **kwargs)

        try:
            # Store in Redis if available
            if self.redis_client:
                self.redis_client.setex(
                    f"llm:{key}",
                    self.ttl_seconds,
                    json.dumps(response)
                )
                logger.debug(f"Cache SET (Redis): {key[:16]}...")

            # Always store in file cache as backup
            cache_file = self.cache_dir / f"{key}.json"
            with open(cache_file, "w") as f:
                json.dump(response, f, indent=2)
            logger.debug(f"Cache SET (File): {key[:16]}...")

        except Exception as e:
            logger.warning(f"Cache write error: {e}")

    def clear(self):
        """Clear all cache entries."""
        try:
            # Clear Redis
            if self.redis_client:
                for key in self.redis_client.scan_iter("llm:*"):
                    self.redis_client.delete(key)
                logger.info("Redis cache cleared")

            # Clear file cache
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
            logger.info("File cache cleared")

        except Exception as e:
            logger.warning(f"Cache clear error: {e}")

    def get_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dict with entry_count, total_size_bytes, oldest_entry_age
        """
        try:
            files = list(self.cache_dir.glob("*.json"))
            total_size = sum(f.stat().st_size for f in files)
            oldest_age = max(
                (time.time() - f.stat().st_mtime for f in files),
                default=0
            )

            return {
                "entry_count": len(files),
                "total_size_bytes": total_size,
                "oldest_entry_age_seconds": oldest_age,
                "backend": "Redis" if self.redis_client else "File",
            }
        except Exception as e:
            logger.warning(f"Cache stats error: {e}")
            return {"error": str(e)}
