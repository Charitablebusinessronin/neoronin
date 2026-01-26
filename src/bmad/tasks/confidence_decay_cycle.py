"""
Confidence Decay Cycle Task

This module provides scheduled monthly task for confidence decay.
- Runs on 1st of each month at 2:00 AM
- Applies 10% decay to stale insights
- Archives low-confidence insights to cold storage
- Logs metrics for monitoring

Author: Brooks (BMAD Dev Agent)
Created: 2026-01-26
Story: 4-1-apply-temporal-decay-to-stale-insights
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.bmad.core.neo4j_client import Neo4jAsyncClient
from src.bmad.services.confidence_decay import (
    ConfidenceDecayService,
    DecayMetrics
)

logger = logging.getLogger(__name__)


class ConfidenceDecayCycle:
    """
    Manages the monthly confidence decay cycle.

    Features:
    - Monthly scheduled execution via APScheduler
    - Multi-group processing
    - Metrics collection and logging
    - Error handling and notifications
    """

    def __init__(self):
        """Initialize the confidence decay cycle task."""
        self.scheduler = AsyncIOScheduler()
        self._client: Optional[Neo4jAsyncClient] = None
        self._service: Optional[ConfidenceDecayService] = None

    async def initialize(self) -> None:
        """Initialize the Neo4j client and service."""
        self._client = Neo4jAsyncClient()
        await self._client.initialize()
        self._service = ConfidenceDecayService(self._client)
        logger.info("ConfidenceDecayCycle initialized")

    async def shutdown(self) -> None:
        """Shutdown the scheduler and close connections."""
        if self.scheduler.running:
            self.scheduler.shutdown()

        if self._client:
            await self._client.close()

        logger.info("ConfidenceDecayCycle shutdown")

    def start(self) -> None:
        """
        Start the scheduled monthly decay cycle.

        Scheduled to run on the 1st of each month at 2:00 AM.
        """
        # Schedule monthly run on 1st of month at 2 AM
        trigger = CronTrigger(day=1, hour=2, minute=0)
        self.scheduler.add_job(
            self.run_cycle,
            trigger=trigger,
            id='confidence_decay_cycle',
            name='Monthly Confidence Decay',
            replace_existing=True
        )

        self.scheduler.start()
        logger.info("Confidence decay cycle scheduled (runs 1st of month at 2 AM)")

    async def run_cycle(self, group_id: Optional[str] = None) -> DecayMetrics:
        """
        Run the full confidence decay cycle.

        Args:
            group_id: Optional specific group to process (None for all)

        Returns:
            DecayMetrics with operation results
        """
        if not self._service:
            await self.initialize()

        logger.info(f"Starting confidence decay cycle for group: {group_id or 'all'}")

        try:
            # Get stale insights count before decay
            stale_counts = await self._service.get_stale_insights_count(group_id)
            logger.info(f"Stale insights before decay: {stale_counts}")

            # Apply decay
            metrics = await self._service.apply_decay(
                group_id=group_id,
                stale_days=90,
                dry_run=False
            )

            # Log results
            logger.info(
                f"Decay cycle complete: "
                f"{metrics.insights_decayed} insights decayed, "
                f"avg confidence {metrics.avg_new_confidence:.4f}, "
                f"{metrics.insights_archived} archived"
            )

            return metrics

        except Exception as e:
            logger.error(f"Decay cycle error: {e}")
            await self._notify_error(str(e))
            raise

    async def run_manual(
        self,
        group_id: Optional[str] = None,
        dry_run: bool = True
    ) -> DecayMetrics:
        """
        Run decay manually (not scheduled).

        Args:
            group_id: Specific group to process (None for all)
            dry_run: If True, simulate without making changes

        Returns:
            DecayMetrics with processing summary
        """
        if not self._service:
            await self.initialize()

        logger.info(f"Manual confidence decay for group: {group_id or 'all'}")

        return await self._service.apply_decay(
            group_id=group_id,
            stale_days=90,
            dry_run=dry_run
        )

    async def _notify_error(self, error_message: str) -> None:
        """Send notification on error."""
        # Log to audit system (simplified)
        logger.error(f"ERROR NOTIFICATION: {error_message}")

        # In production, this would send to Slack/email/PagerDuty
        # For now, just log prominently
        logger.critical(
            f"CONFIDENCE DECAY FAILURE: {error_message}\n"
            f"Manual intervention may be required"
        )


# Global task instance
_decay_cycle: Optional[ConfidenceDecayCycle] = None


def get_decay_cycle() -> ConfidenceDecayCycle:
    """Get the global decay cycle task instance."""
    global _decay_cycle
    if _decay_cycle is None:
        _decay_cycle = ConfidenceDecayCycle()
    return _decay_cycle


async def main():
    """Run manual confidence decay for testing."""
    import os

    # Load environment from .env if available
    from dotenv import load_dotenv
    load_dotenv()

    cycle = get_decay_cycle()
    result = await cycle.run_manual(dry_run=True)

    print(f"\nConfidence Decay Results:")
    print(f"  Insights to decay: {result.insights_decayed}")
    print(f"  Avg new confidence: {result.avg_new_confidence:.4f}")
    print(f"  Insights to archive: {result.insights_archived}")
    print(f"  Processing time: {result.processing_time_ms:.2f}ms")

    await cycle.shutdown()


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) > 1 and sys.argv[1] == '--schedule':
        # Run as scheduled task
        cycle = get_decay_cycle()
        cycle.start()

        # Keep the event loop running
        try:
            asyncio.get_event_loop().run_forever()
        except KeyboardInterrupt:
            pass
    else:
        # Run manual
        asyncio.run(main())