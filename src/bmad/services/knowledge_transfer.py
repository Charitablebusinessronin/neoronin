"""
Knowledge Transfer Service

This module provides cross-agent knowledge sharing for collective learning.
- Share high-confidence insights (confidence_score > 0.8) across agents
- Create CAN_APPLY relationships from recipient agents to shared insights
- Multi-tenant isolation via group_id

Author: Brooks (BMAD Dev Agent)
Created: 2026-01-26
Story: 2-3-share-high-confidence-insights-across-agents
"""

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.bmad.core.neo4j_client import Neo4jAsyncClient

logger = logging.getLogger(__name__)


@dataclass
class Insight:
    """Represents a learned insight."""
    insight_id: str
    rule: str
    category: str
    confidence_score: float
    success_rate: float
    group_id: str
    learned_by: str
    learned_at: datetime
    applies_to: Optional[str] = None
    metadata: Dict[str, Any] = None


@dataclass
class KnowledgeTransferResult:
    """Result of a knowledge transfer operation."""
    insights_shared: int
    agents_updated: int
    transfers: List[Dict[str, Any]]
    latency_ms: float
    group_id: str


@dataclass
class SharedInsight:
    """An insight shared from one agent to another."""
    insight_id: str
    rule: str
    category: str
    confidence_score: float
    success_rate: float
    learned_by: str
    learned_at: datetime
    teacher_agent: str


