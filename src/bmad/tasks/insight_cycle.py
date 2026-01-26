"""
Insight Generation Cycle Task

This module provides scheduled tasks for batch insight generation.
Runs nightly to process outcomes from the last 24 hours.

Author: Brooks (BMAD Dev Agent)
Created: 2026-01-26
Story: 2-1-generate-insights-from-outcomes
"""

import logging
import asyncio
from datetime import datetime, timezone
from typing import List, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.bmad.core.neo4j_client import Neo4jAsyncClient
from src.bmad.services.insight_generator import (
    InsightGenerator,
    ProcessedOutcome,
    BatchGenerationResult
)

logger = logging.getLogger(__name__)


class InsightCycleTask:
    """
    Manages the nightly insight generation cycle.

    Features:
    - Scheduled batch processing via APScheduler
    - Multi-group processing
    - Metrics collection and logging
    """

    def __init__(self):
        """Initialize the insight cycle task."""
        self.scheduler = AsyncIOScheduler()
        self._client: Optional[Neo4jAsyncClient] = None
        self._generator: Optional[InsightGenerator] = None

    async def initialize(self) -> None:
        """Initialize the Neo4j client and generator."""
        self._client = Neo4jAsyncClient()
        await self._client.initialize()
        self._generator = InsightGenerator(self._client)
        logger.info("InsightCycleTask initialized")

    async def shutdown(self) -> None:
        """Shutdown the scheduler and close connections."""
        if self.scheduler.running:
            self.scheduler.shutdown()

        if self._client:
            await self._client.close()

        logger.info("InsightCycleTask shutdown")

    def start(self) -> None:
        """Start the scheduled insight generation cycle."""
        # Schedule nightly run at 2 AM
        trigger = CronTrigger(hour=2, minute=0)
        self.scheduler.add_job(
            self.run_cycle,
            trigger=trigger,
            id='insight_generation_cycle',
            name='Nightly Insight Generation',
            replace_existing=True
        )

        self.scheduler.start()
        logger.info("Insight generation cycle scheduled (runs at 2 AM daily)")

    async def run_cycle(self) -> Optional[BatchGenerationResult]:
        """
        Run the full insight generation cycle.

        Process all unprocessed outcomes from the last 24 hours
        across all project groups.
        """
        if not self._generator:
            await self.initialize()

        logger.info("Starting insight generation cycle...")

        # Get all project groups
        groups = await self._get_project_groups()

        total_result = BatchGenerationResult(
            processed_count=0,
            insights_generated=0,
            patterns_updated=0,
            total_time_ms=0,
            avg_time_per_outcome_ms=0
        )

        all_errors: List[str] = []

        for group_id in groups:
            try:
                # Get unprocessed outcomes for this group
                outcomes = await self._generator.get_unprocessed_outcomes(
                    group_id=group_id,
                    hours_back=24
                )

                if not outcomes:
                    logger.debug(f"No new outcomes for group {group_id}")
                    continue

                logger.info(f"Processing {len(outcomes)} outcomes for group {group_id}")

                # Process batch
                result = await self._generator.process_outcomes_batch(outcomes)

                # Aggregate results
                total_result.processed_count += result.processed_count
                total_result.insights_generated += result.insights_generated
                total_result.patterns_updated += result.patterns_updated
                total_result.total_time_ms += result.total_time_ms
                all_errors.extend(result.errors)

                # Log group-specific metrics
                logger.info(
                    f"Group {group_id}: {result.insights_generated} insights, "
                    f"{result.patterns_updated} patterns updated, "
                    f"{result.avg_time_per_outcome_ms:.2f}ms avg per outcome"
                )

            except Exception as e:
                error_msg = f"Error processing group {group_id}: {e}"
                logger.error(error_msg)
                all_errors.append(error_msg)

        # Calculate average
        if total_result.processed_count > 0:
            total_result.avg_time_per_outcome_ms = (
                total_result.total_time_ms / total_result.processed_count
            )

        # Log final metrics
        logger.info(
            f"Insight cycle complete: {total_result.processed_count} outcomes processed, "
            f"{total_result.insights_generated} insights generated, "
            f"{total_result.patterns_updated} patterns updated, "
            f"avg {total_result.avg_time_per_outcome_ms:.2f}ms per outcome"
        )

        if all_errors:
            logger.warning(f"Cycle had {len(all_errors)} errors")

        return total_result

    async def _get_project_groups(self) -> List[str]:
        """Get all project groups for processing."""
        query = """
        MATCH (g:Brain)
        WHERE g.scope = 'project' OR g.scope = 'global'
        RETURN DISTINCT g.group_id as group_id
        """

        results = await self._client.execute_query(query, {})
        return [r.get('group_id') for r in results if r.get('group_id')]

    async def run_manual(
        self,
        group_id: Optional[str] = None,
        hours_back: int = 24
    ) -> BatchGenerationResult:
        """
        Run insight generation manually (not scheduled).

        Args:
            group_id: Specific group to process (None for all groups)
            hours_back: How many hours back to look

        Returns:
            BatchGenerationResult with processing summary
        """
        if not self._generator:
            await self.initialize()

        logger.info(f"Manual insight generation for group: {group_id or 'all'}")

        if group_id:
            # Process specific group
            outcomes = await self._generator.get_unprocessed_outcomes(
                group_id=group_id,
                hours_back=hours_back
            )
            result = await self._generator.process_outcomes_batch(outcomes)
            return result
        else:
            # Run full cycle
            return await self.run_cycle()


# Global task instance
_insight_cycle: Optional[InsightCycleTask] = None


def get_insight_cycle() -> InsightCycleTask:
    """Get the global insight cycle task instance."""
    global _insight_cycle
    if _insight_cycle is None:
        _insight_cycle = InsightCycleTask()
    return _insight_cycle


async def main():
    """Run manual insight generation for testing."""
    import os
    os.environ['NEO4J_URI'] = 'bolt://localhost:7687'
    os.environ['NEO4J_USER'] = 'neo4j'
    os.environ['NEO4J_PASSWORD'] = 'Kamina2025*'

    cycle = get_insight_cycle()
    result = await cycle.run_manual(hours_back=24)

    print(f"\nInsight Generation Results:")
    print(f"  Processed: {result.processed_count}")
    print(f"  Insights generated: {result.insights_generated}")
    print(f"  Patterns updated: {result.patterns_updated}")
    print(f"  Total time: {result.total_time_ms:.2f}ms")
    print(f"  Avg per outcome: {result.avg_time_per_outcome_ms:.2f}ms")

    if result.errors:
        print(f"\n  Errors ({len(result.errors)}):")
        for error in result.errors[:5]:
            print(f"    - {error}")

    await cycle.shutdown()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--schedule':
        # Run as scheduled task
        cycle = get_insight_cycle()
        cycle.start()

        # Keep the event loop running
        try:
            asyncio.get_event_loop().run_forever()
        except KeyboardInterrupt:
            pass
    else:
        # Run manual
        asyncio.run(main())