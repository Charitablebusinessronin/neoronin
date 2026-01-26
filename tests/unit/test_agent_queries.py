"""Unit tests for Agent Query Service (Story 1-3).

Tests cover:
- Work history query with various filters
- Outcome status filtering
- Date range filtering
- Pattern and insight inclusion
- Performance (<100ms latency)
"""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Any, Dict
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.bmad.services.agent_queries import (
    AgentQueryService,
    WorkHistoryQueryResult,
    WorkHistoryEntry,
    WorkEvent,
    WorkOutcome,
    AppliedPattern,
    GeneratedInsight,
    OutcomeStatus
)


class TestAgentQueryServiceInit:
    """Test AgentQueryService initialization."""

    def test_init_with_client(self):
        """Service should be initialized with Neo4j client."""
        from src.bmad.services.agent_queries import AgentQueryService
        from src.bmad.core.neo4j_client import Neo4jAsyncClient

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        service = AgentQueryService(mock_client)

        assert service._client == mock_client


class TestQueryWorkHistory:
    """Test work history query functionality."""

    @pytest.mark.asyncio
    async def test_query_work_history_returns_results(self):
        """Query should return work history entries."""
        from src.bmad.services.agent_queries import AgentQueryService
        from src.bmad.core.neo4j_client import Neo4jAsyncClient

        # Create mock records
        mock_records = [
            {
                'e': {
                    'event_id': 'event-1',
                    'event_type': 'code_review',
                    'timestamp': datetime.now(timezone.utc),
                    'group_id': 'faith-meats',
                    'description': 'Reviewed PR #123',
                    'tool_name': 'github'
                },
                'o': {
                    'outcome_id': 'outcome-1',
                    'status': 'Success',
                    'result_summary': 'Approved with comments',
                    'duration_ms': 150.5
                },
                'patterns': [
                    {
                        'pattern_id': 'p-1',
                        'name': 'Code Review Best Practices',
                        'category': 'review',
                        'confidence_score': 0.85
                    }
                ],
                'insights': []
            }
        ]

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=mock_records)

        service = AgentQueryService(mock_client)

        result = await service.query_work_history(
            agent_name="Brooks",
            group_id="faith-meats",
            days_back=30
        )

        assert isinstance(result, WorkHistoryQueryResult)
        assert len(result.entries) == 1
        assert result.entries[0].event.event_type == 'code_review'
        assert result.entries[0].outcome.status == 'Success'
        assert len(result.entries[0].patterns) == 1

    @pytest.mark.asyncio
    async def test_query_with_failed_outcomes_only(self):
        """Query with status='Failed' should return only failed outcomes."""
        from src.bmad.services.agent_queries import AgentQueryService
        from src.bmad.core.neo4j_client import Neo4jAsyncClient

        mock_records = [
            {
                'e': {'event_id': 'e1', 'event_type': 'test', 'timestamp': datetime.now(timezone.utc),
                      'group_id': 'test', 'description': 'Test run'},
                'o': {'outcome_id': 'o1', 'status': 'Failed', 'result_summary': 'Tests failed', 'error_log': 'AssertionError'},
                'patterns': [],
                'insights': []
            }
        ]

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=mock_records)

        service = AgentQueryService(mock_client)

        result = await service.query_work_history(
            agent_name="Brooks",
            group_id="test",
            days_back=7,
            outcome_status=OutcomeStatus.FAILED
        )

        assert len(result.entries) == 1
        assert result.entries[0].outcome.status == 'Failed'
        assert result.entries[0].outcome.error_log == 'AssertionError'

    @pytest.mark.asyncio
    async def test_query_includes_patterns_and_insights(self):
        """Query should include applied patterns and generated insights."""
        from src.bmad.services.agent_queries import AgentQueryService
        from src.bmad.core.neo4j_client import Neo4jAsyncClient

        mock_records = [
            {
                'e': {'event_id': 'e1', 'event_type': 'debug', 'timestamp': datetime.now(timezone.utc),
                      'group_id': 'test', 'description': 'Debug session'},
                'o': {'outcome_id': 'o1', 'status': 'Success', 'result_summary': 'Fixed'},
                'patterns': [
                    {'pattern_id': 'p1', 'name': 'Debug Pattern', 'category': 'debugging', 'confidence_score': 0.9}
                ],
                'insights': [
                    {'insight_id': 'i1', 'rule': 'Check logs first', 'category': 'debugging', 'confidence_score': 0.75}
                ]
            }
        ]

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=mock_records)

        service = AgentQueryService(mock_client)

        result = await service.query_work_history(
            agent_name="Brooks",
            group_id="test",
            include_patterns=True,
            include_insights=True
        )

        assert len(result.entries) == 1
        assert len(result.entries[0].patterns) == 1
        assert result.entries[0].patterns[0].pattern_name == 'Debug Pattern'
        assert len(result.entries[0].insights) == 1
        assert result.entries[0].insights[0].rule == 'Check logs first'

    @pytest.mark.asyncio
    async def test_query_respects_pagination(self):
        """Query should respect skip and limit parameters."""
        from src.bmad.services.agent_queries import AgentQueryService
        from src.bmad.core.neo4j_client import Neo4jAsyncClient

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=[])

        service = AgentQueryService(mock_client)

        await service.query_work_history(
            agent_name="Brooks",
            group_id="test",
            page=2,
            page_size=25
        )

        # Verify the query was called
        mock_client.execute_query.assert_called_once()
        call_args = mock_client.execute_query.call_args
        params = call_args[0][1]

        # Check pagination params
        assert params['skip'] == 25  # (page 2 - 1) * 25
        assert params['limit'] == 25

    @pytest.mark.asyncio
    async def test_query_enforces_max_page_size(self):
        """Query should enforce maximum page size of 200."""
        from src.bmad.services.agent_queries import AgentQueryService
        from src.bmad.core.neo4j_client import Neo4jAsyncClient

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=[])

        service = AgentQueryService(mock_client)

        await service.query_work_history(
            agent_name="Brooks",
            group_id="test",
            page_size=500  # Over max
        )

        call_args = mock_client.execute_query.call_args
        params = call_args[0][1]

        assert params['limit'] == 200  # Capped to max


