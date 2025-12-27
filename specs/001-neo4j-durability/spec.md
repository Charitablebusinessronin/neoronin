# Feature Specification: Neo4j Memory Durability

**Feature Branch**: `001-neo4j-durability`
**Created**: 2025-12-27
**Status**: Draft
**Input**: Infrastructure hardening for graph-backed memory system

## User Scenarios & Testing

### User Story 1 - Operator Deploys Neo4j with Persistent Storage (Priority: P1)

An infrastructure operator or developer sets up the Grap system in any environment (local WSL, Linux server, cloud VM) and needs confidence that the graph database survives container restarts, host reboots, and accidental container terminations.

**Why this priority**: Without durable storage, any infrastructure instability wipes the entire memory graph. This is a hard blocker for any production or serious development use.

**Independent Test**: Operator can deploy docker-compose, verify Neo4j is running with named volumes, kill the container mid-operation, restart it, and confirm all data persists and is queryable.

**Acceptance Scenarios**:

1. **Given** Neo4j container is running with named volumes, **When** the container is forcefully stopped (SIGKILL), **Then** data on disk is not corrupted and the container restarts cleanly with all previous data intact
2. **Given** the system has been running for a week with graph mutations, **When** the host is rebooted, **Then** Neo4j container restarts automatically and the graph is in the same state as before reboot
3. **Given** a developer uses WSL with docker-compose, **When** docker-compose is stopped and restarted, **Then** data persists in named volumes (not lost to filesystem unmounting)

---

### User Story 2 - Operator Performs Recovery from Corruption (Priority: P1)

An operator detects or suspects graph corruption (orphaned relationships, duplicate entities, schema violations) and needs a clear, documented procedure to restore the database to a known-good state without manual graph surgery.

**Why this priority**: Recovery procedures are the difference between "system is broken, rebuild from scratch" and "system is broken, rollback 4 hours and resume". Without them, durability is only half the story.

**Independent Test**: Operator deliberately corrupts the graph (e.g., delete critical entities via raw Cypher), restore from a backup taken before corruption, verify graph is consistent and queries return correct results.

**Acceptance Scenarios**:

1. **Given** a backup was created before a bad data write, **When** operator initiates restore procedure, **Then** graph is rolled back to backup state, MCP queries succeed, and no stale data remains from the bad write
2. **Given** operator has multiple dated backups available, **When** operator chooses a specific backup to restore, **Then** system restores to that point-in-time without affecting other backups
3. **Given** a restore is in progress, **When** MCP requests come in, **Then** they are rejected with a clear message "Database is recovering; please retry in X seconds" (no partial reads)

---

### User Story 3 - System Automatically Backs Up Graph on Schedule (Priority: P1)

The system automatically creates point-in-time backups of the graph without manual intervention. Backups are versioned and retained per a documented policy (e.g., keep daily for 7 days, weekly for 4 weeks).

**Why this priority**: Automated backups prevent the common failure mode where "we never took a backup and now we can't recover". If backups are manual, they will be forgotten.

**Independent Test**: Deploy system, run for 24 hours with intermittent graph mutations, verify that at least 2 backups exist at different times, and both are complete and restorable.

**Acceptance Scenarios**:

1. **Given** the system is running with automated backups configured, **When** 24 hours have passed, **Then** at least one backup has been created automatically (without operator action)
2. **Given** daily backups are configured, **When** 8 days have passed, **Then** old backups beyond the retention window have been deleted, and exactly 7 daily backups remain
3. **Given** a backup is in progress, **When** a write request comes to Neo4j, **Then** the write is allowed (backup does not block the database)

---

### User Story 4 - Write Paths Are Governed and Logged (Priority: P2)

All writes to the graph happen through explicit, documented paths (MCP → Graphiti → Neo4j). Direct writes, bulk imports, or schema changes that bypass this path are prevented or clearly logged for audit.

**Why this priority**: Corruption often results from multiple processes writing without coordination. Explicit write governance prevents this class of bug and provides audit trail for debugging.

**Independent Test**: Attempt to write to Neo4j directly (e.g., via `cypher-shell` without going through MCP), verify that either the write is rejected or a warning is logged. Confirm all legitimate MCP writes are logged with timestamp, actor, and payload.

**Acceptance Scenarios**:

1. **Given** a write comes through MCP, **When** Graphiti processes it and commits to Neo4j, **Then** a log entry is created with timestamp, operation type, affected entity IDs, and result (success/conflict)
2. **Given** an attempt is made to write to Neo4j directly (not via MCP/Graphiti), **When** the write occurs, **Then** it is logged as "UNAUTHORIZED_WRITE" with details, or rejected entirely
3. **Given** write logs are enabled, **When** 1000 writes have occurred, **Then** all writes are traceable: operator can replay the sequence of operations that led to current graph state

---

## Requirements

### Functional Requirements

