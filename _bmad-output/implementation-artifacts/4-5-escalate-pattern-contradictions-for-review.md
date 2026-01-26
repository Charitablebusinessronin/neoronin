---
story_id: 4-5-escalate-pattern-contradictions-for-review
epic_id: epic-4
title: Escalate Pattern Contradictions for Review
author: BMad System
created_date: 2026-01-26
status: done
story: |
  As a System Maintainer,
  I want conflicting patterns escalated for human review,
  So that contradictions don't confuse agents.
acceptance_criteria:
  - "Contradicting patterns with confidence delta > 0.3 are detected"
  - "Contradictions are flagged with Alert nodes requiring human review"
  - "Alert includes both pattern IDs, confidence scores, and conflict reason"
  - "Contradiction detection runs daily via scheduled task"
  - "Alerts are exposed via API endpoint for review"
requirements_fulfilled:
  - FR4
dev_notes: |
  ## Technical Context

  Pattern contradiction detection prevents conflicting guidance to agents.

  ## Architecture References

  - PRD Section: "Risk Assessment" - Insight Contradictions mitigation
  - PRD Section: "Open Questions" - Human-in-the-Loop Review Triggers

  ## Contradiction Detection Query

  ```cypher
  MATCH (i1:Insight), (i2:Insight)
  WHERE i1.applies_to = i2.applies_to
    AND i1.rule CONTAINS $keyword1
    AND i2.rule CONTAINS $keyword2
    AND abs(i1.confidence_score - i2.confidence_score) > 0.3
  CREATE (alert:Alert {
    type: 'contradiction',
    insights: [id(i1), id(i2)],
    requires_human_review: true,
    created_date: datetime()
  })
  RETURN alert
  ```
tasks_subtasks:
  - task: "Implement contradiction detection"
    subtasks:
      - "Create services/contradiction_detector.py module"
      - "Implement detect_pattern_conflicts() method"
      - "Check confidence delta > 0.3"
      - "Write unit tests for detection"
  - task: "Add alert creation logic"
    subtasks:
      - "Create Alert nodes for contradictions"
      - "Include pattern IDs and conflict reason"
      - "Set requires_human_review flag"
      - "Write unit tests for alerts"
  - task: "Create daily detection task and API"
    subtasks:
      - "Add APScheduler task for daily detection"
      - "Schedule for 2:15 AM"
      - "Create GET /api/alerts endpoint"
      - "Add alert resolution workflow"
dev_agent_record:
  debug_log:
    - "Fixed resolve_alert() to use bool(results) for proper boolean return"
    - "Fixed Alert dataclass field name from 'insights' to 'insight_ids'"
  completion_notes: "Story 4-5 completed with 17/19 tests passing (2 integration tests skipped). Key features:
    1. ContradictionDetectorService: Detects conflicting patterns with confidence delta > 0.3
    2. Alert creation: Creates Alert nodes with insight IDs, confidence scores, conflict reason
    3. ContradictionDetectionCycle: Daily scheduled task (2:15 AM) for automatic detection
    4. Alerts API: GET /api/alerts, POST /api/alerts/{id}/resolve, POST /api/alerts/detect
    5. Alert resolution workflow: Mark alerts as resolved with notes"
file_list:
  - src/bmad/services/contradiction_detector.py
  - src/bmad/tasks/contradiction_detection_cycle.py
  - src/bmad/api/alerts.py
  - tests/unit/test_contradiction_detector.py
change_log: []
---

## Story

As a System Maintainer,
I want conflicting patterns escalated for human review,
So that contradictions don't confuse agents.

## Acceptance Criteria

### AC 1: Contradiction Detection
**Given** two insights with conflicting rules
**When** the daily detection task runs
**Then** contradictions with confidence delta > 0.3 are detected
**And** Alert nodes are created

### AC 2: Alert Details
**Given** a contradiction is detected
**When** the alert is created
**Then** it includes both pattern IDs, confidence scores, and conflict reason
**And** requires_human_review flag is set to true

### AC 3: Alert API
**Given** alerts exist in the graph
**When** GET /api/alerts is called
**Then** all pending alerts are returned
**And** alerts can be marked as resolved

## Requirements Fulfilled

- FR4: Retrieve conflicting patterns using check_pattern_conflicts

## Tasks / Subtasks

- [x] **Task 1: Implement contradiction detection**
  - [x] Create services/contradiction_detector.py module
  - [x] Implement detect_pattern_conflicts() method
  - [x] Check confidence delta > 0.3
  - [x] Write unit tests for detection

- [x] **Task 2: Add alert creation logic**
  - [x] Create Alert nodes for contradictions
  - [x] Include pattern IDs and conflict reason
  - [x] Set requires_human_review flag
  - [x] Write unit tests for alerts

- [x] **Task 3: Create daily detection task and API**
  - [x] Add APScheduler task for daily detection
  - [x] Schedule for 2:15 AM
  - [x] Create GET /api/alerts endpoint
  - [x] Add alert resolution workflow

## Dev Notes

See frontmatter `dev_notes` section for complete technical context.

## Dev Agent Record

### Debug Log

- Fixed `resolve_alert()` to use `bool(results)` for proper boolean return on empty results
- Fixed `Alert` dataclass field name from `insights` to `insight_ids` to match actual implementation

### Completion Notes

Story 4-5 completed with 17/19 tests passing (2 integration tests skipped due to Neo4j availability). Key features:

1. **ContradictionDetectorService**: Detects conflicting patterns with confidence delta > 0.3
2. **Alert creation**: Creates Alert nodes with insight IDs, confidence scores, conflict reason
3. **ContradictionDetectionCycle**: Daily scheduled task (2:15 AM) for automatic detection
4. **Alerts API**: REST endpoints for getting/resolving alerts and triggering detection
5. **Alert resolution workflow**: Mark alerts as resolved with notes

Files created:
- `src/bmad/services/contradiction_detector.py` - Detection service (350+ lines)
- `src/bmad/tasks/contradiction_detection_cycle.py` - Daily scheduled task (200+ lines)
- `src/bmad/api/alerts.py` - REST API endpoints (250+ lines)
- `tests/unit/test_contradiction_detector.py` - 19 unit tests (17 passing)

## File List

```
src/bmad/services/contradiction_detector.py
src/bmad/tasks/contradiction_detection_cycle.py
src/bmad/api/alerts.py
tests/unit/test_contradiction_detector.py
```

## Change Log
