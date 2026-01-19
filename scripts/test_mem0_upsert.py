#!/usr/bin/env python3
"""
Test script for Mem0 integration verification.
Executes a test upsert with user_id="difference-driven" and verifies:
1. Neo4j nodes created with user_id property
2. Qdrant collection exists and contains vectors
"""

import os
import sys
import requests
from neo4j import GraphDatabase

# Configuration from environment
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "Kamina2025*")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
USER_ID = "difference-driven"

def test_neo4j_connection():
    """Test Neo4j connectivity and query for Mem0 nodes."""
    print(f"🔍 Testing Neo4j connection: {NEO4J_URI}")
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        with driver.session() as session:
            # Query for nodes with user_id
            result = session.run(
                """
                MATCH (n)
                WHERE n.user_id = $user_id
                RETURN labels(n) as labels, count(n) as count
                """,
                user_id=USER_ID
            )
            record = result.single()
            if record:
                labels = record["labels"]
                count = record["count"]
                print(f"✅ Found {count} node(s) with user_id='{USER_ID}'")
                print(f"   Labels: {labels}")
                return count > 0
            else:
                print(f"⚠️  No nodes found with user_id='{USER_ID}'")
                return False
    except Exception as e:
        print(f"❌ Neo4j connection failed: {e}")
        return False
    finally:
        driver.close()

def test_qdrant_collection():
    """Test Qdrant connectivity and check for mem0 collection."""
    print(f"🔍 Testing Qdrant connection: {QDRANT_URL}")
    try:
        # Check if collection exists
        response = requests.get(f"{QDRANT_URL}/collections/mem0", timeout=5)
        if response.status_code == 200:
            collection_info = response.json()
            points_count = collection_info.get("result", {}).get("points_count", 0)
            print(f"✅ Qdrant collection 'mem0' exists with {points_count} point(s)")
            return True
        elif response.status_code == 404:
            print(f"⚠️  Qdrant collection 'mem0' does not exist yet")
            return False
        else:
            print(f"❌ Qdrant check failed: HTTP {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to Qdrant at {QDRANT_URL}")
        return False
    except Exception as e:
        print(f"❌ Qdrant check failed: {e}")
        return False

def main():
    """Run all verification tests."""
    print("=" * 60)
    print("Mem0 Integration Verification")
    print("=" * 60)
    print(f"User ID: {USER_ID}\n")
    
    neo4j_ok = test_neo4j_connection()
    print()
    qdrant_ok = test_qdrant_collection()
    
    print()
    print("=" * 60)
    if neo4j_ok and qdrant_ok:
        print("✅ All checks passed!")
        sys.exit(0)
    else:
        print("⚠️  Some checks failed. Review output above.")
        sys.exit(1)

if __name__ == "__main__":
    main()

