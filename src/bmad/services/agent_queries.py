"""
Agent Work History Query Service

This module provides query methods for agents to retrieve their work history,
enabling self-reflection and learning from past outcomes.

Author: Brooks (BMAD Dev Agent)
Created: 2026-01-26
Story: 1-3-query-and-review-agent-work-history
"""

import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from src.bmad.core.neo4j_client import Neo4jAsyncClient, SecurityError

logger = logging.getLogger(__name__)


class OutcomeStatus(str, Enum):
    """Outcome status enumeration."""
    SUCCESS = "Success"
    FAILED = "Failed"
    ALL = "All"


@dataclass
class WorkEvent:
    """Represents a work event in agent history."""
    event_id: str
    event_type: str
    timestamp: datetime
    group_id: str
    description: str
    tool_name: Optional[str] = None
    input_hash: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkOutcome:
    """Represents an outcome from a work event."""
    outcome_id: str
    status: str
    result_summary: str
    error_log: Optional[str] = None
    duration_ms: Optional[float] = None


@dataclass
class AppliedPattern:
    """Represents a pattern applied to an event."""
    pattern_id: str
    pattern_name: str
    category: str
    confidence_score: float


@dataclass
class GeneratedInsight:
    """Represents an insight generated from an outcome."""
    insight_id: str
    rule: str
    confidence_score: float
    category: str


@dataclass
class WorkHistoryEntry:
    """Complete work history entry with event, outcome, patterns, and insights."""
    event: WorkEvent
    outcome: Optional[WorkOutcome] = None
    patterns: List[AppliedPattern] = field(default_factory=list)
    insights: List[GeneratedInsight] = field(default_factory=list)


@dataclass
class WorkHistoryQueryResult:
    """Result of a work history query."""
    entries: List[WorkHistoryEntry]
    total_count: int
    latency_ms: float
    query_params: Dict[str, Any]


