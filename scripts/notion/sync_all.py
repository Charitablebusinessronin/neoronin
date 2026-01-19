#!/usr/bin/env python3
"""
Main orchestration script for Notion anchor node sync.

This script runs the complete workflow:
1. Extract anchor nodes from Notion
2. Create schema in Neo4j
3. Create anchor nodes in Neo4j
4. Create relationships
5. Sync to Graphiti memory

Usage:
    python scripts/notion/sync_all.py
"""

import sys
import os
import subprocess
from pathlib import Path

# Add scripts directory to path
scripts_dir = Path(__file__).parent.parent
sys.path.insert(0, str(scripts_dir.parent))


def run_script(script_name: str, description: str) -> bool:
    """
    Run a Python script and return success status.
    
    Args:
        script_name: Name of the script file
        description: Description of what the script does
        
    Returns:
        True if successful, False otherwise
    """
    script_path = Path(__file__).parent / script_name
    
    if not script_path.exists():
        print(f"Error: {script_path} not found")
        return False
    
    print(f"\n{'='*60}")
    print(f"Step: {description}")
    print(f"Running: {script_name}")
    print(f"{'='*60}\n")
    
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=scripts_dir.parent,
            check=True,
            capture_output=False
        )
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"Error running {script_name}: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False


def main():
    """Run the complete sync workflow."""
    print("Notion Anchor Nodes Sync Workflow")
    print("=" * 60)
    print("This will:")
    print("  1. Extract anchor nodes from Notion Hub")
    print("  2. Create Neo4j schema for anchor nodes")
    print("  3. Create anchor nodes in Neo4j")
    print("  4. Create relationships between anchor nodes")
    print("  5. Sync anchor nodes to Graphiti memory")
    print("=" * 60)
    
    # Step 1: Extract anchor nodes
    if not run_script("extract_anchor_nodes.py", "Extract anchor nodes from Notion"):
        print("\n❌ Extraction failed. Stopping workflow.")
        sys.exit(1)
    
    # Step 2: Create schema (this is done automatically in create_anchor_nodes.py)
    # But we can verify the schema file exists
    schema_file = Path(__file__).parent.parent / "setup" / "create_anchor_schema.cypher"
    if not schema_file.exists():
        print(f"\n⚠️  Warning: Schema file not found: {schema_file}")
        print("   Schema will be created automatically during node creation.")
    
    # Step 3: Create anchor nodes
    if not run_script("create_anchor_nodes.py", "Create anchor nodes in Neo4j"):
        print("\n❌ Node creation failed. Stopping workflow.")
        sys.exit(1)
    
    # Step 4: Create relationships
    if not run_script("create_anchor_relationships.py", "Create relationships between anchor nodes"):
        print("\n❌ Relationship creation failed. Stopping workflow.")
        sys.exit(1)
    
    # Step 5: Sync to Graphiti
    if not run_script("sync_to_graphiti.py", "Sync anchor nodes to Graphiti memory"):
        print("\n❌ Graphiti sync failed. Stopping workflow.")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✅ Complete! All anchor nodes have been synced.")
    print("=" * 60)
    print("\nYou can now query anchor nodes using:")
    print("  python scripts/notion/query_anchors.py")
    print("\nOr use the AnchorNodeQuerier class in your code:")
    print("  from scripts.notion.query_anchors import AnchorNodeQuerier")


if __name__ == "__main__":
    main()



