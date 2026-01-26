"""
Agent History API Endpoints

This module provides FastAPI endpoints for agents to query their work history.

Author: Brooks (BMAD Dev Agent)
Created: 2026-01-26
Story: 1-3-query-and-review-agent-work-history
"""

import logging
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field

from src.bmad.services.agent_queries import (
    AgentQueryService,
    WorkHistoryQueryResult,
    OutcomeStatus
)
from src.bmad.core.neo4j_client import Neo4jAsyncClient, SecurityError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agents", tags=["agents"])


# Dependency to get the query service
async def get_query_service() -> AgentQueryService:
    """Get the agent query service instance."""
    # In production, this would be a shared instance
    # For now, we'll create a new one per request
    client = Neo4jAsyncClient()
    await client.initialize()
    return AgentQueryService(client)


# Response models
class WorkEventResponse(BaseModel):
    """Response model for a work event."""
    event_id: str
    event_type: str
    timestamp: datetime
    group_id: str
    description: str
    tool_name: Optional[str] = None
    input_hash: Optional[str] = None
    metadata: dict = {}


class WorkOutcomeResponse(BaseModel):
    """Response model for a work outcome."""
    outcome_id: str
    status: str
    result_summary: str
    error_log: Optional[str] = None
    duration_ms: Optional[float] = None


class AppliedPatternResponse(BaseModel):
    """Response model for an applied pattern."""
    pattern_id: str
    pattern_name: str
    category: str
    confidence_score: float


class GeneratedInsightResponse(BaseModel):
    """Response model for a generated insight."""
    insight_id: str
    rule: str
    category: str
    confidence_score: float


class WorkHistoryEntryResponse(BaseModel):
    """Response model for a work history entry."""
    event: WorkEventResponse
    outcome: Optional[WorkOutcomeResponse] = None
    patterns: List[AppliedPatternResponse] = []
    insights: List[GeneratedInsightResponse] = []


class WorkHistoryQueryResponse(BaseModel):
    """Response model for work history query."""
    entries: List[WorkHistoryEntryResponse]
    total_count: int
    latency_ms: float
    page: int
    page_size: int
    query_params: dict


@router.get("/{agent_name}/history", response_model=WorkHistoryQueryResponse)
async def get_agent_history(
    agent_name: str,
    group_id: str = Query(..., description="Project group ID for filtering"),
    days_back: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    status: Optional[str] = Query(None, description="Filter by outcome status (Success/Failed)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Results per page"),
    service: AgentQueryService = Depends(get_query_service)
):
    """
    Get an agent's work history with filtering options.

    Returns Event → Solution → Outcome chains with full context,
    including applied patterns and generated insights.
    """
    try:
        # Convert status string to enum
        outcome_status = OutcomeStatus.ALL
        if status:
            status_upper = status.upper()
            if status_upper == "SUCCESS":
                outcome_status = OutcomeStatus.SUCCESS
            elif status_upper == "FAILED":
                outcome_status = OutcomeStatus.FAILED

        # Execute query
        result: WorkHistoryQueryResult = await service.query_work_history(
            agent_name=agent_name,
            group_id=group_id,
            days_back=days_back,
            outcome_status=outcome_status,
            page=page,
            page_size=page_size,
            include_patterns=True,
            include_insights=True
        )

        # Convert to response model
        entries = []
        for entry in result.entries:
            entry_resp = WorkHistoryEntryResponse(
                event=WorkEventResponse(
                    event_id=entry.event.event_id,
                    event_type=entry.event.event_type,
                    timestamp=entry.event.timestamp,
                    group_id=entry.event.group_id,
                    description=entry.event.description,
                    tool_name=entry.event.tool_name,
                    input_hash=entry.event.input_hash,
                    metadata=entry.event.metadata
                ),
                outcome=WorkOutcomeResponse(
                    outcome_id=entry.outcome.outcome_id,
                    status=entry.outcome.status,
                    result_summary=entry.outcome.result_summary,
                    error_log=entry.outcome.error_log,
                    duration_ms=entry.outcome.duration_ms
                ) if entry.outcome else None,
                patterns=[
                    AppliedPatternResponse(
                        pattern_id=p.pattern_id,
                        pattern_name=p.pattern_name,
                        category=p.category,
                        confidence_score=p.confidence_score
                    ) for p in entry.patterns
                ],
                insights=[
                    GeneratedInsightResponse(
                        insight_id=i.insight_id,
                        rule=i.rule,
                        category=i.category,
                        confidence_score=i.confidence_score
                    ) for i in entry.insights
                ]
            )
            entries.append(entry_resp)

        return WorkHistoryQueryResponse(
            entries=entries,
            total_count=result.total_count,
            latency_ms=result.latency_ms,
            page=page,
            page_size=page_size,
            query_params=result.query_params
        )

    except SecurityError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"Error querying agent history: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{agent_name}/failures")
