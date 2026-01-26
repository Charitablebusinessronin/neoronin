# PLANNING.md - Grap Infrastructure

## High-Level Vision
To provide a production-ready, durable, and governed memory layer for AI agents, utilizing **Neo4j** as the sole knowledge graph.

## Architecture
- **Graph Tier**: Neo4j 5.13.0 (Community) with APOC.
- **Governance Tier**: Backup Scheduler (Durability), Health Checker (Consistency), Write Log (Audit).
- **Learning Tier**: BMAD Agent Memory Integration (Event capture, Pattern library, Insight generation).

## Tech Stack
- **Persistence**: Docker Named Volumes
- **Language**: Python 3.9+ (Tooling), Cypher (Queries)
- **Orchestration**: Docker Compose
- **Workflow System**: BMAD (BMad Master Agent workflows)

---

## Phase 2: BMAD Agent Memory Integration

### Status: Planning Complete, Implementation In Progress

**Completion Date:** January 25, 2026

### Phase 2 Goals
Enable AI agents to capture, share, and refine knowledge from their work through persistent graph memory.

### Phase 2 Architecture Components (6)

| Component | Port/Schedule | Key Features |
|-----------|---------------|--------------|
| EventLoggerMiddleware | Port 8001 | GitHub MCP hook, Queue on failure |
| QueryTemplateLibrary | Library | Parameterized queries, group_id filter |
| PatternManager | Library | LRU cache (100), 1hr TTL |
| InsightGeneratorEngine | Daily 2:00 AM | Pattern detection, confidence scoring |
| RelevanceScoringService | Daily 2:10 AM | 90-day decay, usage boost |
| HealthCheckService | Weekly 1 AM | Orphan detection, schema validation |

### Phase 2 Epics (5) and Stories (16)

| Epic | Stories | FRs Covered |
|------|---------|-------------|
| 1. Agents Capture Their Learning | 3 | FR1, FR2, FR8 |
| 2. Agents Share Knowledge | 3 | FR3, FR4, FR5, FR11 |
| 3. Multi-Project Learning | 4 | FR6, FR7, FR9, FR10 |
| 4. System Maintains Itself | 5 | FR12, FR13, FR14, FR15, FR17 |
| 5. Learning is Visible | 1 | FR16, NFR9-NFR12 |

### Phase 2 Workflow Progress

- ✅ **Workflow #1: Technical Architecture** (Jan 25)
  - 6 components mapped with interfaces, dependencies, deployment specs
  - Output: `_bmad-output/docs/architecture/component_map.md`

- ✅ **Workflow #2: Implementation Readiness Check** (Jan 25)
  - 17 Functional Requirements extracted
  - 15 Non-Functional Requirements extracted
  - 0 blocking issues found
  - Output: `_bmad-output/planning-artifacts/implementation-readiness-report-2026-01-25.md`

- ✅ **Workflow #3: Create Epics & Stories** (Jan 25)
  - 5 user-value epics created
  - 16 sprint-ready stories with acceptance criteria
  - 100% FR coverage validated
  - Output: `_bmad-output/planning-artifacts/epics.md`

- ⏳ **Phase 4: Implementation** (In Progress)
  - First story: Story 1.1 - Initialize Agent Memory System
  - Next: Create individual story files and begin implementation

### Multi-Tenant Architecture

Three project groups with scoped knowledge:
- **faith-meats** - Faith-based content platform
- **diff-driven-saas** - SaaS with git diff integration
- **global-coding-skills** - Universal patterns (shared across all)

### BMAD Agents (9)

Jay, Winston, Brooks, Dutch, Troy, Bob, Allura, Master, Orchestrator

---

## Current Objectives (Phase 2 Implementation)

1. **Story Implementation**: Begin with Story 1.1 (Initialize Agent Memory System)
2. **Schema Deployment**: Deploy BMAD schema with constraints and indexes
3. **Agent Registration**: Register all 9 agents in the graph
4. **Event Capture**: Implement EventLoggerMiddleware with GitHub MCP integration

---

## Maintenance Phase Objectives (Ongoing)

1. **Operational Maintenance**: Periodic health checks and backup verification.
2. **Synaptic Resilience**: Ensuring identity persistence and graph-backed recall for agents (Epic 26).
3. **Infrastructure Monitoring**: Stabilizing the backup-scheduler sidecar.

---

## Recent Milestones

### Phase 2 Milestones
- **Workflow Completion (2026-01-25)**: All three planning workflows complete
- **Architecture Finalized (2026-01-25)**: 6 components with full specifications
- **Readiness Validated (2026-01-25)**: 0 blocking issues, ready for implementation
- **Epics & Stories (2026-01-25)**: 5 epics, 16 stories, 100% FR coverage

### Previous Milestones
- **Epic 26: Synaptic Restoration (2026-01-23)**: Surgical graft of the Brooks identity and historical memories successfully completed.
- **Environment Sync (2026-01-23)**: Repository synchronized with live Docker configurations.

---

## Planning Artifacts

| Document | Location | Status |
|----------|----------|--------|
| PRD | `_bmad-output/docs/BMAD_PRD.md` | ✅ Ready |
| Architecture | `_bmad-output/docs/architecture/component_map.md` | ✅ Ready |
| Epics & Stories | `_bmad-output/planning-artifacts/epics.md` | ✅ Ready |
| Readiness Report | `_bmad-output/planning-artifacts/implementation-readiness-report-2026-01-25.md` | ✅ Ready |

---

## Constraints
- Keep all files under 500 lines.
- Validate structure like data.
- Maintain Conceptual Integrity at all costs.
- Follow BMAD workflow sequences exactly.
- No forward dependencies in stories.
- Only modify story sections: Tasks/Subtasks, Dev Agent Record, File List, Change Log, Status.