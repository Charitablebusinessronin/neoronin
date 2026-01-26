"""
Insight Generation Engine

This module automatically generates insights from outcomes to enable learning.
- Failed outcomes generate tentative insights with low confidence
- Successful outcomes reinforce existing patterns
- Confidence scores increase with repeated success

Author: Brooks (BMAD Dev Agent)
Created: 2026-01-26
Story: 2-1-generate-insights-from-outcomes
"""

import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from src.bmad.core.neo4j_client import Neo4jAsyncClient, SecurityError

logger = logging.getLogger(__name__)


@dataclass
class ProcessedOutcome:
    """Represents an outcome ready for insight generation."""
    outcome_id: str
    status: str  # "Success" or "Failed"
    result_summary: str
    error_log: Optional[str]
    event_type: str
    group_id: str
    agent_name: str
    timestamp: datetime
    used_pattern_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GeneratedInsight:
    """Represents a newly generated insight."""
    insight_id: str
    rule: str
    confidence_score: float
    learned_from_outcome_id: str
    group_id: str
    category: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class PatternUpdate:
    """Represents a pattern update from successful outcome."""
    pattern_id: str
    new_confidence_score: float
    success_rate: float
    times_used: int
    group_id: str


@dataclass
class InsightGenerationResult:
    """Result of processing a single outcome."""
    outcome_id: str
    insight: Optional[GeneratedInsight] = None
    pattern_update: Optional[PatternUpdate] = None
    processing_time_ms: float = 0.0
    error: Optional[str] = None


@dataclass
class BatchGenerationResult:
    """Result of batch insight generation."""
    processed_count: int
    insights_generated: int
    patterns_updated: int
    total_time_ms: float
    avg_time_per_outcome_ms: float
    errors: List[str] = field(default_factory=list)


class ErrorPatternExtractor:
    """Extracts patterns and fixes from error logs."""

    # Common error patterns with suggested fixes
    ERROR_PATTERNS = [
        (r"(NameError|ReferenceError):\s*name ['\"](\w+)['\"] is not defined",
         lambda m: f"Define variable '{m.group(2)}' before use or check for typos"),
        (r"(TypeError):\s*([^'\n]+)",
         lambda m: f"Fix type mismatch: {m.group(2).strip()}"),
        (r"(ValueError):\s*(.+)",
         lambda m: f"Validate input: {m.group(2).strip()}"),
        (r"(AttributeError):\s*(?:NoneType has no attribute|'(\w+)' object has no attribute)",
         lambda m: f"Check if object is None before accessing '{m.group(2)}'"),
        (r"(ImportError|ModuleNotFoundError):\s*No module named ['\"]?(\w+)['\"]?",
         lambda m: f"Install or import module '{m.group(2)}'"),
        (r"(KeyError):\s*['\"](\w+)['\"]",
         lambda m: f"Add key '{m.group(2)}' to dictionary or check for case sensitivity"),
        (r"(IndexError):\s*(?:list index out of range|)",
         lambda m: "Check list length before accessing index"),
        (r"(SyntaxError):\s*(.+)",
         lambda m: f"Fix syntax: {m.group(2).strip()}"),
        (r"(PermissionError):\s*(.+)",
         lambda m: f"Check file permissions: {m.group(2).strip()}"),
        (r"(ConnectionError|TimeoutError):\s*(.+)",
         lambda m: f"Handle connection issue: {m.group(2).strip()}"),
    ]

    @classmethod
    def extract(cls, error_log: str) -> Tuple[str, str]:
        """
        Extract error type and suggested fix from error log.

        Args:
            error_log: The error log text

        Returns:
            Tuple of (error_type, suggested_fix)
        """
        if not error_log:
            return "Unknown Error", "Review the error log for details"

        for pattern, fix_func in cls.ERROR_PATTERNS:
            match = re.search(pattern, error_log, re.IGNORECASE)
            if match:
                error_type = match.group(1) if match.groups() else "Error"
                suggested_fix = fix_func(match)
                return error_type, suggested_fix

        # Generic fallback
        return "Error", "Review error log and add appropriate error handling"

    @classmethod
    def generate_rule(cls, error_log: str, event_type: str) -> str:
        """Generate an insight rule from an error log."""
        error_type, suggested_fix = cls.extract(error_log)
        return f"[{event_type}] Avoid {error_type}: {suggested_fix}"


