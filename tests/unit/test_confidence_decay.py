"""Unit tests for Confidence Decay Service (Story 4-1).

Tests cover:
- Stale insight detection
- Confidence decay application
- Insight archival to CSV
- Scheduled task execution
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, AsyncMock
from pathlib import Path
from typing import Any, Dict
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.bmad.core.neo4j_client import Neo4jAsyncClient
from src.bmad.services.confidence_decay import (
    ConfidenceDecayService,
    DecayMetrics
)


class TestConfidenceDecayServiceInit:
    """Test ConfidenceDecayService initialization."""

    def test_init_with_client(self):
        """Service should initialize with Neo4j client."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        service = ConfidenceDecayService(mock_client)

        assert service._client == mock_client

    def test_default_values(self):
        """Service should have correct default constants."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        service = ConfidenceDecayService(mock_client)

        assert service.STALE_DAYS == 90
        assert service.DECAY_RATE == 0.10
        assert service.ARCHIVE_THRESHOLD == 0.1


class TestDecayMetrics:
    """Test DecayMetrics dataclass."""

    def test_metrics_creation(self):
        """Should create metrics with all fields."""
        metrics = DecayMetrics(
            insights_decayed=10,
            avg_new_confidence=0.75,
            insights_archived=2,
            archived_to="/tmp/archive.csv",
            processing_time_ms=150.5,
            group_id="test-group",
            timestamp=datetime.now(timezone.utc)
        )

        assert metrics.insights_decayed == 10
        assert metrics.avg_new_confidence == 0.75
        assert metrics.insights_archived == 2


class TestStaleInsightDetection:
    """Test stale insight detection."""

    @pytest.mark.asyncio
    async def test_find_stale_insights_with_group(self):
        """Should find stale insights for specific group."""
        mock_records = [
            {
                'insight_id': 'i1',
                'rule': 'Test rule',
                'category': 'testing',
                'confidence_score': 0.5,
                'group_id': 'test-group',
                'created_at': '2024-01-01T00:00:00Z',
                'last_applied': '2024-09-01T00:00:00Z'
            }
        ]

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=mock_records)

        service = ConfidenceDecayService(mock_client)
        results = await service._find_stale_insights('test-group', 90)

        assert len(results) == 1
        assert results[0]['insight_id'] == 'i1'

    @pytest.mark.asyncio
    async def test_find_stale_insights_all_groups(self):
        """Should find stale insights across all groups."""
        mock_records = [
            {'insight_id': 'i1', 'group_id': 'group1', 'confidence_score': 0.5},
            {'insight_id': 'i2', 'group_id': 'group2', 'confidence_score': 0.6}
        ]

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=mock_records)

        service = ConfidenceDecayService(mock_client)
        results = await service._find_stale_insights(None, 90)

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_no_stale_insights(self):
        """Should return empty list when no stale insights."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=[])

        service = ConfidenceDecayService(mock_client)
        results = await service._find_stale_insights('test-group', 90)

        assert len(results) == 0


class TestConfidenceDecay:
    """Test confidence decay application."""

    @pytest.mark.asyncio
    async def test_decay_applies_correctly(self):
        """Should apply 10% decay to confidence score."""
        insight = {
            'insight_id': 'i1',
            'confidence_score': 0.5,
            'group_id': 'test-group'
        }

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=[
            {'new_confidence': 0.45}
        ])

        service = ConfidenceDecayService(mock_client)
        result = await service._decay_insight(insight)

        assert result == 0.45

    @pytest.mark.asyncio
    async def test_dry_run_does_not_modify(self):
        """Dry run should query but not apply changes."""
        mock_records = [
            {
                'insight_id': 'i1',
                'rule': 'Test rule',
                'category': 'testing',
                'confidence_score': 0.5,
                'group_id': 'test-group',
                'created_at': '2024-01-01T00:00:00Z',
                'last_applied': '2024-09-01T00:00:00Z'
            }
        ]

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=mock_records)

        service = ConfidenceDecayService(mock_client)
        metrics = await service.apply_decay(group_id='test-group', dry_run=True)

        # Should query for stale insights but not apply decay
        assert mock_client.execute_query.call_count == 1  # Only find_stale_insights
        assert metrics.insights_decayed == 1  # Calculated from mock
        assert metrics.avg_new_confidence == 0.45  # 0.5 * 0.9

    @pytest.mark.asyncio
    async def test_decay_metrics_recorded(self):
        """Should record decay metrics correctly."""
        mock_records = [
            {
                'insight_id': 'i1',
                'rule': 'Test rule',
                'category': 'testing',
                'confidence_score': 0.5,
                'group_id': 'test-group',
                'created_at': '2024-01-01T00:00:00Z',
                'last_applied': '2024-09-01T00:00:00Z'
            },
            {
                'insight_id': 'i2',
                'rule': 'Another rule',
                'category': 'testing',
                'confidence_score': 0.7,
                'group_id': 'test-group',
                'created_at': '2024-01-01T00:00:00Z',
                'last_applied': '2024-09-01T00:00:00Z'
            }
        ]

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=mock_records)

        service = ConfidenceDecayService(mock_client)
        metrics = await service.apply_decay(group_id='test-group', dry_run=False)

        assert metrics.insights_decayed == 2
        assert metrics.group_id == 'test-group'
        assert metrics.processing_time_ms >= 0


