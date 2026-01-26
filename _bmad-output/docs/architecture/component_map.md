# BMAD Phase 2: Technical Architecture Component Map

**Created:** January 25, 2026, 1:51 PM EST
**Architect:** Winston
**Version:** 1.0 (Phase 2)

---

## Overview

This document maps the 7 Functional Requirements from the BMAD PRD to physical software components with interfaces, dependencies, and deployment specifications.

**Functional Requirements Covered:**
- FR1: Memory Query (Cypher templates for agent pattern recall)
- FR2: Event Logging (GitHub MCP tool responses → Neo4j)
- FR3: Health Check (Detect orphaned agents, schema conflicts)
- FR4: Brain Scoping (Multi-tenant filtering via group_id)
- FR5: Contradiction Detection (Flag conflicting patterns)
- FR6: Temporal Relevance (Pattern decay algorithm)
- FR7: Multi-Tenant Templates (Query isolation enforcement)

---

## Component 1: EventLoggerMiddleware

**Purpose:** Capture agent actions and log them to Neo4j as Event nodes

**File:** `_bmad-output/code/bmad/event_logger.py`
**Language:** Python 3.11+
**Architecture Pattern:** Middleware / Interceptor

### Interface Specification

```python
class EventLoggerMiddleware:
    """
    Intercepts MCP tool responses and creates Event → Solution → Outcome chains
    """

    def __init__(self, neo4j_uri: str, neo4j_auth: tuple):
        """
        Initialize with Neo4j connection details

        Args:
            neo4j_uri: bolt://grap-neo4j:7687
            neo4j_auth: (username, password) tuple
        """
        self.driver = GraphDatabase.driver(neo4j_uri, auth=neo4j_auth)

    def intercept_mcp_response(
        self,
        tool_name: str,           # e.g., "create_pull_request"
        agent_name: str,          # e.g., "Brooks"
        result: dict,             # MCP tool JSON response
        group_id: str             # e.g., "faith-meats"
    ) -> str:
        """
        Main entry point for logging MCP tool execution

        Returns:
            event_id (str): UUID of created Event node
        """

    def create_event_node(
        self,
        event_type: str,          # "code_implementation", "review", "testing"
        agent_name: str,
        description: str,
        context: dict,            # Arbitrary metadata (PR#, files, commits)
        group_id: str
    ) -> str:
        """
        Creates Event node, links to AIAgent via PERFORMED relationship

        Cypher executed:
        MATCH (a:AIAgent {name: $agent_name})
        CREATE (e:Event {
            event_type: $event_type,
            description: $description,
            context: $context,
            timestamp: datetime(),
            group_id: $group_id
        })
        CREATE (a)-[:PERFORMED]->(e)
        RETURN e.id
        """

    def link_event_to_solution(
        self,
        event_id: str,
        approach: str,            # Pattern used, methodology
        code_references: list,    # File paths, line numbers
        pattern_id: str = None    # If pattern was used
    ) -> str:
        """
        Creates Solution node, links to Event and Pattern (if any)

        Returns:
            solution_id (str): UUID of created Solution node
        """

    def record_outcome(
        self,
        solution_id: str,
        status: str,              # "success", "failure", "partial"
        metrics: dict,            # Build status, test results, etc.
        error_message: str = None
    ) -> str:
        """
        Creates Outcome node, updates Pattern success_rate if pattern was used

        Returns:
            outcome_id (str): UUID of created Outcome node
        """
```

### Dependencies

```
neo4j-driver==5.15.0
python-dotenv==1.0.0
pydantic==2.5.0  # For data validation
```

### Integration Points

- **Input:** Claude MCP tool response handler
- **Trigger:** After every GitHub MCP tool execution (create_pull_request, push_files, etc.)
- **Execution:** Async (non-blocking agent workflow)
- **Output:** Event/Solution/Outcome nodes in Neo4j

### Deployment

```yaml
# docker-compose.yml entry
bmad-event-logger:
  build: ./code/bmad
  ports:
    - "8001:8001"
  environment:
    - NEO4J_URI=bolt://grap-neo4j:7687
    - NEO4J_USER=neo4j
    - NEO4J_PASSWORD=${NEO4J_PASSWORD}
  depends_on:
    - grap-neo4j
  restart: unless-stopped
```

### Error Handling Strategy

