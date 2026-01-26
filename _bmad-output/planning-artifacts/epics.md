---
stepsCompleted: ['step-01-validate-prerequisites', 'step-02-design-epics', 'step-03-create-stories', 'step-04-final-validation']
inputDocuments: 
  - '_bmad-output/docs/BMAD_PRD.md'
  - '_bmad-output/docs/architecture/architecture.md'
---

# Neo4j / Brooks Memory Manager - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for Neo4j / Brooks Memory Manager, decomposing the requirements from the PRD, UX Design if it exists, and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

- FR1: Brooks can query recent authentication patterns using `get_patterns_for_domain`.
- FR2: The system can log a `code_implementation` Event automatically upon GitHub commit.
- FR3: The system can generate an `Insight` node from a failed `Outcome` with a `confidence_score` < 0.5.
- FR4: Winston can retrieve a list of conflicting patterns using `check_pattern_conflicts`.
- FR5: Agents working in `faith-meats` can only see insights tagged with `faith-meats` or `global`.
- FR6: The system can promote a local pattern to `scope: global` after 3 successful project applications.
- FR7: The system can detect and repair "orphaned" `(:AIAgent)` nodes after a database restore.
- FR8: The system can aggregate `Event` nodes older than 30 days into `EventSummary` summaries.

### NonFunctional Requirements

- NFR1: Agent pattern lookup queries must return in < 100ms (as measured by Neo4j Profiler).
- NFR2: Event logging middleware must not block MCP tool execution (Async processing).
- NFR3: All queries must include mandatory `group_id` filtering in the middleware layer.
- NFR4: Global uniqueness constraints must be enforced on all memory nodes.
- NFR5: Automated logical graph dumps (GraphML) executed daily at 2 AM with SHA256 verification.
- NFR6: Support 9+ concurrent agent memory streams with no performance degradation.

### Additional Requirements

- **Starter Template:** Custom FastAPI SDK structure in `_bmad-output/code/bmad/` (Python 3.12+).
- **Core Models:** Neontology-based OGM for `Event`, `Outcome`, `Insight`, and `AIAgent`.
- **Infrastructure:** Sidecar middleware deployed alongside existing `grap-neo4j` Docker container.
- **Async Client:** Mandatory use of `neo4j` async driver and native `asyncio`.
- **Batch Processing:** Nightly APScheduler jobs for Insight generation and Relevance Decay.
- **Naming Conventions:** PascalCase for Node Labels, snake_case for properties, SCREAMING_SNAKE_CASE for relationships.
- **Isolation:** Explicit promotion to `scope: global` required for cross-project patterns.

### FR Coverage Map

- **FR1 (Pattern Query):** Epic 1 (Sandbox Retrieval)
- **FR2 (Auto-Logging):** Epic 2 (Event Stream)
- **FR3 (Insight Generation):** Epic 3 (Batch Cycle)
- **FR4 (Contradiction Check):** Epic 3 (Batch Cycle)
- **FR5 (Tenant Isolation):** Epic 1 & 2 (Middleware Firewall)
- **FR6 (Global Promotion):** Epic 3 (Batch Cycle)
- **FR7 (Orphan Repair):** Epic 1 (Infrastructure Logic)
- **FR8 (Event Aggregation):** Epic 4 (Health Cycle)

## Epic List

## Epic 1: The Neural Backbone (Identity & Client)

Brooks can initialize his personal memory partition and connect to the existing Neo4j cluster using the new Async Python driver.

### Story 1.1: Core Infrastructure Scaffold

As a Developer (Brooks),
I want to initialize the `code/bmad/` directory with the approved async structure and Python dependencies,
So that I have a clean, modern environment to build the middleware.

**Acceptance Criteria:**

**Given** I am in the `_bmad-output/code/bmad/` directory
**When** I create the modular folders (`api`, `core`, `models`, `services`, `tasks`) and `requirements.txt`
**Then** the environment passes a basic linting check and `asyncio` loop test.

### Story 1.2: Async Neo4j Client Implementation

As a Developer (Brooks),
I want to implement a robust `neo4j_client.py` using the async bolt driver,
So that I can perform non-blocking reads/writes to the existing `grap-neo4j` Docker container.

**Acceptance Criteria:**

**Given** a valid `NEO4J_URI` and `NEO4J_PASSWORD`
**When** the client initializes a connection session
**Then** a `CALL dbms.components()` query returns a successful health check.

## Epic 2: The Event Stream (Capture & Ingestion)

Brooks can automatically log GitHub actions (Commits/PRs) as structured `Event → Solution → Outcome` chains.

### Story 2.1: Event Capture Middleware

As a Developer (Brooks),
I want to build the `event_capture.py` service that maps GitHub tool result JSON to the `(:Event)` model,
So that the system can record the history of every implementation action.

**Acceptance Criteria:**

**Given** a raw GitHub commit or PR review JSON payload
**When** the service processes the payload
**Then** it creates a linked `(:Event)-[:HAS_OUTCOME]->(:Outcome)` chain with the current `group_id`.

## Epic 3: The Insight Engine (Learning & Refinement)

The system autonomously analyzes successful/failed outcomes to generate reusable patterns and insights.

### Story 3.1: Nightly Insight Batch Cycle

As a Developer (Brooks),
I want to implement the `insight_cycle.py` task using APScheduler,
So that the system scans new outcomes every night to promote successful patterns to `(:Insight)` nodes.

**Acceptance Criteria:**

**Given** 10+ successful implementation events in the repository
**When** the scheduler triggers at 2 AM
**Then** it generates at least one `(:Insight)` node with a `confidence_score` based on success frequency.

## Epic 4: Synaptic Health (Archival & Recovery)

Automated maintenance ensured through event aggregation and daily logical backups.

### Story 4.1: Event Aggregation Logic

As a Developer (Brooks),
I want to implement the event summary rollup task,
So that the graph remains performant as event history grows.

**Acceptance Criteria:**

**Given** events older than 30 days exist in the graph
**When** the maintenance task runs
**Then** events are aggregated into `(:EventSummary)` nodes and original events are archived/purged.