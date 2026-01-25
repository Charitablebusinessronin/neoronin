// ============================================================================
// BMAD Agent Schema - Core Infrastructure for Self-Improving Coding Agents
// ============================================================================
// Version: 1.0
// Date: 2026-01-25
// Purpose: Define nodes, relationships, constraints, and indexes for BMAD
//          multi-agent learning system integrated with Grap Neo4j infrastructure
//
// Architecture:
// - Agent Layer: AI agents with distinct roles and capabilities
// - Work Execution Layer: Projects, tasks, solutions, and outcomes
// - Self-Improvement Layer: Events, insights, and patterns for learning
// - Knowledge Layer: Documentation, artifacts, and system integrations
//
// Multi-Tenancy: Uses group_id for isolation across:
//   - faith-meats: Faith Meats project-specific context
//   - diff-driven-saas: Diff-Driven SaaS project context
//   - global-coding-skills: Cross-project universal patterns
// ============================================================================

// ============================================================================
// CONSTRAINTS - Ensure Data Integrity
// ============================================================================

// Agent Layer Constraints
CREATE CONSTRAINT agent_name_unique IF NOT EXISTS 
FOR (a:AIAgent) REQUIRE a.name IS UNIQUE;

// Work Execution Layer Constraints
CREATE CONSTRAINT project_name_groupid_unique IF NOT EXISTS 
FOR (p:Project) REQUIRE (p.name, p.group_id) IS UNIQUE;

// Knowledge Layer Constraints
CREATE CONSTRAINT brain_name_groupid_unique IF NOT EXISTS 
FOR (b:Brain) REQUIRE (b.name, b.group_id) IS UNIQUE;

CREATE CONSTRAINT system_name_unique IF NOT EXISTS 
FOR (s:System) REQUIRE s.name IS UNIQUE;

// ============================================================================
// INDEXES - Query Performance Optimization
// ============================================================================

// Agent Layer Indexes
CREATE INDEX agent_role IF NOT EXISTS 
FOR (a:AIAgent) ON (a.role);

CREATE INDEX agent_status IF NOT EXISTS 
FOR (a:AIAgent) ON (a.status);

// Work Execution Layer Indexes
CREATE INDEX project_groupid IF NOT EXISTS 
FOR (p:Project) ON (p.group_id);

CREATE INDEX project_status IF NOT EXISTS 
FOR (p:Project) ON (p.status);

CREATE INDEX task_status_groupid IF NOT EXISTS 
FOR (t:Task) ON (t.status, t.group_id);

CREATE INDEX task_complexity IF NOT EXISTS 
FOR (t:Task) ON (t.complexity);

CREATE INDEX solution_groupid IF NOT EXISTS 
FOR (s:Solution) ON (s.group_id);

CREATE INDEX outcome_status_groupid IF NOT EXISTS 
FOR (o:Outcome) ON (o.status, o.group_id);

CREATE INDEX outcome_timestamp IF NOT EXISTS 
FOR (o:Outcome) ON (o.timestamp);

// Self-Improvement Layer Indexes
CREATE INDEX event_type IF NOT EXISTS 
FOR (e:Event) ON (e.event_type);

CREATE INDEX event_timestamp IF NOT EXISTS 
FOR (e:Event) ON (e.timestamp);

CREATE INDEX event_groupid IF NOT EXISTS 
FOR (e:Event) ON (e.group_id);

CREATE INDEX insight_confidence IF NOT EXISTS 
FOR (i:Insight) ON (i.confidence_score);

CREATE INDEX insight_groupid IF NOT EXISTS 
FOR (i:Insight) ON (i.group_id);

CREATE INDEX insight_applies_to IF NOT EXISTS 
FOR (i:Insight) ON (i.applies_to);

CREATE INDEX pattern_category IF NOT EXISTS 
FOR (p:Pattern) ON (p.category);

CREATE INDEX pattern_success_rate IF NOT EXISTS 
FOR (p:Pattern) ON (p.success_rate);

CREATE INDEX pattern_groupid IF NOT EXISTS 
FOR (p:Pattern) ON (p.group_id);

// Knowledge Layer Indexes
CREATE INDEX knowledge_accessible IF NOT EXISTS 
FOR (k:KnowledgeItem) ON (k.ai_accessible, k.group_id);

CREATE INDEX knowledge_content_type IF NOT EXISTS 
FOR (k:KnowledgeItem) ON (k.content_type);

CREATE INDEX knowledge_category IF NOT EXISTS 
FOR (k:KnowledgeItem) ON (k.category);

CREATE INDEX artifact_type IF NOT EXISTS 
FOR (a:Artifact) ON (a.artifact_type);

CREATE INDEX artifact_groupid IF NOT EXISTS 
FOR (a:Artifact) ON (a.group_id);

CREATE INDEX brain_scope IF NOT EXISTS 
FOR (b:Brain) ON (b.scope);

CREATE INDEX brain_groupid IF NOT EXISTS 
FOR (b:Brain) ON (b.group_id);

