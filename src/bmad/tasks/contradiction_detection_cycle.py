"""
Contradiction Detection Cycle Task

This module provides scheduled daily task for pattern contradiction detection.
- Runs daily at 2:15 AM
- Detects conflicting patterns
- Creates Alert nodes for human review

Author: Brooks (BMAD Dev Agent)
Created: 2026-01-26
Story: 4-5-escalate-pattern-contradictions-for-review
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.bmad.core.neo4j_client import Neo4jAsyncClient
from src.bmad.services.contradiction_detector import (
    ContradictionDetectorService,
    ContradictionDetectionResult
)

logger = logging.getLogger(__name__)


class ContradictionDetectionCycle:
    """
    Manages the daily contradiction detection cycle.

    Features:
    - Daily scheduled execution via APScheduler
    - Pattern contradiction detection
    - Alert creation for human review
    - Performance monitoring
    """

    def __init__(self):
        """Initialize the contradiction detection cycle task."""
        self.scheduler = AsyncIOScheduler()
        self._client: Optional[Neo4jAsyncClient] = None
        self._service: Optional[ContradictionDetectorService] = None

    async def initialize(self) -> None:
        """Initialize the Neo4j client and service."""
        self._client = Neo4jAsyncClient()
        await self._client.initialize()
        self._service = ContradictionDetectorService(self._client)
        logger.info("ContradictionDetectionCycle initialized")

    async def shutdown(self) -> None:
        """Shutdown the scheduler and close connections."""
        if self.scheduler.running:
            self.scheduler.shutdown()

        if self._client:
            await self._client.close()

        logger.info("ContradictionDetectionCycle shutdown")

    def start(self) -> None:
        """
        Start the scheduled daily contradiction detection.

        Scheduled to run daily at 2:15 AM (after insight generation).
        """
        # Schedule daily run at 2:15 AM (after 2 AM insight generation)
        trigger = CronTrigger(hour=2, minute=15)
        self.scheduler.add_job(
            self.run_cycle,
            trigger=trigger,
            id='contradiction_detection_cycle',
            name='Daily Pattern Contradiction Detection',
            replace_existing=True
        )

        self.scheduler.start()
        logger.info("Contradiction detection cycle scheduled (runs daily at 2:15 AM)")

    async def run_cycle(
        self,
        applies_to: Optional[str] = None
    ) -> dict:
        """
        Run the full contradiction detection cycle.

        Args:
            applies_to: Optional filter for specific domain

        Returns:
            Dict with detection results
        """
        if not self._service:
            await self.initialize()

        logger.info("Starting daily contradiction detection cycle")

        try:
            # Run detection
            result = await self._service.run_detection_cycle(applies_to)

            # Log results
            if result.contradictions_found > 0:
                logger.warning(
                    f"Detection cycle found {result.contradictions_found} contradictions, "
                    f"created {result.alerts_created} alerts"
                )
            else:
                logger.info(
                    f"Detection cycle complete: no contradictions detected, "
                    f"{result.existing_alerts} pending alerts"
                )

            return {
                "contradictions_found": result.contradictions_found,
                "alerts_created": result.alerts_created,
                "existing_alerts": result.existing_alerts,
                "processing_time_ms": result.processing_time_ms,
                "timestamp": result.timestamp.isoformat()
            }

        except Exception as e:
            logger.error(f"Contradiction detection cycle error: {e}")
            await self._notify_error(str(e))
            raise

    async def run_detection_only(self) -> ContradictionDetectionResult:
        """
        Run detection without scheduling (manual mode).

        Returns:
            ContradictionDetectionResult with findings
        """
        if not self._service:
            await self.initialize()

        logger.info("Running manual contradiction detection")
        return await self._service.run_detection_cycle()

    async def get_pending_alerts(self, limit: int = 50) -> list:
        """
        Get pending alerts for review.

        Args:
            limit: Maximum number of alerts to return

        Returns:
            List of pending alerts
        """
        if not self._service:
            await self.initialize()

        return await self._service.get_pending_alerts(limit)

    async def resolve_alert(
        self,
        alert_id: str,
        resolution_notes: str,
        resolved_by: str = "manual"
    ) -> bool:
        """
        Resolve a pending alert.

        Args:
            alert_id: ID of the alert to resolve
            resolution_notes: Resolution notes
            resolved_by: Who resolved the alert

        Returns:
            True if resolved successfully
        """
        if not self._service:
            await self.initialize()

        return await self._service.resolve_alert(alert_id, resolution_notes, resolved_by)

    async def _notify_error(self, error_message: str) -> None:
        """Send notification on error."""
        logger.error(f"ERROR NOTIFICATION: {error_message}")

        # In production, this would send to Slack/email/PagerDuty
        logger.critical(
            f"CONTRADICTION DETECTION FAILURE: {error_message}\n"
            f"Manual intervention may be required"
        )


# Global task instance
_contradiction_cycle: Optional[ContradictionDetectionCycle] = None


def get_contradiction_detection_cycle() -> ContradictionDetectionCycle:
    """Get the global contradiction detection cycle task instance."""
    global _contradiction_cycle
    if _contradiction_cycle is None:
        _contradiction_cycle = ContradictionDetectionCycle()
    return _contradiction_cycle


async def main():
    """Run manual contradiction detection for testing."""
    from dotenv import load_dotenv
    load_dotenv()

    cycle = get_contradiction_detection_cycle()
    result = await cycle.run_detection_only()

    print(f"\nContradiction Detection Results:")
    print(f"  Contradictions found: {result.contradictions_found}")
    print(f"  Alerts created: {result.alerts_created}")
    print(f"  Existing pending: {result.existing_alerts}")
    print(f"  Processing time: {result.processing_time_ms:.2f}ms")

    # Show pending alerts
    alerts = await cycle.get_pending_alerts()
    print(f"\nPending Alerts ({len(alerts)}):")
    for alert in alerts[:5]:
        print(f"  - {alert['alert_id']}: {alert['conflict_reason']}")

    await cycle.shutdown()


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) > 1 and sys.argv[1] == '--schedule':
        cycle = get_contradiction_detection_cycle()
        cycle.start()

        try:
            asyncio.get_event_loop().run_forever()
        except KeyboardInterrupt:
            pass
    else:
        asyncio.run(main())