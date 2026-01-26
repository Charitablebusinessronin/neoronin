"""
Audit Logging Service

This module provides audit trail functionality for tracking all data access.
- Log all group_id access attempts
- Record cross-group access attempts (potential security events)
- Provide audit report endpoints for security review

Author: Brooks (BMAD Dev Agent)
Created: 2026-01-26
Story: 3-1-enforce-multi-tenant-isolation
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.bmad.core.neo4j_client import Neo4jAsyncClient

logger = logging.getLogger(__name__)


@dataclass
class AuditLogEntry:
    """Represents a single audit log entry."""
    audit_id: str
    timestamp: datetime
    agent_name: str
    group_id: str
    action: str  # "query", "write", "schema", "health"
    query_type: str  # "read", "write"
    success: bool
    group_accessed: str
    cross_group_attempt: bool
    error_message: Optional[str] = None
    query_preview: Optional[str] = None
    latency_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AuditQueryFilters:
    """Query parameters for audit log search."""
    agent_name: Optional[str] = None
    group_id: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    action: Optional[str] = None
    cross_group_only: bool = False
    failed_only: bool = False
    limit: int = 100


@dataclass
class AuditSummary:
    """Summary statistics for audit logs."""
    total_accesses: int
    cross_group_attempts: int
    failed_accesses: int
    unique_agents: int
    unique_groups: int
    by_agent: Dict[str, int]
    by_group: Dict[str, int]
    by_action: Dict[str, int]


class AuditLogger:
    """
    Service for logging and querying audit trails.

    Features:
    - Log all data access attempts with group_id context
    - Flag cross-group access attempts
    - Query audit logs with filters
    - Generate summary statistics

    Note: This service has its group_id validation disabled
    to allow logging access from any tenant context.
    """

    def __init__(self, client: Neo4jAsyncClient):
        """
        Initialize the audit logger.

        Args:
            client: Neo4j async client for database operations
        """
        self._client = client

    async def log_access(
        self,
        agent_name: str,
        group_id: str,
        action: str,
        query_type: str,
        success: bool,
        group_accessed: str,
        cross_group_attempt: bool = False,
        error_message: Optional[str] = None,
        query_preview: Optional[str] = None,
        latency_ms: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log a data access attempt.

        Args:
            agent_name: Name of the agent making the access
            group_id: The agent's assigned group
            action: Type of action (query, write, schema, health)
            query_type: read or write
            success: Whether the access was successful
            group_accessed: The group being accessed
            cross_group_attempt: Whether this was a cross-group attempt
            error_message: Error message if failed
            query_preview: First 200 chars of query
            latency_ms: Query execution time
            metadata: Additional metadata

        Returns:
            The audit_id of the created log entry
        """
        import uuid

        audit_id = f"audit-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)

        cypher = """
        CREATE (a:AuditLog {
            audit_id: $audit_id,
            timestamp: datetime($timestamp),
            agent_name: $agent_name,
            agent_group_id: $agent_group_id,
            action: $action,
            query_type: $query_type,
            success: $success,
            group_accessed: $group_accessed,
            cross_group_attempt: $cross_group_attempt,
            error_message: $error_message,
            query_preview: $query_preview,
            latency_ms: $latency_ms,
            metadata: $metadata
        })
        RETURN a.audit_id as audit_id
        """

        await self._client.execute_write(
            cypher,
            {
                "audit_id": audit_id,
                "timestamp": now.isoformat(),
                "agent_name": agent_name,
                "agent_group_id": group_id,
                "action": action,
                "query_type": query_type,
                "success": success,
                "group_accessed": group_accessed,
                "cross_group_attempt": cross_group_attempt,
                "error_message": error_message,
                "query_preview": query_preview[:200] if query_preview else None,
                "latency_ms": latency_ms,
                "metadata": metadata or {}
            },
            validate_group_id=False  # Audit logger can access any group
        )

        if cross_group_attempt:
            logger.warning(
                f"Cross-group access attempt: agent={agent_name} "
                f"from={group_id} accessed={group_accessed}"
            )

        return audit_id

    async def query_audit_logs(
        self,
        filters: AuditQueryFilters
    ) -> List[AuditLogEntry]:
        """
        Query audit logs with filters.

        Args:
            filters: Query parameters for filtering

        Returns:
            List of matching audit log entries
        """
        # Build the query dynamically
        conditions = []
        params = {}

        if filters.agent_name:
            conditions.append("a.agent_name = $agent_name")
            params["agent_name"] = filters.agent_name

        if filters.group_id:
            conditions.append("a.agent_group_id = $group_id")
            params["group_id"] = filters.group_id

        if filters.start_time:
            conditions.append("a.timestamp >= datetime($start_time)")
            params["start_time"] = filters.start_time.isoformat()

        if filters.end_time:
            conditions.append("a.timestamp <= datetime($end_time)")
            params["end_time"] = filters.end_time.isoformat()

        if filters.action:
            conditions.append("a.action = $action")
            params["action"] = filters.action

        if filters.cross_group_only:
            conditions.append("a.cross_group_attempt = true")

        if filters.failed_only:
            conditions.append("a.success = false")

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        cypher = f"""
        MATCH (a:AuditLog)
        WHERE {where_clause}
        RETURN a
        ORDER BY a.timestamp DESC
        LIMIT $limit
        """

        params["limit"] = min(filters.limit, 500)

        records = await self._client.execute_query(
            cypher,
            params,
            validate_group_id=False  # Audit logger can query all logs
        )

        entries = []
        for record in records:
            a = record.get('a', {})
            timestamp = a.get('timestamp')
            if hasattr(timestamp, 'to_native'):
                timestamp = timestamp.to_native()

            entries.append(AuditLogEntry(
                audit_id=a.get('audit_id', ''),
                timestamp=timestamp or datetime.now(timezone.utc),
                agent_name=a.get('agent_name', ''),
                group_id=a.get('agent_group_id', ''),
                action=a.get('action', ''),
                query_type=a.get('query_type', ''),
                success=a.get('success', False),
                group_accessed=a.get('group_accessed', ''),
                cross_group_attempt=a.get('cross_group_attempt', False),
                error_message=a.get('error_message'),
                query_preview=a.get('query_preview'),
                latency_ms=a.get('latency_ms', 0.0),
                metadata=a.get('metadata', {})
            ))

        return entries

    async def get_summary(
        self,
        group_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> AuditSummary:
        """
        Get summary statistics for audit logs.

        Args:
            group_id: Optional filter by agent group
            start_time: Start of time range
            end_time: End of time range

        Returns:
            AuditSummary with statistics
        """
        conditions = []
        params = {}

        if group_id:
            conditions.append("a.agent_group_id = $group_id")
            params["group_id"] = group_id

        if start_time:
            conditions.append("a.timestamp >= datetime($start_time)")
            params["start_time"] = start_time.isoformat()

        if end_time:
            conditions.append("a.timestamp <= datetime($end_time)")
            params["end_time"] = end_time.isoformat()

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        cypher = f"""
        MATCH (a:AuditLog)
        WHERE {where_clause}

        WITH a

        OPTIONAL MATCH (a)-[:BY_AGENT]->(agent:AIAgent)
        OPTIONAL MATCH (a)-[:ACCESSED_GROUP]->(grp:ProjectGroup)

        RETURN count(a) as total_accesses,
               sum(case when a.cross_group_attempt = true then 1 else 0 end) as cross_group,
               sum(case when a.success = false then 1 else 0 end) as failed,
               count(distinct a.agent_name) as unique_agents,
               count(distinct a.agent_group_id) as unique_groups
        """

        summary_records = await self._client.execute_query(
            cypher,
            params,
            validate_group_id=False
        )

        # Get breakdown by agent
        agent_cypher = f"""
        MATCH (a:AuditLog)
        WHERE {where_clause}
        RETURN a.agent_name as agent, count(a) as count
        ORDER BY count DESC
        LIMIT 10
        """

        agent_records = await self._client.execute_query(
            agent_cypher, params, validate_group_id=False
        )

        # Get breakdown by group
        group_cypher = f"""
        MATCH (a:AuditLog)
        WHERE {where_clause}
        RETURN a.group_accessed as grp, count(a) as count
        ORDER BY count DESC
        LIMIT 10
        """

        group_records = await self._client.execute_query(
            group_cypher, params, validate_group_id=False
        )

        # Get breakdown by action
        action_cypher = f"""
        MATCH (a:AuditLog)
        WHERE {where_clause}
        RETURN a.action as action, count(a) as count
        """

        action_records = await self._client.execute_query(
            action_cypher, params, validate_group_id=False
        )

        summary = summary_records[0] if summary_records else {}

        return AuditSummary(
            total_accesses=summary.get('total_accesses', 0),
            cross_group_attempts=summary.get('cross_group', 0),
            failed_accesses=summary.get('failed', 0),
            unique_agents=summary.get('unique_agents', 0),
            unique_groups=summary.get('unique_groups', 0),
            by_agent={r.get('agent', ''): r.get('count', 0) for r in agent_records},
            by_group={r.get('grp', ''): r.get('count', 0) for r in group_records},
            by_action={r.get('action', ''): r.get('count', 0) for r in action_records}
        )

    async def get_cross_group_attempts(
        self,
        limit: int = 50
    ) -> List[AuditLogEntry]:
        """
        Get all cross-group access attempts.

        Args:
            limit: Maximum number to return

        Returns:
            List of cross-group access log entries
        """
        cypher = """
        MATCH (a:AuditLog)
        WHERE a.cross_group_attempt = true
        RETURN a
        ORDER BY a.timestamp DESC
        LIMIT $limit
        """

        records = await self._client.execute_query(
            cypher,
            {"limit": limit},
            validate_group_id=False
        )

        entries = []
        for record in records:
            a = record.get('a', {})
            timestamp = a.get('timestamp')
            if hasattr(timestamp, 'to_native'):
                timestamp = timestamp.to_native()

            entries.append(AuditLogEntry(
                audit_id=a.get('audit_id', ''),
                timestamp=timestamp or datetime.now(timezone.utc),
                agent_name=a.get('agent_name', ''),
                group_id=a.get('agent_group_id', ''),
                action=a.get('action', ''),
                query_type=a.get('query_type', ''),
                success=a.get('success', False),
                group_accessed=a.get('group_accessed', ''),
                cross_group_attempt=True,
                error_message=a.get('error_message'),
                query_preview=a.get('query_preview'),
                latency_ms=a.get('latency_ms', 0.0),
                metadata=a.get('metadata', {})
            ))

        return entries


async def main():
    """Quick test of the audit logger."""
    import os
    os.environ['NEO4J_URI'] = 'bolt://localhost:7687'
    os.environ['NEO4J_USER'] = 'neo4j'
    os.environ['NEO4J_PASSWORD'] = 'Kamina2025*'

    from src.bmad.core.neo4j_client import Neo4jAsyncClient

    async with Neo4jAsyncClient() as client:
        logger_service = AuditLogger(client)

        print("Testing audit logger...")

        # Log some access attempts
        await logger_service.log_access(
            agent_name="brooks",
            group_id="faith-meats",
            action="query",
            query_type="read",
            success=True,
            group_accessed="faith-meats",
            latency_ms=15.5
        )

        await logger_service.log_access(
            agent_name="brooks",
            group_id="faith-meats",
            action="query",
            query_type="read",
            success=False,
            group_accessed="diff-driven-saas",
            cross_group_attempt=True,
            error_message="SecurityError: group_id mismatch"
        )

        # Query audit logs
        filters = AuditQueryFilters(
            agent_name="brooks",
            limit=10
        )
        logs = await logger_service.query_audit_logs(filters)
        print(f"\nFound {len(logs)} audit log entries")

        # Get cross-group attempts
        cross_group = await logger_service.get_cross_group_attempts()
        print(f"Cross-group attempts: {len(cross_group)}")

        # Get summary
        summary = await logger_service.get_summary()
        print(f"\nAudit Summary:")
        print(f"  Total accesses: {summary.total_accesses}")
        print(f"  Cross-group attempts: {summary.cross_group_attempts}")
        print(f"  Failed: {summary.failed_accesses}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())