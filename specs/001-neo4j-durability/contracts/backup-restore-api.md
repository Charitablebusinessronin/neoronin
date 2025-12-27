# Contract: Backup & Restore Operations

**Feature**: 001-neo4j-durability
**Type**: CLI + Optional HTTP API
**Purpose**: Backup creation, restoration, and management

---

## Backup Operations

### Backup Script: `scripts/backup/neo4j-backup.py`

Operator-facing tool to create and manage backups manually or via scheduling.

#### Usage

```bash
python scripts/backup/neo4j-backup.py [OPTIONS]
```

#### Options

- `--create`: Create a new backup now
- `--list`: List all available backups
- `--delete <backup_id>`: Delete a specific backup
- `--validate <backup_id>`: Validate backup integrity (checksum)
- `--schedule`: Start the backup scheduler (runs continuously)
- `--config <file>`: Load configuration from file (default: env vars)
- `--dry-run`: Show what would happen without making changes
- `-v, --verbose`: Verbose output

#### Environment Variables

```bash
BACKUP_STORAGE_PATH=/backups            # Where backups are stored
NEO4J_DATA_PATH=/data/databases/neo4j   # Neo4j data directory
BACKUP_SCHEDULE="0 2 * * *"             # Cron expression for automated backups
BACKUP_RETENTION_DAYS=7                 # How long to keep backups
BACKUP_COMPRESSION=gzip                 # Compression algorithm (gzip|none)
BACKUP_ALERT_EMAIL=ops@example.com      # Email for alerts (optional)
```

#### Success Output

```
INFO: Starting backup creation...
INFO: Neo4j version: 5.13.0
INFO: Running: neo4j-admin backup --from-path=/data/databases/neo4j --backup-path=/backups/neo4j-20251227-153000
INFO: Backup created successfully in 145 seconds
INFO: Compressing backup with gzip...
INFO: Compressed size: 314.5 MB (60% of original 524.3 MB)
INFO: Computing checksum...
INFO: Backup ID: neo4j-20251227-153000
INFO: Checksum SHA256: abc123def456...
SUCCESS: Backup completed
```

#### Failure Output

```
ERROR: Failed to create backup
ERROR: Reason: No space left on device (/backups filesystem is full)
ERROR: Required: 524 MB | Available: 50 MB
ERROR: Action: Free up space and retry, or configure BACKUP_STORAGE_PATH to different location
CRITICAL: Operator attention required
```

---

## Restore Operations

### Restore Script: `scripts/backup/neo4j-restore.py`

Offline restore of a backup to a separate test Neo4j instance.

#### Usage

```bash
python scripts/backup/neo4j-restore.py [OPTIONS]
```

#### Options

- `--backup-id <id>`: Restore this backup (required)
- `--target <instance>`: Target Neo4j instance (default: `test-neo4j`)
- `--validate`: Run health checks after restore (default: yes)
- `--promote`: Promote restored instance to production (requires manual confirmation)
- `--dry-run`: Show what would happen
- `-v, --verbose`: Verbose output

#### Environment Variables

```bash
BACKUP_STORAGE_PATH=/backups
NEO4J_DATA_PATH=/data/databases/neo4j
TEST_NEO4J_CONTAINER=test-neo4j  # Docker container name for test instance
PROMOTE_AFTER_VALIDATION=false   # Auto-promote if validation passes (safety: false)
```

#### Success Output

```
INFO: Starting restore from backup neo4j-20251227-150000
INFO: Validating backup integrity...
INFO: Checksum verification: PASSED
INFO: Uncompressing backup...
INFO: Backup size (compressed): 314.5 MB
INFO: Backup size (uncompressed): 524.3 MB
INFO: Creating test Neo4j instance (test-neo4j container)...
INFO: Restoring data...
INFO: Restore completed in 8 minutes 42 seconds
INFO: Running health checks on restored instance...
INFO: Health check: connectivity ... PASS
INFO: Health check: schema_consistency ... PASS
INFO: Health check: orphan_detection ... PASS
SUCCESS: Restore completed and validated
INFO: Restored backup: neo4j-20251227-150000
INFO: Graph stats: 1500 nodes, 3200 relationships
INFO: Next step: Verify restored data, then run: --promote to switch to production
```

#### Failure Output (Corrupted Backup)

```
ERROR: Backup validation failed
ERROR: Checksum mismatch!
ERROR: Expected: abc123def456...
ERROR: Got: xyz789def999...
ERROR: This backup appears to be corrupted on disk
ERROR: Action: Try a different backup with --backup-id <other_id>
```

#### Failure Output (Health Check Failed)

```
ERROR: Restore completed but health check failed
ERROR: Failed check: orphan_detection
ERROR: Found 45 orphaned relationships
ERROR: This indicates the backup itself is corrupted (not a restore error)
ERROR: Action: Restore a different backup, or investigate if manual graph modifications occurred before backup
```

---

## Backup Listing

### List All Backups

```bash
python scripts/backup/neo4j-backup.py --list
```

**Output**:

```
Available Backups:
==================

neo4j-20251227-153000
  Created:        2025-12-27 15:30:00 UTC
  Expires:        2026-01-03 15:30:00 UTC
  Status:         COMPLETE, VALIDATED
  Uncompressed:   524.3 MB
  Compressed:     314.5 MB (60%)
  Checksum:       abc123def456...
  Graph Stats:    1500 nodes, 3200 relationships
  Backup Duration: 145 seconds

neo4j-20251226-030000
  Created:        2025-12-26 03:00:00 UTC
  Expires:        2026-01-02 03:00:00 UTC
  Status:         COMPLETE
  Uncompressed:   523.1 MB
  Compressed:     313.8 MB (60%)
  Checksum:       def456ghi789...
  Graph Stats:    1498 nodes, 3195 relationships
  Backup Duration: 142 seconds

[... more backups ...]

Total: 7 backups, consuming 2.2 GB of storage
Expiring soon: neo4j-20251220-030000 (expires in 2 days)
```

