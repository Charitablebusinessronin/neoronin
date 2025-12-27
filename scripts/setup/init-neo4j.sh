#!/bin/bash

# Initialize Neo4j with schema constraints and backup metadata tables
# Usage: ./scripts/setup/init-neo4j.sh

set -e

# Configuration
NEO4J_HOST=${NEO4J_HOST:-neo4j}
NEO4J_PORT=${NEO4J_PORT:-7687}
NEO4J_USER=${NEO4J_USER:-neo4j}
NEO4J_PASSWORD=${NEO4J_PASSWORD:-changeme}

# Create cypher-shell command
CYPHER_CMD="cypher-shell -a bolt://${NEO4J_HOST}:${NEO4J_PORT} -u ${NEO4J_USER} -p ${NEO4J_PASSWORD}"

echo "Initializing Neo4j schema constraints..."

# Create unique constraints
echo "Creating unique constraints..."
$CYPHER_CMD << 'EOF'
CREATE CONSTRAINT backup_id_unique IF NOT EXISTS
FOR (b:BackupMetadata) REQUIRE b.id IS UNIQUE;

CREATE CONSTRAINT audit_entry_id_unique IF NOT EXISTS
FOR (a:AuditLogEntry) REQUIRE a.id IS UNIQUE;

CREATE CONSTRAINT recovery_state_id_unique IF NOT EXISTS
FOR (r:RecoveryState) REQUIRE r.id IS UNIQUE;
EOF

# Create property existence constraints
echo "Creating property existence constraints..."
$CYPHER_CMD << 'EOF'
CREATE CONSTRAINT backup_required_fields IF NOT EXISTS
FOR (b:BackupMetadata) REQUIRE (b.id, b.timestamp_created, b.status, b.backup_file) IS NOT NULL;

CREATE CONSTRAINT audit_required_fields IF NOT EXISTS
FOR (a:AuditLogEntry) REQUIRE (a.id, a.timestamp, a.operation, a.actor, a.result) IS NOT NULL;

CREATE CONSTRAINT recovery_required_fields IF NOT EXISTS
FOR (r:RecoveryState) REQUIRE (r.id, r.status) IS NOT NULL;
EOF

# Create indices for fast lookups
echo "Creating indices..."
$CYPHER_CMD << 'EOF'
CREATE INDEX backup_timestamp IF NOT EXISTS FOR (b:BackupMetadata) ON (b.timestamp_created);
CREATE INDEX backup_status IF NOT EXISTS FOR (b:BackupMetadata) ON (b.status);
CREATE INDEX audit_timestamp IF NOT EXISTS FOR (a:AuditLogEntry) ON (a.timestamp);
CREATE INDEX audit_entity_type_timestamp IF NOT EXISTS FOR (a:AuditLogEntry) ON (a.entity_type, a.timestamp);
CREATE INDEX audit_actor IF NOT EXISTS FOR (a:AuditLogEntry) ON (a.actor);
EOF

echo "✓ Neo4j schema initialization complete"
