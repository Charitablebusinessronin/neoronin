# Quickstart: Neo4j Memory Durability

**Feature**: 001-neo4j-durability
**Audience**: Infrastructure operators and developers
**Goal**: Set up, test, and operate Neo4j with durable backups in under 30 minutes

---

## Prerequisites

- Docker and docker-compose installed
- 10 GB free disk space (5 GB for Neo4j data, 5 GB for backup storage)
- Linux shell access (bash or zsh)

---

## 5-Minute Setup

### 1. Update docker-compose.yml

Add Neo4j service with named volume and backup storage:

```yaml
version: '3.8'

services:
  neo4j:
    image: neo4j:5.13.0
    container_name: grap-neo4j
    environment:
      NEO4J_ACCEPT_LICENSE_AGREEMENT: "yes"
      NEO4J_AUTH: "neo4j/changeme"
      NEO4J_initial_dbms_default__database__name: "neo4j"
    ports:
      - "127.0.0.1:7474:7474"  # HTTP (local only)
      - "127.0.0.1:7687:7687"  # Bolt (local only)
    volumes:
      - grap-neo4j-data:/var/lib/neo4j/data
      - grap-backups:/backups
    networks:
      - grap-network
    healthcheck:
      test: ["CMD", "cypher-shell", "-u", "neo4j", "-p", "changeme", "RETURN 1"]
      interval: 10s
      timeout: 5s
      retries: 3

  mcp-gateway:
    image: mcp-gateway:latest  # Your MCP implementation
    container_name: grap-mcp
    environment:
      NEO4J_HOST: neo4j
      NEO4J_PORT: 7687
      NEO4J_AUTH: "neo4j/changeme"
    ports:
      - "127.0.0.1:8080:8080"
    depends_on:
      neo4j:
        condition: service_healthy
    networks:
      - grap-network

volumes:
  grap-neo4j-data:
    driver: local
  grap-backups:
    driver: local

networks:
  grap-network:
    driver: bridge
    driver_opts:
      com.docker.network.driver.mtu: 1450
```

**Key Details**:
- `grap-neo4j-data`: Persists Neo4j data across restarts
- `grap-backups`: Stores backup files
- Network: Only MCP gateway can access Neo4j (port 7687 not exposed to host)
- Healthcheck: Validates Neo4j is accepting connections

### 2. Start Services

```bash
docker-compose up -d
```

Verify Neo4j is healthy:

```bash
docker-compose ps
# NAME               STATUS
# grap-neo4j        Up 5s (healthy)
# grap-mcp          Up 2s
```

### 3. Create First Backup

```bash
python scripts/backup/neo4j-backup.py --create
```

Expected output:

```
INFO: Starting backup creation...
INFO: Neo4j version: 5.13.0
SUCCESS: Backup completed
```

Verify backup was created:

```bash
python scripts/backup/neo4j-backup.py --list
# Available Backups:
# neo4j-20251227-153000 ... COMPLETE
```

---

## Testing Data Persistence

### Test 1: Container Restart

Verify data survives container restart:

```bash
# Create sample data
docker exec grap-neo4j cypher-shell -u neo4j -p changeme \
  "CREATE (n:TestNode {id: 'test-1', created: datetime()})"

# Kill the container
docker-compose stop neo4j

# Wait 5 seconds
sleep 5

# Restart
docker-compose up -d neo4j

# Wait for healthy
sleep 10

# Verify data persists
docker exec grap-neo4j cypher-shell -u neo4j -p changeme \
  "MATCH (n:TestNode) RETURN count(n) as count"
# Result: count = 1
```

### Test 2: Host Reboot Simulation

Verify data persists through hard restart:

```bash
# Create test data
docker exec grap-neo4j cypher-shell -u neo4j -p changeme \
  "CREATE (n:TestNode {id: 'test-2', data: 'persistent'})"

# Stop all containers
docker-compose down

# Restart (simulates host reboot)
docker-compose up -d

# Verify data
docker exec grap-neo4j cypher-shell -u neo4j -p changeme \
  "MATCH (n:TestNode {id: 'test-2'}) RETURN n.data"
# Result: "persistent"
```

---

## Testing Backup & Restore

### Test 3: Backup → Deliberate Corruption → Restore

Verify recovery from backup:

```bash
# Create test data before backup
docker exec grap-neo4j cypher-shell -u neo4j -p changeme \
  "CREATE (n:CriticalData {id: 'critical-1', name: 'Important'})"

# Create backup
python scripts/backup/neo4j-backup.py --create
BACKUP_ID=$(python scripts/backup/neo4j-backup.py --list | grep "neo4j-" | head -1 | awk '{print $1}')

# Simulate corruption: delete all CriticalData
docker exec grap-neo4j cypher-shell -u neo4j -p changeme \
  "MATCH (n:CriticalData) DELETE n"

# Verify data is gone
docker exec grap-neo4j cypher-shell -u neo4j -p changeme \
  "MATCH (n:CriticalData) RETURN count(n) as count"
# Result: count = 0

# Restore from backup
python scripts/backup/neo4j-restore.py --backup-id $BACKUP_ID --validate
# Restores to test-neo4j instance
# Runs health checks
# Output: "SUCCESS: Restore completed and validated"

# Promote to production (manual verification step)
python scripts/backup/neo4j-restore.py --promote
# Swaps test instance to production

# Verify data is restored
docker exec grap-neo4j cypher-shell -u neo4j -p changeme \
  "MATCH (n:CriticalData) RETURN n.name"
# Result: "Important"
```

