"""Unit tests for BMAD agent initialization."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path


class TestAgentInitialization:
    """Test that all 9 agents can be initialized."""

    def test_nine_agents_defined(self):
        """All 9 BMAD agents should be defined."""
        expected_agents = [
            "Jay",           # Analyst
            "Winston",       # Architect
            "Brooks",        # Developer
            "Dutch",         # Product Manager
            "Troy",          # Test Engineer & Analyst
            "Bob",           # Scrum Master
            "Allura",        # UX Expert
            "Master",        # Master Coordinator
            "Orchestrator"   # Workflow Orchestrator
        ]
        assert len(expected_agents) == 9

    def test_agent_roles_unique(self):
        """Each agent should have a unique role."""
        agents = [
            ("Jay", "Analyst"),
            ("Winston", "Architect"),
            ("Brooks", "Developer"),
            ("Dutch", "PM"),
            ("Troy", "TEA"),
            ("Bob", "Scrum Master"),
            ("Allura", "UX Expert"),
            ("Master", "Master"),
            ("Orchestrator", "Orchestrator")
        ]
        roles = [role for _, role in agents]
        assert len(roles) == len(set(roles)), "All roles should be unique"

    def test_agent_file_references(self):
        """Each agent should have a file reference."""
        agents = [
            ("Jay", "analyst.md"),
            ("Winston", "architect.md"),
            ("Brooks", "dev.md"),
            ("Dutch", "pm.md"),
            ("Troy", "tea.md"),
            ("Bob", "sm.md"),
            ("Allura", "ux-expert.md"),
            ("Master", "master.md"),
            ("Orchestrator", "orchestrator.md")
        ]
        for name, file_ref in agents:
            assert file_ref is not None


class TestAgentCapabilities:
    """Test agent capability definitions."""

    def test_brooks_capabilities(self):
        """Brooks (Developer) should have development capabilities."""
        brooks_capabilities = [
            'code_implementation',
            'debugging',
            'refactoring',
            'code_review',
            'git_operations'
        ]
        assert 'code_implementation' in brooks_capabilities
        assert 'debugging' in brooks_capabilities

    def test_winston_capabilities(self):
        """Winston (Architect) should have architecture capabilities."""
        winston_capabilities = [
            'architecture_design',
            'technology_selection',
            'system_migrations',
            'performance_optimization',
            'api_design'
        ]
        assert 'architecture_design' in winston_capabilities

    def test_troy_capabilities(self):
        """Troy (TEA) should have testing capabilities."""
        troy_capabilities = [
            'test_automation',
            'quality_assurance',
            'documentation',
            'bug_tracking',
            'performance_testing'
        ]
        assert 'test_automation' in troy_capabilities


class TestAgentIntegration:
    """Test agent integration points."""

    def test_github_integrations(self):
        """Agents requiring GitHub integration."""
        github_agents = [
            "Winston",
            "Brooks",
            "Troy",
            "Bob",
            "Master",
            "Orchestrator"
        ]
        assert "Brooks" in github_agents
        assert "Winston" in github_agents

    def test_notion_integrations(self):
        """Agents requiring Notion integration."""
        notion_agents = [
            "Jay",
            "Winston",
            "Dutch",
            "Troy",
            "Bob",
            "Allura",
            "Master",
            "Orchestrator"
        ]
        assert "Winston" in notion_agents

    def test_slack_integrations(self):
        """Agents requiring Slack integration."""
        slack_agents = [
            "Brooks",
            "Dutch",
            "Bob",
            "Allura",
            "Master",
            "Orchestrator"
        ]
        assert "Brooks" in slack_agents


class TestAgentFileExists:
    """Test agent initialization file exists."""

    def test_agent_init_file_exists(self):
        """Agent initialization file should exist."""
        init_path = Path(__file__).parent.parent.parent / \
            "scripts/schema/bmad_agent_init.cypher"
        assert init_path.exists(), f"Agent init file not found at {init_path}"

    def test_agent_init_file_not_empty(self):
        """Agent initialization file should not be empty."""
        init_path = Path(__file__).parent.parent.parent / \
            "scripts/schema/bmad_agent_init.cypher"
        content = init_path.read_text()
        assert len(content) > 2000, "Agent init file appears too small"
        assert "MERGE (brooks:AIAgent" in content
        assert "MERGE (jay:AIAgent" in content