class AgentQueryService:
    """
    Service for querying agent work history and learning from past outcomes.

    Features:
    - Query recent work history with date range filtering
    - Filter by outcome status (Success/Failed/All)
    - Multi-tenant isolation with group_id enforcement
    - Pattern and insight inclusion in results
    - Performance optimization for <100ms latency
    """

    DEFAULT_PAGE_SIZE = 50
    MAX_PAGE_SIZE = 200
    DEFAULT_DAYS_BACK = 30

    def __init__(self, client: Neo4jAsyncClient):
        """
        Initialize the query service.

        Args:
            client: Neo4j async client for database operations
        """
        self._client = client

    async def query_work_history(
        self,
        agent_name: str,
        group_id: str,
        days_back: int = DEFAULT_DAYS_BACK,
        outcome_status: OutcomeStatus = OutcomeStatus.ALL,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
        include_patterns: bool = True,
        include_insights: bool = True
    ) -> WorkHistoryQueryResult:
        """
        Query an agent's work history with filtering options.

        Args:
            agent_name: Name of the agent querying their history
            group_id: Project group ID for multi-tenant isolation
            days_back: Number of days to look back (default: 30)
            outcome_status: Filter by outcome status (default: ALL)
            page: Page number for pagination (default: 1)
            page_size: Results per page (default: 50, max: 200)
            include_patterns: Include applied patterns in results
            include_insights: Include generated insights in results

        Returns:
            WorkHistoryQueryResult with entries and metadata

        Raises:
            SecurityError: If group_id validation fails
        """
        # Validate and cap page_size
        page_size = min(page_size, self.MAX_PAGE_SIZE)
        skip = (page - 1) * page_size

        start_time = time.perf_counter()

        # Build the query based on filters
        query, params = self._build_history_query(
            agent_name=agent_name,
            group_id=group_id,
            days_back=days_back,
            outcome_status=outcome_status,
            skip=skip,
            limit=page_size,
            include_patterns=include_patterns,
            include_insights=include_insights
        )

        # Execute query
        records = await self._client.execute_query(query, params)

        # Parse results
        entries = self._parse_history_results(records)

        latency_ms = (time.perf_counter() - start_time) * 1000

        return WorkHistoryQueryResult(
            entries=entries,
            total_count=len(entries),  # For now, return count of returned items
            latency_ms=round(latency_ms, 2),
            query_params={
                "agent_name": agent_name,
                "group_id": group_id,
                "days_back": days_back,
                "outcome_status": outcome_status.value,
                "page": page,
                "page_size": page_size
            }
        )

    async def query_failures(
        self,
        agent_name: str,
        group_id: str,
        days_back: int = 7
    ) -> WorkHistoryQueryResult:
        """
        Query an agent's failed outcomes for learning.

        Args:
            agent_name: Name of the agent
            group_id: Project group ID
            days_back: Number of days to look back (default: 7)

        Returns:
            WorkHistoryQueryResult with failed outcomes and lessons learned
        """
        return await self.query_work_history(
            agent_name=agent_name,
            group_id=group_id,
            days_back=days_back,
            outcome_status=OutcomeStatus.FAILED,
            include_patterns=True,
            include_insights=True
        )

    async def get_event_chain(
        self,
        agent_name: str,
        group_id: str,
        event_id: str
    ) -> Optional[WorkHistoryEntry]:
        """
        Get a complete Event → Solution → Outcome chain for a specific event.

        Args:
            agent_name: Name of the agent
            group_id: Project group ID
            event_id: ID of the event to retrieve

        Returns:
            WorkHistoryEntry with complete chain or None if not found
        """
        query = """
        MATCH (agent:AIAgent {name: $agent_name})-[:PERFORMED]->(e:Event {group_id: $group_id})
        WHERE elementId(e) = $event_id OR e.event_id = $event_id
        MATCH (e)-[:HAS_OUTCOME]->(o:Outcome)
        OPTIONAL MATCH (e)-[:USED_PATTERN]->(p:Pattern)
        OPTIONAL MATCH (o)-[:GENERATED]->(i:Insight)
        RETURN e, o, collect(p) as patterns, collect(i) as insights
        """

        params = {
            "agent_name": agent_name,
            "group_id": group_id,
            "event_id": event_id
        }

        records = await self._client.execute_query(query, params)

        if not records:
            return None

        entries = self._parse_history_results(records)
        return entries[0] if entries else None

    def _build_history_query(
        self,
        agent_name: str,
        group_id: str,
        days_back: int,
        outcome_status: OutcomeStatus,
        skip: int,
        limit: int,
        include_patterns: bool,
        include_insights: bool
    ) -> tuple[str, Dict[str, Any]]:
        """Build the Cypher query for work history."""

        # Base match clause
        query = """
        MATCH (agent:AIAgent {name: $agent_name})-[:PERFORMED]->(e:Event)
        WHERE e.group_id = $group_id
          AND e.timestamp > datetime() - duration({days: $days_back})
        """

        params = {
            "agent_name": agent_name,
            "group_id": group_id,
            "days_back": days_back
        }

        # Add outcome filter
        if outcome_status != OutcomeStatus.ALL:
            query += """
            MATCH (e)-[:HAS_OUTCOME]->(o:Outcome {status: $outcome_status})
            """
            params["outcome_status"] = outcome_status.value
        else:
            query += """
            MATCH (e)-[:HAS_OUTCOME]->(o:Outcome)
            """

        # Add optional pattern matching
        if include_patterns:
            query += """
            OPTIONAL MATCH (e)-[:USED_PATTERN]->(p:Pattern)
            """
        else:
            query += """
            OPTIONAL MATCH (e)-[:USED_PATTERN]->(p:Pattern)
            WHERE false
            """

        # Add optional insight matching
        if include_insights:
            query += """
            OPTIONAL MATCH (o)-[:GENERATED]->(i:Insight)
            """
        else:
            query += """
            OPTIONAL MATCH (o)-[:GENERATED]->(i:Insight)
            WHERE false
            """

        # Return clause
        query += """
        RETURN e, o, collect(DISTINCT p) as patterns, collect(DISTINCT i) as insights
        ORDER BY e.timestamp DESC
        SKIP $skip
        LIMIT $limit
        """

        params["skip"] = skip
        params["limit"] = limit

        return query, params

    def _parse_history_results(self, records: List[Dict[str, Any]]) -> List[WorkHistoryEntry]:
        """Parse query results into WorkHistoryEntry objects."""
        entries = []

        for record in records:
            e = record.get('e', {})
            o = record.get('o', {})
            patterns = record.get('patterns', [])
            insights = record.get('insights', [])

            # Parse event
            event = WorkEvent(
                event_id=e.get('event_id', ''),
                event_type=e.get('event_type', ''),
                timestamp=self._parse_datetime(e.get('timestamp')),
                group_id=e.get('group_id', ''),
                description=e.get('description', ''),
                tool_name=e.get('tool_name'),
                input_hash=e.get('input_hash'),
                metadata=e.get('metadata', {})
            )

            # Parse outcome
            outcome = None
            if o:
                outcome = WorkOutcome(
                    outcome_id=o.get('outcome_id', ''),
                    status=o.get('status', ''),
                    result_summary=o.get('result_summary', ''),
                    error_log=o.get('error_log'),
                    duration_ms=o.get('duration_ms')
                )

            # Parse patterns
            applied_patterns = []
            for p in patterns:
                if p:
                    applied_patterns.append(AppliedPattern(
                        pattern_id=p.get('pattern_id', ''),
                        pattern_name=p.get('name', ''),
                        category=p.get('category', ''),
                        confidence_score=p.get('confidence_score', 0.0)
                    ))

            # Parse insights
            generated_insights = []
            for i in insights:
                if i:
                    generated_insights.append(GeneratedInsight(
                        insight_id=i.get('insight_id', ''),
                        rule=i.get('rule', ''),
                        confidence_score=i.get('confidence_score', 0.0),
                        category=i.get('category', '')
                    ))

            entries.append(WorkHistoryEntry(
                event=event,
                outcome=outcome,
                patterns=applied_patterns,
                insights=generated_insights
            ))

        return entries

    def _parse_datetime(self, dt_value: Any) -> datetime:
        """Parse datetime from Neo4j result."""
        if dt_value is None:
            return datetime.now(timezone.utc)

        if isinstance(dt_value, datetime):
            return dt_value

        if hasattr(dt_value, 'to_native'):
            return dt_value.to_native()

        # Try parsing string
        if isinstance(dt_value, str):
            try:
                return datetime.fromisoformat(dt_value.replace('Z', '+00:00'))
            except ValueError:
                pass

        return datetime.now(timezone.utc)


async def main():
    """Quick test of the query service."""
    import os
    os.environ['NEO4J_URI'] = 'bolt://localhost:7687'
    os.environ['NEO4J_USER'] = 'neo4j'
    os.environ['NEO4J_PASSWORD'] = 'Kamina2025*'

    from src.bmad.core.neo4j_client import Neo4jAsyncClient

    async with Neo4jAsyncClient() as client:
        service = AgentQueryService(client)

        print("Testing work history query for Brooks...")
        result = await service.query_work_history(
            agent_name="Brooks",
            group_id="global-coding-skills",
            days_back=30
        )

        print(f"\nQuery Results:")
        print(f"  Total entries: {result.total_count}")
        print(f"  Latency: {result.latency_ms:.2f}ms")

        for entry in result.entries[:3]:
            print(f"\n  Event: {entry.event.event_type}")
            print(f"    Timestamp: {entry.event.timestamp}")
            print(f"    Outcome: {entry.outcome.status if entry.outcome else 'N/A'}")
            if entry.patterns:
                print(f"    Patterns: {[p.pattern_name for p in entry.patterns]}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())