class KnowledgeTransferService:
    """
    Service for cross-agent knowledge sharing.

    Features:
    - Share high-confidence insights across all agents in group
    - Create CAN_APPLY relationships for shared insights
    - Query shared insights by teacher agent
    - Batch processing under 2 seconds for typical workloads
    """

    # Threshold for sharing: only insights with confidence > 0.8 are shared
    CONFIDENCE_THRESHOLD = 0.8

    def __init__(self, client: Neo4jAsyncClient):
        """
        Initialize the knowledge transfer service.

        Args:
            client: Neo4j async client for database operations
        """
        self._client = client

    async def share_high_confidence_insights(
        self,
        group_id: str
    ) -> KnowledgeTransferResult:
        """
        Share high-confidence insights across all agents in a group.

        Args:
            group_id: Project group for isolation

        Returns:
            KnowledgeTransferResult with transfer metrics
        """
        start_time = time.perf_counter()

        # Share insights from global group as well
        cypher = """
        // Find high-confidence insights not yet shared with all agents
        MATCH (teacher:AIAgent)-[:LEARNED]->(i:Insight)
        WHERE (i.group_id = $group_id OR i.group_id = 'global-coding-skills')
          AND i.confidence_score >= $threshold
          AND i.success_rate >= 0.8

        // Find recipient agents in the same group
        MATCH (learner:AIAgent)
        WHERE learner.group_id = $group_id
          AND learner.name <> teacher.name

        // Filter out insights already shared to this learner
        AND NOT exists((learner)-[:CAN_APPLY]->(i))

        // Create the CAN_APPLY relationship
        MERGE (learner)-[:CAN_APPLY {shared_at: datetime()}]->(i)

        // Return transfer details
        RETURN teacher.name as teacher,
               collect(learner.name) as learners,
               i.insight_id as insight_id,
               i.rule as rule,
               i.category as category
        """

        records = await self._client.execute_write(
            cypher,
            {
                "group_id": group_id,
                "threshold": self.CONFIDENCE_THRESHOLD
            }
        )

        # Parse results
        transfers = []
        agents_updated = set()

        for record in records:
            teachers = record.get('teacher', '')
            learners = record.get('learners', [])
            insight_id = record.get('insight_id', '')

            for learner in learners:
                agents_updated.add(learner)

            if learners:
                transfers.append({
                    "insight_id": insight_id,
                    "rule": record.get('rule', '')[:100],
                    "category": record.get('category', ''),
                    "teacher": teachers,
                    "learners": list(learners)
                })

        latency_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            f"Knowledge transfer for {group_id}: "
            f"{len(transfers)} insights shared to {len(agents_updated)} agents "
            f"in {latency_ms:.2f}ms"
        )

        return KnowledgeTransferResult(
            insights_shared=len(transfers),
            agents_updated=len(agents_updated),
            transfers=transfers,
            latency_ms=round(latency_ms, 2),
            group_id=group_id
        )

    async def get_shared_insights(
        self,
        agent_name: str,
        group_id: str,
        teacher_name: Optional[str] = None,
        min_confidence: float = 0.8,
        limit: int = 20
    ) -> List[SharedInsight]:
        """
        Get insights shared to an agent from other agents.

        Args:
            agent_name: The agent receiving insights
            group_id: Project group for isolation
            teacher_name: Optional filter for specific teacher
            min_confidence: Minimum confidence score to include
            limit: Maximum results to return

        Returns:
            List of SharedInsight objects
        """
        # Enforce max limit
        limit = min(limit, 50)

        cypher = """
        MATCH (learner:AIAgent {name: $agent_name, group_id: $group_id})
              -[:CAN_APPLY]->(i:Insight)
        MATCH (teacher:AIAgent)-[:LEARNED]->(i)
        WHERE i.confidence_score >= $min_confidence
        """

        params = {
            "agent_name": agent_name,
            "group_id": group_id,
            "min_confidence": min_confidence
        }

        if teacher_name:
            cypher += " AND teacher.name = $teacher_name"
            params["teacher_name"] = teacher_name

        cypher += """
        RETURN i.insight_id as insight_id,
               i.rule as rule,
               i.category as category,
               i.confidence_score as confidence_score,
               i.success_rate as success_rate,
               i.learned_at as learned_at,
               teacher.name as teacher_agent
        ORDER BY i.confidence_score DESC, i.success_rate DESC
        LIMIT $limit
        """

        params["limit"] = limit

        records = await self._client.execute_query(cypher, params)

        insights = []
        for record in records:
            learned_at = record.get('learned_at')
            if hasattr(learned_at, 'to_native'):
                learned_at = learned_at.to_native()

            insights.append(SharedInsight(
                insight_id=record.get('insight_id', ''),
                rule=record.get('rule', ''),
                category=record.get('category', ''),
                confidence_score=record.get('confidence_score', 0.0),
                success_rate=record.get('success_rate', 0.0),
                learned_by=record.get('teacher_agent', ''),
                learned_at=learned_at or datetime.now(timezone.utc),
                teacher_agent=record.get('teacher_agent', '')
            ))

        return insights

    async def get_insights_to_share(
        self,
        group_id: str,
        teacher_name: Optional[str] = None
    ) -> List[Insight]:
        """
        Get all insights that can be shared (high-confidence).

        Args:
            group_id: Project group for isolation
            teacher_name: Optional filter for specific teacher

        Returns:
            List of Insight objects ready to share
        """
        cypher = """
        MATCH (teacher:AIAgent)-[:LEARNED]->(i:Insight)
        WHERE (i.group_id = $group_id OR i.group_id = 'global-coding-skills')
          AND i.confidence_score >= $threshold
          AND i.success_rate >= 0.8
        """

        params = {
            "group_id": group_id,
            "threshold": self.CONFIDENCE_THRESHOLD
        }

        if teacher_name:
            cypher += " AND teacher.name = $teacher_name"
            params["teacher_name"] = teacher_name

        cypher += """
        RETURN i.insight_id as insight_id,
               i.rule as rule,
               i.category as category,
               i.confidence_score as confidence_score,
               i.success_rate as success_rate,
               i.group_id as group_id,
               teacher.name as learned_by,
               i.learned_at as learned_at,
               i.applies_to as applies_to,
               i.metadata as metadata
        ORDER BY i.confidence_score DESC, i.success_rate DESC
        """

        records = await self._client.execute_query(cypher, params)

        insights = []
        for record in records:
            learned_at = record.get('learned_at')
            if hasattr(learned_at, 'to_native'):
                learned_at = learned_at.to_native()

            insights.append(Insight(
                insight_id=record.get('insight_id', ''),
                rule=record.get('rule', ''),
                category=record.get('category', ''),
                confidence_score=record.get('confidence_score', 0.0),
                success_rate=record.get('success_rate', 0.0),
                group_id=record.get('group_id', group_id),
                learned_by=record.get('learned_by', ''),
                learned_at=learned_at or datetime.now(timezone.utc),
                applies_to=record.get('applies_to'),
                metadata=record.get('metadata', {})
            ))

        return insights

    async def count_pending_shares(
        self,
        group_id: str
    ) -> Dict[str, int]:
        """
        Count insights pending to be shared across the group.

        Args:
            group_id: Project group for isolation

        Returns:
            Dictionary with pending counts
        """
        cypher = """
        MATCH (teacher:AIAgent)-[:LEARNED]->(i:Insight)
        WHERE (i.group_id = $group_id OR i.group_id = 'global-coding-skills')
          AND i.confidence_score >= $threshold
          AND i.success_rate >= 0.8

        MATCH (learner:AIAgent)
        WHERE learner.group_id = $group_id
          AND learner.name <> teacher.name
          AND NOT exists((learner)-[:CAN_APPLY]->(i))

        RETURN count(DISTINCT i) as insights_pending,
               count(DISTINCT learner) as agents_waiting,
               count(*) as total_shares_needed
        """

        records = await self._client.execute_query(
            cypher,
            {
                "group_id": group_id,
                "threshold": self.CONFIDENCE_THRESHOLD
            }
        )

        if records:
            return {
                "insights_pending": records[0].get('insights_pending', 0),
                "agents_waiting": records[0].get('agents_waiting', 0),
                "total_shares_needed": records[0].get('total_shares_needed', 0)
            }

        return {
            "insights_pending": 0,
            "agents_waiting": 0,
            "total_shares_needed": 0
        }


async def main():
    """Quick test of the knowledge transfer service."""
    import os
    os.environ['NEO4J_URI'] = 'bolt://localhost:7687'
    os.environ['NEO4J_USER'] = 'neo4j'
    os.environ['NEO4J_PASSWORD'] = 'Kamina2025*'

    from src.bmad.core.neo4j_client import Neo4jAsyncClient

    async with Neo4jAsyncClient() as client:
        service = KnowledgeTransferService(client)

        print("Testing knowledge transfer service...")

        # Check pending shares
        pending = await service.count_pending_shares("global-coding-skills")
        print(f"\nPending shares: {pending}")

        # Run knowledge transfer
        result = await service.share_high_confidence_insights("global-coding-skills")
        print(f"\nKnowledge Transfer Result:")
        print(f"  Insights shared: {result.insights_shared}")
        print(f"  Agents updated: {result.agents_updated}")
        print(f"  Latency: {result.latency_ms:.2f}ms")

        # Get shared insights for an agent
        if result.agents_updated > 0:
            insights = await service.get_shared_insights(
                "brooks",
                "global-coding-skills",
                limit=5
            )
            print(f"\nInsights shared to brooks: {len(insights)}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())