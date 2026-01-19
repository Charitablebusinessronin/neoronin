"""
Create anchor nodes in Neo4j from extracted Notion data.

This script reads the extracted anchor nodes JSON and creates
them in Neo4j with proper labels and properties.
"""

import json
import os
import sys
from typing import Dict, List, Optional
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Neo4j connection settings
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "changeme")


def create_anchor_node(driver, node_data: Dict) -> Optional[str]:
    """
    Create a single anchor node in Neo4j.
    
    Args:
        driver: Neo4j driver instance
        node_data: Dictionary containing node properties
        
    Returns:
        Node ID if successful, None otherwise
    """
    with driver.session() as session:
        # Build Cypher query
        query = """
        MERGE (n:AnchorNode {id: $id})
        SET n.notion_id = $notion_id,
            n.title = $title,
            n.type = $type,
            n.url = $url,
            n.description = $description,
            n.tags = $tags,
            n.created_at = $created_at,
            n.updated_at = $updated_at,
            n.metadata = $metadata
        RETURN n.id as id
        """
        
        result = session.run(
            query,
            id=node_data["id"],
            notion_id=node_data.get("notion_id"),
            title=node_data["title"],
            type=node_data["type"],
            url=node_data.get("url"),
            description=node_data.get("description", ""),
            tags=node_data.get("tags", []),
            created_at=node_data.get("created_at"),
            updated_at=node_data.get("updated_at"),
            metadata=json.dumps(node_data.get("metadata", {}))
        )
        
        record = result.single()
        return record["id"] if record else None


def create_all_anchor_nodes(anchor_nodes: List[Dict], driver) -> Dict[str, int]:
    """
    Create all anchor nodes in Neo4j.
    
    Args:
        anchor_nodes: List of anchor node dictionaries
        driver: Neo4j driver instance
        
    Returns:
        Dictionary with creation statistics
    """
    stats = {
        "total": len(anchor_nodes),
        "created": 0,
        "failed": 0,
        "by_type": {}
    }
    
    for node in anchor_nodes:
        try:
            node_id = create_anchor_node(driver, node)
            if node_id:
                stats["created"] += 1
                node_type = node["type"]
                stats["by_type"][node_type] = stats["by_type"].get(node_type, 0) + 1
            else:
                stats["failed"] += 1
        except Exception as e:
            print(f"Error creating node {node.get('title', 'unknown')}: {e}")
            stats["failed"] += 1
    
    return stats


def initialize_schema(driver):
    """
    Initialize Neo4j schema for anchor nodes.
    
    Args:
        driver: Neo4j driver instance
    """
    with driver.session() as session:
        # Read and execute schema file
        schema_file = os.path.join(
            os.path.dirname(__file__),
            "..",
            "setup",
            "create_anchor_schema.cypher"
        )
        
        if os.path.exists(schema_file):
            with open(schema_file, "r") as f:
                schema_cypher = f.read()
            
            # Execute each statement (split by semicolons)
            statements = [s.strip() for s in schema_cypher.split(";") if s.strip() and not s.strip().startswith("//")]
            
            for statement in statements:
                try:
                    session.run(statement)
                except Exception as e:
                    # Ignore errors for IF NOT EXISTS constraints/indexes
                    if "already exists" not in str(e).lower():
                        print(f"Warning: Schema statement failed: {e}")


def main():
    """Main function to create anchor nodes."""
    # Load extracted anchor nodes
    input_file = "notion_anchor_nodes.json"
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found. Run extract_anchor_nodes.py first.")
        sys.exit(1)
    
    with open(input_file, "r") as f:
        anchor_nodes = json.load(f)
    
    print(f"Loading {len(anchor_nodes)} anchor nodes...")
    
    # Connect to Neo4j
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        # Initialize schema
        print("Initializing Neo4j schema...")
        initialize_schema(driver)
        
        # Create all nodes
        print("Creating anchor nodes in Neo4j...")
        stats = create_all_anchor_nodes(anchor_nodes, driver)
        
        # Print results
        print(f"\n✓ Anchor node creation complete")
        print(f"  Total: {stats['total']}")
        print(f"  Created: {stats['created']}")
        print(f"  Failed: {stats['failed']}")
        print(f"\n  By type:")
        for node_type, count in sorted(stats["by_type"].items()):
            print(f"    {node_type}: {count}")
        
    finally:
        driver.close()


if __name__ == "__main__":
    main()



