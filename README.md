# Grap Neo4j Durability System

A production-ready Neo4j memory infrastructure for persistent graph-backed AI systems. Implements Constitution Principle VI with automated APOC-based backups, recovery procedures, health monitoring, and comprehensive audit logging.

## Features

### 🗄️ Persistent Storage
- Docker named volumes for Neo4j data and backups
- **APOC-based Logical Backups** (Community Edition compatible)
- Automatic schema initialization

### 🔄 Automated Backups
- Sidecar container using `apscheduler`
- `apoc.export.graphml.all` for logical graph dumps
- SHA256 checksum verification
- Configurable retention policy (default: 30 days)

### 🏥 Health Monitoring
- Connectivity checks (5s timeout)
- Orphaned relationship detection
- Fast-fail behavior

### 🐳 Containerization
- **Neo4j 5.13.0 Community**
- **Backup Scheduler Sidecar** (Python 3.9)
- Zero external vector dependencies (No Qdrant/Mem0)

## Quick Start

### Prerequisites
- Docker & Docker Compose 3.8+
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
   ```

3. **Start services**:
   ```bash
   docker compose up -d
   ```

4. **Verify startup**:
   ```bash
   # Check services
   docker ps

   # Verify backup capability
   docker exec grap-backup-scheduler python -c "from scripts.backup.neo4j_backup import BackupManager; from neo4j import GraphDatabase; import os; driver = GraphDatabase.driver(os.environ['NEO4J_URI'], auth=(os.environ['NEO4J_USER'], os.environ['NEO4J_PASSWORD'])); bm = BackupManager(driver, os.environ['BACKUP_DIR']); print(bm.create_backup())"
   ```

## Architecture

### Service Architecture

```
┌─────────────────────────────────────────────┐
│          Neo4j Database (5.13.0)            │
│  - Community Edition                        │
│  - APOC Plugin Enabled                      │
│  - Volume: grap-neo4j-data (/data)          │
│  - Volume: grap-backups (/import)           │
└────────────┬────────────────────────────────┘
             │
             │ Bolt (7687)
             │
    ┌────────▼────────┐
    │  Backup Sidecar │
    │ (Python 3.9)    │
    │  - Scheduler    │
    │  - Logic Checks │
    │  - Volume:      │
    │    grap-backups │
    └─────────────────┘
```

**Note**: We purposely avoid `neo4j-admin` backups to maintain compatibility with standard Docker volumes and Community Edition limitations. We use `apoc.export.graphml.all` to dump the graph structure and data to the shared volume.

## Configuration

### Environment Variables (.env)

| Variable | Default | Description |
|----------|---------|-------------|
| `NEO4J_AUTH` | `neo4j/Kamina2025*` | Database credentials |
| `BACKUP_SCHEDULE` | `0 2 * * *` | Cron schedule (2 AM daily) |
| `BACKUP_RETENTION_DAYS` | `30` | Backup retention period |

## Project Structure

```
Grap/
├── docker/
│   ├── neo4j/              # Database image config
│   └── backup-sidecar/     # Python scheduler logic
├── scripts/
│   ├── backup/             # BackupManager logic (APOC based)
│   └── health/             # Health check scripts
├── src/                    # Shared library code
├── docker-compose.yml      # Service definition
└── README.md               # This file
```

## Troubleshooting

### Backup Fails with "FileNotFound"
Ensure the `grap-backups` volume is correctly mounted to `/var/lib/neo4j/import` in the Neo4j container. APOC security settings restrict file writing to this directory.

### Backup Fails with "Export not enabled"
Check `docker-compose.yml` for `NEO4J_apoc_export_file_enabled: "true"`.