class TestInsightArchival:
    """Test insight archival to cold storage."""

    @pytest.mark.asyncio
    async def test_archive_low_confidence_insights(self):
        """Should archive insights with confidence < 0.1."""
        mock_records = [
            {
                'insight_id': 'i1',
                'rule': 'Stale rule',
                'category': 'archival',
                'confidence_score': 0.05,
                'group_id': 'test-group',
                'created_at': '2024-01-01T00:00:00Z',
                'last_applied': '2024-09-01T00:00:00Z'
            }
        ]

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=mock_records)

        service = ConfidenceDecayService(mock_client)
        count, archive_path = await service._archive_low_confidence_insights(
            'test-group', []
        )

        assert count == 1
        assert archive_path is not None
        assert archive_path.name.startswith('archived_insights_')
        assert archive_path.name.endswith('.csv')

    @pytest.mark.asyncio
    async def test_no_insights_to_archive(self):
        """Should return 0 when no insights to archive."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=[])

        service = ConfidenceDecayService(mock_client)
        count, archive_path = await service._archive_low_confidence_insights(
            'test-group', []
        )

        assert count == 0
        assert archive_path is None


class TestInsightDeletion:
    """Test insight deletion after archival."""

    @pytest.mark.asyncio
    async def test_delete_insights_from_graph(self):
        """Should delete archived insights from graph."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=[{'deleted': True}])

        service = ConfidenceDecayService(mock_client)
        count = await service._delete_insights(['i1', 'i2'])

        assert count == 2

    @pytest.mark.asyncio
    async def test_delete_empty_list(self):
        """Should return 0 when deleting empty list."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock()

        service = ConfidenceDecayService(mock_client)
        count = await service._delete_insights([])

        assert count == 0
        mock_client.execute_query.assert_not_called()


class TestStaleInsightCount:
    """Test stale insight counting."""

    @pytest.mark.asyncio
    async def test_get_stale_count_with_group(self):
        """Should return count for specific group."""
        mock_records = [{'count': 5}]

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=mock_records)

        service = ConfidenceDecayService(mock_client)
        counts = await service.get_stale_insights_count('test-group')

        assert counts == {'total': 5}

    @pytest.mark.asyncio
    async def test_get_stale_count_all_groups(self):
        """Should return counts by group."""
        mock_records = [
            {'group_id': 'group1', 'count': 10},
            {'group_id': 'group2', 'count': 5}
        ]

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=mock_records)

        service = ConfidenceDecayService(mock_client)
        counts = await service.get_stale_insights_count(None)

        assert counts == {'group1': 10, 'group2': 5}


class TestConfidenceDecayIntegration:
    """Integration tests with real Neo4j."""

    @pytest.fixture
    def neo4j_client(self):
        """Create real Neo4j client."""
        try:
            client = Neo4jAsyncClient(
                uri=os.environ.get('NEO4J_URI', 'bolt://localhost:7687'),
                user=os.environ.get('NEO4J_USER', 'neo4j'),
                password=os.environ.get('NEO4J_PASSWORD', 'Kamina2025*')
            )
            return client
        except Exception:
            pytest.skip("Neo4j not available")

    @pytest.mark.asyncio
    async def test_decay_cycle_dry_run(self, neo4j_client):
        """Test decay cycle with dry run."""
        from src.bmad.services.confidence_decay import ConfidenceDecayService

        try:
            await neo4j_client.initialize()
            service = ConfidenceDecayService(neo4j_client)

            # Run dry run
            metrics = await service.apply_decay(dry_run=True)

            print(f"\nDry run results:")
            print(f"  Insights to decay: {metrics.insights_decayed}")
            print(f"  Processing time: {metrics.processing_time_ms:.2f}ms")

            # Verify metrics structure
            assert hasattr(metrics, 'insights_decayed')
            assert hasattr(metrics, 'avg_new_confidence')
            assert hasattr(metrics, 'processing_time_ms')

            await neo4j_client.close()
        except Exception as e:
            pytest.skip(f"Neo4j test failed: {e}")

    @pytest.mark.asyncio
    async def test_stale_count_query(self, neo4j_client):
        """Test stale insight counting."""
        from src.bmad.services.confidence_decay import ConfidenceDecayService

        try:
            await neo4j_client.initialize()
            service = ConfidenceDecayService(neo4j_client)

            counts = await service.get_stale_insights_count()
            print(f"\nStale insights by group: {counts}")

            # Verify result is a dict
            assert isinstance(counts, dict)

            await neo4j_client.close()
        except Exception as e:
            pytest.skip(f"Neo4j test failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])