"""Tests for cache service."""

import pytest
import json
from app.services.cache_service import CacheService, get_cache_service


class TestCacheService:
    """Test Redis cache service."""

    def test_cache_service_initialization(self):
        """Test cache service initialization."""
        cache = CacheService("redis://localhost:6379")
        assert cache is not None

    def test_cache_get_set(self):
        """Test setting and getting cache values."""
        cache = CacheService("redis://localhost:6379")

        if not cache.enabled:
            pytest.skip("Redis not available")

        # Set value
        success = cache.set("test_key", {"data": "value"}, ttl=60)
        assert success is True

        # Get value
        value = cache.get("test_key")
        assert value is not None
        assert value["data"] == "value"

    def test_cache_delete(self):
        """Test deleting cache values."""
        cache = CacheService("redis://localhost:6379")

        if not cache.enabled:
            pytest.skip("Redis not available")

        # Set value
        cache.set("delete_key", {"data": "value"}, ttl=60)

        # Delete value
        success = cache.delete("delete_key")
        assert success is True

        # Verify deletion
        value = cache.get("delete_key")
        assert value is None

    def test_cache_exists(self):
        """Test checking if key exists."""
        cache = CacheService("redis://localhost:6379")

        if not cache.enabled:
            pytest.skip("Redis not available")

        # Set value
        cache.set("exists_key", {"data": "value"}, ttl=60)

        # Check exists
        exists = cache.exists("exists_key")
        assert exists is True

        # Check non-existent
        exists = cache.exists("nonexistent_key")
        assert exists is False

    def test_cache_ttl(self):
        """Test cache TTL expiration."""
        import time
        cache = CacheService("redis://localhost:6379")

        if not cache.enabled:
            pytest.skip("Redis not available")

        # Set value with short TTL
        cache.set("ttl_key", {"data": "value"}, ttl=1)

        # Should exist immediately
        value = cache.get("ttl_key")
        assert value is not None

        # Wait for expiration
        time.sleep(2)

        # Should be expired
        value = cache.get("ttl_key")
        assert value is None

    def test_cache_get_nonexistent(self):
        """Test getting non-existent key."""
        cache = CacheService("redis://localhost:6379")

        if not cache.enabled:
            pytest.skip("Redis not available")

        value = cache.get("nonexistent_key")
        assert value is None

    def test_cache_disabled_gracefully(self):
        """Test cache behavior when Redis is unavailable."""
        cache = CacheService("redis://nonexistent:9999")

        # Should degrade gracefully
        cache.set("key", "value")  # Should not crash
        value = cache.get("key")

        # Should return None when cache is disabled
        if not cache.enabled:
            assert value is None

    def test_cache_service_singleton(self):
        """Test cache service singleton pattern."""
        service1 = get_cache_service()
        service2 = get_cache_service()

        assert service1 is service2

    def test_cache_json_serialization(self):
        """Test caching complex JSON objects."""
        cache = CacheService("redis://localhost:6379")

        if not cache.enabled:
            pytest.skip("Redis not available")

        complex_obj = {
            "users": [
                {"id": 1, "name": "Alice"},
                {"id": 2, "name": "Bob"}
            ],
            "count": 2,
            "metadata": {
                "created_at": "2026-10-11",
                "version": "1.0"
            }
        }

        cache.set("complex_key", complex_obj, ttl=60)
        retrieved = cache.get("complex_key")

        assert retrieved == complex_obj

    def test_cache_clear(self):
        """Test clearing all cache."""
        cache = CacheService("redis://localhost:6379")

        if not cache.enabled:
            pytest.skip("Redis not available")

        # Set multiple values
        cache.set("key1", "value1", ttl=60)
        cache.set("key2", "value2", ttl=60)

        # Clear cache
        success = cache.clear()
        assert success is True

        # Verify all cleared
        assert cache.get("key1") is None
        assert cache.get("key2") is None
