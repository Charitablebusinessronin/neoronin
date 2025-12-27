# Grap Neo4j Durability System

A production-ready Neo4j memory durability infrastructure for persistent graph-backed AI systems. Implements Constitution Principle VI with automated backups, recovery procedures, health monitoring, and comprehensive audit logging.

## Features

### 🗄️ Persistent Storage
- Docker named volumes for Neo4j data and backups
- Automatic schema initialization on container startup
- Named volume lifecycle management
- Data persistence across restarts

### 🔄 Automated Backups
- APScheduler-based backup scheduling (default: daily at 2 AM)
- SHA256 checksum verification
- Configurable retention policy (default: 30 days)
- Automatic cleanup of old backups
- Compression support

### 🔧 Recovery Procedures
- Safe restore-to-test workflow
- Multi-tier validation (connectivity, schema, orphans)
- Production promotion gates
- Atomic state transitions
- Rollback on validation failure

### 🏥 Health Monitoring
- Connectivity checks (5s timeout)
- Schema consistency verification (10s timeout)
- Orphaned relationship detection (30s timeout)
- Fast-fail behavior for rapid issue detection
- JSON and text output formats

### 📝 Write Governance
- Comprehensive audit logging of all operations
- Actor tracking and attribution
- Operation result tracking (SUCCESS/FAILED/PARTIAL)
- Immutable audit trail
- Entity-level operation tracking

### 🐳 Containerization
- Docker Compose orchestration
- Neo4j 5.13.0 community edition
- Python 3.9 sidecar services
- Network isolation (internal-only)
- Health checks for all services

## Quick Start

### Prerequisites
- Docker & Docker Compose 3.8+
- 50GB+ available disk space
- 4GB+ RAM

### Installation

1. **Clone the repository**:
```bash
git clone https://github.com/your-org/Grap.git
cd Grap
```

2. **Configure environment**:
```bash
cp .env.example .env
# Edit .env - change default credentials in production!
```

3. **Start services**:
```bash
docker-compose up -d
```

4. **Verify startup**:
```bash
# Check all services healthy
docker-compose ps

# View initialization logs
docker logs grap-neo4j | grep "Schema initialization"

# Run health check
docker exec grap-mcp python -m scripts.health.health_check
```

### Create a Test Backup

```bash
# Verify backup scheduler is running
docker logs grap-backup-scheduler

# List backups
docker exec grap-backup-scheduler python -c "
from scripts.backup.neo4j_backup import BackupManager
from neo4j import GraphDatabase
driver = GraphDatabase.driver('bolt://neo4j:7687', auth=('neo4j', 'changeme'))
for b in BackupManager(driver, '/app/backups').list_backups():
    print(f'{b[\"id\"]}: {b[\"status\"]}, {b[\"size_bytes\"]} bytes')
driver.close()
"
```

## Project Structure

```
Grap/
├── docker/
│   ├── neo4j/
│   │   ├── Dockerfile          # Neo4j with custom entrypoint
│   │   └── entrypoint.sh        # Schema initialization wrapper
│   └── backup-sidecar/
│       └── Dockerfile          # Backup scheduler container
├── src/
│   ├── durability/
│   │   ├── recovery.py          # RecoveryStateMachine
│   │   └── backup.py            # DurabilityOrchestrator
│   └── health/
│       └── checker.py           # HealthChecker with 3-tier checks
├── scripts/
│   ├── backup/
│   │   ├── neo4j-backup.py     # BackupManager
│   │   ├── neo4j-restore.py    # RestoreManager
│   │   └── backup_scheduler.py  # Automated scheduling
│   ├── health/
│   │   └── health-check.py      # CLI interface
│   └── setup/
│       └── init-neo4j.sh        # Schema constraints/indices
├── tests/
│   ├── integration/
│   │   ├── test_persistent_storage.py   # US1 tests
│   │   ├── test_recovery_workflow.py     # US2 tests
│   │   ├── test_backup_automation.py     # US3 tests
│   │   ├── test_write_governance.py      # US4 tests
│   │   └── test_health_checks.py         # Health check tests
│   └── unit/
│       └── test_backup_manager.py        # BackupManager tests
├── docs/
│   ├── OPERATOR_GUIDE.md        # Operational procedures
│   └── API.md                   # API reference (if applicable)
├── docker-compose.yml            # Service orchestration
├── requirements.txt              # Python dependencies
├── .env.example                 # Configuration template
└── README.md                    # This file
```

## Configuration

### Environment Variables

Key settings in `.env`:

```bash
# Neo4j Connection
NEO4J_AUTH=neo4j/changeme              # CHANGE IN PRODUCTION!
NEO4J_URI=bolt://neo4j:7687

# Backup Settings
BACKUP_SCHEDULE="0 2 * * *"           # Cron: 2 AM daily
BACKUP_RETENTION_DAYS=30              # Keep 30 days
BACKUP_COMPRESSION=true               # Compress backups

# Recovery
PROMOTE_AFTER_VALIDATION=false        # Require manual promotion

# Monitoring
LOG_LEVEL=INFO
```

