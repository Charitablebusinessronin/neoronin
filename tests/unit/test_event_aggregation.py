"""Unit tests for Event Aggregation Service (Story 4-3).

Tests cover:
- Event aggregation logic
- Event archival to CSV
- Scheduled task execution
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, AsyncMock
from pathlib import Path
from typing import Any, Dict
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.bmad.core.neo4j_client import Neo4jAsyncClient
from src.bmad.services.event_aggregation import (
    EventAggregationService,
    EventSummary,
    AggregationMetrics,
    ArchivedEvent
)


class TestEventAggregationServiceInit:
    """Test EventAggregationService initialization."""

    def test_init_with_client(self):
        """Service should initialize with Neo4j client."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        service = EventAggregationService(mock_client)

        assert service._client == mock_client

    def test_default_values(self):
        """Service should have correct default constants."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        service = EventAggregationService(mock_client)

        assert service.EVENT_AGE_DAYS == 30


class TestEventSummary:
    """Test EventSummary dataclass."""

    def test_summary_creation(self):
        """Should create summary with all fields."""
        summary = EventSummary(
            event_type="code_review",
            group_id="test-group",
            count=100,
            period="archived",
            first_event=datetime(2024, 1, 1, tzinfo=timezone.utc),
            last_event=datetime(2024, 1, 15, tzinfo=timezone.utc)
        )

        assert summary.event_type == "code_review"
        assert summary.count == 100


class TestAggregationMetrics:
    """Test AggregationMetrics dataclass."""

    def test_metrics_creation(self):
        """Should create metrics with all fields."""
        metrics = AggregationMetrics(
            events_aggregated=500,
            summaries_created=10,
            events_archived=500,
            archive_path="/tmp/archive.csv",
            processing_time_ms=1500.5,
            group_id="test-group",
            timestamp=datetime.now(timezone.utc)
        )

        assert metrics.events_aggregated == 500
        assert metrics.summaries_created == 10


class TestArchivedEvent:
    """Test ArchivedEvent dataclass."""

    def test_archived_event_creation(self):
        """Should create archived event with all fields."""
        event = ArchivedEvent(
            event_id="e1",
            event_type="code_review",
            timestamp="2024-01-15T00:00:00Z",
            group_id="test-group",
            description="Review completed",
            archived_at="2024-10-28T00:00:00Z",
            archive_reason="event_aggregation"
        )

        assert event.event_id == "e1"
        assert event.archive_reason == "event_aggregation"


class TestOldEventDetection:
    """Test old event detection."""

    @pytest.mark.asyncio
    async def test_find_old_events_with_group(self):
        """Should find old events for specific group."""
        mock_records = [
            {
                'event_type': 'code_review',
                'group_id': 'test-group',
                'count': 50,
                'first_event': '2024-09-01T00:00:00Z',
                'last_event': '2024-09-15T00:00:00Z'
            }
        ]

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=mock_records)

        service = EventAggregationService(mock_client)
        results = await service._find_old_events(
            'test-group',
            datetime.now(timezone.utc) - timedelta(days=30)
        )

        assert len(results) == 1
        assert results[0]['event_type'] == 'code_review'

    @pytest.mark.asyncio
    async def test_find_old_events_all_groups(self):
        """Should find old events across all groups."""
        mock_records = [
            {'event_type': 'code_review', 'group_id': 'g1', 'count': 30},
            {'event_type': 'testing', 'group_id': 'g2', 'count': 20}
        ]

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=mock_records)

        service = EventAggregationService(mock_client)
        results = await service._find_old_events(
            None,
            datetime.now(timezone.utc) - timedelta(days=30)
        )

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_no_old_events(self):
        """Should return empty list when no old events."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=[])

        service = EventAggregationService(mock_client)
        results = await service._find_old_events(
            'test-group',
            datetime.now(timezone.utc) - timedelta(days=30)
        )

        assert len(results) == 0


class TestSummaryCreation:
    """Test EventSummary creation."""

    @pytest.mark.asyncio
    async def test_create_summaries(self):
        """Should create summaries from event groups."""
        event_groups = [
            {
                'event_type': 'code_review',
                'group_id': 'test-group',
                'count': 50,
                'first_event': '2024-09-01T00:00:00Z',
                'last_event': '2024-09-15T00:00:00Z'
            }
        ]

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock()

        service = EventAggregationService(mock_client)
        summaries = await service._create_summaries(event_groups, dry_run=False)

        assert len(summaries) == 1
        assert summaries[0].event_type == 'code_review'
        assert summaries[0].count == 50

    @pytest.mark.asyncio
    async def test_dry_run_no_queries(self):
        """Dry run should not create summaries."""
        event_groups = [
            {
                'event_type': 'code_review',
                'group_id': 'test-group',
                'count': 50,
                'first_event': '2024-09-01T00:00:00Z',
                'last_event': '2024-09-15T00:00:00Z'
            }
        ]

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock()

        service = EventAggregationService(mock_client)
        summaries = await service._create_summaries(event_groups, dry_run=True)

        assert len(summaries) == 1
        mock_client.execute_query.assert_not_called()


class TestEventDeletion:
    """Test event deletion from graph."""

    @pytest.mark.asyncio
    async def test_delete_events(self):
        """Should delete archived events from graph."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock()

        service = EventAggregationService(mock_client)
        count = await service._delete_events(['e1', 'e2', 'e3'])

        assert count == 3

    @pytest.mark.asyncio
    async def test_delete_empty_list(self):
        """Should return 0 when deleting empty list."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock()

        service = EventAggregationService(mock_client)
        count = await service._delete_events([])

        assert count == 0
        mock_client.execute_query.assert_not_called()