async def get_agent_failures(
    agent_name: str,
    group_id: str = Query(..., description="Project group ID for filtering"),
    days_back: int = Query(7, ge=1, le=365, description="Number of days to look back"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    service: AgentQueryService = Depends(get_query_service)
):
    """
    Get an agent's failed outcomes for learning.

    Returns failed events with error logs and generated insights.
    """
    try:
        result = await service.query_failures(
            agent_name=agent_name,
            group_id=group_id,
            days_back=days_back
        )

        # Convert to response (similar to above)
        entries = []
        for entry in result.entries:
            entry_resp = WorkHistoryEntryResponse(
                event=WorkEventResponse(
                    event_id=entry.event.event_id,
                    event_type=entry.event.event_type,
                    timestamp=entry.event.timestamp,
                    group_id=entry.event.group_id,
                    description=entry.event.description,
                    tool_name=entry.event.tool_name,
                    input_hash=entry.event.input_hash,
                    metadata=entry.event.metadata
                ),
                outcome=WorkOutcomeResponse(
                    outcome_id=entry.outcome.outcome_id,
                    status=entry.outcome.status,
                    result_summary=entry.outcome.result_summary,
                    error_log=entry.outcome.error_log,
                    duration_ms=entry.outcome.duration_ms
                ) if entry.outcome else None,
                patterns=[
                    AppliedPatternResponse(
                        pattern_id=p.pattern_id,
                        pattern_name=p.pattern_name,
                        category=p.category,
                        confidence_score=p.confidence_score
                    ) for p in entry.patterns
                ],
                insights=[
                    GeneratedInsightResponse(
                        insight_id=i.insight_id,
                        rule=i.rule,
                        category=i.category,
                        confidence_score=i.confidence_score
                    ) for i in entry.insights
                ]
            )
            entries.append(entry_resp)

        return WorkHistoryQueryResponse(
            entries=entries,
            total_count=result.total_count,
            latency_ms=result.latency_ms,
            page=page,
            page_size=page_size,
            query_params=result.query_params
        )

    except SecurityError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"Error querying agent failures: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{agent_name}/history/{event_id}")
async def get_event_chain(
    agent_name: str,
    event_id: str,
    group_id: str = Query(..., description="Project group ID"),
    service: AgentQueryService = Depends(get_query_service)
):
    """
    Get a complete Event → Solution → Outcome chain for a specific event.
    """
    try:
        entry = await service.get_event_chain(
            agent_name=agent_name,
            group_id=group_id,
            event_id=event_id
        )

        if entry is None:
            raise HTTPException(status_code=404, detail="Event not found")

        return {
            "event": WorkEventResponse(
                event_id=entry.event.event_id,
                event_type=entry.event.event_type,
                timestamp=entry.event.timestamp,
                group_id=entry.event.group_id,
                description=entry.event.description,
                tool_name=entry.event.tool_name,
                input_hash=entry.event.input_hash,
                metadata=entry.event.metadata
            ),
            "outcome": WorkOutcomeResponse(
                outcome_id=entry.outcome.outcome_id,
                status=entry.outcome.status,
                result_summary=entry.outcome.result_summary,
                error_log=entry.outcome.error_log,
                duration_ms=entry.outcome.duration_ms
            ) if entry.outcome else None,
            "patterns": [
                AppliedPatternResponse(
                    pattern_id=p.pattern_id,
                    pattern_name=p.pattern_name,
                    category=p.category,
                    confidence_score=p.confidence_score
                ) for p in entry.patterns
            ],
            "insights": [
                GeneratedInsightResponse(
                    insight_id=i.insight_id,
                    rule=i.rule,
                    category=i.category,
                    confidence_score=i.confidence_score
                ) for i in entry.insights
            ]
        }

    except SecurityError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying event chain: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")