"""
Knowledge Transfer Batch Task

This module provides a daily scheduled task for cross-agent knowledge sharing.
- Runs at 2:10 AM (after insight generation at 2:00 AM)
- Processes all project groups
- Logs transfer metrics for monitoring

Author: Brooks (BMAD Dev Agent)
Created: 2026-01-26
Story: 2-3-share-high-confidence-insights-across-agents
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.bmad.core.neo4j_client import Neo4jAsyncClient
from src.bmad.services.knowledge_transfer import KnowledgeTransferService

logger = logging.getLogger(__name__)


class KnowledgeTransferCycle:
    """
    Daily batch task for cross-agent knowledge sharing.

    Scheduled to run at 2:10 AM, after the insight generation task.
    Processes all project groups and shares high-confidence insights.
    """

    def __init__(self, neo4j_client: Neo4jAsyncClient):
        """
        Initialize the knowledge transfer cycle task.

        Args:
            neo4j_client: Neo4j async client for database operations
        """
        self._client = neo4j_client
        self._service = KnowledgeTransferService(neo4j_client)
        self._scheduler = AsyncIOScheduler()
        self._groups_to_process: List[str] = []

    def add_group(self, group_id: str) -> None:
        """
        Add a project group to the processing queue.

        Args:
            group_id: The project group ID to process
        """
        if group_id not in self._groups_to_process:
            self._groups_to_process.append(group_id)
            logger.info(f"Added group '{group_id}' to knowledge transfer queue")

    def remove_group(self, group_id: str) -> None:
        """
        Remove a project group from the processing queue.

        Args:
            group_id: The project group ID to remove
        """
        if group_id in self._groups_to_process:
            self._groups_to_process.remove(group_id)
            logger.info(f"Removed group '{group_id}' from knowledge transfer queue")

    async def run_cycle(self) -> Dict[str, Any]:
        """
        Execute one full knowledge transfer cycle for all groups.

        Returns:
            Dictionary with cycle metrics
        """
        start_time = datetime.now(timezone.utc)
        total_results = {
            "started_at": start_time.isoformat(),
            "groups_processed": 0,
            "total_insights_shared": 0,
            "total_agents_updated": 0,
            "group_results": []
        }

        # If no groups configured, use default
        if not self._groups_to_process:
            self._groups_to_process = ["global-coding-skills"]

        logger.info(
            f"Starting knowledge transfer cycle for {len(self._groups_to_process)} groups: "
            f"{', '.join(self._groups_to_process)}"
        )

        for group_id in self._groups_to_process:
            try:
                # Check pending shares first
                pending = await self._service.count_pending_shares(group_id)
                logger.info(f"Group {group_id}: {pending['insights_pending']} insights pending")

                if pending['total_shares_needed'] > 0:
                    # Run knowledge transfer for this group
                    result = await self._service.share_high_confidence_insights(group_id)

                    group_result = {
                        "group_id": group_id,
                        "insights_shared": result.insights_shared,
                        "agents_updated": result.agents_updated,
                        "latency_ms": result.latency_ms
                    }
                    total_results["group_results"].append(group_result)

                    total_results["total_insights_shared"] += result.insights_shared
                    total_results["total_agents_updated"] += result.agents_updated

                    logger.info(
                        f"Group {group_id}: {result.insights_shared} insights shared to "
                        f"{result.agents_updated} agents in {result.latency_ms:.2f}ms"
                    )
                else:
                    total_results["group_results"].append({
                        "group_id": group_id,
                        "insights_shared": 0,
                        "agents_updated": 0,
                        "latency_ms": 0,
                        "status": "no_changes"
                    })

                total_results["groups_processed"] += 1

            except Exception as e:
                logger.error(f"Knowledge transfer failed for group {group_id}: {e}")
                total_results["group_results"].append({
                    "group_id": group_id,
                    "error": str(e),
                    "status": "failed"
                })

        # Calculate cycle metrics
        end_time = datetime.now(timezone.utc)
        cycle_duration = (end_time - start_time).total_seconds()

        total_results["completed_at"] = end_time.isoformat()
        total_results["duration_seconds"] = round(cycle_duration, 2)

        logger.info(
            f"Knowledge transfer cycle complete: "
            f"{total_results['total_insights_shared']} insights shared to "
            f"{total_results['total_agents_updated']} agents in {cycle_duration:.2f}s"
        )

        return total_results

    async def run_for_group(self, group_id: str) -> Dict[str, Any]:
        """
        Run knowledge transfer for a single group (manual/API use).

        Args:
            group_id: The project group ID to process

        Returns:
            Knowledge transfer result for the group
        """
        logger.info(f"Manual knowledge transfer triggered for group: {group_id}")

        pending = await self._service.count_pending_shares(group_id)
        logger.info(f"Pending: {pending}")

        result = await self._service.share_high_confidence_insights(group_id)

        return {
            "group_id": group_id,
            "insights_shared": result.insights_shared,
            "agents_updated": result.agents_updated,
            "transfers": result.transfers,
            "latency_ms": result.latency_ms
        }

    def start(self) -> None:
        """Start the scheduler for daily knowledge transfer at 2:10 AM."""
        # Schedule for 2:10 AM daily (after insight generation at 2:00 AM)
        trigger = CronTrigger(hour=2, minute=10)

        self._scheduler.add_job(
            self.run_cycle,
            trigger=trigger,
            id='knowledge_transfer_cycle',
            name='Daily Knowledge Transfer',
            replace_existing=True
        )

        self._scheduler.start()
        logger.info("Knowledge transfer scheduler started (runs daily at 2:10 AM)")

    def stop(self) -> None:
        """Stop the scheduler."""
        if self._scheduler.running:
            self._scheduler.shutdown()
            logger.info("Knowledge transfer scheduler stopped")

    def is_running(self) -> bool:
        """Check if the scheduler is running."""
        return self._scheduler.running


async def main():
    """Quick test of the knowledge transfer cycle."""
    import os
    os.environ['NEO4J_URI'] = 'bolt://localhost:7687'
    os.environ['NEO4J_USER'] = 'neo4j'
    os.environ['NEO4J_PASSWORD'] = 'Kamina2025*'

    from src.bmad.core.neo4j_client import Neo4jAsyncClient

    async with Neo4jAsyncClient() as client:
        cycle = KnowledgeTransferCycle(client)

        # Add groups to process
        cycle.add_group("global-coding-skills")

        print("Running knowledge transfer cycle...")
        result = await cycle.run_cycle()

        print(f"\nCycle Results:")
        print(f"  Groups processed: {result['groups_processed']}")
        print(f"  Total insights shared: {result['total_insights_shared']}")
        print(f"  Total agents updated: {result['total_agents_updated']}")
        print(f"  Duration: {result['duration_seconds']}s")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())