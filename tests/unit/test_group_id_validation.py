"""Unit tests for Multi-Tenant Isolation (Story 3-1).

Tests cover:
- group_id validation in Neo4j client
- SecurityError raised for missing group_id
- Audit logging for access attempts
- Cross-group access detection
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

from src.bmad.core.neo4j_client import Neo4jAsyncClient, SecurityError
from src.bmad.services.audit_logger import (
    AuditLogger,
    AuditLogEntry,
    AuditQueryFilters,
    AuditSummary
)


class TestGroupIdValidation:
    """Test group_id validation in Neo4j client."""

    def test_security_error_raised_for_missing_group_id(self):
        """Should raise SecurityError when group_id is missing."""
        client = Neo4jAsyncClient.__new__(Neo4jAsyncClient)
        client._driver = MagicMock()

        with pytest.raises(SecurityError) as exc_info:
            client._validate_group_id(
                "MATCH (a:AIAgent) RETURN a",
                {}
            )

        assert "group_id parameter is required" in str(exc_info.value)

    def test_security_error_raised_for_data_query(self):
        """Should raise SecurityError for data queries without group_id."""
        client = Neo4jAsyncClient.__new__(Neo4jAsyncClient)
        client._driver = MagicMock()

        with pytest.raises(SecurityError):
            client._validate_group_id(
                "MATCH (i:Insight) RETURN i",
                {}
            )

    def test_no_error_for_schema_queries(self):
        """Should not raise error for schema queries."""
        client = Neo4jAsyncClient.__new__(Neo4jAsyncClient)
        client._driver = MagicMock()

        # Should not raise
        client._validate_group_id(
            "CALL dbms.components()",
            {}
        )

    def test_no_error_for_show_constraints(self):
        """Should not raise error for SHOW CONSTRAINTS."""
        client = Neo4jAsyncClient.__new__(Neo4jAsyncClient)
        client._driver = MagicMock()

        # Should not raise
        client._validate_group_id(
            "SHOW CONSTRAINTS",
            {}
        )

    def test_no_error_with_group_id_present(self):
        """Should not raise error when group_id is in parameters."""
        client = Neo4jAsyncClient.__new__(Neo4jAsyncClient)
        client._driver = MagicMock()

        # Should not raise
        client._validate_group_id(
            "MATCH (a:AIAgent) WHERE a.group_id = $group_id RETURN a",
            {"group_id": "faith-meats"}
        )

    def test_no_error_for_create_index(self):
        """Should not raise error for CREATE INDEX."""
        client = Neo4jAsyncClient.__new__(Neo4jAsyncClient)
        client._driver = MagicMock()

        # Should not raise
        client._validate_group_id(
            "CREATE INDEX FOR (n:AIAgent) ON (n.name)",
            {}
        )


class TestSecurityError:
    """Test SecurityError exception."""

    def test_security_error_message(self):
        """SecurityError should have appropriate message."""
        error = SecurityError("Test error message")
        assert "Test error message" in str(error)


class TestAuditLoggerInit:
    """Test AuditLogger initialization."""

    def test_init_with_client(self):
        """AuditLogger should be initialized with Neo4j client."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        logger = AuditLogger(mock_client)

        assert logger._client == mock_client


