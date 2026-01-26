"""
Pattern Effectiveness Tracking Service

This module tracks and updates pattern effectiveness metrics daily.
- Recalculate success_rate from outcome history
- Update times_used counter
- Alert on patterns with success_rate < 0.6

Author: Brooks (BMAD Dev Agent)
Created: 2026-01-26
Story: 4-2-track-pattern-effectiveness-daily
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.bmad.core.neo4j_client import Neo4jAsyncClient

logger = logging.getLogger(__name__)


@dataclass
class PatternMetrics:
    """Metrics for a single pattern."""
    pattern_id: str
    pattern_name: str
    success_rate: float
    times_used: int
    group_id: str
    category: str


@dataclass
class EffectivenessReport:
    """Report from an effectiveness tracking run."""
    patterns_updated: int
    avg_success_rate: float
    patterns_with_alerts: int
    low_effectiveness_patterns: List[PatternMetrics]
    processing_time_ms: float
    group_id: str
    timestamp: datetime


@dataclass
class PatternAlert:
    """Alert for a low-effectiveness pattern."""
    pattern_id: str
    pattern_name: str
    success_rate: float
    threshold: float
    group_id: str
    timestamp: datetime
    alert_type: str = "low_effectiveness"


class PatternEffectivenessService:
    """
    Service for tracking pattern effectiveness metrics.

    Features:
    - Recalculate success_rate from outcome history
    - Update times_used counter
    - Alert on patterns with success_rate < 0.6
    - Multi-tenant isolation via group_id
    """

    # Configuration constants
    LOW_EFFECTIVENESS_THRESHOLD = 0.6

    def __init__(self, client: Neo4jAsyncClient):
        """
        Initialize the pattern effectiveness service.

        Args:
            client: Neo4j async client
        """
        self._client = client

    async def update_effectiveness(
        self,
        group_id: Optional[str] = None
    ) -> EffectivenessReport:
        """
        Update pattern effectiveness metrics.

        Args:
            group_id: Optional specific group to process (None for all)

        Returns:
            EffectivenessReport with update results
        """
        start_time = datetime.now(timezone.utc)

        logger.info("Starting pattern effectiveness update")

        # Update all patterns with outcome metrics
        update_results = await self._update_pattern_metrics(group_id)

        # Get patterns that need alerting
        low_patterns = await self._get_low_effectiveness_patterns(group_id)

        # Generate alerts
        alerts = await self._generate_alerts(low_patterns)

        processing_time_ms = (
            datetime.now(timezone.utc) - start_time
        ).total_seconds() * 1000

        avg_success = (
            sum(p.success_rate for p in update_results) / len(update_results)
            if update_results else 0.0
        )

        report = EffectivenessReport(
            patterns_updated=len(update_results),
            avg_success_rate=round(avg_success, 4),
            patterns_with_alerts=len(alerts),
            low_effectiveness_patterns=low_patterns,
            processing_time_ms=round(processing_time_ms, 2),
            group_id=group_id or "all",
            timestamp=datetime.now(timezone.utc)
        )

        logger.info(
            f"Effectiveness update complete: {report.patterns_updated} updated, "
            f"{report.patterns_with_alerts} alerts, {report.processing_time_ms:.2f}ms"
        )

        return report

    async def _update_pattern_metrics(
        self,
        group_id: Optional[str]
    ) -> List[PatternMetrics]:
        """Update success_rate and times_used for all patterns."""
        query = """
        MATCH (p:Pattern)<-[:USED_IN]-(s:Solution)-[:RESULTED_IN]->(o:Outcome)
        """

        params: Dict[str, Any] = {}

        if group_id:
            query += " WHERE p.group_id = $group_id"
            params["group_id"] = group_id

        query += """
        WITH p,
             count(o) as total,
             count(CASE WHEN o.status = 'Success' THEN 1 END) as successes
        SET p.success_rate = toFloat(successes) / total,
            p.times_used = total,
            p.last_updated = $timestamp
        RETURN p.pattern_id as pattern_id,
               p.name as pattern_name,
               p.success_rate as success_rate,
               p.times_used as times_used,
               p.group_id as group_id,
               p.category as category
        ORDER BY p.times_used DESC
        """

        params["timestamp"] = datetime.now(timezone.utc).isoformat()

        results = await self._client.execute_query(query, params)

        return [
            PatternMetrics(
                pattern_id=r.get('pattern_id', ''),
                pattern_name=r.get('pattern_name', ''),
                success_rate=float(r.get('success_rate', 0.0)),
                times_used=int(r.get('times_used', 0)),
                group_id=r.get('group_id', ''),
                category=r.get('category', '')
            )
            for r in results
        ]

    async def _get_low_effectiveness_patterns(
        self,
        group_id: Optional[str]
    ) -> List[PatternMetrics]:
        """Get patterns with success_rate < threshold."""
        query = """
        MATCH (p:Pattern)
        WHERE p.success_rate < $threshold
        """

        params: Dict[str, Any] = {"threshold": self.LOW_EFFECTIVENESS_THRESHOLD}

        if group_id:
            query += " AND p.group_id = $group_id"
            params["group_id"] = group_id

        query += """
        RETURN p.pattern_id as pattern_id,
               p.name as pattern_name,
               p.success_rate as success_rate,
               p.times_used as times_used,
               p.group_id as group_id,
               p.category as category
        ORDER BY p.success_rate ASC
        """

        results = await self._client.execute_query(query, params)

        return [
            PatternMetrics(
                pattern_id=r.get('pattern_id', ''),
                pattern_name=r.get('pattern_name', ''),
                success_rate=float(r.get('success_rate', 0.0)),
                times_used=int(r.get('times_used', 0)),
                group_id=r.get('group_id', ''),
                category=r.get('category', '')
            )
            for r in results
        ]

    async def _generate_alerts(
        self,
        low_patterns: List[PatternMetrics]
    ) -> List[PatternAlert]:
        """Generate alerts for low effectiveness patterns."""
        alerts = []

        for pattern in low_patterns:
            alert = PatternAlert(
                pattern_id=pattern.pattern_id,
                pattern_name=pattern.pattern_name,
                success_rate=pattern.success_rate,
                threshold=self.LOW_EFFECTIVENESS_THRESHOLD,
                group_id=pattern.group_id,
                timestamp=datetime.now(timezone.utc)
            )
            alerts.append(alert)

            # Log the alert
            logger.warning(
                f"LOW EFFECTIVENESS ALERT: Pattern '{pattern.pattern_name}' "
                f"(ID: {pattern.pattern_id}) has success_rate {pattern.success_rate:.2%} "
                f"below threshold {self.LOW_EFFECTIVENESS_THRESHOLD:.0%}"
            )

        if alerts:
            logger.info(f"Generated {len(alerts)} low effectiveness alerts")

        return alerts

    async def get_pattern_metrics(
        self,
        pattern_id: str
    ) -> Optional[PatternMetrics]:
        """Get current metrics for a specific pattern."""
        query = """
        MATCH (p:Pattern {pattern_id: $pattern_id})
        OPTIONAL MATCH (p)<-[:USED_IN]-(s:Solution)-[:RESULTED_IN]->(o:Outcome)
        WITH p, count(o) as total,
             count(CASE WHEN o.status = 'Success' THEN 1 END) as successes
        RETURN p.pattern_id as pattern_id,
               p.name as pattern_name,
               p.success_rate as success_rate,
               p.times_used as times_used,
               p.group_id as group_id,
               p.category as category,
               toFloat(successes) / total as calculated_rate
        """

        results = await self._client.execute_query(query, {"pattern_id": pattern_id})

        if not results:
            return None

        r = results[0]
        return PatternMetrics(
            pattern_id=r.get('pattern_id', ''),
            pattern_name=r.get('pattern_name', ''),
            success_rate=float(r.get('calculated_rate', r.get('success_rate', 0.0))),
            times_used=int(r.get('times_used', 0)),
            group_id=r.get('group_id', ''),
            category=r.get('category', '')
        )

    async def get_effectiveness_summary(
        self,
        group_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get a summary of pattern effectiveness metrics."""
        query = """
        MATCH (p:Pattern)
        """

        params: Dict[str, Any] = {}

        if group_id:
            query += " WHERE p.group_id = $group_id"
            params["group_id"] = group_id

        query += """
        RETURN count(p) as total_patterns,
               avg(p.success_rate) as avg_success_rate,
               min(p.success_rate) as min_success_rate,
               max(p.success_rate) as max_success_rate,
               sum(p.times_used) as total_uses
        """

        results = await self._client.execute_query(query, params)

        if not results:
            return {
                "total_patterns": 0,
                "avg_success_rate": 0.0,
                "min_success_rate": 0.0,
                "max_success_rate": 0.0,
                "total_uses": 0
            }

        r = results[0]
        return {
            "total_patterns": int(r.get('total_patterns', 0)),
            "avg_success_rate": round(float(r.get('avg_success_rate', 0.0)), 4),
            "min_success_rate": round(float(r.get('min_success_rate', 0.0)), 4),
            "max_success_rate": round(float(r.get('max_success_rate', 0.0)), 4),
            "total_uses": int(r.get('total_uses', 0))
        }


async def main():
    """Test the pattern effectiveness service."""
    from src.bmad.core.neo4j_client import Neo4jAsyncClient

    async with Neo4jAsyncClient() as client:
        service = PatternEffectivenessService(client)

        print("Testing pattern effectiveness service...")

        # Get effectiveness summary
        summary = await service.get_effectiveness_summary()
        print(f"\nEffectiveness Summary:")
        print(f"  Total patterns: {summary['total_patterns']}")
        print(f"  Avg success rate: {summary['avg_success_rate']:.2%}")
        print(f"  Total uses: {summary['total_uses']}")

        # Run effectiveness update
        report = await service.update_effectiveness()
        print(f"\nUpdate Report:")
        print(f"  Patterns updated: {report.patterns_updated}")
        print(f"  Avg success rate: {report.avg_success_rate:.2%}")
        print(f"  Alerts: {report.patterns_with_alerts}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())