1. **Neo4j Unavailable:**
   - Queue events to local JSON file (`/tmp/bmad_events_queue.json`)
   - Retry connection every 30 seconds
   - Flush queue on reconnect

2. **Validation Failure:**
   - Log error to stderr
   - Don't crash agent workflow
   - Create error metric for monitoring

3. **Timeout:**
   - 5-second timeout per log operation
   - If exceeded, queue event and continue

---

## Component 2: QueryTemplateLibrary

**Purpose:** Provide multi-tenant safe Cypher queries for agents

**File:** `_bmad-output/code/bmad/query_templates.py`
**Language:** Python 3.11+
**Architecture Pattern:** Static utility class

### Interface Specification

```python
class QueryTemplates:
    """
    Parameterized Cypher queries with mandatory multi-tenant isolation
    All queries enforce group_id filtering to prevent cross-project contamination
    """

    @staticmethod
    def get_patterns_for_domain(
        domain: str,
        group_id: str,
        limit: int = 10
    ) -> str:
        """
        Returns Cypher query for patterns in domain, scoped to group_id

        Security: Enforces group_id IN [specified, 'global-coding-skills']
        This prevents faith-meats from seeing diff-driven-saas patterns

        Returns:
            Parameterized Cypher query string
        """
        return """
        MATCH (p:Pattern)-[:APPLIES_TO]->(d:Domain {name: $domain})
        WHERE p.group_id IN [$group_id, 'global-coding-skills']
          AND p.status = 'active'
          AND p.relevance_score > 0.6
        RETURN p.id, p.name, p.description, p.success_rate,
               p.usage_count, p.warnings, p.code_reference
        ORDER BY p.relevance_score DESC, p.usage_count DESC
        LIMIT $limit
        """

    @staticmethod
    def get_recent_insights(
        group_id: str,
        days: int = 30,
        quality_threshold: float = 0.7
    ) -> str:
        """
        Returns high-quality insights from last N days
        Filters by quality_score to reduce noise
        """
        return """
        MATCH (i:Insight)
        WHERE i.group_id IN [$group_id, 'global-coding-skills']
          AND i.created_date >= datetime() - duration({days: $days})
          AND i.quality_score >= $quality_threshold
        RETURN i.id, i.insight_text, i.actionability,
               i.created_date, i.validated_by
        ORDER BY i.quality_score DESC, i.created_date DESC
        """

    @staticmethod
    def get_agent_history(
        agent_name: str,
        group_id: str,
        days: int = 14
    ) -> str:
        """
        Returns agent's recent events, solutions, outcomes
        Used for "show me my recent work" queries
        """
        return """
        MATCH (a:AIAgent {name: $agent_name})-[:PERFORMED]->(e:Event)
        WHERE e.group_id = $group_id
          AND e.timestamp >= datetime() - duration({days: $days})
        OPTIONAL MATCH (e)-[:PRODUCED]->(s:Solution)-[:PRODUCED]->(o:Outcome)
        RETURN e.event_type, e.description, e.timestamp,
               s.approach, o.status, o.metrics
        ORDER BY e.timestamp DESC
        """

    @staticmethod
    def check_pattern_conflicts(domain: str) -> str:
        """
        Detects contradictory patterns in same domain
        Returns pairs that recommend conflicting approaches
        """
        return """
        MATCH (p1:Pattern)-[:APPLIES_TO]->(d:Domain {name: $domain})
        MATCH (p2:Pattern)-[:APPLIES_TO]->(d)
        WHERE p1.id < p2.id  // Avoid duplicate pairs
          AND p1.recommendation != p2.recommendation
          AND NOT (p1)-[:CONTRADICTS]-(p2)  // Not already flagged
        RETURN p1.id, p1.name, p1.recommendation,
               p2.id, p2.name, p2.recommendation
        """
```

### Dependencies

```
neo4j-driver==5.15.0
```

### Security Model

**Multi-Tenant Isolation Enforcement:**
- All queries include `WHERE p.group_id IN [$group_id, 'global-coding-skills']`
- Global fallback (`'global-coding-skills'`) always included
- No raw Cypher execution allowed - only parameterized templates
- SQL injection protection via parameter binding

---

## Component 3: PatternManager

**Purpose:** CRUD operations on Pattern nodes with usage tracking

**File:** `_bmad-output/code/bmad/pattern_manager.py`
**Language:** Python 3.11+
**Architecture Pattern:** Repository pattern with caching

