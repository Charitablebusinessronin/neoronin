"""
Pattern Query Engine

This module provides fast pattern matching queries with caching.
- Sub-100ms query performance with caching
- LRU cache with 1-hour TTL
- Performance metrics and monitoring
- Support for filtering by category, tags, success_rate

Author: Brooks (BMAD Dev Agent)
Created: 2026-01-26
Story: 3-4-fast-pattern-matching-query-engine
"""

import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.bmad.core.neo4j_client import Neo4jAsyncClient
from src.bmad.core.cache_manager import AsyncCacheManager, get_pattern_cache, CacheStats
from src.bmad.services.pattern_matcher import Pattern, PatternQuery

logger = logging.getLogger(__name__)


@dataclass
class QueryMetrics:
    """Metrics for a single query execution."""
    query_hash: str
    latency_ms: float
    cache_hit: bool
    cache_hit_rate: float
    result_count: int
    timestamp: datetime
    group_id: str
    filters: Dict[str, Any]


@dataclass
class PerformanceReport:
    """Overall performance report for pattern queries."""
    total_queries: int
    cache_hit_rate: float
    avg_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    slow_queries: int
    cache_stats: CacheStats
    timestamp: datetime


class PatternQueryEngine:
    """
    High-performance pattern query engine with caching.

    Features:
    - Sub-100ms queries via LRU caching
    - 1-hour TTL for cached patterns
    - Performance metrics tracking
    - Support for category, tags, and success_rate filtering
    - Thread-safe for concurrent access
    """

    # Performance thresholds
    LATENCY_THRESHOLD_MS = 100.0
    SLOW_QUERY_THRESHOLD_MS = 200.0

    def __init__(
        self,
        client: Neo4jAsyncClient,
        cache: Optional[AsyncCacheManager] = None
    ):
        """
        Initialize the pattern query engine.

        Args:
            client: Neo4j async client
            cache: Optional cache manager (uses global pattern cache if not provided)
        """
        self._client = client
        self._cache = cache or get_pattern_cache()
        self._query_history: List[QueryMetrics] = []
        self._history_lock = threading.RLock()
        self._slow_query_count = 0

    def _generate_query_hash(
        self,
        group_id: str,
        category: Optional[str],
        tags: Optional[List[str]],
        min_success_rate: float,
        limit: int
    ) -> str:
        """Generate a unique hash for the query parameters."""
        import hashlib
        params = f"{group_id}:{category}:{tags}:{min_success_rate}:{limit}"
        return hashlib.md5(params.encode()).hexdigest()[:12]

    async def fast_pattern_lookup(
        self,
        group_id: str,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        min_success_rate: float = 0.0,
        limit: int = 10,
        use_cache: bool = True
    ) -> List[Pattern]:
        """
        Fast pattern lookup with caching.

        Args:
            group_id: Project group for isolation
            category: Optional category filter
            tags: Optional tags filter (any match)
            min_success_rate: Minimum success rate filter
            limit: Maximum results
            use_cache: Whether to use cache (default: True)

        Returns:
            List of matching patterns
        """
        start_time = time.perf_counter()
        cache_hit = False
        query_hash = self._generate_query_hash(
            group_id, category, tags, min_success_rate, limit
        )

        # Try cache first
        if use_cache:
            cached_result = await self._cache.get(query_hash)
            if cached_result is not None:
                cache_hit = True
                result = cached_result
            else:
                result = await self._execute_query(
                    group_id, category, tags, min_success_rate, limit
                )
                await self._cache.set(query_hash, result)
        else:
            result = await self._execute_query(
                group_id, category, tags, min_success_rate, limit
            )

        latency_ms = (time.perf_counter() - start_time) * 1000

        # Log slow queries
        if latency_ms > self.LATENCY_THRESHOLD_MS:
            self._slow_query_count += 1
            logger.warning(
                f"Slow pattern query: {latency_ms:.2f}ms (threshold: {self.LATENCY_THRESHOLD_MS}ms)"
            )

        # Record metrics
        cache_stats = await self._cache.get_stats()
        metrics = QueryMetrics(
            query_hash=query_hash,
            latency_ms=latency_ms,
            cache_hit=cache_hit,
            cache_hit_rate=cache_stats.hit_rate,
            result_count=len(result),
            timestamp=datetime.now(timezone.utc),
            group_id=group_id,
            filters={
                "category": category,
                "tags": tags,
                "min_success_rate": min_success_rate,
                "limit": limit
            }
        )
        self._record_metrics(metrics)

        return result

    async def _execute_query(
        self,
        group_id: str,
        category: Optional[str],
        tags: Optional[List[str]],
        min_success_rate: float,
        limit: int
    ) -> List[Pattern]:
        """Execute the actual Neo4j query."""
        # Enforce max limit
        limit = min(limit, 50)

        # Build optimized Cypher query
        cypher = """
        MATCH (p:Pattern)
        WHERE p.group_id = $group_id OR p.group_id = 'global-coding-skills'
        """

        params = {"group_id": group_id}

        if category:
            cypher += " AND p.category = $category"
            params["category"] = category

        if min_success_rate > 0:
            cypher += " AND p.success_rate >= $min_success_rate"
            params["min_success_rate"] = min_success_rate

        if tags:
            cypher += " AND any(tag IN $tags WHERE tag IN p.tags)"
            params["tags"] = tags

        cypher += """
        RETURN p
        ORDER BY p.success_rate DESC, p.times_used DESC
        SKIP 0
        LIMIT $limit
        """

        params["limit"] = limit

        records = await self._client.execute_query(cypher, params)

        return self._parse_pattern_results(records)

    def _parse_pattern_results(self, records: List[Dict[str, Any]]) -> List[Pattern]:
        """Parse Neo4j records to Pattern objects."""
        patterns = []
        for record in records:
            p = record.get('p', {})
            if p:
                patterns.append(Pattern(
                    pattern_id=p.get('pattern_id', ''),
                    name=p.get('name', ''),
                    description=p.get('description', ''),
                    category=p.get('category', ''),
                    tags=p.get('tags', []),
                    success_rate=p.get('success_rate', 0.0),
                    times_used=p.get('times_used', 0),
                    group_id=p.get('group_id', 'global-coding-skills'),
                    scope=p.get('scope', 'global'),
                    confidence_score=p.get('confidence_score', 0.5),
                    metadata=p.get('metadata', {})
                ))
        return patterns

    def _record_metrics(self, metrics: QueryMetrics) -> None:
        """Record query metrics for monitoring."""
        with self._history_lock:
            self._query_history.append(metrics)
            # Keep only last 1000 metrics
            if len(self._query_history) > 1000:
                self._query_history = self._query_history[-1000:]

    async def get_performance_report(self) -> PerformanceReport:
        """
        Generate a performance report for pattern queries.

        Returns:
            PerformanceReport with latency stats and cache metrics
        """
        stats = await self._cache.get_stats()

        if not self._query_history:
            return PerformanceReport(
                total_queries=0,
                cache_hit_rate=0.0,
                avg_latency_ms=0.0,
                p95_latency_ms=0.0,
                p99_latency_ms=0.0,
                slow_queries=0,
                cache_stats=stats,
                timestamp=datetime.now(timezone.utc)
            )

        latencies = [m.latency_ms for m in self._query_history]
        latencies.sort()

        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        p95_idx = int(len(latencies) * 0.95)
        p99_idx = int(len(latencies) * 0.99)

        cache_hit_rate = stats.hit_rate

        report = PerformanceReport(
            total_queries=len(self._query_history),
            cache_hit_rate=cache_hit_rate,
            avg_latency_ms=avg_latency,
            p95_latency_ms=latencies[p95_idx] if latencies else 0,
            p99_latency_ms=latencies[p99_idx] if latencies else 0,
            slow_queries=self._slow_query_count,
            cache_stats=stats,
            timestamp=datetime.now(timezone.utc)
        )

        return report

    async def invalidate_cache(self, pattern_id: Optional[str] = None) -> int:
        """
        Invalidate cached pattern queries.

        Args:
            pattern_id: Optional specific pattern to invalidate

        Returns:
            Number of entries invalidated
        """
        count = await self._cache.invalidate_expired()
        with self._history_lock:
            self._query_history.clear()
        self._slow_query_count = 0
        if pattern_id:
            logger.info(f"Cache invalidated for pattern update")
        return count

    def get_cache_stats(self) -> CacheStats:
        """Get current cache statistics."""
        return self._cache._cache.get_stats()

    async def check_performance_compliance(self) -> Dict[str, Any]:
        """
        Check if the query engine meets performance targets.

        Returns:
            Dict with compliance status and metrics
        """
        report = await self.get_performance_report()

        compliant = (
            report.avg_latency_ms < self.LATENCY_THRESHOLD_MS and
            report.p95_latency_ms < self.LATENCY_THRESHOLD_MS * 2 and
            report.cache_hit_rate >= 70.0
        )

        return {
            "compliant": compliant,
            "avg_latency_ms": report.avg_latency_ms,
            "p95_latency_ms": report.p95_latency_ms,
            "cache_hit_rate": report.cache_hit_rate,
            "slow_queries": report.slow_queries,
            "threshold_ms": self.LATENCY_THRESHOLD_MS
        }


