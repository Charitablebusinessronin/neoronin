#!/bin/bash
# synaptic_hardening.sh - Repair orphaned BMAD agents

echo "🔧 Phase 1.5: Synaptic Hardening"
echo "================================="

NEO4J_CONTAINER="grap-neo4j"
NEO4J_USER="neo4j"
NEO4J_PASS="Kamina2025*"

run_query() {
    docker exec $NEO4J_CONTAINER cypher-shell -u $NEO4J_USER -p $NEO4J_PASS "$1"
}

echo -e "\n[1/4] Cleaning Brooks label conflict..."
run_query "
MATCH (b:AIAgent {name: 'Brooks'})
WHERE 'Memory' IN labels(b)
REMOVE b:Memory
RETURN 'Brooks cleaned' as status
"

echo -e "\n[2/4] Deploying missing constraints..."
run_query "
CREATE CONSTRAINT agent_name_unique IF NOT EXISTS FOR (a:AIAgent) REQUIRE a.name IS UNIQUE;
CREATE CONSTRAINT project_name_groupid_unique IF NOT EXISTS FOR (p:Project) REQUIRE (p.name, p.group_id) IS UNIQUE;
CREATE CONSTRAINT brain_name_groupid_unique IF NOT EXISTS FOR (b:Brain) REQUIRE (b.name, b.group_id) IS UNIQUE;
CREATE CONSTRAINT system_name_unique IF NOT EXISTS FOR (s:System) REQUIRE s.name IS UNIQUE;
"

echo -e "\n[3/4] Wiring agent relationships..."
run_query "
// Ensure Systems exist
MERGE (github:System {name: 'GitHub'})
ON CREATE SET github.type = 'version_control', github.version = 'Enterprise';
MERGE (notion:System {name: 'Notion'})
ON CREATE SET notion.type = 'documentation', notion.version = 'Enterprise';
MERGE (slack:System {name: 'Slack'})
ON CREATE SET slack.type = 'communication', slack.version = 'Enterprise';
MERGE (neo4j:System {name: 'Neo4j'})
ON CREATE SET neo4j.type = 'database', neo4j.version = '5.13.0';

// Ensure Domains exist
MERGE (coding:Domain {name: 'Coding & Development'})
ON CREATE SET coding.description = 'Software development, implementation, code quality';
MERGE (architecture:Domain {name: 'Architecture'})
ON CREATE SET architecture.description = 'System design, technical architecture, scalability';
MERGE (testing:Domain {name: 'Testing'})
ON CREATE SET testing.description = 'Quality assurance, test automation, documentation';
MERGE (ux:Domain {name: 'UX Design'})
ON CREATE SET ux.description = 'User experience, interface design, usability';
MERGE (product:Domain {name: 'Product Management'})
ON CREATE SET product.description = 'Requirements, roadmap, stakeholder management';
MERGE (analysis:Domain {name: 'Business Analysis'})
ON CREATE SET analysis.description = 'Requirements analysis, user stories, business logic';
MERGE (project:Domain {name: 'Project Management'})
ON CREATE SET project.description = 'Sprint planning, task tracking, team coordination';

// Ensure Global Brain exists
MERGE (global_brain:Brain {name: 'BMAD Global Brain', group_id: 'global-coding-skills'})
ON CREATE SET 
  global_brain.scope = 'global',
  global_brain.created_date = datetime();

// Wire Jay
MATCH (jay:AIAgent {name: 'Jay'})
MATCH (analysis:Domain {name: 'Business Analysis'})
MATCH (notion:System {name: 'Notion'})
MATCH (slack:System {name: 'Slack'})
MATCH (global_brain:Brain {name: 'BMAD Global Brain'})
MERGE (jay)-[:SPECIALIZES_IN]->(analysis)
MERGE (jay)-[:INTEGRATES_WITH]->(notion)
MERGE (jay)-[:INTEGRATES_WITH]->(slack)
MERGE (jay)-[:HAS_MEMORY_IN]->(global_brain)
MERGE (jay_brain:Brain {name: 'Jay Brain', group_id: 'global-coding-skills'})
ON CREATE SET jay_brain.scope = 'agent_specific', jay_brain.created_date = datetime()
MERGE (jay)-[:HAS_MEMORY_IN]->(jay_brain);

