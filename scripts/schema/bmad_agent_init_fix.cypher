// ============================================================================
// BMAD Agent Initialization FIX - Uses MATCH-based relationship creation
// ============================================================================
// This script fixes the relationship creation issue by using MATCH
// instead of relying on variable persistence across statements
// ============================================================================

// ============================================================================
// Create relationships for each agent
// ============================================================================

// Jay - Business Analyst
MATCH (jay:AIAgent {name: 'Jay'})
MATCH (analysis:Domain {name: 'Business Analysis'})
MATCH (notion:System {name: 'Notion'})
MATCH (slack:System {name: 'Slack'})
MATCH (global_brain:Brain {name: 'BMAD Global Brain'})
MATCH (jay_brain:Brain {name: 'Jay Brain'})
MERGE (jay)-[:SPECIALIZES_IN]->(analysis)
MERGE (jay)-[:INTEGRATES_WITH]->(notion)
MERGE (jay)-[:INTEGRATES_WITH]->(slack)
MERGE (jay)-[:HAS_MEMORY_IN]->(global_brain)
MERGE (jay)-[:HAS_MEMORY_IN]->(jay_brain);

// Winston - Architect
MATCH (winston:AIAgent {name: 'Winston'})
MATCH (architecture:Domain {name: 'Architecture'})
MATCH (github:System {name: 'GitHub'})
MATCH (winston_brain:Brain {name: 'Winston Brain'})
MERGE (winston)-[:SPECIALIZES_IN]->(architecture)
MERGE (winston)-[:INTEGRATES_WITH]->(github)
MERGE (winston)-[:INTEGRATES_WITH]->(notion)
MERGE (winston)-[:HAS_MEMORY_IN]->(global_brain)
MERGE (winston)-[:HAS_MEMORY_IN]->(winston_brain);

// Brooks - Developer
MATCH (brooks:AIAgent {name: 'Brooks'})
MATCH (coding:Domain {name: 'Coding & Development'})
MATCH (brooks_brain:Brain {name: 'Brooks Brain'})
MERGE (brooks)-[:SPECIALIZES_IN]->(coding)
MERGE (brooks)-[:INTEGRATES_WITH]->(github)
MERGE (brooks)-[:INTEGRATES_WITH]->(slack)
MERGE (brooks)-[:HAS_MEMORY_IN]->(global_brain)
MERGE (brooks)-[:HAS_MEMORY_IN]->(brooks_brain);

// Dutch - Product Manager
MATCH (dutch:AIAgent {name: 'Dutch'})
MATCH (product:Domain {name: 'Product Management'})
MATCH (dutch_brain:Brain {name: 'Dutch Brain'})
MERGE (dutch)-[:SPECIALIZES_IN]->(product)
MERGE (dutch)-[:INTEGRATES_WITH]->(notion)
MERGE (dutch)-[:INTEGRATES_WITH]->(slack)
MERGE (dutch)-[:HAS_MEMORY_IN]->(global_brain)
MERGE (dutch)-[:HAS_MEMORY_IN]->(dutch_brain);

// Troy - Test Engineer & Analyst
MATCH (troy:AIAgent {name: 'Troy'})
MATCH (testing:Domain {name: 'Testing'})
MATCH (troy_brain:Brain {name: 'Troy Brain'})
MERGE (troy)-[:SPECIALIZES_IN]->(testing)
MERGE (troy)-[:INTEGRATES_WITH]->(github)
MERGE (troy)-[:INTEGRATES_WITH]->(notion)
MERGE (troy)-[:HAS_MEMORY_IN]->(global_brain)
MERGE (troy)-[:HAS_MEMORY_IN]->(troy_brain);

// Bob - Scrum Master
MATCH (bob:AIAgent {name: 'Bob'})
MATCH (project:Domain {name: 'Project Management'})
MATCH (bob_brain:Brain {name: 'Bob Brain'})
MERGE (bob)-[:SPECIALIZES_IN]->(project)
MERGE (bob)-[:INTEGRATES_WITH]->(notion)
MERGE (bob)-[:INTEGRATES_WITH]->(slack)
MERGE (bob)-[:INTEGRATES_WITH]->(github)
MERGE (bob)-[:HAS_MEMORY_IN]->(global_brain)
MERGE (bob)-[:HAS_MEMORY_IN]->(bob_brain);

