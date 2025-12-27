# Data Model: Neo4j Memory Durability

**Feature**: 001-neo4j-durability
**Date**: 2025-12-27
**Purpose**: Define schema for backup metadata, recovery state, and audit logging

## Neo4j Node Types

### Backup Metadata Node

**Node Label**: `BackupMetadata`

**Purpose**: Track all point-in-time backups with version, size, integrity info

**Properties**:

| Property | Type | Required | Notes |
|----------|------|----------|-------|
| `id` | UUID | Yes | Unique identifier for this backup (e.g., `neo4j-20251227-153000`) |
| `timestamp_created` | DateTime | Yes | When backup was created (UTC) |
| `timestamp_expires` | DateTime | No | When backup should be deleted per retention policy |
| `backup_file` | String | Yes | Filename (e.g., `neo4j-20251227-153000.backup.gz`) |
| `backup_path` | String | Yes | Full path to backup file (e.g., `/backups/neo4j-20251227-153000.backup.gz`) |
| `uncompressed_size_bytes` | Integer | Yes | Size before compression |
| `compressed_size_bytes` | Integer | Yes | Size after gzip compression |
| `compression_ratio` | Float | Yes | Calculated: compressed / uncompressed (e.g., 0.60 = 60%) |
| `checksum_sha256` | String | Yes | SHA256 hash of backup file for integrity validation |
| `neo4j_version` | String | Yes | Neo4j version that created this backup (e.g., `5.13.0`) |
| `backup_duration_seconds` | Integer | Yes | Time to create backup (includes compression) |
| `graph_node_count` | Integer | Yes | Number of nodes in graph at backup time |
| `graph_relationship_count` | Integer | Yes | Number of relationships at backup time |
| `status` | String | Yes | Enum: `COMPLETE`, `IN_PROGRESS`, `FAILED`, `VALIDATED`, `ARCHIVED` |
| `health_check_passed` | Boolean | No | True if health checks passed on this backup after restore |
| `tags` | [String] | No | User-provided tags (e.g., `["pre-migration", "critical"]`) |
| `notes` | String | No | Human-readable notes about this backup |

**Example**:
```cypher
CREATE (b:BackupMetadata {
  id: "neo4j-20251227-153000",
  timestamp_created: datetime("2025-12-27T15:30:00Z"),
  timestamp_expires: datetime("2026-01-03T15:30:00Z"),
  backup_file: "neo4j-20251227-153000.backup.gz",
  backup_path: "/backups/neo4j-20251227-153000.backup.gz",
  uncompressed_size_bytes: 524288000,
  compressed_size_bytes: 314572800,
  compression_ratio: 0.60,
  checksum_sha256: "abc123def456...",
  neo4j_version: "5.13.0",
  backup_duration_seconds: 145,
  graph_node_count: 1500,
  graph_relationship_count: 3200,
  status: "COMPLETE",
  health_check_passed: true,
  tags: ["daily", "automated"],
  notes: "Routine daily backup before maintenance window"
})
```

**Indices**:
- `BackupMetadata(id)` - Unique lookup
- `BackupMetadata(timestamp_created)` - Sorted by creation time
- `BackupMetadata(status)` - Filter by status (find failed backups, etc.)

---

### Audit Log Entry Node

**Node Label**: `AuditLogEntry`

**Purpose**: Record all mutations to the graph for auditability and replay

**Properties**:

| Property | Type | Required | Notes |
|----------|------|----------|-------|
| `id` | UUID | Yes | Unique identifier for this audit entry |
| `timestamp` | DateTime | Yes | When the mutation occurred (UTC) |
| `operation` | String | Yes | Enum: `CREATE`, `UPDATE`, `DELETE`, `MERGE` |
| `entity_type` | String | Yes | Type of entity modified (e.g., `User`, `Memory`, `Relationship`) |
| `actor` | String | Yes | User/service that performed the mutation (e.g., `system:mcp-gateway`, `user:alice@example.com`) |
| `payload` | String | Yes | JSON string of the mutation payload (properties before and after) |
| `result` | String | Yes | Enum: `SUCCESS`, `CONFLICT`, `FAILED` |
| `affected_entity_ids` | [String] | Yes | List of entity IDs affected by this mutation |
| `transaction_id` | String | Yes | Neo4j transaction ID (for traceability) |
| `error_message` | String | No | If result is `FAILED`, error details |
| `duration_ms` | Integer | No | Time to execute mutation |
| `backup_id` | String | No | Backup ID if this mutation was part of a bulk restore |

**Example**:
```cypher
CREATE (a:AuditLogEntry {
  id: "audit-20251227-120500-abc123",
  timestamp: datetime("2025-12-27T12:05:00Z"),
  operation: "CREATE",
  entity_type: "User",
  actor: "system:graphiti",
  payload: "{\"name\": \"Alice\", \"email\": \"alice@example.com\"}",
  result: "SUCCESS",
  affected_entity_ids: ["user-uuid-123"],
  transaction_id: "neo4j-tx-456789",
  duration_ms: 45
})
```

**Indices**:
- `AuditLogEntry(timestamp)` - Sorted by time (range queries)
- `AuditLogEntry(entity_type, timestamp)` - Filter by entity type and time window
- `AuditLogEntry(actor)` - Find mutations by specific actor

---

### Recovery State Node

**Node Label**: `RecoveryState`

**Purpose**: Track ongoing or completed recovery operations

**Properties**:

