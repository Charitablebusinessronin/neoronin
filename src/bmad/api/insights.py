"""
Insights API Endpoints

This module provides REST API endpoints for accessing shared insights.
- GET /api/agents/{agent_name}/shared-insights - Get insights shared to an agent
- GET /api/insights/pending - Check pending knowledge transfers
- POST /api/insights/transfer - Trigger manual knowledge transfer

Author: Brooks (BMAD Dev Agent)
Created: 2026-01-26
Story: 2-3-share-high-confidence-insights-across-agents
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.bmad.core.neo4j_client import Neo4jAsyncClient
from src.bmad.services.knowledge_transfer import (
    KnowledgeTransferService,
    SharedInsight
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/insights", tags=["insights"])


# Request/Response Models

class SharedInsightResponse(BaseModel):
    """Response model for a shared insight."""
    insight_id: str
    rule: str
    category: str
    confidence_score: float
    success_rate: float
    learned_by: str
    learned_at: datetime
    teacher_agent: str

    class Config:
        from_attributes = True


class KnowledgeTransferRequest(BaseModel):
    """Request model for triggering knowledge transfer."""
    group_id: str = "global-coding-skills"


class KnowledgeTransferResponse(BaseModel):
    """Response model for knowledge transfer operation."""
    group_id: str
    insights_shared: int
    agents_updated: int
    latency_ms: float
    timestamp: datetime


class PendingSharesResponse(BaseModel):
    """Response model for pending shares count."""
    group_id: str
    insights_pending: int
    agents_waiting: int
    total_shares_needed: int


class CycleRunResponse(BaseModel):
    """Response model for running a full cycle."""
    groups_processed: int
    total_insights_shared: int
    total_agents_updated: int
    duration_seconds: float
    group_results: List[dict]
    timestamp: datetime


# Dependency factory

def get_knowledge_transfer_service(
    client: Neo4jAsyncClient
) -> KnowledgeTransferService:
    """Factory for KnowledgeTransferService dependency."""
    return KnowledgeTransferService(client)


# Endpoints

@router.get("/shared/{agent_name}", response_model=List[SharedInsightResponse])
async def get_shared_insights(
    agent_name: str,
    group_id: str = Query(..., description="Project group ID for isolation"),
    teacher_name: Optional[str] = Query(None, description="Filter by teacher agent"),
    min_confidence: float = Query(0.8, ge=0.0, le=1.0, description="Minimum confidence score"),
    limit: int = Query(20, ge=1, le=50, description="Maximum results"),
    service: KnowledgeTransferService = None
):
    """
    Get insights that have been shared to an agent from other agents.

    Only returns insights with confidence_score >= 0.8 that were shared
    through the daily knowledge transfer process.
    """
    if not service:
        raise HTTPException(status_code=503, detail="Service not available")

    try:
        insights = await service.get_shared_insights(
            agent_name=agent_name,
            group_id=group_id,
            teacher_name=teacher_name,
            min_confidence=min_confidence,
            limit=limit
        )

        return [
            SharedInsightResponse(
                insight_id=i.insight_id,
                rule=i.rule,
                category=i.category,
                confidence_score=i.confidence_score,
                success_rate=i.success_rate,
                learned_by=i.learned_by,
                learned_at=i.learned_at,
                teacher_agent=i.teacher_agent
            )
            for i in insights
        ]

    except Exception as e:
        logger.error(f"Failed to get shared insights for {agent_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pending/{group_id}", response_model=PendingSharesResponse)
async def get_pending_shares(
    group_id: str,
    service: KnowledgeTransferService = None
):
    """
    Check how many insights are pending to be shared for a group.

    Returns counts of:
    - insights_pending: Unique insights not yet shared
    - agents_waiting: Agents waiting to receive insights
    - total_shares_needed: Total relationship creations needed
    """
    if not service:
        raise HTTPException(status_code=503, detail="Service not available")

    try:
        pending = await service.count_pending_shares(group_id)

        return PendingSharesResponse(
            group_id=group_id,
            insights_pending=pending['insights_pending'],
            agents_waiting=pending['agents_waiting'],
            total_shares_needed=pending['total_shares_needed']
        )

    except Exception as e:
        logger.error(f"Failed to check pending shares for {group_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/transfer", response_model=KnowledgeTransferResponse)
async def trigger_knowledge_transfer(
    request: KnowledgeTransferRequest,
    service: KnowledgeTransferService = None
):
    """
    Manually trigger knowledge transfer for a specific group.

    This will share all high-confidence insights (confidence_score >= 0.8)
    from one agent to all other agents in the same group.
    """
    if not service:
        raise HTTPException(status_code=503, detail="Service not available")

    try:
        result = await service.share_high_confidence_insights(request.group_id)

        return KnowledgeTransferResponse(
            group_id=request.group_id,
            insights_shared=result.insights_shared,
            agents_updated=result.agents_updated,
            latency_ms=result.latency_ms,
            timestamp=datetime.now(timezone.utc)
        )

    except Exception as e:
        logger.error(f"Knowledge transfer failed for {request.group_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cycle/run", response_model=CycleRunResponse)
async def run_full_cycle(
    service: KnowledgeTransferService = None
):
    """
    Manually trigger a full knowledge transfer cycle.

    Processes all configured groups and shares high-confidence insights.
    Typically runs automatically at 2:10 AM daily.
    """
    if not service:
        raise HTTPException(status_code=503, detail="Service not available")

    from src.bmad.tasks.knowledge_transfer_cycle import KnowledgeTransferCycle

    try:
        # Create cycle and run it
        # Note: In production, use the singleton instance
        cycle = KnowledgeTransferCycle(service._client)
        cycle.add_group("global-coding-skills")

        result = await cycle.run_cycle()

        return CycleRunResponse(
            groups_processed=result['groups_processed'],
            total_insights_shared=result['total_insights_shared'],
            total_agents_updated=result['total_agents_updated'],
            duration_seconds=result['duration_seconds'],
            group_results=result['group_results'],
            timestamp=datetime.now(timezone.utc)
        )

    except Exception as e:
        logger.error(f"Knowledge transfer cycle failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/to-share/{group_id}")
async def get_insights_to_share(
    group_id: str,
    teacher_name: Optional[str] = Query(None, description="Filter by teacher agent"),
    service: KnowledgeTransferService = None
):
    """
    Get list of insights that will be shared (high-confidence).

    Returns all insights in the group that meet the sharing criteria
    (confidence_score >= 0.8, success_rate >= 0.8).
    """
    if not service:
        raise HTTPException(status_code=503, detail="Service not available")

    try:
        insights = await service.get_insights_to_share(
            group_id=group_id,
            teacher_name=teacher_name
        )

        return {
            "group_id": group_id,
            "count": len(insights),
            "threshold": KnowledgeTransferService.CONFIDENCE_THRESHOLD,
            "insights": [
                {
                    "insight_id": i.insight_id,
                    "rule": i.rule,
                    "category": i.category,
                    "confidence_score": i.confidence_score,
                    "success_rate": i.success_rate,
                    "learned_by": i.learned_by,
                    "learned_at": i.learned_at.isoformat()
                }
                for i in insights
            ]
        }

    except Exception as e:
        logger.error(f"Failed to get insights to share for {group_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Health check endpoint

@router.get("/health")
async def insights_health():
    """Health check for insights API."""
    return {
        "status": "healthy",
        "service": "knowledge_transfer",
        "confidence_threshold": KnowledgeTransferService.CONFIDENCE_THRESHOLD
    }