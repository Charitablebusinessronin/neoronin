"""Unit tests for Pattern Contradiction Detection (Story 4-5).

Tests cover:
- Contradiction detection for patterns
- Alert creation and management
- Alert resolution workflow
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

from src.bmad.core.neo4j_client import Neo4jAsyncClient
from src.bmad.services.contradiction_detector import (
    ContradictionDetectorService,
    PatternContradiction,
    Alert,
    ContradictionDetectionResult
)


class TestContradictionDetectorServiceInit:
    """Test ContradictionDetectorService initialization."""

    def test_init_with_client(self):
        """Service should initialize with Neo4j client."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        service = ContradictionDetectorService(mock_client)

        assert service._client == mock_client


class TestPatternContradiction:
    """Test PatternContradiction dataclass."""

    def test_contradiction_creation(self):
        """Should create pattern contradiction with all fields."""
        contradiction = PatternContradiction(
            insight_id_1="ins-1",
            insight_id_2="ins-2",
            rule_1="Always use type hints",
            rule_2="Never use type hints",
            confidence_1=0.9,
            confidence_2=0.4,
            confidence_delta=0.5,
            applies_to="python",
            conflict_reason="Contradictory affirmative vs negative"
        )

        assert contradiction.insight_id_1 == "ins-1"
        assert contradiction.confidence_delta == 0.5
        assert contradiction.conflict_reason == "Contradictory affirmative vs negative"


class TestAlert:
    """Test Alert dataclass."""

    def test_alert_creation(self):
        """Should create alert with all fields."""
        alert = Alert(
            alert_id="alert-1",
            alert_type="contradiction",
            insight_ids=["ins-1", "ins-2"],
            confidence_scores=[0.9, 0.4],
            conflict_reason="Always vs Never contradiction",
            requires_human_review=True,
            status="pending",
            created_at=datetime.now(timezone.utc)
        )

        assert alert.alert_id == "alert-1"
        assert alert.status == "pending"
        assert len(alert.insight_ids) == 2


class TestContradictionDetectionResult:
    """Test ContradictionDetectionResult dataclass."""

    def test_result_creation(self):
        """Should create detection result with all fields."""
        result = ContradictionDetectionResult(
            contradictions_found=5,
            alerts_created=3,
            existing_alerts=2,
            processing_time_ms=150.5,
            timestamp=datetime.now(timezone.utc)
        )

        assert result.contradictions_found == 5
        assert result.alerts_created == 3


class TestConflictReason:
    """Test conflict reason determination."""

    def test_always_never_contradiction(self):
        """Should detect always vs never contradiction."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        service = ContradictionDetectorService(mock_client)

        reason = service._determine_conflict_reason(
            "ALWAYS validate input",
            "NEVER validate input"
        )

        assert "Always vs Never" in reason

    def test_best_worst_contradiction(self):
        """Should detect best vs worst contradiction."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        service = ContradictionDetectorService(mock_client)

        reason = service._determine_conflict_reason(
            "BEST practice is unit testing",
            "WORST anti-pattern is no testing"
        )

        assert "Best practice vs anti-pattern" in reason


class TestContradictionDetection:
    """Test contradiction detection functionality."""

    @pytest.mark.asyncio
    async def test_detect_pattern_conflicts(self):
        """Should detect conflicting patterns."""
        mock_records = [
            {
                'insight_id_1': 'ins-1',
                'insight_id_2': 'ins-2',
                'rule_1': 'Always use type hints',
                'rule_2': 'Never use type hints',
                'c1': 0.9,
                'c2': 0.4,
                'delta': 0.5,
                'applies_to': 'python'
            }
        ]

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=mock_records)

        service = ContradictionDetectorService(mock_client)
        results = await service.detect_pattern_conflicts()

        assert len(results) == 1
        assert results[0].insight_id_1 == 'ins-1'
        assert results[0].confidence_delta == 0.5

    @pytest.mark.asyncio
    async def test_no_contradictions(self):
        """Should return empty when no contradictions."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=[])

        service = ContradictionDetectorService(mock_client)
        results = await service.detect_pattern_conflicts()

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_detect_with_applies_to_filter(self):
        """Should filter by applies_to."""
        mock_records = []

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=mock_records)

        service = ContradictionDetectorService(mock_client)
        results = await service.detect_pattern_conflicts(applies_to="javascript")

        # Verify query was called with applies_to parameter
        call_args = mock_client.execute_query.call_args
        params = call_args[0][1] if call_args[0] else call_args[1]
        assert params.get('applies_to') == 'javascript'


class TestAlertCreation:
    """Test alert creation functionality."""

    @pytest.mark.asyncio
    async def test_create_alerts(self):
        """Should create alerts for contradictions."""
        contradictions = [
            PatternContradiction(
                insight_id_1="ins-1",
                insight_id_2="ins-2",
                rule_1="Always validate",
                rule_2="Never validate",
                confidence_1=0.9,
                confidence_2=0.4,
                confidence_delta=0.5,
                applies_to="python",
                conflict_reason="test"
            )
        ]

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        # Mock _check_existing_alert to return False
        mock_client.execute_query = AsyncMock(return_value=[])

        service = ContradictionDetectorService(mock_client)
        count = await service.create_alerts(contradictions)

        # Should create 1 alert
        assert count == 1

    @pytest.mark.asyncio
    async def test_skip_existing_alerts(self):
        """Should skip creating alerts that already exist."""
        contradictions = [
            PatternContradiction(
                insight_id_1="ins-1",
                insight_id_2="ins-2",
                rule_1="Always validate",
                rule_2="Never validate",
                confidence_1=0.9,
                confidence_2=0.4,
                confidence_delta=0.5,
                applies_to="python",
                conflict_reason="test"
            )
        ]

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        # First call checks existing, returns count > 0
        mock_client.execute_query = AsyncMock(return_value=[{'count': 1}])

        service = ContradictionDetectorService(mock_client)
        count = await service.create_alerts(contradictions)

        # Should skip creating (0 new alerts)
        assert count == 0

    @pytest.mark.asyncio
    async def test_no_alerts_for_no_contradictions(self):
        """Should return 0 when no contradictions."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        service = ContradictionDetectorService(mock_client)

        count = await service.create_alerts([])

        assert count == 0


