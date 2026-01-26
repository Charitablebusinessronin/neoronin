"""
Schema Deployer for BMAD Agent Memory System.

Provides functionality to:
- Deploy schema constraints and indexes from Cypher files
- Verify schema deployment against Neo4j
- Execute initialization scripts for AIAgent nodes
- Measure deployment performance
"""

import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from neo4j import GraphDatabase, Driver

logger = logging.getLogger(__name__)


class SchemaDeployer:
    """Manages BMAD schema deployment and verification."""

    def __init__(self, driver: Driver):
        """Initialize schema deployer.

        Args:
            driver: Neo4j driver connection
        """
        self.driver = driver
        self.schema_path = Path(__file__).parent.parent.parent / "scripts" / "schema"

    def get_constraints(self) -> List[Dict[str, str]]:
        """Retrieve deployed constraints from Neo4j.

        Returns:
            List of constraint information dictionaries
        """
        with self.driver.session() as session:
            result = session.run("SHOW CONSTRAINTS")
            constraints = []
            for record in result:
                constraints.append({
                    'name': record.get('name', ''),
                    'type': record.get('type', ''),
                    'labels': record.get('labelsOrTypes', []),
                    'properties': record.get('properties', [])
                })
            return constraints

    def get_indexes(self) -> List[Dict[str, Any]]:
        """Retrieve deployed indexes from Neo4j.

        Returns:
            List of index information dictionaries
        """
        with self.driver.session() as session:
            result = session.run("SHOW INDEXES")
            indexes = []
            for record in result:
                indexes.append({
                    'name': record.get('name', ''),
                    'type': record.get('type', ''),
                    'labels': record.get('labelsOrTypes', []),
                    'properties': record.get('properties', []),
                    'unique': record.get('isUnique', False)
                })
            return indexes

    def deploy_from_file(self, filename: str = "bmad_schema.cypher") -> Dict[str, Any]:
        """Deploy schema from a Cypher file.

        Args:
            filename: Name of the Cypher file to deploy

        Returns:
            Dictionary with deployment results and timing
        """
        schema_file = self.schema_path / filename
        if not schema_file.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_file}")

        start_time = time.time()
        cypher_content = schema_file.read_text()

        # Split on semicolons and filter empty statements
        statements = [s.strip() for s in cypher_content.split(';') if s.strip() and not s.strip().startswith('//')]

        with self.driver.session() as session:
            for statement in statements:
                if statement:
                    try:
                        session.run(statement)
                    except Exception as e:
                        # Ignore "already exists" errors
                        if "already exists" not in str(e).lower():
                            logger.warning(f"Statement execution warning: {e}")

        duration = time.time() - start_time

        return {
            'success': True,
            'statements_executed': len(statements),
            'duration_seconds': duration,
            'file': str(schema_file)
        }

    def deploy_agents_from_file(self, filename: str = "bmad_agent_init.cypher") -> Dict[str, Any]:
        """Deploy agent initialization from a Cypher file.

        Args:
            filename: Name of the Cypher file to deploy

        Returns:
            Dictionary with deployment results and timing
        """
        init_file = self.schema_path / filename
        if not init_file.exists():
            raise FileNotFoundError(f"Agent init file not found: {init_file}")

        start_time = time.time()
        cypher_content = init_file.read_text()

        # Split on semicolons and filter empty statements
        statements = [s.strip() for s in cypher_content.split(';') if s.strip() and not s.strip().startswith('//')]

        with self.driver.session() as session:
            for statement in statements:
                if statement:
                    try:
                        session.run(statement)
                    except Exception as e:
                        # Ignore "already exists" errors for MERGE statements
                        if "already exists" not in str(e).lower() and "constraint" not in str(e).lower():
                            logger.warning(f"Statement execution warning: {e}")

        duration = time.time() - start_time

        return {
            'success': True,
            'statements_executed': len(statements),
            'duration_seconds': duration,
            'file': str(init_file)
        }

    def query_agent_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Query an AIAgent node by name.

        Args:
            name: Name of the agent to find

        Returns:
            Agent node data or None if not found
        """
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (a:AIAgent {name: $name})
                RETURN a.name as name, a.role as role, a.capabilities as capabilities,
                       a.status as status, a.integration_points as integration_points
                """,
                name=name
            )
            record = result.single()
            if record:
                return {
                    'name': record['name'],
                    'role': record['role'],
                    'capabilities': record['capabilities'],
                    'status': record['status'],
                    'integration_points': record['integration_points']
                }
            return None

    def verify_all_agents(self) -> Dict[str, Any]:
        """Verify all 9 BMAD agents are properly registered.

        Returns:
            Dictionary with verification results
        """
        expected_agents = [
            'Jay', 'Winston', 'Brooks', 'Dutch', 'Troy',
            'Bob', 'Allura', 'BMad Master', 'BMad Orchestrator'
        ]

        with self.driver.session() as session:
            result = session.run("MATCH (a:AIAgent) RETURN a.name as name, a.role as role, a.status as status")
            agents = {r['name']: {'role': r['role'], 'status': r['status']} for r in result}

        missing = [a for a in expected_agents if a not in agents]
        extra = [a for a in agents.keys() if a not in expected_agents]

        return {
            'all_present': len(missing) == 0,
            'expected_count': len(expected_agents),
            'actual_count': len(agents),
            'missing_agents': missing,
            'extra_agents': extra,
            'agents': agents
        }

    def verify_project_groups(self) -> Dict[str, Any]:
        """Verify project group Brain nodes exist.

        Returns:
            Dictionary with verification results
        """
        expected_groups = [
            'faith-meats',
            'diff-driven-saas',
            'global-coding-skills'
        ]

        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (b:Brain)
                WHERE b.group_id IN $groups
                RETURN b.name as name, b.group_id as group_id, b.scope as scope
                """,
                groups=expected_groups
            )
            groups = {r['group_id']: {'name': r['name'], 'scope': r['scope']} for r in result}

        missing = [g for g in expected_groups if g not in groups]

        return {
            'all_present': len(missing) == 0,
            'expected_groups': expected_groups,
            'actual_groups': list(groups.keys()),
            'missing': missing,
            'group_details': groups
        }

    def full_deployment(self) -> Dict[str, Any]:
        """Run complete BMAD schema and agent deployment.

        Returns:
            Comprehensive deployment results
        """
        results = {
            'schema_deployment': None,
            'agent_initialization': None,
            'agents_verified': None,
            'groups_verified': None,
            'total_duration': 0
        }

        start_total = time.time()

        # Deploy schema
        results['schema_deployment'] = self.deploy_from_file()

        # Initialize agents
        results['agent_initialization'] = self.deploy_agents_from_file()

        # Verify
        results['agents_verified'] = self.verify_all_agents()
        results['groups_verified'] = self.verify_project_groups()

        results['total_duration'] = time.time() - start_total

        # Overall success
        results['success'] = (
            results['schema_deployment']['success'] and
            results['agent_initialization']['success'] and
            results['agents_verified']['all_present'] and
            results['groups_verified']['all_present']
        )

        return results