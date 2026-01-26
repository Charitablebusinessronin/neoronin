---
story_id: 4-4-detect-and-resolve-orphaned-relationships
epic_id: epic-4
title: Detect and Resolve Orphaned Relationships
author: BMad System
created_date: 2026-01-26
status: done
story: |
  As a System Maintainer,
  I want orphaned relationships detected and repaired,
  So that graph integrity is maintained.
acceptance_criteria:
  - "Health check detects orphaned AIAgent nodes without brain relationships"
  - "Orphaned relationships are automatically repaired"
  - "Health check runs weekly via scheduled task"
  - "Repair metrics are logged (orphans found, relationships created)"
  - "Health check completes in under 5 seconds"
requirements_fulfilled:
  - FR7
  - NFR5
dev_notes: |
  ## Technical Context

  Orphan detection and repair ensures graph integrity after backups/restores.

  ## Architecture References

  - PRD Section: "Phase 1: Schema Deployment" - Health check extension
  - PRD Section: "Risk Assessment" - Orphan repair

  ## Orphan Detection Query

  ```cypher
  MATCH (agent:AIAgent)
  WHERE NOT exists((agent)-[:HAS_MEMORY_IN]->(:Brain))
  RETURN agent.name as orphaned_agent
  ```

  ## Repair Query

  ```cypher
  MATCH (agent:AIAgent)
  WHERE NOT exists((agent)-[:HAS_MEMORY_IN]->(:Brain))
  MATCH (brain:Brain {name: agent.name + ' Brain'})
  MERGE (agent)-[:HAS_MEMORY_IN]->(brain)
  RETURN agent.name, brain.name
  ```
tasks_subtasks:
  - task: "Implement orphan detection"
    subtasks:
      - "Create orphan_repair.py service module"
      - "Detect orphaned AIAgent nodes"
      - "Detect orphaned Brain nodes"
      - "Write unit tests for detection"
  - task: "Add automatic repair logic"
    subtasks:
      - "Implement repair_orphaned_relationships() method"
      - "Create missing HAS_MEMORY_IN relationships"
      - "Create missing Brain nodes when needed"
      - "Write unit tests for repair"
  - task: "Create weekly health check task"
    subtasks:
      - "Add health_check_cycle.py scheduled task"
      - "Schedule for Monday 1:00 AM"
      - "Log health check results"
      - "Add error handling and alerts"
dev_agent_record:
  debug_log:
    - "Fixed RepairResult.to_dict() - added method to dataclass"
    - "Removed duplicate to_dict() from OrphanRepairService class"
  completion_notes: "Story 4-4 completed with 16/18 tests passing (2 integration tests skipped). Key features:
    1. OrphanRepairService: Detects AIAgent nodes without HAS_MEMORY_IN relationships
    2. Auto-repair: Creates missing Brain nodes and establishes relationships
    3. HealthCheckCycle: Weekly scheduled task (Monday at 1 AM) with performance monitoring
    4. RepairResult.to_dict(): Added for serialization in health check cycle"
file_list:
  - src/bmad/services/orphan_repair.py
  - src/bmad/tasks/health_check_cycle.py
  - tests/unit/test_orphan_repair.py
change_log: []
---

## Story

As a System Maintainer,
I want orphaned relationships detected and repaired,
So that graph integrity is maintained.

## Acceptance Criteria

### AC 1: Orphan Detection
**Given** AIAgent nodes without brain relationships
**When** the weekly health check runs
**Then** orphaned agents are detected
**And** orphan count is logged

### AC 2: Automatic Repair
**Given** orphaned relationships detected
**When** the repair logic executes
**Then** missing HAS_MEMORY_IN relationships are created
**And** repair metrics are logged

### AC 3: Performance Target
**Given** the health check runs
**When** orphan detection and repair complete
**Then** total execution time is under 5 seconds

## Requirements Fulfilled

- FR7: Detect and repair orphaned AIAgent nodes
- NFR5: Automated graph maintenance

## Tasks / Subtasks

- [x] **Task 1: Implement orphan detection**
  - [x] Create orphan_repair.py service module
  - [x] Detect orphaned AIAgent nodes
  - [x] Detect orphaned Brain nodes
  - [x] Write unit tests for detection

- [x] **Task 2: Add automatic repair logic**
  - [x] Implement repair_orphaned_relationships() method
  - [x] Create missing HAS_MEMORY_IN relationships
  - [x] Create missing Brain nodes when needed
  - [x] Write unit tests for repair

- [x] **Task 3: Create weekly health check task**
  - [x] Add health_check_cycle.py scheduled task
  - [x] Schedule for Monday 1:00 AM
  - [x] Log health check results
  - [x] Add error handling and alerts

## Dev Notes

See frontmatter `dev_notes` section for complete technical context.

## Dev Agent Record

### Debug Log

- Fixed `RepairResult.to_dict()` - added method to dataclass for serialization
- Removed duplicate `to_dict()` method from `OrphanRepairService` class

### Completion Notes

Story 4-4 completed with 16/18 tests passing (2 integration tests skipped due to Neo4j availability). Key features:

1. **OrphanRepairService**: Detects AIAgent nodes without HAS_MEMORY_IN relationships and Brain nodes without group_id
2. **Auto-repair**: Creates missing Brain nodes and establishes HAS_MEMORY_IN relationships for orphaned agents
3. **HealthCheckCycle**: Weekly scheduled task (Monday at 1 AM) with performance monitoring (<5 second target)
4. **RepairResult.to_dict()**: Added for serialization in health check cycle return values

Files created:
- `src/bmad/services/orphan_repair.py` - Detection and repair service (260+ lines)
- `src/bmad/tasks/health_check_cycle.py` - Weekly scheduled task (200+ lines)
- `tests/unit/test_orphan_repair.py` - 18 unit tests (16 passing)

## File List

```
src/bmad/services/orphan_repair.py
src/bmad/tasks/health_check_cycle.py
tests/unit/test_orphan_repair.py
```

## Change Log
