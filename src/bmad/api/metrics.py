"""
Metrics API Endpoints

This module provides REST API endpoints for Prometheus metrics.
- GET /metrics - Prometheus scraping endpoint
- GET /api/metrics/summary - Human-readable metrics summary
- POST /api/metrics/refresh - Force metrics refresh

Author: Brooks (BMAD Dev Agent)
Created: 2026-01-26
Story: 5-1-export-learning-metrics-to-prometheus
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from src.bmad.core.neo4j_client import Neo4jAsyncClient
from src.bmad.services.metrics_exporter import (
    MetricsExporter,
    MetricsScheduler,
    create_metrics_exporter
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/metrics", tags=["metrics"])

# Global instances
_metrics_exporter: Optional[MetricsExporter] = None
_metrics_scheduler: Optional[MetricsScheduler] = None


def get_metrics_exporter(
    client: Neo4jAsyncClient
) -> MetricsExporter:
    """Factory for MetricsExporter dependency."""
    global _metrics_exporter
    if _metrics_exporter is None:
        _metrics_exporter = create_metrics_exporter(client)
    return _metrics_exporter


def get_metrics_scheduler(
    client: Neo4jAsyncClient
) -> MetricsScheduler:
    """Factory for MetricsScheduler dependency."""
    global _metrics_scheduler, _metrics_exporter

    if _metrics_scheduler is None:
        if _metrics_exporter is None:
            _metrics_exporter = create_metrics_exporter(client)
        _metrics_scheduler = MetricsScheduler(_metrics_exporter)

    return _metrics_scheduler


# Request/Response Models

class MetricsSummaryResponse(BaseModel):
    """Response model for metrics summary."""
    last_update: Optional[str]
    update_interval_seconds: int
    insight_count_by_domain: dict
    avg_confidence: float
    health_status: str
    orphaned_agents: int
    active_patterns: dict


class RefreshResponse(BaseModel):
    """Response model for metrics refresh."""
    status: str
    update_time_ms: float
    timestamp: str


class HealthResponse(BaseModel):
    """Response model for metrics service health."""
    status: str
    exporter_ready: bool
    scheduler_running: bool
    last_update: Optional[str]


# Endpoints

@router.get("/summary", response_model=MetricsSummaryResponse)
async def get_metrics_summary(
    client: Neo4jAsyncClient
):
    """
    Get human-readable summary of all metrics.

    Returns current values of all BMAD learning metrics.
    """
    try:
        exporter = get_metrics_exporter(client)
        summary = exporter.get_metrics_summary()

        return MetricsSummaryResponse(
            last_update=summary.get("last_update"),
            update_interval_seconds=summary.get("update_interval_seconds", 300),
            insight_count_by_domain=summary.get("insight_count_by_domain", {}),
            avg_confidence=summary.get("avg_confidence", 0.0),
            health_status=summary.get("health_status", "unknown"),
            orphaned_agents=summary.get("orphaned_agents", 0),
            active_patterns=summary.get("active_patterns", {})
        )

    except Exception as e:
        logger.error(f"Failed to get metrics summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_metrics(
    background_tasks: BackgroundTasks,
    client: Neo4jAsyncClient
):
    """
    Force refresh all metrics from Neo4j.

    This triggers an immediate update of all metrics.
    """
    try:
        exporter = get_metrics_exporter(client)
        result = await exporter.update_all_metrics()

        return RefreshResponse(
            status=result.get("status", "unknown"),
            update_time_ms=result.get("update_time_ms", 0.0),
            timestamp=result.get("timestamp", datetime.now(timezone.utc).isoformat())
        )

    except Exception as e:
        logger.error(f"Failed to refresh metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", response_model=HealthResponse)
async def metrics_health(
    client: Neo4jAsyncClient
):
    """
    Check health of the metrics service.
    """
    try:
        exporter = get_metrics_exporter(client)
        scheduler = get_metrics_scheduler(client)

        return HealthResponse(
            status="healthy",
            exporter_ready=exporter is not None,
            scheduler_running=scheduler._running if scheduler else False,
            last_update=exporter.last_update.isoformat() if exporter and exporter.last_update else None
        )

    except Exception as e:
        logger.error(f"Metrics health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            exporter_ready=False,
            scheduler_running=False,
            last_update=None
        )


# Prometheus-compatible endpoint

@router.get("/prometheus")
async def prometheus_metrics(
    client: Neo4jAsyncClient
):
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus exposition format.
    This endpoint is designed to be scraped by Prometheus.
    """
    try:
        exporter = get_metrics_exporter(client)

        # Check if we need to update metrics first
        if exporter.last_update is None:
            await exporter.update_all_metrics()

        # Return metrics in Prometheus format
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

        metrics_output = generate_latest()

        return Response(
            content=metrics_output,
            media_type=CONTENT_TYPE_LATEST
        )

    except Exception as e:
        logger.error(f"Failed to generate Prometheus metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Import Response at the end to avoid circular imports
from fastapi import Response


# Background scheduler management

async def start_metrics_scheduler(
    interval_seconds: int = 300,
    client: Optional[Neo4jAsyncClient] = None
) -> None:
    """
    Start the background metrics scheduler.

    Args:
        interval_seconds: How often to update metrics
        client: Neo4j client (optional, creates new if not provided)
    """
    global _metrics_exporter, _metrics_scheduler

    if client is None:
        client = Neo4jAsyncClient()
        await client.initialize()

    if _metrics_exporter is None:
        _metrics_exporter = create_metrics_exporter(client)

    if _metrics_scheduler is None:
        _metrics_scheduler = MetricsScheduler(_metrics_exporter)

    await _metrics_scheduler.start(interval_seconds)


def stop_metrics_scheduler() -> None:
    """Stop the background metrics scheduler."""
    global _metrics_scheduler
    if _metrics_scheduler:
        _metrics_scheduler.stop()
        _metrics_scheduler = None


if __name__ == "__main__":
    import uvicorn
    from src.bmad.core.neo4j_client import Neo4jAsyncClient
    from dotenv import load_dotenv
    load_dotenv()

    async def run_server():
        """Run the metrics API server."""
        from fastapi import FastAPI
        from fastapi.middleware.cors import CORSMiddleware

        app = FastAPI(title="BMAD Metrics API")

        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )

        @app.on_event("startup")
        async def startup():
            await start_metrics_scheduler(interval_seconds=300)

        @app.on_event("shutdown")
        async def shutdown():
            stop_metrics_scheduler()

        app.include_router(router)

        @app.get("/metrics")
        async def prometheus_scrape():
            """Prometheus scraping endpoint."""
            return prometheus_metrics()

        # Start server
        config = uvicorn.Config(app, host="0.0.0.0", port=9090)
        server = uvicorn.Server(config)
        await server.serve()

    asyncio.run(run_server())