class ConfidenceScorer:
    """Manages confidence scoring for insights and patterns."""

    # Confidence thresholds
    INITIAL_FAILURE = 0.3
    AFTER_ONE_SUCCESS = 0.5
    AFTER_THREE_SUCCESSES = 0.7
    AFTER_FIVE_SUCCESSES = 0.8
    HIGH_CONFIDENCE = 0.8
    MAX_CONFIDENCE = 1.0

    # Confidence increment per success
    SUCCESS_INCREMENT = 0.1

    @classmethod
    def get_initial_confidence(cls, outcome_status: str) -> float:
        """Get initial confidence based on outcome status."""
        if outcome_status == "Failed":
            return cls.INITIAL_FAILURE
        return cls.INITIAL_FAILURE  # Start low for all

    @classmethod
    def calculate_pattern_confidence(
        cls,
        current_confidence: float,
        success_rate: float,
        times_used: int
    ) -> float:
        """
        Calculate new confidence for a pattern based on success history.

        Args:
            current_confidence: Current confidence score
            success_rate: Percentage of successful uses (0-1)
            times_used: Total times the pattern has been used

        Returns:
            New confidence score
        """
        if times_used < 5:
            # Still learning
            return min(cls.MAX_CONFIDENCE, current_confidence + cls.SUCCESS_INCREMENT)

        if success_rate > 0.8:
            # High success rate - increase confidence
            new_confidence = current_confidence + (0.05 * (success_rate - 0.8) / 0.2)
        elif success_rate < 0.5:
            # Low success rate - decrease confidence
            new_confidence = current_confidence - 0.1
        else:
            # Stable
            new_confidence = current_confidence

        return max(0.1, min(cls.MAX_CONFIDENCE, new_confidence))


