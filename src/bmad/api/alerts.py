"""
Alerts API Endpoints

This module provides REST API endpoints for accessing and managing pattern contradiction alerts.
- GET /api/alerts - Get all pending alerts
- GET /api/alerts/{alert_id} - Get specific alert details
- POST /api/alerts/{alert_id}/resolve - Resolve an alert
- POST /api/alerts/detect - Trigger manual contradiction detection

Author: Brooks (BMAD Dev Agent)
Created: 2026-01-26
Story: 4-5-escalate-pattern-contradictions-for-review
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.bmad.core.neo4j_client import Neo4jAsyncClient
from src.bmad.services.contradiction_detector import (
    ContradictionDetectorService,
    ContradictionDetectionResult
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


# Request/Response Models

class AlertResponse(BaseModel):
    """Response model for an alert."""
    alert_id: str
    alert_type: str
    insights: List[str]
    confidence_scores: List[float]
    conflict_reason: str
    requires_human_review: bool
    status: str
    created_at: str
    applies_to: Optional[str] = None
    resolved_at: Optional[str] = None
    resolved_by: Optional[str] = None
    resolution_notes: Optional[str] = None


class AlertListResponse(BaseModel):
    """Response model for list of alerts."""
    count: int
    alerts: List[AlertResponse]


class ResolveAlertRequest(BaseModel):
    """Request model for resolving an alert."""
    resolution_notes: str
    resolved_by: str = "manual"


class ResolveAlertResponse(BaseModel):
    """Response model for alert resolution."""
    alert_id: str
    resolved: bool
    timestamp: datetime


class DetectRequest(BaseModel):
    """Request model for triggering detection."""
    applies_to: Optional[str] = None


class DetectResponse(BaseModel):
    """Response model for detection results."""
    contradictions_found: int
    alerts_created: int
    existing_alerts: int
    processing_time_ms: float
    timestamp: datetime


# Dependency factory

def get_contradiction_detector_service(
    client: Neo4jAsyncClient
) -> ContradictionDetectorService:
    """Factory for ContradictionDetectorService dependency."""
    return ContradictionDetectorService(client)


# Endpoints

@router.get("", response_model=AlertListResponse)
async def get_alerts(
    status: str = Query("pending", description="Filter by status (pending/resolved/all)"),
    alert_type: str = Query(None, description="Filter by alert type"),
    limit: int = Query(50, ge=1, le=100, description="Maximum results"),
    service: ContradictionDetectorService = None
):
    """
    Get all alerts for review.

    Returns pending alerts by default. Use status=all to see resolved alerts too.
    """
    if not service:
        raise HTTPException(status_code=503, detail="Service not available")

    try:
        # Get pending alerts
        alerts = await service.get_pending_alerts(limit)

        # Filter by status if needed
        if status != "all":
            alerts = [a for a in alerts if a.get("status", "") == status]

        return AlertListResponse(
            count=len(alerts),
            alerts=[AlertResponse(**alert) for alert in alerts]
        )

    except Exception as e:
        logger.error(f"Failed to get alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: str,
    service: ContradictionDetectorService = None
):
    """
    Get details of a specific alert.
    """
    if not service:
        raise HTTPException(status_code=503, detail="Service not available")

    try:
        # Get all alerts and find the specific one
        alerts = await service.get_pending_alerts(100)

        for alert in alerts:
            if alert.get("alert_id") == alert_id:
                return AlertResponse(**alert)

        # Check if it's a resolved alert
        query = """
        MATCH (alert:Alert {alert_id: $alert_id})
        RETURN alert
        """

        results = await service._client.execute_query(query, {"alert_id": alert_id})

        if results and results[0].get('alert'):
            alert_data = results[0]['alert']
            return AlertResponse(
                alert_id=alert_data.get('alert_id', ''),
                alert_type=alert_data.get('type', ''),
                insights=alert_data.get('insights', []),
                confidence_scores=alert_data.get('confidence_scores', []),
                conflict_reason=alert_data.get('conflict_reason', ''),
                requires_human_review=alert_data.get('requires_human_review', False),
                status=alert_data.get('status', ''),
                created_at=alert_data.get('created_at', ''),
                applies_to=alert_data.get('applies_to'),
                resolved_at=alert_data.get('resolved_at'),
                resolved_by=alert_data.get('resolved_by'),
                resolution_notes=alert_data.get('resolution_notes')
            )

        raise HTTPException(status_code=404, detail="Alert not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get alert {alert_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{alert_id}/resolve", response_model=ResolveAlertResponse)
async def resolve_alert(
    alert_id: str,
    request: ResolveAlertRequest,
    service: ContradictionDetectorService = None
):
    """
    Resolve a pending alert.

    Requires resolution_notes explaining how the contradiction was addressed.
    """
    if not service:
        raise HTTPException(status_code=503, detail="Service not available")

    if not request.resolution_notes:
        raise HTTPException(status_code=400, detail="resolution_notes is required")

    try:
        resolved = await service.resolve_alert(
            alert_id=alert_id,
            resolution_notes=request.resolution_notes,
            resolved_by=request.resolved_by
        )

        if not resolved:
            raise HTTPException(status_code=404, detail="Alert not found or already resolved")

        return ResolveAlertResponse(
            alert_id=alert_id,
            resolved=True,
            timestamp=datetime.now(timezone.utc)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resolve alert {alert_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/detect", response_model=DetectResponse)
async def trigger_detection(
    request: DetectRequest = None,
    service: ContradictionDetectorService = None
):
    """
    Manually trigger contradiction detection.

    Optionally specify applies_to to filter by domain.
    """
    if not service:
        raise HTTPException(status_code=503, detail="Service not available")

    try:
        applies_to = request.applies_to if request else None
        result = await service.run_detection_cycle(applies_to)

        return DetectResponse(
            contradictions_found=result.contradictions_found,
            alerts_created=result.alerts_created,
            existing_alerts=result.existing_alerts,
            processing_time_ms=result.processing_time_ms,
            timestamp=result.timestamp
        )

    except Exception as e:
        logger.error(f"Contradiction detection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/summary")
async def get_alert_stats(
    service: ContradictionDetectorService = None
):
    """
    Get summary statistics for alerts.
    """
    if not service:
        raise HTTPException(status_code=503, detail="Service not available")

    try:
        # Count by status
        query = """
        MATCH (alert:Alert)
        WHERE alert.type = 'contradiction'
        RETURN alert.status as status, count(alert) as count
        """

        results = await service._client.execute_query(query, {})

        stats = {"pending": 0, "resolved": 0, "total": 0}
        for r in results:
            status = r.get('status', 'unknown')
            count = r.get('count', 0)
            stats[status] = count
            stats['total'] += count

        return {
            "by_status": stats,
            "confidence_delta_threshold": ContradictionDetectorService.CONFIDENCE_DELTA_THRESHOLD
        }

    except Exception as e:
        logger.error(f"Failed to get alert stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Health check endpoint

@router.get("/health")
async def alerts_health():
    """Health check for alerts API."""
    return {
        "status": "healthy",
        "service": "contradiction_detector",
        "confidence_delta_threshold": ContradictionDetectorService.CONFIDENCE_DELTA_THRESHOLD
    }