# Singleton instance
_query_engine: Optional[PatternQueryEngine] = None


def get_query_engine(client: Neo4jAsyncClient) -> PatternQueryEngine:
    """Get or create the global query engine instance."""
    global _query_engine
    if _query_engine is None:
        _query_engine = PatternQueryEngine(client)
    return _query_engine


async def main():
    """Quick test of the pattern query engine."""
    from src.bmad.core.neo4j_client import Neo4jAsyncClient

    async with Neo4jAsyncClient() as client:
        engine = PatternQueryEngine(client)

        print("Testing pattern query engine...")

        # Run pattern lookup
        patterns = await engine.fast_pattern_lookup(
            "global-coding-skills",
            category="architectural",
            limit=5
        )

        print(f"\nFound {len(patterns)} architectural patterns")

        # Check performance report
        report = await engine.get_performance_report()
        print(f"\nPerformance Report:")
        print(f"  Total queries: {report.total_queries}")
        print(f"  Avg latency: {report.avg_latency_ms:.2f}ms")
        print(f"  P95 latency: {report.p95_latency_ms:.2f}ms")
        print(f"  Cache hit rate: {report.cache_hit_rate:.1f}%")
        print(f"  Slow queries: {report.slow_queries}")

        # Check compliance
        compliance = await engine.check_performance_compliance()
        print(f"\nCompliance: {compliance['compliant']}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())