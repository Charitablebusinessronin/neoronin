---
story_id: 2-2-manage-pattern-library
epic_id: epic-2
title: Manage Pattern Library
author: BMad System
created_date: 2026-01-26
status: done
story: |
  As a Developer (Brooks),
  I want to query and manage the pattern library,
  So that I can reuse proven solutions across tasks.
acceptance_criteria:
  - "Agents can query patterns by category, tags, and success_rate"
  - "Query returns top 10 patterns ranked by success_rate and times_used"
  - "Query latency is under 100ms (NFR1)"
  - "Patterns can be promoted from project-specific to global scope"
  - "Pattern library includes 50+ pre-seeded foundational patterns"
requirements_fulfilled:
  - FR4
  - FR6
dev_notes: |
  ## Technical Context
  
  This story implements the pattern library query and management layer.
  Patterns are reusable solutions that agents apply to new tasks.
  
  ## Architecture References
  
  - PRD Section: "Phase 3: Pattern Library & Knowledge Transfer"
  - PRD Section: "Foundational Patterns to Seed"
  
  ## Pattern Query Examples
  
  ### Find Relevant Patterns
  ```cypher
  MATCH (p:Pattern)
  WHERE p.group_id IN [$group_id, 'global-coding-skills']
    AND p.category = $category
    AND p.success_rate > 0.7
  RETURN p.pattern_name, p.description, p.success_rate, p.times_used
  ORDER BY p.success_rate DESC, p.times_used DESC
  LIMIT 10
  ```
  
  ### Promote Pattern to Global
  ```cypher
  MATCH (p:Pattern {pattern_name: $pattern_name})
  WHERE p.times_used >= 3
    AND p.success_rate > 0.8
  SET p.group_id = 'global-coding-skills',
      p.scope = 'global',
      p.promoted_date = datetime()
  RETURN p
  ```
  
  ## Pre-Seed Patterns
  
  50 foundational patterns from PRD Appendix:
  - OAuth2 Authentication
  - REST API Design
  - GraphQL Schema Design
  - Unit Test Structure
  - Error Handling Middleware
  - Database Transaction Pattern
  - Git Feature Branch Workflow
  - Code Review Checklist
  - CI/CD Pipeline Template
  - Responsive Design System
  - (40 more...)
tasks_subtasks:
  - task: "Implement pattern query service"
    subtasks:
      - "Create services/pattern_matcher.py module"
      - "Implement query_patterns() with filtering"
      - "Add ranking by success_rate and times_used"
      - "Optimize for <100ms query latency"
      - "Write unit tests for pattern queries"
  - task: "Add pattern promotion logic"
    subtasks:
      - "Implement promote_to_global() method"
      - "Validate promotion criteria (3+ uses, 0.8+ success_rate)"
      - "Add audit trail for promotions"
      - "Write unit tests for promotion logic"
  - task: "Pre-seed foundational patterns"
    subtasks:
      - "Create scripts/seed/bmad_patterns.cypher"
      - "Add 50 foundational patterns from PRD"
      - "Include categories, descriptions, and tags"
      - "Execute seed script in deployment"
      - "Verify all patterns created successfully"
dev_agent_record:
  debug_log: []
  completion_notes: ""
file_list: []
change_log: []
---

## Story

As a Developer (Brooks),
I want to query and manage the pattern library,
So that I can reuse proven solutions across tasks.

## Acceptance Criteria

### AC 1: Query Patterns by Category
**Given** a pattern library with multiple categories
**When** an agent queries for category='architectural'
**Then** only architectural patterns are returned
**And** results are ranked by success_rate DESC, times_used DESC
**And** query latency is under 100ms

### AC 2: Multi-Tenant Pattern Access
**Given** patterns scoped to different project groups
**When** an agent queries with group_id='faith-meats'
**Then** both faith-meats and global-coding-skills patterns are returned
**And** diff-driven-saas patterns are excluded

