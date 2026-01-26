"""
Event Aggregation Cycle Task

This module provides scheduled weekly task for event aggregation.
- Runs weekly on Sunday at 3:00 AM
- Aggregates events older than 30 days
- Archives original events to CSV

Author: Brooks (BMAD Dev Agent)
Created: 2026-01-26
Story: 4-3-aggregate-old-events
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.bmad.core.neo4j_client import Neo4jAsyncClient
from src.bmad.services.event_aggregation import (
    EventAggregationService,
    AggregationMetrics
)

logger = logging.getLogger(__name__)


class EventAggregationCycle:
    """
    Manages the weekly event aggregation cycle.

    Features:
    - Weekly scheduled execution via APScheduler
    - Multi-group processing
    - CSV archival of old events
    - Metrics collection and logging
    """

    def __init__(self):
        """Initialize the event aggregation cycle task."""
        self.scheduler = AsyncIOScheduler()
        self._client: Optional[Neo4jAsyncClient] = None
        self._service: Optional[EventAggregationService] = None

    async def initialize(self) -> None:
        """Initialize the Neo4j client and service."""
        self._client = Neo4jAsyncClient()
        await self._client.initialize()
        self._service = EventAggregationService(self._client)
        logger.info("EventAggregationCycle initialized")

    async def shutdown(self) -> None:
        """Shutdown the scheduler and close connections."""
        if self.scheduler.running:
            self.scheduler.shutdown()

        if self._client:
            await self._client.close()

        logger.info("EventAggregationCycle shutdown")

    def start(self) -> None:
        """
        Start the scheduled weekly aggregation.

        Scheduled to run weekly on Sunday at 3:00 AM.
        """
        # Schedule weekly run on Sunday at 3 AM
        trigger = CronTrigger(day_of_week='sun', hour=3, minute=0)
        self.scheduler.add_job(
            self.run_cycle,
            trigger=trigger,
            id='event_aggregation_cycle',
            name='Weekly Event Aggregation',
            replace_existing=True
        )

        self.scheduler.start()
        logger.info("Event aggregation cycle scheduled (runs Sunday at 3 AM)")

    async def run_cycle(
        self,
        group_id: Optional[str] = None,
        event_age_days: int = 30
    ) -> AggregationMetrics:
        """
        Run the full event aggregation cycle.

        Args:
            group_id: Optional specific group to process (None for all)
            event_age_days: Age threshold for aggregation (default 30)

        Returns:
            AggregationMetrics with operation results
        """
        if not self._service:
            await self.initialize()

        logger.info(f"Starting event aggregation cycle for group: {group_id or 'all'}")

        try:
            # Get event counts before aggregation
            before_counts = await self._service.get_event_counts(group_id)
            logger.info(
                f"Before aggregation - Total: {before_counts['total_events']}, "
                f"Old: {before_counts['old_events']}"
            )

            # Run aggregation
            metrics = await self._service.aggregate_events(
                group_id=group_id,
                event_age_days=event_age_days,
                dry_run=False
            )

            # Log results
            logger.info(
                f"Aggregation cycle complete: "
                f"{metrics.events_aggregated} events aggregated, "
                f"{metrics.events_archived} archived, "
                f"{metrics.processing_time_ms:.2f}ms"
            )

            # Log archive location
            if metrics.archive_path:
                logger.info(f"Events archived to: {metrics.archive_path}")

            return metrics

        except Exception as e:
            logger.error(f"Aggregation cycle error: {e}")
            await self._notify_error(str(e))
            raise

    async def run_manual(
        self,
        group_id: Optional[str] = None,
        dry_run: bool = True
    ) -> AggregationMetrics:
        """
        Run aggregation manually (not scheduled).

        Args:
            group_id: Specific group to process (None for all)
            dry_run: If True, simulate without making changes

        Returns:
            AggregationMetrics with processing summary
        """
        if not self._service:
            await self.initialize()

        logger.info(f"Manual event aggregation for group: {group_id or 'all'}")

        return await self._service.aggregate_events(
            group_id=group_id,
            dry_run=dry_run
        )

    async def get_event_counts(
        self,
        group_id: Optional[str] = None
    ) -> dict:
        """
        Get event counts without running aggregation.

        Args:
            group_id: Specific group (None for all)

        Returns:
            Counts dict
        """
        if not self._service:
            await self.initialize()

        return await self._service.get_event_counts(group_id)

    async def _notify_error(self, error_message: str) -> None:
        """Send notification on error."""
        logger.error(f"ERROR NOTIFICATION: {error_message}")

        # In production, this would send to Slack/email/PagerDuty
        logger.critical(
            f"EVENT AGGREGATION FAILURE: {error_message}\n"
            f"Manual intervention may be required"
        )


# Global task instance
_aggregation_cycle: Optional[EventAggregationCycle] = None


def get_aggregation_cycle() -> EventAggregationCycle:
    """Get the global aggregation cycle task instance."""
    global _aggregation_cycle
    if _aggregation_cycle is None:
        _aggregation_cycle = EventAggregationCycle()
    return _aggregation_cycle


async def main():
    """Run manual event aggregation for testing."""
    import os
    from dotenv import load_dotenv
    load_dotenv()

    cycle = get_aggregation_cycle()
    metrics = await cycle.run_manual(dry_run=True)

    print(f"\nEvent Aggregation Results:")
    print(f"  Events to aggregate: {metrics.events_aggregated}")
    print(f"  Summaries to create: {metrics.summaries_created}")
    print(f"  Processing time: {metrics.processing_time_ms:.2f}ms")

    await cycle.shutdown()


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) > 1 and sys.argv[1] == '--schedule':
        cycle = get_aggregation_cycle()
        cycle.start()

        try:
            asyncio.get_event_loop().run_forever()
        except KeyboardInterrupt:
            pass
    else:
        asyncio.run(main())