---

## Testing Health Checks

### Test 4: Health Check API

Verify the health endpoint works:

```bash
# Check health (should be healthy)
curl http://localhost:8080/health/graph
# Response:
# {
#   "status": "healthy",
#   "checks": {
#     "connectivity": {"status": "pass"},
#     "schema_consistency": {"status": "pass"},
#     "orphan_detection": {"status": "pass"}
#   }
# }

# Detailed health check
curl http://localhost:8080/health/graph?detailed=true
# Returns additional check durations and graph statistics
```

### Test 5: Health Check Detects Problems

Stop Neo4j and verify health check fails:

```bash
# Stop Neo4j
docker-compose stop neo4j

# Health check should fail
curl http://localhost:8080/health/graph
# Response: 503 Service Unavailable
# {
#   "status": "unhealthy",
#   "failed_check": "connectivity",
#   "message": "Cannot reach Neo4j..."
# }

# Restart Neo4j
docker-compose up -d neo4j
sleep 10

# Health check should pass again
curl http://localhost:8080/health/graph
# Response: 200 OK, status "healthy"
```

---

## Setting Up Automated Backups

### Enable Automatic Backup Scheduler

Add to docker-compose.yml:

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
    BACKUP_ALERT_EMAIL: ops@example.com
  command: python /app/scripts/backup/neo4j-backup.py --schedule
  depends_on:
    - neo4j
  networks:
    - grap-network
```

Start the scheduler:

```bash
docker-compose up -d backup-scheduler
```

Monitor scheduler:

```bash
docker logs -f grap-backup-scheduler
# INFO: Backup scheduler started
# INFO: Schedule: Daily at 02:00 UTC
# INFO: Next backup: 2025-12-28 02:00:00 UTC
```

---

## Daily Operations

### Check Backup Status

```bash
python scripts/backup/neo4j-backup.py --list
```

### Create Manual Backup

```bash
python scripts/backup/neo4j-backup.py --create
```

### Check Neo4j Health

```bash
curl http://localhost:8080/health/graph
```

### View Neo4j Logs

```bash
docker logs -f grap-neo4j
```

### Recovery (Emergency)

If Neo4j becomes corrupted:

```bash
# List available backups
python scripts/backup/neo4j-backup.py --list

# Restore from most recent backup
python scripts/backup/neo4j-restore.py --backup-id neo4j-20251227-153000 --validate

# Verify health on restored instance
curl http://localhost:8080/health/graph

# Promote to production
python scripts/backup/neo4j-restore.py --promote

# Verify production is operational
curl http://localhost:8080/health/graph
```

---

## Troubleshooting

### Problem: Backup Failed with "No Space Left"

```bash
# Check available space
df -h /backups

# If full, delete old backups
python scripts/backup/neo4j-backup.py --cleanup --delete-expired

# Or increase allocation
# Edit docker-compose.yml and increase grap-backups volume
```

### Problem: Restore Failed - "Checksum Mismatch"

```bash
# Backup file is corrupted on disk
# Try a different backup
python scripts/backup/neo4j-restore.py --backup-id <older_backup_id>
```

### Problem: Health Check Fails - "Orphaned Relationships"

```bash
# Graph has corruption
# 1. Restore from backup (see Recovery section above)
# 2. If all backups have orphans, investigate backup creation time
#    (corruption may have occurred before backup was taken)
```

### Problem: Neo4j Container Won't Start

```bash
# Check logs
docker logs grap-neo4j

# If volume is corrupted, restore from backup
docker-compose stop neo4j
python scripts/backup/neo4j-restore.py --backup-id <backup_id> --promote
docker-compose up -d neo4j
```

---

## Next Steps

1. **Production Deployment**: Adjust `docker-compose.yml` for your environment (resource limits, memory, etc.)
2. **Monitoring**: Set up alerts on health check failures and backup failures
3. **Documentation**: Share recovery procedure with your team
4. **Testing**: Run a recovery drill monthly to ensure procedures work
5. **Backup Offsite** (Future): Consider adding S3 upload after initial stable period

---

## Reference

- Specification: [spec.md](./spec.md)
- Data Model: [data-model.md](./data-model.md)
- Health Check API: [contracts/health-check-api.md](./contracts/health-check-api.md)
- Backup/Restore: [contracts/backup-restore-api.md](./contracts/backup-restore-api.md)
- Constitution: [Principle VI - Memory Durability](.specify/memory/constitution.md)