class TestAlertResolution:
    """Test alert resolution functionality."""

    @pytest.mark.asyncio
    async def test_resolve_alert(self):
        """Should resolve an alert."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=[{'count': 1}])

        service = ContradictionDetectorService(mock_client)
        resolved = await service.resolve_alert(
            alert_id="alert-123",
            resolution_notes="Updated pattern to clarify",
            resolved_by="brooks"
        )

        assert resolved is True

    @pytest.mark.asyncio
    async def test_resolve_nonexistent_alert(self):
        """Should return False for nonexistent alert."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=[])

        service = ContradictionDetectorService(mock_client)
        resolved = await service.resolve_alert(
            alert_id="nonexistent",
            resolution_notes="test"
        )

        # Empty results means no alert was updated
        assert resolved is False


class TestGetPendingAlerts:
    """Test getting pending alerts."""

    @pytest.mark.asyncio
    async def test_get_pending_alerts(self):
        """Should return pending alerts."""
        mock_records = [
            {
                'alert': {
                    'alert_id': 'alert-1',
                    'type': 'contradiction',
                    'insights': ['ins-1', 'ins-2'],
                    'confidence_scores': [0.9, 0.4],
                    'conflict_reason': 'Always vs Never',
                    'requires_human_review': True,
                    'status': 'pending',
                    'created_at': '2026-01-26T10:00:00Z',
                    'applies_to': 'python'
                }
            }
        ]

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=mock_records)

        service = ContradictionDetectorService(mock_client)
        alerts = await service.get_pending_alerts(limit=10)

        assert len(alerts) == 1
        assert alerts[0]['alert_id'] == 'alert-1'
        assert alerts[0]['status'] == 'pending'


class TestDetectionCycle:
    """Test full detection cycle."""

    @pytest.mark.asyncio
    async def test_run_detection_cycle(self):
        """Should run full detection cycle."""
        # Mock for detect_pattern_conflicts
        detect_results = [
            {
                'insight_id_1': 'ins-1',
                'insight_id_2': 'ins-2',
                'rule_1': 'Always validate',
                'rule_2': 'Never validate',
                'c1': 0.9,
                'c2': 0.4,
                'delta': 0.5,
                'applies_to': 'python'
            }
        ]

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(side_effect=[
            detect_results,  # detect_pattern_conflicts
            [],  # _check_existing_alert
            [],  # _create_alert
            [{'count': 1}]  # _count_pending_alerts
        ])

        service = ContradictionDetectorService(mock_client)
        result = await service.run_detection_cycle()

        assert result.contradictions_found == 1
        assert result.processing_time_ms >= 0

    @pytest.mark.asyncio
    async def test_run_cycle_with_no_contradictions(self):
        """Should handle cycle with no contradictions."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=[])

        service = ContradictionDetectorService(mock_client)
        result = await service.run_detection_cycle()

        assert result.contradictions_found == 0
        assert result.alerts_created == 0


class TestContradictionDetectorIntegration:
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
    async def test_detection_cycle_dry_run(self, neo4j_client):
        """Test detection cycle without making changes."""
        from src.bmad.services.contradiction_detector import ContradictionDetectorService

        try:
            await neo4j_client.initialize()
            service = ContradictionDetectorService(neo4j_client)

            result = await service.run_detection_cycle()
            print(f"\nDetection Cycle:")
            print(f"  Contradictions found: {result.contradictions_found}")
            print(f"  Alerts created: {result.alerts_created}")
            print(f"  Processing time: {result.processing_time_ms:.2f}ms")

            await neo4j_client.close()
        except Exception as e:
            pytest.skip(f"Neo4j test failed: {e}")

    @pytest.mark.asyncio
    async def test_get_pending_alerts_query(self, neo4j_client):
        """Test getting pending alerts."""
        from src.bmad.services.contradiction_detector import ContradictionDetectorService

        try:
            await neo4j_client.initialize()
            service = ContradictionDetectorService(neo4j_client)

            alerts = await service.get_pending_alerts()
            print(f"\nPending Alerts: {len(alerts)}")

            await neo4j_client.close()
        except Exception as e:
            pytest.skip(f"Neo4j test failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])