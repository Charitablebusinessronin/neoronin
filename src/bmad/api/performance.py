"""
Performance API Endpoints

This module provides REST API endpoints for performance monitoring.
- GET /api/performance/report - Performance report
- GET /api/performance/compliance - NFR compliance check
- GET /api/performance/cache/stats - Cache statistics
- GET /api/performance/metrics - Recent query metrics

Author: Brooks (BMAD Dev Agent)
Created: 2026-01-26
Story: 3-4-fast-pattern-matching-query-engine
"""

import logging
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.bmad.core.neo4j_client import Neo4jAsyncClient
from src.bmad.services.pattern_query_engine import (
    PatternQueryEngine,
    get_query_engine,
    PerformanceReport,
    QueryMetrics
)
from src.bmad.core.cache_manager import CacheStats

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/performance", tags=["performance"])


# Request/Response Models

class PerformanceReportResponse(BaseModel):
    """Response model for performance report."""
    total_queries: int
    cache_hit_rate: float
    avg_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    slow_queries: int
    cache_stats: dict
    timestamp: datetime


class PerformanceComplianceResponse(BaseModel):
    """Response for NFR compliance check."""
    compliant: bool
    avg_latency_ms: float
    p95_latency_ms: float
    cache_hit_rate: float
    slow_queries: int
    threshold_ms: float
    status: str


class CacheStatsResponse(BaseModel):
    """Response for cache statistics."""
    hits: int
    misses: int
    evictions: int
    size: int
    max_size: int
    hit_rate: float
    timestamp: datetime


class QueryMetricsResponse(BaseModel):
    """Response for recent query metrics."""
    query_hash: str
    latency_ms: float
    cache_hit: bool
    result_count: int
    timestamp: datetime
    group_id: str
    filters: dict


class HealthResponse(BaseModel):
    """Response for performance service health."""
    status: str
    service: str
    threshold_ms: float
    cache_enabled: bool


# Endpoints

@router.get("/report", response_model=PerformanceReportResponse)
async def get_performance_report(
    engine: PatternQueryEngine = None
):
    """
    Get performance report for pattern queries.

    Returns latency statistics, cache metrics, and query counts.
    """
    if not engine:
        raise HTTPException(status_code=503, detail="Service not available")

    try:
        report = await engine.get_performance_report()

        return PerformanceReportResponse(
            total_queries=report.total_queries,
            cache_hit_rate=report.cache_hit_rate,
            avg_latency_ms=report.avg_latency_ms,
            p95_latency_ms=report.p95_latency_ms,
            p99_latency_ms=report.p99_latency_ms,
            slow_queries=report.slow_queries,
            cache_stats={
                "hits": report.cache_stats.hits,
                "misses": report.cache_stats.misses,
                "evictions": report.cache_stats.evictions,
                "size": report.cache_stats.size,
                "max_size": report.cache_stats.max_size,
                "hit_rate": report.cache_stats.hit_rate
            },
            timestamp=report.timestamp
        )

    except Exception as e:
        logger.error(f"Failed to get performance report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/compliance", response_model=PerformanceComplianceResponse)
async def check_performance_compliance(
    engine: PatternQueryEngine = None
):
    """
    Check if the system meets NFR performance targets.

    Returns compliance status for:
    - Average latency < 100ms
    - P95 latency < 200ms
    - Cache hit rate > 70%
    """
    if not engine:
        raise HTTPException(status_code=503, detail="Service not available")

    try:
        compliance = await engine.check_performance_compliance()

        status = "Compliant" if compliance["compliant"] else "Non-Compliant"

        return PerformanceComplianceResponse(
            compliant=compliance["compliant"],
            avg_latency_ms=compliance["avg_latency_ms"],
            p95_latency_ms=compliance["p95_latency_ms"],
            cache_hit_rate=compliance["cache_hit_rate"],
            slow_queries=compliance["slow_queries"],
            threshold_ms=compliance["threshold_ms"],
            status=status
        )

    except Exception as e:
        logger.error(f"Failed to check compliance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cache/stats", response_model=CacheStatsResponse)
async def get_cache_stats(
    engine: PatternQueryEngine = None
):
    """
    Get cache statistics for pattern queries.

    Returns hit/miss counts, eviction counts, and current size.
    """
    if not engine:
        raise HTTPException(status_code=503, detail="Service not available")

    try:
        stats = engine.get_cache_stats()

        return CacheStatsResponse(
            hits=stats.hits,
            misses=stats.misses,
            evictions=stats.evictions,
            size=stats.size,
            max_size=stats.max_size,
            hit_rate=stats.hit_rate,
            timestamp=datetime.now(timezone.utc)
        )

    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics", response_model=List[QueryMetricsResponse])
async def get_query_metrics(
    limit: int = Field(default=20, ge=1, le=100, description="Maximum metrics to return"),
    engine: PatternQueryEngine = None
):
    """
    Get recent query metrics.

    Returns the most recent query executions with latency and cache info.
    """
    if not engine:
        raise HTTPException(status_code=503, detail="Service not available")

    try:
        # Access the private query history (limited access)
        with engine._history_lock:
            recent_metrics = engine._query_history[-limit:]

        return [
            QueryMetricsResponse(
                query_hash=m.query_hash,
                latency_ms=m.latency_ms,
                cache_hit=m.cache_hit,
                result_count=m.result_count,
                timestamp=m.timestamp,
                group_id=m.group_id,
                filters=m.filters
            )
            for m in recent_metrics
        ]

    except Exception as e:
        logger.error(f"Failed to get query metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cache/invalidate")
async def invalidate_cache(
    engine: PatternQueryEngine = None
):
    """
    Invalidate the pattern cache.

    Use when patterns are updated to ensure fresh results.
    """
    if not engine:
        raise HTTPException(status_code=503, detail="Service not available")

    try:
        count = await engine.invalidate_cache()
        logger.info(f"Cache invalidated, removed {count} entries")

        return {
            "status": "success",
            "entries_invalidated": count,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to invalidate cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", response_model=HealthResponse)
async def performance_health():
    """Health check for performance service."""
    return {
        "status": "healthy",
        "service": "pattern_query_engine",
        "threshold_ms": PatternQueryEngine.LATENCY_THRESHOLD_MS,
        "cache_enabled": True
    }


# Dependency factory for FastAPI

def get_pattern_query_engine(
    client: Neo4jAsyncClient
) -> PatternQueryEngine:
    """Factory for PatternQueryEngine dependency."""
    return get_query_engine(client)