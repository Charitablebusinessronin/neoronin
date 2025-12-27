#!/bin/bash

# Neo4j entrypoint wrapper
# Runs schema initialization before starting Neo4j

set -e

# Wait for Neo4j to be ready and accept connections
wait_for_neo4j() {
    local max_attempts=30
    local attempt=0

    echo "Waiting for Neo4j to be ready..."

    while [ $attempt -lt $max_attempts ]; do
        if cypher-shell -a bolt://localhost:7687 -u "${NEO4J_USER:-neo4j}" -p "${NEO4J_PASSWORD:-changeme}" "RETURN 1" > /dev/null 2>&1; then
            echo "Neo4j is ready"
            return 0
        fi

        attempt=$((attempt + 1))
        echo "Attempt $attempt/$max_attempts - Neo4j not ready yet, waiting..."
        sleep 2
    done

    echo "Neo4j failed to start after $max_attempts attempts"
    return 1
}

# Initialize schema if not already initialized
init_schema() {
    echo "Initializing Neo4j schema..."

    # Check if schema already initialized (look for constraints)
    if cypher-shell -a bolt://localhost:7687 -u "${NEO4J_USER:-neo4j}" -p "${NEO4J_PASSWORD:-changeme}" \
        "SHOW CONSTRAINTS YIELD name WHERE name CONTAINS 'backup_id_unique' RETURN count(*)" 2>/dev/null | grep -q "1"; then
        echo "Schema already initialized, skipping"
        return 0
    fi

    # Create unique constraints
    echo "Creating unique constraints..."
    cypher-shell -a bolt://localhost:7687 -u "${NEO4J_USER:-neo4j}" -p "${NEO4J_PASSWORD:-changeme}" << 'EOF'
CREATE CONSTRAINT backup_id_unique IF NOT EXISTS
FOR (b:BackupMetadata) REQUIRE b.id IS UNIQUE;

CREATE CONSTRAINT audit_entry_id_unique IF NOT EXISTS
FOR (a:AuditLogEntry) REQUIRE a.id IS UNIQUE;

CREATE CONSTRAINT recovery_state_id_unique IF NOT EXISTS
FOR (r:RecoveryState) REQUIRE r.id IS UNIQUE;
EOF

    # Create property existence constraints
    echo "Creating property existence constraints..."
    cypher-shell -a bolt://localhost:7687 -u "${NEO4J_USER:-neo4j}" -p "${NEO4J_PASSWORD:-changeme}" << 'EOF'
CREATE CONSTRAINT backup_required_fields IF NOT EXISTS
FOR (b:BackupMetadata) REQUIRE (b.id, b.timestamp_created, b.status, b.backup_file) IS NOT NULL;

CREATE CONSTRAINT audit_required_fields IF NOT EXISTS
FOR (a:AuditLogEntry) REQUIRE (a.id, a.timestamp, a.operation, a.actor, a.result) IS NOT NULL;

CREATE CONSTRAINT recovery_required_fields IF NOT EXISTS
FOR (r:RecoveryState) REQUIRE (r.id, r.status) IS NOT NULL;
EOF

    # Create indices
    echo "Creating indices..."
    cypher-shell -a bolt://localhost:7687 -u "${NEO4J_USER:-neo4j}" -p "${NEO4J_PASSWORD:-changeme}" << 'EOF'
CREATE INDEX backup_timestamp IF NOT EXISTS FOR (b:BackupMetadata) ON (b.timestamp_created);
CREATE INDEX backup_status IF NOT EXISTS FOR (b:BackupMetadata) ON (b.status);
CREATE INDEX audit_timestamp IF NOT EXISTS FOR (a:AuditLogEntry) ON (a.timestamp);
CREATE INDEX audit_entity_type_timestamp IF NOT EXISTS FOR (a:AuditLogEntry) ON (a.entity_type, a.timestamp);
CREATE INDEX audit_actor IF NOT EXISTS FOR (a:AuditLogEntry) ON (a.actor);
EOF

    echo "Schema initialization completed"
}

# Main entrypoint logic
echo "Neo4j Durability Entrypoint Starting"
echo "Starting Neo4j database..."

# Start Neo4j in the background
/sbin/tini -g -- /startup/entrypoint.sh neo4j &
NEO4J_PID=$!

# Wait for Neo4j to be ready
if wait_for_neo4j; then
    # Initialize schema
    init_schema
else
    echo "Failed to initialize Neo4j"
    kill $NEO4J_PID || true
    exit 1
fi

# Keep the container running with Neo4j
wait $NEO4J_PID