### Interface Specification

```python
class PatternManager:
    """
    Manages Pattern lifecycle: search, usage tracking, success rate updates
    """

    def __init__(self, neo4j_driver, cache_size: int = 100):
        """
        Initialize with Neo4j driver and LRU cache

        Args:
            neo4j_driver: Neo4j GraphDatabase.driver() instance
            cache_size: Max patterns to cache in memory (default 100)
        """
        self.driver = neo4j_driver
        self.cache = LRUCache(cache_size)  # Hot patterns cached

    def search_patterns(
        self,
        keywords: list[str],
        domain: str,
        group_id: str,
        limit: int = 10
    ) -> list[dict]:
        """
        Full-text search across Pattern names and descriptions

        Args:
            keywords: List of search terms (AND logic)
            domain: Filter by domain (optional, pass None for all)
            group_id: Multi-tenant isolation
            limit: Max results

        Returns:
            List of pattern dicts with metadata
        """

    def get_pattern_details(self, pattern_id: str) -> dict:
        """
        Fetch complete pattern with warnings, code refs, history

        Caching strategy:
        - Check cache first
        - If miss, fetch from Neo4j and cache
        - Cache TTL: 1 hour

        Returns:
            Pattern dict with all properties
        """
        if pattern_id in self.cache:
            return self.cache[pattern_id]
        # ... fetch from Neo4j and cache

    def record_pattern_usage(
        self,
        pattern_id: str,
        task_id: str,
        agent_name: str
    ) -> None:
        """
        Increments Pattern.usage_count
        Creates USED_PATTERN relationship from Solution to Pattern

        Side effects:
        - Invalidates pattern cache entry
        - Updates Pattern.last_used_date
        """

    def update_success_rate(
        self,
        pattern_id: str,
        outcome_status: str  # "success" or "failure"
    ) -> float:
        """
        Recalculates Pattern.success_rate based on outcomes

        Formula:
        success_rate = success_count / total_usage_count

        Returns:
            New success_rate (float 0.0-1.0)
        """

    def create_pattern(
        self,
        name: str,
        domain: str,
        description: str,
        code_reference: str,
        warnings: list[str],
        group_id: str
    ) -> str:
        """
        Creates new Pattern node

        Returns:
            pattern_id (str): UUID of created pattern
        """
```

### Dependencies

```
neo4j-driver==5.15.0
cachetools==5.3.0  # For LRU cache
```

### Caching Strategy

- **Cache Size:** Top 100 most-used patterns
- **Invalidation:** On success_rate update or usage increment
- **TTL:** 1 hour
- **Eviction:** Least Recently Used (LRU)

---

## Component 4: InsightGeneratorEngine

**Purpose:** Analyze outcomes and auto-generate actionable insights

**File:** `_bmad-output/code/bmad/insight_generator.py`
**Language:** Python 3.11+
**Architecture Pattern:** Batch processor (cron job)

### Interface Specification

```python
class InsightGeneratorEngine:
    """
    Nightly job: Analyzes patterns, outcomes, generates insights
    """

    def __init__(self, neo4j_driver):
        self.driver = neo4j_driver

    def analyze_pattern_effectiveness(self, days: int = 30) -> list[dict]:
        """
        Identifies patterns with:
        - Low success rate (<60%) and high usage (5+) → Warning insight
        - High success rate (>85%) and low awareness → Promotion insight

        Returns:
            List of insight dicts to create
        """

    def detect_pattern_contradictions(self) -> list[dict]:
        """
        Finds patterns in same domain with conflicting recommendations
        Uses QueryTemplates.check_pattern_conflicts()

        Returns:
            List of contradiction insights for architect review
        """

    def identify_failure_patterns(
        self,
        group_id: str,
        days: int = 14
    ) -> list[dict]:
        """
        Detects recurring errors (same error_message 3+ times)

        Returns:
            List of failure pattern insights
        """

    def generate_insights(self, quality_threshold: float = 0.7) -> int:
        """
        Main orchestrator: Runs all analysis methods
        Creates Insight nodes for actionable findings

        Workflow:
        1. Run all analyzers
        2. Score insights for quality
        3. Filter by quality threshold
        4. Create Insight nodes
        5. Link to related patterns/outcomes

        Returns:
            Count of high-quality insights generated
        """

    def calculate_insight_quality(self, insight_data: dict) -> float:
        """
        Quality scoring algorithm:

        quality = (
            actionability * 0.4 +      # Can agent act on this?
            novelty * 0.3 +             # Is this new information?
            evidence_strength * 0.2 +   # How many data points?
            potential_impact * 0.1      # How much improvement expected?
        )

        Returns:
            Quality score (float 0.0-1.0)
        """
```

