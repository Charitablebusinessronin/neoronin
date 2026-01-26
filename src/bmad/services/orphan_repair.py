"""
Orphan Detection and Repair Service

This module detects and repairs orphaned relationships in the graph.
- Detect AIAgent nodes without HAS_MEMORY_IN relationships
- Detect Brain nodes without proper connections
- Automatically repair missing relationships

Author: Brooks (BMAD Dev Agent)
Created: 2026-01-26
Story: 4-4-detect-and-resolve-orphaned-relationships
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.bmad.core.neo4j_client import Neo4jAsyncClient

logger = logging.getLogger(__name__)


@dataclass
class OrphanedAgent:
    """An AIAgent node without proper brain connection."""
    agent_id: str
    name: str
    role: str
    group_id: str


@dataclass
class OrphanedBrain:
    """A Brain node without proper connections."""
    brain_id: str
    name: str
    group_id: str


@dataclass
class RepairResult:
    """Result of a repair operation."""
    agents_repaired: int
    brains_repaired: int
    relationships_created: int
    agents_still_orphaned: List[str]
    processing_time_ms: float
    timestamp: datetime

    def to_dict(self) -> dict:
        """Convert repair result to dictionary."""
        return {
            "agents_repaired": self.agents_repaired,
            "brains_repaired": self.brains_repaired,
            "relationships_created": self.relationships_created,
            "agents_still_orphaned": self.agents_still_orphaned,
            "processing_time_ms": self.processing_time_ms,
            "timestamp": self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else self.timestamp
        }


@dataclass
class HealthCheckResult:
    """Result of a health check operation."""
    is_healthy: bool
    orphaned_agents: List[OrphanedAgent]
    orphaned_brains: List[OrphanedBrain]
    total_checks: int
    checks_passed: int
    processing_time_ms: float
    timestamp: datetime


class OrphanRepairService:
    """
    Service for detecting and repairing orphaned relationships.

    Features:
    - Detect AIAgent nodes without HAS_MEMORY_IN relationships
    - Detect Brain nodes without proper group_id
    - Auto-repair missing relationships
    - Performance tracking (<5 second target)
    """

    def __init__(self, client: Neo4jAsyncClient):
        """
        Initialize the orphan repair service.

        Args:
            client: Neo4j async client
        """
        self._client = client

    async def run_health_check(self) -> HealthCheckResult:
        """
        Run comprehensive health check for orphan detection.

        Returns:
            HealthCheckResult with orphan details
        """
        start_time = datetime.now(timezone.utc)

        # Check for orphaned agents
        orphaned_agents = await self._detect_orphaned_agents()

        # Check for orphaned brains
        orphaned_brains = await self._detect_orphaned_brains()

        processing_time_ms = (
            datetime.now(timezone.utc) - start_time
        ).total_seconds() * 1000

        is_healthy = len(orphaned_agents) == 0 and len(orphaned_brains) == 0
        total_checks = 2
        checks_passed = (1 if len(orphaned_agents) == 0 else 0) + (1 if len(orphaned_brains) == 0 else 0)

        result = HealthCheckResult(
            is_healthy=is_healthy,
            orphaned_agents=orphaned_agents,
            orphaned_brains=orphaned_brains,
            total_checks=total_checks,
            checks_passed=checks_passed,
            processing_time_ms=round(processing_time_ms, 2),
            timestamp=datetime.now(timezone.utc)
        )

        logger.info(
            f"Health check complete: healthy={is_healthy}, "
            f"orphan_agents={len(orphaned_agents)}, "
            f"orphan_brains={len(orphaned_brains)}, "
            f"{processing_time_ms:.2f}ms"
        )

        return result

    async def repair_orphaned_relationships(self) -> RepairResult:
        """
        Repair orphaned relationships automatically.

        Returns:
            RepairResult with repair details
        """
        start_time = datetime.now(timezone.utc)

        # Detect orphans
        orphaned_agents = await self._detect_orphaned_agents()

        # Repair agent-brain connections
        agents_repaired, rels_created = await self._repair_agent_brains(orphaned_agents)

        # Detect and repair orphaned brains
        orphaned_brains = await self._detect_orphaned_brains()
        brains_repaired = await self._repair_brains(orphaned_brains)

        processing_time_ms = (
            datetime.now(timezone.utc) - start_time
        ).total_seconds() * 1000

        result = RepairResult(
            agents_repaired=agents_repaired,
            brains_repaired=brains_repaired,
            relationships_created=rels_created,
            agents_still_orphaned=[a.name for a in orphaned_agents],
            processing_time_ms=round(processing_time_ms, 2),
            timestamp=datetime.now(timezone.utc)
        )

        return result

    async def _detect_orphaned_agents(self) -> List[OrphanedAgent]:
        """Detect AIAgent nodes without HAS_MEMORY_IN relationships."""
        query = """
        MATCH (a:AIAgent)
        WHERE NOT (a)-[:HAS_MEMORY_IN]->(:Brain)
        RETURN a.agent_id as agent_id, a.name as name,
               a.role as role, a.group_id as group_id
        """

        results = await self._client.execute_query(query, {})

        return [
            OrphanedAgent(
                agent_id=r.get('agent_id', ''),
                name=r.get('name', ''),
                role=r.get('role', ''),
                group_id=r.get('group_id', '')
            )
            for r in results
        ]

    async def _detect_orphaned_brains(self) -> List[OrphanedBrain]:
        """Detect Brain nodes without proper connections."""
        query = """
        MATCH (b:Brain)
        WHERE b.group_id IS NULL OR b.group_id = ''
        RETURN b.brain_id as brain_id, b.name as name, b.group_id as group_id
        """

        results = await self._client.execute_query(query, {})

        return [
            OrphanedBrain(
                brain_id=r.get('brain_id', ''),
                name=r.get('name', ''),
                group_id=r.get('group_id', '')
            )
            for r in results
        ]

    async def _repair_agent_brains(
        self,
        orphaned_agents: List[OrphanedAgent]
    ) -> tuple[int, int]:
        """Repair agent-brain relationships."""
        if not orphaned_agents:
            return 0, 0

        repaired_count = 0
        rels_created = 0

        for agent in orphaned_agents:
            # Try to find or create matching brain
            brain_name = agent.name + ' Brain' if agent.name else None
            if not brain_name:
                # Skip agents without names
                continue

            query = """
            MATCH (a:AIAgent {agent_id: $agent_id})
            """

            params = {
                "agent_id": agent.agent_id or agent.name,
                "brain_name": brain_name,
                "group_id": agent.group_id or 'default'
            }

            # Try to find matching brain
            check_query = """
            MATCH (a:AIAgent)
            WHERE a.agent_id = $agent_id OR a.name = $agent_id
            OPTIONAL MATCH (b:Brain {name: $brain_name})
            RETURN a, b
            """

            check_results = await self._client.execute_query(check_query, params)

            if check_results:
                a_record = check_results[0].get('a')
                b_record = check_results[0].get('b')

                if a_record and b_record:
                    # Brain exists, create relationship
                    create_query = """
                    MATCH (a:AIAgent {agent_id: $agent_id OR a.name = $agent_id})
                    MATCH (b:Brain {name: $brain_name})
                    MERGE (a)-[:HAS_MEMORY_IN]->(b)
                    RETURN 1 as created
                    """
                    await self._client.execute_query(create_query, params)
                    repaired_count += 1
                    rels_created += 1
                elif a_record and not b_record:
                    # Need to create brain first, then relationship
                    create_brain = """
                    CREATE (b:Brain {
                        brain_id: $brain_id,
                        name: $brain_name,
                        group_id: $group_id,
                        created_at: $timestamp,
                        scope: 'project'
                    })
                    RETURN b
                    """
                    await self._client.execute_query(create_brain, {
                        "brain_id": f"brain-{agent.name.lower().replace(' ', '-')}",
                        "brain_name": brain_name,
                        "group_id": params["group_id"],
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })

                    # Now create relationship
                    create_rel = """
                    MATCH (a:AIAgent)
                    WHERE a.agent_id = $agent_id OR a.name = $agent_id
                    MATCH (b:Brain {name: $brain_name})
                    MERGE (a)-[:HAS_MEMORY_IN]->(b)
                    RETURN 1 as created
                    """
                    await self._client.execute_query(create_rel, params)
                    repaired_count += 1
                    rels_created += 1

        return repaired_count, rels_created

    async def _repair_brains(
        self,
        orphaned_brains: List[OrphanedBrain]
    ) -> int:
        """Repair orphaned brains by setting group_id."""
        if not orphaned_brains:
            return 0

        repaired_count = 0

        for brain in orphaned_brains:
            # Assign default group_id if missing
            if not brain.group_id or brain.group_id == '':
                query = """
                MATCH (b:Brain {brain_id: $brain_id})
                SET b.group_id = 'default'
                RETURN 1 as updated
                """
                await self._client.execute_query(query, {"brain_id": brain.brain_id})
                repaired_count += 1

        return repaired_count

    async def get_repair_candidates(self) -> Dict[str, Any]:
        """Get summary of potential repair candidates."""
        agents = await self._detect_orphaned_agents()
        brains = await self._detect_orphaned_brains()

        return {
            "orphaned_agent_count": len(agents),
            "orphaned_brain_count": len(brains),
            "total_repairs_needed": len(agents) + len(brains),
            "agents": [
                {"name": a.name, "role": a.role, "group_id": a.group_id}
                for a in agents
            ],
            "brains": [
                {"name": b.name, "brain_id": b.brain_id}
                for b in brains
            ]
        }


async def main():
    """Test the orphan repair service."""
    from src.bmad.core.neo4j_client import Neo4jAsyncClient

    async with Neo4jAsyncClient() as client:
        service = OrphanRepairService(client)

        print("Testing orphan repair service...")

        # Get repair candidates
        candidates = await service.get_repair_candidates()
        print(f"\nRepair Candidates:")
        print(f"  Orphaned agents: {candidates['orphaned_agent_count']}")
        print(f"  Orphaned brains: {candidates['orphaned_brain_count']}")

        # Run health check
        health = await service.run_health_check()
        print(f"\nHealth Check:")
        print(f"  Healthy: {health.is_healthy}")
        print(f"  Checks passed: {health.checks_passed}/{health.total_checks}")
        print(f"  Processing time: {health.processing_time_ms:.2f}ms")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())