// Wire Winston
MATCH (winston:AIAgent {name: 'Winston'})
MATCH (architecture:Domain {name: 'Architecture'})
MATCH (github:System {name: 'GitHub'})
MATCH (notion:System {name: 'Notion'})
MATCH (global_brain:Brain {name: 'BMAD Global Brain'})
MERGE (winston)-[:SPECIALIZES_IN]->(architecture)
MERGE (winston)-[:INTEGRATES_WITH]->(github)
MERGE (winston)-[:INTEGRATES_WITH]->(notion)
MERGE (winston)-[:HAS_MEMORY_IN]->(global_brain)
MERGE (winston_brain:Brain {name: 'Winston Brain', group_id: 'global-coding-skills'})
ON CREATE SET winston_brain.scope = 'agent_specific', winston_brain.created_date = datetime()
MERGE (winston)-[:HAS_MEMORY_IN]->(winston_brain);

// Wire Brooks
MATCH (brooks:AIAgent {name: 'Brooks'})
MATCH (coding:Domain {name: 'Coding & Development'})
MATCH (github:System {name: 'GitHub'})
MATCH (slack:System {name: 'Slack'})
MATCH (global_brain:Brain {name: 'BMAD Global Brain'})
MERGE (brooks)-[:SPECIALIZES_IN]->(coding)
MERGE (brooks)-[:INTEGRATES_WITH]->(github)
MERGE (brooks)-[:INTEGRATES_WITH]->(slack)
MERGE (brooks)-[:HAS_MEMORY_IN]->(global_brain)
MERGE (brooks_brain:Brain {name: 'Brooks Brain', group_id: 'global-coding-skills'})
ON CREATE SET brooks_brain.scope = 'agent_specific', brooks_brain.created_date = datetime()
MERGE (brooks)-[:HAS_MEMORY_IN]->(brooks_brain);

// Wire Dutch
MATCH (dutch:AIAgent {name: 'Dutch'})
MATCH (product:Domain {name: 'Product Management'})
MATCH (notion:System {name: 'Notion'})
MATCH (slack:System {name: 'Slack'})
MATCH (global_brain:Brain {name: 'BMAD Global Brain'})
MERGE (dutch)-[:SPECIALIZES_IN]->(product)
MERGE (dutch)-[:INTEGRATES_WITH]->(notion)
MERGE (dutch)-[:INTEGRATES_WITH]->(slack)
MERGE (dutch)-[:HAS_MEMORY_IN]->(global_brain)
MERGE (dutch_brain:Brain {name: 'Dutch Brain', group_id: 'global-coding-skills'})
ON CREATE SET dutch_brain.scope = 'agent_specific', dutch_brain.created_date = datetime()
MERGE (dutch)-[:HAS_MEMORY_IN]->(dutch_brain);

// Wire Troy
MATCH (troy:AIAgent {name: 'Troy'})
MATCH (testing:Domain {name: 'Testing'})
MATCH (github:System {name: 'GitHub'})
MATCH (notion:System {name: 'Notion'})
MATCH (global_brain:Brain {name: 'BMAD Global Brain'})
MERGE (troy)-[:SPECIALIZES_IN]->(testing)
MERGE (troy)-[:INTEGRATES_WITH]->(github)
MERGE (troy)-[:INTEGRATES_WITH]->(notion)
MERGE (troy)-[:HAS_MEMORY_IN]->(global_brain)
MERGE (troy_brain:Brain {name: 'Troy Brain', group_id: 'global-coding-skills'})
ON CREATE SET troy_brain.scope = 'agent_specific', troy_brain.created_date = datetime()
MERGE (troy)-[:HAS_MEMORY_IN]->(troy_brain);

// Wire Bob
MATCH (bob:AIAgent {name: 'Bob'})
MATCH (project:Domain {name: 'Project Management'})
MATCH (notion:System {name: 'Notion'})
MATCH (slack:System {name: 'Slack'})
MATCH (github:System {name: 'GitHub'})
MATCH (global_brain:Brain {name: 'BMAD Global Brain'})
MERGE (bob)-[:SPECIALIZES_IN]->(project)
MERGE (bob)-[:INTEGRATES_WITH]->(notion)
MERGE (bob)-[:INTEGRATES_WITH]->(slack)
MERGE (bob)-[:INTEGRATES_WITH]->(github)
MERGE (bob)-[:HAS_MEMORY_IN]->(global_brain)
MERGE (bob_brain:Brain {name: 'Bob Brain', group_id: 'global-coding-skills'})
ON CREATE SET bob_brain.scope = 'agent_specific', bob_brain.created_date = datetime()
MERGE (bob)-[:HAS_MEMORY_IN]->(bob_brain);

