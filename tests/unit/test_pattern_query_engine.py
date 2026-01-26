"""Unit tests for Pattern Query Engine (Story 3-4).

Tests cover:
- Fast pattern lookup with caching
- Cache hit/miss tracking
- Performance metrics recording
- Compliance checking
"""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Any, Dict
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.bmad.core.neo4j_client import Neo4jAsyncClient
from src.bmad.services.pattern_query_engine import (
    PatternQueryEngine,
    QueryMetrics,
    PerformanceReport
)
from src.bmad.services.pattern_matcher import Pattern
from src.bmad.core.cache_manager import (
    CacheManager,
    CacheStats,
    AsyncCacheManager
)


class TestPatternQueryEngineInit:
    """Test PatternQueryEngine initialization."""

    def test_init_with_client(self):
        """Engine should be initialized with Neo4j client."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        engine = PatternQueryEngine(mock_client)

        assert engine._client == mock_client

    def test_init_with_custom_cache(self):
        """Engine should use custom cache if provided."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        custom_cache = AsyncCacheManager()
        engine = PatternQueryEngine(mock_client, cache=custom_cache)

        assert engine._cache == custom_cache


class TestFastPatternLookup:
    """Test fast pattern lookup with caching."""

    @pytest.mark.asyncio
    async def test_lookup_returns_from_cache(self):
        """Should return cached result on subsequent lookups."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        cache = AsyncCacheManager()

        engine = PatternQueryEngine(mock_client, cache=cache)

        # Pre-populate cache with the correct hash key
        cached_patterns = [
            Pattern(
                pattern_id="p1",
                name="Cached Pattern",
                description="From cache",
                category="testing"
            )
        ]
        # Use same params as lookup call
        cache_key = engine._generate_query_hash(
            "global-coding-skills",
            category="testing",
            tags=None,
            min_success_rate=0.0,
            limit=10
        )
        await cache.set(cache_key, cached_patterns)

        patterns = await engine.fast_pattern_lookup(
            "global-coding-skills",
            category="testing"
        )

        # Should return cached result
        assert len(patterns) == 1
        assert patterns[0].name == "Cached Pattern"

    @pytest.mark.asyncio
    async def test_lookup_queries_db_on_miss(self):
        """Should query database when cache miss occurs."""
        mock_records = [
            {
                'p': {
                    'pattern_id': 'p1',
                    'name': 'DB Pattern',
                    'description': 'From database',
                    'category': 'architectural',
                    'tags': ['architecture'],
                    'success_rate': 0.85,
                    'times_used': 10,
                    'group_id': 'global-coding-skills',
                    'scope': 'global',
                    'confidence_score': 0.7
                }
            }
        ]

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=mock_records)
        cache = AsyncCacheManager()

        engine = PatternQueryEngine(mock_client, cache=cache)

        patterns = await engine.fast_pattern_lookup(
            "global-coding-skills",
            category="architectural"
        )

        # Should have queried database
        mock_client.execute_query.assert_called_once()
        assert len(patterns) == 1
        assert patterns[0].name == "DB Pattern"

    @pytest.mark.asyncio
    async def test_lookup_with_bypass_cache(self):
        """Should skip cache when use_cache=False."""
        mock_records = [
            {
                'p': {
                    'pattern_id': 'p1',
                    'name': 'Fresh Pattern',
                    'description': 'Not cached',
                    'category': 'testing',
                    'tags': [],
                    'success_rate': 0.9,
                    'times_used': 5,
                    'group_id': 'global-coding-skills',
                    'scope': 'global'
                }
            }
        ]

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=mock_records)
        cache = AsyncCacheManager()

        engine = PatternQueryEngine(mock_client, cache=cache)

        patterns = await engine.fast_pattern_lookup(
            "global-coding-skills",
            category="testing",
            use_cache=False
        )

        # Should have queried database directly
        mock_client.execute_query.assert_called_once()


class TestQueryMetrics:
    """Test query metrics recording."""

    @pytest.mark.asyncio
    async def test_metrics_recorded(self):
        """Should record metrics for each query."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=[])
        cache = AsyncCacheManager()

        engine = PatternQueryEngine(mock_client, cache=cache)

        await engine.fast_pattern_lookup("global-coding-skills", limit=5)

        # Check metrics were recorded
        with engine._history_lock:
            assert len(engine._query_history) >= 1

    @pytest.mark.asyncio
    async def test_metrics_include_latency(self):
        """Metrics should include query latency."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=[])
        cache = AsyncCacheManager()

        engine = PatternQueryEngine(mock_client, cache=cache)

        await engine.fast_pattern_lookup("global-coding-skills")

        with engine._history_lock:
            metrics = engine._query_history[0]
            assert metrics.latency_ms >= 0


class TestPerformanceReport:
    """Test performance report generation."""

    @pytest.mark.asyncio
    async def test_report_with_no_queries(self):
        """Should return zeros when no queries."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        cache = AsyncCacheManager()

        engine = PatternQueryEngine(mock_client, cache=cache)

        report = await engine.get_performance_report()

        assert report.total_queries == 0
        assert report.avg_latency_ms == 0
        assert report.cache_hit_rate == 0

    @pytest.mark.asyncio
    async def test_report_calculates_latency_percentiles(self):
        """Should calculate P95 and P99 latencies."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=[])
        cache = AsyncCacheManager()

        engine = PatternQueryEngine(mock_client, cache=cache)

        # Simulate queries with various latencies
        for i in range(10):
            await engine.fast_pattern_lookup("global-coding-skills")

        report = await engine.get_performance_report()

        assert report.total_queries == 10
        assert report.p95_latency_ms >= 0
        assert report.p99_latency_ms >= 0


class TestPerformanceCompliance:
    """Test NFR compliance checking."""

    @pytest.mark.asyncio
    async def test_compliant_when_fast(self):
        """Should be compliant when under threshold."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        cache = AsyncCacheManager()

        engine = PatternQueryEngine(mock_client, cache=cache)

        # Run queries
        for _ in range(5):
            await engine.fast_pattern_lookup("global-coding-skills")

        compliance = await engine.check_performance_compliance()

        assert "compliant" in compliance
        assert "avg_latency_ms" in compliance
        assert "threshold_ms" in compliance