- **FR-001**: System MUST store Neo4j data in named Docker volumes (not bind mounts to filesystem paths). Volume name MUST be stable and documented in docker-compose.yml.
- **FR-002**: System MUST create point-in-time backups of the Neo4j database on a documented schedule (e.g., every 6 hours, or daily).
- **FR-003**: System MUST retain backups according to a retention policy (e.g., keep last 7 daily backups, last 4 weekly backups). Policy MUST be configurable via environment variable.
- **FR-004**: System MUST provide a documented restore procedure. Recovery process MUST be testable without affecting production database (e.g., restore to a test container, verify data, then promote if correct).
- **FR-005**: System MUST log all writes to Neo4j with timestamp, operation type, affected entities, and result. Logs MUST be queryable (e.g., "all writes to User entity in last 24 hours").
- **FR-006**: System MUST prevent unauthorized direct access to Neo4j port from outside the docker-compose network. Only MCP gateway MUST have network access to Neo4j.
- **FR-007**: System MUST provide a health check endpoint that validates: (a) Neo4j is reachable, (b) graph schema is consistent, (c) no orphaned relationships detected. Health check MUST fail fast if any check fails.
- **FR-008**: System MUST handle recovery gracefully: if a backup is being restored, concurrent read/write requests MUST be queued or rejected with a clear message (not silently failing or returning stale data).
- **FR-009**: System MUST document write-path governance: which operations are allowed through MCP, which trigger backups, which require human approval. Governance rules MUST be stored in Constitution (updated as part of this feature).
- **FR-010**: Backups MUST be versioned and stored outside the Neo4j container (e.g., on a local volume mount or external storage). Version metadata (timestamp, graph statistics, checksum) MUST be captured per backup.

### Non-Functional Requirements

- **NFR-001**: Backup creation MUST NOT block writes to Neo4j. Backup performance MUST be measured; target: backup completes in under 5 minutes for a graph with 1 million nodes/relationships.
- **NFR-002**: Backup files MUST be compressed to reduce storage footprint. Compression ratio target: 60% of uncompressed size.
- **NFR-003**: Recovery from backup MUST complete in under 10 minutes for a 1GB backup. Recovery time MUST be measured and logged.
- **NFR-004**: Write logs MUST have minimal overhead. Target: <1ms added latency per write operation for logging.
- **NFR-005**: System MUST be resilient to partial failures: if backup fails, MCP and queries continue uninterrupted; if backup fails repeatedly, alerts MUST be generated (operator intervention required).

### Key Entities

- **Backup**: Point-in-time snapshot of graph, with metadata (timestamp created, timestamp expires, compressed size, uncompressed size, checksum).
- **Write Log Entry**: Record of a mutation to the graph (operation type, entity IDs, result, timestamp, actor, payload).
- **Health Check Result**: Status of graph consistency (schema valid, no orphans, no duplicates, last modified timestamp).
- **Recovery State**: Enum: NOT_RECOVERING, RECOVERING (X% complete), RECOVERY_FAILED, RECOVERY_SUCCESS.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Infrastructure operators can deploy the system using docker-compose.yml and have all data automatically persisted to named volumes with zero additional configuration.
- **SC-002**: A backup created before a data corruption event can be restored, bringing the graph to a consistent state, within 10 minutes (verified by test).
- **SC-003**: Backups are created automatically on schedule with zero failed backups in a 30-day test period.
- **SC-004**: All writes to the graph are logged and queryable; an operator can audit the complete write history for any entity within 1 minute.
- **SC-005**: Recovery procedure is documented, tested, and can be performed by someone unfamiliar with the codebase using only the documentation.
- **SC-006**: Graph health check catches inconsistencies (orphaned relationships, schema violations) before they cause query failures. Health check has <1% false-positive rate on healthy graphs.

## Edge Cases

- **Corrupted Backup**: What happens if a backup is corrupted on disk (checksum fails)? System MUST reject the backup, alert operator, and require choosing an alternative backup.
- **Concurrent Writes During Restore**: What if the operator tries to restore while writes are in flight? System MUST complete in-flight writes before starting restore, or abort restore and log a warning.
- **Full Backup Storage**: What if backup storage fills up and there's no space for the next backup? System MUST alert the operator and prevent the backup from silently failing.
- **Incomplete Backup**: What if a backup is partially created (process killed mid-backup)? System MUST clean up incomplete backups and treat them as failed backups; retry on next schedule.
- **Database Offline During Backup**: What if Neo4j is offline when backup is scheduled? System MUST retry with exponential backoff; if all retries fail, alert operator.

## Assumptions

- Backup storage is local (docker volume or filesystem mount). Remote backup (S3, Azure Blob, etc.) is out of scope for this feature but MUST be designable for future expansion.
- Backup restoration always goes to a separate test Neo4j instance first (not production). The production restore is a manual promotion step after validation.
- Graphiti is assumed to be stateless (all state is in Neo4j graph). MCP is assumed to be stateless (state is in Neo4j, session state in client).
- Docker and docker-compose are available in all deployment environments.
- Operator has shell access to the deployment environment (can run docker-compose commands and check logs).

## Dependencies

- Depends on: Neo4j in Docker (already running per earlier decision)
- Depends on: Docker-compose for orchestration (assumed available)
- Unblocks: Future features that mutate the graph and assume durability (e.g., Graphiti entity creation, MCP write endpoints)

## Out of Scope

- Remote backup to cloud storage (S3, GCS, Azure). Local backups only.
- Incremental backups. Full backups only.
- Backup encryption. Backups are stored in trusted local filesystem.
- Replication across multiple Neo4j instances. Single-instance durability only.
- Point-in-time recovery (recover a single transaction). Full-backup restore only.
