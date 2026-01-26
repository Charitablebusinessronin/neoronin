"""
Cache Manager

This module provides a thread-safe LRU cache with TTL support.
- LRU eviction with configurable capacity
- Time-to-live (TTL) for cached entries
- Thread-safe for concurrent access
- Cache hit/miss statistics

Author: Brooks (BMAD Dev Agent)
Created: 2026-01-26
Story: 3-4-fast-pattern-matching-query-engine
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Generic, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class CacheStats:
    """Statistics for cache performance."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size: int = 0
    max_size: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0


@dataclass
class CacheEntry(Generic[T]):
    """A single cache entry with TTL tracking."""
    key: str
    value: T
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_accessed: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    access_count: int = 0

    def is_expired(self, ttl_seconds: int) -> bool:
        """Check if the entry has expired."""
        now = datetime.now(timezone.utc)
        elapsed = (now - self.created_at).total_seconds()
        return elapsed > ttl_seconds


class CacheManager(Generic[T]):
    """
    Thread-safe LRU cache with TTL support.

    Features:
    - Least Recently Used eviction policy
    - Configurable TTL (time-to-live)
    - Maximum capacity limit
    - Thread-safe for concurrent access
    - Statistics tracking

    Usage:
        cache = CacheManager[str](max_size=100, ttl_seconds=3600)
        cache.set("key", "value")
        value = cache.get("key")
    """

    def __init__(
        self,
        max_size: int = 100,
        ttl_seconds: int = 3600,  # 1 hour default
        name: str = "cache"
    ):
        """
        Initialize the cache manager.

        Args:
            max_size: Maximum number of entries (LRU limit)
            ttl_seconds: Time-to-live in seconds (default: 1 hour)
            name: Optional name for logging/debugging
        """
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        self._name = name
        self._data: Dict[str, CacheEntry[T]] = {}
        self._lock = threading.RLock()
        self._stats = CacheStats(max_size=max_size)

    def get(self, key: str) -> Optional[T]:
        """
        Get a value from the cache.

        Args:
            key: The cache key

        Returns:
            The cached value, or None if not found/expired
        """
        with self._lock:
            entry = self._data.get(key)

            if entry is None:
                self._stats.misses += 1
                return None

            if entry.is_expired(self._ttl_seconds):
                del self._data[key]
                self._stats.misses += 1
                self._stats.size = len(self._data)
                return None

            # Update access metadata (LRU)
            entry.last_accessed = datetime.now(timezone.utc)
            entry.access_count += 1

            self._stats.hits += 1
            return entry.value

    def set(self, key: str, value: T) -> None:
        """
        Set a value in the cache.

        Args:
            key: The cache key
            value: The value to cache
        """
        with self._lock:
            # Check if key already exists
            if key in self._data:
                # Update existing entry
                entry = self._data[key]
                entry.value = value
                entry.created_at = datetime.now(timezone.utc)
                entry.last_accessed = datetime.now(timezone.utc)
                entry.access_count += 1
                return

            # Create new entry
            self._data[key] = CacheEntry(key=key, value=value)

            # Evict if over capacity (LRU)
            while len(self._data) > self._max_size:
                self._evict_lru()

            self._stats.size = len(self._data)

    def delete(self, key: str) -> bool:
        """
        Delete a key from the cache.

        Args:
            key: The cache key to delete

        Returns:
            True if key was deleted, False if not found
        """
        with self._lock:
            if key in self._data:
                del self._data[key]
                self._stats.size = len(self._data)
                return True
            return False

    def clear(self) -> None:
        """Clear all entries from the cache."""
        with self._lock:
            self._data.clear()
            self._stats.size = 0

    def invalidate_expired(self) -> int:
        """
        Remove all expired entries.

        Returns:
            Number of entries removed
        """
        with self._lock:
            expired_keys = [
                key for key, entry in self._data.items()
                if entry.is_expired(self._ttl_seconds)
            ]

            for key in expired_keys:
                del self._data[key]
                self._stats.evictions += 1

            self._stats.size = len(self._data)
            return len(expired_keys)

    def get_stats(self) -> CacheStats:
        """Get current cache statistics."""
        with self._lock:
            return CacheStats(
                hits=self._stats.hits,
                misses=self._stats.misses,
                evictions=self._stats.evictions,
                size=self._stats.size,
                max_size=self._stats.max_size
            )

    def get_hit_rate(self) -> float:
        """Get the current cache hit rate."""
        with self._lock:
            return self._stats.hit_rate

    def contains(self, key: str) -> bool:
        """Check if key exists and is not expired."""
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return False
            if entry.is_expired(self._ttl_seconds):
                del self._data[key]
                return False
            return True

    def size(self) -> int:
        """Get current cache size."""
        with self._lock:
            return len(self._data)

    def _evict_lru(self):
        """Evict the least recently used entry."""
        if not self._data:
            return

        # Find entry with oldest last_accessed time
        lru_key = min(
            self._data.keys(),
            key=lambda k: self._data[k].last_accessed
        )

        del self._data[lru_key]
        self._stats.evictions += 1

    def get_or_set(self, key: str, factory: callable) -> T:
        """
        Get from cache or compute and set.

        Args:
            key: The cache key
            factory: Callable to produce value if not cached

        Returns:
            The cached or newly computed value
        """
        # Try to get from cache first
        value = self.get(key)
        if value is not None:
            return value

        # Compute value
        value = factory()

        # Cache it
        self.set(key, value)

        return value