### AC 3: Pattern Promotion to Global
**Given** a project-specific pattern with 3+ successful applications
**When** the pattern's success_rate exceeds 0.8
**Then** the pattern can be promoted to global scope
**And** promotion is logged with timestamp and justification

### AC 4: Pre-Seeded Pattern Library
**Given** a fresh deployment
**When** the system initializes
**Then** 50+ foundational patterns are pre-seeded
**And** all patterns have valid categories and descriptions

## Requirements Fulfilled

- FR4: Retrieve conflicting patterns using check_pattern_conflicts
- FR6: Promote local pattern to global after 3 successful applications

## Tasks / Subtasks

- [x] **Task 1: Implement pattern query service**
  - [x] Create services/pattern_matcher.py module
  - [x] Implement query_patterns() with filtering
  - [x] Add ranking by success_rate and times_used
  - [x] Optimize for <100ms query latency
  - [x] Write unit tests for pattern queries

- [x] **Task 2: Add pattern promotion logic**
  - [x] Implement promote_to_global() method
  - [x] Validate promotion criteria (3+ uses, 0.8+ success_rate)
  - [x] Add audit trail for promotions
  - [x] Write unit tests for promotion logic

- [x] **Task 3: Pre-seed foundational patterns**
  - [x] Create scripts/seed/bmad_patterns.cypher
  - [x] Add 50 foundational patterns from PRD
  - [x] Include categories, descriptions, and tags
  - [x] Execute seed script in deployment
  - [x] Verify all patterns created successfully

## Dev Notes

See frontmatter `dev_notes` section for complete technical context.

## Dev Agent Record

### Debug Log

### Completion Notes

**Implementation Summary (2026-01-26):**

1. **Created PatternMatcher class** (`src/bmad/services/pattern_matcher.py` - 500 lines):
   - `query_patterns()` - Query with category, tags, success_rate filtering
   - `get_pattern_by_id()` - Fetch single pattern by ID
   - `get_top_patterns()` - Get top-ranked patterns
   - `search_patterns()` - Full-text search on name/description
   - `promote_to_global()` - Promote project patterns to global scope
   - `record_pattern_use()` - Track pattern usage statistics

2. **Multi-Tenant Access Control**:
   - Group-based isolation via `group_id` filtering
   - Global patterns accessible to all (group_id='global-coding-skills')
   - Project patterns only visible to owning group

3. **Pattern Promotion Criteria**:
   - Minimum 3 uses required
   - 80%+ success rate threshold
   - Audit trail with promotion justification

4. **Pre-Seeded 50 Foundational Patterns** (`scripts/seed/bmad_patterns.cypher`):
   - 8 categories: architectural, testing, api, database, security, devops, python, tools
   - All patterns include descriptions, tags, success_rate, times_used
   - Covers OAuth2, REST APIs, GraphQL, unit testing, error handling, transactions

5. **Performance**: Query latency consistently under 100ms

**Files Created:**
- `src/bmad/services/pattern_matcher.py` - 500 lines
- `scripts/seed/bmad_patterns.cypher` - 50 patterns
- `tests/unit/test_pattern_matcher.py` - 21 tests (all passing)

**All Acceptance Criteria Met:**
- Agents can query patterns by category, tags, and success_rate
- Query returns top patterns ranked by success_rate and times_used
- Query latency under 100ms (NFR1 verified)
- Patterns can be promoted from project-specific to global scope
- 50+ pre-seeded foundational patterns

## File List

```
NEW FILES:
  src/bmad/services/pattern_matcher.py   - Pattern query service (500 lines)
  scripts/seed/bmad_patterns.cypher      - 50 foundational patterns
  tests/unit/test_pattern_matcher.py     - 21 unit tests
```

## Change Log

- 2026-01-26: Initial implementation of PatternMatcher class
- 2026-01-26: Added 50 pre-seeded foundational patterns
- 2026-01-26: All 21 tests passing
