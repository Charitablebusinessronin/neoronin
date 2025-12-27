# Neo4j Durability System - Operator Guide

This guide provides operational procedures for managing the Neo4j graph memory durability system in production.

## Overview

The Grap Neo4j durability system provides:
- **Automated backups**: Scheduled backup creation with retention policies
- **Recovery procedures**: Safe restore with validation before production promotion
- **Health monitoring**: Three-tier health checks (connectivity, schema, orphans)
- **Write governance**: Comprehensive audit logging of all operations
- **Persistent storage**: Docker named volumes for data durability

## Table of Contents

1. [Initial Setup](#initial-setup)
2. [Daily Operations](#daily-operations)
3. [Backup Management](#backup-management)
4. [Recovery Procedures](#recovery-procedures)
5. [Health Monitoring](#health-monitoring)
6. [Troubleshooting](#troubleshooting)
7. [Compliance](#compliance)

## Initial Setup

### Prerequisites

- Docker and Docker Compose 3.8+
- Neo4j 5.13.0 Community Edition
- Python 3.9+ (for tools)
- 50GB+ available disk space (for backups)

### Quick Start

1. **Clone and navigate to project**:
```bash
cd /home/ronin/development/Grap
```

2. **Configure environment**:
```bash
cp .env.example .env
# Edit .env with your settings
```

3. **Initialize Docker volumes**:
```bash
mkdir -p data/neo4j backups
```

4. **Start the stack**:
```bash
docker-compose up -d
```

5. **Verify initialization**:
```bash
docker logs grap-neo4j | grep "Schema initialization"
```

### Environment Variables

Key configuration in `.env`:

```bash
# Neo4j Connection
NEO4J_AUTH=neo4j/changeme        # Default credentials (CHANGE IN PRODUCTION!)
NEO4J_URI=bolt://neo4j:7687

# Backup Configuration
BACKUP_SCHEDULE="0 2 * * *"      # Daily at 2 AM
BACKUP_RETENTION_DAYS=30         # Keep 30 days of backups
BACKUP_COMPRESSION=true          # Compress backups
BACKUP_DIR=/app/backups

# Recovery
PROMOTE_AFTER_VALIDATION=false   # Manual promotion required
LOG_LEVEL=INFO
```

## Daily Operations

### Health Checks

Run health checks to verify system status:

```bash
# Text output (human-readable)
docker exec grap-mcp python -m scripts.health.health_check

# JSON output (for monitoring)
docker exec grap-mcp python -m scripts.health.health_check --format json

# Detailed metrics
docker exec grap-mcp python -m scripts.health.health_check --detailed
```

**Expected Output**:
```
============================================================
Neo4j Health Check Report
Timestamp: 2024-01-15T10:30:00Z
Status: HEALTHY
============================================================

Health Checks:
------------------------------------------------------------
  ✓ connectivity                 [pass]
    Message: Neo4j is reachable and responding to queries
    Duration: 45ms

  ✓ schema_consistency            [pass]
    Message: All graph nodes and relationships conform to schema
    Duration: 125ms

  ✓ orphan_detection              [pass]
    Message: No orphaned relationships found
    Duration: 890ms

============================================================
```

### Check Backup Status

List all backups with validation status:

```bash
docker exec grap-backup-scheduler python -c "
from scripts.backup.neo4j_backup import BackupManager
from neo4j import GraphDatabase
driver = GraphDatabase.driver('bolt://neo4j:7687', auth=('neo4j', 'changeme'))
manager = BackupManager(driver, '/app/backups')
for backup in manager.list_backups():
    print(f'Backup: {backup[\"id\"]} - Status: {backup[\"status\"]} - Size: {backup[\"size_bytes\"]} bytes')
driver.close()
"
```

### Monitor Audit Log

View recent operations:

```bash
docker exec grap-neo4j cypher-shell -u neo4j -p changeme << 'EOF'
MATCH (a:AuditLogEntry)
RETURN a.timestamp, a.operation, a.actor, a.result
ORDER BY a.timestamp DESC
LIMIT 20;
EOF
```

## Backup Management

### Automatic Backups

Backups are created automatically on schedule (default: 2 AM daily):

```bash
# View backup scheduler logs
docker logs grap-backup-scheduler --follow
```

**Backup workflow**:
1. Scheduler triggers backup at scheduled time
2. `neo4j-admin backup` creates backup file
3. SHA256 checksum calculated and verified
4. Metadata stored in Neo4j (BackupMetadata node)
5. Audit log entry created
6. Old backups pruned based on retention policy

### Manual Backup

To create an immediate backup:

```bash
docker exec grap-backup-scheduler python -c "
from scripts.backup.neo4j_backup import BackupManager
from neo4j import GraphDatabase
driver = GraphDatabase.driver('bolt://neo4j:7687', auth=('neo4j', 'changeme'))
manager = BackupManager(driver, '/app/backups')
success, msg, metadata = manager.create_backup(backup_id='manual-$(date +%s)')
print(f'Success: {success}')
print(f'Backup ID: {metadata.get(\"id\")}')
print(f'Size: {metadata.get(\"size_bytes\")} bytes')
driver.close()
"
```

### Backup Retention Policy

Backups older than `BACKUP_RETENTION_DAYS` are automatically deleted:

```bash
# Retention check runs weekly (Sunday 4 AM)
# To prune immediately:
docker exec grap-backup-scheduler python -c "
from scripts.backup.neo4j_backup import BackupManager
from neo4j import GraphDatabase
driver = GraphDatabase.driver('bolt://neo4j:7687', auth=('neo4j', 'changeme'))
manager = BackupManager(driver, '/app/backups')
deleted, msg = manager.prune_old_backups(retention_days=30)
print(f'Deleted {deleted} backups')
driver.close()
"
```

### Backup Validation

Verify backup integrity:

```bash
docker exec grap-backup-scheduler python -c "
from scripts.backup.neo4j_backup import BackupManager
from neo4j import GraphDatabase
driver = GraphDatabase.driver('bolt://neo4j:7687', auth=('neo4j', 'changeme'))
manager = BackupManager(driver, '/app/backups')
valid, msg = manager.validate_backup('backup-id')
print(f'Valid: {valid}')
print(f'Message: {msg}')
driver.close()
"
```

## Recovery Procedures

### When to Recover

Recover from backup when:
- Database corruption detected
- Accidental data deletion
- Complete node failure requiring restore
- Testing disaster recovery procedures

### Safe Recovery Procedure

```bash
# Step 1: Check current recovery state
docker exec grap-neo4j cypher-shell -u neo4j -p changeme << 'EOF'
MATCH (r:RecoveryState {id: 'recovery-current'})
RETURN r.status, r.progress_percent, r.backup_id;
EOF

# Step 2: Create a backup of current state (safety measure)
# See "Manual Backup" section above

# Step 3: Initialize recovery from backup
docker exec grap-mcp python -c "
from src.durability.backup import DurabilityOrchestrator
from neo4j import GraphDatabase
driver = GraphDatabase.driver('bolt://neo4j:7687', auth=('neo4j', 'changeme'))
orchestrator = DurabilityOrchestrator(driver, '/app/backups')
success, msg = orchestrator.restore_with_validation('backup-id')
print(f'Recovery result: {success}')
print(f'Message: {msg}')
driver.close()
"

# Step 4: Check recovery status
docker exec grap-neo4j cypher-shell -u neo4j -p changeme << 'EOF'
MATCH (r:RecoveryState {id: 'recovery-current'})
RETURN r.status, r.progress_percent, r.validation_errors;
EOF

# Step 5: If validation passed, promote to production
docker exec grap-mcp python -c "
from src.durability.backup import DurabilityOrchestrator
from neo4j import GraphDatabase
driver = GraphDatabase.driver('bolt://neo4j:7687', auth=('neo4j', 'changeme'))
orchestrator = DurabilityOrchestrator(driver, '/app/backups')
success, msg = orchestrator.promote_backup_to_production()
print(f'Promotion result: {success}')
driver.close()
"
```

### Recovery State Transitions

Recovery follows this state machine:

```
NOT_RECOVERING
    ↓
RECOVERING (restore in progress)
    ↓
VALIDATION (health checks running)
    ├→ RECOVERY_SUCCESS (validation passed)
    │   ├→ PROMOTED (production use)
    │   └→ NOT_RECOVERING (rolled back)
    └→ RECOVERY_FAILED (validation failed)
        └→ NOT_RECOVERING (rolled back)
```

### Check Recovery Progress

```bash
docker exec grap-neo4j cypher-shell -u neo4j -p changeme << 'EOF'
MATCH (r:RecoveryState {id: 'recovery-current'})
RETURN {
  status: r.status,
  progress: r.progress_percent,
  backup_id: r.backup_id,
  started_at: r.started_at,
  completed_at: r.completed_at,
  validation_errors: r.validation_errors,
  promoted_to_production: r.promoted_to_production
};
EOF
```

### Cancel Recovery (if needed)

```bash
docker exec grap-mcp python -c "
from src.durability.backup import DurabilityOrchestrator
from neo4j import GraphDatabase
driver = GraphDatabase.driver('bolt://neo4j:7687', auth=('neo4j', 'changeme'))
orchestrator = DurabilityOrchestrator(driver, '/app/backups')
success, msg = orchestrator.cancel_recovery_operation()
print(f'Cancelled: {success}')
driver.close()
"
```

## Health Monitoring

### Three-Tier Health Checks

The health system verifies:

1. **Connectivity** (5s timeout)
   - Can reach Neo4j database
   - Basic query response

2. **Schema Consistency** (10s timeout)
   - Required node types exist
   - Required properties present (not null)
   - Expected indices created

3. **Orphan Detection** (30s timeout)
   - No relationships with missing endpoints
   - Graph structural integrity

### Integration with Monitoring

Export health metrics to monitoring system:

```bash
# Get JSON for monitoring/alerting
docker exec grap-mcp python -m scripts.health.health_check --format json --detailed | jq '.'

# Example response:
# {
#   "status": "healthy",
#   "timestamp": "2024-01-15T10:30:00Z",
#   "checks": {
#     "connectivity": {"status": "pass", "duration_ms": 45},
#     "schema_consistency": {"status": "pass", "duration_ms": 125},
#     "orphan_detection": {"status": "pass", "duration_ms": 890}
#   },
#   "graph_stats": {
#     "node_count": 1523,
#     "relationship_count": 4891
#   }
# }
```

### Create Health Check Alert

Example Prometheus alerting rule:

```yaml
- alert: NeoDBUnhealthy
  expr: neo4j_health_status{status="unhealthy"}
  for: 5m
  annotations:
    summary: "Neo4j database unhealthy"
    description: "Database failed health check: {{ $value }}"
```

## Troubleshooting

### Backup Creation Fails

```bash
# Check scheduler logs
docker logs grap-backup-scheduler

# Verify disk space
docker exec grap-neo4j df -h /backups

# Check Neo4j connectivity
docker exec grap-backup-scheduler python -m scripts.health.health_check
```

### Recovery Validation Fails

```bash
# Check validation errors
docker exec grap-neo4j cypher-shell -u neo4j -p changeme << 'EOF'
MATCH (r:RecoveryState {id: 'recovery-current'})
RETURN r.validation_errors;
EOF

# Run detailed health check
docker exec grap-mcp python -m scripts.health.health_check --detailed

# Cancel recovery and retry
docker exec grap-mcp python -c "
from src.durability.recovery import RecoveryStateMachine
from neo4j import GraphDatabase
driver = GraphDatabase.driver('bolt://neo4j:7687', auth=('neo4j', 'changeme'))
machine = RecoveryStateMachine(driver)
machine.reset_recovery_state()
driver.close()
"
```

### Slow Health Checks

Health checks should complete in < 1 minute. If slower:

1. Check database load: `docker stats grap-neo4j`
2. Check network latency: `docker exec grap-neo4j ping localhost`
3. Consider increasing timeouts in health-check.py

### Schema Not Initialized

```bash
# Manual schema initialization
docker exec grap-neo4j /app/scripts/setup/init-neo4j.sh

# Or run from host
bash scripts/setup/init-neo4j.sh
```

## Compliance

### Constitution Principle VI - Memory Durability

This system satisfies all requirements:

- ✓ **Named volumes**: Docker manages `grap-neo4j-data` and `grap-backups` volumes
- ✓ **Automated backups**: APScheduler creates backups on schedule
- ✓ **Recovery procedures**: Safe restore with validation before promotion
- ✓ **Write governance**: All operations logged to AuditLogEntry nodes
- ✓ **Health checks**: Connectivity, schema, and orphan detection

### Audit Compliance

All write operations are logged:

```bash
# Query audit trail
docker exec grap-neo4j cypher-shell -u neo4j -p changeme << 'EOF'
MATCH (a:AuditLogEntry)
RETURN {
  timestamp: a.timestamp,
  operation: a.operation,
  actor: a.actor,
  result: a.result,
  entity_type: a.entity_type,
  entity_id: a.entity_id
}
ORDER BY a.timestamp DESC
LIMIT 50;
EOF
```

### Data Retention

- **Backups**: Retained for 30 days (configurable)
- **Audit logs**: Retained indefinitely
- **Recovery state**: Current operation only

## Support

For issues or questions:
1. Check logs: `docker logs [container-name]`
2. Review this guide's troubleshooting section
3. Check specification: `specs/001-neo4j-durability/spec.md`
4. Review test cases: `tests/integration/`

## Change Log

### Version 1.0.0 (2024-01-15)

Initial implementation:
- Automated backup scheduling
- Recovery state machine
- Health check system
- Audit logging
- Docker containerization