// Wire Allura
MATCH (allura:AIAgent {name: 'Allura'})
MATCH (ux:Domain {name: 'UX Design'})
MATCH (notion:System {name: 'Notion'})
MATCH (slack:System {name: 'Slack'})
MATCH (global_brain:Brain {name: 'BMAD Global Brain'})
MERGE (allura)-[:SPECIALIZES_IN]->(ux)
MERGE (allura)-[:INTEGRATES_WITH]->(notion)
MERGE (allura)-[:INTEGRATES_WITH]->(slack)
MERGE (allura)-[:HAS_MEMORY_IN]->(global_brain)
MERGE (allura_brain:Brain {name: 'Allura Brain', group_id: 'global-coding-skills'})
ON CREATE SET allura_brain.scope = 'agent_specific', allura_brain.created_date = datetime()
MERGE (allura)-[:HAS_MEMORY_IN]->(allura_brain);

// Wire Master
MATCH (master:AIAgent {name: 'BMad Master'})
MATCH (project:Domain {name: 'Project Management'})
MATCH (product:Domain {name: 'Product Management'})
MATCH (notion:System {name: 'Notion'})
MATCH (slack:System {name: 'Slack'})
MATCH (github:System {name: 'GitHub'})
MATCH (global_brain:Brain {name: 'BMAD Global Brain'})
MERGE (master)-[:SPECIALIZES_IN]->(project)
MERGE (master)-[:SPECIALIZES_IN]->(product)
MERGE (master)-[:INTEGRATES_WITH]->(notion)
MERGE (master)-[:INTEGRATES_WITH]->(slack)
MERGE (master)-[:INTEGRATES_WITH]->(github)
MERGE (master)-[:HAS_MEMORY_IN]->(global_brain)
MERGE (master_brain:Brain {name: 'Master Brain', group_id: 'global-coding-skills'})
ON CREATE SET master_brain.scope = 'agent_specific', master_brain.created_date = datetime()
MERGE (master)-[:HAS_MEMORY_IN]->(master_brain);

// Wire Orchestrator
MATCH (orchestrator:AIAgent {name: 'BMad Orchestrator'})
MATCH (project:Domain {name: 'Project Management'})
MATCH (neo4j:System {name: 'Neo4j'})
MATCH (github:System {name: 'GitHub'})
MATCH (notion:System {name: 'Notion'})
MATCH (slack:System {name: 'Slack'})
MATCH (global_brain:Brain {name: 'BMAD Global Brain'})
MERGE (orchestrator)-[:SPECIALIZES_IN]->(project)
MERGE (orchestrator)-[:INTEGRATES_WITH]->(neo4j)
MERGE (orchestrator)-[:INTEGRATES_WITH]->(github)
MERGE (orchestrator)-[:INTEGRATES_WITH]->(notion)
MERGE (orchestrator)-[:INTEGRATES_WITH]->(slack)
MERGE (orchestrator)-[:HAS_MEMORY_IN]->(global_brain)
MERGE (orchestrator_brain:Brain {name: 'Orchestrator Brain', group_id: 'global-coding-skills'})
ON CREATE SET orchestrator_brain.scope = 'agent_specific', orchestrator_brain.created_date = datetime()
MERGE (orchestrator)-[:HAS_MEMORY_IN]->(orchestrator_brain);

// Create collaboration relationships
MATCH (orchestrator:AIAgent {name: 'BMad Orchestrator'})
MATCH (master:AIAgent {name: 'BMad Master'})
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
MERGE (orchestrator)-[:COORDINATES]->(allura)

MERGE (master)-[:OVERSEES]->(jay)
MERGE (master)-[:OVERSEES]->(winston)
MERGE (master)-[:OVERSEES]->(brooks)
MERGE (master)-[:OVERSEES]->(dutch)
MERGE (master)-[:OVERSEES]->(troy)
MERGE (master)-[:OVERSEES]->(bob)
MERGE (master)-[:OVERSEES]->(allura)
MERGE (master)-[:OVERSEES]->(orchestrator)

MERGE (jay)-[:COLLABORATES_WITH]->(dutch)
MERGE (dutch)-[:COLLABORATES_WITH]->(winston)
MERGE (winston)-[:COLLABORATES_WITH]->(brooks)
MERGE (brooks)-[:COLLABORATES_WITH]->(troy)
MERGE (troy)-[:COLLABORATES_WITH]->(allura)

MERGE (bob)-[:TRACKS]->(jay)
MERGE (bob)-[:TRACKS]->(winston)
MERGE (bob)-[:TRACKS]->(brooks)
MERGE (bob)-[:TRACKS]->(dutch)
MERGE (bob)-[:TRACKS]->(troy)
MERGE (bob)-[:TRACKS]->(allura)
"

echo -e "\n[4/4] Validation..."
run_query "
MATCH (a:AIAgent)
OPTIONAL MATCH (a)-[r]-()
WITH a, count(r) as connections
RETURN a.name, connections
ORDER BY a.name
"

echo -e "\n✅ Synaptic hardening complete"
