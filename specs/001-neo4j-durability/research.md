# Research: Neo4j Memory Durability (Phase 0)

**Feature**: 001-neo4j-durability
**Date**: 2025-12-27
**Purpose**: Resolve technical unknowns and establish best practices before Phase 1 design

## Key Decisions

### 1. Neo4j Backup Strategy

**Decision**: Use native `neo4j-admin backup` for full backups; compress with gzip

**Rationale**:
- Neo4j 5.0+ includes native backup tooling (`neo4j-admin backup`) that doesn't require running as a separate process
- Official tooling is well-tested and bundled with Neo4j Docker image
- Produces consistent, checksummed backups suitable for compliance
- Non-blocking backups (can run while database is online and accepting writes)

**Alternatives Considered**:
- Full database dump via Cypher: Less efficient, less reliable for large graphs, requires full traversal
- File-level snapshots (LVM, filesystem): Not portable across platforms; coupling to storage layer violates Principle I
- Incremental backups: Out of scope for v1; full backups adequate for typical use

**Implementation**:
```bash
neo4j-admin backup --from-path=/data/databases/neo4j --backup-path=/backups/neo4j-$(date +%Y%m%d-%H%M%S)
```

### 2. Backup Scheduling

**Decision**: Implement scheduler in Python (APScheduler library); run as separate service or cron job

**Rationale**:
- APScheduler is lightweight, cross-platform, and handles timezone-aware scheduling
- Decouples backup from Neo4j process; failure in backup doesn't kill database
- Easier to integrate with alerting and retention policy enforcement
- Python matches project's planned scripting language

**Alternatives Considered**:
- Kubernetes CronJob: Out of scope (single-instance setup)
- Systemd timer: Linux-only; less portable
- Database-side triggers: Not applicable to Neo4j; would violate governance principle
- Manual operator-triggered backups: Would be forgotten; spec requires automation

**Implementation**:
- Standalone Python service (or cron job calling Python script)
- Configurable via environment variables: `BACKUP_SCHEDULE` (cron expression), `BACKUP_RETENTION_DAYS` (integer)
- Failed backups trigger alerts (logged and exposed via health check)

### 3. Backup Storage Location

**Decision**: Local filesystem mounted as Docker volume; live in `backups/` directory

**Rationale**:
- Named volumes are stable and documented in docker-compose.yml
- Filesystem storage is portable across all deployment environments (WSL, Docker Desktop, Linux)
- Easy for operators to inspect, compress, or manually transfer backups
- Avoids coupling to external services (S3, etc.) in v1

**Scope Limitation**:
- Remote backup (S3, GCS, Azure) is explicitly out of scope for v1
- Architecture must permit future addition of S3 upload without refactoring

**Implementation**:
- Docker volume: `grap-backups`
- Mount point in Neo4j container: `/backups`
- Backup path: `/backups/neo4j-{timestamp}.backup`
- Compression: `gzip` to `/backups/neo4j-{timestamp}.backup.gz`

### 4. Recovery Procedure

**Decision**: Offline restore to separate test Neo4j instance; manual promotion to production after validation

**Rationale**:
- Offline restore is safer: zero chance of partial restore visible to clients
- Test instance allows validation before production exposure
- Manual promotion gate prevents accidental rollbacks
- Matches standard database recovery best practices

**Alternatives Considered**:
- Online restore: Risky; could expose inconsistent state if restore fails mid-way
- Automatic promotion: Removes operator control; dangerous for data corruption scenarios

**Implementation**:
- Python script: `neo4j-restore.py`
- Supports: restore to named backup, timestamp-based restore, validation checks
- Validation: Run health checks on restored instance before promotion
- Promotion: Operator manually updates docker-compose to point to restored volume

### 5. Health Check Design

**Decision**: Three-check protocol exposed via HTTP endpoint + CLI script