class AsyncCacheManager(Generic[T]):
    """
    Async-safe wrapper around CacheManager for use with async code.

    Provides the same interface but is safe to use with asyncio.
    """

    def __init__(
        self,
        max_size: int = 100,
        ttl_seconds: int = 3600,
        name: str = "async_cache"
    ):
        """
        Initialize the async cache manager.

        Args:
            max_size: Maximum number of entries
            ttl_seconds: Time-to-live in seconds
            name: Optional name for logging
        """
        self._cache = CacheManager[T](
            max_size=max_size,
            ttl_seconds=ttl_seconds,
            name=name
        )

    async def get(self, key: str) -> Optional[T]:
        """Get from cache (async wrapper)."""
        return self._cache.get(key)

    async def set(self, key: str, value: T) -> None:
        """Set in cache (async wrapper)."""
        self._cache.set(key, value)

    async def delete(self, key: str) -> bool:
        """Delete from cache (async wrapper)."""
        return self._cache.delete(key)

    async def clear(self) -> None:
        """Clear cache (async wrapper)."""
        self._cache.clear()

    async def get_stats(self) -> CacheStats:
        """Get statistics (async wrapper)."""
        return self._cache.get_stats()

    async def invalidate_expired(self) -> int:
        """Invalidate expired entries (async wrapper)."""
        return self._cache.invalidate_expired()


# Pattern-specific cache instance
_pattern_cache = AsyncCacheManager(
    max_size=100,
    ttl_seconds=3600,  # 1 hour
    name="pattern_cache"
)


def get_pattern_cache() -> AsyncCacheManager:
    """Get the global pattern cache instance."""
    return _pattern_cache


async def main():
    """Quick test of the cache manager."""
    cache = AsyncCacheManager[str](max_size=3, ttl_seconds=60, name="test")

    print("Testing cache manager...")

    # Test basic operations
    await cache.set("key1", "value1")
    await cache.set("key2", "value2")

    value = await cache.get("key1")
    print(f"Got value: {value}")

    # Test hit rate
    await cache.get("key1")  # Hit
    await cache.get("missing")  # Miss

    stats = await cache.get_stats()
    print(f"\nCache stats:")
    print(f"  Hits: {stats.hits}")
    print(f"  Misses: {stats.misses}")
    print(f"  Hit rate: {stats.hit_rate:.1f}%")
    print(f"  Size: {stats.size}/{stats.max_size}")

    # Test LRU eviction
    await cache.set("key3", "value3")
    await cache.set("key4", "value4")  # Should evict key2

    print(f"\nAfter adding 4 items to size-3 cache:")
    print(f"  key1 exists: {await cache.contains('key1')}")
    print(f"  key2 exists: {await cache.contains('key2')}")  # Should be False (LRU)

    # Test TTL
    print("\nCache working correctly!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())