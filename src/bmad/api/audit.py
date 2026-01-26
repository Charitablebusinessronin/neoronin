"""
Audit API Endpoints

This module provides REST API endpoints for accessing audit logs.
- GET /api/audit/logs - Query audit logs with filters
- GET /api/audit/summary - Get audit summary statistics
- GET /api/audit/cross-group - Get cross-group access attempts
- GET /api/audit/agent/{agent_name} - Get audit logs for specific agent

Author: Brooks (BMAD Dev Agent)
Created: 2026-01-26
Story: 3-1-enforce-multi-tenant-isolation
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.bmad.core.neo4j_client import Neo4jAsyncClient
from src.bmad.services.audit_logger import (
    AuditLogger,
    AuditLogEntry,
    AuditQueryFilters,
    AuditSummary
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/audit", tags=["audit"])


# Request/Response Models

class AuditLogResponse(BaseModel):
    """Response model for a single audit log entry."""
    audit_id: str
    timestamp: datetime
    agent_name: str
    agent_group_id: str
    action: str
    query_type: str
    success: bool
    group_accessed: str
    cross_group_attempt: bool
    error_message: Optional[str] = None
    query_preview: Optional[str] = None
    latency_ms: float

    class Config:
        from_attributes = True


class AuditSummaryResponse(BaseModel):
    """Response model for audit summary."""
    total_accesses: int
    cross_group_attempts: int
    failed_accesses: int
    unique_agents: int
    unique_groups: int
    by_agent: dict
    by_group: dict
    by_action: dict
    timestamp: datetime


class AuditQueryRequest(BaseModel):
    """Request model for querying audit logs."""
    agent_name: Optional[str] = None
    group_id: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    action: Optional[str] = None
    cross_group_only: bool = False
    failed_only: bool = False
    limit: int = Field(default=100, ge=1, le=500)


class CrossGroupResponse(BaseModel):
    """Response for cross-group access attempts."""
    count: int
    attempts: List[AuditLogResponse]
    timestamp: datetime


# Endpoints

@router.get("/logs", response_model=List[AuditLogResponse])
async def get_audit_logs(
    agent_name: Optional[str] = Query(None, description="Filter by agent name"),
    group_id: Optional[str] = Query(None, description="Filter by agent group"),
    start_time: Optional[datetime] = Query(None, description="Start of time range (ISO format)"),
    end_time: Optional[datetime] = Query(None, description="End of time range (ISO format)"),
    action: Optional[str] = Query(None, description="Filter by action type"),
    cross_group_only: bool = Query(False, description="Only show cross-group attempts"),
    failed_only: bool = Query(False, description="Only show failed accesses"),
    limit: int = Query(100, ge=1, le=500, description="Maximum results"),
    service: AuditLogger = None
):
    """
    Query audit logs with filters.

    Returns audit entries matching the specified criteria.
    """
    if not service:
        raise HTTPException(status_code=503, detail="Service not available")

    try:
        filters = AuditQueryFilters(
            agent_name=agent_name,
            group_id=group_id,
            start_time=start_time,
            end_time=end_time,
            action=action,
            cross_group_only=cross_group_only,
            failed_only=failed_only,
            limit=limit
        )

        logs = await service.query_audit_logs(filters)

        return [
            AuditLogResponse(
                audit_id=log.audit_id,
                timestamp=log.timestamp,
                agent_name=log.agent_name,
                agent_group_id=log.group_id,
                action=log.action,
                query_type=log.query_type,
                success=log.success,
                group_accessed=log.group_accessed,
                cross_group_attempt=log.cross_group_attempt,
                error_message=log.error_message,
                query_preview=log.query_preview,
                latency_ms=log.latency_ms
            )
            for log in logs
        ]

    except Exception as e:
        logger.error(f"Failed to query audit logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary", response_model=AuditSummaryResponse)
async def get_audit_summary(
    group_id: Optional[str] = Query(None, description="Filter by group"),
    start_time: Optional[datetime] = Query(None, description="Start of time range"),
    end_time: Optional[datetime] = Query(None, description="End of time range"),
    service: AuditLogger = None
):
    """
    Get audit summary statistics.

    Returns counts and breakdowns of audit activity.
    """
    if not service:
        raise HTTPException(status_code=503, detail="Service not available")

    try:
        summary = await service.get_summary(
            group_id=group_id,
            start_time=start_time,
            end_time=end_time
        )

        return AuditSummaryResponse(
            total_accesses=summary.total_accesses,
            cross_group_attempts=summary.cross_group_attempts,
            failed_accesses=summary.failed_accesses,
            unique_agents=summary.unique_agents,
            unique_groups=summary.unique_groups,
            by_agent=summary.by_agent,
            by_group=summary.by_group,
            by_action=summary.by_action,
            timestamp=datetime.now(timezone.utc)
        )

    except Exception as e:
        logger.error(f"Failed to get audit summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cross-group", response_model=CrossGroupResponse)
async def get_cross_group_attempts(
    limit: int = Query(50, ge=1, le=100, description="Maximum results"),
    service: AuditLogger = None
):
    """
    Get all cross-group access attempts.

    These are flagged as potential security events.
    """
    if not service:
        raise HTTPException(status_code=503, detail="Service not available")

    try:
        attempts = await service.get_cross_group_attempts(limit=limit)

        return CrossGroupResponse(
            count=len(attempts),
            attempts=[
                AuditLogResponse(
                    audit_id=log.audit_id,
                    timestamp=log.timestamp,
                    agent_name=log.agent_name,
                    agent_group_id=log.group_id,
                    action=log.action,
                    query_type=log.query_type,
                    success=log.success,
                    group_accessed=log.group_accessed,
                    cross_group_attempt=True,
                    error_message=log.error_message,
                    query_preview=log.query_preview,
                    latency_ms=log.latency_ms
                )
                for log in attempts
            ],
            timestamp=datetime.now(timezone.utc)
        )

    except Exception as e:
        logger.error(f"Failed to get cross-group attempts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agent/{agent_name}", response_model=List[AuditLogResponse])
async def get_agent_audit_logs(
    agent_name: str,
    group_id: Optional[str] = Query(None, description="Filter by agent group"),
    limit: int = Query(50, ge=1, le=100, description="Maximum results"),
    service: AuditLogger = None
):
    """
    Get audit logs for a specific agent.
    """
    if not service:
        raise HTTPException(status_code=503, detail="Service not available")

    try:
        filters = AuditQueryFilters(
            agent_name=agent_name,
            group_id=group_id,
            limit=limit
        )

        logs = await service.query_audit_logs(filters)

        return [
            AuditLogResponse(
                audit_id=log.audit_id,
                timestamp=log.timestamp,
                agent_name=log.agent_name,
                agent_group_id=log.group_id,
                action=log.action,
                query_type=log.query_type,
                success=log.success,
                group_accessed=log.group_accessed,
                cross_group_attempt=log.cross_group_attempt,
                error_message=log.error_message,
                query_preview=log.query_preview,
                latency_ms=log.latency_ms
            )
            for log in logs
        ]

    except Exception as e:
        logger.error(f"Failed to get agent audit logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def audit_health():
    """Health check for audit API."""
    return {
        "status": "healthy",
        "service": "audit_logger"
    }


# Dependency factory for FastAPI

def get_audit_logger(
    client: Neo4jAsyncClient
) -> AuditLogger:
    """Factory for AuditLogger dependency."""
    return AuditLogger(client)