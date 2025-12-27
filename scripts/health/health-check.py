"""
Health check CLI for Neo4j graph database.

Provides command-line interface to run health checks and expose results
in various formats (text, JSON).

Usage:
    python -m scripts.health.health_check [--format json|text] [--detailed]
"""

import logging
import json
import sys
import argparse
from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

# Import health checker
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.health.checker import HealthChecker

# Load environment
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HealthCheckCLI:
    """CLI interface for health checks."""

    def __init__(self):
        """Initialize health check CLI."""
        neo4j_uri = os.environ.get('NEO4J_URI', 'bolt://neo4j:7687')
        neo4j_user = os.environ.get('NEO4J_USER', 'neo4j')
        neo4j_password = os.environ.get('NEO4J_PASSWORD', 'changeme')

        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        self.checker = HealthChecker(self.driver)

    def run_checks(self, detailed: bool = False) -> dict:
        """Run all health checks.

        Args:
            detailed: Include detailed metrics

        Returns:
            dict: Health check results
        """
        return self.checker.perform_all_checks(detailed=detailed)

    def format_text(self, results: dict) -> str:
        """Format results as human-readable text.

        Args:
            results: Health check results

        Returns:
            str: Formatted text output
        """
        lines = []

        lines.append("=" * 60)
        lines.append(f"Neo4j Health Check Report")
        lines.append(f"Timestamp: {results['timestamp']}")
        lines.append(f"Status: {results['status'].upper()}")
        lines.append("=" * 60)
        lines.append("")

        # Overall status
        if results['status'] == 'unhealthy':
            lines.append(f"⚠ UNHEALTHY - {results['message']}")
            lines.append(f"Failed Check: {results.get('failed_check', 'unknown')}")
            lines.append("")

        # Individual checks
        lines.append("Health Checks:")
        lines.append("-" * 60)

        for check_name, check_result in results.get('checks', {}).items():
            status = check_result['status']
            symbol = "✓" if status == 'pass' else ("✗" if status == 'fail' else "⊘")
            message = check_result.get('message', '')
            duration = check_result.get('duration_ms', 0)

            lines.append(f"  {symbol} {check_name:<25} [{status}]")
            lines.append(f"    Message: {message}")
            lines.append(f"    Duration: {duration}ms")
            lines.append("")

        # Graph statistics (if included)
        if 'graph_stats' in results:
            lines.append("Graph Statistics:")
            lines.append("-" * 60)
            stats = results['graph_stats']
            lines.append(f"  Node Count: {stats.get('node_count', 'N/A')}")
            lines.append(f"  Relationship Count: {stats.get('relationship_count', 'N/A')}")
            lines.append(f"  Last Write: {stats.get('last_write_timestamp', 'N/A')}")
            lines.append("")

        lines.append("=" * 60)

        return "\n".join(lines)

    def format_json(self, results: dict) -> str:
        """Format results as JSON.

        Args:
            results: Health check results

        Returns:
            str: JSON formatted output
        """
        return json.dumps(results, indent=2)

    def close(self):
        """Close database connection."""
        if self.driver:
            self.driver.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Run Neo4j health checks',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                              # Text output (summary)
  %(prog)s --detailed                   # Text output (detailed stats)
  %(prog)s --format json                # JSON output
  %(prog)s --format json --detailed     # JSON output with stats
        """
    )

    parser.add_argument(
        '--format',
        choices=['text', 'json'],
        default='text',
        help='Output format (default: text)'
    )

    parser.add_argument(
        '--detailed',
        action='store_true',
        help='Include detailed metrics (graph statistics, etc)'
    )

    args = parser.parse_args()

    try:
        logger.info("Starting health check...")
        cli = HealthCheckCLI()

        # Run checks
        results = cli.run_checks(detailed=args.detailed)

        # Format and output
        if args.format == 'json':
            output = cli.format_json(results)
        else:
            output = cli.format_text(results)

        print(output)

        # Exit with appropriate code
        exit_code = 0 if results['status'] == 'healthy' else 1
        sys.exit(exit_code)

    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        error_result = {
            'status': 'unhealthy',
            'message': f'Health check failed: {str(e)}',
            'timestamp': '',
            'checks': {}
        }

        if args.format == 'json':
            print(json.dumps(error_result, indent=2))
        else:
            print(f"Health check failed: {str(e)}")

        sys.exit(1)

    finally:
        cli.close()


if __name__ == '__main__':
    main()
