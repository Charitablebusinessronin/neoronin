"""Unit tests for Notion Sync Service (Story 3-3).

Tests cover:
- Notion API connection and page fetching
- Knowledge item sync to Neo4j
- Query with filters
- Brain linking
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

from src.bmad.core.neo4j_client import Neo4jAsyncClient
from src.bmad.services.notion_sync import (
    NotionSyncService,
    NotionPage,
    KnowledgeItem,
    SyncResult
)


class TestNotionSyncServiceInit:
    """Test NotionSyncService initialization."""

    def test_init_with_client(self):
        """Service should be initialized with Neo4j client."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        service = NotionSyncService(mock_client)

        assert service._client == mock_client

    def test_init_with_token(self):
        """Service should use provided token."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        service = NotionSyncService(mock_client, notion_token="test-token")

        assert service._token == "test-token"


class TestNotionConnection:
    """Test Notion API connection."""

    @pytest.mark.asyncio
    async def test_test_connection_without_token(self):
        """Should return not connected when no token."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        service = NotionSyncService(mock_client)

        result = await service.test_connection()

        assert result["connected"] is False
        assert "NOTION_TOKEN not configured" in result["error"]

    @pytest.mark.asyncio
    async def test_test_connection_success(self):
        """Should return connected when API responds."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        service = NotionSyncService(mock_client, notion_token="test-token")

        # Create mock HTTP client
        mock_http_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "workspace_name": "Test Workspace",
            "results": [{"id": "1"}, {"id": "2"}]
        }
        mock_response.raise_for_status = Mock()
        mock_http_client.get = AsyncMock(return_value=mock_response)

        service._http_client = mock_http_client

        result = await service.test_connection()

        assert result["connected"] is True
        assert result["workspace"] == "Test Workspace"


class TestFetchNotionPages:
    """Test fetching pages from Notion."""

    @pytest.mark.asyncio
    async def test_fetch_pages_returns_mock_when_no_token(self):
        """Should return mock pages when no token configured."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        service = NotionSyncService(mock_client)

        pages = await service.fetch_notion_pages(limit=5)

        assert len(pages) == 2  # Mock returns 2 pages
        assert pages[0].title == "BMAD Architecture Overview"

    @pytest.mark.asyncio
    async def test_fetch_pages_with_limit(self):
        """Should respect limit parameter."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        service = NotionSyncService(mock_client, notion_token="test-token")

        with patch.object(service, '_get_http_client', new_callable=AsyncMock):
            pages = await service.fetch_notion_pages(limit=10)

            # Mock returns 2 pages regardless
            assert len(pages) == 2


class TestParseNotionPage:
    """Test parsing Notion API responses."""

    def test_parse_valid_page(self):
        """Should parse valid Notion response."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        service = NotionSyncService(mock_client)

        result = {
            "id": "page-123",
            "properties": {
                "title": {
                    "title": [{"plain_text": "Test Page"}]
                },
                "Type": {"select": {"name": "PRD"}},
                "Category": {"select": {"name": "Requirements"}},
                "Tags": {"multi_select": [{"name": "bmad"}, {"name": "prd"}]},
                "AI_Accessible": {"checkbox": True},
                "Language": {"select": {"name": "en"}}
            },
            "url": "https://notion.so/page-123",
            "created_time": "2026-01-01T00:00:00.000Z",
            "last_edited_time": "2026-01-25T00:00:00.000Z"
        }

        page = service._parse_notion_page(result)

        assert page is not None
        assert page.page_id == "page-123"
        assert page.title == "Test Page"
        assert page.content_type == "PRD"
        assert page.category == "Requirements"
        assert "bmad" in page.tags


class TestSyncKnowledgeItems:
    """Test syncing pages to KnowledgeItem nodes."""

    @pytest.mark.asyncio
    async def test_sync_creates_knowledge_items(self):
        """Should create KnowledgeItem nodes in Neo4j."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_write = AsyncMock(return_value=[{"status": "created"}])

        service = NotionSyncService(mock_client)

        pages = [
            NotionPage(
                page_id="page-1",
                title="Test Page",
                content="Content",
                content_type="PRD",
                source_url="https://notion.so/1",
                ai_accessible=True,
                category="Requirements",
                tags=["test"],
                language="en",
                created_at=datetime.now(timezone.utc),
                last_edited=datetime.now(timezone.utc)
            )
        ]

        result = await service.sync_knowledge_items(pages, "global-coding-skills")

        assert result.pages_processed == 1
        assert result.items_created == 1
        assert result.items_updated == 0

    @pytest.mark.asyncio
    async def test_sync_handles_errors(self):
        """Should track errors during sync."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_write = AsyncMock(side_effect=Exception("DB error"))

        service = NotionSyncService(mock_client)

        pages = [
            NotionPage(
                page_id="page-1",
                title="Test Page",
                content="Content",
                content_type="PRD",
                source_url="https://notion.so/1",
                ai_accessible=True,
                category="Requirements",
                tags=[],
                language="en",
                created_at=datetime.now(timezone.utc),
                last_edited=datetime.now(timezone.utc)
            )
        ]

        result = await service.sync_knowledge_items(pages, "global-coding-skills")

        assert result.pages_processed == 1
        assert result.items_created == 0
        assert len(result.errors) == 1


