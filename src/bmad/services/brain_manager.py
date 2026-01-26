"""
Brain Manager Service

This module provides management for the three-tier brain scoping model.
- Agent-specific brains (one per AI agent)
- Project-specific brains (faith-meats, diff-driven-saas, global-coding-skills)
- Global brain for cross-project patterns
- Priority ordering: agent_specific -> project_specific -> global

Author: Brooks (BMAD Dev Agent)
Created: 2026-01-26
Story: 3-2-implement-brain-scoping-model
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.bmad.core.neo4j_client import Neo4jAsyncClient

logger = logging.getLogger(__name__)


@dataclass
class Brain:
    """Represents a knowledge brain."""
    brain_id: str
    name: str
    scope: str  # 'agent_specific', 'project_specific', 'global'
    group_id: str
    created_at: datetime
    description: Optional[str] = None
    metadata: Dict[str, Any] = None


@dataclass
class AgentBrains:
    """Holds all brains accessible to an agent with priority ordering."""
    agent_name: str
    group_id: str
    agent_specific_brain: Optional[Brain]
    project_specific_brain: Optional[Brain]
    global_brain: Brain
    all_brains: List[Brain]


class BrainManager:
    """
    Service for managing brain scoping.

    Features:
    - Query accessible brains for an agent
    - Priority-based brain access (agent → project → global)
    - Brain initialization and validation
    - Multi-tenant isolation
    """

    # Brain scope ordering (lower = higher priority)
    SCOPE_PRIORITY = {
        'agent_specific': 1,
        'project_specific': 2,
        'global': 3
    }

    def __init__(self, client: Neo4jAsyncClient):
        """
        Initialize the brain manager.

        Args:
            client: Neo4j async client for database operations
        """
        self._client = client

    async def get_agent_brains(
        self,
        agent_name: str,
        group_id: str
    ) -> AgentBrains:
        """
        Get all brains accessible to an agent in priority order.

        Args:
            agent_name: The agent requesting access
            group_id: The agent's project group

        Returns:
            AgentBrains with all accessible brains
        """
        cypher = """
        // Get agent's brains in priority order
        MATCH (agent:AIAgent {name: $agent_name})-[:HAS_MEMORY_IN]->(brain:Brain)
        WHERE brain.group_id = $group_id
           OR brain.group_id = 'global-coding-skills'
        RETURN brain.brain_id as brain_id,
               brain.name as name,
               brain.scope as scope,
               brain.group_id as group_id,
               brain.created_at as created_at,
               brain.description as description,
               brain.metadata as metadata
        ORDER BY
            CASE brain.scope
                WHEN 'agent_specific' THEN 1
                WHEN 'project_specific' THEN 2
                ELSE 3
            END
        """

        records = await self._client.execute_query(
            cypher,
            {"agent_name": agent_name, "group_id": group_id},
            validate_group_id=False  # Brain queries need full graph access
        )

        agent_brain = None
        project_brain = None
        global_brain = None

        for record in records:
            brain = self._parse_brain(record)
            scope = record.get('scope', '')

            if scope == 'agent_specific' and agent_brain is None:
                agent_brain = brain
            elif scope == 'project_specific' and project_brain is None:
                project_brain = brain
            elif scope == 'global':
                global_brain = brain

        # Get all brains in order for list
        all_brains = [b for b in [agent_brain, project_brain, global_brain] if b is not None]

        return AgentBrains(
            agent_name=agent_name,
            group_id=group_id,
            agent_specific_brain=agent_brain,
            project_specific_brain=project_brain,
            global_brain=global_brain,
            all_brains=all_brains
        )

    async def get_brain_by_name(
        self,
        brain_name: str,
        group_id: str
    ) -> Optional[Brain]:
        """
        Get a specific brain by name.

        Args:
            brain_name: The brain name to find
            group_id: Project group for access control

        Returns:
            Brain if found and accessible, None otherwise
        """
        cypher = """
        MATCH (b:Brain)
        WHERE b.name = $name
          AND (b.group_id = $group_id OR b.group_id = 'global-coding-skills')
        RETURN b.brain_id as brain_id,
               b.name as name,
               b.scope as scope,
               b.group_id as group_id,
               b.created_at as created_at,
               b.description as description,
               b.metadata as metadata
        """

        records = await self._client.execute_query(
            cypher,
            {"name": brain_name, "group_id": group_id}
        )

        if not records:
            return None

        return self._parse_brain(records[0])

    async def get_brains_by_scope(
        self,
        scope: str,
        group_id: str
    ) -> List[Brain]:
        """
        Get all brains of a specific scope.

        Args:
            scope: 'agent_specific', 'project_specific', or 'global'
            group_id: Project group for access control

        Returns:
            List of matching brains
        """
        cypher = """
        MATCH (b:Brain)
        WHERE b.scope = $scope
          AND (b.group_id = $group_id OR b.group_id = 'global-coding-skills')
        RETURN b.brain_id as brain_id,
               b.name as name,
               b.scope as scope,
               b.group_id as group_id,
               b.created_at as created_at,
               b.description as description,
               b.metadata as metadata
        ORDER BY b.name
        """

        records = await self._client.execute_query(
            cypher,
            {"scope": scope, "group_id": group_id}
        )

        return [self._parse_brain(r) for r in records]

    async def get_all_brains(
        self,
        group_id: str
    ) -> Dict[str, List[Brain]]:
        """
        Get all brains organized by scope.

        Args:
            group_id: Project group for access control

        Returns:
            Dictionary with keys: agent_specific, project_specific, global
        """
        cypher = """
        MATCH (b:Brain)
        WHERE b.group_id = $group_id OR b.group_id = 'global-coding-skills'
        RETURN b.brain_id as brain_id,
               b.name as name,
               b.scope as scope,
               b.group_id as group_id,
               b.created_at as created_at,
               b.description as description,
               b.metadata as metadata
        ORDER BY b.scope, b.name
        """

        records = await self._client.execute_query(
            cypher,
            {"group_id": group_id},
            validate_group_id=False
        )

        result = {
            'agent_specific': [],
            'project_specific': [],
            'global': []
        }

        for record in records:
            brain = self._parse_brain(record)
            scope = record.get('scope', '')
            if scope in result:
                result[scope].append(brain)

        return result

    async def validate_agent_brain_connectivity(
        self,
        agent_name: str
    ) -> Dict[str, Any]:
        """
        Validate that an agent has proper brain connectivity.

        Args:
            agent_name: The agent to validate

        Returns:
            Dictionary with validation results
        """
        cypher = """
        MATCH (agent:AIAgent {name: $agent_name})-[:HAS_MEMORY_IN]->(brain:Brain)
        RETURN brain.scope as scope, brain.name as name, count(*) as count
        """

        records = await self._client.execute_query(
            cypher,
            {"agent_name": agent_name},
            validate_group_id=False
        )

        scopes_found = {r.get('scope') for r in records}

        required_scopes = {'global'}
        agent_has_agent_brain = await self._agent_has_specific_brain(agent_name)

        if agent_has_agent_brain:
            required_scopes.add('agent_specific')

        missing_scopes = required_scopes - scopes_found

        return {
            "agent_name": agent_name,
            "connected": len(missing_scopes) == 0,
            "scopes_found": list(scopes_found),
            "missing_scopes": list(missing_scopes),
            "brain_count": len(records)
        }

    async def _agent_has_specific_brain(self, agent_name: str) -> bool:
        """Check if agent has an agent-specific brain."""
        brain_name = f"{agent_name} Brain"
        brain = await self.get_brain_by_name(brain_name, "global-coding-skills")
        return brain is not None and brain.scope == 'agent_specific'

    async def count_brains(self, group_id: str) -> Dict[str, int]:
        """
        Count brains by scope for a group.

        Args:
            group_id: Project group

        Returns:
            Dictionary with counts by scope
        """
        cypher = """
        MATCH (b:Brain)
        WHERE b.group_id = $group_id OR b.group_id = 'global-coding-skills'
        RETURN b.scope as scope, count(*) as count
        """

        records = await self._client.execute_query(
            cypher,
            {"group_id": group_id},
            validate_group_id=False
        )

        return {
            r.get('scope', 'unknown'): r.get('count', 0)
            for r in records
        }

    def _parse_brain(self, record: Dict[str, Any]) -> Brain:
        """Parse a brain record from Neo4j result."""
        created_at = record.get('created_at')
        if hasattr(created_at, 'to_native'):
            created_at = created_at.to_native()

        return Brain(
            brain_id=record.get('brain_id', ''),
            name=record.get('name', ''),
            scope=record.get('scope', ''),
            group_id=record.get('group_id', ''),
            created_at=created_at or datetime.now(timezone.utc),
            description=record.get('description'),
            metadata=record.get('metadata', {})
        )


async def main():
    """Quick test of the brain manager."""
    import os
    os.environ['NEO4J_URI'] = 'bolt://localhost:7687'
    os.environ['NEO4J_USER'] = 'neo4j'
    os.environ['NEO4J_PASSWORD'] = 'Kamina2025*'

    from src.bmad.core.neo4j_client import Neo4jAsyncClient

    async with Neo4jAsyncClient() as client:
        manager = BrainManager(client)

        print("Testing brain manager...")

        # Get Brooks's brains
        brains = await manager.get_agent_brains("Brooks", "global-coding-skills")
        print(f"\nBrooks's brains:")
        print(f"  Agent-specific: {brains.agent_specific_brain.name if brains.agent_specific_brain else 'None'}")
        print(f"  Project: {brains.project_specific_brain.name if brains.project_specific_brain else 'None'}")
        print(f"  Global: {brains.global_brain.name if brains.global_brain else 'None'}")

        # Get all brains by scope
        all_by_scope = await manager.get_all_brains("global-coding-skills")
        print(f"\nBrain counts by scope:")
        for scope, brains_list in all_by_scope.items():
            print(f"  {scope}: {len(brains_list)}")

        # Validate brain connectivity
        validation = await manager.validate_agent_brain_connectivity("Brooks")
        print(f"\nBrain connectivity for Brooks: {validation}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())