// Allura - UX Expert
MATCH (allura:AIAgent {name: 'Allura'})
MATCH (ux:Domain {name: 'UX Design'})
MATCH (allura_brain:Brain {name: 'Allura Brain'})
MERGE (allura)-[:SPECIALIZES_IN]->(ux)
MERGE (allura)-[:INTEGRATES_WITH]->(notion)
MERGE (allura)-[:INTEGRATES_WITH]->(slack)
MERGE (allura)-[:HAS_MEMORY_IN]->(global_brain)
MERGE (allura)-[:HAS_MEMORY_IN]->(allura_brain);

// BMad Master - Master Coordinator
MATCH (master:AIAgent {name: 'BMad Master'})
MATCH (master_brain:Brain {name: 'Master Brain'})
MERGE (master)-[:SPECIALIZES_IN]->(project)
MERGE (master)-[:SPECIALIZES_IN]->(product)
MERGE (master)-[:INTEGRATES_WITH]->(notion)
MERGE (master)-[:INTEGRATES_WITH]->(slack)
MERGE (master)-[:INTEGRATES_WITH]->(github)
MERGE (master)-[:HAS_MEMORY_IN]->(global_brain)
MERGE (master)-[:HAS_MEMORY_IN]->(master_brain);

// BMad Orchestrator - Workflow Orchestrator
MATCH (orchestrator:AIAgent {name: 'BMad Orchestrator'})
MATCH (neo4j:System {name: 'Neo4j'})
MATCH (orchestrator_brain:Brain {name: 'Orchestrator Brain'})
MERGE (orchestrator)-[:SPECIALIZES_IN]->(project)
MERGE (orchestrator)-[:INTEGRATES_WITH]->(neo4j)
MERGE (orchestrator)-[:INTEGRATES_WITH]->(github)
MERGE (orchestrator)-[:INTEGRATES_WITH]->(notion)
MERGE (orchestrator)-[:INTEGRATES_WITH]->(slack)
MERGE (orchestrator)-[:HAS_MEMORY_IN]->(global_brain)
MERGE (orchestrator)-[:HAS_MEMORY_IN]->(orchestrator_brain);

// ============================================================================
// Agent Collaboration Relationships
// ============================================================================

// Orchestrator coordinates all agents
MATCH (orchestrator:AIAgent {name: 'BMad Orchestrator'})
MATCH (jay:AIAgent {name: 'Jay'})
MATCH (winston:AIAgent {name: 'Winston'})
MATCH (brooks:AIAgent {name: 'Brooks'})
MATCH (dutch:AIAgent {name: 'Dutch'})
MATCH (troy:AIAgent {name: 'Troy'})
MATCH (bob:AIAgent {name: 'Bob'})
MATCH (allura:AIAgent {name: 'Allura'})
MERGE (orchestrator)-[:COORDINATES]->(jay)
MERGE (orchestrator)-[:COORDINATES]->(winston)
MERGE (orchestrator)-[:COORDINATES]->(brooks)
MERGE (orchestrator)-[:COORDINATES]->(dutch)
MERGE (orchestrator)-[:COORDINATES]->(troy)
MERGE (orchestrator)-[:COORDINATES]->(bob)
MERGE (orchestrator)-[:COORDINATES]->(allura);

// Master oversees all agents
MATCH (master:AIAgent {name: 'BMad Master'})
MERGE (master)-[:OVERSEES]->(jay)
MERGE (master)-[:OVERSEES]->(winston)
MERGE (master)-[:OVERSEES]->(brooks)
MERGE (master)-[:OVERSEES]->(dutch)
MERGE (master)-[:OVERSEES]->(troy)
MERGE (master)-[:OVERSEES]->(bob)
MERGE (master)-[:OVERSEES]->(allura)
MERGE (master)-[:OVERSEES]->(orchestrator);

// Planning phase collaborations
MATCH (dutch:AIAgent {name: 'Dutch'})
MATCH (winston:AIAgent {name: 'Winston'})
MERGE (jay)-[:COLLABORATES_WITH]->(dutch)
MERGE (dutch)-[:COLLABORATES_WITH]->(winston)
MERGE (winston)-[:COLLABORATES_WITH]->(brooks);

// Development phase collaborations
MERGE (brooks)-[:COLLABORATES_WITH]->(troy)
MERGE (troy)-[:COLLABORATES_WITH]->(allura);

// Coordination collaborations
MERGE (bob)-[:TRACKS]->(jay)
MERGE (bob)-[:TRACKS]->(winston)
MERGE (bob)-[:TRACKS]->(brooks)
MERGE (bob)-[:TRACKS]->(dutch)
MERGE (bob)-[:TRACKS]->(troy)
MERGE (bob)-[:TRACKS]->(allura);

// ============================================================================
// END OF FIX SCRIPT
// ============================================================================