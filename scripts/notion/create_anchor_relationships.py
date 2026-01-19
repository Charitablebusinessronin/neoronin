"""
Create relationships between anchor nodes in Neo4j.

This script establishes the organizational structure by connecting
anchor nodes with appropriate relationship types.
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


def find_hub_node(driver) -> Optional[str]:
    """Find the Hub anchor node ID."""
    with driver.session() as session:
        result = session.run(
            "MATCH (n:AnchorNode {type: 'Hub'}) RETURN n.id as id LIMIT 1"
        )
        record = result.single()
        return record["id"] if record else None


def create_relationship(
    driver,
    from_id: str,
    to_id: str,
    rel_type: str,
    properties: Optional[Dict] = None
) -> bool:
    """
    Create a relationship between two anchor nodes.
    
    Args:
        driver: Neo4j driver instance
        from_id: Source node ID
        to_id: Target node ID
        rel_type: Relationship type (e.g., HAS_TEAMSPACE)
        properties: Optional relationship properties
        
    Returns:
        True if successful, False otherwise
    """
    with driver.session() as session:
        if properties:
            query = f"""
            MATCH (a:AnchorNode {{id: $from_id}})
            MATCH (b:AnchorNode {{id: $to_id}})
            MERGE (a)-[r:{rel_type}]->(b)
            SET r += $properties
            RETURN r
            """
            result = session.run(query, from_id=from_id, to_id=to_id, properties=properties)
        else:
            query = f"""
            MATCH (a:AnchorNode {{id: $from_id}})
            MATCH (b:AnchorNode {{id: $to_id}})
            MERGE (a)-[r:{rel_type}]->(b)
            RETURN r
            """
            result = session.run(query, from_id=from_id, to_id=to_id)
        
        return result.single() is not None


def create_hub_relationships(driver, hub_id: str, anchor_nodes: List[Dict]) -> Dict[str, int]:
    """
    Create relationships from Hub to all other anchor nodes.
    
    Args:
        driver: Neo4j driver instance
        hub_id: Hub node ID
        anchor_nodes: List of all anchor nodes
        
    Returns:
        Dictionary with relationship creation statistics
    """
    stats = {
        "total": 0,
        "created": 0,
        "failed": 0,
        "by_type": {}
    }
    
    # Map relationship types by node type
    rel_type_map = {
        "Teamspace": "HAS_TEAMSPACE",
        "Database": "HAS_DATABASE",
        "Agent": "HAS_AGENT",
        "TagCategory": "HAS_TAG",
        "KnowledgeCategory": "HAS_CATEGORY"
    }
    
    for node in anchor_nodes:
        # Skip the hub node itself
        if node["type"] == "Hub":
            continue
        
        node_id = node["id"]
        node_type = node["type"]
        rel_type = rel_type_map.get(node_type)
        
        if not rel_type:
            continue
        
        stats["total"] += 1
        
        try:
            # Create relationship from Hub to this node
            if create_relationship(driver, hub_id, node_id, rel_type):
                stats["created"] += 1
                stats["by_type"][rel_type] = stats["by_type"].get(rel_type, 0) + 1
            else:
                stats["failed"] += 1
        except Exception as e:
            print(f"Error creating relationship {rel_type} for {node.get('title', 'unknown')}: {e}")
            stats["failed"] += 1
    
    return stats


def create_agent_tag_relationships(driver, anchor_nodes: List[Dict]) -> Dict[str, int]:
    """
    Create relationships between agents and tag categories.
    
    Args:
        driver: Neo4j driver instance
        anchor_nodes: List of all anchor nodes
        
    Returns:
        Dictionary with relationship creation statistics
    """
    stats = {
        "total": 0,
        "created": 0,
        "failed": 0
    }
    
    # Find all agents and tag categories
    agents = [n for n in anchor_nodes if n["type"] == "Agent"]
    tag_categories = {n["title"]: n["id"] for n in anchor_nodes if n["type"] == "TagCategory"}
    
    # Map agents to relevant tags based on their descriptions/metadata
    agent_tag_mapping = {
        "Troy Davis": ["Programming", "Technical"],
        "Steven": ["Project Management", "Content"],
        "Tommy Oliver": ["Technical", "AI/ML"],
        "Ari Khalid": ["Research & Discovery", "Content"],
        "John": ["Project Management"],
        "Troy": ["Programming", "Technical"],
        "Sally": ["Content"],
        "BMad Builder": ["Technical", "AI/ML"],
        "Frederick P. Brooks Jr.": ["Project Management", "Content"]
    }
    
    for agent in agents:
        agent_name = agent["title"]
        agent_id = agent["id"]
        
        # Get tags for this agent
        tags = agent_tag_mapping.get(agent_name, [])
        
        for tag_name in tags:
            tag_id = tag_categories.get(tag_name)
            if tag_id:
                stats["total"] += 1
                try:
                    if create_relationship(driver, agent_id, tag_id, "TAGGED_WITH"):
                        stats["created"] += 1
                    else:
                        stats["failed"] += 1
                except Exception as e:
                    print(f"Error creating TAGGED_WITH for {agent_name} -> {tag_name}: {e}")
                    stats["failed"] += 1
    
    return stats


def create_database_category_relationships(driver, anchor_nodes: List[Dict]) -> Dict[str, int]:
    """
    Create relationships between databases and knowledge categories.
    
    Args:
        driver: Neo4j driver instance
        anchor_nodes: List of all anchor nodes
        
    Returns:
        Dictionary with relationship creation statistics
    """
    stats = {
        "total": 0,
        "created": 0,
        "failed": 0
    }
    
    # Find Master Knowledge Base database
    kb_db = next((n for n in anchor_nodes if n["title"] == "Master Knowledge Base"), None)
    if not kb_db:
        return stats
    
    kb_db_id = kb_db["id"]
    
    # Find all knowledge categories
    kb_categories = [n for n in anchor_nodes if n["type"] == "KnowledgeCategory"]
    
    for category in kb_categories:
        stats["total"] += 1
        try:
            if create_relationship(driver, kb_db_id, category["id"], "HAS_CATEGORY"):
                stats["created"] += 1
            else:
                stats["failed"] += 1
        except Exception as e:
            print(f"Error creating HAS_CATEGORY for {category.get('title', 'unknown')}: {e}")
            stats["failed"] += 1
    
    return stats


def create_reverse_relationships(driver) -> Dict[str, int]:
    """
    Create reverse BELONGS_TO relationships from all nodes to Hub.
    
    Args:
        driver: Neo4j driver instance
        
    Returns:
        Dictionary with relationship creation statistics
    """
    stats = {
        "total": 0,
        "created": 0,
        "failed": 0
    }
    
    hub_id = find_hub_node(driver)
    if not hub_id:
        print("Warning: Hub node not found, skipping reverse relationships")
        return stats
    
    with driver.session() as session:
        # Find all non-Hub anchor nodes
        result = session.run(
            "MATCH (n:AnchorNode) WHERE n.type <> 'Hub' RETURN n.id as id"
        )
        
        for record in result:
            node_id = record["id"]
            stats["total"] += 1
            try:
                if create_relationship(driver, node_id, hub_id, "BELONGS_TO"):
                    stats["created"] += 1
                else:
                    stats["failed"] += 1
            except Exception as e:
                print(f"Error creating BELONGS_TO for node {node_id}: {e}")
                stats["failed"] += 1
    
    return stats


def main():
    """Main function to create all relationships."""
    # Load anchor nodes
    input_file = "notion_anchor_nodes.json"
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found. Run create_anchor_nodes.py first.")
        sys.exit(1)
    
    with open(input_file, "r") as f:
        anchor_nodes = json.load(f)
    
    print("Creating anchor node relationships...")
    
    # Connect to Neo4j
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        # Find Hub node
        hub_id = find_hub_node(driver)
        if not hub_id:
            print("Error: Hub node not found. Run create_anchor_nodes.py first.")
            sys.exit(1)
        
        # Create Hub relationships
        print("Creating Hub relationships...")
        hub_stats = create_hub_relationships(driver, hub_id, anchor_nodes)
        print(f"  Created: {hub_stats['created']}, Failed: {hub_stats['failed']}")
        
        # Create agent-tag relationships
        print("Creating agent-tag relationships...")
        tag_stats = create_agent_tag_relationships(driver, anchor_nodes)
        print(f"  Created: {tag_stats['created']}, Failed: {tag_stats['failed']}")
        
        # Create database-category relationships
        print("Creating database-category relationships...")
        db_stats = create_database_category_relationships(driver, anchor_nodes)
        print(f"  Created: {db_stats['created']}, Failed: {db_stats['failed']}")
        
        # Create reverse relationships
        print("Creating reverse BELONGS_TO relationships...")
        reverse_stats = create_reverse_relationships(driver)
        print(f"  Created: {reverse_stats['created']}, Failed: {reverse_stats['failed']}")
        
        # Summary
        total_created = hub_stats["created"] + tag_stats["created"] + db_stats["created"] + reverse_stats["created"]
        total_failed = hub_stats["failed"] + tag_stats["failed"] + db_stats["failed"] + reverse_stats["failed"]
        
        print(f"\n✓ Relationship creation complete")
        print(f"  Total created: {total_created}")
        print(f"  Total failed: {total_failed}")
        
    finally:
        driver.close()


if __name__ == "__main__":
    main()

