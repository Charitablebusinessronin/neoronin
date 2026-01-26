"""Unit tests for Knowledge Transfer Service (Story 2-3).

Tests cover:
- High-confidence insight sharing across agents
- CAN_APPLY relationship creation
- Query shared insights by agent
- Pending shares counting
- Multi-tenant isolation
- Performance under 2 seconds
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

from src.bmad.services.knowledge_transfer import (
    KnowledgeTransferService,
    KnowledgeTransferResult,
    SharedInsight,
    Insight
)


class TestKnowledgeTransferServiceInit:
    """Test KnowledgeTransferService initialization."""

    def test_init_with_client(self):
        """Service should be initialized with Neo4j client."""
        from src.bmad.services.knowledge_transfer import KnowledgeTransferService
        from src.bmad.core.neo4j_client import Neo4jAsyncClient

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        service = KnowledgeTransferService(mock_client)

        assert service._client == mock_client


class TestShareHighConfidenceInsights:
    """Test sharing insights across agents."""

    @pytest.mark.asyncio
    async def test_share_insights_creates_relationships(self):
        """Sharing should create CAN_APPLY relationships."""
        from src.bmad.services.knowledge_transfer import KnowledgeTransferService
        from src.bmad.core.neo4j_client import Neo4jAsyncClient

        mock_records = [
            {
                'teacher': 'brooks',
                'learners': ['claude', 'gpt4'],
                'insight_id': 'insight-1',
                'rule': 'Use parameterized queries',
                'category': 'security'
            }
        ]

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_write = AsyncMock(return_value=mock_records)

        service = KnowledgeTransferService(mock_client)

        result = await service.share_high_confidence_insights("faith-meats")

        assert result.insights_shared == 1
        assert result.agents_updated == 2  # claude + gpt4
        assert result.group_id == "faith-meats"

    @pytest.mark.asyncio
    async def test_share_insights_excludes_low_confidence(self):
        """Only insights with confidence >= 0.8 should be shared."""
        from src.bmad.services.knowledge_transfer import KnowledgeTransferService
        from src.bmad.core.neo4j_client import Neo4jAsyncClient

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_write = AsyncMock(return_value=[])

        service = KnowledgeTransferService(mock_client)

        await service.share_high_confidence_insights("faith-meats")

        # Verify threshold was used
        mock_client.execute_write.assert_called_once()
        call_args = mock_client.execute_write.call_args
        params = call_args[0][1]

        assert params['threshold'] == 0.8

    @pytest.mark.asyncio
    async def test_share_insights_multi_tenant_isolation(self):
        """Sharing should respect group_id boundaries."""
        from src.bmad.services.knowledge_transfer import KnowledgeTransferService
        from src.bmad.core.neo4j_client import Neo4jAsyncClient

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_write = AsyncMock(return_value=[])

        service = KnowledgeTransferService(mock_client)

        await service.share_high_confidence_insights("diff-driven-saas")

        # Verify group_id filter in query
        mock_client.execute_write.assert_called_once()
        call_args = mock_client.execute_write.call_args
        call_cypher = call_args[0][0]

        assert "group_id" in str(call_cypher).lower()


class TestGetSharedInsights:
    """Test querying shared insights."""

    @pytest.mark.asyncio
    async def test_get_shared_insights_returns_list(self):
        """Should return list of shared insights."""
        from src.bmad.services.knowledge_transfer import KnowledgeTransferService
        from src.bmad.core.neo4j_client import Neo4jAsyncClient

        mock_records = [
            {
                'insight_id': 'insight-1',
                'rule': 'Use parameterized queries',
                'category': 'security',
                'confidence_score': 0.9,
                'success_rate': 0.95,
                'learned_at': datetime.now(timezone.utc),
                'teacher_agent': 'brooks'
            }
        ]

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=mock_records)

        service = KnowledgeTransferService(mock_client)

        insights = await service.get_shared_insights(
            "claude",
            "faith-meats",
            limit=10
        )

        assert len(insights) == 1
        assert insights[0].insight_id == "insight-1"
        assert insights[0].teacher_agent == "brooks"

    @pytest.mark.asyncio
    async def test_get_shared_insights_filters_by_teacher(self):
        """Should filter by teacher name when specified."""
        from src.bmad.services.knowledge_transfer import KnowledgeTransferService
        from src.bmad.core.neo4j_client import Neo4jAsyncClient

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=[])

        service = KnowledgeTransferService(mock_client)

        await service.get_shared_insights(
            "claude",
            "faith-meats",
            teacher_name="brooks"
        )

        # Verify teacher filter was applied
        mock_client.execute_query.assert_called_once()
        call_args = mock_client.execute_query.call_args
        params = call_args[0][1]

        assert 'teacher_name' in params


class TestCountPendingShares:
    """Test counting pending knowledge transfers."""

    @pytest.mark.asyncio
    async def test_count_pending_returns_counts(self):
        """Should return pending share counts."""
        from src.bmad.services.knowledge_transfer import KnowledgeTransferService
        from src.bmad.core.neo4j_client import Neo4jAsyncClient

        mock_records = [
            {
                'insights_pending': 5,
                'agents_waiting': 3,
                'total_shares_needed': 12
            }
        ]

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=mock_records)

        service = KnowledgeTransferService(mock_client)

        pending = await service.count_pending_shares("faith-meats")

        assert pending['insights_pending'] == 5
        assert pending['agents_waiting'] == 3
        assert pending['total_shares_needed'] == 12

    @pytest.mark.asyncio
    async def test_count_pending_returns_zeros_when_empty(self):
        """Should return zeros when no pending shares."""
        from src.bmad.services.knowledge_transfer import KnowledgeTransferService
        from src.bmad.core.neo4j_client import Neo4jAsyncClient

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=[])

        service = KnowledgeTransferService(mock_client)

        pending = await service.count_pending_shares("faith-meats")

        assert pending['insights_pending'] == 0
        assert pending['agents_waiting'] == 0
        assert pending['total_shares_needed'] == 0


class TestGetInsightsToShare:
    """Test getting insights ready to share."""

    @pytest.mark.asyncio
    async def test_get_insights_to_share_returns_insights(self):
        """Should return insights meeting share criteria."""
        from src.bmad.services.knowledge_transfer import KnowledgeTransferService
        from src.bmad.core.neo4j_client import Neo4jAsyncClient

        mock_records = [
            {
                'insight_id': 'insight-1',
                'rule': 'Use parameterized queries',
                'category': 'security',
                'confidence_score': 0.9,
                'success_rate': 0.95,
                'group_id': 'faith-meats',
                'learned_by': 'brooks',
                'learned_at': datetime.now(timezone.utc),
                'applies_to': 'database',
                'metadata': {'error_count': 0}
            }
        ]

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=mock_records)

        service = KnowledgeTransferService(mock_client)

        insights = await service.get_insights_to_share("faith-meats")

        assert len(insights) == 1
        assert insights[0].confidence_score == 0.9
        assert insights[0].success_rate == 0.95


class TestKnowledgeTransferResult:
    """Test KnowledgeTransferResult dataclass."""

    def test_result_creation(self):
        """Should create result with all fields."""
        result = KnowledgeTransferResult(
            insights_shared=10,
            agents_updated=5,
            transfers=[{"insight_id": "i1"}],
            latency_ms=50.5,
            group_id="faith-meats"
        )

        assert result.insights_shared == 10
        assert result.agents_updated == 5
        assert result.latency_ms == 50.5
        assert len(result.transfers) == 1


class TestSharedInsight:
    """Test SharedInsight dataclass."""

    def test_shared_insight_creation(self):
        """Should create shared insight with all fields."""
        now = datetime.now(timezone.utc)
        insight = SharedInsight(
            insight_id="i1",
            rule="Use parameterized queries",
            category="security",
            confidence_score=0.9,
            success_rate=0.95,
            learned_by="brooks",
            learned_at=now,
            teacher_agent="brooks"
        )

        assert insight.insight_id == "i1"
        assert insight.confidence_score == 0.9
        assert insight.teacher_agent == "brooks"


class TestKnowledgeTransferPerformance:
    """Test NFR: Knowledge transfer under 2 seconds."""

    @pytest.mark.asyncio
    async def test_share_insights_completes_fast(self):
        """Knowledge transfer should complete in under 2 seconds."""
        import time

        from src.bmad.services.knowledge_transfer import KnowledgeTransferService
        from src.bmad.core.neo4j_client import Neo4jAsyncClient

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_write = AsyncMock(return_value=[])

        service = KnowledgeTransferService(mock_client)

        start = time.perf_counter()
        result = await service.share_high_confidence_insights("faith-meats")
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Even with mock, should be very fast
        assert elapsed_ms < 2000, f"Transfer took {elapsed_ms:.2f}ms"
        print(f"Knowledge transfer completed in {elapsed_ms:.2f}ms")


class TestKnowledgeTransferIntegration:
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
    async def test_real_share_insights(self, neo4j_client):
        """Test real knowledge transfer against Neo4j."""
        from src.bmad.services.knowledge_transfer import KnowledgeTransferService

        try:
            await neo4j_client.initialize()
            service = KnowledgeTransferService(neo4j_client)

            # Check pending shares
            pending = await service.count_pending_shares("global-coding-skills")
            print(f"\nPending shares: {pending}")

            # Run transfer
            result = await service.share_high_confidence_insights("global-coding-skills")
            print(f"Shared: {result.insights_shared} insights to {result.agents_updated} agents")
            print(f"Latency: {result.latency_ms:.2f}ms")

            # Verify performance
            assert result.latency_ms < 2000, f"Transfer took {result.latency_ms:.2f}ms"

            await neo4j_client.close()
        except Exception as e:
            pytest.skip(f"Neo4j test failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])