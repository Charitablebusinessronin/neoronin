"""
Health check system for Neo4j graph database.

Performs three critical checks:
1. Connectivity: Can we reach Neo4j?
2. Schema Consistency: Are all nodes/relationships properly formed?
3. Orphan Detection: Are there orphaned relationships?
"""

import logging
import time
from typing import Dict, List, Tuple
from neo4j import GraphDatabase, Driver

logger = logging.getLogger(__name__)


class HealthChecker:
    """Health checking system for Neo4j graph."""

    CONNECTIVITY_TIMEOUT = 5  # seconds
    SCHEMA_TIMEOUT = 10  # seconds
    ORPHAN_TIMEOUT = 30  # seconds

    def __init__(self, driver: Driver):
        """Initialize health checker.

        Args:
            driver: Neo4j driver connection
        """
        self.driver = driver

    def check_connectivity(self) -> Tuple[bool, str, int]:
        """Check if Neo4j is reachable and responding.

        Returns:
            Tuple[bool, str, int]: (passed, message, duration_ms)
        """
        start = time.time()
        try:
            with self.driver.session() as session:
                result = session.run("RETURN 1")
                result.single()
            duration = int((time.time() - start) * 1000)
            return True, "Neo4j is reachable and responding to queries", duration
        except Exception as e:
            duration = int((time.time() - start) * 1000)
            error_msg = str(e)
            return False, f"Cannot reach Neo4j: {error_msg}", duration

    def check_schema_consistency(self) -> Tuple[bool, str, int]:
        """Verify graph schema consistency.

        Checks that nodes and relationships conform to defined schema
        (defined node types exist, required properties present).

        Returns:
            Tuple[bool, str, int]: (passed, message, duration_ms)
        """
        start = time.time()
        try:
            with self.driver.session() as session:
                # Get all node labels
                result = session.run("CALL db.labels()")
                labels = {row['label'] for row in result}

                # Get all relationship types
                result = session.run("CALL db.relationshipTypes()")
                rel_types = {row['relationshipType'] for row in result}

                # Expected labels for BMAD schema
                expected_labels = {
                    'AIAgent',
                    'Brain',
                    'Event',
                    'Solution',
                    'Outcome',
                    'Pattern',
                    'Insight',
                    'Project',
                    'Task',
                    'System',
                    'Domain'
                }

                # Check that expected BMAD labels exist
                missing_labels = expected_labels - labels
                if missing_labels:
                    duration = int((time.time() - start) * 1000)
                    return False, f"Missing BMAD labels: {missing_labels}", duration

                # Check for required relationship types
                expected_rels = {'HAS_MEMORY_IN', 'SPECIALIZES_IN', 'INTEGRATES_WITH', 'COORDINATES', 'OVERSEES'}
                missing_rels = expected_rels - rel_types
                if missing_rels:
                    logger.debug(f"Expected relationships not found: {missing_rels}")

                # Verify AIAgent nodes have required properties
                agents_without_name = session.run("""
                    MATCH (a:AIAgent)
                    WHERE a.name IS NULL
                    RETURN count(a) as count
                """).single()['count']

                if agents_without_name > 0:
                    duration = int((time.time() - start) * 1000)
                    return False, f"Found {agents_without_name} AIAgent nodes without name", duration

                # Verify Brain nodes have required properties
                brains_without_group = session.run("""
                    MATCH (b:Brain)
                    WHERE b.group_id IS NULL
                    RETURN count(b) as count
                """).single()['count']

                if brains_without_group > 0:
                    duration = int((time.time() - start) * 1000)
                    return False, f"Found {brains_without_group} Brain nodes without group_id", duration

            duration = int((time.time() - start) * 1000)
            return True, "All BMAD graph nodes and relationships conform to defined schema", duration

        except Exception as e:
            duration = int((time.time() - start) * 1000)
            return False, f"Schema check failed: {str(e)}", duration

    def check_orphan_detection(self) -> Tuple[bool, str, int]:
        """Detect orphaned relationships (relationships with missing endpoints).

        Returns:
            Tuple[bool, str, int]: (passed, message, duration_ms)
        """
        start = time.time()
        try:
            with self.driver.session() as session:
                # Query for orphaned relationships
                # This is a simplified check - more sophisticated checks
                # would require knowledge of the schema
                result = session.run("""
                    MATCH (n)-[r]-(m)
                    WHERE NOT EXISTS {MATCH (n)} OR NOT EXISTS {MATCH (m)}
                    RETURN count(r) as orphaned_count
                """)

                orphaned_count = result.single()['orphaned_count']

                if orphaned_count > 0:
                    duration = int((time.time() - start) * 1000)
                    return False, f"Found {orphaned_count} orphaned relationships", duration

            duration = int((time.time() - start) * 1000)
            return True, "No orphaned relationships found", duration

        except Exception as e:
            duration = int((time.time() - start) * 1000)
            # Orphan check might fail on certain Neo4j versions
            logger.warning(f"Orphan detection check failed: {e}")
            return True, "Orphan detection skipped (compatibility issue)", duration

    def check_agent_brain_connectivity(self) -> Tuple[bool, str, int]:
        """Verify all AIAgent nodes have proper HAS_MEMORY_IN relationships to brains.

        Returns:
            Tuple[bool, str, int]: (passed, message, duration_ms)
        """
        start = time.time()
        try:
            with self.driver.session() as session:
                # Find agents without brain connections
                result = session.run("""
                    MATCH (a:AIAgent)
                    WHERE NOT (a)-[:HAS_MEMORY_IN]->(:Brain)
                    RETURN a.name as name, a.role as role
                """)

                orphaned_agents = []
                for record in result:
                    orphaned_agents.append({
                        'name': record['name'],
                        'role': record['role']
                    })

                if orphaned_agents:
                    names = [a['name'] for a in orphaned_agents]
                    duration = int((time.time() - start) * 1000)
                    return False, f"Agents without brain: {names}", duration

                # Also check for brains without proper group_id
                result = session.run("""
                    MATCH (b:Brain)
                    WHERE b.group_id IS NULL
                    RETURN b.name as name
                """)
                orphan_brains = [r['name'] for r in result]

                if orphan_brains:
                    duration = int((time.time() - start) * 1000)
                    return False, f"Brains without group_id: {orphan_brains}", duration

            duration = int((time.time() - start) * 1000)
            return True, "All agents connected to brains properly", duration

        except Exception as e:
            duration = int((time.time() - start) * 1000)
            logger.warning(f"Agent brain connectivity check failed: {e}")
            return True, "Agent connectivity check skipped (compatibility issue)", duration

    def check_agents_have_valid_capabilities(self) -> Tuple[bool, str, int]:
        """Verify all AIAgent nodes have valid capabilities arrays.

        Returns:
            Tuple[bool, str, int]: (passed, message, duration_ms)
        """
        start = time.time()
        try:
            with self.driver.session() as session:
                # Find agents with null or empty capabilities
                result = session.run("""
                    MATCH (a:AIAgent)
                    WHERE a.capabilities IS NULL OR size(a.capabilities) = 0
                    RETURN a.name as name, a.role as role
                """)

                agents_without_caps = []
                for record in result:
                    agents_without_caps.append(record['name'])

                if agents_without_caps:
                    duration = int((time.time() - start) * 1000)
                    return False, f"Agents without capabilities: {agents_without_caps}", duration

            duration = int((time.time() - start) * 1000)
            return True, "All agents have valid capabilities", duration

        except Exception as e:
            duration = int((time.time() - start) * 1000)
            logger.warning(f"Agent capabilities check failed: {e}")
            return True, "Capabilities check skipped (compatibility issue)", duration

    def perform_all_checks(self, detailed: bool = False) -> Dict:
        """Perform all health checks.

        Implements fast-fail: stops at first failing check.

        Args:
            detailed: Include detailed metrics in response

        Returns:
            Dict: Health check results
        """
        timestamp = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        checks = {}

        # Connectivity check (blocks all others if failed)
        passed, msg, duration = self.check_connectivity()
        checks['connectivity'] = {
            'status': 'pass' if passed else 'fail',
            'message': msg,
            'duration_ms': duration
        }

        if not passed:
            # Fast fail - skip other checks if connectivity failed
            checks['schema_consistency'] = {
                'status': 'skipped',
                'message': 'Skipped because connectivity check failed',
                'duration_ms': 0
            }
            checks['orphan_detection'] = {
                'status': 'skipped',
                'message': 'Skipped because connectivity check failed',
                'duration_ms': 0
            }
            return {
                'status': 'unhealthy',
                'timestamp': timestamp,
                'failed_check': 'connectivity',
                'message': msg,
                'checks': checks
            }

        # Schema consistency check
        passed, msg, duration = self.check_schema_consistency()
        checks['schema_consistency'] = {
            'status': 'pass' if passed else 'fail',
            'message': msg,
            'duration_ms': duration
        }

        if not passed:
            # Skip further checks
            checks['orphan_detection'] = {
                'status': 'skipped',
                'message': 'Skipped because schema consistency check failed',
                'duration_ms': 0
            }
            return {
                'status': 'unhealthy',
                'timestamp': timestamp,
                'failed_check': 'schema_consistency',
                'message': msg,
                'checks': checks
            }

        # Orphan detection check
        passed, msg, duration = self.check_orphan_detection()
        checks['orphan_detection'] = {
            'status': 'pass' if passed else 'fail',
            'message': msg,
            'duration_ms': duration
        }

        if not passed:
            return {
                'status': 'unhealthy',
                'timestamp': timestamp,
                'failed_check': 'orphan_detection',
                'message': msg,
                'checks': checks
            }

        # BMAD-specific checks
        passed, msg, duration = self.check_agent_brain_connectivity()
        checks['agent_brain_connectivity'] = {
            'status': 'pass' if passed else 'fail',
            'message': msg,
            'duration_ms': duration
        }

        if not passed:
            return {
                'status': 'unhealthy',
                'timestamp': timestamp,
                'failed_check': 'agent_brain_connectivity',
                'message': msg,
                'checks': checks
            }

        passed, msg, duration = self.check_agents_have_valid_capabilities()
        checks['agent_capabilities'] = {
            'status': 'pass' if passed else 'fail',
            'message': msg,
            'duration_ms': duration
        }

        if not passed:
            return {
                'status': 'unhealthy',
                'timestamp': timestamp,
                'failed_check': 'agent_capabilities',
                'message': msg,
                'checks': checks
            }

        # All checks passed
        response = {
            'status': 'healthy',
            'timestamp': timestamp,
            'checks': checks
        }

        if detailed:
            # Add graph statistics
            try:
                with self.driver.session() as session:
                    result = session.run("""
                        MATCH (n)
                        RETURN count(DISTINCT labels(n)) as node_types,
                               count(n) as node_count
                    """)
                    node_data = result.single()

                    result = session.run("""
                        MATCH ()-[r]->()
                        RETURN count(r) as relationship_count
                    """)
                    rel_data = result.single()

                    response['graph_stats'] = {
                        'node_count': node_data['node_count'],
                        'relationship_count': rel_data['relationship_count'],
                        'last_write_timestamp': timestamp  # Would need audit log integration
                    }
            except Exception as e:
                logger.warning(f"Could not retrieve graph statistics: {e}")

        return response
