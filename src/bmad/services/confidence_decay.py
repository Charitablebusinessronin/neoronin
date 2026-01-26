"""
Confidence Decay Service

This module applies temporal decay to stale insights.
- Insights not applied in 90+ days have confidence reduced by 10%
- Insights with confidence < 0.1 are archived to cold storage
- Batch processing with metrics tracking

Author: Brooks (BMAD Dev Agent)
Created: 2026-01-26
Story: 4-1-apply-temporal-decay-to-stale-insights
"""

import csv
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.bmad.core.neo4j_client import Neo4jAsyncClient

logger = logging.getLogger(__name__)


@dataclass
class DecayMetrics:
    """Metrics from a decay operation."""
    insights_decayed: int
    avg_new_confidence: float
    insights_archived: int
    archived_to: str
    processing_time_ms: float
    group_id: str
    timestamp: datetime


@dataclass
class ArchivedInsight:
    """An insight that has been archived."""
    insight_id: str
    rule: str
    category: str
    confidence_score: float
    group_id: str
    archived_at: datetime
    original_created_at: datetime
    last_applied: Optional[datetime]
    archived_reason: str


class ConfidenceDecayService:
    """
    Service for applying temporal decay to stale insights.

    Features:
    - Apply 10% decay to insights inactive for 90+ days
    - Archive insights with confidence < 0.1 to CSV
    - Multi-tenant isolation via group_id
    - Metrics collection for monitoring
    """

    # Configuration constants
    STALE_DAYS = 90
    DECAY_RATE = 0.10  # 10% decay
    ARCHIVE_THRESHOLD = 0.1

    def __init__(
        self,
        client: Neo4jAsyncClient,
        archive_dir: Optional[str] = None
    ):
        """
        Initialize the confidence decay service.

        Args:
            client: Neo4j async client
            archive_dir: Optional custom archive directory
        """
        self._client = client
        default_dir = os.environ.get(
            'CONFIDENCE_DECAY_ARCHIVE_DIR',
            '/home/ronin/development/Neo4j/data/archived_insights'
        )
        self._archive_dir = Path(archive_dir or default_dir)
        self._archive_dir.mkdir(parents=True, exist_ok=True)

    async def apply_decay(
        self,
        group_id: Optional[str] = None,
        stale_days: int = STALE_DAYS,
        dry_run: bool = False
    ) -> DecayMetrics:
        """
        Apply confidence decay to stale insights.

        Args:
            group_id: Optional specific group to process (None for all)
            stale_days: Days of inactivity before decay applies
            dry_run: If True, simulate without making changes

        Returns:
            DecayMetrics with operation results
        """
        start_time = datetime.now(timezone.utc)

        logger.info(f"Starting confidence decay (dry_run={dry_run})")

        # Find insights requiring decay
        stale_insights = await self._find_stale_insights(group_id, stale_days)

        insights_decayed = 0
        confidence_sum = 0.0
        decayed_ids = []

        for insight in stale_insights:
            if dry_run:
                new_confidence = insight['confidence_score'] * (1 - self.DECAY_RATE)
                confidence_sum += new_confidence
                insights_decayed += 1
                decayed_ids.append(insight['insight_id'])
            else:
                result = await self._decay_insight(insight)
                if result:
                    insights_decayed += 1
                    confidence_sum += result
                    decayed_ids.append(insight['insight_id'])

        # Archive low-confidence insights (skip during dry run)
        if dry_run:
            archived_count = 0
            archive_path = None
        else:
            archived_count, archive_path = await self._archive_low_confidence_insights(
                group_id, decayed_ids
            )

        processing_time_ms = (
            datetime.now(timezone.utc) - start_time
        ).total_seconds() * 1000

        avg_confidence = (
            confidence_sum / insights_decayed if insights_decayed > 0 else 0.0
        )

        metrics = DecayMetrics(
            insights_decayed=insights_decayed,
            avg_new_confidence=round(avg_confidence, 4),
            insights_archived=archived_count,
            archived_to=str(archive_path) if archive_path else "",
            processing_time_ms=round(processing_time_ms, 2),
            group_id=group_id or "all",
            timestamp=datetime.now(timezone.utc)
        )

        logger.info(
            f"Decay complete: {metrics.insights_decayed} decayed, "
            f"{metrics.insights_archived} archived, "
            f"{metrics.processing_time_ms:.2f}ms"
        )

        return metrics

    async def _find_stale_insights(
        self,
        group_id: Optional[str],
        stale_days: int
    ) -> List[Dict[str, Any]]:
        """Find insights that need decay applied."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=stale_days)

        if group_id:
            query = """
            MATCH (i:Insight)
            WHERE i.group_id = $group_id
              AND (i.last_applied IS NULL OR i.last_applied < $cutoff_date)
              AND i.confidence_score > 0.0
            RETURN i.insight_id as insight_id, i.rule as rule,
                   i.category as category, i.confidence_score as confidence_score,
                   i.group_id as group_id, i.created_at as created_at,
                   i.last_applied as last_applied
            """
            params = {"group_id": group_id, "cutoff_date": cutoff_date}
        else:
            query = """
            MATCH (i:Insight)
            WHERE (i.last_applied IS NULL OR i.last_applied < $cutoff_date)
              AND i.confidence_score > 0.0
            RETURN i.insight_id as insight_id, i.rule as rule,
                   i.category as category, i.confidence_score as confidence_score,
                   i.group_id as group_id, i.created_at as created_at,
                   i.last_applied as last_applied
            """
            params = {"cutoff_date": cutoff_date}

        results = await self._client.execute_query(query, params)
        return results

    async def _decay_insight(self, insight: Dict[str, Any]) -> Optional[float]:
        """Apply decay to a single insight."""
        current_confidence = insight['confidence_score']
        new_confidence = current_confidence * (1 - self.DECAY_RATE)

        query = """
        MATCH (i:Insight {insight_id: $insight_id})
        SET i.confidence_score = $new_confidence,
            i.last_decay_applied = $timestamp
        RETURN i.confidence_score as new_confidence
        """

        result = await self._client.execute_query(query, {
            "insight_id": insight['insight_id'],
            "new_confidence": round(new_confidence, 4),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        if result:
            return float(result[0].get('new_confidence', new_confidence))
        return None

    async def _archive_low_confidence_insights(
        self,
        group_id: Optional[str],
        exclude_ids: List[str]
    ) -> tuple[int, Optional[Path]]:
        """
        Archive insights with confidence < 0.1 to CSV.

        Returns:
            Tuple of (archived_count, archive_path)
        """
        query = """
        MATCH (i:Insight)
        WHERE i.confidence_score < $threshold
        """

        params = {"threshold": self.ARCHIVE_THRESHOLD}

        if group_id:
            query += " AND i.group_id = $group_id"
            params["group_id"] = group_id

        if exclude_ids:
            query += " AND NOT i.insight_id IN $exclude_ids"
            params["exclude_ids"] = exclude_ids

        query += """
        RETURN i.insight_id as insight_id, i.rule as rule,
               i.category as category, i.confidence_score as confidence_score,
               i.group_id as group_id, i.created_at as created_at,
               i.last_applied as last_applied
        """

        results = await self._client.execute_query(query, params)

        if not results:
            return 0, None

        # Create archive file
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        archive_name = f"archived_insights_{timestamp}.csv"
        archive_path = self._archive_dir / archive_name

        archived_count = 0
        archived_records = []

        for record in results:
            archived_record = {
                'insight_id': record.get('insight_id'),
                'rule': record.get('rule', ''),
                'category': record.get('category', ''),
                'confidence_score': record.get('confidence_score'),
                'group_id': record.get('group_id'),
                'original_created_at': record.get('created_at'),
                'last_applied': record.get('last_applied'),
                'archived_at': datetime.now(timezone.utc).isoformat(),
                'archived_reason': f"confidence_below_{self.ARCHIVE_THRESHOLD}"
            }
            archived_records.append(archived_record)
            archived_count += 1

        # Write to CSV
        if archived_records:
            with open(archive_path, 'w', newline='', encoding='utf-8') as f:
                if archived_records:
                    writer = csv.DictWriter(f, fieldnames=archived_records[0].keys())
                    writer.writeheader()
                    writer.writerows(archived_records)

            logger.info(f"Archived {archived_count} insights to {archive_path}")

            # Delete archived insights from graph
            ids_to_delete = [r['insight_id'] for r in archived_records]
            await self._delete_insights(ids_to_delete)

        return archived_count, archive_path

    async def _delete_insights(self, insight_ids: List[str]) -> int:
        """Delete archived insights from the graph."""
        if not insight_ids:
            return 0

        query = """
        MATCH (i:Insight)
        WHERE i.insight_id IN $ids
        DETACH DELETE i
        """

        result = await self._client.execute_query(query, {"ids": insight_ids})
        logger.info(f"Deleted {len(insight_ids)} archived insights from graph")

        return len(insight_ids)

    async def get_stale_insights_count(self, group_id: Optional[str] = None) -> Dict[str, int]:
        """Get count of stale insights by group."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.STALE_DAYS)

        if group_id:
            query = """
            MATCH (i:Insight)
            WHERE i.group_id = $group_id
              AND (i.last_applied IS NULL OR i.last_applied < $cutoff_date)
            RETURN count(i) as count
            """
            params = {"group_id": group_id, "cutoff_date": cutoff_date}
        else:
            query = """
            MATCH (i:Insight)
            WHERE (i.last_applied IS NULL OR i.last_applied < $cutoff_date)
            RETURN i.group_id as group_id, count(i) as count
            """
            params = {"cutoff_date": cutoff_date}

        results = await self._client.execute_query(query, params)

        if group_id:
            return {"total": results[0].get('count', 0) if results else 0}
        else:
            return {
                r.get('group_id', 'unknown'): r.get('count', 0)
                for r in results
            }


async def main():
    """Test the confidence decay service."""
    from src.bmad.core.neo4j_client import Neo4jAsyncClient

    async with Neo4jAsyncClient() as client:
        service = ConfidenceDecayService(client)

        print("Testing confidence decay service...")

        # Get stale insights count
        counts = await service.get_stale_insights_count()
        print(f"\nStale insights by group: {counts}")

        # Run dry run
        metrics = await service.apply_decay(dry_run=True)
        print(f"\nDry run results:")
        print(f"  Insights to decay: {metrics.insights_decayed}")
        print(f"  Avg new confidence: {metrics.avg_new_confidence:.4f}")
        print(f"  Insights to archive: {metrics.insights_archived}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())