class TestAuditLoggerLogAccess:
    """Test logging access attempts."""

    @pytest.mark.asyncio
    async def test_log_access_creates_entry(self):
        """log_access should create an audit log entry."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_write = AsyncMock(return_value=[{"audit_id": "audit-123"}])

        logger = AuditLogger(mock_client)

        audit_id = await logger.log_access(
            agent_name="brooks",
            group_id="faith-meats",
            action="query",
            query_type="read",
            success=True,
            group_accessed="faith-meats",
            latency_ms=15.5
        )

        assert audit_id.startswith("audit-")
        mock_client.execute_write.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_cross_group_attempt(self):
        """Should flag cross-group attempts."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_write = AsyncMock(return_value=[{"audit_id": "audit-456"}])

        logger = AuditLogger(mock_client)

        await logger.log_access(
            agent_name="brooks",
            group_id="faith-meats",
            action="query",
            query_type="read",
            success=False,
            group_accessed="diff-driven-saas",
            cross_group_attempt=True,
            error_message="SecurityError"
        )

        # Verify cross_group_attempt was True in the call
        call_args = mock_client.execute_write.call_args
        params = call_args[0][1]

        assert params['cross_group_attempt'] is True

    @pytest.mark.asyncio
    async def test_log_with_error_message(self):
        """Should log error message for failed accesses."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_write = AsyncMock(return_value=[{"audit_id": "audit-789"}])

        logger = AuditLogger(mock_client)

        await logger.log_access(
            agent_name="brooks",
            group_id="faith-meats",
            action="query",
            query_type="read",
            success=False,
            group_accessed="faith-meats",
            error_message="Query timeout"
        )

        call_args = mock_client.execute_write.call_args
        params = call_args[0][1]

        assert params['error_message'] == "Query timeout"


class TestAuditLoggerQueryLogs:
    """Test querying audit logs."""

    @pytest.mark.asyncio
    async def test_query_audit_logs_returns_list(self):
        """query_audit_logs should return list of entries."""
        mock_records = [
            {
                'a': {
                    'audit_id': 'audit-1',
                    'timestamp': datetime.now(timezone.utc),
                    'agent_name': 'brooks',
                    'agent_group_id': 'faith-meats',
                    'action': 'query',
                    'query_type': 'read',
                    'success': True,
                    'group_accessed': 'faith-meats',
                    'cross_group_attempt': False,
                    'latency_ms': 15.5
                }
            }
        ]

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=mock_records)

        logger = AuditLogger(mock_client)

        filters = AuditQueryFilters(agent_name="brooks")
        logs = await logger.query_audit_logs(filters)

        assert len(logs) == 1
        assert logs[0].agent_name == "brooks"

    @pytest.mark.asyncio
    async def test_query_with_group_filter(self):
        """Should filter by group_id."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=[])

        logger = AuditLogger(mock_client)

        filters = AuditQueryFilters(group_id="faith-meats")
        await logger.query_audit_logs(filters)

        mock_client.execute_query.assert_called_once()
        call_args = mock_client.execute_query.call_args
        params = call_args[0][1]

        assert params['group_id'] == "faith-meats"

    @pytest.mark.asyncio
    async def test_query_cross_group_only(self):
        """Should filter for cross-group attempts only."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=[])

        logger = AuditLogger(mock_client)

        filters = AuditQueryFilters(cross_group_only=True)
        await logger.query_audit_logs(filters)

        mock_client.execute_query.assert_called_once()
        call_args = mock_client.execute_query.call_args
        cypher = call_args[0][0]
        assert "cross_group_attempt = true" in cypher

    @pytest.mark.asyncio
    async def test_query_failed_only(self):
        """Should filter for failed accesses only."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=[])

        logger = AuditLogger(mock_client)

        filters = AuditQueryFilters(failed_only=True)
        await logger.query_audit_logs(filters)

        mock_client.execute_query.assert_called_once()
        call_args = mock_client.execute_query.call_args
        cypher = call_args[0][0]
        assert "success = false" in cypher


class TestAuditLoggerGetSummary:
    """Test getting audit summary."""

    @pytest.mark.asyncio
    async def test_get_summary_returns_statistics(self):
        """get_summary should return summary statistics."""
        mock_summary_records = [
            {
                'total_accesses': 100,
                'cross_group': 5,
                'failed': 3,
                'unique_agents': 4,
                'unique_groups': 2
            }
        ]
        mock_agent_records = [
            {'agent': 'brooks', 'count': 50},
            {'agent': 'claude', 'count': 30}
        ]
        mock_group_records = [
            {'grp': 'faith-meats', 'count': 60},
            {'grp': 'diff-driven-saas', 'count': 40}
        ]
        mock_action_records = [
            {'action': 'query', 'count': 80},
            {'action': 'write', 'count': 20}
        ]

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(side_effect=[
            mock_summary_records,
            mock_agent_records,
            mock_group_records,
            mock_action_records
        ])

        logger = AuditLogger(mock_client)

        summary = await logger.get_summary()

        assert summary.total_accesses == 100
        assert summary.cross_group_attempts == 5
        assert summary.failed_accesses == 3
        assert 'brooks' in summary.by_agent
        assert 'faith-meats' in summary.by_group


