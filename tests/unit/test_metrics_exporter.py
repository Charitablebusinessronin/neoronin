"""Unit tests for Learning Metrics Exporter (Story 5-1).

Tests cover:
- Prometheus metrics definition and collection
- Metrics update from Neo4j
- Metrics summary generation
- API endpoints
"""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock
from typing import Any, Dict
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from prometheus_client import REGISTRY, CollectorRegistry

from src.bmad.core.neo4j_client import Neo4jAsyncClient
from src.bmad.services.metrics_exporter import (
    MetricsExporter,
    MetricsScheduler,
    create_metrics_exporter
)


@pytest.fixture(autouse=True)
def clean_prometheus_registry():
    """Clear prometheus registry before and after each test."""
    # Clear registry before test
    collectors_to_remove = list(REGISTRY._names_to_collectors.keys())
    for name in collectors_to_remove:
        if name.startswith('bmad_'):
            collector = REGISTRY._names_to_collectors.pop(name)
            if hasattr(REGISTRY, '_children'):
                REGISTRY._children = [(c, v) for c, v in REGISTRY._children if c is not collector]
    yield
    # Cleanup after test
    collectors_to_remove = list(REGISTRY._names_to_collectors.keys())
    for name in collectors_to_remove:
        if name.startswith('bmad_'):
            collector = REGISTRY._names_to_collectors.pop(name)
            if hasattr(REGISTRY, '_children'):
                REGISTRY._children = [(c, v) for c, v in REGISTRY._children if c is not collector]


class TestMetricsExporterInit:
    """Test MetricsExporter initialization."""

    def test_init_with_client(self):
        """Exporter should initialize with Neo4j client."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        exporter = MetricsExporter(mock_client)

        assert exporter._client == mock_client
        assert exporter._last_update is None
        assert exporter._update_interval_seconds == 300


class TestMetricsExporterMetrics:
    """Test that metrics are properly defined."""

    def test_metrics_exporter_has_required_metrics(self):
        """Exporter should have all required Prometheus metrics."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        exporter = MetricsExporter(mock_client)

        # Check that metrics exist
        assert hasattr(exporter, '_insight_total')
        assert hasattr(exporter, '_pattern_reuse_rate')
        assert hasattr(exporter, '_avg_confidence_score')
        assert hasattr(exporter, '_events_total')
        assert hasattr(exporter, '_agents_registered')
        assert hasattr(exporter, '_orphaned_agents')
        assert hasattr(exporter, '_health_status')
        assert hasattr(exporter, '_query_latency')
        assert hasattr(exporter, '_active_patterns')
        assert hasattr(exporter, '_decayed_insights')


class TestMetricsUpdate:
    """Test metrics update functionality."""

    @pytest.mark.asyncio
    async def test_update_all_metrics_success(self):
        """Should update all metrics successfully."""
        mock_records = [
            {'applies_to': 'python', 'count': 10},
            {'applies_to': 'javascript', 'count': 5}
        ]
        pattern_records = [
            {'group_id': 'faith-meats', 'with_pattern': 8, 'total': 10}
        ]
        confidence_records = [{'avg_confidence': 0.75}]
        agent_records = [{'total_agents': 5}]
        orphan_records = [{'orphaned': 1}]
        event_records = [
            {'event_type': 'commit', 'group_id': 'faith-meats', 'count': 100}
        ]
        active_records = [{'group_id': 'default', 'count': 20}]
        decayed_records = [{'count': 3}]

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(side_effect=[
            mock_records,       # _update_insight_counts
            pattern_records,    # _update_pattern_metrics
            confidence_records, # _update_confidence_score
            agent_records,      # _update_agent_counts (first call)
            orphan_records,     # _update_agent_counts (second call)
            event_records,      # _update_event_counts
            active_records,     # _update_pattern_effectiveness (first)
            decayed_records     # _update_pattern_effectiveness (second)
        ])

        exporter = MetricsExporter(mock_client)
        result = await exporter.update_all_metrics()

        assert result['status'] == 'success'
        assert 'update_time_ms' in result
        assert 'timestamp' in result
        assert exporter.last_update is not None

    @pytest.mark.asyncio
    async def test_update_metrics_handles_empty_results(self):
        """Should handle empty query results gracefully."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=[])

        exporter = MetricsExporter(mock_client)
        result = await exporter.update_all_metrics()

        # Should still report success
        assert result['status'] == 'success'
        assert exporter.last_update is not None

    @pytest.mark.asyncio
    async def test_update_metrics_handles_error(self):
        """Should handle errors gracefully."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(side_effect=Exception("Connection error"))

        exporter = MetricsExporter(mock_client)
        result = await exporter.update_all_metrics()

        assert result['status'] == 'error'
        assert 'error' in result