CREATE INDEX system_type IF NOT EXISTS 
FOR (s:System) ON (s.type);

CREATE INDEX domain_name IF NOT EXISTS 
FOR (d:Domain) ON (d.name);

// ============================================================================
// SAMPLE PATTERNS - Query Templates for Common Operations
// ============================================================================

// Pattern 1: Self-Improvement Loop (Core Learning Cycle)
// Task → Solution → Outcome → Insight → Pattern → [Future Solutions]
// Example usage:
// MATCH (t:Task {description: 'Implement user authentication'})
// MATCH (t)-[:IMPLEMENTED_BY]->(s:Solution)
// MATCH (s)-[:RESULTED_IN]->(o:Outcome {status: 'Success'})
// CREATE (o)-[:GENERATED]->(i:Insight {rule: 'Use OAuth2 for third-party auth'})
// MERGE (p:Pattern {pattern_name: 'OAuth2 Authentication'})
// CREATE (i)-[:INFORMS]->(p)

// Pattern 2: Agent Learning
// Agents learn from insights and apply patterns to new work
// Example usage:
// MATCH (agent:AIAgent {name: 'Brooks'})
// MATCH (i:Insight) WHERE i.confidence_score > 0.8
// CREATE (agent)-[:LEARNED]->(i)

// Pattern 3: Cross-Agent Knowledge Transfer
// Share high-confidence insights across agents
// Example usage:
// MATCH (agent1:AIAgent)-[:LEARNED]->(i:Insight)
// WHERE i.success_rate > 0.8 AND i.group_id = 'global-coding-skills'
// MATCH (agent2:AIAgent) WHERE agent2.name <> agent1.name
// MERGE (agent2)-[:CAN_APPLY]->(i)

// Pattern 4: Temporal Insight Invalidation
// Mark outdated insights and replace with updated knowledge
// Example usage:
// MATCH (old_insight:Insight {rule: 'Use REST for all APIs'})
// MATCH (new_insight:Insight {rule: 'Use GraphQL for complex data fetching'})
// CREATE (new_insight)-[:INVALIDATES {reason: 'GraphQL provides better performance', date: datetime()}]->(old_insight)

// Pattern 5: Brain-Scoped Memory Retrieval
// Retrieve agent-specific, project-specific, or global knowledge
// Example usage:
// MATCH (agent:AIAgent {name: 'Troy'})-[:HAS_MEMORY_IN]->(brain:Brain {scope: 'agent_specific'})
// MATCH (brain)-[:CONTAINS]->(e:Event) WHERE e.timestamp > datetime() - duration('P7D')
// RETURN e ORDER BY e.timestamp DESC LIMIT 20

// ============================================================================
// MAINTENANCE QUERIES - Health and Cleanup
// ============================================================================

// Query 1: Confidence Decay for Stale Insights (Run Monthly)
// Reduces confidence of insights not applied recently
// MATCH (i:Insight)
// WHERE i.last_applied < datetime() - duration('P90D')
// SET i.confidence_score = i.confidence_score * 0.9
// RETURN count(i) as insights_decayed

// Query 2: Pattern Effectiveness Update (Run Daily)
// Recalculates success_rate based on recent outcomes
// MATCH (p:Pattern)<-[:USED_IN]-(s:Solution)-[:RESULTED_IN]->(o:Outcome)
// WITH p, count(o) as total, count(CASE WHEN o.status = 'Success' THEN 1 END) as successes
// SET p.success_rate = toFloat(successes) / total, p.times_used = total
// RETURN p.pattern_name, p.success_rate, p.times_used

// Query 3: Orphaned Relationship Detection (Integrated with Health Checks)
// Find patterns or insights not connected to outcomes or tasks
// MATCH (i:Insight) WHERE NOT (i)<-[:GENERATED]-(:Outcome)
// RETURN i.rule as orphaned_insight
// UNION
// MATCH (p:Pattern) WHERE NOT (p)<-[:INFORMS]-(:Insight)
// RETURN p.pattern_name as orphaned_pattern

// Query 4: Event Aggregation for Old Data (Run Weekly)
// Archive events older than 30 days to summary metrics
// MATCH (e:Event) WHERE e.timestamp < datetime() - duration('P30D')
// WITH e.event_type as type, e.group_id as group, count(e) as event_count
// MERGE (summary:EventSummary {event_type: type, group_id: group, period: 'archived'})
// ON CREATE SET summary.count = event_count
// ON MATCH SET summary.count = summary.count + event_count
// WITH type, group
// MATCH (e:Event {event_type: type, group_id: group})
// WHERE e.timestamp < datetime() - duration('P30D')
// DETACH DELETE e
// RETURN count(e) as events_archived

// ============================================================================
// SCHEMA VALIDATION
// ============================================================================
// Run this query to validate schema deployment:
// CALL db.constraints()
// UNION
// CALL db.indexes()
// Expected: 6 constraints, 30+ indexes

// ============================================================================
// END OF SCHEMA
// ============================================================================
