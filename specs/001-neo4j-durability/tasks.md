---

description: "Task list for Neo4j Memory Durability feature implementation"

---

# Tasks: Neo4j Memory Durability

**Input**: Design documents from `/specs/001-neo4j-durability/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/, quickstart.md

**Tests**: NOT included in this task list (feature spec did not request TDD approach)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story. Each user story is independently testable and deployable.

## Format: `[ID] [P?] [Story?] Description`

- **[ID]**: Task identifier (T001, T002, etc.) in execution order
- **[P]**: Parallelizable (different files, no dependencies on incomplete tasks)
- **[Story]**: User story label (US1, US2, US3, US4) - REQUIRED for story phase tasks only
- **Description**: Action with exact file paths

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create docker-compose.yml with Neo4j service, named volumes (grap-neo4j-data, grap-backups), and MCP gateway network isolation
- [ ] T002 [P] Create docker/neo4j/Dockerfile inheriting from neo4j:5.13.0 with required admin tools
- [ ] T003 [P] Create docker/backup-sidecar/Dockerfile with Python 3.9 base for backup scheduler
- [ ] T004 [P] Create .env.example with backup configuration defaults (BACKUP_SCHEDULE, BACKUP_RETENTION_DAYS, etc.)
- [ ] T005 [P] Create scripts/backup/ directory structure and __init__.py files
- [ ] T006 [P] Create scripts/health/ directory structure and __init__.py files
- [ ] T007 [P] Create src/durability/ directory structure and __init__.py files
- [ ] T008 [P] Create src/health/ directory structure and __init__.py files
- [ ] T009 [P] Create tests/contract/, tests/integration/, tests/unit/ directories
- [ ] T010 Create scripts/setup/init-neo4j.sh to initialize named volumes and create schema constraints

**Checkpoint**: Project structure ready; docker-compose can start Neo4j with persistent volumes

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Infrastructure and core systems that MUST be complete before ANY user story can be implemented

- [ ] T011 Implement src/durability/recovery.py with RecoveryState machine (NOT_RECOVERING, RECOVERING, VALIDATION, SUCCESS, FAILED)
- [ ] T012 Implement src/health/checker.py with three-check protocol (connectivity, schema_consistency, orphan_detection)
- [ ] T013 Implement scripts/health/health-check.py CLI wrapper exposing /health/graph endpoint logic
- [ ] T014 [P] Implement scripts/backup/neo4j-backup.py with create, list, delete, validate operations (wraps neo4j-admin backup)
- [ ] T015 [P] Implement scripts/backup/neo4j-restore.py with restore, validate, promote operations (wraps neo4j-admin restore)
- [ ] T016 [P] Implement scripts/backup/backup-scheduler.py with APScheduler integration (daily backup, retention cleanup)
- [ ] T017 Implement Neo4j schema constraints in scripts/setup/init-neo4j.sh (BackupMetadata, AuditLogEntry, RecoveryState unique constraints)
- [ ] T018 Update docker-compose.yml to include backup-scheduler service with BACKUP_SCHEDULE env var
- [ ] T019 Create src/durability/backup.py module providing interface for backup orchestration (called from Python code, not just CLI)
- [ ] T020 Create requirements.txt with dependencies: neo4j, apscheduler, pyyaml, pytest

**Checkpoint**: Foundation ready - backup tooling, recovery state machine, health checks all functional. No user story work can begin until this phase completes.

---

## Phase 3: User Story 1 - Operator Deploys Neo4j with Persistent Storage (Priority: P1) 🎯 MVP

**Goal**: Operator can deploy docker-compose and data survives container restarts and host reboots

**Independent Test**: Operator deploys, creates test data, kills container, restarts, verifies data intact and queryable

### Implementation for User Story 1

- [ ] T021 [P] [US1] Update docker-compose.yml Neo4j service with proper volume mounts and healthcheck
- [ ] T022 [P] [US1] Configure docker-compose.yml to use named volume grap-neo4j-data with proper driver options
- [ ] T023 [P] [US1] Create documentation/DEPLOYMENT.md with deployment instructions for WSL2, Docker Desktop, Linux
- [ ] T024 [US1] Implement src/durability/backup.py function `backup_metadata_from_neo4j()` to create BackupMetadata nodes on backup completion
- [ ] T025 [US1] Test persistence: Docker container kill → restart → verify data queryable (manual test documented in quickstart.md)
- [ ] T026 [US1] Document recovery procedure in docs/RECOVERY.md with step-by-step operator instructions
- [ ] T027 [US1] Create docker/neo4j/healthcheck-wrapper.sh that docker-compose healthcheck calls to verify Neo4j is up

**Checkpoint**: Operator can deploy, create data, and data persists across restarts

---

## Phase 4: User Story 2 - Operator Performs Recovery from Corruption (Priority: P1)

**Goal**: Operator can restore from backup, bringing graph to consistent state with zero data loss

**Independent Test**: Corrupt graph (delete entities), restore from pre-corruption backup, verify health checks pass and data intact

### Implementation for User Story 2

- [ ] T028 [P] [US2] Create src/durability/recovery.py RecoveryState transition functions (start_recovery, validation_passed, validation_failed, promote_to_production)
- [ ] T029 [P] [US2] Enhance scripts/backup/neo4j-restore.py with state machine integration (update RecoveryState during restore progress)
- [ ] T030 [P] [US2] Implement restore validation: Run health checks on restored instance before allowing promotion
- [ ] T031 [US2] Create scripts/backup/neo4j-restore.py --promote function that swaps test instance to production (docker-compose update)
- [ ] T032 [US2] Create docs/RECOVERY-PROCEDURE.md with detailed step-by-step recovery process (including tests to verify restored data)
- [ ] T033 [US2] Implement scripts/backup/neo4j-restore.py error handling for corrupted backups (checksum validation, clear error messages)
- [ ] T034 [US2] Test recovery: Deliberately corrupt graph, restore from backup, verify consistency via health checks (manual test in quickstart.md)
- [ ] T035 [US2] Create scripts/backup/backup-validator.py to validate backup integrity independent of restore (offline validation)

**Checkpoint**: Operator can recover from corruption within 10 minutes; all pre-corruption data restored

---

## Phase 5: User Story 3 - System Automatically Backs Up Graph on Schedule (Priority: P1)

**Goal**: Backups are created automatically without manual intervention; retention policy enforced; old backups cleaned up

**Independent Test**: Deploy system, run 24 hours, verify 2+ backups exist at different times, both restorable; verify old backups deleted per retention

### Implementation for User Story 3

- [ ] T036 [P] [US3] Implement scripts/backup/backup-scheduler.py with APScheduler (parse BACKUP_SCHEDULE cron expression, run neo4j-backup.py at scheduled time)
- [ ] T037 [P] [US3] Implement backup scheduler retention cleanup (compare timestamp_expires with current time, delete expired BackupMetadata + backup files)
- [ ] T038 [P] [US3] Implement backup scheduler failure handling (retry with exponential backoff; alert on repeated failures)
- [ ] T039 [P] [US3] Enhance scripts/backup/neo4j-backup.py to create BackupMetadata nodes in Neo4j (timestamp_created, backup_file, checksum, status: COMPLETE)
- [ ] T040 [P] [US3] Implement backup file compression: gzip backup after creation, store .backup.gz with metadata in separate .meta JSON file
- [ ] T041 [P] [US3] Implement scripts/backup/backup-scheduler.py logging (log each backup start/success/failure with timestamps)
- [ ] T042 [US3] Create docker/backup-sidecar/entrypoint.sh that starts scheduler service in docker-compose
- [ ] T043 [US3] Create docs/BACKUP-POLICY.md documenting retention rules (7 daily, 4 weekly, 1 monthly; configurable via env)
- [ ] T044 [US3] Test backup automation: Run scheduler for 24 hours simulated time, verify correct number of backups created and old ones deleted (test/integration/test_backup_scheduler.py)

**Checkpoint**: Backups are created on schedule; retention policy enforced; no manual operator action needed

---

## Phase 6: User Story 4 - Write Paths Are Governed and Logged (Priority: P2)

**Goal**: All writes to graph flow through MCP → Graphiti → Neo4j; audit trail captures every mutation with timestamps, actors, payloads

**Independent Test**: Confirm MCP writes are logged with full audit trail; verify direct writes are detected and logged/rejected

### Implementation for User Story 4

- [ ] T045 [P] [US4] Implement src/durability/write_log.py module with `log_mutation(operation, actor, payload, affected_entity_ids)` function
- [ ] T046 [P] [US4] Implement write_log.py to create AuditLogEntry nodes in Neo4j (timestamp, operation, actor, result, affected_entity IDs as relationships)
- [ ] T047 [P] [US4] Integrate write_log.py with Graphiti's mutation pipeline (called after each CREATE/UPDATE/DELETE, same transaction)
- [ ] T048 [P] [US4] Create src/durability/write_monitor.py to detect unauthorized writes to Neo4j (not via MCP/Graphiti)
- [ ] T049 [US4] Create src/durability/write_monitor.py endpoint (optionally exposed via MCP) for querying audit trail (e.g., "all writes to User in last 24h")
- [ ] T050 [US4] Create docs/WRITE-GOVERNANCE.md documenting which write paths are allowed, how to query audit logs, how to replay operations
- [ ] T051 [US4] Test write audit: Perform writes via MCP, verify AuditLogEntry nodes created with correct metadata; test query audit trail by entity type and time window
- [ ] T052 [US4] Test unauthorized write detection: Attempt direct Cypher write (not via MCP), verify it's logged as UNAUTHORIZED_WRITE or rejected

**Checkpoint**: All mutations are audited; write governance is enforced; audit trail is queryable

---

## Phase 7: Integration & Health Check API

**Purpose**: Tie all pieces together; expose health endpoint

- [ ] T053 [P] Create src/health/api.py with HTTP endpoint GET /health/graph (returns JSON with status and check results)
- [ ] T054 [P] Create src/health/api.py support for ?detailed=true query param (returns check durations and graph stats)
- [ ] T055 [P] Integrate src/health/api.py with MCP gateway (endpoint accessible via http://localhost:8080/health/graph)
- [ ] T056 [US4] Implement health check for write log consistency (verify no orphaned AuditLogEntry nodes)
- [ ] T057 Create tests/contract/test_health_endpoint.py with contract tests for all health check scenarios (healthy, unhealthy, recovery in progress)
- [ ] T058 [P] Create docs/HEALTH-CHECKS.md with operator guide to interpreting health endpoint responses

**Checkpoint**: Health endpoint is operational; operators can monitor graph health

---

## Phase 8: Documentation & Operator Guides

**Purpose**: Comprehensive documentation for deployment, operation, and recovery

- [ ] T059 Update README.md to reference durability features (named volumes, automatic backups, recovery procedures)
- [ ] T060 Create docs/OPERATIONS.md with daily operational tasks (check backup status, monitor health, manually trigger backups if needed)
- [ ] T061 Create docs/TROUBLESHOOTING.md with common issues and solutions (backup failures, restore failures, health check issues)
- [ ] T062 [P] Create backup failure alert template (email/Slack message with action items for operators)
- [ ] T063 [P] Create recovery drill checklist (steps to practice recovery procedure monthly)
- [ ] T064 Review and finalize quickstart.md with actual file paths and commands from implementation

**Checkpoint**: Operators have complete documentation for all scenarios

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Improvements and validation across all stories

- [ ] T065 [P] Add comprehensive error handling to all Python scripts (backup, restore, health checks)
- [ ] T066 [P] Add logging to all Python modules (use Python logging module, log to stdout/file)
- [ ] T067 [P] Create scripts/test/run-all-tests.sh to run unit, integration, contract tests
- [ ] T068 [P] Create scripts/setup/verify-setup.sh to validate docker-compose configuration and named volumes
- [ ] T069 Validate all tasks complete all 4 user stories (each is independently testable)
- [ ] T070 Create docs/ARCHITECTURE.md summarizing Neo4j durability design (schema, backup strategy, recovery flow)
- [ ] T071 Validate docker-compose.yml with `docker-compose config` (catch YAML errors)
- [ ] T072 Run quickstart.md tests end-to-end (persistence test, backup test, restore test, health check test)
- [ ] T073 Create CHANGELOG.md entry documenting durability feature
- [ ] T074 Run final validation: Deploy from scratch using docker-compose up, verify all components healthy

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - **BLOCKS all user stories**
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - US1 (Persistent Storage): Can start after Foundational
  - US2 (Recovery): Can start after Foundational (depends on US1 for practical testing)
  - US3 (Automated Backups): Can start after Foundational (depends on US1, US2 for validation)
  - US4 (Write Governance): Can start after Foundational (independent from US1-3)
- **Integration (Phase 7)**: Depends on all user story phases
- **Documentation (Phase 8)**: Depends on all implementation phases
- **Polish (Phase 9)**: Depends on all prior phases

### User Story Dependencies

| Story | Blocks | Depends On |
|-------|--------|-----------|
| US1 (Persistent Storage) | US2, US3, US4 practically | Phase 2 Foundational |
| US2 (Recovery) | US3 practically | Phase 2 Foundational, US1 |
| US3 (Automated Backups) | None | Phase 2 Foundational, US1, US2 |
| US4 (Write Governance) | None | Phase 2 Foundational |

### Parallel Opportunities

**Phase 1 Setup** (all marked [P] can run in parallel):
- T002, T003, T004, T005, T006, T007, T008, T009 - different files, no interdependencies

**Phase 2 Foundational** (marked [P] can run in parallel):
- T014 (neo4j-backup.py) + T015 (neo4j-restore.py) + T016 (scheduler) - independent scripts
- T002, T012, T013 - independent implementations

**Phase 3 User Story 1** (marked [P] can run in parallel):
- T021, T022, T023 - different files

**Phase 4 User Story 2** (marked [P] can run in parallel):
- T028, T029, T030 - independent functions and modules

**Phase 5 User Story 3** (marked [P] can run in parallel):
- T036, T037, T038, T039, T040, T041 - independent scheduler components

**Phase 6 User Story 4** (marked [P] can run in parallel):
- T045, T046, T047, T048 - independent logging and monitoring modules

**Phase 7 Integration** (marked [P]):
- T053, T054, T055, T058 - independent endpoints and health checks

**Phase 8 Documentation** (marked [P]):
- T062, T063, T064 - independent documentation files

**Phase 9 Polish** (marked [P]):
- T065, T066, T067, T068 - independent error handling, logging, test scripts

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (backup tooling, recovery SM, health checks)
3. Complete Phase 3: User Story 1 (persistent storage)
4. **STOP and VALIDATE**: Test data persistence (container restart, host reboot)
5. Deploy/demo if ready

**MVP Scope**: Operator can deploy and data survives restarts. Backup tooling exists but not automated.

**MVP Timeline**: ~3-5 days for 1-2 developers

### Incremental Delivery

1. Phase 1: Setup (1 day)
2. Phase 2: Foundational (2-3 days)
3. Phase 3: US1 Persistent Storage (1 day) → **MVP Deployable**
4. Phase 4: US2 Recovery (2 days) → Full recovery capability
5. Phase 5: US3 Automated Backups (2 days) → Hands-off operation
6. Phase 6: US4 Write Governance (2 days) → Complete audit trail
7. Phase 7: Integration (1 day)
8. Phase 8: Documentation (2 days)
9. Phase 9: Polish (1-2 days)

**Total Effort**: ~14-18 days for 1 developer; ~7-10 days with parallel team

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (3 days)
2. Once Foundational done:
   - Developer A: US1 (Persistent Storage) + US2 (Recovery) = 3 days
   - Developer B: US3 (Automated Backups) = 2 days
   - Developer C: US4 (Write Governance) = 2 days
3. All integrate Phase 7 (1 day)
4. All collaborate Phase 8 & 9 (3 days)

**Parallel timeline**: ~10-12 days total

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Verify tests pass before completing tasks
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Follow Constitution Principle VI (Memory Durability) for all implementation decisions

---

## Task Count Summary

| Phase | Count | Parallelizable |
|-------|-------|-----------------|
| Phase 1: Setup | 10 | 8 |
| Phase 2: Foundational | 10 | 5 |
| Phase 3: US1 | 7 | 3 |
| Phase 4: US2 | 8 | 2 |
| Phase 5: US3 | 9 | 6 |
| Phase 6: US4 | 8 | 4 |
| Phase 7: Integration | 6 | 4 |
| Phase 8: Documentation | 6 | 3 |
| Phase 9: Polish | 10 | 7 |
| **TOTAL** | **74** | **42** |

**Coverage**: 4 user stories, each independently testable and deliverable

**MVP Path**: Phases 1-3 (27 tasks) deliver persistent storage with data surviving restarts
