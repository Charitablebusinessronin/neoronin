"""
Event Aggregation Service

This module aggregates old events into summary nodes for performance.
- Events older than 30 days are aggregated by type and group_id
- Original events are archived to CSV and deleted
- Aggregation preserves metrics while reducing graph size

Author: Brooks (BMAD Dev Agent)
Created: 2026-01-26
Story: 4-3-aggregate-old-events
"""

import csv
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.bmad.core.neo4j_client import Neo4jAsyncClient

logger = logging.getLogger(__name__)


@dataclass
class EventSummary:
    """Summary of aggregated events."""
    event_type: str
    group_id: str
    count: int
    period: str
    first_event: datetime
    last_event: datetime


@dataclass
class AggregationMetrics:
    """Metrics from an aggregation operation."""
    events_aggregated: int
    summaries_created: int
    events_archived: int
    archive_path: str
    processing_time_ms: float
    group_id: str
    timestamp: datetime


@dataclass
class ArchivedEvent:
    """An event that has been archived."""
    event_id: str
    event_type: str
    timestamp: str
    group_id: str
    description: str
    archived_at: str
    archive_reason: str


class EventAggregationService:
    """
    Service for aggregating old events into summaries.

    Features:
    - Aggregate events by type and group_id
    - Archive original events to CSV
    - Delete archived events from graph
    - Multi-tenant isolation via group_id
    """

    # Configuration constants
    EVENT_AGE_DAYS = 30
    ARCHIVE_DIR = "/home/ronin/development/Neo4j/data/archived_events"

    def __init__(
        self,
        client: Neo4jAsyncClient,
        archive_dir: Optional[str] = None
    ):
        """
        Initialize the event aggregation service.

        Args:
            client: Neo4j async client
            archive_dir: Optional custom archive directory
        """
        self._client = client
        default_dir = os.environ.get(
            'EVENT_ARCHIVE_DIR',
            archive_dir or '/home/ronin/development/Neo4j/data/archived_events'
        )
        self._archive_dir = Path(default_dir)
        self._archive_dir.mkdir(parents=True, exist_ok=True)

    async def aggregate_events(
        self,
        group_id: Optional[str] = None,
        event_age_days: int = EVENT_AGE_DAYS,
        dry_run: bool = False
    ) -> AggregationMetrics:
        """
        Aggregate old events into EventSummary nodes.

        Args:
            group_id: Optional specific group to process (None for all)
            event_age_days: Age threshold for aggregation
            dry_run: If True, simulate without making changes

        Returns:
            AggregationMetrics with operation results
        """
        start_time = datetime.now(timezone.utc)
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=event_age_days)

        logger.info(f"Starting event aggregation (dry_run={dry_run})")

        # Get event IDs for archival first (before aggregation)
        # Find summary metrics for aggregation
        events_to_aggregate = await self._find_old_events(group_id, cutoff_date)

        logger.info(f"Found {len(events_to_aggregate)} aggregation groups")

        # Find specific event IDs for archival and deletion
        event_ids = []
        if events_to_aggregate:
            event_ids = await self._find_event_ids(group_id, cutoff_date)
            logger.info(f"Found {len(event_ids)} individual events to archive/delete")

        # Fetch full event details for archival
        if event_ids and not dry_run:
            archived_events = await self._fetch_events_for_archival(event_ids)
        else:
            archived_events = []

        # Create summaries (dry run simulates)
        summaries = await self._create_summaries(
            events_to_aggregate,
            dry_run
        )

        # Delete original events (skip on dry run)
        if event_ids and not dry_run:
            deleted_count = await self._delete_events(event_ids)
        else:
            deleted_count = 0

        # Archive to CSV
        if archived_events and not dry_run:
            archive_path = await self._archive_to_csv(archived_events, group_id)
        else:
            archive_path = ""

        processing_time_ms = (
            datetime.now(timezone.utc) - start_time
        ).total_seconds() * 1000

        metrics = AggregationMetrics(
            events_aggregated=len(events_to_aggregate), # groups aggregated
            summaries_created=len(summaries),
            events_archived=len(archived_events),
            archive_path=archive_path,
            processing_time_ms=round(processing_time_ms, 2),
            group_id=group_id or "all",
            timestamp=datetime.now(timezone.utc)
        )

        logger.info(
            f"Aggregation complete: {len(events_to_aggregate)} groups, "
            f"{metrics.events_archived} events archived, {metrics.processing_time_ms:.2f}ms"
        )

        return metrics

    async def _get_old_event_ids(
        self,
        group_id: Optional[str],
        cutoff_date: datetime
    ) -> List[str]:
        """Get event IDs for events older than cutoff date."""
        query = """
        MATCH (e:Event)
        WHERE e.timestamp < $cutoff_date
        """

        params = {"cutoff_date": cutoff_date.isoformat()}

        if group_id:
            query += " AND e.group_id = $group_id"
            params["group_id"] = group_id

        query += " RETURN e.event_id as event_id"

        results = await self._client.execute_query(query, params)
        return [r['event_id'] for r in results if r.get('event_id')]

    async def _find_event_ids(
        self,
        group_id: Optional[str],
        cutoff_date: datetime
    ) -> List[str]:
        """Find IDs of events older than cutoff."""
        query = """
        MATCH (e:Event)
        WHERE e.timestamp < $cutoff_date
        """
        
        params = {"cutoff_date": cutoff_date.isoformat()}
        
        if group_id:
            query += " AND e.group_id = $group_id"
            params["group_id"] = group_id
            
        query += " RETURN e.event_id as event_id"
        
        results = await self._client.execute_query(query, params)
        return [r['event_id'] for r in results if r.get('event_id')]

    async def _find_old_events(
        self,
        group_id: Optional[str],
        cutoff_date: datetime
    ) -> List[Dict[str, Any]]:
        """Find event summary stats older than cutoff date."""
        query = """
        MATCH (e:Event)
        WHERE e.timestamp < $cutoff_date
        """

        params = {"cutoff_date": cutoff_date.isoformat()}

        if group_id:
            query += " AND e.group_id = $group_id"
            params["group_id"] = group_id

        query += """
        WITH e.event_type as event_type, e.group_id as group_id,
             count(e) as count,
             min(e.timestamp) as first_event,
             max(e.timestamp) as last_event
        RETURN event_type, group_id, count, first_event, last_event
        ORDER BY count DESC
        """

        results = await self._client.execute_query(query, params)
        return results

    async def _fetch_events_for_archival(
        self,
        event_ids: List[str]
    ) -> List[ArchivedEvent]:
        """Fetch full event details for archival."""
        if not event_ids:
            return []

        query = """
        MATCH (e:Event)
        WHERE e.event_id IN $event_ids
        RETURN e.event_id as event_id, e.event_type as event_type,
               e.timestamp as timestamp, e.group_id as group_id,
               e.description as description
        """

        results = await self._client.execute_query(query, {"event_ids": event_ids})

        return [
            ArchivedEvent(
                event_id=r.get('event_id', ''),
                event_type=r.get('event_type', ''),
                timestamp=r.get('timestamp', ''),
                group_id=r.get('group_id', ''),
                description=r.get('description', ''),
                archived_at=datetime.now(timezone.utc).isoformat(),
                archive_reason="event_aggregation"
            )
            for r in results
        ]

    async def _create_summaries(
        self,
        event_groups: List[Dict[str, Any]],
        dry_run: bool
    ) -> List[EventSummary]:
        """Create EventSummary nodes from event groups."""
        if not event_groups:
            return []

        summaries = []
        for group in event_groups:
            summary = EventSummary(
                event_type=group.get('event_type', ''),
                group_id=group.get('group_id', ''),
                count=group.get('count', 0),
                period="archived",
                first_event=group.get('first_event', datetime.now(timezone.utc)),
                last_event=group.get('last_event', datetime.now(timezone.utc))
            )
            summaries.append(summary)

            if not dry_run:
                await self._upsert_summary(summary)

        return summaries

    async def _upsert_summary(self, summary: EventSummary) -> None:
        """Upsert an EventSummary node."""
        query = """
        MERGE (s:EventSummary {
            event_type: $event_type,
            group_id: $group_id,
            period: $period
        })
        ON CREATE SET s.count = $count,
                      s.first_event = $first_event,
                      s.last_event = $last_event,
                      s.created_at = $created_at
        ON MATCH SET s.count = s.count + $count,
                     s.last_event = $last_event
        """

        await self._client.execute_query(query, {
            "event_type": summary.event_type,
            "group_id": summary.group_id,
            "period": summary.period,
            "count": summary.count,
            "first_event": summary.first_event.isoformat() if isinstance(summary.first_event, datetime) else summary.first_event,
            "last_event": summary.last_event.isoformat() if isinstance(summary.last_event, datetime) else summary.last_event,
            "created_at": datetime.now(timezone.utc).isoformat()
        })

    async def _delete_events(self, event_ids: List[str]) -> int:
        """Delete archived events from the graph."""
        if not event_ids:
            return 0

        query = """
        MATCH (e:Event)
        WHERE e.event_id IN $event_ids
        DETACH DELETE e
        """

        await self._client.execute_query(query, {"event_ids": event_ids})
        logger.info(f"Deleted {len(event_ids)} archived events from graph")

        return len(event_ids)

    async def _archive_to_csv(
        self,
        events: List[ArchivedEvent],
        group_id: Optional[str]
    ) -> str:
        """Archive events to CSV file."""
        if not events:
            return ""

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        suffix = f"_{group_id}" if group_id else ""
        archive_name = f"archived_events{suffix}_{timestamp}.csv"
        archive_path = self._archive_dir / archive_name

        # Get field names from first event
        field_names = ['event_id', 'event_type', 'timestamp', 'group_id',
                      'description', 'archived_at', 'archive_reason']

        with open(archive_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=field_names)
            writer.writeheader()
            writer.writerows([
                {
                    'event_id': e.event_id,
                    'event_type': e.event_type,
                    'timestamp': e.timestamp,
                    'group_id': e.group_id,
                    'description': e.description[:500] if e.description else '',  # Truncate long descriptions
                    'archived_at': e.archived_at,
                    'archive_reason': e.archive_reason
                }
                for e in events
            ])

        logger.info(f"Archived {len(events)} events to {archive_path}")
        return str(archive_path)

    async def get_event_counts(
        self,
        group_id: Optional[str] = None
    ) -> Dict[str, int]:
        """Get counts of events by age category."""
        now = datetime.now(timezone.utc)
        cutoff_30d = now - timedelta(days=30)
        cutoff_90d = now - timedelta(days=90)

        query = """
        MATCH (e:Event)
        """

        params = {}
        if group_id:
            query += " WHERE e.group_id = $group_id"
            params["group_id"] = group_id

        query += """
        RETURN count(e) as total_events,
               count(CASE WHEN e.timestamp >= $cutoff_30d THEN 1 END) as recent_events,
               count(CASE WHEN e.timestamp < $cutoff_30d THEN 1 END) as old_events
        """

        params["cutoff_30d"] = cutoff_30d.isoformat()

        results = await self._client.execute_query(query, params)

        if results:
            r = results[0]
            return {
                "total_events": int(r.get('total_events', 0)),
                "recent_events": int(r.get('recent_events', 0)),
                "old_events": int(r.get('old_events', 0))
            }

        return {"total_events": 0, "recent_events": 0, "old_events": 0}


async def main():
    """Test the event aggregation service."""
    from src.bmad.core.neo4j_client import Neo4jAsyncClient

    async with Neo4jAsyncClient() as client:
        service = EventAggregationService(client)

        print("Testing event aggregation service...")

        # Get event counts
        counts = await service.get_event_counts()
        print(f"\nEvent Counts:")
        print(f"  Total: {counts['total_events']}")
        print(f"  Recent (<30d): {counts['recent_events']}")
        print(f"  Old (>=30d): {counts['old_events']}")

        # Run dry run aggregation
        metrics = await service.aggregate_events(dry_run=True)
        print(f"\nDry Run Results:")
        print(f"  Events to aggregate: {metrics.events_aggregated}")
        print(f"  Summaries to create: {metrics.summaries_created}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())