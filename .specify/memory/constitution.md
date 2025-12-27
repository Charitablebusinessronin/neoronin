<!--
SYNC IMPACT REPORT - Constitution v1.1.0
==========================================
Version: 1.0.0 → 1.1.0 (MINOR: Added Principle VI - Memory Durability)
Ratification: 2025-12-27
Last Amendment: 2025-12-27

Principles:
- I. Graph-First: All knowledge as structured relationships
- II. MCP Interface Contract: Controlled external communication
- III. Consistent Recall: Query-driven consistency over hallucination
- IV. Atomic Memory Updates: Graphiti-managed versioning
- V. Containerized Deployment: Docker-based reproducibility
- VI. Memory Durability (NEW): Durable backups, recovery, write governance

Rationale for v1.1.0:
Principle VI (Memory Durability) is a new principle that formalizes infrastructure
durability requirements discovered during feature planning. It clarifies that durability
is non-optional and part of the foundation, not a "nice-to-have" that can be added later.
This aligns with the Neo4j durability feature spec (001-neo4j-durability).

Templates Already Updated:
✅ plan-template.md: Constitution Check reference (line 30-34)
✅ spec-template.md: Requirements framework
✅ tasks-template.md: Task organization for graph-based development

Sections Present:
✅ Governance: Amendment procedures, versioning policy, compliance
✅ Development Workflow: Testing discipline, code review gates, complexity justification

Runtime Documentation:
⚠ README.md (does not exist yet - referenced in Governance section)
⚠ /docs/architecture/ (does not exist yet - referenced for detailed guidance)
-->

# Grap Constitution

## Core Principles

### I. Graph-First

Knowledge lives as structured relationships in Neo4j, not text blobs or unstructured data. Every entity, relationship, and fact must be explicitly modeled as a graph node or edge. This enables:

- **Precise Queries**: Ask "what do we know about X" and get consistent, traceable answers instead of hallucinations
- **Relationship Integrity**: Dependencies, causality, and connections are first-class—not inferred from text
- **Temporal Consistency**: Historical versions and updates are tracked as graph mutations, not document revisions
- **Auditability**: Every piece of knowledge has a source, timestamp, and lineage

**Non-negotiable**: All persistent data MUST have a corresponding graph schema. Text-only storage is only acceptable for temporary, non-recalled data.

### II. MCP Interface Contract

All external communication with AI services and clients flows through Model Context Protocol (MCP). The MCP boundary is the contract—anything outside MCP is internal implementation detail.

- **Explicit Boundaries**: MCP defines what information enters/leaves the system; no direct database access from outside
- **Versioning**: MCP schema changes are breaking changes; old API versions must coexist or migration is documented
- **Format Consistency**: JSON in, JSON out (or negotiated format); text protocols only for debugging/human interfaces
- **Resource Limits**: MCP enforces rate limiting, pagination, and query complexity constraints

**Non-negotiable**: Every AI query MUST go through MCP. Direct Neo4j/Graphiti access bypasses governance.

### III. Consistent Recall (Query-Over-Hallucination)

The system MUST prioritize querying known facts over generating plausible guesses. When answering "do we know about X", the answer is either "yes (here's the graph path)" or "no (this is not in memory)", never "maybe" or "guess".

- **Query-First Responses**: Always try to answer from the graph before synthesizing
- **Traceability**: Every recalled fact includes its source node(s) and relationship chain
- **Confidence Levels**: Distinguish between directly stored facts (high confidence) and derived inferences (lower confidence, must be validated before persistence)
- **Graceful Degradation**: If memory is incomplete, return partial results with gaps explicitly marked, not inferences

**Non-negotiable**: Hallucinations MUST NOT be persisted to the graph without explicit user approval.

### IV. Atomic Memory Updates

Graphiti manages entity and relationship versioning. Memory mutations are atomic—either fully applied or fully rolled back. Breaking changes (schema modifications, entity merges, relationship redefinition) require a documented migration plan.

- **Versioning**: Every entity has a version; every update is a new version, old ones retained for audit
- **Atomic Transactions**: Multi-step memory updates MUST succeed or fail as one unit, not partially
- **Migration Protocol**: Schema or entity structure changes MUST be announced, timed, and migrated (not silent upgrades)
- **Conflict Resolution**: Concurrent updates use last-write-wins with conflict markers; manual resolution path documented

**Non-negotiable**: No silent data mutations. Every change either succeeds atomically or fails cleanly.

### V. Containerized Deployment

Docker is the deployment unit. Every component (Neo4j, Graphiti, AI service, MCP gateway) runs in a container. This ensures reproducibility, portability, and isolation.

