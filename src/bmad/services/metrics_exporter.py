"""
Learning Metrics Exporter for Prometheus

This module exports BMAD learning metrics to Prometheus for monitoring.
- Track pattern reuse rate, insight generation, confidence scores
- Expose metrics via Prometheus client library
- Update metrics on configurable interval

Author: Brooks (BMAD Dev Agent)
Created: 2026-01-26
Story: 5-1-export-learning-metrics-to-prometheus
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional

from prometheus_client import Gauge, Counter, Histogram, Enum, REGISTRY, generate_latest, CONTENT_TYPE_LATEST

from src.bmad.core.neo4j_client import Neo4jAsyncClient

logger = logging.getLogger(__name__)


class MetricsExporter:
    """
    Exporter for BMAD learning metrics to Prometheus.

    Metrics Exposed:
    - bmad_insight_total: Total insights in the graph
    - bmad_pattern_reuse_rate: Percentage of tasks using patterns
    - bmad_avg_confidence_score: Average confidence across insights
    - bmad_events_total: Total events captured
    - bmad_agents_registered: Number of registered agents
    - bmad_knowledge_transfers_total: Cross-agent knowledge transfers
    - bmad_orphaned_agents: Count of orphaned AIAgent nodes
    - bmad_health_status: System health status (1=healthy, 0=unhealthy)
    - bmad_query_latency_seconds: Query latency histogram
    """

    def __init__(self, client: Neo4jAsyncClient):
        """
        Initialize the metrics exporter.

        Args:
            client: Neo4j async client for querying metrics
        """
        self._client = client
        self._last_update: Optional[datetime] = None
        self._update_interval_seconds = 300  # 5 minutes default

        # Define Prometheus metrics (auto-register to global REGISTRY)
        self._insight_total = Counter(
            'bmad_insight_total',
            'Total number of insights in the graph',
            ['applies_to']
        )
        self._pattern_reuse_rate = Gauge(
            'bmad_pattern_reuse_rate',
            'Percentage of tasks that leverage existing patterns',
            ['group_id']
        )
        self._avg_confidence_score = Gauge(
            'bmad_avg_confidence_score',
            'Average confidence score across all insights'
        )
        self._events_total = Counter(
            'bmad_events_total',
            'Total events captured in the system',
            ['event_type', 'group_id']
        )
        self._agents_registered = Gauge(
            'bmad_agents_registered',
            'Number of registered AIAgent nodes'
        )
        self._knowledge_transfers_total = Counter(
            'bmad_knowledge_transfers_total',
            'Total cross-agent knowledge transfers',
            ['from_agent', 'to_agent']
        )
        self._orphaned_agents = Gauge(
            'bmad_orphaned_agents',
            'Number of AIAgent nodes without brain connections'
        )
        self._active_patterns = Gauge(
            'bmad_active_patterns',
            'Number of active (non-decayed) patterns',
            ['group_id']
        )
        self._decayed_insights = Gauge(
            'bmad_decayed_insights',
            'Number of insights with decayed confidence'
        )

        # Histogram for query latency
        self._query_latency = Histogram(
            'bmad_query_latency_seconds',
            'Query latency in seconds',
            ['query_type'],
            buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
        )

        # Counters for rate calculations
        self._insights_generated_total = Counter(
            'bmad_insights_generated_total',
            'Total insights generated over time'
        )
        self._insights_generated_this_week = Gauge(
            'bmad_insights_generated_this_week',
            'Number of insights generated this week'
        )

        # Health status using Gauge with enum-like values
        self._health_status = Gauge(
            'bmad_health_status_numeric',
            'System health status (1=healthy, 2=degraded, 3=unhealthy)'
        )

    @property
    def last_update(self) -> Optional[datetime]:
        """When metrics were last updated."""
        return self._last_update

    @property
    def update_interval_seconds(self) -> int:
        """How often metrics are updated."""
        return self._update_interval_seconds

    async def update_all_metrics(self) -> Dict[str, Any]:
        """
        Update all metrics from Neo4j.

        Returns:
            Dict with update status and metrics summary
        """
        start_time = datetime.now(timezone.utc)

        try:
            # Update basic counts
            await self._update_insight_counts()
            await self._update_pattern_metrics()
            await self._update_confidence_score()
            await self._update_event_counts()
            await self._update_agent_counts()
            await self._update_health_status()
            await self._update_pattern_effectiveness_metrics()

            self._last_update = datetime.now(timezone.utc)
            update_time_ms = (self._last_update - start_time).total_seconds() * 1000

            logger.info(f"Metrics updated in {update_time_ms:.2f}ms")

            return {
                "status": "success",
                "update_time_ms": update_time_ms,
                "timestamp": self._last_update.isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to update metrics: {e}")
            self._health_status.set(2)  # degraded status
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    async def _update_insight_counts(self) -> None:
        """Update insight count metrics."""
        query = """
        MATCH (i:Insight)
        RETURN i.applies_to as applies_to, count(i) as count
        """

        results = await self._client.execute_query(query, {})

        for r in results:
            applies_to = r.get('applies_to', 'unknown') or 'unknown'
            count = r.get('count', 0)
            self._insight_total.labels(applies_to=applies_to).inc(count - self._get_current_count('insight', applies_to))
            # Set absolute value as well
            self._insight_total.labels(applies_to=applies_to)._value.set(count)

    def _get_current_count(self, metric_type: str, label: str) -> int:
        """Get current counter value for rate calculation."""
        # Simplified - return 0 for rate calculation
        return 0

    async def _update_pattern_metrics(self) -> None:
        """Update pattern reuse rate metrics."""
        query = """
        MATCH (o:Outcome)
        WHERE o.pattern_id IS NOT NULL
        WITH o.group_id as group_id, count(o) as with_pattern, o.group_id as g
        RETURN group_id, with_pattern, count(*) as total
        """

        try:
            results = await self._client.execute_query(query, {})

            for r in results:
                group_id = r.get('group_id', 'unknown') or 'unknown'
                with_pattern = r.get('with_pattern', 0)
                total = r.get('total', 1)  # Avoid division by zero

                reuse_rate = with_pattern / total if total > 0 else 0.0
                self._pattern_reuse_rate.labels(group_id=group_id).set(reuse_rate)

        except Exception as e:
            logger.warning(f"Could not update pattern metrics: {e}")
            # Set default values
            self._pattern_reuse_rate.labels(group_id='default').set(0.0)

    async def _update_confidence_score(self) -> None:
        """Update average confidence score metric."""
        query = """
        MATCH (i:Insight)
        WHERE i.confidence_score IS NOT NULL
        RETURN avg(i.confidence_score) as avg_confidence
        """

        try:
            results = await self._client.execute_query(query, {})
            if results and results[0].get('avg_confidence'):
                avg_confidence = float(results[0]['avg_confidence'])
                self._avg_confidence_score.set(avg_confidence)
            else:
                self._avg_confidence_score.set(0.0)
        except Exception as e:
            logger.warning(f"Could not update confidence metrics: {e}")
            self._avg_confidence_score.set(0.0)

    async def _update_event_counts(self) -> None:
        """Update event count metrics."""
        query = """
        MATCH (e:Event)
        RETURN e.event_type as event_type, e.group_id as group_id, count(e) as count
        """

        results = await self._client.execute_query(query, {})

        for r in results:
            event_type = r.get('event_type', 'unknown') or 'unknown'
            group_id = r.get('group_id', 'unknown') or 'unknown'
            count = r.get('count', 0)
            self._events_total.labels(event_type=event_type, group_id=group_id)._value.set(count)

    async def _update_agent_counts(self) -> None:
        """Update agent count and orphan metrics."""
        # Total agents
        query = """
        MATCH (a:AIAgent)
        RETURN count(a) as total_agents
        """

        try:
            results = await self._client.execute_query(query, {})
            if results and results[0].get('total_agents'):
                self._agents_registered.set(results[0]['total_agents'])

            # Orphaned agents
            orphan_query = """
            MATCH (a:AIAgent)
            WHERE NOT (a)-[:HAS_MEMORY_IN]->(:Brain)
            RETURN count(a) as orphaned
            """

            orphan_results = await self._client.execute_query(orphan_query, {})
            if orphan_results and orphan_results[0].get('orphaned'):
                self._orphaned_agents.set(orphan_results[0]['orphaned'])

        except Exception as e:
            logger.warning(f"Could not update agent metrics: {e}")

    async def _update_health_status(self) -> None:
        """Update system health status."""
        try:
            # Check for orphans
            orphan_query = """
            MATCH (a:AIAgent)
            WHERE NOT (a)-[:HAS_MEMORY_IN]->(:Brain)
            RETURN count(a) as orphaned
            """

            results = await self._client.execute_query(orphan_query, {})
            orphaned = results[0].get('orphaned', 0) if results else 0

            # 1 = healthy, 2 = degraded, 3 = unhealthy
            if orphaned == 0:
                self._health_status.set(1)
            elif orphaned < 5:
                self._health_status.set(2)
            else:
                self._health_status.set(3)

        except Exception as e:
            logger.warning(f"Could not update health status: {e}")
            self._health_status.set(2)  # degraded on error

    async def _update_pattern_effectiveness_metrics(self) -> None:
        """Update pattern effectiveness and decay metrics."""
        try:
            # Active patterns (success rate > 0.6)
            active_query = """
            MATCH (p:Pattern)
            WHERE p.success_rate >= 0.6
            RETURN p.group_id as group_id, count(p) as count
            """

            results = await self._client.execute_query(active_query, {})
            for r in results:
                group_id = r.get('group_id', 'unknown') or 'unknown'
                self._active_patterns.labels(group_id=group_id).set(r.get('count', 0))

            # Decayed insights (confidence < 0.3)
            decayed_query = """
            MATCH (i:Insight)
            WHERE i.confidence_score < 0.3
            RETURN count(i) as count
            """

            decayed_results = await self._client.execute_query(decayed_query, {})
            if decayed_results:
                self._decayed_insights.set(decayed_results[0].get('count', 0))

        except Exception as e:
            logger.warning(f"Could not update effectiveness metrics: {e}")

    def record_query_latency(self, query_type: str, latency_seconds: float) -> None:
        """Record query latency for monitoring."""
        self._query_latency.labels(query_type=query_type).observe(latency_seconds)

    def generate_metrics(self) -> bytes:
        """Generate metrics output in Prometheus format."""
        return generate_latest(REGISTRY)

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get current metrics summary."""
        # Map health status numeric to string
        health_value = self._health_status._value.get()
        health_map = {1: "healthy", 2: "degraded", 3: "unhealthy"}
        health_status = health_map.get(health_value, "unknown")

        return {
            "last_update": self._last_update.isoformat() if self._last_update else None,
            "update_interval_seconds": self._update_interval_seconds,
            "insight_count_by_domain": {
                "python": self._insight_total.labels(applies_to="python")._value.get(),
                "javascript": self._insight_total.labels(applies_to="javascript")._value.get(),
                "default": self._insight_total.labels(applies_to="default")._value.get()
            },
            "avg_confidence": self._avg_confidence_score._value.get(),
            "health_status": health_status,
            "orphaned_agents": self._orphaned_agents._value.get(),
            "active_patterns": {
                "default": self._active_patterns.labels(group_id="default")._value.get()
            }
        }


