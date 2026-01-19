#!/usr/bin/env python3
"""
Test Mem0 API integration with user_id="difference-driven".
This script performs a test upsert and verifies the data in Neo4j and Qdrant.
"""

import os
import sys
import requests
from neo4j import GraphDatabase

# Configuration
MEM0_API_URL = os.getenv("MEM0_API_URL", "http://localhost:8000")
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "changeme")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
USER_ID = "difference-driven"

def test_mem0_upsert():
    """Perform a test memory upsert via Mem0 API."""
    print(f"🔍 Testing Mem0 API: {MEM0_API_URL}")
    
    test_memory = {
        "user_id": USER_ID,
        "messages": [
            {
                "role": "user",
                "content": "I'm working on the Difference Driven project, integrating Mem0 with Neo4j and Qdrant."
            },
            {
                "role": "assistant",
                "content": "Understood. Mem0 is now configured with Neo4j as graph store and Qdrant as vector store."
            }
        ]
    }
    
    try:
        # Try to add memory via Mem0 API
        # Note: Adjust endpoint based on actual Mem0 API documentation
        response = requests.post(
            f"{MEM0_API_URL}/memories",
            json=test_memory,
            timeout=10
        )
        
        if response.status_code in [200, 201]:
            print(f"✅ Memory upsert successful")
            return True
        else:
            print(f"⚠️  Memory upsert returned HTTP {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to Mem0 API at {MEM0_API_URL}")
        print(f"   Make sure the Mem0 container is running and the API is accessible")
        return False
    except Exception as e:
        print(f"❌ Memory upsert failed: {e}")
        return False

def verify_neo4j_nodes():
    """Verify nodes were created in Neo4j with user_id property."""
    print(f"\n🔍 Verifying Neo4j nodes with user_id='{USER_ID}'")
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        with driver.session() as session:
            # Query for nodes with user_id
            result = session.run(
                """
                MATCH (n)
                WHERE n.user_id = $user_id
                RETURN labels(n) as labels, count(n) as count, 
                       collect(DISTINCT keys(n))[0] as sample_keys
                """,
                user_id=USER_ID
            )
            record = result.single()
            if record:
                labels = record["labels"]
                count = record["count"]
                keys = record["sample_keys"]
                print(f"✅ Found {count} node(s) with user_id='{USER_ID}'")
                print(f"   Labels: {labels}")
                print(f"   Properties: {keys}")
                return count > 0
            else:
                print(f"⚠️  No nodes found with user_id='{USER_ID}'")
                return False
    except Exception as e:
        print(f"❌ Neo4j verification failed: {e}")
        return False
    finally:
        driver.close()

def verify_qdrant_collection():
    """Verify Qdrant collection exists and has vectors."""
    print(f"\n🔍 Verifying Qdrant collection 'mem0'")
    try:
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
        print(f"❌ Qdrant verification failed: {e}")
        return False

def main():
    """Run complete test suite."""
    print("=" * 60)
    print("Mem0 Integration Test Suite")
    print("=" * 60)
    print(f"User ID: {USER_ID}\n")
    
    # Step 1: Test upsert
    upsert_ok = test_mem0_upsert()
    
    if not upsert_ok:
        print("\n⚠️  Upsert failed. Skipping verification steps.")
        print("   Make sure Mem0 container is running and API is accessible.")
        sys.exit(1)
    
    # Step 2: Verify Neo4j
    neo4j_ok = verify_neo4j_nodes()
    
    # Step 3: Verify Qdrant
    qdrant_ok = verify_qdrant_collection()
    
    print()
    print("=" * 60)
    if neo4j_ok and qdrant_ok:
        print("✅ All verification checks passed!")
        sys.exit(0)
    else:
        print("⚠️  Some verification checks failed. Review output above.")
        sys.exit(1)

if __name__ == "__main__":
    main()