| Property | Type | Required | Notes |
|----------|------|----------|-------|
| `id` | UUID | Yes | Unique identifier (usually just `recovery-current`) |
| `status` | String | Yes | Enum: `NOT_RECOVERING`, `RECOVERING`, `VALIDATION`, `RECOVERY_FAILED`, `RECOVERY_SUCCESS` |
| `backup_id` | String | No | Backup being restored (FK to BackupMetadata) |
| `started_at` | DateTime | No | When recovery started |
| `completed_at` | DateTime | No | When recovery completed or failed |
| `progress_percent` | Integer | No | Current progress (0-100) |
| `target_instance` | String | No | Where recovery is happening (e.g., `test-neo4j` container) |
| `validation_errors` | [String] | No | List of validation errors (if RECOVERY_FAILED) |
| `promoted_to_production` | Boolean | No | True if this recovery was promoted to production |
| `promoted_at` | DateTime | No | When promoted |

**Example**:
```cypher
CREATE (r:RecoveryState {
  id: "recovery-current",
  status: "RECOVERING",
  backup_id: "neo4j-20251227-150000",
  started_at: datetime("2025-12-27T16:00:00Z"),
  progress_percent: 65,
  target_instance: "test-neo4j"
})
```

---

## Relationships

### BackupMetadata → Previous Backup

**Relationship Type**: `PREVIOUS_BACKUP`

**Purpose**: Chain backups in chronological order for easy traversal

**Example**:
```cypher
(backup-newer)-[:PREVIOUS_BACKUP]->(backup-older)
```

---

### AuditLogEntry → Affected Entity

**Relationship Type**: `AFFECTED_ENTITY`

**Purpose**: Link audit entry to the entities it modified

**Example**:
```cypher
(audit-entry)-[:AFFECTED_ENTITY]->(user-node)
(audit-entry)-[:AFFECTED_ENTITY]->(relationship-node)
```

---

### BackupMetadata → RecoveryState

**Relationship Type**: `RESTORED_BY`

**Purpose**: Link backup to recovery operations that used it

**Example**:
```cypher
(backup-node)-[:RESTORED_BY]->(recovery-state)
```

---

## Schema Constraints

### Unique Constraints

```cypher
CREATE CONSTRAINT backup_id_unique IF NOT EXISTS
FOR (b:BackupMetadata) REQUIRE b.id IS UNIQUE;

CREATE CONSTRAINT audit_entry_id_unique IF NOT EXISTS
FOR (a:AuditLogEntry) REQUIRE a.id IS UNIQUE;

CREATE CONSTRAINT recovery_state_id_unique IF NOT EXISTS
FOR (r:RecoveryState) REQUIRE r.id IS UNIQUE;
```

### Property Existence Constraints

```cypher
CREATE CONSTRAINT backup_required_fields IF NOT EXISTS
FOR (b:BackupMetadata) REQUIRE (b.id, b.timestamp_created, b.status, b.backup_file) IS NOT NULL;

CREATE CONSTRAINT audit_required_fields IF NOT EXISTS
FOR (a:AuditLogEntry) REQUIRE (a.id, a.timestamp, a.operation, a.actor, a.result) IS NOT NULL;

CREATE CONSTRAINT recovery_required_fields IF NOT EXISTS
FOR (r:RecoveryState) REQUIRE (r.id, r.status) IS NOT NULL;
```

---

## Queries

### Find latest backup

```cypher
MATCH (b:BackupMetadata)
WHERE b.status IN ["COMPLETE", "VALIDATED"]
RETURN b
ORDER BY b.timestamp_created DESC
LIMIT 1;
```

### Find backups older than retention window

```cypher
MATCH (b:BackupMetadata)
WHERE b.timestamp_expires < datetime.now()
RETURN b;
```

### Audit trail for specific entity

```cypher
MATCH (e:Entity {id: $entity_id})<-[:AFFECTED_ENTITY]-(a:AuditLogEntry)
RETURN a
ORDER BY a.timestamp DESC;
```

### Count mutations by actor in time window

```cypher
MATCH (a:AuditLogEntry)
WHERE a.timestamp >= $start_time
  AND a.timestamp <= $end_time
  AND a.actor = $actor
RETURN a.operation, count(*) as count
GROUP BY a.operation;
```

### Check for orphaned relationships (health check)

```cypher
MATCH (n)-[r]-(m)
WHERE NOT EXISTS {MATCH (n)} OR NOT EXISTS {MATCH (m)}
RETURN count(r) as orphaned_count;
```

---

## Data Retention Policy

**Default Policy**:
- Keep 7 daily backups (delete backups older than 7 days)
- Keep 4 weekly backups (Sunday of each week)
- Keep 1 monthly backup (first of month)
- Total typical retention: ~35 days

**Audit Log Retention**:
- Keep all audit log entries for 90 days
- Archive to cold storage (out of scope for v1) after 90 days
- Never delete active audit logs (compliance requirement)

**Configurable Via Environment**:
```bash
BACKUP_RETENTION_DAILY_COUNT=7
BACKUP_RETENTION_WEEKLY_COUNT=4
BACKUP_RETENTION_MONTHLY_COUNT=1
AUDIT_LOG_RETENTION_DAYS=90
```

---

## Migration Path (Future)

When moving to cloud backup storage (out of scope for v1):
1. Backup metadata remains in Neo4j (unchanged)
2. Add `backup_location` property to BackupMetadata (e.g., `LOCAL`, `S3`)
3. Update backup script to support S3 upload
4. Archive old local backups to S3 after configurable period
5. Support restore from either local or S3 backup

This design is forward-compatible and requires no schema refactoring.