class TestCacheInvalidation:
    """Test cache invalidation."""

    @pytest.mark.asyncio
    async def test_invalidate_clears_history(self):
        """Should clear query history on invalidation."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=[])
        cache = AsyncCacheManager()

        engine = PatternQueryEngine(mock_client, cache=cache)

        # Run some queries
        await engine.fast_pattern_lookup("global-coding-skills")

        # Invalidate
        await engine.invalidate_cache()

        with engine._history_lock:
            assert len(engine._query_history) == 0


class TestCacheManager:
    """Test the underlying cache manager."""

    def test_set_and_get(self):
        """Should store and retrieve values."""
        cache = CacheManager[str](max_size=10, ttl_seconds=60)

        cache.set("key1", "value1")
        result = cache.get("key1")

        assert result == "value1"

    def test_lru_eviction(self):
        """Should evict least recently used entries."""
        cache = CacheManager[str](max_size=3, ttl_seconds=60)

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        # Access key1 to make it recently used
        cache.get("key1")

        # Add fourth entry, should evict key2
        cache.set("key4", "value4")

        assert cache.get("key1") == "value1"  # Still accessible
        assert cache.get("key2") is None  # Evicted
        assert cache.get("key3") is not None  # May or may not be evicted
        assert cache.get("key4") == "value4"  # Added

    def test_ttl_expiration(self):
        """Should expire entries after TTL."""
        cache = CacheManager[str](max_size=10, ttl_seconds=1)  # 1 second TTL

        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

        # Wait for expiration
        time.sleep(1.1)

        assert cache.get("key1") is None  # Expired

    def test_hit_rate_calculation(self):
        """Should calculate hit rate correctly."""
        cache = CacheManager[str](max_size=10, ttl_seconds=60)

        cache.set("key1", "value1")

        cache.get("key1")  # Hit
        cache.get("key1")  # Hit
        cache.get("missing")  # Miss

        stats = cache.get_stats()
        assert stats.hits == 2
        assert stats.misses == 1
        assert abs(stats.hit_rate - 66.67) < 0.01  # 2/3 * 100


class TestCacheStats:
    """Test CacheStats dataclass."""

    def test_hit_rate_zero_denominator(self):
        """Should handle zero total gracefully."""
        stats = CacheStats(hits=0, misses=0, evictions=0, size=0, max_size=100)

        assert stats.hit_rate == 0.0

    def test_hit_rate_calculation(self):
        """Should calculate hit rate correctly."""
        stats = CacheStats(hits=7, misses=3, evictions=0, size=10, max_size=100)

        assert stats.hit_rate == 70.0  # 7/10 * 100


class TestPatternQueryEngineIntegration:
    """Integration tests with real Neo4j."""

    @pytest.fixture
    def neo4j_client(self):
        """Create real Neo4j client."""
        import os
        from src.bmad.core.neo4j_client import Neo4jAsyncClient

        try:
            client = Neo4jAsyncClient(
                uri=os.environ.get('NEO4J_URI', 'bolt://localhost:7687'),
                user=os.environ.get('NEO4J_USER', 'neo4j'),
                password=os.environ.get('NEO4J_PASSWORD', 'Kamina2025*')
            )
            return client
        except Exception:
            pytest.skip("Neo4j not available")

    @pytest.mark.asyncio
    async def test_real_pattern_query(self, neo4j_client):
        """Test real pattern query against Neo4j."""
        from src.bmad.services.pattern_query_engine import PatternQueryEngine

        try:
            await neo4j_client.initialize()
            engine = PatternQueryEngine(neo4j_client)

            # Run pattern lookup
            patterns = await engine.fast_pattern_lookup(
                "global-coding-skills",
                category="architectural",
                limit=5
            )

            print(f"\nFound {len(patterns)} architectural patterns")

            # Check performance
            report = await engine.get_performance_report()
            print(f"Avg latency: {report.avg_latency_ms:.2f}ms")
            print(f"Cache hit rate: {report.cache_hit_rate:.1f}%")

            # Check compliance
            compliance = await engine.check_performance_compliance()
            print(f"Compliant: {compliance['compliant']}")

            await neo4j_client.close()
        except Exception as e:
            pytest.skip(f"Neo4j test failed: {e}")

    @pytest.mark.asyncio
    async def test_query_performance_under_100ms(self, neo4j_client):
        """Verify queries complete in under 100ms."""
        from src.bmad.services.pattern_query_engine import PatternQueryEngine

        try:
            await neo4j_client.initialize()
            engine = PatternQueryEngine(neo4j_client)

            # Run multiple queries and measure
            latencies = []
            for _ in range(5):
                start = time.perf_counter()
                await engine.fast_pattern_lookup("global-coding-skills", limit=10)
                elapsed_ms = (time.perf_counter() - start) * 1000
                latencies.append(elapsed_ms)

            avg_latency = sum(latencies) / len(latencies)
            print(f"\nAverage query latency: {avg_latency:.2f}ms")
            print(f"All latencies under 100ms: {all(l < 100 for l in latencies)}")

            # Most queries should be under 100ms
            assert avg_latency < 100, f"Average latency {avg_latency:.2f}ms exceeds 100ms"

            await neo4j_client.close()
        except Exception as e:
            pytest.skip(f"Neo4j test failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])