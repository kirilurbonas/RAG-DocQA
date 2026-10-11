"""Redis caching service for performance optimization."""

import json
import logging
import os
from typing import Any, Optional
from redis import Redis
from redis.exceptions import ConnectionError

logger = logging.getLogger(__name__)


class CacheService:
    """Redis-based caching service."""

    def __init__(self, redis_url: Optional[str] = None):
        """Initialize cache service."""
        self.redis_url = redis_url or os.getenv('REDIS_URL', 'redis://localhost:6379')
        self.redis = None
        self.enabled = True
        self._connect()

    def _connect(self):
        """Connect to Redis."""
        try:
            self.redis = Redis.from_url(self.redis_url, decode_responses=True)
            self.redis.ping()
            logger.info("Connected to Redis cache")
        except (ConnectionError, Exception) as e:
            logger.warning(f"Failed to connect to Redis: {e}. Cache disabled.")
            self.enabled = False
            self.redis = None

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self.enabled or not self.redis:
            return None

        try:
            value = self.redis.get(key)
            if value:
                return json.loads(value)
        except Exception as e:
            logger.warning(f"Cache get failed for key {key}: {e}")

        return None

    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in cache with TTL."""
        if not self.enabled or not self.redis:
            return False

        try:
            self.redis.setex(key, ttl, json.dumps(value))
            return True
        except Exception as e:
            logger.warning(f"Cache set failed for key {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        if not self.enabled or not self.redis:
            return False

        try:
            self.redis.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Cache delete failed for key {key}: {e}")
            return False

    def clear(self) -> bool:
        """Clear all cache."""
        if not self.enabled or not self.redis:
            return False

        try:
            self.redis.flushdb()
            return True
        except Exception as e:
            logger.warning(f"Cache clear failed: {e}")
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        if not self.enabled or not self.redis:
            return False

        try:
            return self.redis.exists(key) > 0
        except Exception as e:
            logger.warning(f"Cache exists check failed for key {key}: {e}")
            return False


# Global cache instance
_cache_instance = None


def get_cache_service() -> CacheService:
    """Get or create cache service singleton."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = CacheService()
    return _cache_instance