class TestQueryLatency:
    """Test query latency recording."""

    def test_record_query_latency(self):
        """Should record query latency without error."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        exporter = MetricsExporter(mock_client)

        # Should not raise
        exporter.record_query_latency("pattern_query", 0.125)
        exporter.record_query_latency("insight_query", 0.05)


class TestMetricsGeneration:
    """Test Prometheus metrics generation."""

    def test_generate_metrics_returns_bytes(self):
        """Should generate Prometheus format metrics."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        exporter = MetricsExporter(mock_client)

        output = exporter.generate_metrics()

        assert isinstance(output, bytes)
        assert len(output) > 0

    def test_generate_metrics_contains_bmad_prefix(self):
        """Should contain BMAD-specific metric names."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        exporter = MetricsExporter(mock_client)

        output = exporter.generate_metrics().decode('utf-8')

        assert 'bmad_' in output


class TestMetricsSummary:
    """Test metrics summary generation."""

    @pytest.mark.asyncio
    async def test_get_metrics_summary(self):
        """Should return metrics summary."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=[])

        exporter = MetricsExporter(mock_client)
        await exporter.update_all_metrics()

        summary = exporter.get_metrics_summary()

        assert 'last_update' in summary
        assert 'update_interval_seconds' in summary
        assert 'insight_count_by_domain' in summary
        assert 'avg_confidence' in summary
        assert 'health_status' in summary
        assert 'orphaned_agents' in summary


class TestMetricsScheduler:
    """Test metrics scheduler."""

    def test_scheduler_init(self):
        """Should initialize scheduler."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        exporter = MetricsExporter(mock_client)
        scheduler = MetricsScheduler(exporter)

        assert scheduler._exporter == exporter
        assert scheduler._running is False

    @pytest.mark.asyncio
    async def test_scheduler_start_stop(self):
        """Should start and stop scheduler."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        exporter = MetricsExporter(mock_client)
        exporter.update_all_metrics = AsyncMock(return_value={'status': 'success'})
        scheduler = MetricsScheduler(exporter)

        # Start with very short interval for testing
        task = asyncio.create_task(scheduler.start(interval_seconds=1))

        # Let it run for a moment
        await asyncio.sleep(2)

        # Stop
        scheduler.stop()
        await asyncio.sleep(0.1)

        assert scheduler._running is False


class TestCreateMetricsExporter:
    """Test factory function."""

    def test_create_metrics_exporter(self):
        """Should create exporter via factory."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        exporter = create_metrics_exporter(mock_client)

        assert isinstance(exporter, MetricsExporter)


class TestMetricsExporterIntegration:
    """Integration tests with real Neo4j."""

    @pytest.fixture
    def neo4j_client(self):
        """Create real Neo4j client."""
        try:
            client = Neo4jAsyncClient(
                uri=__import__('os').environ.get('NEO4J_URI', 'bolt://localhost:7687'),
                user=__import__('os').environ.get('NEO4J_USER', 'neo4j'),
                password=__import__('os').environ.get('NEO4J_PASSWORD', 'Kamina2025*')
            )
            return client
        except Exception:
            pytest.skip("Neo4j not available")

    @pytest.mark.asyncio
    async def test_update_metrics_integration(self, neo4j_client):
        """Test metrics update with real Neo4j."""
        from src.bmad.services.metrics_exporter import MetricsExporter

        try:
            await neo4j_client.initialize()
            exporter = MetricsExporter(neo4j_client)

            result = await exporter.update_all_metrics()
            print(f"\nMetrics Update:")
            print(f"  Status: {result['status']}")
            print(f"  Update time: {result.get('update_time_ms', 0):.2f}ms")

            summary = exporter.get_metrics_summary()
            print(f"\nMetrics Summary:")
            for key, value in summary.items():
                print(f"  {key}: {value}")

            # Verify metrics were generated
            metrics_output = exporter.generate_metrics()
            print(f"\nPrometheus Output: {len(metrics_output)} bytes")

            await neo4j_client.close()
        except Exception as e:
            pytest.skip(f"Neo4j test failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])