"""
Health Check Cycle Task

This module provides scheduled weekly task for health checks and orphan repair.
- Runs weekly on Monday at 1:00 AM
- Checks for orphaned relationships
- Automatically repairs issues found

Author: Brooks (BMAD Dev Agent)
Created: 2026-01-26
Story: 4-4-detect-and-resolve-orphaned-relationships
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.bmad.core.neo4j_client import Neo4jAsyncClient
from src.bmad.services.orphan_repair import (
    OrphanRepairService,
    HealthCheckResult,
    RepairResult
)

logger = logging.getLogger(__name__)


class HealthCheckCycle:
    """
    Manages the weekly health check and repair cycle.

    Features:
    - Weekly scheduled execution via APScheduler
    - Orphan detection and automatic repair
    - Performance monitoring (<5 second target)
    - Metrics collection and logging
    """

    def __init__(self):
        """Initialize the health check cycle task."""
        self.scheduler = AsyncIOScheduler()
        self._client: Optional[Neo4jAsyncClient] = None
        self._service: Optional[OrphanRepairService] = None

    async def initialize(self) -> None:
        """Initialize the Neo4j client and service."""
        self._client = Neo4jAsyncClient()
        await self._client.initialize()
        self._service = OrphanRepairService(self._client)
        logger.info("HealthCheckCycle initialized")

    async def shutdown(self) -> None:
        """Shutdown the scheduler and close connections."""
        if self.scheduler.running:
            self.scheduler.shutdown()

        if self._client:
            await self._client.close()

        logger.info("HealthCheckCycle shutdown")

    def start(self) -> None:
        """
        Start the scheduled weekly health check.

        Scheduled to run weekly on Monday at 1:00 AM.
        """
        # Schedule weekly run on Monday at 1 AM
        trigger = CronTrigger(day_of_week='mon', hour=1, minute=0)
        self.scheduler.add_job(
            self.run_cycle,
            trigger=trigger,
            id='health_check_cycle',
            name='Weekly Health Check and Repair',
            replace_existing=True
        )

        self.scheduler.start()
        logger.info("Health check cycle scheduled (runs Monday at 1 AM)")

    async def run_cycle(
        self,
        auto_repair: bool = True
    ) -> dict:
        """
        Run the full health check and repair cycle.

        Args:
            auto_repair: Whether to automatically repair issues found

        Returns:
            Dict with health check and repair results
        """
        if not self._service:
            await self.initialize()

        logger.info("Starting weekly health check cycle")

        try:
            # Run health check
            health = await self._service.run_health_check()

            repair_result = None
            if not health.is_healthy and auto_repair:
                logger.warning(
                    f"Health issues detected: {len(health.orphaned_agents)} orphaned agents, "
                    f"{len(health.orphaned_brains)} orphaned brains"
                )

                # Run repair
                repair_result = await self._service.repair_orphaned_relationships()

                # Re-check health
                health = await self._service.run_health_check()

            # Log results
            if health.is_healthy:
                logger.info(
                    f"Health check complete: HEALTHY, "
                    f"{health.checks_passed}/{health.total_checks} checks passed, "
                    f"{health.processing_time_ms:.2f}ms"
                )
            else:
                logger.warning(
                    f"Health check complete: UNHEALTHY, "
                    f"{len(health.orphaned_agents)} orphaned agents, "
                    f"{len(health.orphaned_brains)} orphaned brains"
                )

            # Check performance target
            if health.processing_time_ms > 5000:
                logger.warning(
                    f"Health check exceeded 5 second target: {health.processing_time_ms:.2f}ms"
                )

            return {
                "health_check": {
                    "is_healthy": health.is_healthy,
                    "checks_passed": health.checks_passed,
                    "total_checks": health.total_checks,
                    "orphaned_agents": len(health.orphaned_agents),
                    "orphaned_brains": len(health.orphaned_brains),
                    "processing_time_ms": health.processing_time_ms
                },
                "repair": repair_result.to_dict() if repair_result else None
            }

        except Exception as e:
            logger.error(f"Health check cycle error: {e}")
            await self._notify_error(str(e))
            raise

    async def run_health_check_only(self) -> HealthCheckResult:
        """
        Run health check without repair (manual mode).

        Returns:
            HealthCheckResult with findings
        """
        if not self._service:
            await self.initialize()

        logger.info("Running manual health check")
        return await self._service.run_health_check()

    async def run_repair_only(self) -> RepairResult:
        """
        Run repair without pre-check (manual mode).

        Returns:
            RepairResult with repair details
        """
        if not self._service:
            await self.initialize()

        logger.info("Running manual repair")
        return await self._service.repair_orphaned_relationships()

    async def get_repair_candidates(self) -> dict:
        """
        Get summary of repair candidates without running full check.

        Returns:
            Dict with candidate summary
        """
        if not self._service:
            await self.initialize()

        return await self._service.get_repair_candidates()

    async def _notify_error(self, error_message: str) -> None:
        """Send notification on error."""
        logger.error(f"ERROR NOTIFICATION: {error_message}")

        # In production, this would send to Slack/email/PagerDuty
        logger.critical(
            f"HEALTH CHECK FAILURE: {error_message}\n"
            f"Manual intervention may be required"
        )


# Global task instance
_health_cycle: Optional[HealthCheckCycle] = None


def get_health_check_cycle() -> HealthCheckCycle:
    """Get the global health check cycle task instance."""
    global _health_cycle
    if _health_cycle is None:
        _health_cycle = HealthCheckCycle()
    return _health_cycle


async def main():
    """Run manual health check for testing."""
    import os
    from dotenv import load_dotenv
    load_dotenv()

    cycle = get_health_checkCycle()
    health = await cycle.run_health_check_only()

    print(f"\nHealth Check Results:")
    print(f"  Healthy: {health.is_healthy}")
    print(f"  Checks passed: {health.checks_passed}/{health.total_checks}")
    print(f"  Orphaned agents: {len(health.orphaned_agents)}")
    print(f"  Orphaned brains: {len(health.orphaned_brains)}")
    print(f"  Processing time: {health.processing_time_ms:.2f}ms")

    await cycle.shutdown()


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) > 1 and sys.argv[1] == '--schedule':
        cycle = get_health_checkCycle()
        cycle.start()

        try:
            asyncio.get_event_loop().run_forever()
        except KeyboardInterrupt:
            pass
    else:
        asyncio.run(main())