- **Reproducibility**: Same Dockerfile + compose config = same behavior on laptop, CI, and production
- **Isolation**: Service failures do not cascade; network boundaries are explicit (docker-compose port mapping)
- **Configuration**: All environment-specific values (Neo4j password, API keys, service URLs) come from `.env` or secrets, not hardcoded in containers
- **Health Checks**: Each container has a health check; orchestration responds to failures (restart, remove, scale)

**Non-negotiable**: Features requiring new infrastructure (databases, services, message queues) MUST be containerized with working docker-compose setup before merge.

### VI. Memory Durability

All graph data is persisted durably and recoverably. Durability is not optional—it's the foundation of trust in a memory-backed system.

- **Named Volumes**: Neo4j data lives in Docker-managed named volumes (not bind mounts or ephemeral storage). Volume names are stable and documented.
- **Automated Backups**: Point-in-time backups are created automatically on a documented schedule (e.g., daily). Backup creation must not block writes.
- **Retention Policy**: Backups are retained per a documented policy (e.g., keep 7 daily + 4 weekly). Expired backups are automatically cleaned up.
- **Recovery Procedure**: A tested, documented procedure exists to restore from any backup without data loss or manual graph surgery. Recovery is testable on a separate instance before promoting to production.
- **Write Path Governance**: All mutations to the graph flow through documented paths (MCP → Graphiti → Neo4j). Direct writes are logged or rejected. Write audit trail enables replaying sequence of operations.
- **Health Checks**: Regular validation detects inconsistencies (orphaned relationships, duplicates, schema violations) before they cascade. Health checks are fast and have minimal false-positive rate.
- **Graceful Degradation**: If backup fails, MCP continues operating. If recovery is in progress, requests are queued or rejected with clear messaging (not silently failing).

**Non-negotiable**: Memory durability MUST be configured before any graph mutation feature merges. Backup automation and recovery testing are mandatory. No "we'll add durability later"—it's part of the foundation.

## Development Workflow

### Testing Discipline

- **Contract Tests**: MCP endpoint behavior is tested before implementation (test the interface contract)
- **Integration Tests**: Entity mutations and graph queries are validated in isolation (Neo4j + Graphiti in test container)
- **System Tests**: End-to-end flows through MCP gateway with containerized services
- **Red-Green-Refactor**: Tests MUST fail before code; verify failure is real (not a broken test)

### Code Review Gates

All PRs must verify:
1. **Graph Schema**: If entity/relationship changes, schema update is included and migration plan is documented
2. **MCP Compliance**: No direct database access outside MCP boundary; API versioning correct
3. **Atomicity**: Multi-step operations are wrapped in transactions or marked as eventually-consistent with recovery steps
4. **Docker Setup**: New services have working Dockerfile; compose config tested locally
5. **No Hallucinations**: If feature uses inference, confidence levels are explicit and inferences are not persisted without approval

### Complexity Justification

If a PR violates a principle, the complexity trade-off MUST be documented:

| Violation | Why Needed | Simpler Alternative Rejected |
|-----------|-----------|------------------------------|
| Example: Direct Neo4j query bypassing MCP | Bootstrapping system with existing data | Import via MCP migration endpoint takes 2x longer but is the correct path after system stabilizes |

## Governance

### Amendment Procedure

1. **Proposal**: File an issue with proposed change and rationale
2. **Discussion**: Core team (at least 2 members) reviews; changes to principles require consensus
3. **Migration Plan**: If change affects entities, schema, or MCP contract, document migration for existing data
4. **Versioning**: Bump constitution version (MAJOR for breaking principle changes, MINOR for new guidance, PATCH for clarifications)
5. **Announcement**: Update README and migration guide; old behavior is supported for one release cycle before removal

### Versioning Policy

- **MAJOR**: Principle removed/redefined, MCP breaking change, schema incompatibility
- **MINOR**: New principle added, new MCP endpoint, new schema field (backward-compatible)
- **PATCH**: Clarifications, wording, non-semantic refinements, bug fixes

### Compliance Review

- Every feature spec MUST reference which principles it adheres to
- Every PR MUST pass "Constitution Check" gate (plan-template.md line 30-34)
- Monthly: Review open issues for principle violations; escalate if pattern emerges

### Guidance & Runtime Documentation

See `.specify/templates/` for development templates:
- `spec-template.md`: Feature specification structure with principle checkpoints
- `plan-template.md`: Implementation planning with Constitution Check gate
- `tasks-template.md`: Task organization for graph-based development (entities, relationships, queries)

For runtime guidance, see the project README (TBD) and architecture documentation in `/docs/` (TBD).

## Version History

**Version**: 1.1.0 | **Ratified**: 2025-12-27 | **Last Amended**: 2025-12-27