**Rationale**:
- Fast fail: If any check fails, immediately return error (don't wait for full scan)
- Three checks catch most corruption scenarios without full graph scan

**Checks**:
1. **Reachability**: Can we connect to Neo4j and run a simple query (e.g., `RETURN 1`)?
2. **Schema Consistency**: Do all defined node/relationship types have required properties? (Requires schema definition from Graphiti)
3. **Orphan Detection**: Are there any relationships pointing to non-existent nodes? (Cypher query: `MATCH (n)-[r]-(m) WHERE n IS NULL OR m IS NULL RETURN count(r)`)

**Performance Target**: <5 seconds for 1M node/relationship graphs; parallelized queries where possible

**Alternatives Considered**:
- Full DBMS consistency check (`neo4j-admin check-consistency`): Too slow for operational monitoring; suitable for offline validation only
- Sampling-based checks: Introduces false negatives; skipped for v1

**Implementation**:
- HTTP endpoint: `/health/graph` returns JSON with status of each check
- CLI script: Can be invoked standalone for troubleshooting

### 6. Write Audit Logging

**Decision**: Graphiti writes log entries to a separate Neo4j node type (`AuditLogEntry`) with relationships to affected entities

**Rationale**:
- Keeps all data in graph (Principle I); no external logging systems
- Graphiti already manages entity mutations; logging is a side effect
- Audit log is queryable with Cypher (e.g., "all writes to User in last 24h")
- Timestamps and versioning enable replay of operations

**Schema**:
```
(:AuditLogEntry {
  id: UUID,
  timestamp: DateTime,
  operation: "CREATE|UPDATE|DELETE",
  actor: String,              // User/service that triggered write
  payload: String,            // JSON of changed properties
  result: "SUCCESS|CONFLICT",
  affectedEntities: [Relationship to affected nodes]
})
```

**Alternatives Considered**:
- External logging (ELK, Datadog): Out of scope; adds complexity
- Text logs: Violates Principle I (Graph-First); not queryable
- No logging: Violates Principle VI (Memory Durability); can't audit or replay

**Implementation**:
- Graphiti calls `write_log.log_mutation(operation, actor, payload, affected_node_ids)`
- Function creates `AuditLogEntry` node and relationships in same transaction as the write
- Adds <1ms overhead (in-process call; same transaction)

### 7. Network Isolation

**Decision**: Neo4j only accessible from MCP gateway container (docker-compose network)

**Rationale**:
- Prevents direct database access from outside the docker-compose stack
- Enforces MCP contract (Principle II)
- Simplifies security: no need to expose Neo4j port to host network

**Implementation**:
- Docker-compose network: `grap-network` (internal only)
- Neo4j service: Only listens on `neo4j` (internal hostname)
- MCP gateway: On same network; can access `neo4j:7687`
- Backup/restore services: On same network; can access Neo4j
- No port mapping for Neo4j in docker-compose.yml

**Testing**:
- Verify `docker exec neo4j-container curl neo4j:7687` fails from outside container
- Verify MCP gateway can connect normally

### 8. Backup Metadata & Versioning

**Decision**: Store metadata in JSON file alongside each backup; track version, size, checksum, timestamp

**Rationale**:
- Self-describing backup artifacts
- Enables verification before restore
- Checksum prevents corrupt backup use
- JSON format is portable and operator-friendly

**Schema** (`neo4j-{timestamp}.backup.meta`):
```json
{
  "version": "1.0.0",
  "timestamp": "2025-12-27T15:30:00Z",
  "backup_duration_seconds": 145,
  "neo4j_version": "5.13.0",
  "graph_stats": {
    "node_count": 1500,
    "relationship_count": 3200
  },
  "backup_file": "neo4j-20251227-153000.backup.gz",
  "uncompressed_size_bytes": 524288000,
  "compressed_size_bytes": 314572800,
  "checksum_sha256": "abc123..."
}
```

## Technology Stack Summary

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Database | Neo4j 5.0+ (Docker) | Specified in project; native backup support |
| Backup Tool | `neo4j-admin` | Official; non-blocking; checksummed |
| Scheduling | APScheduler (Python) | Lightweight; cross-platform; alertable |
| Health Checks | Python + Cypher | Fast; queryable; no external deps |
| Orchestration | docker-compose | Project standard; explicit, reproducible |
| Audit Logging | Neo4j AuditLogEntry nodes | Graph-first (Principle I); queryable |
| Compression | gzip | Standard; good ratio; portable |
| Testing | pytest | Python standard; integrated with CI |

## Risks & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Backup storage fills up | Medium | High (backups fail silently) | Monitor free space; alert if <20% free; fail loudly if no space |
| Network partition during backup | Low | Medium (inconsistent backup) | Use checksums; validate before restore; retry with backoff |
| Recovery procedure too complex for operators | Medium | High (unable to recover) | Document thoroughly; provide recovery testing environment; practice runbook |
| Audit log grows unbounded | Medium | Medium (query slowdown) | Archive old logs; implement retention; monitor log size |
| Graphiti integration timing issues | Low | High (writes blocked) | Implement async logging; measure overhead; ensure <1ms target |

## Next Steps

- **Phase 1**: Use these decisions to design data model, API contracts, and implementation structure
- **Phase 2**: Generate tasks based on Phase 1 designs
- **Phase 3**: Implement tasks in priority order (P1 features first)
