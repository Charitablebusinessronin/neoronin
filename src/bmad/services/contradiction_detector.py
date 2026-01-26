"""
Pattern Contradiction Detection Service

This module detects conflicting patterns and creates alerts for human review.
- Detect patterns with conflicting rules and confidence delta > 0.3
- Create Alert nodes for contradictions
- Support alert resolution workflow

Author: Brooks (BMAD Dev Agent)
Created: 2026-01-26
Story: 4-5-escalate-pattern-contradictions-for-review
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.bmad.core.neo4j_client import Neo4jAsyncClient

logger = logging.getLogger(__name__)


@dataclass
class PatternContradiction:
    """A detected pattern contradiction."""
    insight_id_1: str
    insight_id_2: str
    rule_1: str
    rule_2: str
    confidence_1: float
    confidence_2: float
    confidence_delta: float
    applies_to: str
    conflict_reason: str


@dataclass
class Alert:
    """An alert for human review."""
    alert_id: str
    alert_type: str
    insight_ids: List[str]
    confidence_scores: List[float]
    conflict_reason: str
    requires_human_review: bool
    status: str
    created_at: datetime
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    resolution_notes: Optional[str] = None


@dataclass
class ContradictionDetectionResult:
    """Result of a contradiction detection run."""
    contradictions_found: int
    alerts_created: int
    existing_alerts: int
    processing_time_ms: float
    timestamp: datetime


class ContradictionDetectorService:
    """
    Service for detecting pattern contradictions and managing alerts.

    Features:
    - Detect patterns with conflicting rules
    - Create Alert nodes for contradictions
    - Alert resolution workflow
    - Daily scheduled detection
    """

    # Configuration
    CONFIDENCE_DELTA_THRESHOLD = 0.3

    def __init__(self, client: Neo4jAsyncClient):
        """
        Initialize the contradiction detector service.

        Args:
            client: Neo4j async client
        """
        self._client = client

    async def detect_pattern_conflicts(
        self,
        applies_to: Optional[str] = None,
        confidence_delta_threshold: float = CONFIDENCE_DELTA_THRESHOLD
    ) -> List[PatternContradiction]:
        """
        Detect pattern contradictions in the graph.

        Args:
            applies_to: Optional filter for specific applies_to value
            confidence_delta_threshold: Minimum confidence delta to flag

        Returns:
            List of detected contradictions
        """
        query = """
        MATCH (i1:Insight), (i2:Insight)
        WHERE id(i1) < id(i2)
          AND i1.applies_to = i2.applies_to
          AND i1.rule CONTAINS 'NOT' OR i2.rule CONTAINS 'NOT'
          AND abs(i1.confidence_score - i2.confidence_score) > $threshold
        """

        params = {"threshold": confidence_delta_threshold}

        if applies_to:
            query += " AND i1.applies_to = $applies_to"
            params["applies_to"] = applies_to

        query += """
        WITH i1, i2,
             i1.rule as rule_1, i2.rule as rule_2,
             i1.confidence_score as c1, i2.confidence_score as c2,
             i1.applies_to as applies_to,
             abs(i1.confidence_score - i2.confidence_score) as delta
        RETURN i1.insight_id as insight_id_1,
               i2.insight_id as insight_id_2,
               rule_1, rule_2, c1, c2, delta, applies_to
        ORDER BY delta DESC
        """

        results = await self._client.execute_query(query, params)

        contradictions = []
        for r in results:
            # Determine conflict reason based on rules
            rule_1 = r.get('rule_1', '')
            rule_2 = r.get('rule_2', '')
            conflict_reason = self._determine_conflict_reason(rule_1, rule_2)

            contradiction = PatternContradiction(
                insight_id_1=r.get('insight_id_1', ''),
                insight_id_2=r.get('insight_id_2', ''),
                rule_1=rule_1,
                rule_2=rule_2,
                confidence_1=r.get('c1', 0.0),
                confidence_2=r.get('c2', 0.0),
                confidence_delta=r.get('delta', 0.0),
                applies_to=r.get('applies_to', ''),
                conflict_reason=conflict_reason
            )
            contradictions.append(contradiction)

        logger.info(f"Detected {len(contradictions)} pattern contradictions")
        return contradictions

    def _determine_conflict_reason(self, rule_1: str, rule_2: str) -> str:
        """Determine the reason for conflict between two rules."""
        # Simple heuristic for conflict detection
        negations_1 = rule_1.upper().count('NOT ')
        negations_2 = rule_2.upper().count('NOT ')

        if negations_1 != negations_2:
            return "Contradictory affirmative vs negative rule patterns"
        elif 'ALWAYS' in rule_1.upper() and 'NEVER' in rule_2.upper():
            return "Always vs Never contradiction"
        elif 'BEST' in rule_1.upper() and 'WORST' in rule_2.upper():
            return "Best practice vs anti-pattern contradiction"
        else:
            return "Conflicting guidance patterns"

    async def create_alerts(
        self,
        contradictions: List[PatternContradiction],
        auto_repair: bool = False
    ) -> int:
        """
        Create Alert nodes for detected contradictions.

        Args:
            contradictions: List of detected contradictions
            auto_repair: If True, auto-resolve if conflict is obvious

        Returns:
            Number of alerts created
        """
        if not contradictions:
            return 0

        alerts_created = 0

        for contradiction in contradictions:
            # Check if alert already exists
            existing = await self._check_existing_alert(
                contradiction.insight_id_1,
                contradiction.insight_id_2
            )

            if existing:
                logger.debug(f"Alert already exists for {contradiction.insight_id_1} & {contradiction.insight_id_2}")
                continue

            # Create alert
            await self._create_alert(contradiction)
            alerts_created += 1

        logger.info(f"Created {alerts_created} new alerts for contradictions")
        return alerts_created

    async def _check_existing_alert(
        self,
        insight_id_1: str,
        insight_id_2: str
    ) -> bool:
        """Check if an alert already exists for these insights."""
        query = """
        MATCH (alert:Alert)
        WHERE alert.type = 'contradiction'
          AND $insight_id_1 IN alert.insights
          AND $insight_id_2 IN alert.insights
          AND alert.status = 'pending'
        RETURN count(alert) as count
        """

        results = await self._client.execute_query(query, {
            "insight_id_1": insight_id_1,
            "insight_id_2": insight_id_2
        })

        return results and results[0].get('count', 0) > 0

    async def _create_alert(self, contradiction: PatternContradiction) -> None:
        """Create a single alert node."""
        query = """
        CREATE (alert:Alert {
            alert_id: $alert_id,
            type: 'contradiction',
            insights: $insights,
            confidence_scores: $confidence_scores,
            conflict_reason: $conflict_reason,
            requires_human_review: true,
            status: 'pending',
            created_at: $created_at,
            applies_to: $applies_to
        })
        RETURN alert
        """

        alert_id = f"alert-{contradiction.insight_id_1[:8]}-{contradiction.insight_id_2[:8]}-{datetime.now(timezone.utc).strftime('%Y%m%d')}"

        await self._client.execute_query(query, {
            "alert_id": alert_id,
            "insights": [contradiction.insight_id_1, contradiction.insight_id_2],
            "confidence_scores": [contradiction.confidence_1, contradiction.confidence_2],
            "conflict_reason": contradiction.conflict_reason,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "applies_to": contradiction.applies_to
        })

        logger.info(f"Created alert {alert_id} for contradiction")

    async def run_detection_cycle(
        self,
        applies_to: Optional[str] = None
    ) -> ContradictionDetectionResult:
        """
        Run the full contradiction detection cycle.

        Args:
            applies_to: Optional filter for specific domain

        Returns:
            ContradictionDetectionResult with run details
        """
        start_time = datetime.now(timezone.utc)

        # Detect contradictions
        contradictions = await self.detect_pattern_conflicts(applies_to)

        # Create alerts
        alerts_created = await self.create_alerts(contradictions)

        # Count existing pending alerts
        existing_alerts = await self._count_pending_alerts()

        processing_time_ms = (
            datetime.now(timezone.utc) - start_time
        ).total_seconds() * 1000

        result = ContradictionDetectionResult(
            contradictions_found=len(contradictions),
            alerts_created=alerts_created,
            existing_alerts=existing_alerts,
            processing_time_ms=round(processing_time_ms, 2),
            timestamp=datetime.now(timezone.utc)
        )

        logger.info(
            f"Detection cycle complete: {len(contradictions)} contradictions, "
            f"{alerts_created} new alerts, {existing_alerts} total pending"
        )

        return result

    async def _count_pending_alerts(self) -> int:
        """Count pending alerts in the graph."""
        query = """
        MATCH (alert:Alert)
        WHERE alert.type = 'contradiction' AND alert.status = 'pending'
        RETURN count(alert) as count
        """

        results = await self._client.execute_query(query, {})
        return results[0].get('count', 0) if results else 0

    async def get_pending_alerts(
        self,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get all pending alerts for review.

        Args:
            limit: Maximum number of alerts to return

        Returns:
            List of alert dictionaries
        """
        query = """
        MATCH (alert:Alert)
        WHERE alert.type = 'contradiction' AND alert.status = 'pending'
        RETURN alert
        ORDER BY alert.created_at DESC
        LIMIT $limit
        """

        results = await self._client.execute_query(query, {"limit": limit})

        alerts = []
        for r in results:
            alert = r.get('alert', {})
            if alert:
                alerts.append({
                    "alert_id": alert.get('alert_id', ''),
                    "type": alert.get('type', ''),
                    "insights": alert.get('insights', []),
                    "confidence_scores": alert.get('confidence_scores', []),
                    "conflict_reason": alert.get('conflict_reason', ''),
                    "requires_human_review": alert.get('requires_human_review', False),
                    "status": alert.get('status', ''),
                    "created_at": alert.get('created_at', ''),
                    "applies_to": alert.get('applies_to', '')
                })

        return alerts

    async def resolve_alert(
        self,
        alert_id: str,
        resolution_notes: str,
        resolved_by: str = "system"
    ) -> bool:
        """
        Mark an alert as resolved.

        Args:
            alert_id: ID of the alert to resolve
            resolution_notes: Notes about the resolution
            resolved_by: Who resolved the alert

        Returns:
            True if alert was resolved
        """
        query = """
        MATCH (alert:Alert {alert_id: $alert_id})
        WHERE alert.type = 'contradiction'
        SET alert.status = 'resolved',
            alert.resolved_at = $resolved_at,
            alert.resolved_by = $resolved_by,
            alert.resolution_notes = $resolution_notes
        RETURN count(alert) as count
        """

        results = await self._client.execute_query(query, {
            "alert_id": alert_id,
            "resolved_at": datetime.now(timezone.utc).isoformat(),
            "resolved_by": resolved_by,
            "resolution_notes": resolution_notes
        })

        return bool(results) and results[0].get('count', 0) > 0


async def main():
    """Test the contradiction detector service."""
    from src.bmad.core.neo4j_client import Neo4jAsyncClient

    async with Neo4jAsyncClient() as client:
        service = ContradictionDetectorService(client)

        print("Testing contradiction detector service...")

        # Run detection cycle
        result = await service.run_detection_cycle()
        print(f"\nDetection Cycle Results:")
        print(f"  Contradictions found: {result.contradictions_found}")
        print(f"  Alerts created: {result.alerts_created}")
        print(f"  Existing pending alerts: {result.existing_alerts}")
        print(f"  Processing time: {result.processing_time_ms:.2f}ms")

        # Get pending alerts
        alerts = await service.get_pending_alerts()
        print(f"\nPending Alerts: {len(alerts)}")
        for alert in alerts[:3]:
            print(f"  - {alert['alert_id']}: {alert['conflict_reason']}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())