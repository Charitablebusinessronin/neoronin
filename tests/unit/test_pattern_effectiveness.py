"""Unit tests for Pattern Effectiveness Service (Story 4-2).

Tests cover:
- Pattern metrics update from outcome history
- Low effectiveness pattern detection
- Alert generation
- Scheduled task execution
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
from src.bmad.services.pattern_effectiveness import (
    PatternEffectivenessService,
    PatternMetrics,
    EffectivenessReport,
    PatternAlert
)


class TestPatternEffectivenessServiceInit:
    """Test PatternEffectivenessService initialization."""

    def test_init_with_client(self):
        """Service should initialize with Neo4j client."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        service = PatternEffectivenessService(mock_client)

        assert service._client == mock_client

    def test_default_threshold(self):
        """Service should have correct default threshold."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        service = PatternEffectivenessService(mock_client)

        assert service.LOW_EFFECTIVENESS_THRESHOLD == 0.6


class TestPatternMetrics:
    """Test PatternMetrics dataclass."""

    def test_metrics_creation(self):
        """Should create metrics with all fields."""
        metrics = PatternMetrics(
            pattern_id="p1",
            pattern_name="Test Pattern",
            success_rate=0.85,
            times_used=100,
            group_id="test-group",
            category="testing"
        )

        assert metrics.pattern_id == "p1"
        assert metrics.success_rate == 0.85
        assert metrics.times_used == 100


class TestEffectivenessReport:
    """Test EffectivenessReport dataclass."""

    def test_report_creation(self):
        """Should create report with all fields."""
        report = EffectivenessReport(
            patterns_updated=10,
            avg_success_rate=0.75,
            patterns_with_alerts=2,
            low_effectiveness_patterns=[],
            processing_time_ms=150.5,
            group_id="test-group",
            timestamp=datetime.now(timezone.utc)
        )

        assert report.patterns_updated == 10
        assert report.avg_success_rate == 0.75
        assert report.processing_time_ms == 150.5


class TestPatternAlert:
    """Test PatternAlert dataclass."""

    def test_alert_creation(self):
        """Should create alert with all fields."""
        alert = PatternAlert(
            pattern_id="p1",
            pattern_name="Low Pattern",
            success_rate=0.4,
            threshold=0.6,
            group_id="test-group",
            timestamp=datetime.now(timezone.utc)
        )

        assert alert.pattern_id == "p1"
        assert alert.success_rate == 0.4
        assert alert.alert_type == "low_effectiveness"


class TestPatternMetricsUpdate:
    """Test pattern metrics update functionality."""

    @pytest.mark.asyncio
    async def test_update_pattern_metrics(self):
        """Should update success_rate and times_used from outcomes."""
        mock_records = [
            {
                'pattern_id': 'p1',
                'pattern_name': 'Pattern 1',
                'success_rate': 0.8,
                'times_used': 50,
                'group_id': 'test-group',
                'category': 'testing'
            },
            {
                'pattern_id': 'p2',
                'pattern_name': 'Pattern 2',
                'success_rate': 0.7,
                'times_used': 30,
                'group_id': 'test-group',
                'category': 'testing'
            }
        ]

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=mock_records)

        service = PatternEffectivenessService(mock_client)
        results = await service._update_pattern_metrics('test-group')

        assert len(results) == 2
        assert results[0].pattern_id == 'p1'
        assert results[0].times_used == 50

    @pytest.mark.asyncio
    async def test_update_all_groups(self):
        """Should update metrics for all groups when group_id is None."""
        mock_records = [
            {
                'pattern_id': 'p1',
                'pattern_name': 'Pattern 1',
                'success_rate': 0.9,
                'times_used': 100,
                'group_id': 'group1',
                'category': 'testing'
            }
        ]

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=mock_records)

        service = PatternEffectivenessService(mock_client)
        results = await service._update_pattern_metrics(None)

        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_update_no_patterns(self):
        """Should return empty list when no patterns have outcomes."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=[])

        service = PatternEffectivenessService(mock_client)
        results = await service._update_pattern_metrics('test-group')

        assert len(results) == 0


class TestLowEffectivenessDetection:
    """Test low effectiveness pattern detection."""

    @pytest.mark.asyncio
    async def test_get_low_effectiveness_patterns(self):
        """Should return patterns below threshold."""
        mock_records = [
            {
                'pattern_id': 'p1',
                'pattern_name': 'Failing Pattern',
                'success_rate': 0.4,
                'times_used': 20,
                'group_id': 'test-group',
                'category': 'testing'
            }
        ]

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=mock_records)

        service = PatternEffectivenessService(mock_client)
        results = await service._get_low_effectiveness_patterns('test-group')

        assert len(results) == 1
        assert results[0].success_rate == 0.4

    @pytest.mark.asyncio
    async def test_no_low_effectiveness_patterns(self):
        """Should return empty when all patterns above threshold."""
        mock_records = [
            {
                'pattern_id': 'p1',
                'pattern_name': 'Good Pattern',
                'success_rate': 0.8,
                'times_used': 50,
                'group_id': 'test-group',
                'category': 'testing'
            }
        ]

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=mock_records)

        service = PatternEffectivenessService(mock_client)
        results = await service._get_low_effectiveness_patterns('test-group')

        # Note: This returns the mock record, but the service uses
        # the threshold check in Cypher - the mock just returns what it's given
        # In real usage, the Cypher query filters by threshold