### Dependencies

```
neo4j-driver==5.15.0
schedule==1.2.0  # For cron-like scheduling
```

### Execution Schedule

```python
# Runs daily at 2:00 AM
import schedule

schedule.every().day.at("02:00").do(insight_generator.generate_insights)
```

**Expected Runtime:** 5-10 minutes for 1000+ events

---

## Component 5: RelevanceScoringService

**Purpose:** Apply temporal decay to pattern relevance

**File:** `_bmad-output/code/bmad/relevance_scoring.py`
**Language:** Python 3.11+
**Architecture Pattern:** Batch processor

### Algorithm

```python
import math

def calculate_relevance(
    success_rate: float,
    usage_count: int,
    days_since_last_use: int,
    half_life_days: int = 90
) -> float:
    """
    Relevance formula with temporal decay

    Components:
    - decay_factor: Exponential decay (90-day half-life)
    - usage_boost: Logarithmic scaling from usage count
    - base_quality: Pattern success rate

    Formula:
    relevance = success_rate * decay_factor * (1 + usage_boost)

    Returns:
        Relevance score (float 0.0-1.0, capped)
    """
    decay_factor = math.exp(-days_since_last_use / half_life_days)
    usage_boost = math.log(usage_count + 1) / 3

    relevance = success_rate * decay_factor * (1 + usage_boost)
    return min(relevance, 1.0)  # Cap at 1.0
```

### Execution

- Runs after InsightGeneratorEngine (2:10 AM daily)
- Updates all Pattern.relevance_score properties
- Marks patterns unused for 180+ days as "stale"
- Runtime: ~2 minutes for 500+ patterns

---

## Component 6: HealthCheckService

**Purpose:** Detect orphaned nodes, schema conflicts, system health

**File:** `_bmad-output/code/bmad/health_check.py`
**Language:** Python 3.11+
**Architecture Pattern:** Diagnostic utility

### Interface Specification

```python
class HealthCheckService:
    """
    System health monitoring and auto-repair triggers
    """

    def check_orphaned_agents(self) -> list[str]:
        """
        Finds AIAgent nodes with 0 relationships

        Query:
        MATCH (a:AIAgent)
        WHERE NOT (a)--()
        RETURN a.name

        Returns:
            List of orphaned agent names
        """

    def check_schema_conflicts(self) -> list[dict]:
        """
        Detects indexes/constraints that block schema updates

        Returns:
            List of conflicts with resolution steps
        """

    def check_brain_connectivity(self) -> dict:
        """
        Verifies all agents connected to:
        - Personal brain (1 per agent)
        - Global brain (shared)

        Returns:
            Stats dict with connectivity report
        """

    def run_full_health_check(self) -> dict:
        """
        Orchestrates all health checks

        Returns:
            Comprehensive health report dict
        """
        return {
            'orphaned_agents': self.check_orphaned_agents(),
            'schema_conflicts': self.check_schema_conflicts(),
            'brain_connectivity': self.check_brain_connectivity(),
            'timestamp': datetime.now().isoformat()
        }
```

### Execution

- **On-demand:** `python -m bmad.health_check`
- **Automated:** Weekly (Sunday 1 AM)
- **Output:** JSON report to stdout + log file

---

## Component Dependency Graph

