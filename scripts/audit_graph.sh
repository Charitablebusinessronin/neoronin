#!/bin/bash
# Neo4j Graph Audit Script
# Usage: ./audit_graph.sh

NEO4J_CONTAINER="grap-neo4j"
NEO4J_USER="neo4j"
NEO4J_PASS="Kamina2025*"

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║        Neo4j Graph Database Audit - $(date '+%Y-%m-%d %H:%M')        ║"
echo "╚════════════════════════════════════════════════════════════════╝"

# Function to run query
run_query() {
    local query="$1"
    docker exec $NEO4J_CONTAINER cypher-shell -u $NEO4J_USER -p $NEO4J_PASS "$query" 2>&1
}

echo -e "\n[1/11] Database Statistics..."
run_query "CALL apoc.meta.stats() YIELD nodeCount, relCount RETURN nodeCount, relCount"

echo -e "\n[2/11] Node Types..."
run_query "MATCH (n) RETURN labels(n) as type, count(n) as count ORDER BY count DESC"

echo -e "\n[3/11] Relationship Types..."
run_query "MATCH ()-[r]->() RETURN type(r) as type, count(r) as count ORDER BY count DESC"

echo -e "\n[4/11] Constraints..."
run_query "SHOW CONSTRAINTS YIELD name, type, entityType, labelsOrTypes, properties RETURN name, type, labelsOrTypes, properties"

echo -e "\n[5/11] Indexes..."
run_query "SHOW INDEXES YIELD name, type, labelsOrTypes, properties, state RETURN name, type, labelsOrTypes, properties, state"

echo -e "\n[6/11] BMAD Artifacts..."
run_query "MATCH (n) WHERE any(label IN labels(n) WHERE label IN ['AIAgent', 'Brain', 'Domain', 'System']) RETURN labels(n) as type, count(n) as count"

echo -e "\n[7/11] AIAgent Details (if exist)..."
run_query "MATCH (n:AIAgent) RETURN n.name, n.role, n.created_date LIMIT 10"

echo -e "\n[8/11] Orphaned Nodes..."
run_query "MATCH (n) WHERE NOT (n)--() RETURN labels(n) as type, count(n) as count ORDER BY count DESC LIMIT 5"

echo -e "\n[9/11] Graph Connectivity..."
run_query "MATCH (n) OPTIONAL MATCH (n)-[r]-() WITH labels(n)[0] as type, count(r) as degree RETURN type, avg(degree) as avg_connections ORDER BY avg_connections DESC LIMIT 5"

echo -e "\n[10/11] Property Keys..."
run_query "CALL db.propertyKeys() YIELD propertyKey RETURN propertyKey ORDER BY propertyKey LIMIT 20"

echo -e "\n[11/11] Recent Activity..."
run_query "MATCH (n) WHERE n.created_date IS NOT NULL OR n.timestamp IS NOT NULL RETURN labels(n) as type, coalesce(n.name, n.id) as identifier, coalesce(n.created_date, n.timestamp) as date ORDER BY date DESC LIMIT 10"

echo -e "\n╔════════════════════════════════════════════════════════════════╗"
echo "║                     Audit Complete                              ║"
echo "╚════════════════════════════════════════════════════════════════╝"
