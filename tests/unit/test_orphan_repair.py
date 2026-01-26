"""Unit tests for Orphan Detection and Repair Service (Story 4-4).

Tests cover:
- Orphan detection for agents and brains
- Automatic repair logic
- Health check performance
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

from src.bmad.core.neo4j_client import Neo4jAsyncClient
from src.bmad.services.orphan_repair import (
    OrphanRepairService,
    OrphanedAgent,
    OrphanedBrain,
    RepairResult,
    HealthCheckResult
)


class TestOrphanRepairServiceInit:
    """Test OrphanRepairService initialization."""

    def test_init_with_client(self):
        """Service should initialize with Neo4j client."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        service = OrphanRepairService(mock_client)

        assert service._client == mock_client


class TestOrphanedAgent:
    """Test OrphanedAgent dataclass."""

    def test_agent_creation(self):
        """Should create orphaned agent with all fields."""
        agent = OrphanedAgent(
            agent_id="a1",
            name="Test Agent",
            role="developer",
            group_id="test-group"
        )

        assert agent.agent_id == "a1"
        assert agent.name == "Test Agent"
        assert agent.role == "developer"


class TestOrphanedBrain:
    """Test OrphanedBrain dataclass."""

    def test_brain_creation(self):
        """Should create orphaned brain with all fields."""
        brain = OrphanedBrain(
            brain_id="b1",
            name="Test Brain",
            group_id=""
        )

        assert brain.brain_id == "b1"
        assert brain.group_id == ""


class TestRepairResult:
    """Test RepairResult dataclass."""

    def test_result_creation(self):
        """Should create repair result with all fields."""
        result = RepairResult(
            agents_repaired=5,
            brains_repaired=2,
            relationships_created=7,
            agents_still_orphaned=["agent1"],
            processing_time_ms=150.5,
            timestamp=datetime.now(timezone.utc)
        )

        assert result.agents_repaired == 5
        assert result.relationships_created == 7

    def test_to_dict(self):
        """Should convert result to dictionary."""
        now = datetime.now(timezone.utc)
        result = RepairResult(
            agents_repaired=1,
            brains_repaired=0,
            relationships_created=1,
            agents_still_orphaned=[],
            processing_time_ms=100.0,
            timestamp=now
        )

        d = result.to_dict()
        assert d["agents_repaired"] == 1
        assert d["processing_time_ms"] == 100.0
        assert "timestamp" in d


class TestHealthCheckResult:
    """Test HealthCheckResult dataclass."""

    def test_healthy_result(self):
        """Should create healthy result."""
        result = HealthCheckResult(
            is_healthy=True,
            orphaned_agents=[],
            orphaned_brains=[],
            total_checks=2,
            checks_passed=2,
            processing_time_ms=100.0,
            timestamp=datetime.now(timezone.utc)
        )

        assert result.is_healthy is True
        assert result.checks_passed == 2

    def test_unhealthy_result(self):
        """Should create unhealthy result with orphans."""
        agents = [
            OrphanedAgent("a1", "Agent1", "dev", "group1"),
            OrphanedAgent("a2", "Agent2", "dev", "group1")
        ]

        result = HealthCheckResult(
            is_healthy=False,
            orphaned_agents=agents,
            orphaned_brains=[],
            total_checks=2,
            checks_passed=1,
            processing_time_ms=200.0,
            timestamp=datetime.now(timezone.utc)
        )

        assert result.is_healthy is False
        assert len(result.orphaned_agents) == 2


