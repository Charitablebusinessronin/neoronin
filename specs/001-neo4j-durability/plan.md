# Implementation Plan: Neo4j Memory Durability

**Branch**: `001-neo4j-durability` | **Date**: 2025-12-27 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-neo4j-durability/spec.md`

## Summary

Implement infrastructure durability for the Neo4j graph memory layer. Four user stories drive the design:
1. **Persistent Storage**: Named Docker volumes ensure data survives container restarts and host reboots
2. **Recovery Procedures**: Backup restoration with consistency validation enables recovery from corruption
3. **Automated Backups**: Scheduled, versioned backups with configurable retention prevent data loss
4. **Write Governance**: Audit logging and write-path control prevent unauthorized mutations

Technical approach: Docker-compose-based setup with Neo4j backup/restore tooling, optional sidecar backup service, health check API, and Graphiti write logging integration.

## Technical Context

**Language/Version**: Python 3.9+ (for backup/recovery scripting and health checks)
**Primary Dependencies**: Neo4j Docker image (5.0+), docker-compose, Neo4j admin tools (neo4j-admin)
**Storage**: Neo4j named volumes + local filesystem for backup storage
**Testing**: pytest for unit/integration tests; docker-compose for contract/system tests
**Target Platform**: Linux (WSL2, Docker Desktop on macOS/Windows, cloud VMs)
**Project Type**: Infrastructure/DevOps (dockerized services, no frontend)
**Performance Goals**: Backup <5min for 1M nodes/relationships; recovery <10min for 1GB backup; write log overhead <1ms per operation
**Constraints**: Non-blocking backups; graceful degradation on failure; minimal write path latency
**Scale/Scope**: Single Neo4j instance; 1M nodes/relationships target; 7-day default backup retention

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Principle I (Graph-First)**: ✅ PASS
- Feature creates and manages persistent Neo4j storage; all knowledge stays in graph
- Backups are full graph snapshots, not text exports
- Write logs are metadata in Neo4j (or adjacent log storage), not filesystem blobs

**Principle II (MCP Interface Contract)**: ✅ PASS
- Recovery and backup operations are exposed via health check endpoint (part of MCP gateway)
- Direct Neo4j access is prevented; write path is MCP → Graphiti → Neo4j
- Network isolation: Neo4j only accessible from MCP gateway container

**Principle III (Consistent Recall)**: ✅ PASS
- Backups preserve graph consistency; restore brings graph to known-good state
- Write logs enable replaying operations to understand system state at any point
- Health checks detect inconsistencies before queries fail

**Principle IV (Atomic Memory Updates)**: ✅ PASS
- Backup metadata tracks version and timestamp
- Recovery is atomic: restore completes fully or fails cleanly (no partial restore)
- Write logs are transactional (all-or-nothing per operation)

**Principle V (Containerized Deployment)**: ✅ PASS
- Neo4j runs in Docker with named volume persistence
- Backup/restore tooling is containerized (sidecar or init-container pattern)
- docker-compose.yml is the sole source of truth for infrastructure

**Principle VI (Memory Durability)**: ✅ PASS
- Feature IS the implementation of Principle VI
- Named volumes, automated backups, recovery procedures, write governance all covered

**Conclusion**: All constitution principles are satisfied. No violations. No complexity justification needed.

## Project Structure

### Documentation (this feature)

```text
specs/001-neo4j-durability/
├── plan.md                      # This file
├── research.md                  # Phase 0 output (best practices, tool selection)
├── data-model.md                # Phase 1 output (backup metadata, write logs schema)
├── quickstart.md                # Phase 1 output (operator setup guide)
├── contracts/
│   ├── health-check-api.md      # Health check endpoint contract
│   └── backup-restore-api.md    # Backup/restore CLI + API contracts
├── checklists/
│   └── requirements.md          # Specification quality (complete)
└── tasks.md                     # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
docker-compose.yml              # Updated: Neo4j service with named volume + backups
docker/
├── neo4j/                       # Neo4j Dockerfile (inherits official image)
└── backup-sidecar/              # Optional sidecar container for backup automation

scripts/
├── backup/
│   ├── neo4j-backup.py          # Wrapper around neo4j-admin backup
│   ├── neo4j-restore.py         # Wrapper around neo4j-admin restore
│   └── backup-scheduler.py      # Cron-like scheduler for automated backups
├── health/
│   └── health-check.py          # Graph consistency validation (orphans, schema)
└── setup/
    └── init-neo4j.sh            # Initialize named volumes and schema

src/
├── durability/
│   ├── backup.py                # Backup coordination (interface for backup sidecar)
│   ├── recovery.py              # Recovery state machine
│   └── write_log.py             # Write audit logging integration with Graphiti
└── health/
    └── checker.py               # Health check implementation

tests/
├── contract/
│   ├── test_health_endpoint.py  # Health check API contract tests
│   └── test_backup_restore.py   # Backup/restore CLI contract tests
├── integration/
│   ├── test_backup_workflow.py  # End-to-end backup + restore
│   ├── test_persistence.py      # Named volume data persistence
│   └── test_write_logs.py       # Write audit trail capture
└── unit/
    ├── test_backup_ops.py       # Backup tool operations
    ├── test_recovery_sm.py      # Recovery state machine
    └── test_health_checks.py    # Consistency validation logic
```

**Structure Decision**: Infrastructure/DevOps feature implemented primarily as docker-compose orchestration + Python utility scripts. No frontend; no distributed system. Python chosen for tooling because it's portable and good for devops scripting. Scripts live in `/scripts/` for easy operator access.

## Complexity Tracking

No violations detected. All constitution principles satisfied. Complexity is straightforward: containerized setup + backup tooling + health checks.