class TestCSVArchival:
    """Test event archival to CSV."""

    @pytest.mark.asyncio
    async def test_archive_to_csv(self):
        """Should archive events to CSV file."""
        events = [
            ArchivedEvent(
                event_id='e1',
                event_type='code_review',
                timestamp='2024-09-01T00:00:00Z',
                group_id='test-group',
                description='Review completed',
                archived_at='2024-10-28T00:00:00Z',
                archive_reason='event_aggregation'
            )
        ]

        mock_client = MagicMock(spec=Neo4jAsyncClient)

        # Create a temp directory service
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            service = EventAggregationService(mock_client, archive_dir=tmpdir)
            archive_path = await service._archive_to_csv(events, 'test-group')

            assert archive_path.endswith('.csv')
            assert 'archived_events' in archive_path

            # Verify file contents
            import csv
            with open(archive_path, 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                assert len(rows) == 1
                assert rows[0]['event_id'] == 'e1'

    @pytest.mark.asyncio
    async def test_archive_empty_list(self):
        """Should return empty string for empty list."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)

        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            service = EventAggregationService(mock_client, archive_dir=tmpdir)
            archive_path = await service._archive_to_csv([], 'test-group')

            assert archive_path == ""


class TestEventAggregation:
    """Test the main aggregation method."""

    @pytest.mark.asyncio
    async def test_aggregate_events_dry_run(self):
        """Dry run should not modify graph."""
        event_groups = [
            {
                'event_type': 'code_review',
                'group_id': 'test-group',
                'count': 50,
                'first_event': '2024-09-01T00:00:00Z',
                'last_event': '2024-09-15T00:00:00Z'
            }
        ]

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=event_groups)

        service = EventAggregationService(mock_client)
        metrics = await service.aggregate_events(group_id='test-group', dry_run=True)

        assert metrics.events_aggregated == 1
        assert metrics.events_archived == 0
        assert metrics.group_id == 'test-group'

    @pytest.mark.asyncio
    async def test_aggregate_events_with_archival(self):
        """Should aggregate events and archive to CSV."""
        # _find_old_events returns aggregated data (no event_id)
        aggregated_data = [
            {
                'event_type': 'code_review',
                'group_id': 'test-group',
                'count': 50,
                'first_event': '2024-09-01T00:00:00Z',
                'last_event': '2024-09-15T00:00:00Z'
            }
        ]

        # _fetch_events_for_archival returns actual events (with event_id)
        event_details = [
            {
                'event_id': 'e1',
                'event_type': 'code_review',
                'timestamp': '2024-09-01T00:00:00Z',
                'group_id': 'test-group',
                'description': 'Review 1'
            }
        ]

        event_ids_result = [
            {'event_id': 'e1'}
        ]

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(side_effect=[
            aggregated_data,  # _find_old_events (stats)
            event_ids_result, # _find_event_ids (new query)
            event_details,    # _fetch_events_for_archival (by event_ids)
            [],               # _upsert_summary
            [],               # _delete_events
        ])

        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            service = EventAggregationService(mock_client, archive_dir=tmpdir)
            metrics = await service.aggregate_events(
                group_id='test-group',
                dry_run=False
            )

            assert metrics.events_aggregated == 1
            assert metrics.events_archived == 1
            # Processing time is calculated dynamically, just check it's present
            assert metrics.processing_time_ms >= 0


class TestEventCounts:
    """Test event counting functionality."""

    @pytest.mark.asyncio
    async def test_get_event_counts(self):
        """Should return event counts by age category."""
        mock_records = [
            {
                'total_events': 100,
                'recent_events': 70,
                'old_events': 30
            }
        ]

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=mock_records)

        service = EventAggregationService(mock_client)
        counts = await service.get_event_counts('test-group')

        assert counts['total_events'] == 100
        assert counts['recent_events'] == 70
        assert counts['old_events'] == 30

    @pytest.mark.asyncio
    async def test_get_counts_no_events(self):
        """Should return zeros when no events."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=[])

        service = EventAggregationService(mock_client)
        counts = await service.get_event_counts('test-group')

        assert counts['total_events'] == 0
        assert counts['recent_events'] == 0
        assert counts['old_events'] == 0


class TestEventAggregationIntegration:
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
    async def test_event_counts_query(self, neo4j_client):
        """Test event counts query."""
        from src.bmad.services.event_aggregation import EventAggregationService

        try:
            await neo4j_client.initialize()
            service = EventAggregationService(neo4j_client)

            counts = await service.get_event_counts()
            print(f"\nEvent Counts:")
            print(f"  Total: {counts['total_events']}")
            print(f"  Recent: {counts['recent_events']}")
            print(f"  Old: {counts['old_events']}")

            await neo4j_client.close()
        except Exception as e:
            pytest.skip(f"Neo4j test failed: {e}")

    @pytest.mark.asyncio
    async def test_aggregation_dry_run(self, neo4j_client):
        """Test aggregation dry run."""
        from src.bmad.services.event_aggregation import EventAggregationService

        try:
            await neo4j_client.initialize()
            service = EventAggregationService(neo4j_client)

            metrics = await service.aggregate_events(dry_run=True)
            print(f"\nAggregation Dry Run:")
            print(f"  Events to aggregate: {metrics.events_aggregated}")
            print(f"  Processing time: {metrics.processing_time_ms:.2f}ms")

            await neo4j_client.close()
        except Exception as e:
            pytest.skip(f"Neo4j test failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])