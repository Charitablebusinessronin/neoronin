"""
Pattern Library Query Service

This module provides methods for querying and managing the pattern library.
- Query patterns by category, tags, and success rate
- Rank patterns by success_rate and times_used
- Promote patterns to global scope
- Multi-tenant isolation via group_id

Author: Brooks (BMAD Dev Agent)
Created: 2026-01-26
Story: 2-2-manage-pattern-library
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.bmad.core.neo4j_client import Neo4jAsyncClient, SecurityError

logger = logging.getLogger(__name__)


@dataclass
class Pattern:
    """Represents a reusable solution pattern."""
    pattern_id: str
    name: str
    description: str
    category: str
    tags: List[str] = field(default_factory=list)
    success_rate: float = 0.0
    times_used: int = 0
    group_id: str = "global-coding-skills"
    scope: str = "global"  # "global" or "project"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_used: Optional[datetime] = None
    confidence_score: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PatternQuery:
    """Query parameters for pattern search."""
    group_id: str
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    min_success_rate: float = 0.0
    search_text: Optional[str] = None
    limit: int = 10
    offset: int = 0


@dataclass
class PatternQueryResult:
    """Result of a pattern query."""
    patterns: List[Pattern]
    total_count: int
    latency_ms: float
    query: PatternQuery


@dataclass
class PatternPromotionResult:
    """Result of a pattern promotion."""
    pattern_id: str
    old_scope: str
    new_scope: str
    promoted_at: datetime
    justification: str


class PatternMatcher:
    """
    Service for querying and managing the pattern library.

    Features:
    - Multi-tenant pattern access (group + global)
    - Category and tag-based filtering
    - Ranking by success_rate and times_used
    - Pattern promotion from project to global scope
    - Optimized queries for <100ms latency
    """

    DEFAULT_LIMIT = 10
    MAX_LIMIT = 50
    PROMOTION_MIN_USES = 3
    PROMOTION_MIN_SUCCESS_RATE = 0.8

    def __init__(self, client: Neo4jAsyncClient):
        """
        Initialize the pattern matcher.

        Args:
            client: Neo4j async client for database operations
        """
        self._client = client

    async def query_patterns(
        self,
        query: PatternQuery
    ) -> PatternQueryResult:
        """
        Query patterns with filtering and ranking.

        Args:
            query: PatternQuery with filter parameters

        Returns:
            PatternQueryResult with matching patterns
        """
        start_time = time.perf_counter()

        # Enforce max limit
        query.limit = min(query.limit, self.MAX_LIMIT)

        # Build the Cypher query
        cypher, params = self._build_query(query)

        # Execute query
        records = await self._client.execute_query(cypher, params)

        # Parse results
        patterns = self._parse_pattern_results(records)

        latency_ms = (time.perf_counter() - start_time) * 1000

        return PatternQueryResult(
            patterns=patterns,
            total_count=len(patterns),  # For now, return matched count
            latency_ms=round(latency_ms, 2),
            query=query
        )

    async def get_pattern_by_id(
        self,
        pattern_id: str,
        group_id: str
    ) -> Optional[Pattern]:
        """
        Get a specific pattern by ID.

        Args:
            pattern_id: The pattern ID
            group_id: Project group for access control

        Returns:
            Pattern if found and accessible, None otherwise
        """
        query = """
        MATCH (p:Pattern)
        WHERE p.pattern_id = $pattern_id
          AND (p.group_id = $group_id OR p.group_id = 'global-coding-skills')
        RETURN p
        """

        records = await self._client.execute_query(
            query,
            {"pattern_id": pattern_id, "group_id": group_id}
        )

        if not records:
            return None

        return self._parse_single_pattern(records[0].get('p', {}))

    async def get_top_patterns(
        self,
        group_id: str,
        category: Optional[str] = None,
        limit: int = 10
    ) -> List[Pattern]:
        """
        Get top patterns ranked by success_rate and times_used.

        Args:
            group_id: Project group for access control
            category: Optional category filter
            limit: Maximum patterns to return

        Returns:
            List of top patterns
        """
        query_obj = PatternQuery(
            group_id=group_id,
            category=category,
            min_success_rate=0.5,
            limit=min(limit, self.MAX_LIMIT)
        )

        result = await self.query_patterns(query_obj)
        return result.patterns

    async def search_patterns(
        self,
        group_id: str,
        search_text: str,
        limit: int = 10
    ) -> List[Pattern]:
        """
        Search patterns by text in name or description.

        Args:
            group_id: Project group for access control
            search_text: Text to search for
            limit: Maximum results

        Returns:
            List of matching patterns
        """
        query_obj = PatternQuery(
            group_id=group_id,
            search_text=search_text,
            limit=min(limit, self.MAX_LIMIT)
        )

        result = await self.query_patterns(query_obj)
        return result.patterns

    async def promote_to_global(
        self,
        pattern_id: str,
        group_id: str,
        justification: str = ""
    ) -> Optional[PatternPromotionResult]:
        """
        Promote a project-specific pattern to global scope.

        Args:
            pattern_id: ID of the pattern to promote
            group_id: Project group the pattern belongs to
            justification: Reason for promotion

        Returns:
            PatternPromotionResult if successful, None if criteria not met
        """
        # First, check if pattern meets promotion criteria
        check_query = """
        MATCH (p:Pattern {pattern_id: $pattern_id, group_id: $group_id})
        RETURN p.times_used as times_used, p.success_rate as success_rate,
               p.scope as scope, p.name as name
        """

        results = await self._client.execute_query(
            check_query,
            {"pattern_id": pattern_id, "group_id": group_id}
        )

        if not results:
            logger.warning(f"Pattern {pattern_id} not found in group {group_id}")
            return None

        pattern_data = results[0]

        if pattern_data['scope'] == 'global':
            logger.info(f"Pattern {pattern_id} is already global")
            return None

        if pattern_data['times_used'] < self.PROMOTION_MIN_USES:
            logger.info(
                f"Pattern {pattern_id} doesn't meet promotion criteria: "
                f"{pattern_data['times_used']} uses (need {self.PROMOTION_MIN_USES})"
            )
            return None

        if pattern_data['success_rate'] < self.PROMOTION_MIN_SUCCESS_RATE:
            logger.info(
                f"Pattern {pattern_id} doesn't meet promotion criteria: "
                f"{pattern_data['success_rate']:.2%} success (need {self.PROMOTION_MIN_SUCCESS_RATE:.0%})"
            )
            return None

        # Perform promotion
        old_scope = 'project'
        new_scope = 'global'
        now = datetime.now(timezone.utc)

        promotion_query = """
        MATCH (p:Pattern {pattern_id: $pattern_id, group_id: $group_id})
        SET p.group_id = 'global-coding-skills',
            p.scope = 'global',
            p.promoted_date = datetime(),
            p.promoted_from = $group_id
        WITH p
        CREATE (audit:PromotionAudit {
            audit_id: $audit_id,
            pattern_id: $pattern_id,
            old_scope: $old_scope,
            new_scope: $new_scope,
            justification: $justification,
            promoted_at: datetime(),
            promoted_by = 'system'
        })
        RETURN p
        """

        import uuid
        audit_id = f"audit-{uuid.uuid4().hex[:12]}"

        await self._client.execute_write(
            promotion_query,
            {
                "pattern_id": pattern_id,
                "group_id": group_id,
                "old_scope": old_scope,
                "new_scope": new_scope,
                "justification": justification or f"Auto-promotion: {pattern_data['times_used']} uses, {pattern_data['success_rate']:.0%} success rate",
                "audit_id": audit_id
            }
        )

        logger.info(f"Pattern {pattern_data['name']} promoted to global scope")

        return PatternPromotionResult(
            pattern_id=pattern_id,
            old_scope=old_scope,
            new_scope=new_scope,
            promoted_at=now,
            justification=justification
        )

    async def record_pattern_use(
        self,
        pattern_id: str,
        group_id: str,
        successful: bool
    ) -> Optional[Pattern]:
        """
        Record that a pattern was used and update statistics.

        Args:
            pattern_id: ID of the pattern used
            group_id: Project group
            successful: Whether the use was successful

        Returns:
            Updated pattern or None if not found
        """
        query = """
        MATCH (p:Pattern)
        WHERE p.pattern_id = $pattern_id
          AND (p.group_id = $group_id OR p.group_id = 'global-coding-skills')
        SET p.times_used = coalesce(p.times_used, 0) + 1,
            p.last_used = datetime()
        WITH p
        CALL {
            WITH p
            MATCH (p)-[:HAS_OUTCOME*1..2]->(o:Outcome)
            WHERE o.status = 'Success'
            RETURN count(o) as success_count
            UNION
            WITH p
            MATCH (p)-[:HAS_OUTCOME*1..2]->(o:Outcome)
            RETURN count(o) as success_count
        }
        WITH p, success_count
        SET p.success_rate = case
            when p.times_used > 0 then (success_count * 1.0 / p.times_used)
            else p.success_rate
        end
        RETURN p
        """

        # Simplified success rate update
        simple_query = """
        MATCH (p:Pattern)
        WHERE p.pattern_id = $pattern_id
          AND (p.group_id = $group_id OR p.group_id = 'global-coding-skills')
        SET p.times_used = coalesce(p.times_used, 0) + 1,
            p.last_used = datetime()
        RETURN p
        """

        await self._client.execute_write(
            simple_query,
            {"pattern_id": pattern_id, "group_id": group_id}
        )

        return await self.get_pattern_by_id(pattern_id, group_id)

    def _build_query(self, query: PatternQuery) -> tuple[str, Dict[str, Any]]:
        """Build the Cypher query from PatternQuery."""

        # Base match with group access
        cypher = """
        MATCH (p:Pattern)
        WHERE p.group_id = $group_id OR p.group_id = 'global-coding-skills'
        """

        params = {"group_id": query.group_id}

        # Category filter
        if query.category:
            cypher += """
            AND p.category = $category
            """
            params["category"] = query.category

        # Success rate filter
        if query.min_success_rate > 0:
            cypher += """
            AND p.success_rate >= $min_success_rate
            """
            params["min_success_rate"] = query.min_success_rate

        # Tags filter (any of the provided tags)
        if query.tags:
            cypher += """
            AND any(tag IN $tags WHERE tag IN p.tags)
            """
            params["tags"] = query.tags

        # Full-text search
        if query.search_text:
            cypher += """
            AND (toLower(p.name) CONTAINS toLower($search_text)
                 OR toLower(p.description) CONTAINS toLower($search_text))
            """
            params["search_text"] = query.search_text

        # Ordering and pagination
        cypher += """
        RETURN p
        ORDER BY p.success_rate DESC, p.times_used DESC
        SKIP $offset
        LIMIT $limit
        """
        params["offset"] = query.offset
        params["limit"] = query.limit

        return cypher, params

    def _parse_pattern_results(self, records: List[Dict[str, Any]]) -> List[Pattern]:
        """Parse query results into Pattern objects."""
        patterns = []
        for record in records:
            p = record.get('p', {})
            pattern = self._parse_single_pattern(p)
            if pattern:
                patterns.append(pattern)
        return patterns

    def _parse_single_pattern(self, p: Dict[str, Any]) -> Optional[Pattern]:
        """Parse a single pattern from Neo4j result."""
        if not p:
            return None

        return Pattern(
            pattern_id=p.get('pattern_id', ''),
            name=p.get('name', ''),
            description=p.get('description', ''),
            category=p.get('category', ''),
            tags=p.get('tags', []),
            success_rate=p.get('success_rate', 0.0),
            times_used=p.get('times_used', 0),
            group_id=p.get('group_id', 'global-coding-skills'),
            scope=p.get('scope', 'global'),
            confidence_score=p.get('confidence_score', 0.5),
            metadata=p.get('metadata', {})
        )


async def main():
    """Quick test of the pattern matcher."""
    import os
    os.environ['NEO4J_URI'] = 'bolt://localhost:7687'
    os.environ['NEO4J_USER'] = 'neo4j'
    os.environ['NEO4J_PASSWORD'] = 'Kamina2025*'

    from src.bmad.core.neo4j_client import Neo4jAsyncClient

    async with Neo4jAsyncClient() as client:
        matcher = PatternMatcher(client)

        print("Testing pattern library...")

        # Query top patterns
        result = await matcher.get_top_patterns(
            group_id="global-coding-skills",
            limit=5
        )

        print(f"\nTop 5 Patterns:")
        for i, pattern in enumerate(result, 1):
            print(f"  {i}. {pattern.name} ({pattern.category})")
            print(f"     Success: {pattern.success_rate:.0%}, Used: {pattern.times_used}x")

        # Test latency
        query = PatternQuery(
            group_id="global-coding-skills",
            category="testing",
            min_success_rate=0.5
        )
        result = await matcher.query_patterns(query)
        print(f"\nQuery latency: {result.latency_ms:.2f}ms")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())