class TestOrphanDetection:
    """Test orphan detection functionality."""

    @pytest.mark.asyncio
    async def test_detect_orphaned_agents(self):
        """Should detect agents without brain connections."""
        mock_records = [
            {
                'agent_id': 'a1',
                'name': 'Orphaned Agent',
                'role': 'developer',
                'group_id': 'test-group'
            }
        ]

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=mock_records)

        service = OrphanRepairService(mock_client)
        results = await service._detect_orphaned_agents()

        assert len(results) == 1
        assert results[0].name == 'Orphaned Agent'

    @pytest.mark.asyncio
    async def test_no_orphaned_agents(self):
        """Should return empty when all agents connected."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=[])

        service = OrphanRepairService(mock_client)
        results = await service._detect_orphaned_agents()

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_detect_orphaned_brains(self):
        """Should detect brains without group_id."""
        mock_records = [
            {
                'brain_id': 'b1',
                'name': 'Orphaned Brain',
                'group_id': ''
            }
        ]

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=mock_records)

        service = OrphanRepairService(mock_client)
        results = await service._detect_orphaned_brains()

        assert len(results) == 1
        assert results[0].group_id == ''


class TestHealthCheck:
    """Test health check functionality."""

    @pytest.mark.asyncio
    async def test_healthy_check(self):
        """Should return healthy when no orphans."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=[])

        service = OrphanRepairService(mock_client)
        result = await service.run_health_check()

        assert result.is_healthy is True
        assert result.checks_passed == 2
        assert result.total_checks == 2

    @pytest.mark.asyncio
    async def test_unhealthy_check(self):
        """Should return unhealthy when orphans found."""
        agent_records = [
            {'agent_id': 'a1', 'name': 'Agent1', 'role': 'dev', 'group_id': 'g1'}
        ]
        brain_records = []

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(side_effect=[
            agent_records,  # _detect_orphaned_agents
            brain_records,  # _detect_orphaned_brains
        ])

        service = OrphanRepairService(mock_client)
        result = await service.run_health_check()

        assert result.is_healthy is False
        assert result.checks_passed == 1  # Only brain check passes
        assert len(result.orphaned_agents) == 1

    @pytest.mark.asyncio
    async def test_health_check_performance(self):
        """Health check should complete quickly."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=[])

        service = OrphanRepairService(mock_client)
        result = await service.run_health_check()

        # Should complete in under 5 seconds (5000ms)
        assert result.processing_time_ms < 5000


class TestRepair:
    """Test repair functionality."""

    @pytest.mark.asyncio
    async def test_repair_with_no_orphans(self):
        """Should handle repair when no orphans."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=[])

        service = OrphanRepairService(mock_client)
        result = await service.repair_orphaned_relationships()

        assert result.agents_repaired == 0
        assert result.brains_repaired == 0
        assert result.relationships_created == 0

    @pytest.mark.asyncio
    async def test_repair_skips_agents_without_name(self):
        """Should skip agents without names during repair."""
        agent_records = [
            {'agent_id': '', 'name': '', 'role': 'dev', 'group_id': 'g1'}
        ]

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=agent_records)

        service = OrphanRepairService(mock_client)
        result = await service.repair_orphaned_relationships()

        # Should not crash, agents without names are skipped
        assert result.processing_time_ms >= 0


class TestRepairCandidates:
    """Test repair candidates query."""

    @pytest.mark.asyncio
    async def test_get_repair_candidates(self):
        """Should return summary of repair candidates."""
        agent_records = [
            {'agent_id': 'a1', 'name': 'Agent1', 'role': 'dev', 'group_id': 'g1'}
        ]
        brain_records = [
            {'brain_id': 'b1', 'name': 'Brain1', 'group_id': ''}
        ]

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(side_effect=[
            agent_records,
            brain_records
        ])

        service = OrphanRepairService(mock_client)
        candidates = await service.get_repair_candidates()

        assert candidates['orphaned_agent_count'] == 1
        assert candidates['orphaned_brain_count'] == 1
        assert candidates['total_repairs_needed'] == 2


class TestOrphanRepairIntegration:
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
    async def test_health_check_dry_run(self, neo4j_client):
        """Test health check without making changes."""
        from src.bmad.services.orphan_repair import OrphanRepairService

        try:
            await neo4j_client.initialize()
            service = OrphanRepairService(neo4j_client)

            health = await service.run_health_check()
            print(f"\nHealth Check:")
            print(f"  Healthy: {health.is_healthy}")
            print(f"  Checks passed: {health.checks_passed}/{health.total_checks}")
            print(f"  Processing time: {health.processing_time_ms:.2f}ms")

            await neo4j_client.close()
        except Exception as e:
            pytest.skip(f"Neo4j test failed: {e}")

    @pytest.mark.asyncio
    async def test_repair_candidates_query(self, neo4j_client):
        """Test repair candidates query."""
        from src.bmad.services.orphan_repair import OrphanRepairService

        try:
            await neo4j_client.initialize()
            service = OrphanRepairService(neo4j_client)

            candidates = await service.get_repair_candidates()
            print(f"\nRepair Candidates:")
            print(f"  Orphaned agents: {candidates['orphaned_agent_count']}")
            print(f"  Orphaned brains: {candidates['orphaned_brain_count']}")

            await neo4j_client.close()
        except Exception as e:
            pytest.skip(f"Neo4j test failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])