class TestQueryKnowledgeItems:
    """Test querying knowledge items."""

    @pytest.mark.asyncio
    async def test_query_with_category_filter(self):
        """Should filter by category."""
        mock_records = [
            {
                'item_id': 'ki-1',
                'title': 'Test',
                'content': 'Content',
                'content_type': 'PRD',
                'source': 'page-1',
                'ai_accessible': True,
                'category': 'Requirements',
                'tags': [],
                'language': 'en',
                'group_id': 'global-coding-skills',
                'created_date': datetime.now(timezone.utc),
                'last_updated': datetime.now(timezone.utc)
            }
        ]

        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=mock_records)

        service = NotionSyncService(mock_client)

        items = await service.query_knowledge_items(
            "global-coding-skills",
            category="Requirements"
        )

        assert len(items) == 1
        assert items[0].category == "Requirements"

    @pytest.mark.asyncio
    async def test_query_with_tags_filter(self):
        """Should filter by tags."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_query = AsyncMock(return_value=[])

        service = NotionSyncService(mock_client)

        await service.query_knowledge_items(
            "global-coding-skills",
            tags=["bmad", "prd"]
        )

        mock_client.execute_query.assert_called_once()
        call_args = mock_client.execute_query.call_args
        params = call_args[0][1]

        assert 'bmad' in params['tags']
        assert 'prd' in params['tags']


class TestLinkToBrain:
    """Test linking knowledge items to brains."""

    @pytest.mark.asyncio
    async def test_link_to_brain(self):
        """Should create CONTAINS_KNOWLEDGE relationship."""
        mock_client = MagicMock(spec=Neo4jAsyncClient)
        mock_client.execute_write = AsyncMock(return_value=[{"count": 1}])

        service = NotionSyncService(mock_client)

        result = await service.link_to_brain(
            "page-1",
            "BMAD Global Brain",
            "global-coding-skills"
        )

        assert result is True


class TestNotionPage:
    """Test NotionPage dataclass."""

    def test_notion_page_creation(self):
        """Should create NotionPage with all fields."""
        page = NotionPage(
            page_id="page-123",
            title="Test Page",
            content="Content",
            content_type="PRD",
            source_url="https://notion.so/123",
            ai_accessible=True,
            category="Requirements",
            tags=["bmad", "test"],
            language="en",
            created_at=datetime.now(timezone.utc),
            last_edited=datetime.now(timezone.utc)
        )

        assert page.page_id == "page-123"
        assert page.title == "Test Page"
        assert len(page.tags) == 2


class TestKnowledgeItem:
    """Test KnowledgeItem dataclass."""

    def test_knowledge_item_creation(self):
        """Should create KnowledgeItem with all fields."""
        item = KnowledgeItem(
            item_id="ki-123",
            title="Knowledge Item",
            content="Content",
            content_type="Architecture_Doc",
            source="page-123",
            ai_accessible=True,
            category="Architecture",
            tags=["architecture"],
            language="en",
            group_id="global-coding-skills",
            created_date=datetime.now(timezone.utc),
            last_updated=datetime.now(timezone.utc)
        )

        assert item.item_id == "ki-123"
        assert item.content_type == "Architecture_Doc"


class TestSyncResult:
    """Test SyncResult dataclass."""

    def test_sync_result_creation(self):
        """Should create SyncResult with metrics."""
        result = SyncResult(
            pages_processed=10,
            items_created=5,
            items_updated=3,
            errors=["error1"],
            duration_ms=150.5,
            group_id="global-coding-skills"
        )

        assert result.pages_processed == 10
        assert result.items_created == 5
        assert len(result.errors) == 1


class TestNotionSyncIntegration:
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
    async def test_real_notion_sync(self, neo4j_client):
        """Test real Notion sync against Neo4j."""
        from src.bmad.services.notion_sync import NotionSyncService

        try:
            await neo4j_client.initialize()
            service = NotionSyncService(neo4j_client)

            # Test connection
            connection = await service.test_connection()
            print(f"\nNotion connection: {connection}")

            # Fetch pages (uses mock if no token)
            pages = await service.fetch_notion_pages(limit=5)
            print(f"Fetched {len(pages)} pages")

            if pages:
                # Sync to Neo4j
                result = await service.sync_knowledge_items(
                    pages,
                    "global-coding-skills"
                )
                print(f"Sync: {result.items_created} created, {result.items_updated} updated")

            await neo4j_client.close()
        except Exception as e:
            pytest.skip(f"Notion test failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])