## Usage

### Health Checks

```bash
# Human-readable output
docker exec grap-mcp python -m scripts.health.health_check

# JSON output (for monitoring)
docker exec grap-mcp python -m scripts.health.health_check --format json

# Include detailed metrics
docker exec grap-mcp python -m scripts.health.health_check --detailed
```

### Backup Operations

```bash
# List all backups
docker exec grap-backup-scheduler python -c "
from scripts.backup.neo4j_backup import BackupManager
from neo4j import GraphDatabase
driver = GraphDatabase.driver('bolt://neo4j:7687', auth=('neo4j', 'changeme'))
manager = BackupManager(driver, '/app/backups')
for b in manager.list_backups():
    print(f'{b[\"id\"]}: {b[\"status\"]}, {b[\"size_bytes\"]} bytes')
driver.close()
"

# Create backup
docker exec grap-backup-scheduler python -c "
from scripts.backup.neo4j_backup import BackupManager
from neo4j import GraphDatabase
import uuid
driver = GraphDatabase.driver('bolt://neo4j:7687', auth=('neo4j', 'changeme'))
manager = BackupManager(driver, '/app/backups')
success, msg, metadata = manager.create_backup()
print(f'Backup {metadata[\"id\"]}: {msg}')
driver.close()
"
```

### Recovery Procedures

```bash
# Start recovery with validation
docker exec grap-mcp python -c "
from src.durability.backup import DurabilityOrchestrator
from neo4j import GraphDatabase
driver = GraphDatabase.driver('bolt://neo4j:7687', auth=('neo4j', 'changeme'))
orchestrator = DurabilityOrchestrator(driver, '/app/backups')
success, msg = orchestrator.restore_with_validation('backup-id')
print(f'Recovery: {msg}')
driver.close()
"

# Promote to production (after successful validation)
docker exec grap-mcp python -c "
from src.durability.backup import DurabilityOrchestrator
from neo4j import GraphDatabase
driver = GraphDatabase.driver('bolt://neo4j:7687', auth=('neo4j', 'changeme'))
orchestrator = DurabilityOrchestrator(driver, '/app/backups')
success, msg = orchestrator.promote_backup_to_production()
print(f'Promotion: {msg}')
driver.close()
"
```

## Testing

### Run All Tests

```bash
# Integration tests (requires running containers)
docker exec grap-mcp pytest tests/integration -v

# Unit tests
docker exec grap-mcp pytest tests/unit -v

# Specific test file
docker exec grap-mcp pytest tests/integration/test_health_checks.py -v
```

### Test Coverage

- **Unit tests**: 20 tests for backup manager
- **Integration tests**: 67 tests across 5 modules
  - Persistent storage: 14 tests
  - Recovery workflow: 18 tests
  - Backup automation: 20 tests
  - Write governance: 18 tests
  - Health checks: 15 tests

## Architecture

### Service Architecture

```
┌─────────────────────────────────────────────┐
│          Neo4j Database (5.13.0)            │
│  - BackupMetadata nodes                     │
│  - AuditLogEntry nodes                      │
│  - RecoveryState nodes                      │
│  - Named volume: grap-neo4j-data            │
└────────────┬────────────────────────────────┘
             │
    ┌────────┴────────┬──────────────────┐
    │                 │                  │
┌───▼────────┐  ┌────▼────────┐  ┌─────▼─────┐
│  Backup    │  │   Health    │  │    MCP    │
│ Scheduler  │  │   Check     │  │  Gateway  │
│            │  │   CLI       │  │           │
│ APScheduler│  │ (JSON/Text) │  │ Interface │
└────────────┘  └─────────────┘  └───────────┘
     │
     └─→ Backups Volume (grap-backups)
         - Backup files
         - Metadata
         - Checksums
```

### State Machine Architecture

Recovery follows this state machine:

```
    ┌─────────────────────┐
    │  NOT_RECOVERING     │
    │   (initial)         │
    └──────────┬──────────┘
               │
               │ initialize_recovery()
               ▼
    ┌─────────────────────┐
    │   RECOVERING        │ (restore in progress)
    │  progress: 0-100%   │
    └──────────┬──────────┘
               │
               │ start_validation()
               ▼
    ┌─────────────────────┐
    │   VALIDATION        │ (health checks)
    │  progress: 100%     │
    └────┬────────────┬───┘
         │            │
         │ PASS       │ FAIL
         ▼            ▼
  ┌────────────┐  ┌──────────────┐
  │   SUCCESS  │  │   FAILED     │
  │            │  │              │
  │  promote() │  │ (rollback)   │
  │    ↓       │  │    ↓         │
  │ PROMOTED   │  │ reset()      │
  └────────────┘  └──────────────┘
         │              │
         └──────┬───────┘
                │
                ▼
        NOT_RECOVERING
```

