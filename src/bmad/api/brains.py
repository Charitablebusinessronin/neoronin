"""
Brains API Endpoints

This module provides REST API endpoints for brain management.
- GET /api/brains/agent/{agent_name} - Get accessible brains for agent
- GET /api/brains/scope/{scope} - Get brains by scope
- GET /api/brains/all - Get all brains organized by scope
- GET /api/brains/validate/{agent_name} - Validate brain connectivity

Author: Brooks (BMAD Dev Agent)
Created: 2026-01-26
Story: 3-2-implement-brain-scoping-model
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.bmad.core.neo4j_client import Neo4jAsyncClient
from src.bmad.services.brain_manager import BrainManager, Brain, AgentBrains

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/brains", tags=["brains"])


# Request/Response Models

class BrainResponse(BaseModel):
    """Response model for a brain."""
    brain_id: str
    name: str
    scope: str
    group_id: str
    created_at: datetime
    description: Optional[str] = None

    class Config:
        from_attributes = True


class AgentBrainsResponse(BaseModel):
    """Response for agent brain access."""
    agent_name: str
    group_id: str
    agent_specific_brain: Optional[BrainResponse] = None
    project_specific_brain: Optional[BrainResponse] = None
    global_brain: Optional[BrainResponse] = None
    brain_count: int
    all_brains: List[BrainResponse]


class AllBrainsResponse(BaseModel):
    """Response for all brains by scope."""
    group_id: str
    agent_specific: List[BrainResponse]
    project_specific: List[BrainResponse]
    global_brains: List[BrainResponse]
    total_count: int
    timestamp: datetime


class BrainValidationResponse(BaseModel):
    """Response for brain connectivity validation."""
    agent_name: str
    connected: bool
    scopes_found: List[str]
    missing_scopes: List[str]
    brain_count: int


class BrainCountResponse(BaseModel):
    """Response for brain counts by scope."""
    group_id: str
    counts: dict
    timestamp: datetime


# Endpoints

@router.get("/agent/{agent_name}", response_model=AgentBrainsResponse)
async def get_agent_brains(
    agent_name: str,
    group_id: str = Query(..., description="Project group ID"),
    service: BrainManager = None
):
    """
    Get all brains accessible to an agent.

    Returns brains in priority order:
    1. Agent-specific brain
    2. Project-specific brain
    3. Global brain
    """
    if not service:
        raise HTTPException(status_code=503, detail="Service not available")

    try:
        agent_brains = await service.get_agent_brains(agent_name, group_id)

        def brain_to_response(b: Brain) -> BrainResponse:
            if b is None:
                return None
            return BrainResponse(
                brain_id=b.brain_id,
                name=b.name,
                scope=b.scope,
                group_id=b.group_id,
                created_at=b.created_at,
                description=b.description
            )

        return AgentBrainsResponse(
            agent_name=agent_brains.agent_name,
            group_id=agent_brains.group_id,
            agent_specific_brain=brain_to_response(agent_brains.agent_specific_brain),
            project_specific_brain=brain_to_response(agent_brains.project_specific_brain),
            global_brain=brain_to_response(agent_brains.global_brain),
            brain_count=len(agent_brains.all_brains),
            all_brains=[brain_to_response(b) for b in agent_brains.all_brains]
        )

    except Exception as e:
        logger.error(f"Failed to get brains for {agent_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scope/{scope}", response_model=List[BrainResponse])
async def get_brains_by_scope(
    scope: str,
    group_id: str = Query(..., description="Project group ID"),
    service: BrainManager = None
):
    """
    Get all brains of a specific scope.

    Scope options:
    - agent_specific: One brain per AI agent
    - project_specific: One brain per project group
    - global: Cross-project patterns
    """
    if scope not in ['agent_specific', 'project_specific', 'global']:
        raise HTTPException(
            status_code=400,
            detail="Invalid scope. Must be: agent_specific, project_specific, or global"
        )

    if not service:
        raise HTTPException(status_code=503, detail="Service not available")

    try:
        brains = await service.get_brains_by_scope(scope, group_id)

        return [
            BrainResponse(
                brain_id=b.brain_id,
                name=b.name,
                scope=b.scope,
                group_id=b.group_id,
                created_at=b.created_at,
                description=b.description
            )
            for b in brains
        ]

    except Exception as e:
        logger.error(f"Failed to get brains for scope {scope}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/all", response_model=AllBrainsResponse)
async def get_all_brains(
    group_id: str = Query(..., description="Project group ID"),
    service: BrainManager = None
):
    """
    Get all brains organized by scope.
    """
    if not service:
        raise HTTPException(status_code=503, detail="Service not available")

    try:
        brains_by_scope = await service.get_all_brains(group_id)

        def to_response(b: Brain) -> BrainResponse:
            return BrainResponse(
                brain_id=b.brain_id,
                name=b.name,
                scope=b.scope,
                group_id=b.group_id,
                created_at=b.created_at,
                description=b.description
            )

        total = (
            len(brains_by_scope['agent_specific']) +
            len(brains_by_scope['project_specific']) +
            len(brains_by_scope['global'])
        )

        return AllBrainsResponse(
            group_id=group_id,
            agent_specific=[to_response(b) for b in brains_by_scope['agent_specific']],
            project_specific=[to_response(b) for b in brains_by_scope['project_specific']],
            global_brains=[to_response(b) for b in brains_by_scope['global']],
            total_count=total,
            timestamp=datetime.now(timezone.utc)
        )

    except Exception as e:
        logger.error(f"Failed to get all brains: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/validate/{agent_name}", response_model=BrainValidationResponse)
async def validate_brain_connectivity(
    agent_name: str,
    service: BrainManager = None
):
    """
    Validate that an agent has proper brain connectivity.

    Returns validation status and any missing brain connections.
    """
    if not service:
        raise HTTPException(status_code=503, detail="Service not available")

    try:
        validation = await service.validate_agent_brain_connectivity(agent_name)

        return BrainValidationResponse(
            agent_name=validation['agent_name'],
            connected=validation['connected'],
            scopes_found=validation['scopes_found'],
            missing_scopes=validation['missing_scopes'],
            brain_count=validation['brain_count']
        )

    except Exception as e:
        logger.error(f"Failed to validate brain connectivity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/counts", response_model=BrainCountResponse)
async def get_brain_counts(
    group_id: str = Query(..., description="Project group ID"),
    service: BrainManager = None
):
    """
    Get brain counts by scope for a group.
    """
    if not service:
        raise HTTPException(status_code=503, detail="Service not available")

    try:
        counts = await service.count_brains(group_id)

        return BrainCountResponse(
            group_id=group_id,
            counts=counts,
            timestamp=datetime.now(timezone.utc)
        )

    except Exception as e:
        logger.error(f"Failed to get brain counts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def brains_health():
    """Health check for brains API."""
    return {
        "status": "healthy",
        "service": "brain_manager",
        "scopes": ["agent_specific", "project_specific", "global"]
    }


# Dependency factory for FastAPI

def get_brain_manager(
    client: Neo4jAsyncClient
) -> BrainManager:
    """Factory for BrainManager dependency."""
    return BrainManager(client)