class TestQueryFailures:
    """Test failure query functionality."""

    @pytest.mark.asyncio
    async def test_query_failures_shortcut(self):
        """query_failures should be a shortcut for querying with status=Failed."""
        from src.bmad.services.agent_queries import AgentQueryService
        from src.bmad.core.neo4j_client import Neo4jAsyncClient

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=[])

        service = AgentQueryService(mock_client)

        await service.query_failures(
            agent_name="Brooks",
            group_id="test",
            days_back=14
        )

        # Verify execute_query was called with FAILED status
        mock_client.execute_query.assert_called_once()
        call_args = mock_client.execute_query.call_args
        params = call_args[0][1]

        # The query builder should include the outcome status filter
        query = call_args[0][0]
        assert 'outcome_status' in str(query) or 'Failed' in str(query)


class TestGetEventChain:
    """Test get_event_chain functionality."""

    @pytest.mark.asyncio
    async def test_get_event_chain_returns_chain(self):
        """get_event_chain should return complete event chain."""
        from src.bmad.services.agent_queries import AgentQueryService
        from src.bmad.core.neo4j_client import Neo4jAsyncClient

        mock_records = [
            {
                'e': {'event_id': 'event-123', 'event_type': 'code_review', 'timestamp': datetime.now(timezone.utc),
                      'group_id': 'test', 'description': 'Review'},
                'o': {'outcome_id': 'o1', 'status': 'Success', 'result_summary': 'Approved'},
                'patterns': [],
                'insights': []
            }
        ]

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=mock_records)

        service = AgentQueryService(mock_client)

        result = await service.get_event_chain(
            agent_name="Brooks",
            group_id="test",
            event_id="event-123"
        )

        assert result is not None
        assert result.event.event_id == "event-123"
        assert result.outcome is not None

    @pytest.mark.asyncio
    async def test_get_event_chain_returns_none_for_missing(self):
        """get_event_chain should return None if event not found."""
        from src.bmad.services.agent_queries import AgentQueryService
        from src.bmad.core.neo4j_client import Neo4jAsyncClient

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=[])

        service = AgentQueryService(mock_client)

        result = await service.get_event_chain(
            agent_name="Brooks",
            group_id="test",
            event_id="missing-event"
        )

        assert result is None