class InsightGenerator:
    """
    Generates insights from outcomes and reinforces patterns from successes.

    Features:
    - Automatic insight generation from failed outcomes
    - Pattern reinforcement from successful outcomes
    - Multi-tenant isolation via group_id
    - Confidence scoring algorithm
    """

    def __init__(self, client: Neo4jAsyncClient):
        """
        Initialize the insight generator.

        Args:
            client: Neo4j async client for database operations
        """
        self._client = client

    async def generate_insight_from_outcome(
        self,
        outcome: ProcessedOutcome
    ) -> InsightGenerationResult:
        """
        Generate insight from a single outcome.

        Args:
            outcome: The outcome to process

        Returns:
            InsightGenerationResult with generated insight or pattern update
        """
        start_time = time.perf_counter()

        try:
            if outcome.status == "Failed":
                return await self._process_failed_outcome(outcome)
            else:
                return await self._process_successful_outcome(outcome)

        except Exception as e:
            logger.error(f"Error processing outcome {outcome.outcome_id}: {e}")
            return InsightGenerationResult(
                outcome_id=outcome.outcome_id,
                processing_time_ms=(time.perf_counter() - start_time) * 1000,
                error=str(e)
            )

    async def _process_failed_outcome(
        self,
        outcome: ProcessedOutcome
    ) -> InsightGenerationResult:
        """Process a failed outcome to generate a tentative insight."""
        start_time = time.perf_counter()

        # Generate insight from error log
        rule = ErrorPatternExtractor.generate_rule(
            outcome.error_log or "",
            outcome.event_type
        )

        confidence = ConfidenceScorer.get_initial_confidence("Failed")

        # Create insight in database
        insight_id = await self._create_insight(
            rule=rule,
            confidence_score=confidence,
            learned_from=outcome.outcome_id,
            group_id=outcome.group_id,
            category=outcome.event_type
        )

        processing_time = (time.perf_counter() - start_time) * 1000

        return InsightGenerationResult(
            outcome_id=outcome.outcome_id,
            insight=GeneratedInsight(
                insight_id=insight_id,
                rule=rule,
                confidence_score=confidence,
                learned_from_outcome_id=outcome.outcome_id,
                group_id=outcome.group_id,
                category=outcome.event_type
            ),
            processing_time_ms=processing_time
        )

    async def _process_successful_outcome(
        self,
        outcome: ProcessedOutcome
    ) -> InsightGenerationResult:
        """Process a successful outcome to reinforce patterns."""
        start_time = time.perf_counter()

        if not outcome.used_pattern_id:
            # No pattern to reinforce
            return InsightGenerationResult(
                outcome_id=outcome.outcome_id,
                processing_time_ms=(time.perf_counter() - start_time) * 1000
            )

        # Get pattern details and calculate new confidence
        pattern_data = await self._get_pattern_data(outcome.used_pattern_id)

        if pattern_data:
            new_confidence = ConfidenceScorer.calculate_pattern_confidence(
                current_confidence=pattern_data['confidence_score'],
                success_rate=pattern_data['success_rate'],
                times_used=pattern_data['times_used']
            )

            # Update pattern in database
            await self._update_pattern_confidence(
                pattern_id=outcome.used_pattern_id,
                new_confidence=new_confidence,
                success_rate=pattern_data['success_rate'],
                times_used=pattern_data['times_used'] + 1
            )

            processing_time = (time.perf_counter() - start_time) * 1000

            return InsightGenerationResult(
                outcome_id=outcome.outcome_id,
                pattern_update=PatternUpdate(
                    pattern_id=outcome.used_pattern_id,
                    new_confidence_score=new_confidence,
                    success_rate=pattern_data['success_rate'],
                    times_used=pattern_data['times_used'] + 1,
                    group_id=outcome.group_id
                ),
                processing_time_ms=processing_time
            )

        return InsightGenerationResult(
            outcome_id=outcome.outcome_id,
            processing_time_ms=(time.perf_counter() - start_time) * 1000
        )

    async def _create_insight(
        self,
        rule: str,
        confidence_score: float,
        learned_from: str,
        group_id: str,
        category: str
    ) -> str:
        """Create an Insight node in the database."""
        import uuid

        insight_id = f"insight-{uuid.uuid4().hex[:12]}"

        query = """
        CREATE (i:Insight {
            insight_id: $insight_id,
            rule: $rule,
            confidence_score: $confidence_score,
            learned_from: $learned_from,
            group_id: $group_id,
            category: $category,
            created_at: datetime(),
            status: 'active'
        })
        RETURN elementId(i) as id
        """

        await self._client.execute_write(
            query,
            {
                "insight_id": insight_id,
                "rule": rule,
                "confidence_score": confidence_score,
                "learned_from": learned_from,
                "group_id": group_id,
                "category": category
            }
        )

        return insight_id

    async def _get_pattern_data(self, pattern_id: str) -> Optional[Dict[str, float]]:
        """Get pattern data for confidence calculation."""
        query = """
        MATCH (p:Pattern {pattern_id: $pattern_id})
        RETURN p.confidence_score as confidence_score,
               p.success_rate as success_rate,
               p.times_used as times_used
        """

        results = await self._client.execute_query(
            query,
            {"pattern_id": pattern_id}
        )

        if results:
            return results[0]
        return None

    async def _update_pattern_confidence(
        self,
        pattern_id: str,
        new_confidence: float,
        success_rate: float,
        times_used: int
    ) -> None:
        """Update pattern confidence in the database."""
        query = """
        MATCH (p:Pattern {pattern_id: $pattern_id})
        SET p.confidence_score = $new_confidence,
            p.success_rate = $success_rate,
            p.times_used = $times_used,
            p.last_updated = datetime()
        """

        await self._client.execute_write(
            query,
            {
                "pattern_id": pattern_id,
                "new_confidence": new_confidence,
                "success_rate": success_rate,
                "times_used": times_used
            }
        )

    async def process_outcomes_batch(
        self,
        outcomes: List[ProcessedOutcome]
    ) -> BatchGenerationResult:
        """
        Process a batch of outcomes for insight generation.

        Args:
            outcomes: List of outcomes to process

        Returns:
            BatchGenerationResult with processing summary
        """
        start_time = time.perf_counter()

        insights_generated = 0
        patterns_updated = 0
        errors = []

        for outcome in outcomes:
            result = await self.generate_insight_from_outcome(outcome)

            if result.insight:
                insights_generated += 1
            elif result.pattern_update:
                patterns_updated += 1

            if result.error:
                errors.append(f"Outcome {result.outcome_id}: {result.error}")

        total_time = (time.perf_counter() - start_time) * 1000

        return BatchGenerationResult(
            processed_count=len(outcomes),
            insights_generated=insights_generated,
            patterns_updated=patterns_updated,
            total_time_ms=total_time,
            avg_time_per_outcome_ms=total_time / len(outcomes) if outcomes else 0,
            errors=errors
        )

    async def get_unprocessed_outcomes(
        self,
        group_id: str,
        hours_back: int = 24
    ) -> List[ProcessedOutcome]:
        """
        Get outcomes that haven't been processed for insights.

        Args:
            group_id: Project group ID for isolation
            hours_back: How many hours back to look

        Returns:
            List of unprocessed outcomes
        """
        query = """
        MATCH (o:Outcome)
        WHERE o.group_id = $group_id
          AND o.status IN ['Success', 'Failed']
          AND NOT exists((o)-[:GENERATED]->(:Insight))
          AND o.timestamp > datetime() - duration({hours: $hours_back})
        MATCH (e:Event)-[:HAS_OUTCOME]->(o)
        MATCH (agent:AIAgent)-[:PERFORMED]->(e)
        OPTIONAL MATCH (e)-[:USED_PATTERN]->(p:Pattern)
        RETURN o.outcome_id as outcome_id,
               o.status as status,
               o.result_summary as result_summary,
               o.error_log as error_log,
               e.event_type as event_type,
               o.group_id as group_id,
               agent.name as agent_name,
               o.timestamp as timestamp,
               p.pattern_id as pattern_id
        ORDER BY o.timestamp DESC
        """

        results = await self._client.execute_query(
            query,
            {"group_id": group_id, "hours_back": hours_back}
        )

        return [
            ProcessedOutcome(
                outcome_id=r.get('outcome_id', ''),
                status=r.get('status', ''),
                result_summary=r.get('result_summary', ''),
                error_log=r.get('error_log'),
                event_type=r.get('event_type', ''),
                group_id=r.get('group_id', ''),
                agent_name=r.get('agent_name', ''),
                timestamp=r.get('timestamp', datetime.now(timezone.utc)),
                used_pattern_id=r.get('pattern_id')
            )
            for r in results
        ]


