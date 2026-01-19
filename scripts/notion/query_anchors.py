"""
Utility functions for querying anchor nodes in Neo4j.

These functions provide convenient access to anchor nodes for
graph traversal and RAG retrieval operations.
"""

import os
from typing import List, Dict, Optional
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Neo4j connection settings
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "changeme")


class AnchorNodeQuerier:
    """Helper class for querying anchor nodes."""
    
    def __init__(self, driver=None):
        """Initialize with optional driver (creates new if not provided)."""
        if driver:
            self.driver = driver
            self._close_driver = False
        else:
            self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
            self._close_driver = True
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._close_driver:
            self.driver.close()
    
    def get_anchors_by_type(self, node_type: str) -> List[Dict]:
        """
        Find all anchor nodes of a specific type.
        
        Args:
            node_type: Type of anchor node (Hub, Teamspace, Database, Agent, etc.)
            
        Returns:
            List of anchor node dictionaries
        """
        with self.driver.session() as session:
            query = """
            MATCH (n:AnchorNode {type: $type})
            RETURN n
            ORDER BY n.title
            """
            result = session.run(query, type=node_type)
            return [dict(record["n"]) for record in result]
    
    def get_anchor_by_notion_id(self, notion_id: str) -> Optional[Dict]:
        """
        Find anchor node by Notion ID.
        
        Args:
            notion_id: Notion page/database ID
            
        Returns:
            Anchor node dictionary or None if not found
        """
        with self.driver.session() as session:
            query = """
            MATCH (n:AnchorNode {notion_id: $notion_id})
            RETURN n
            LIMIT 1
            """
            result = session.run(query, notion_id=notion_id)
            record = result.single()
            return dict(record["n"]) if record else None
    
    def get_anchor_by_id(self, anchor_id: str) -> Optional[Dict]:
        """
        Find anchor node by Neo4j ID.
        
        Args:
            anchor_id: Anchor node UUID
            
        Returns:
            Anchor node dictionary or None if not found
        """
        with self.driver.session() as session:
            query = """
            MATCH (n:AnchorNode {id: $id})
            RETURN n
            LIMIT 1
            """
            result = session.run(query, id=anchor_id)
            record = result.single()
            return dict(record["n"]) if record else None
    
    def get_all_teamspaces(self) -> List[Dict]:
        """Get all teamspace anchor nodes."""
        return self.get_anchors_by_type("Teamspace")
    
    def get_all_agents(self) -> List[Dict]:
        """Get all agent anchor nodes."""
        return self.get_anchors_by_type("Agent")
    
    def get_all_databases(self) -> List[Dict]:
        """Get all database anchor nodes."""
        return self.get_anchors_by_type("Database")
    
    def get_hub_node(self) -> Optional[Dict]:
        """Get the Hub anchor node."""
        results = self.get_anchors_by_type("Hub")
        return results[0] if results else None
    
    def get_related_anchors(
        self,
        anchor_id: str,
        relationship_type: Optional[str] = None,
        direction: str = "outgoing"
    ) -> List[Dict]:
        """
        Get anchors related to a given anchor node.
        
        Args:
            anchor_id: Source anchor node ID
            relationship_type: Optional relationship type filter (e.g., HAS_TEAMSPACE)
            direction: 'outgoing' (default), 'incoming', or 'both'
            
        Returns:
            List of related anchor node dictionaries
        """
        with self.driver.session() as session:
            if relationship_type:
                if direction == "outgoing":
                    query = f"""
                    MATCH (a:AnchorNode {{id: $id}})-[r:{relationship_type}]->(b:AnchorNode)
                    RETURN b
                    ORDER BY b.title
                    """
                elif direction == "incoming":
                    query = f"""
                    MATCH (a:AnchorNode {{id: $id}})<-[r:{relationship_type}]-(b:AnchorNode)
                    RETURN b
                    ORDER BY b.title
                    """
                else:  # both
                    query = f"""
                    MATCH (a:AnchorNode {{id: $id}})-[r:{relationship_type}]-(b:AnchorNode)
                    RETURN b
                    ORDER BY b.title
                    """
            else:
                if direction == "outgoing":
                    query = """
                    MATCH (a:AnchorNode {id: $id})-[r]->(b:AnchorNode)
                    RETURN b
                    ORDER BY b.title
                    """
                elif direction == "incoming":
                    query = """
                    MATCH (a:AnchorNode {id: $id})<-[r]-(b:AnchorNode)
                    RETURN b
                    ORDER BY b.title
                    """
                else:  # both
                    query = """
                    MATCH (a:AnchorNode {id: $id})-[r]-(b:AnchorNode)
                    RETURN b
                    ORDER BY b.title
                    """
            
            result = session.run(query, id=anchor_id)
            return [dict(record["b"]) for record in result]
    
    def get_agents_by_teamspace(self, teamspace_id: str) -> List[Dict]:
        """
        Get all agents associated with a teamspace.
        
        Args:
            teamspace_id: Teamspace anchor node ID
            
        Returns:
            List of agent anchor nodes
        """
        return self.get_related_anchors(teamspace_id, "MANAGED_BY", "incoming")
    
    def get_tags_for_agent(self, agent_id: str) -> List[Dict]:
        """
        Get all tag categories associated with an agent.
        
        Args:
            agent_id: Agent anchor node ID
            
        Returns:
            List of tag category anchor nodes
        """
        return self.get_related_anchors(agent_id, "TAGGED_WITH", "outgoing")
    
    def get_categories_for_database(self, database_id: str) -> List[Dict]:
        """
        Get all knowledge categories for a database.
        
        Args:
            database_id: Database anchor node ID
            
        Returns:
            List of knowledge category anchor nodes
        """
        return self.get_related_anchors(database_id, "HAS_CATEGORY", "outgoing")
    
    def search_anchors_by_title(self, search_term: str) -> List[Dict]:
        """
        Search anchor nodes by title (case-insensitive partial match).
        
        Args:
            search_term: Search term to match against titles
            
        Returns:
            List of matching anchor node dictionaries
        """
        with self.driver.session() as session:
            query = """
            MATCH (n:AnchorNode)
            WHERE toLower(n.title) CONTAINS toLower($term)
            RETURN n
            ORDER BY n.title
            """
            result = session.run(query, term=search_term)
            return [dict(record["n"]) for record in result]
    
    def get_anchor_statistics(self) -> Dict:
        """
        Get statistics about anchor nodes in the graph.
        
        Returns:
            Dictionary with counts by type and total counts
        """
        with self.driver.session() as session:
            query = """
            MATCH (n:AnchorNode)
            RETURN n.type as type, count(n) as count
            ORDER BY count DESC
            """
            result = session.run(query)
            
            stats = {
                "by_type": {},
                "total": 0
            }
            
            for record in result:
                node_type = record["type"]
                count = record["count"]
                stats["by_type"][node_type] = count
                stats["total"] += count
            
            return stats