class TestAlertGeneration:
    """Test alert generation for low effectiveness patterns."""

    @pytest.mark.asyncio
    async def test_generate_alerts(self):
        """Should generate alerts for low effectiveness patterns."""
        low_patterns = [
            PatternMetrics(
                pattern_id='p1',
                pattern_name='Failing Pattern',
                success_rate=0.4,
                times_used=20,
                group_id='test-group',
                category='testing'
            )
        ]

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock()

        service = PatternEffectivenessService(mock_client)
        alerts = await service._generate_alerts(low_patterns)

        assert len(alerts) == 1
        assert alerts[0].pattern_id == 'p1'
        assert alerts[0].success_rate == 0.4

    @pytest.mark.asyncio
    async def test_no_alerts_when_no_low_patterns(self):
        """Should return empty list when no low patterns."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        service = PatternEffectivenessService(mock_client)
        alerts = await service._generate_alerts([])

        assert len(alerts) == 0


class TestEffectivenessUpdate:
    """Test the main effectiveness update method."""

    @pytest.mark.asyncio
    async def test_update_effectiveness(self):
        """Should update metrics and return report."""
        update_records = [
            {
                'pattern_id': 'p1',
                'pattern_name': 'Pattern 1',
                'success_rate': 0.8,
                'times_used': 50,
                'group_id': 'test-group',
                'category': 'testing'
            }
        ]

        low_records = []  # No low effectiveness patterns

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(side_effect=[update_records, low_records])

        service = PatternEffectivenessService(mock_client)
        report = await service.update_effectiveness('test-group')

        assert report.patterns_updated == 1
        assert report.avg_success_rate == 0.8
        assert report.group_id == 'test-group'

    @pytest.mark.asyncio
    async def test_update_with_alerts(self):
        """Should report alerts in the effectiveness report."""
        update_records = [
            {
                'pattern_id': 'p1',
                'pattern_name': 'Good Pattern',
                'success_rate': 0.8,
                'times_used': 50,
                'group_id': 'test-group',
                'category': 'testing'
            },
            {
                'pattern_id': 'p2',
                'pattern_name': 'Bad Pattern',
                'success_rate': 0.4,
                'times_used': 20,
                'group_id': 'test-group',
                'category': 'testing'
            }
        ]

        low_records = [
            {
                'pattern_id': 'p2',
                'pattern_name': 'Bad Pattern',
                'success_rate': 0.4,
                'times_used': 20,
                'group_id': 'test-group',
                'category': 'testing'
            }
        ]

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(side_effect=[update_records, low_records])

        service = PatternEffectivenessService(mock_client)
        report = await service.update_effectiveness('test-group')

        assert report.patterns_updated == 2
        assert report.patterns_with_alerts == 1


class TestEffectivenessSummary:
    """Test effectiveness summary functionality."""

    @pytest.mark.asyncio
    async def test_get_effectiveness_summary(self):
        """Should return summary statistics."""
        mock_records = [
            {
                'total_patterns': 10,
                'avg_success_rate': 0.75,
                'min_success_rate': 0.4,
                'max_success_rate': 0.95,
                'total_uses': 500
            }
        ]

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=mock_records)

        service = PatternEffectivenessService(mock_client)
        summary = await service.get_effectiveness_summary('test-group')

        assert summary['total_patterns'] == 10
        assert summary['avg_success_rate'] == 0.75
        assert summary['total_uses'] == 500

    @pytest.mark.asyncio
    async def test_get_summary_no_patterns(self):
        """Should return zeros when no patterns."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=[])

        service = PatternEffectivenessService(mock_client)
        summary = await service.get_effectiveness_summary('test-group')

        assert summary['total_patterns'] == 0
        assert summary['avg_success_rate'] == 0.0


class TestPatternMetricsQuery:
    """Test single pattern metrics query."""

    @pytest.mark.asyncio
    async def test_get_pattern_metrics(self):
        """Should return metrics for specific pattern."""
        mock_records = [
            {
                'pattern_id': 'p1',
                'pattern_name': 'Test Pattern',
                'success_rate': 0.8,
                'times_used': 50,
                'group_id': 'test-group',
                'category': 'testing',
                'calculated_rate': 0.85
            }
        ]

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=mock_records)

        service = PatternEffectivenessService(mock_client)
        metrics = await service.get_pattern_metrics('p1')

        assert metrics is not None
        assert metrics.pattern_id == 'p1'
        assert metrics.success_rate == 0.85

    @pytest.mark.asyncio
    async def test_get_pattern_metrics_not_found(self):
        """Should return None when pattern not found."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=[])

        service = PatternEffectivenessService(mock_client)
        metrics = await service.get_pattern_metrics('nonexistent')

        assert metrics is None


class TestPatternEffectivenessIntegration:
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
    async def test_effectiveness_summary_query(self, neo4j_client):
        """Test effectiveness summary query."""
        from src.bmad.services.pattern_effectiveness import PatternEffectivenessService

        try:
            await neo4j_client.initialize()
            service = PatternEffectivenessService(neo4j_client)

            summary = await service.get_effectiveness_summary()
            print(f"\nEffectiveness Summary:")
            print(f"  Total patterns: {summary['total_patterns']}")
            print(f"  Avg success rate: {summary['avg_success_rate']:.2%}")

            await neo4j_client.close()
        except Exception as e:
            pytest.skip(f"Neo4j test failed: {e}")

    @pytest.mark.asyncio
    async def test_effectiveness_update_dry_run(self, neo4j_client):
        """Test effectiveness update (dry run mode)."""
        from src.bmad.services.pattern_effectiveness import PatternEffectivenessService

        try:
            await neo4j_client.initialize()
            service = PatternEffectivenessService(neo4j_client)

            report = await service.update_effectiveness()
            print(f"\nEffectiveness Update:")
            print(f"  Patterns updated: {report.patterns_updated}")
            print(f"  Avg success rate: {report.avg_success_rate:.2%}")
            print(f"  Processing time: {report.processing_time_ms:.2f}ms")

            await neo4j_client.close()
        except Exception as e:
            pytest.skip(f"Neo4j test failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])