---

## Retention Policy

### Default Behavior

Retention is enforced automatically by the scheduler:

```python
# Keep all backups within retention window
keep_daily_for_days = 7
keep_weekly_for_weeks = 4
keep_monthly_for_months = 3

# Cleanup: older backups are automatically deleted
```

### Manual Cleanup

```bash
# Delete a specific backup
python scripts/backup/neo4j-backup.py --delete neo4j-20251220-030000

# Delete all expired backups
python scripts/backup/neo4j-backup.py --cleanup --delete-expired

# Cleanup with confirmation
python scripts/backup/neo4j-backup.py --cleanup --dry-run  # Preview what would be deleted
python scripts/backup/neo4j-backup.py --cleanup            # Actually delete
```

---

## Scheduler Service

### Start Scheduler

```bash
python scripts/backup/neo4j-backup.py --schedule
```

Runs as a persistent process. Recommended to run in docker-compose or systemd service.

**Example docker-compose.yml section**:

```yaml
backup-scheduler:
  image: python:3.9-slim
  volumes:
    - ./scripts:/app/scripts
    - grap-backups:/backups
    - grap-neo4j-data:/data/databases/neo4j:ro
  environment:
    BACKUP_STORAGE_PATH: /backups
    NEO4J_DATA_PATH: /data/databases/neo4j
    BACKUP_SCHEDULE: "0 2 * * *"  # 2 AM UTC daily
    BACKUP_RETENTION_DAYS: 7
  command: python /app/scripts/backup/neo4j-backup.py --schedule
  depends_on:
    - neo4j
```

**Scheduler Output** (running with `--schedule`):

```
INFO: Backup scheduler started
INFO: Schedule: Daily at 02:00 UTC
INFO: Next backup: 2025-12-28 02:00:00 UTC

[2025-12-27 02:00:00] BACKUP_START: neo4j-20251227-020000
[2025-12-27 02:02:25] BACKUP_SUCCESS: neo4j-20251227-020000 (145 seconds)
[2025-12-27 02:02:26] CLEANUP_START: Remove backups older than 7 days
[2025-12-27 02:02:27] CLEANUP_SUCCESS: Deleted 1 backup (neo4j-20251220-020000)
[2025-12-27 02:02:27] NEXT_BACKUP: 2025-12-28 02:00:00 UTC

[2025-12-28 02:00:00] BACKUP_START: neo4j-20251228-020000
... (continues indefinitely)
```

**Failure Handling**:
- If backup fails, log error and retry with exponential backoff (1 min, 5 min, 30 min, 24 hours)
- If backup fails 5 times in a row, send critical alert and pause scheduler (operator intervention required)

---

## State Transitions

### Recovery State Machine

```
NOT_RECOVERING
  |
  +--[Operator initiates restore]--> RECOVERING
                                        |
                                        +--[Restore completes]--> VALIDATION
                                                                      |
                                        +--[Validation passes]--> RECOVERY_SUCCESS
                                        |
                                        +--[Validation fails]--> RECOVERY_FAILED
                                        |                           |
                                        +--[Operator cancels]--------+
```

---

## Contract Tests

### Test: Backup Creation

```
GIVEN: Neo4j running with 1500 nodes
WHEN: Run `python scripts/backup/neo4j-backup.py --create`
THEN: Backup file is created in BACKUP_STORAGE_PATH
AND: Backup metadata is stored in BackupMetadata node
AND: Status is "COMPLETE"
AND: Checksum matches backup file
```

### Test: Restore Success

```
GIVEN: Valid backup exists
AND: Test Neo4j instance is ready
WHEN: Run `python scripts/backup/neo4j-restore.py --backup-id <id> --validate`
THEN: Data is restored to test instance
AND: Health checks pass
AND: Graph node/relationship counts match backup metadata
```

### Test: Corrupted Backup Rejected

```
GIVEN: Backup file has been modified (corrupted)
WHEN: Run `python scripts/backup/neo4j-restore.py --backup-id <id>`
THEN: Checksum validation fails
AND: Restore is aborted
AND: Error message directs to use different backup
```

### Test: Scheduler Respects Retention

```
GIVEN: BACKUP_RETENTION_DAYS=7
AND: 10 daily backups exist (10 days old)
WHEN: Scheduler runs cleanup
THEN: Only 7 most recent backups remain
AND: 3 oldest backups are deleted
```

### Test: Space Alert

```
GIVEN: BACKUP_STORAGE_PATH filesystem has < 20% free space
WHEN: Backup scheduler runs
THEN: Backup fails with clear message about space
AND: Alert is sent to BACKUP_ALERT_EMAIL
AND: Scheduler does NOT silently skip the backup
```

---

## Error Codes

| Code | Message | Action |
|------|---------|--------|
| `BACKUP_NO_SPACE` | Backup storage is full | Free space or increase allocation |
| `BACKUP_CORRUPTED` | Checksum mismatch | Use different backup |
| `BACKUP_NOT_FOUND` | Requested backup doesn't exist | List available backups |
| `RESTORE_HEALTH_FAILED` | Health checks failed post-restore | Restore different backup |
| `NEO4J_UNREACHABLE` | Cannot connect to Neo4j | Check Neo4j container status |
| `NEO4J_ADMIN_FAILED` | neo4j-admin command failed | Check neo4j-admin logs |