```
┌────────────────────────────────────────────────────┐
│         Agent (Brooks/Troy/Winston/etc.)           │
└─────────────┬───────────────────┬──────────────────┘
              │                   │
              ▼                   ▼
┌─────────────────────┐  ┌────────────────────────┐
│  PatternManager     │  │ EventLoggerMiddleware  │
│  - search_patterns()│  │ - intercept_mcp()      │
│  - record_usage()   │  │ - create_event()       │
└──────────┬──────────┘  └──────────┬─────────────┘
           │                        │
           ▼                        ▼
┌──────────────────────────────────────────────┐
│  QueryTemplateLibrary                        │
│  - get_patterns_for_domain()                 │
│  - get_recent_insights()                     │
│  (Ensures multi-tenant isolation)            │
└────────────────┬─────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────┐
│         Neo4j Graph Database                 │
│  Nodes: AIAgent, Event, Pattern, Insight     │
│  Edges: PERFORMED, USED_PATTERN, GENERATES   │
│  Indexes: (group_id, domain, timestamp)      │
└────────────┬─────────────────────────────────┘
             │
    ┌────────┴────────┐
    ▼                 ▼
┌──────────────────────────┐  ┌──────────────────────┐
│ InsightGeneratorEngine   │  │ RelevanceScoringService│
│ - analyze_effectiveness()│  │ - calculate_relevance()│
│ - detect_contradictions()│  │ - update_all_patterns()│
│ (Runs 2 AM daily)        │  │ (Runs 2:10 AM daily)  │
└──────────────────────────┘  └──────────────────────┘
```

---

## Deployment Architecture

### Docker Compose Stack

```yaml
version: '3.8'

services:
  grap-neo4j:
    image: neo4j:5.13.0-enterprise
    ports:
      - "7474:7474"  # Browser
      - "7687:7687"  # Bolt
    environment:
      - NEO4J_AUTH=neo4j/Kamina2025*
    volumes:
      - neo4j-data:/data
      - neo4j-logs:/logs

  bmad-event-logger:
    build: ./_bmad-output/code/bmad
    ports:
      - "8001:8001"
    environment:
      - NEO4J_URI=bolt://grap-neo4j:7687
      - NEO4J_USER=neo4j
      - NEO4J_PASSWORD=Kamina2025*
      - LOG_LEVEL=INFO
    depends_on:
      - grap-neo4j
    restart: unless-stopped

  bmad-scheduler:
    build: ./_bmad-output/code/bmad
    command: python -m bmad.scheduler
    environment:
      - NEO4J_URI=bolt://grap-neo4j:7687
      - NEO4J_USER=neo4j
      - NEO4J_PASSWORD=Kamina2025*
      - INSIGHT_SCHEDULE=0 2 * * *   # 2 AM daily
      - RELEVANCE_SCHEDULE=10 2 * * * # 2:10 AM daily
      - HEALTH_SCHEDULE=0 1 * * 0     # Sunday 1 AM
    depends_on:
      - grap-neo4j
    restart: unless-stopped

volumes:
  neo4j-data:
  neo4j-logs:
```

---

## Configuration

### Environment Variables

```bash
# .env file
NEO4J_URI=bolt://grap-neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=Kamina2025*

# Event Logger
EVENT_LOGGER_PORT=8001
EVENT_QUEUE_PATH=/tmp/bmad_events_queue.json
EVENT_RETRY_INTERVAL=30  # seconds

# Insight Generation
INSIGHT_GENERATION_SCHEDULE=0 2 * * *    # 2 AM daily
INSIGHT_QUALITY_THRESHOLD=0.7
INSIGHT_ANALYSIS_WINDOW=30  # days

# Relevance Scoring
RELEVANCE_UPDATE_SCHEDULE=10 2 * * *     # 2:10 AM daily
RELEVANCE_HALF_LIFE=90  # days
STALE_PATTERN_THRESHOLD=180  # days

# Health Checks
HEALTH_CHECK_SCHEDULE=0 1 * * 0          # Sunday 1 AM
HEALTH_CHECK_OUTPUT=/var/log/bmad/health_checks/
```

---

## Testing Strategy

### Unit Tests
- Each component has isolated unit tests
- Mocked Neo4j driver for speed
- Test fixtures for sample data

### Integration Tests
- Use test Neo4j instance
- End-to-end event logging flow
- Pattern query multi-tenancy validation

### Performance Tests
- Event logger: 100+ events without degradation
- Query templates: <100ms execution
- Insight generation: <10 min for 1000+ events

---

## Success Metrics

**Phase 2 Component Acceptance:**
- ✅ Event logger processes 100+ events error-free
- ✅ Pattern queries enforce multi-tenant isolation (0 cross-project leaks)
- ✅ Insight quality >80% (quality_score >= 0.7)
- ✅ Query latency <100ms (95th percentile)
- ✅ Relevance scoring completes in <2 minutes

---

**Document Version:** 1.0
**Last Updated:** January 25, 2026, 1:58 PM EST
**Next Review:** Phase 2 completion (Feb 14, 2026)