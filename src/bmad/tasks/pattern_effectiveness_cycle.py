"""
Pattern Effectiveness Cycle Task

This module provides scheduled daily task for pattern effectiveness tracking.
- Runs daily at 2:05 AM (after insight generation)
- Updates success_rate from outcome history
- Generates alerts for low-effectiveness patterns

Author: Brooks (BMAD Dev Agent)
Created: 2026-01-26
Story: 4-2-track-pattern-effectiveness-daily
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.bmad.core.neo4j_client import Neo4jAsyncClient
from src.bmad.services.pattern_effectiveness import (
    PatternEffectivenessService,
    EffectivenessReport
)

logger = logging.getLogger(__name__)


class PatternEffectivenessCycle:
    """
    Manages the daily pattern effectiveness tracking cycle.

    Features:
    - Daily scheduled execution via APScheduler
    - Multi-group processing
    - Alert generation for low effectiveness
    - Metrics collection and logging
    """

    def __init__(self):
        """Initialize the pattern effectiveness cycle task."""
        self.scheduler = AsyncIOScheduler()
        self._client: Optional[Neo4jAsyncClient] = None
        self._service: Optional[PatternEffectivenessService] = None

    async def initialize(self) -> None:
        """Initialize the Neo4j client and service."""
        self._client = Neo4jAsyncClient()
        await self._client.initialize()
        self._service = PatternEffectivenessService(self._client)
        logger.info("PatternEffectivenessCycle initialized")

    async def shutdown(self) -> None:
        """Shutdown the scheduler and close connections."""
        if self.scheduler.running:
            self.scheduler.shutdown()

        if self._client:
            await self._client.close()

        logger.info("PatternEffectivenessCycle shutdown")

    def start(self) -> None:
        """
        Start the scheduled daily effectiveness tracking.

        Scheduled to run daily at 2:05 AM (after insight generation at 2 AM).
        """
        # Schedule daily run at 2:05 AM
        trigger = CronTrigger(hour=2, minute=5)
        self.scheduler.add_job(
            self.run_cycle,
            trigger=trigger,
            id='pattern_effectiveness_cycle',
            name='Daily Pattern Effectiveness Tracking',
            replace_existing=True
        )

        self.scheduler.start()
        logger.info("Pattern effectiveness cycle scheduled (runs daily at 2:05 AM)")

    async def run_cycle(
        self,
        group_id: Optional[str] = None
    ) -> EffectivenessReport:
        """
        Run the full effectiveness tracking cycle.

        Args:
            group_id: Optional specific group to process (None for all)

        Returns:
            EffectivenessReport with update results
        """
        if not self._service:
            await self.initialize()

        logger.info(f"Starting pattern effectiveness cycle for group: {group_id or 'all'}")

        try:
            # Get summary before update
            before_summary = await self._service.get_effectiveness_summary(group_id)
            logger.info(
                f"Before update - Patterns: {before_summary['total_patterns']}, "
                f"Avg success: {before_summary['avg_success_rate']:.2%}"
            )

            # Run effectiveness update
            report = await self._service.update_effectiveness(group_id)

            # Log results
            logger.info(
                f"Effectiveness cycle complete: "
                f"{report.patterns_updated} patterns updated, "
                f"avg success {report.avg_success_rate:.2%}, "
                f"{report.patterns_with_alerts} alerts"
            )

            # Log low effectiveness patterns
            if report.low_effectiveness_patterns:
                logger.warning(
                    f"LOW EFFECTIVENESS PATTERNS: "
                    f"{len(report.low_effectiveness_patterns)} patterns below "
                    f"{EffectivenessReport.LOW_EFFECTIVENESS_THRESHOLD:.0%} threshold"
                )

            return report

        except Exception as e:
            logger.error(f"Effectiveness cycle error: {e}")
            await self._notify_error(str(e))
            raise

    async def run_manual(
        self,
        group_id: Optional[str] = None
    ) -> EffectivenessReport:
        """
        Run effectiveness tracking manually (not scheduled).

        Args:
            group_id: Specific group to process (None for all)

        Returns:
            EffectivenessReport with processing summary
        """
        if not self._service:
            await self.initialize()

        logger.info(f"Manual effectiveness tracking for group: {group_id or 'all'}")

        return await self._service.update_effectiveness(group_id)

    async def get_summary(
        self,
        group_id: Optional[str] = None
    ) -> dict:
        """
        Get effectiveness summary without running update.

        Args:
            group_id: Specific group (None for all)

        Returns:
            Summary dict
        """
        if not self._service:
            await self.initialize()

        return await self._service.get_effectiveness_summary(group_id)

    async def _notify_error(self, error_message: str) -> None:
        """Send notification on error."""
        logger.error(f"ERROR NOTIFICATION: {error_message}")

        # In production, this would send to Slack/email/PagerDuty
        logger.critical(
            f"PATTERN EFFECTIVENESS FAILURE: {error_message}\n"
            f"Manual intervention may be required"
        )


# Global task instance
_effectiveness_cycle: Optional[PatternEffectivenessCycle] = None


def get_effectiveness_cycle() -> PatternEffectivenessCycle:
    """Get the global effectiveness cycle task instance."""
    global _effectiveness_cycle
    if _effectiveness_cycle is None:
        _effectiveness_cycle = PatternEffectivenessCycle()
    return _effectiveness_cycle


async def main():
    """Run manual effectiveness tracking for testing."""
    import os
    from dotenv import load_dotenv
    load_dotenv()

    cycle = get_effectivenessCycle()
    report = await cycle.run_manual()

    print(f"\nPattern Effectiveness Results:")
    print(f"  Patterns updated: {report.patterns_updated}")
    print(f"  Avg success rate: {report.avg_success_rate:.2%}")
    print(f"  Alerts: {report.patterns_with_alerts}")
    print(f"  Processing time: {report.processing_time_ms:.2f}ms")

    if report.low_effectiveness_patterns:
        print(f"\n  Low effectiveness patterns:")
        for p in report.low_effectiveness_patterns[:5]:
            print(f"    - {p.pattern_name}: {p.success_rate:.2%}")

    await cycle.shutdown()


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) > 1 and sys.argv[1] == '--schedule':
        cycle = get_effectivenessCycle()
        cycle.start()

        try:
            asyncio.get_event_loop().run_forever()
        except KeyboardInterrupt:
            pass
    else:
        asyncio.run(main())