async def main():
    """Quick test of the insight generator."""
    import os
    os.environ['NEO4J_URI'] = 'bolt://localhost:7687'
    os.environ['NEO4J_USER'] = 'neo4j'
    os.environ['NEO4J_PASSWORD'] = 'Kamina2025*'

    from src.bmad.core.neo4j_client import Neo4jAsyncClient

    async with Neo4jAsyncClient() as client:
        generator = InsightGenerator(client)

        print("Testing insight generation...")

        # Test with a failed outcome
        failed_outcome = ProcessedOutcome(
            outcome_id="test-fail-1",
            status="Failed",
            result_summary="Test failed",
            error_log="TypeError: unsupported operand type(s) for +: 'NoneType' and 'int'",
            event_type="test",
            group_id="global-coding-skills",
            agent_name="Brooks",
            timestamp=datetime.now(timezone.utc)
        )

        result = await generator.generate_insight_from_outcome(failed_outcome)

        print(f"\nFailed Outcome Processing:")
        print(f"  Outcome: {result.outcome_id}")
        print(f"  Insight: {result.insight.rule if result.insight else 'None'}")
        print(f"  Confidence: {result.insight.confidence_score if result.insight else 'N/A'}")
        print(f"  Time: {result.processing_time_ms:.2f}ms")

        if result.error:
            print(f"  Error: {result.error}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())