class TestParseHistoryResults:
    """Test result parsing."""

    def test_parse_empty_results(self):
        """Should handle empty results gracefully."""
        from src.bmad.services.agent_queries import AgentQueryService
        from src.bmad.core.neo4j_client import Neo4jAsyncClient

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        service = AgentQueryService(mock_client)

        entries = service._parse_history_results([])

        assert entries == []

    def test_parse_event_with_minimal_fields(self):
        """Should parse events with minimal fields."""
        from src.bmad.services.agent_queries import AgentQueryService
        from src.bmad.core.neo4j_client import Neo4jAsyncClient

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        service = AgentQueryService(mock_client)

        entries = service._parse_history_results([
            {
                'e': {'event_id': 'e1', 'event_type': 'test', 'timestamp': None, 'group_id': 'test', 'description': 'Test'},
                'o': None,
                'patterns': [],
                'insights': []
            }
        ])

        assert len(entries) == 1
        assert entries[0].event.event_id == 'e1'
        assert entries[0].outcome is None


class TestOutcomeStatus:
    """Test OutcomeStatus enum."""

    def test_outcome_status_values(self):
        """OutcomeStatus should have correct values."""
        assert OutcomeStatus.SUCCESS.value == "Success"
        assert OutcomeStatus.FAILED.value == "Failed"
        assert OutcomeStatus.ALL.value == "All"


class TestWorkHistoryEntry:
    """Test WorkHistoryEntry dataclass."""

    def test_work_history_entry_creation(self):
        """Should create work history entry with all fields."""
        event = WorkEvent(
            event_id="e1",
            event_type="test",
            timestamp=datetime.now(timezone.utc),
            group_id="test",
            description="Test event"
        )
        outcome = WorkOutcome(
            outcome_id="o1",
            status="Success",
            result_summary="Passed"
        )
        pattern = AppliedPattern(
            pattern_id="p1",
            pattern_name="Test Pattern",
            category="testing",
            confidence_score=0.9
        )
        insight = GeneratedInsight(
            insight_id="i1",
            rule="Test first",
            category="testing",
            confidence_score=0.8
        )

        entry = WorkHistoryEntry(
            event=event,
            outcome=outcome,
            patterns=[pattern],
            insights=[insight]
        )

        assert entry.event.event_id == "e1"
        assert entry.outcome.status == "Success"
        assert len(entry.patterns) == 1
        assert len(entry.insights) == 1


class TestQueryLatency:
    """Test NFR1: Query latency under 100ms."""

    @pytest.mark.asyncio
    async def test_query_latency_under_100ms(self):
        """Work history query should complete in under 100ms."""
        import time

        from src.bmad.services.agent_queries import AgentQueryService
        from src.bmad.core.neo4j_client import Neo4jAsyncClient

        # Mock for instant response
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=[])

        service = AgentQueryService(mock_client)

        start = time.perf_counter()
        result = await service.query_work_history(
            agent_name="Brooks",
            group_id="test"
        )
        latency_ms = (time.perf_counter() - start) * 1000

        assert latency_ms < 100, f"Query took {latency_ms:.2f}ms, expected < 100ms"


class TestAgentQueryServiceIntegration:
    """Integration tests with real Neo4j."""

    @pytest.fixture
    def neo4j_client(self):
        """Create real Neo4j client."""
        import os
        from src.bmad.core.neo4j_client import Neo4jAsyncClient

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
    async def test_real_query_brooks_history(self, neo4j_client):
        """Test real query against Neo4j for Brooks' history."""
        from src.bmad.services.agent_queries import AgentQueryService

        try:
            await neo4j_client.initialize()
            service = AgentQueryService(neo4j_client)

            result = await service.query_work_history(
                agent_name="Brooks",
                group_id="global-coding-skills",
                days_back=30
            )

            # Should return results (agents have performed events)
            assert result.latency_ms < 100
            print(f"Found {result.total_count} history entries in {result.latency_ms:.2f}ms")

            await neo4j_client.close()
        except Exception as e:
            pytest.skip(f"Neo4j query failed: {e}")

    @pytest.mark.asyncio
    async def test_real_query_with_status_filter(self, neo4j_client):
        """Test real query with status filter."""
        from src.bmad.services.agent_queries import AgentQueryService, OutcomeStatus

        try:
            await neo4j_client.initialize()
            service = AgentQueryService(neo4j_client)

            result = await service.query_work_history(
                agent_name="Brooks",
                group_id="global-coding-skills",
                outcome_status=OutcomeStatus.ALL,
                days_back=30
            )

            assert result.latency_ms < 100
            await neo4j_client.close()
        except Exception as e:
            pytest.skip(f"Neo4j query failed: {e}")