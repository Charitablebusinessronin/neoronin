"""
Notion Sync Cycle Task

This module provides a daily scheduled task for syncing Notion pages.
- Runs at 3:00 AM daily
- Fetches pages from Notion API
- Syncs to KnowledgeItem nodes in Neo4j
- Logs sync metrics

Author: Brooks (BMAD Dev Agent)
Created: 2026-01-26
Story: 3-3-integrate-notion-knowledge-base
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.bmad.core.neo4j_client import Neo4jAsyncClient
from src.bmad.services.notion_sync import NotionSyncService, SyncResult

logger = logging.getLogger(__name__)


class NotionSyncCycle:
    """
    Daily batch task for Notion knowledge sync.

    Scheduled to run at 3:00 AM to avoid peak usage hours.
    Syncs all configured Notion databases to KnowledgeItem nodes.
    """

    def __init__(self, neo4j_client: Neo4jAsyncClient):
        """
        Initialize the Notion sync cycle task.

        Args:
            neo4j_client: Neo4j async client for database operations
        """
        self._client = neo4j_client
        self._service = NotionSyncService(neo4j_client)
        self._scheduler = AsyncIOScheduler()
        self._groups_to_sync: List[str] = ["global-coding-skills"]
        self._database_ids: List[str] = []

    def add_group(self, group_id: str) -> None:
        """Add a project group to the sync queue."""
        if group_id not in self._groups_to_sync:
            self._groups_to_sync.append(group_id)
            logger.info(f"Added group '{group_id}' to Notion sync queue")

    def add_database(self, database_id: str) -> None:
        """Add a Notion database ID to sync."""
        if database_id not in self._database_ids:
            self._database_ids.append(database_id)
            logger.info(f"Added Notion database '{database_id}' to sync list")

    async def run_cycle(self) -> Dict[str, Any]:
        """
        Execute one full sync cycle for all groups.

        Returns:
            Dictionary with cycle metrics
        """
        start_time = datetime.now(timezone.utc)
        total_results = {
            "started_at": start_time.isoformat(),
            "groups_processed": 0,
            "total_pages": 0,
            "total_created": 0,
            "total_updated": 0,
            "total_errors": 0,
            "group_results": []
        }

        logger.info(
            f"Starting Notion sync cycle for {len(self._groups_to_sync)} groups: "
            f"{', '.join(self._groups_to_sync)}"
        )

        for group_id in self._groups_to_sync:
            try:
                # Fetch pages from Notion
                pages = await self._service.fetch_notion_pages(
                    database_id=self._database_ids[0] if self._database_ids else None,
                    limit=100
                )

                if pages:
                    # Sync to Neo4j
                    result = await self._service.sync_knowledge_items(pages, group_id)

                    group_result = {
                        "group_id": group_id,
                        "pages_processed": result.pages_processed,
                        "created": result.items_created,
                        "updated": result.items_updated,
                        "errors": len(result.errors),
                        "duration_ms": result.duration_ms
                    }
                    total_results["group_results"].append(group_result)

                    total_results["total_pages"] += result.pages_processed
                    total_results["total_created"] += result.items_created
                    total_results["total_updated"] += result.items_updated
                    total_results["total_errors"] += len(result.errors)

                    logger.info(
                        f"Group {group_id}: {result.pages_processed} pages synced "
                        f"({result.items_created} created, {result.items_updated} updated)"
                    )
                else:
                    total_results["group_results"].append({
                        "group_id": group_id,
                        "status": "no_pages"
                    })

                total_results["groups_processed"] += 1

            except Exception as e:
                logger.error(f"Notion sync failed for group {group_id}: {e}")
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
            f"Notion sync cycle complete: "
            f"{total_results['total_pages']} pages, "
            f"{total_results['total_created']} created, "
            f"{total_results['total_updated']} updated in {cycle_duration:.2f}s"
        )

        return total_results

    async def run_for_group(
        self,
        group_id: str,
        database_id: Optional[str] = None
    ) -> SyncResult:
        """
        Run sync for a single group (manual/API use).

        Args:
            group_id: The project group ID to sync for
            database_id: Optional Notion database ID

        Returns:
            SyncResult for the operation
        """
        logger.info(f"Manual Notion sync triggered for group: {group_id}")

        pages = await self._service.fetch_notion_pages(
            database_id=database_id,
            limit=100
        )

        result = await self._service.sync_knowledge_items(pages, group_id)

        return result

    def start(self) -> None:
        """Start the scheduler for daily sync at 3:00 AM."""
        # Schedule for 3:00 AM daily
        trigger = CronTrigger(hour=3, minute=0)

        self._scheduler.add_job(
            self.run_cycle,
            trigger=trigger,
            id='notion_sync_cycle',
            name='Daily Notion Sync',
            replace_existing=True
        )

        self._scheduler.start()
        logger.info("Notion sync scheduler started (runs daily at 3:00 AM)")

    def stop(self) -> None:
        """Stop the scheduler."""
        if self._scheduler.running:
            self._scheduler.shutdown()
            logger.info("Notion sync scheduler stopped")

    def is_running(self) -> bool:
        """Check if the scheduler is running."""
        return self._scheduler.running


async def main():
    """Quick test of the Notion sync cycle."""
    from src.bmad.core.neo4j_client import Neo4jAsyncClient

    async with Neo4jAsyncClient() as client:
        cycle = NotionSyncCycle(client)

        # Add groups to sync
        cycle.add_group("global-coding-skills")

        print("Running Notion sync cycle...")
        result = await cycle.run_cycle()

        print(f"\nCycle Results:")
        print(f"  Groups processed: {result['groups_processed']}")
        print(f"  Total pages: {result['total_pages']}")
        print(f"  Total created: {result['total_created']}")
        print(f"  Total updated: {result['total_updated']}")
        print(f"  Duration: {result['duration_seconds']}s")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())