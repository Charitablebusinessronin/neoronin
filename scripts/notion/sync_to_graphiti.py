"""
Sync anchor nodes to Graphiti memory system.

This script creates Graphiti memory facts and episodes for each anchor node,
enabling AI agents to query and recall anchor node information.
"""

import json
import os
import sys
from typing import Dict, List
from datetime import datetime
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Neo4j connection settings
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "changeme")

# Graphiti group ID
GROUP_ID = os.getenv("GRAPHITI_GROUP_ID", "difference-driven")


def create_graphiti_fact(driver, anchor_node: Dict) -> bool:
    """
    Create a Graphiti memory fact for an anchor node.
    
    Graphiti facts are stored as nodes with label 'Fact' and properties:
    - group_id: Memory group identifier
    - content: The fact content
    - created_at: Timestamp
    - metadata: Additional metadata (including link to anchor node)
    
    Args:
        driver: Neo4j driver instance
        anchor_node: Anchor node dictionary
        
    Returns:
        True if successful, False otherwise
    """
    with driver.session() as session:
        # Create fact content
        fact_content = f"Anchor node: {anchor_node['title']} (Type: {anchor_node['type']})"
        if anchor_node.get("description"):
            fact_content += f". {anchor_node['description']}"
        if anchor_node.get("url"):
            fact_content += f" URL: {anchor_node['url']}"
        
        # Create fact node
        query = """
        MATCH (anchor:AnchorNode {id: $anchor_id})
        CREATE (f:Fact {
            group_id: $group_id,
            content: $content,
            created_at: $created_at,
            metadata: $metadata
        })
        CREATE (anchor)-[:HAS_GRAPHITI_FACT]->(f)
        RETURN f
        """
        
        metadata = {
            "anchor_node_id": anchor_node["id"],
            "anchor_node_type": anchor_node["type"],
            "notion_id": anchor_node.get("notion_id"),
            "tags": anchor_node.get("tags", [])
        }
        
        result = session.run(
            query,
            anchor_id=anchor_node["id"],
            group_id=GROUP_ID,
            content=fact_content,
            created_at=datetime.utcnow().isoformat(),
            metadata=json.dumps(metadata)
        )
        
        return result.single() is not None


def create_sync_episode(driver, stats: Dict) -> bool:
    """
    Create a Graphiti episode for the sync operation.
    
    Args:
        driver: Neo4j driver instance
        stats: Statistics about the sync operation
        
    Returns:
        True if successful, False otherwise
    """
    with driver.session() as session:
        # Create episode content
        episode_content = {
            "task": "Notion Anchor Nodes Sync",
            "description": f"Synced {stats['total']} anchor nodes from Notion Hub to Neo4j and Graphiti",
            "solution": f"Created {stats['facts_created']} Graphiti facts linked to anchor nodes",
            "outcome": "success" if stats['facts_failed'] == 0 else "partial",
            "insight": "Anchor nodes enable efficient graph traversal for RAG retrieval. Each anchor serves as an entry point for 1-2 hop context expansion.",
            "confidence": 0.95
        }
        
        query = """
        CREATE (e:Episode {
            group_id: $group_id,
            content: $content,
            created_at: $created_at,
            metadata: $metadata
        })
        RETURN e
        """
        
        metadata = {
            "sync_stats": stats,
            "anchor_node_types": stats.get("by_type", {}),
            "sync_timestamp": datetime.utcnow().isoformat()
        }
        
        result = session.run(
            query,
            group_id=GROUP_ID,
            content=json.dumps(episode_content),
            created_at=datetime.utcnow().isoformat(),
            metadata=json.dumps(metadata)
        )
        
        return result.single() is not None


def sync_all_anchor_nodes(anchor_nodes: List[Dict], driver) -> Dict[str, int]:
    """
    Sync all anchor nodes to Graphiti memory.
    
    Args:
        anchor_nodes: List of anchor node dictionaries
        driver: Neo4j driver instance
        
    Returns:
        Dictionary with sync statistics
    """
    stats = {
        "total": len(anchor_nodes),
        "facts_created": 0,
        "facts_failed": 0,
        "by_type": {}
    }
    
    for node in anchor_nodes:
        try:
            if create_graphiti_fact(driver, node):
                stats["facts_created"] += 1
                node_type = node["type"]
                stats["by_type"][node_type] = stats["by_type"].get(node_type, 0) + 1
            else:
                stats["facts_failed"] += 1
        except Exception as e:
            print(f"Error creating Graphiti fact for {node.get('title', 'unknown')}: {e}")
            stats["facts_failed"] += 1
    
    return stats


def main():
    """Main function to sync anchor nodes to Graphiti."""
    # Load anchor nodes
    input_file = "notion_anchor_nodes.json"
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found. Run create_anchor_nodes.py first.")
        sys.exit(1)
    
    with open(input_file, "r") as f:
        anchor_nodes = json.load(f)
    
    print(f"Syncing {len(anchor_nodes)} anchor nodes to Graphiti memory...")
    print(f"Using group_id: {GROUP_ID}")
    
    # Connect to Neo4j
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        # Sync all nodes
        print("Creating Graphiti memory facts...")
        stats = sync_all_anchor_nodes(anchor_nodes, driver)
        
        # Create sync episode
        print("Creating sync episode...")
        episode_created = create_sync_episode(driver, stats)
        
        # Print results
        print(f"\n✓ Graphiti sync complete")
        print(f"  Total anchor nodes: {stats['total']}")
        print(f"  Facts created: {stats['facts_created']}")
        print(f"  Facts failed: {stats['facts_failed']}")
        print(f"  Episode created: {'Yes' if episode_created else 'No'}")
        print(f"\n  Facts by type:")
        for node_type, count in sorted(stats["by_type"].items()):
            print(f"    {node_type}: {count}")
        
    finally:
        driver.close()


if __name__ == "__main__":
    main()



