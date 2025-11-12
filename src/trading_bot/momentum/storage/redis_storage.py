"""
Redis storage backend for momentum scan results.

Provides persistent storage for scan results with TTL support.
Falls back to in-memory storage if Redis is unavailable.
"""

import json
import logging
from typing import Optional, Dict, Any
from datetime import timedelta

logger = logging.getLogger(__name__)

# Optional Redis import
try:
    import redis
    from redis import Redis
    HAS_REDIS = True
except ImportError:
    redis = None
    Redis = None
    HAS_REDIS = False


class ScanResultStorage:
    """
    Storage backend for momentum scan results.

    Supports both Redis (production) and in-memory (development) storage.
    Automatically falls back to in-memory if Redis is unavailable.
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        ttl_seconds: int = 3600  # 1 hour default TTL
    ):
        """
        Initialize storage backend.

        Args:
            redis_url: Redis connection URL (redis://localhost:6379/0)
                      If None, uses in-memory storage
            ttl_seconds: Time-to-live for scan results (default: 1 hour)
        """
        self.ttl_seconds = ttl_seconds
        self._redis: Optional[Any] = None
        self._memory_storage: Dict[str, Dict[str, Any]] = {}

        # Try to connect to Redis if URL provided
        if redis_url and HAS_REDIS:
            try:
                self._redis = redis.from_url(
                    redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                # Test connection
                self._redis.ping()
                logger.info(f"Connected to Redis at {redis_url}")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}. Using in-memory storage.")
                self._redis = None
        else:
            if redis_url and not HAS_REDIS:
                logger.warning(
                    "Redis URL provided but redis module not installed. "
                    "Install with: pip install redis"
                )
            logger.info("Using in-memory storage for scan results")

    def store_scan(self, scan_id: str, scan_data: Dict[str, Any]) -> None:
        """
        Store scan result.

        Args:
            scan_id: Unique scan identifier
            scan_data: Scan result data dictionary
        """
        if self._redis:
            try:
                # Store in Redis with TTL
                key = f"scan:{scan_id}"
                self._redis.setex(
                    key,
                    timedelta(seconds=self.ttl_seconds),
                    json.dumps(scan_data)
                )
                logger.debug(f"Stored scan {scan_id} in Redis")
            except Exception as e:
                logger.error(f"Failed to store scan in Redis: {e}. Using memory fallback.")
                self._memory_storage[scan_id] = scan_data
        else:
            # In-memory storage
            self._memory_storage[scan_id] = scan_data
            logger.debug(f"Stored scan {scan_id} in memory")

    def get_scan(self, scan_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve scan result.

        Args:
            scan_id: Unique scan identifier

        Returns:
            Scan data dictionary or None if not found
        """
        if self._redis:
            try:
                key = f"scan:{scan_id}"
                data = self._redis.get(key)
                if data:
                    logger.debug(f"Retrieved scan {scan_id} from Redis")
                    return json.loads(data)
                return None
            except Exception as e:
                logger.error(f"Failed to retrieve scan from Redis: {e}. Checking memory fallback.")
                return self._memory_storage.get(scan_id)
        else:
            # In-memory retrieval
            return self._memory_storage.get(scan_id)

    def delete_scan(self, scan_id: str) -> bool:
        """
        Delete scan result.

        Args:
            scan_id: Unique scan identifier

        Returns:
            True if deleted, False if not found
        """
        if self._redis:
            try:
                key = f"scan:{scan_id}"
                deleted = self._redis.delete(key)
                logger.debug(f"Deleted scan {scan_id} from Redis: {deleted > 0}")
                return deleted > 0
            except Exception as e:
                logger.error(f"Failed to delete scan from Redis: {e}. Checking memory fallback.")
                if scan_id in self._memory_storage:
                    del self._memory_storage[scan_id]
                    return True
                return False
        else:
            # In-memory deletion
            if scan_id in self._memory_storage:
                del self._memory_storage[scan_id]
                logger.debug(f"Deleted scan {scan_id} from memory")
                return True
            return False

    def list_scans(self, limit: int = 100) -> list[str]:
        """
        List all scan IDs.

        Args:
            limit: Maximum number of scan IDs to return

        Returns:
            List of scan IDs
        """
        if self._redis:
            try:
                # Get all scan keys
                keys = self._redis.keys("scan:*")
                # Extract scan IDs (remove "scan:" prefix)
                scan_ids = [key.replace("scan:", "") for key in keys[:limit]]
                logger.debug(f"Retrieved {len(scan_ids)} scan IDs from Redis")
                return scan_ids
            except Exception as e:
                logger.error(f"Failed to list scans from Redis: {e}. Using memory fallback.")
                return list(self._memory_storage.keys())[:limit]
        else:
            # In-memory list
            return list(self._memory_storage.keys())[:limit]

    def clear_all(self) -> int:
        """
        Clear all scan results (for testing/maintenance).

        Returns:
            Number of scans deleted
        """
        if self._redis:
            try:
                keys = self._redis.keys("scan:*")
                if keys:
                    deleted = self._redis.delete(*keys)
                    logger.info(f"Cleared {deleted} scans from Redis")
                    return deleted
                return 0
            except Exception as e:
                logger.error(f"Failed to clear Redis: {e}. Clearing memory fallback.")
                count = len(self._memory_storage)
                self._memory_storage.clear()
                return count
        else:
            # Clear in-memory storage
            count = len(self._memory_storage)
            self._memory_storage.clear()
            logger.info(f"Cleared {count} scans from memory")
            return count

    @property
    def backend(self) -> str:
        """Get current storage backend name."""
        return "redis" if self._redis else "memory"

    @property
    def is_redis(self) -> bool:
        """Check if using Redis backend."""
        return self._redis is not None
