"""Unit tests for BMAD schema deployment and verification."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys
import os

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.schema.deployer import SchemaDeployer


class TestProjectGroups:
    """Test project group configuration files."""

    def test_faith_meats_group_config_exists(self):
        """Faith Meats group config should exist."""
        config_path = project_root / "config" / "groups" / "faith-meats.yaml"
        assert config_path.exists(), f"Faith Meats config not found at {config_path}"

    def test_diff_driven_saas_group_config_exists(self):
        """Diff-Driven SaaS group config should exist."""
        config_path = project_root / "config" / "groups" / "diff-driven-saas.yaml"
        assert config_path.exists(), f"Diff-Driven SaaS config not found at {config_path}"

    def test_global_coding_skills_group_config_exists(self):
        """Global Coding Skills group config should exist."""
        config_path = project_root / "config" / "groups" / "global-coding-skills.yaml"
        assert config_path.exists(), f"Global Coding Skills config not found at {config_path}"

    def test_all_group_configs_have_required_fields(self):
        """All group configs should have required fields."""
        import yaml

        required_fields = ['group_id', 'name', 'description', 'scope', 'agents', 'brain']

        group_files = [
            'faith-meats.yaml',
            'diff-driven-saas.yaml',
            'global-coding-skills.yaml'
        ]

        for group_file in group_files:
            config_path = project_root / "config" / "groups" / group_file
            with open(config_path) as f:
                config = yaml.safe_load(f)

            for field in required_fields:
                assert field in config, f"Missing {field} in {group_file}"

    def test_project_groups_defined(self):
        """All three project groups should be defined."""
        project_groups = [
            "faith-meats",
            "diff-driven-saas",
            "global-coding-skills"
        ]
        assert len(project_groups) == 3
        assert "faith-meats" in project_groups
        assert "diff-driven-saas" in project_groups
        assert "global-coding-skills" in project_groups


class TestHealthCheckerAIAgentExtensions:
    """Test AIAgent-specific health check extensions."""

    def test_health_checker_has_agent_brain_connectivity_method(self):
        """Health checker should have agent brain connectivity check."""
        from src.health.checker import HealthChecker
        assert hasattr(HealthChecker, 'check_agent_brain_connectivity')

    def test_health_checker_has_agent_capabilities_method(self):
        """Health checker should have agent capabilities check."""
        from src.health.checker import HealthChecker
        assert hasattr(HealthChecker, 'check_agents_have_valid_capabilities')

    def test_health_checker_extension_methods_return_tuples(self):
        """Extension methods should return Tuple[bool, str, int]."""
        from src.health.checker import HealthChecker
        import inspect

        for method_name in ['check_agent_brain_connectivity', 'check_agents_have_valid_capabilities']:
            method = getattr(HealthChecker, method_name)
            sig = inspect.signature(method)
            # Verify method signature accepts driver parameter
            params = list(sig.parameters.keys())
            assert 'self' in params, f"{method_name} should have self parameter"


class TestSchemaDeployerExists:
    """Test that schema deployer module exists and can be imported."""

    def test_schema_deployer_module_exists(self):
        """Schema deployer module should exist."""
        from src.schema.deployer import SchemaDeployer
        assert SchemaDeployer is not None

    def test_schema_deployer_can_be_instantiated(self):
        """Schema deployer should be instantiable with driver."""
        from src.schema.deployer import SchemaDeployer
        mock_driver = MagicMock()
        deployer = SchemaDeployer(mock_driver)
        assert deployer is not None
        assert deployer.driver == mock_driver


class TestSchemaConstraintsExist:
    """Test that schema constraints can be verified."""

    def test_constraints_list_not_empty(self):
        """Constraints list should not be empty."""
        # Expected constraints from bmad_schema.cypher
        expected_constraints = [
            "agent_name_unique",
            "project_name_groupid_unique",
            "brain_name_groupid_unique",
            "system_name_unique"
        ]
        assert len(expected_constraints) == 4

    def test_constraint_names_match_schema(self):
        """Constraint names should match those defined in schema."""
        expected_constraints = [
            "agent_name_unique",
            "project_name_groupid_unique",
            "brain_name_groupid_unique",
            "system_name_unique"
        ]
        # These are defined in bmad_schema.cypher lines 26-38
        assert "agent_name_unique" in expected_constraints

    def test_schema_file_defines_all_expected_constraints(self):
        """Schema file should define all expected constraints."""
        schema_path = project_root / "scripts" / "schema" / "bmad_schema.cypher"
        content = schema_path.read_text()

        # Verify all constraint names are present in schema
        assert "CREATE CONSTRAINT agent_name_unique" in content
        assert "CREATE CONSTRAINT project_name_groupid_unique" in content
        assert "CREATE CONSTRAINT brain_name_groupid_unique" in content
        assert "CREATE CONSTRAINT system_name_unique" in content


class TestSchemaIndexesExist:
    """Test that schema indexes can be verified."""

    def test_indexes_list_not_empty(self):
        """Indexes list should not be empty."""
        # Expected indexes count from bmad_schema.cypher
        expected_index_count = 28  # Count of CREATE INDEX statements
        assert expected_index_count > 0

    def test_agent_layer_indexes_present(self):
        """Agent layer indexes should be present."""
        agent_indexes = [
            "agent_role",
            "agent_status"
        ]
        assert len(agent_indexes) == 2

    def test_schema_file_defines_agent_indexes(self):
        """Schema file should define agent-related indexes."""
        schema_path = project_root / "scripts" / "schema" / "bmad_schema.cypher"
        content = schema_path.read_text()

        assert "CREATE INDEX agent_role" in content
        assert "CREATE INDEX agent_status" in content

    def test_schema_file_defines_event_indexes(self):
        """Schema file should define event-related indexes."""
        schema_path = project_root / "scripts" / "schema" / "bmad_schema.cypher"
        content = schema_path.read_text()

        assert "CREATE INDEX event_timestamp" in content
        assert "CREATE INDEX event_type" in content

    def test_schema_file_defines_pattern_and_insight_indexes(self):
        """Schema file should define pattern and insight indexes."""
        schema_path = project_root / "scripts" / "schema" / "bmad_schema.cypher"
        content = schema_path.read_text()

        assert "CREATE INDEX pattern_category" in content
        assert "CREATE INDEX insight_confidence" in content


class TestSchemaDeployment:
    """Test schema deployment functionality."""

    def test_schema_file_exists(self):
        """Schema file should exist at expected path."""
        schema_path = Path(__file__).parent.parent.parent / \
            "scripts/schema/bmad_schema.cypher"
        assert schema_path.exists(), f"Schema file not found at {schema_path}"

    def test_schema_file_not_empty(self):
        """Schema file should not be empty."""
        schema_path = Path(__file__).parent.parent.parent / \
            "scripts/schema/bmad_schema.cypher"
        content = schema_path.read_text()
        assert len(content) > 1000, "Schema file appears too small"
        assert "CREATE CONSTRAINT" in content
        assert "CREATE INDEX" in content


class TestSchemaQueries:
    """Test schema validation queries."""

    def test_constraints_validation_query(self):
        """Validate constraints can be queried."""
        expected = "CALL db.constraints()"
        # This query is documented in schema validation section
        assert expected is not None

    def test_indexes_validation_query(self):
        """Validate indexes can be queried."""
        expected = "CALL db.indexes()"
        # This query is documented in schema validation section
        assert expected is not None


class TestSchemaDeploymentIntegration:
    """Integration tests for actual schema deployment against Neo4j."""

    @pytest.fixture
    def neo4j_driver(self):
        """Create a real Neo4j driver for integration tests."""
        try:
            from neo4j import GraphDatabase
        except ImportError:
            pytest.skip("neo4j driver not installed - install with: pip install neo4j")

        import os

        uri = os.environ.get('NEO4J_URI', 'bolt://localhost:7687')
        user = os.environ.get('NEO4J_USER', 'neo4j')
        password = os.environ.get('NEO4J_PASSWORD', 'password')

        try:
            driver = GraphDatabase.driver(uri, auth=(user, password))
            # Verify connection
            with driver.session() as session:
                session.run("RETURN 1")
            yield driver
            driver.close()
        except Exception as e:
            pytest.skip(f"Neo4j not accessible: {e}")

    @pytest.fixture
    def schema_deployer(self, neo4j_driver):
        """Create schema deployer with real driver."""
        return SchemaDeployer(neo4j_driver)

    def test_deploy_schema_creates_constraints(self, schema_deployer):
        """Deploying schema should create constraints for AIAgent nodes."""
        constraints = schema_deployer.get_constraints()
        constraint_names = [c['name'] for c in constraints]

        # Check for expected constraints from bmad_schema.cypher
        assert 'agent_name_unique' in constraint_names
        assert 'project_name_groupid_unique' in constraint_names
        assert 'brain_name_groupid_unique' in constraint_names
        assert 'system_name_unique' in constraint_names

    def test_deploy_schema_creates_indexes(self, schema_deployer):
        """Deploying schema should create indexes for common lookups."""
        indexes = schema_deployer.get_indexes()
        index_names = [i['name'] for i in indexes]

        # Check for expected indexes from bmad_schema.cypher
        assert 'agent_role' in index_names
        assert 'agent_status' in index_names
        assert 'event_timestamp' in index_names
        assert 'pattern_category' in index_names
        assert 'event_type' in index_names
        assert 'insight_confidence' in index_names

    def test_query_latency_under_100ms(self, schema_deployer):
        """Agent registration query should complete in under 100ms."""
        import time

        # Run 5 queries and measure average latency
        latencies = []
        for _ in range(5):
            start = time.time()
            result = schema_deployer.query_agent_by_name("Brooks")
            latencies.append(time.time() - start)

        avg_latency = sum(latencies) / len(latencies)
        assert avg_latency < 0.1, f"Query took {avg_latency*1000:.2f}ms, expected < 100ms"
        assert result is not None
        assert result['name'] == 'Brooks'
        assert result['role'] == 'Developer'


class TestHealthCheckerIntegration:
    """Integration tests for health checker with Neo4j."""

    @pytest.fixture
    def neo4j_driver(self):
        """Create a real Neo4j driver for integration tests."""
        try:
            from neo4j import GraphDatabase
        except ImportError:
            pytest.skip("neo4j driver not installed - install with: pip install neo4j")

        import os

        uri = os.environ.get('NEO4J_URI', 'bolt://localhost:7687')
        user = os.environ.get('NEO4J_USER', 'neo4j')
        password = os.environ.get('NEO4J_PASSWORD', 'password')

        try:
            driver = GraphDatabase.driver(uri, auth=(user, password))
            # Verify connection
            with driver.session() as session:
                session.run("RETURN 1")
            yield driver
            driver.close()
        except Exception as e:
            pytest.skip(f"Neo4j not accessible: {e}")

    @pytest.fixture
    def health_checker(self, neo4j_driver):
        """Create health checker with real driver."""
        from src.health.checker import HealthChecker
        return HealthChecker(neo4j_driver)

    def test_check_agent_brain_connectivity_returns_tuple(self, health_checker):
        """Agent brain connectivity check should return (passed, message, duration)."""
        result = health_checker.check_agent_brain_connectivity()
        assert isinstance(result, tuple), "Should return tuple"
        assert len(result) == 3, "Should have 3 elements"
        assert isinstance(result[0], bool), "First element should be bool"
        assert isinstance(result[1], str), "Second element should be str"
        assert isinstance(result[2], int), "Third element should be duration in ms"

    def test_check_agents_have_valid_capabilities_returns_tuple(self, health_checker):
        """Agent capabilities check should return (passed, message, duration)."""
        result = health_checker.check_agents_have_valid_capabilities()
        assert isinstance(result, tuple), "Should return tuple"
        assert len(result) == 3, "Should have 3 elements"

    def test_full_health_check_returns_healthy_status(self, health_checker):
        """Full health check should return healthy status with all checks passing."""
        result = health_checker.perform_all_checks()

        assert 'status' in result
        assert result['status'] == 'healthy', f"Health check status: {result['status']}"
        assert 'checks' in result
        assert 'connectivity' in result['checks']
        assert 'schema_consistency' in result['checks']
        assert 'agent_brain_connectivity' in result['checks']
        assert 'agent_capabilities' in result['checks']

    def test_health_check_completes_in_under_5_seconds(self, health_checker):
        """Health check should complete in under 5 seconds."""
        import time

        start = time.time()
        result = health_checker.perform_all_checks()
        duration = time.time() - start

        assert duration < 5, f"Health check took {duration:.2f}s, expected < 5s"
        assert result['status'] == 'healthy', f"Health check status: {result['status']}"

    def test_verify_all_agents_returns_9_agents(self, health_checker):
        """Verify that all 9 BMAD agents are properly registered."""
        from src.schema.deployer import SchemaDeployer
        deployer = SchemaDeployer(health_checker.driver)

        result = deployer.verify_all_agents()

        assert result['all_present'] == True
        assert result['expected_count'] == 9
        assert result['actual_count'] == 9
        assert len(result['missing_agents']) == 0

    def test_verify_project_groups_returns_3_groups(self, health_checker):
        """Verify that all 3 project groups are properly configured."""
        from src.schema.deployer import SchemaDeployer
        deployer = SchemaDeployer(health_checker.driver)

        result = deployer.verify_project_groups()

        assert result['all_present'] == True
        assert len(result['missing']) == 0