# Convenience functions for direct use
def get_anchors_by_type(node_type: str) -> List[Dict]:
    """Get anchors by type (convenience function)."""
    with AnchorNodeQuerier() as querier:
        return querier.get_anchors_by_type(node_type)


def get_anchor_by_notion_id(notion_id: str) -> Optional[Dict]:
    """Get anchor by Notion ID (convenience function)."""
    with AnchorNodeQuerier() as querier:
        return querier.get_anchor_by_notion_id(notion_id)


def get_all_teamspaces() -> List[Dict]:
    """Get all teamspaces (convenience function)."""
    with AnchorNodeQuerier() as querier:
        return querier.get_all_teamspaces()


def get_all_agents() -> List[Dict]:
    """Get all agents (convenience function)."""
    with AnchorNodeQuerier() as querier:
        return querier.get_all_agents()


def get_related_anchors(anchor_id: str, relationship_type: Optional[str] = None) -> List[Dict]:
    """Get related anchors (convenience function)."""
    with AnchorNodeQuerier() as querier:
        return querier.get_related_anchors(anchor_id, relationship_type)


if __name__ == "__main__":
    # Example usage
    print("Anchor Node Query Utilities")
    print("=" * 50)
    
    with AnchorNodeQuerier() as querier:
        # Get statistics
        stats = querier.get_anchor_statistics()
        print(f"\nTotal anchor nodes: {stats['total']}")
        print("\nBy type:")
        for node_type, count in sorted(stats["by_type"].items()):
            print(f"  {node_type}: {count}")
        
        # Get Hub node
        hub = querier.get_hub_node()
        if hub:
            print(f"\nHub: {hub.get('title', 'Unknown')}")
        
        # Get all teamspaces
        teamspaces = querier.get_all_teamspaces()
        print(f"\nTeamspaces ({len(teamspaces)}):")
        for ts in teamspaces:
            print(f"  - {ts.get('title', 'Unknown')}")
        
        # Get all agents
        agents = querier.get_all_agents()
        print(f"\nAgents ({len(agents)}):")
        for agent in agents[:5]:  # Show first 5
            print(f"  - {agent.get('title', 'Unknown')}")
        if len(agents) > 5:
            print(f"  ... and {len(agents) - 5} more")



