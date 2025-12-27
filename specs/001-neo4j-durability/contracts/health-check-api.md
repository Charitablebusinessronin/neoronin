# Contract: Health Check Endpoint

**Feature**: 001-neo4j-durability
**Type**: HTTP REST API
**Purpose**: Validate Neo4j graph health without full consistency scan

## Endpoint

### GET /health/graph

Returns current health status of the Neo4j graph. Fast-fail if any check fails.

**Response Time Target**: <5 seconds for 1M node/relationship graphs

---

## Request

**Method**: `GET`
**Path**: `/health/graph`
**Headers**: None required
**Body**: None
**Query Parameters**:
- `detailed` (optional, boolean): If true, return detailed results of each check; if false, return summary only. Default: false.

---

## Response

### Success Response (200 OK)

```json
{
  "status": "healthy",
  "timestamp": "2025-12-27T15:30:00Z",
  "checks": {
    "connectivity": {
      "status": "pass",
      "message": "Neo4j is reachable and responding to queries"
    },
    "schema_consistency": {
      "status": "pass",
      "message": "All graph nodes and relationships conform to defined schema"
    },
    "orphan_detection": {
      "status": "pass",
      "message": "No orphaned relationships found"
    }
  },
  "graph_stats": {
    "node_count": 1500,
    "relationship_count": 3200,
    "last_write_timestamp": "2025-12-27T15:29:45Z"
  }
}
```

### Unhealthy Response (503 Service Unavailable)