class MetricsScheduler:
    """
    Scheduler for periodic metrics updates.

    Updates metrics every 5 minutes and exposes them via HTTP.
    """

    def __init__(self, exporter: MetricsExporter):
        """Initialize the metrics scheduler."""
        self._exporter = exporter
        self._update_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self, interval_seconds: int = 300) -> None:
        """Start periodic metrics updates."""
        self._running = True
        logger.info(f"Starting metrics scheduler (interval: {interval_seconds}s)")

        # Initial update
        await self._exporter.update_all_metrics()

        # Periodic updates
        while self._running:
            await asyncio.sleep(interval_seconds)
            if self._running:
                await self._exporter.update_all_metrics()

    def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        logger.info("Metrics scheduler stopped")


def create_metrics_exporter(client: Neo4jAsyncClient) -> MetricsExporter:
    """Factory function to create a metrics exporter."""
    return MetricsExporter(client)


async def main():
    """Test the metrics exporter."""
    from src.bmad.core.neo4j_client import Neo4jAsyncClient

    async with Neo4jAsyncClient() as client:
        exporter = MetricsExporter(client)

        print("Testing metrics exporter...")

        # Update metrics
        result = await exporter.update_all_metrics()
        print(f"\nUpdate Result: {result}")

        # Get summary
        summary = exporter.get_metrics_summary()
        print(f"\nMetrics Summary:")
        for key, value in summary.items():
            print(f"  {key}: {value}")

        # Generate Prometheus output
        metrics_output = exporter.generate_metrics()
        print(f"\nPrometheus Output ({len(metrics_output)} bytes):")
        print(metrics_output[:500].decode('utf-8') + "...")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())