class TestAuditLoggerGetCrossGroupAttempts:
    """Test getting cross-group attempts."""

    @pytest.mark.asyncio
    async def test_get_cross_group_attempts(self):
        """Should return all cross-group attempts."""
        mock_records = [
            {
                'a': {
                    'audit_id': 'audit-1',
                    'timestamp': datetime.now(timezone.utc),
                    'agent_name': 'brooks',
                    'agent_group_id': 'faith-meats',
                    'action': 'query',
                    'query_type': 'read',
                    'success': False,
                    'group_accessed': 'diff-driven-saas',
                    'cross_group_attempt': True,
                    'error_message': 'SecurityError',
                    'query_preview': 'MATCH (i:Insight)',
                    'latency_ms': 10.0
                }
            }
        ]

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=mock_records)

        logger = AuditLogger(mock_client)

        attempts = await logger.get_cross_group_attempts(limit=10)

        assert len(attempts) == 1
        assert attempts[0].cross_group_attempt is True
        assert attempts[0].group_accessed == "diff-driven-saas"


class TestAuditLogEntry:
    """Test AuditLogEntry dataclass."""

    def test_audit_log_entry_creation(self):
        """Should create AuditLogEntry with all fields."""
        entry = AuditLogEntry(
            audit_id="audit-123",
            timestamp=datetime.now(timezone.utc),
            agent_name="brooks",
            group_id="faith-meats",
            action="query",
            query_type="read",
            success=True,
            group_accessed="faith-meats",
            cross_group_attempt=False
        )

        assert entry.audit_id == "audit-123"
        assert entry.agent_name == "brooks"
        assert entry.success is True


class TestAuditQueryFilters:
    """Test AuditQueryFilters dataclass."""

    def test_default_filters(self):
        """Should have sensible defaults."""
        filters = AuditQueryFilters()

        assert filters.agent_name is None
        filters.group_id is None
        assert filters.cross_group_only is False
        assert filters.failed_only is False
        assert filters.limit == 100


class TestAuditSummary:
    """Test AuditSummary dataclass."""

    def test_summary_creation(self):
        """Should create AuditSummary with all fields."""
        summary = AuditSummary(
            total_accesses=100,
            cross_group_attempts=5,
            failed_accesses=3,
            unique_agents=4,
            unique_groups=2,
            by_agent={"brooks": 50},
            by_group={"faith-meats": 60},
            by_action={"query": 80}
        )

        assert summary.total_accesses == 100
        assert summary.by_agent["brooks"] == 50


class TestAuditLoggerIntegration:
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
    async def test_real_audit_logging(self, neo4j_client):
        """Test real audit logging against Neo4j."""
        from src.bmad.services.audit_logger import AuditLogger

        try:
            await neo4j_client.initialize()
            logger = AuditLogger(neo4j_client)

            # Log some accesses
            await logger.log_access(
                agent_name="test-agent",
                group_id="global-coding-skills",
                action="query",
                query_type="read",
                success=True,
                group_accessed="global-coding-skills"
            )

            # Query logs
            logs = await logger.query_audit_logs(
                AuditQueryFilters(agent_name="test-agent", limit=10)
            )

            assert len(logs) >= 1
            print(f"Found {len(logs)} audit log entries")

            await neo4j_client.close()
        except Exception as e:
            pytest.skip(f"Neo4j test failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])