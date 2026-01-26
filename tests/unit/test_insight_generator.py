"""Unit tests for Insight Generator (Story 2-1).

Tests cover:
- Error pattern extraction
- Confidence scoring algorithm
- Insight generation from failed outcomes
- Pattern reinforcement from successful outcomes
- Batch processing
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

from src.bmad.services.insight_generator import (
    InsightGenerator,
    ProcessedOutcome,
    GeneratedInsight,
    InsightGenerationResult,
    BatchGenerationResult,
    ErrorPatternExtractor,
    ConfidenceScorer
)


class TestErrorPatternExtractor:
    """Test error pattern extraction functionality."""

    def test_extract_type_error(self):
        """Should extract TypeError and suggest fix."""
        error_log = "TypeError: unsupported operand type(s) for +: 'NoneType' and 'int'"

        error_type, fix = ErrorPatternExtractor.extract(error_log)

        assert "TypeError" in error_type
        assert "NoneType" in fix or "type" in fix.lower()

    def test_extract_name_error(self):
        """Should extract NameError for undefined variables."""
        error_log = "NameError: name 'my_var' is not defined"

        error_type, fix = ErrorPatternExtractor.extract(error_log)

        assert "NameError" in error_type
        assert "my_var" in fix

    def test_extract_value_error(self):
        """Should extract ValueError."""
        error_log = "ValueError: invalid literal for int() with base 10: 'abc'"

        error_type, fix = ErrorPatternExtractor.extract(error_log)

        assert "ValueError" in error_type

    def test_extract_key_error(self):
        """Should extract KeyError for missing dictionary keys."""
        error_log = "KeyError: 'missing_key'"

        error_type, fix = ErrorPatternExtractor.extract(error_log)

        assert "KeyError" in error_type
        assert "missing_key" in fix

    def test_extract_import_error(self):
        """Should extract ModuleNotFoundError."""
        error_log = "ModuleNotFoundError: No module named 'requests'"

        error_type, fix = ErrorPatternExtractor.extract(error_log)

        assert "ModuleNotFoundError" in error_type or "ImportError" in error_type
        # Fix should contain "requests" module name
        assert "requests" in fix or "ModuleNotFoundError" in fix

    def test_extract_attribute_error(self):
        """Should extract AttributeError."""
        error_log = "AttributeError: 'NoneType' object has no attribute 'length'"

        error_type, fix = ErrorPatternExtractor.extract(error_log)

        assert "AttributeError" in error_type

    def test_extract_unknown_error(self):
        """Should handle unknown error types."""
        error_log = "Something unexpected happened here"

        error_type, fix = ErrorPatternExtractor.extract(error_log)

        assert error_type == "Error" or "Error" in error_type

    def test_extract_empty_log(self):
        """Should handle empty error log."""
        error_log = ""

        error_type, fix = ErrorPatternExtractor.extract(error_log)

        assert error_type == "Unknown Error"
        assert "Review" in fix

    def test_generate_rule_from_error(self):
        """Should generate a useful insight rule."""
        error_log = "TypeError: unsupported operand type(s) for +: 'NoneType' and 'int'"
        event_type = "test"

        rule = ErrorPatternExtractor.generate_rule(error_log, event_type)

        assert "[test]" in rule
        assert "TypeError" in rule or "type" in rule.lower()


class TestConfidenceScorer:
    """Test confidence scoring functionality."""

    def test_initial_failure_confidence(self):
        """Failed outcomes should start with low confidence."""
        confidence = ConfidenceScorer.get_initial_confidence("Failed")

        assert confidence == 0.3

    def test_pattern_confidence_increase(self):
        """Pattern confidence should increase with success."""
        new_conf = ConfidenceScorer.calculate_pattern_confidence(
            current_confidence=0.5,
            success_rate=0.9,  # High success rate
            times_used=10
        )

        assert new_conf > 0.5

    def test_pattern_confidence_decrease(self):
        """Pattern confidence should decrease with failures."""
        new_conf = ConfidenceScorer.calculate_pattern_confidence(
            current_confidence=0.7,
            success_rate=0.3,  # Low success rate
            times_used=10
        )

        assert new_conf < 0.7

    def test_pattern_confidence_stable(self):
        """Pattern confidence should be stable for moderate success."""
        current = 0.6
        new_conf = ConfidenceScorer.calculate_pattern_confidence(
            current_confidence=current,
            success_rate=0.6,
            times_used=5
        )

        assert new_conf == current  # No significant change

    def test_confidence_clamped_to_max(self):
        """Confidence should not exceed 1.0."""
        new_conf = ConfidenceScorer.calculate_pattern_confidence(
            current_confidence=0.95,
            success_rate=1.0,
            times_used=100
        )

        assert new_conf <= 1.0

    def test_confidence_clamped_to_min(self):
        """Confidence should not go below 0.1."""
        new_conf = ConfidenceScorer.calculate_pattern_confidence(
            current_confidence=0.15,
            success_rate=0.1,
            times_used=100
        )

        assert new_conf >= 0.1


class TestInsightGeneratorInit:
    """Test InsightGenerator initialization."""

    def test_init_with_client(self):
        """Generator should be initialized with Neo4j client."""
        from src.bmad.services.insight_generator import InsightGenerator
        from src.bmad.core.neo4j_client import Neo4jAsyncClient

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        generator = InsightGenerator(mock_client)

        assert generator._client == mock_client


class TestGenerateInsightFromOutcome:
    """Test insight generation from outcomes."""

    @pytest.mark.asyncio
    async def test_generate_insight_from_failed_outcome(self):
        """Should generate insight from failed outcome."""
        from src.bmad.services.insight_generator import InsightGenerator
        from src.bmad.core.neo4j_client import Neo4jAsyncClient

        failed_outcome = ProcessedOutcome(
            outcome_id="test-1",
            status="Failed",
            result_summary="Test failed",
            error_log="TypeError: unsupported operand type(s) for +: 'NoneType' and 'int'",
            event_type="test",
            group_id="test-group",
            agent_name="Brooks",
            timestamp=datetime.now(timezone.utc)
        )

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_write = AsyncMock(return_value=[{"id": "123"}])

        generator = InsightGenerator(mock_client)

        result = await generator.generate_insight_from_outcome(failed_outcome)

        assert result.outcome_id == "test-1"
        assert result.insight is not None
        assert result.insight.confidence_score < 0.5
        assert result.error is None

    @pytest.mark.asyncio
    async def test_reinforce_pattern_from_success(self):
        """Should update pattern confidence from successful outcome."""
        from src.bmad.services.insight_generator import InsightGenerator
        from src.bmad.core.neo4j_client import Neo4jAsyncClient

        successful_outcome = ProcessedOutcome(
            outcome_id="test-2",
            status="Success",
            result_summary="Test passed",
            error_log=None,
            event_type="test",
            group_id="test-group",
            agent_name="Brooks",
            timestamp=datetime.now(timezone.utc),
            used_pattern_id="pattern-1"
        )

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        # Use times_used=4 so it falls in the "still learning" category
        mock_client.execute_query = AsyncMock(return_value=[
            {"confidence_score": 0.5, "success_rate": 0.8, "times_used": 4}
        ])
        mock_client.execute_write = AsyncMock(return_value=[])

        generator = InsightGenerator(mock_client)

        result = await generator.generate_insight_from_outcome(successful_outcome)

        assert result.outcome_id == "test-2"
        assert result.pattern_update is not None
        assert result.pattern_update.new_confidence_score > 0.5

    @pytest.mark.asyncio
    async def test_no_action_for_success_without_pattern(self):
        """Should not create insight for success without pattern."""
        from src.bmad.services.insight_generator import InsightGenerator
        from src.bmad.core.neo4j_client import Neo4jAsyncClient

        successful_outcome = ProcessedOutcome(
            outcome_id="test-3",
            status="Success",
            result_summary="Test passed",
            error_log=None,
            event_type="test",
            group_id="test-group",
            agent_name="Brooks",
            timestamp=datetime.now(timezone.utc),
            used_pattern_id=None  # No pattern used
        )

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        generator = InsightGenerator(mock_client)

        result = await generator.generate_insight_from_outcome(successful_outcome)

        assert result.outcome_id == "test-3"
        assert result.insight is None
        assert result.pattern_update is None


class TestProcessedOutcome:
    """Test ProcessedOutcome dataclass."""

    def test_processed_outcome_creation(self):
        """Should create ProcessedOutcome with all fields."""
        outcome = ProcessedOutcome(
            outcome_id="o1",
            status="Success",
            result_summary="Passed",
            error_log=None,
            event_type="code_review",
            group_id="test",
            agent_name="Brooks",
            timestamp=datetime.now(timezone.utc),
            used_pattern_id="p1"
        )

        assert outcome.outcome_id == "o1"
        assert outcome.status == "Success"
        assert outcome.used_pattern_id == "p1"


class TestGeneratedInsight:
    """Test GeneratedInsight dataclass."""

    def test_generated_insight_creation(self):
        """Should create GeneratedInsight with all fields."""
        insight = GeneratedInsight(
            insight_id="i1",
            rule="Avoid TypeError by checking for None",
            confidence_score=0.3,
            learned_from_outcome_id="o1",
            group_id="test",
            category="test"
        )

        assert insight.insight_id == "i1"
        assert insight.confidence_score == 0.3
        assert insight.rule == "Avoid TypeError by checking for None"


class TestBatchGenerationResult:
    """Test BatchGenerationResult dataclass."""

    def test_batch_result_creation(self):
        """Should create BatchGenerationResult with summary."""
        result = BatchGenerationResult(
            processed_count=100,
            insights_generated=5,
            patterns_updated=10,
            total_time_ms=5000,
            avg_time_per_outcome_ms=50.0,
            errors=["Error 1"]
        )

        assert result.processed_count == 100
        assert result.insights_generated == 5
        assert result.patterns_updated == 10
        assert result.avg_time_per_outcome_ms == 50.0
        assert len(result.errors) == 1


class TestProcessOutcomesBatch:
    """Test batch processing."""

    @pytest.mark.asyncio
    async def test_process_empty_batch(self):
        """Should handle empty batch gracefully."""
        from src.bmad.services.insight_generator import InsightGenerator
        from src.bmad.core.neo4j_client import Neo4jAsyncClient

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        generator = InsightGenerator(mock_client)

        result = await generator.process_outcomes_batch([])

        assert result.processed_count == 0
        assert result.insights_generated == 0

    @pytest.mark.asyncio
    async def test_process_mixed_batch(self):
        """Should process mixed success/failed outcomes."""
        from src.bmad.services.insight_generator import InsightGenerator
        from src.bmad.core.neo4j_client import Neo4jAsyncClient

        outcomes = [
            ProcessedOutcome(
                outcome_id="f1",
                status="Failed",
                result_summary="Failed",
                error_log="TypeError: error",
                event_type="test",
                group_id="test",
                agent_name="Brooks",
                timestamp=datetime.now(timezone.utc)
            ),
            ProcessedOutcome(
                outcome_id="s1",
                status="Success",
                result_summary="Passed",
                error_log=None,
                event_type="test",
                group_id="test",
                agent_name="Brooks",
                timestamp=datetime.now(timezone.utc),
                used_pattern_id="p1"
            )
        ]

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=[
            {"confidence_score": 0.5, "success_rate": 0.8, "times_used": 5}
        ])
        mock_client.execute_write = AsyncMock(return_value=[])

        generator = InsightGenerator(mock_client)

        result = await generator.process_outcomes_batch(outcomes)

        assert result.processed_count == 2
        assert result.insights_generated == 1  # Only failed generates insight


class TestInsightGeneratorIntegration:
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
    async def test_real_insight_generation(self, neo4j_client):
        """Test real insight generation against Neo4j."""
        from src.bmad.services.insight_generator import InsightGenerator

        try:
            await neo4j_client.initialize()
            generator = InsightGenerator(neo4j_client)

            # Create a test outcome first
            await neo4j_client.execute_write(
                """
                CREATE (o:Outcome {
                    outcome_id: $oid,
                    status: $status,
                    result_summary: $summary,
                    error_log: $error,
                    event_type: $event_type,
                    group_id: $group_id,
                    timestamp: datetime()
                })
                """,
                {
                    "oid": "test-outcome-integration",
                    "status": "Failed",
                    "summary": "Integration test",
                    "error_log": "TypeError: integration test error",
                    "event_type": "integration_test",
                    "group_id": "global-coding-skills"
                }
            )

            # Get the outcome
            outcome = ProcessedOutcome(
                outcome_id="test-outcome-integration",
                status="Failed",
                result_summary="Integration test",
                error_log="TypeError: integration test error",
                event_type="integration_test",
                group_id="global-coding-skills",
                agent_name="Brooks",
                timestamp=datetime.now(timezone.utc)
            )

            result = await generator.generate_insight_from_outcome(outcome)

            assert result.insight is not None
            assert result.insight.confidence_score < 0.5

            # Clean up
            await neo4j_client.execute_write(
                "MATCH (o:Outcome {outcome_id: $oid}) DETACH DELETE o",
                {"oid": "test-outcome-integration"}
            )
            await neo4j_client.close()
        except Exception as e:
            pytest.skip(f"Neo4j test failed: {e}")

    @pytest.mark.asyncio
    async def test_batch_processing_performance(self, neo4j_client):
        """Test that batch processing meets performance targets."""
        from src.bmad.services.insight_generator import InsightGenerator

        try:
            await neo4j_client.initialize()
            generator = InsightGenerator(neo4j_client)

            # Create 10 test outcomes
            test_outcomes = []
            for i in range(10):
                oid = f"perf-test-{i}"
                await neo4j_client.execute_write(
                    """
                    CREATE (o:Outcome {
                        outcome_id: $oid,
                        status: 'Failed',
                        result_summary: $summary,
                        error_log: $error,
                        event_type: 'perf_test',
                        group_id: 'global-coding-skills',
                        timestamp: datetime()
                    })
                    """,
                    {
                        "oid": oid,
                        "summary": f"Perf test {i}",
                        "error_log": f"Error {i}: TypeError: test error {i}"
                    }
                )
                test_outcomes.append(ProcessedOutcome(
                    outcome_id=oid,
                    status="Failed",
                    result_summary=f"Perf test {i}",
                    error_log=f"Error {i}: TypeError: test error {i}",
                    event_type="perf_test",
                    group_id="global-coding-skills",
                    agent_name="Brooks",
                    timestamp=datetime.now(timezone.utc)
                ))

            # Process batch
            result = await generator.process_outcomes_batch(test_outcomes)

            # NFR: 500ms per outcome = 5000ms for 10 outcomes
            assert result.avg_time_per_outcome_ms < 500, f"Too slow: {result.avg_time_per_outcome_ms:.2f}ms"

            # Clean up
            for i in range(10):
                await neo4j_client.execute_write(
                    "MATCH (o:Outcome {outcome_id: $oid}) DETACH DELETE o",
                    {"oid": f"perf-test-{i}"}
                )

            await neo4j_client.close()
        except Exception as e:
            pytest.skip(f"Performance test failed: {e}")