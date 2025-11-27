"""In-memory caching utilities for F1 API data."""
from typing import Dict, Optional, Any
from datetime import datetime, timedelta


class Cache:
    """Simple in-memory cache with TTL support."""

    def __init__(self, provider: str = "sportmonks", ttl_minutes: int = 10):
        """
        Initialize cache.

        Args:
            provider: Provider name for cache key prefix
            ttl_minutes: Cache TTL in minutes (default: 10)
        """
        self.provider = provider
        self._cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self._cache_ttl = timedelta(minutes=ttl_minutes)

    def get_cache_key(self, key: str) -> str:
        """Generate cache key with provider prefix."""
        return f"{self.provider}:{key}"

    def get(self, key: str) -> Optional[Any]:
        """
        Get cached value if it exists and hasn't expired.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found or expired
        """
        cache_key = self.get_cache_key(key)
        if cache_key in self._cache:
            ts = self._cache_timestamps.get(cache_key)
            if ts and datetime.utcnow() - ts < self._cache_ttl:
                return self._cache[cache_key]
            # expired
            self._cache.pop(cache_key, None)
            self._cache_timestamps.pop(cache_key, None)
        return None

    def set(self, key: str, value: Any):
        """
        Set cached value with current timestamp.

        Args:
            key: Cache key
            value: Value to cache
        """
        cache_key = self.get_cache_key(key)
        self._cache[cache_key] = value
        self._cache_timestamps[cache_key] = datetime.utcnow()