When ANY check fails, return 503 immediately (don't wait for other checks).

```json
{
  "status": "unhealthy",
  "timestamp": "2025-12-27T15:30:00Z",
  "failed_check": "connectivity",
  "message": "Cannot reach Neo4j: Connection timeout after 5s",
  "checks": {
    "connectivity": {
      "status": "fail",
      "message": "Cannot reach Neo4j: Connection timeout after 5s"
    },
    "schema_consistency": {
      "status": "skipped",
      "message": "Skipped because connectivity check failed"
    },
    "orphan_detection": {
      "status": "skipped",
      "message": "Skipped because connectivity check failed"
    }
  }
}
```

### Recovery in Progress Response (503 Service Unavailable)

When database is being recovered from backup:

```json
{
  "status": "unavailable",
  "timestamp": "2025-12-27T15:30:00Z",
  "reason": "database_recovery_in_progress",
  "message": "Database is being recovered from backup. Please retry in approximately 5 minutes.",
  "recovery": {
    "backup_id": "neo4j-20251227-150000",
    "started_at": "2025-12-27T15:25:00Z",
    "progress_percent": 75,
    "estimated_completion": "2025-12-27T15:32:00Z"
  }
}
```

---

## Detailed Response (with ?detailed=true)

```json
{
  "status": "healthy",
  "timestamp": "2025-12-27T15:30:00Z",
  "checks": {
    "connectivity": {
      "status": "pass",
      "message": "Neo4j is reachable and responding to queries",
      "duration_ms": 45,
      "test_query": "RETURN 1"
    },
    "schema_consistency": {
      "status": "pass",
      "message": "All graph nodes and relationships conform to defined schema",
      "duration_ms": 250,
      "schema_version": "1.0.0",
      "defined_node_types": ["User", "Memory", "Entity", "AuditLogEntry", "BackupMetadata", "RecoveryState"],
      "defined_relationship_types": ["HAS", "RELATES_TO", "AFFECTED_ENTITY", "RESTORED_BY"]
    },
    "orphan_detection": {
      "status": "pass",
      "message": "No orphaned relationships found",
      "duration_ms": 3200,
      "orphaned_count": 0,
      "sample_checked": 100000
    }
  },
  "graph_stats": {
    "node_count": 1500,
    "relationship_count": 3200,
    "last_write_timestamp": "2025-12-27T15:29:45Z",
    "node_type_breakdown": {
      "User": 250,
      "Memory": 1000,
      "Entity": 150,
      "AuditLogEntry": 100
    }
  }
}
```

---

## Check Specifications

### 1. Connectivity Check

**Purpose**: Verify Neo4j is reachable and accepting queries

**Implementation**:
```cypher
RETURN 1
```

**Success Criteria**: Query returns 1 result within 5 seconds

**Failure Scenarios**:
- Connection refused (Neo4j offline)
- Timeout (Neo4j hanging)
- Authentication failed (wrong credentials)

---

### 2. Schema Consistency Check

**Purpose**: Verify all nodes and relationships conform to defined schema

**Implementation**:
1. Fetch schema definition from Neo4j (or from Graphiti metadata)
2. Sample nodes of each type; verify required properties exist
3. Sample relationships of each type; verify start/end nodes are correct type

**Success Criteria**:
- 100% of sampled nodes have required properties
- 100% of sampled relationships have correct node types at both ends
- No null/missing values in required fields

**Failure Scenarios**:
- Node missing required property
- Relationship connecting incompatible node types
- Property has unexpected type

---

### 3. Orphan Detection Check

**Purpose**: Find relationships pointing to non-existent nodes

**Implementation**:
```cypher
MATCH (n)-[r]-(m)
WHERE NOT EXISTS {MATCH (n)} OR NOT EXISTS {MATCH (m)}
RETURN count(r) as orphaned_count
```

**Success Criteria**: `orphaned_count = 0`

**Failure Scenarios**:
- Relationship exists but one or both endpoints were deleted
- Indicates corruption or failed transaction rollback

---

## Status Codes

| Code | Meaning | When to Return |
|------|---------|----------------|
| 200 | Healthy | All checks pass |
| 503 | Unavailable | Any check fails OR recovery in progress |
| 500 | Internal Error | Unexpected exception (log full error) |

---

## Error Handling

If any check throws an exception:
1. Log full exception with stack trace
2. Return 500 with error message (don't expose stack trace to client)
3. Alert operator via monitoring system

Example:
```json
{
  "status": "error",
  "timestamp": "2025-12-27T15:30:00Z",
  "error_code": "health_check_exception",
  "message": "Unexpected error during health check",
  "error_id": "health-check-abc123def456"  // For operator to look up in logs
}
```

---

## Monitoring & Alerting

**Recommended Polling**:
- Every 30 seconds during normal operation
- Every 10 seconds during recovery
- Every 60 seconds if previous check failed (backoff)

**Alert Conditions**:
- Health check fails 3 consecutive times → Page on-call
- Health check response time > 30 seconds → Warning alert
- Orphan count > 0 → Critical alert (data corruption)
- Recovery stuck (progress % unchanged for 10 minutes) → Critical alert

---

## Contract Testing

### Test Case 1: Healthy Graph

```
GIVEN: Neo4j is running with valid graph
WHEN: GET /health/graph
THEN: Return 200 with "healthy" status
AND: All checks have "pass" status
```

### Test Case 2: Neo4j Offline

```
GIVEN: Neo4j is stopped or unreachable
WHEN: GET /health/graph
THEN: Return 503 within 5 seconds
AND: failed_check = "connectivity"
```

### Test Case 3: Orphaned Relationships

```
GIVEN: Graph has orphaned relationships (manual Cypher delete)
WHEN: GET /health/graph
THEN: Return 503
AND: failed_check = "orphan_detection"
AND: orphaned_count > 0
```

### Test Case 4: Recovery in Progress

```
GIVEN: Recovery operation is running (progress 50%)
WHEN: GET /health/graph
THEN: Return 503
AND: status = "unavailable"
AND: reason = "database_recovery_in_progress"
AND: progress_percent = 50
```

### Test Case 5: Detailed Response

```
GIVEN: Health is good
WHEN: GET /health/graph?detailed=true
THEN: Return 200 with full check details and graph stats
AND: Include duration_ms for each check
AND: Include node_type_breakdown
```
