# Legacy Mapping Report - Neo4j Driver to MCP Migration

**Generated:** 2026-01-26
**Project:** Neo4j Agent Memory System
**Migration Target:** Neo4j Memory MCP
**Orchestrator:** BMad Master

---

## Executive Summary

**Total Files Analyzed:** 64 Python files
**Total Neo4j Driver References:** 120+ occurrences
**Primary Entry Point:** `src/bmad/core/neo4j_client.py`

---

## 1. Core Infrastructure Layer

### 1.1 Neo4j Client (`src/bmad/core/neo4j_client.py`)

| Pattern | Occurrences | Business Context | MCP Equivalent |
|---------|-------------|------------------|----------------|
| `execute_query` | 2 | Async query execution wrapper | `memory_search` / `memory_retrieve` |
| `session.run` | 3 | Direct Cypher execution | `memory_search` with query param |
| `GraphDatabase` | 2 | Driver initialization | N/A (MCP handles connection) |
| `neo4j` import | 1 | Neo4j package dependency | MCP server handles |

**Impact:** **CRITICAL** - This is the central async client used by all services. Migration strategy:
1. Wrap MCP calls in async interface for backward compatibility
2. Deprecate direct `execute_query` method
3. Implement MCP adapter pattern

---

### 1.2 Schema Deployer (`src/schema/deployer.py`)

| Pattern | Occurrences | Business Context | MCP Equivalent |
|---------|-------------|------------------|----------------|
| `session.run` | 7 | Schema deployment (constraints, indexes) | Manual MCP setup required |
| `GraphDatabase` | 1 | Driver initialization | N/A |
| `neo4j` import | 1 | Neo4j package dependency | MCP server handles |

**Impact:** **HIGH** - Schema deployment tool. Migration:
1. MCP memory_manage for node creation
2. Schema constraints must be configured at MCP server level

---

## 2. Service Layer (Primary Consumers)

### 2.1 Brain Manager (`src/bmad/services/brain_manager.py`)

| Pattern | Occurrences | Business Context | MCP Equivalent |
|---------|-------------|------------------|----------------|
| `execute_query` | 6 | Brain scoping model queries | `memory_search` with scope filters |

**Queries:**
- `get_agent_brains` - Multi-scope brain retrieval
- `get_brain_by_name` - Single brain lookup
- `get_brains_by_scope` - Filtered brain list
- `get_all_brains` - Complete brain inventory
- `validate_agent_brain_connectivity` - Connectivity verification
- `count_brains` - Brain statistics

**Impact:** **HIGH** - Core brain scoping service. Migration:
- Use `memory_search` with memoryTypes filter
- Implement scope-aware search in application layer

---

### 2.2 Pattern Matcher (`src/bmad/services/pattern_matcher.py`)

| Pattern | Occurrences | Business Context | MCP Equivalent |
|---------|-------------|------------------|----------------|
| `execute_query` | 3 | Pattern matching queries | `memory_search` + semantic matching |

**Queries:**
- Pattern discovery and matching
- Relationship traversal
- Effectiveness tracking

**Impact:** **MEDIUM** - Pattern matching can leverage MCP's semantic search.

---

### 2.3 Insight Generator (`src/bmad/services/insight_generator.py`)

| Pattern | Occurrences | Business Context | MCP Equivalent |
|---------|-------------|------------------|----------------|
| `execute_query` | 2 | Insight extraction queries | `memory_search` with observation content |

**Impact:** **MEDIUM** - Insight generation benefits from MCP's graph context.

---

### 2.4 Additional Services (execute_query usage)

| Service | Occurrences | Purpose |
|---------|-------------|---------|
| `agent_queries.py` | Multiple | Agent metadata queries |
| `audit_logger.py` | Multiple | Audit trail operations |
| `contradiction_detector.py` | Multiple | Conflict detection |
| `event_aggregation.py` | Multiple | Event consolidation |
| `knowledge_transfer.py` | Multiple | Cross-agent knowledge sync |
| `metrics_exporter.py` | Multiple | Metrics queries |
| `notion_sync.py` | Multiple | Notion integration |
| `orphan_repair.py` | Multiple | Relationship cleanup |

---

## 3. Background Tasks Layer

| Task File | Purpose | Impact |
|-----------|---------|--------|
| `confidence_decay_cycle.py` | Temporal insight decay | MEDIUM |
| `contradiction_detection_cycle.py` | Conflict monitoring | MEDIUM |
| `event_aggregation_cycle.py` | Event consolidation | MEDIUM |
| `health_check_cycle.py` | System health | LOW |
| `insight_cycle.py` | Insight generation | MEDIUM |
| `knowledge_transfer_cycle.py` | Cross-agent sync | MEDIUM |
| `notion_sync_cycle.py` | Notion integration | LOW |
| `pattern_effectiveness_cycle.py` | Pattern tracking | MEDIUM |

---

## 4. Utility Scripts

| Script | Purpose | Impact |
|--------|---------|--------|
| `health/health-check.py` | Health verification | LOW |
| `notion/create_anchor_nodes.py` | Notion anchor creation | LOW |
| `backup/neo4j_backup.py` | Backup operations | MEDIUM |
| `backup/neo4j_restore.py` | Restore operations | MEDIUM |

---

## 5. Test Files

**Unit Tests:** 18 test files with Neo4j driver mocks
**Integration Tests:** 6 test files with actual Neo4j connections

**Impact:** **MEDIUM** - Tests will need MCP mocking strategies.

---

## 6. Migration Complexity Assessment

### Tier 1: Critical (Core Client Layer)
- `neo4j_client.py` - **Must migrate first**
- `schema/deployer.py` - **Manual MCP setup required**

### Tier 2: High (Business Logic Services)
- `brain_manager.py`
- `pattern_matcher.py`
- `insight_generator.py`

### Tier 3: Medium (Supporting Services)
- All other `src/bmad/services/*.py`
- Background tasks

### Tier 4: Low (Utilities & Tests)
- Scripts, backup utilities
- Test files (can be refactored after services)

---

## 7. Proposed Migration Order

1. **Phase 3.1:** Wrap MCP in async adapter (preserve `Neo4jAsyncClient` interface)
2. **Phase 3.2:** Migrate `brain_manager.py` (highest value)
3. **Phase 3.3:** Migrate Tier 2 services (pattern_matcher, insight_generator, etc.)
4. **Phase 3.4:** Migrate Tier 3 services
5. **Phase 3.5:** Update tests and utilities

---

## 8. MCP Tool Mapping Summary

| Legacy Pattern | MCP Tool | Notes |
|---------------|----------|-------|
| `SELECT/MATCH` | `memory_search` | Semantic search, threshold |
| `INSERT/CREATE` | `memory_manage` (create) | Memory type, observations |
| `UPDATE` | `memory_manage` (update) | Memory ID required |
| `DELETE` | `memory_manage` (delete) | Memory ID required |
| `GET BY ID` | `memory_retrieve` | Returns with graph context |
| `RELATIONSHIPS` | `relation_manage` | Connect memories |

---

## 9. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| MCP semantic search differs from exact Cypher | HIGH | Implement adapter with query preservation |
| MCP lacks schema constraints | MEDIUM | Add application-layer validation |
| Async interface compatibility | MEDIUM | Wrapper maintains async/await pattern |
| Test coverage regression | LOW | Incremental test updates |

---

**Phase 0 Complete.** Ready for Phase 1: Integration Planning (Architect).