## API Reference

### HealthChecker

```python
from src.health.checker import HealthChecker

checker = HealthChecker(driver)

# Run all checks
result = checker.perform_all_checks(detailed=True)
# Returns: {
#   'status': 'healthy|unhealthy',
#   'timestamp': '2024-01-15T10:30:00Z',
#   'checks': {
#     'connectivity': {'status': 'pass|fail|skipped', 'duration_ms': int},
#     'schema_consistency': {...},
#     'orphan_detection': {...}
#   }
# }
```

### RecoveryStateMachine

```python
from src.durability.recovery import RecoveryStateMachine

machine = RecoveryStateMachine(driver)

# Operations
machine.initialize_recovery('backup-id')
machine.update_progress(50)
machine.start_validation()
machine.validation_passed()  # or validation_failed(['error1', 'error2'])
machine.promote_to_production()
machine.reset_recovery_state()
```

### DurabilityOrchestrator

```python
from src.durability.backup import DurabilityOrchestrator

orchestrator = DurabilityOrchestrator(driver, '/path/to/backups')

# Backup operations
success, msg, metadata = orchestrator.backup_and_verify()
backups = orchestrator.list_backups_with_status()
deleted, msg = orchestrator.cleanup_old_backups(retention_days=30)

# Recovery operations
success, msg = orchestrator.restore_with_validation('backup-id')
success, msg = orchestrator.promote_backup_to_production()
state = orchestrator.get_recovery_status()

# Health checks
health = orchestrator.check_database_health(detailed=True)
```

## Monitoring & Alerting

### Prometheus Integration

Export health status to Prometheus:

```bash
# Get JSON metrics
docker exec grap-mcp python -m scripts.health.health_check --format json | jq '.'
```

### Alert Rules

Example alert for unhealthy database:

```yaml
groups:
  - name: neo4j
    rules:
      - alert: NeoDBUnhealthy
        expr: neo4j_health_status == 0
        for: 5m
        annotations:
          summary: "Neo4j database unhealthy"
```

## Compliance

### Constitution Principle VI - Memory Durability

This system satisfies all requirements:

✓ **Named Volumes**: Docker-managed persistent storage
✓ **Automated Backups**: APScheduler with configurable retention
✓ **Recovery Procedures**: Safe restore with validation gates
✓ **Write Governance**: Comprehensive audit logging
✓ **Health Checks**: Three-tier verification system

See [Operator Guide](docs/OPERATOR_GUIDE.md) for detailed compliance verification.

## Troubleshooting

### Backup Creation Fails
```bash
docker logs grap-backup-scheduler
docker exec grap-neo4j df -h /backups  # Check disk space
```

### Recovery Validation Fails
```bash
docker exec grap-mcp python -m scripts.health.health_check --detailed
docker logs grap-neo4j  # Check Neo4j logs
```

### Schema Not Initialized
```bash
bash scripts/setup/init-neo4j.sh
```

See [Operator Guide - Troubleshooting](docs/OPERATOR_GUIDE.md#troubleshooting) for more.

## Development

### Running Tests Locally

```bash
# Install test dependencies
pip install -r requirements.txt

# Run tests (requires Docker stack running)
pytest tests/ -v

# Specific test file
pytest tests/integration/test_health_checks.py -v
```

### Building Custom Images

```bash
# Build Neo4j image
docker build -f docker/neo4j/Dockerfile -t grap-neo4j .

# Build backup-scheduler image
docker build -f docker/backup-sidecar/Dockerfile -t grap-scheduler .
```

## Documentation

- [Operator Guide](docs/OPERATOR_GUIDE.md) - Operational procedures, backup/recovery, troubleshooting
- [Specification](specs/001-neo4j-durability/spec.md) - Requirements and acceptance criteria
- [Implementation Plan](specs/001-neo4j-durability/plan.md) - Architecture and design decisions
- [Data Model](specs/001-neo4j-durability/data-model.md) - Neo4j schema and relationships

## License

This project is part of the Grap system. See LICENSE file for details.

## Contributing

1. Create feature branch from `master`
2. Make changes and add tests
3. Run test suite: `pytest tests/`
4. Submit pull request
5. Ensure all checks pass

## Support

For issues:
1. Check [Operator Guide - Troubleshooting](docs/OPERATOR_GUIDE.md#troubleshooting)
2. Review test cases for usage examples
3. Check container logs: `docker logs [container-name]`

## Changelog

### Version 1.0.0 (2024-01-15)
- Initial release
- Automated backup scheduling
- Recovery state machine
- Health check system
- Audit logging
- Docker containerization
- Comprehensive test suite
- Operator documentation
