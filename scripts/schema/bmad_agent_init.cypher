// ============================================================================
// BMAD Agent Initialization - Create the 9 Core BMAD Agents
// ============================================================================
// Version: 2.0
// Date: 2026-01-25
// Updated: 2026-01-26 - Fixed variable binding issue with MATCH-based approach
// Purpose: Initialize AIAgent nodes for the BMAD framework roster
//
// NOTE: This script uses MATCH-based relationship creation because
// variable bindings don't persist across cypher-shell statements.
// ============================================================================

// ============================================================================
// CORE SYSTEMS - Define External Integration Points
// ============================================================================

MERGE (github:System {name: 'GitHub'})
ON CREATE SET
  github.type = 'version_control',
  github.version = 'Enterprise';

MERGE (notion:System {name: 'Notion'})
ON CREATE SET
  notion.type = 'documentation',
  notion.version = 'Enterprise';

MERGE (slack:System {name: 'Slack'})
ON CREATE SET
  slack.type = 'communication',
  slack.version = 'Enterprise';

MERGE (neo4j:System {name: 'Neo4j'})
ON CREATE SET
  neo4j.type = 'database',
  neo4j.version = '5.13.0';

MERGE (payload:System {name: 'Payload CMS'})
ON CREATE SET
  payload.type = 'cms',
  payload.version = '3.0';

MERGE (vercel:System {name: 'Vercel'})
ON CREATE SET
  vercel.type = 'hosting',
  vercel.version = 'Production';

// ============================================================================
// DOMAINS - Define Knowledge Areas
// ============================================================================

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

// ============================================================================
// PROJECT-SPECIFIC BRAINS - Knowledge for Each Project Group
// ============================================================================

// Faith Meats Project Brain
MERGE (faith_meats_brain:Brain {name: 'Faith Meats Brain', group_id: 'faith-meats'})
ON CREATE SET
  faith_meats_brain.scope = 'project_specific',
  faith_meats_brain.description = 'Faith Meats e-commerce platform knowledge, domain model, and implementation patterns',
  faith_meats_brain.created_date = datetime();

// Diff-Driven SaaS Project Brain
MERGE (diff_driven_brain:Brain {name: 'Diff-Driven SaaS Brain', group_id: 'diff-driven-saas'})
ON CREATE SET
  diff_driven_brain.scope = 'project_specific',
  diff_driven_brain.description = 'Diff-driven SaaS platform knowledge, state management, and collaboration patterns',
  diff_driven_brain.created_date = datetime();

// Global Coding Skills Brain (for cross-project patterns)
MERGE (coding_skills_brain:Brain {name: 'Coding Skills Brain', group_id: 'global-coding-skills'})
ON CREATE SET
  coding_skills_brain.scope = 'project_specific',
  coding_skills_brain.description = 'Universal coding patterns, best practices, and development workflows',
  coding_skills_brain.created_date = datetime();

// ============================================================================
// GLOBAL BRAIN - Shared Knowledge Across All Agents
// ============================================================================

MERGE (global_brain:Brain {name: 'BMAD Global Brain', group_id: 'global-coding-skills'})
ON CREATE SET
  global_brain.scope = 'global',
  global_brain.description = 'BMAD framework workflows, agent coordination, and system-level knowledge',
  global_brain.created_date = datetime();

// ============================================================================
// AGENT 1: JAY - Business Analyst
// ============================================================================

MERGE (jay:AIAgent {name: 'Jay'})
ON CREATE SET
  jay.role = 'Analyst',
  jay.file_reference = 'analyst.md',
  jay.capabilities = ['requirements_analysis', 'user_story_creation', 'stakeholder_interviews', 'business_logic_modeling'],
  jay.integration_points = ['Notion', 'Slack'],
  jay.created_date = datetime(),
  jay.status = 'active';

MERGE (jay)-[:SPECIALIZES_IN]->(analysis);
MERGE (jay)-[:INTEGRATES_WITH]->(notion);
MERGE (jay)-[:INTEGRATES_WITH]->(slack);
MERGE (jay)-[:HAS_MEMORY_IN]->(global_brain);

// Create Jay's personal brain
MERGE (jay_brain:Brain {name: 'Jay Brain', group_id: 'global-coding-skills'})
ON CREATE SET
  jay_brain.scope = 'agent_specific',
  jay_brain.created_date = datetime();
MERGE (jay)-[:HAS_MEMORY_IN]->(jay_brain);

// ============================================================================
// AGENT 2: WINSTON - Architect
// ============================================================================

MERGE (winston:AIAgent {name: 'Winston'})
ON CREATE SET
  winston.role = 'Architect',
  winston.file_reference = 'architect.md',
  winston.capabilities = ['architecture_design', 'technology_selection', 'system_migrations', 'performance_optimization', 'api_design'],
  winston.integration_points = ['GitHub', 'Notion'],
  winston.created_date = datetime(),
  winston.status = 'active';

MERGE (winston)-[:SPECIALIZES_IN]->(architecture);
MERGE (winston)-[:INTEGRATES_WITH]->(github);
MERGE (winston)-[:INTEGRATES_WITH]->(notion);
MERGE (winston)-[:HAS_MEMORY_IN]->(global_brain);

MERGE (winston_brain:Brain {name: 'Winston Brain', group_id: 'global-coding-skills'})
ON CREATE SET
  winston_brain.scope = 'agent_specific',
  winston_brain.created_date = datetime();
MERGE (winston)-[:HAS_MEMORY_IN]->(winston_brain);

// ============================================================================
// AGENT 3: BROOKS - Developer
// ============================================================================

MERGE (brooks:AIAgent {name: 'Brooks'})
ON CREATE SET
  brooks.role = 'Developer',
  brooks.file_reference = 'dev.md',
  brooks.capabilities = ['code_implementation', 'debugging', 'refactoring', 'code_review', 'git_operations'],
  brooks.integration_points = ['GitHub', 'Slack'],
  brooks.created_date = datetime(),
  brooks.status = 'active';

MERGE (brooks)-[:SPECIALIZES_IN]->(coding);
MERGE (brooks)-[:INTEGRATES_WITH]->(github);
MERGE (brooks)-[:INTEGRATES_WITH]->(slack);
MERGE (brooks)-[:HAS_MEMORY_IN]->(global_brain);

MERGE (brooks_brain:Brain {name: 'Brooks Brain', group_id: 'global-coding-skills'})
ON CREATE SET
  brooks_brain.scope = 'agent_specific',
  brooks_brain.created_date = datetime();
MERGE (brooks)-[:HAS_MEMORY_IN]->(brooks_brain);

// ============================================================================
// AGENT 4: DUTCH - Product Manager
// ============================================================================

MERGE (dutch:AIAgent {name: 'Dutch'})
ON CREATE SET
  dutch.role = 'PM',
  dutch.file_reference = 'pm.md',
  dutch.capabilities = ['prd_creation', 'roadmap_planning', 'feature_prioritization', 'stakeholder_communication'],
  dutch.integration_points = ['Notion', 'Slack'],
  dutch.created_date = datetime(),
  dutch.status = 'active';

MERGE (dutch)-[:SPECIALIZES_IN]->(product);
MERGE (dutch)-[:INTEGRATES_WITH]->(notion);
MERGE (dutch)-[:INTEGRATES_WITH]->(slack);
MERGE (dutch)-[:HAS_MEMORY_IN]->(global_brain);

MERGE (dutch_brain:Brain {name: 'Dutch Brain', group_id: 'global-coding-skills'})
ON CREATE SET
  dutch_brain.scope = 'agent_specific',
  dutch_brain.created_date = datetime();
MERGE (dutch)-[:HAS_MEMORY_IN]->(dutch_brain);

// ============================================================================
// AGENT 5: TROY - Test Engineer & Analyst (TEA)
// ============================================================================

MERGE (troy:AIAgent {name: 'Troy'})
ON CREATE SET
  troy.role = 'TEA',
  troy.file_reference = 'tea.md',
  troy.capabilities = ['test_automation', 'quality_assurance', 'documentation', 'bug_tracking', 'performance_testing'],
  troy.integration_points = ['GitHub', 'Notion'],
  troy.created_date = datetime(),
  troy.status = 'active';

MERGE (troy)-[:SPECIALIZES_IN]->(testing);
MERGE (troy)-[:INTEGRATES_WITH]->(github);
MERGE (troy)-[:INTEGRATES_WITH]->(notion);
MERGE (troy)-[:HAS_MEMORY_IN]->(global_brain);

MERGE (troy_brain:Brain {name: 'Troy Brain', group_id: 'global-coding-skills'})
ON CREATE SET
  troy_brain.scope = 'agent_specific',
  troy_brain.created_date = datetime();
MERGE (troy)-[:HAS_MEMORY_IN]->(troy_brain);

// ============================================================================
// AGENT 6: BOB - Scrum Master
// ============================================================================

MERGE (bob:AIAgent {name: 'Bob'})
ON CREATE SET
  bob.role = 'Scrum Master',
  bob.file_reference = 'sm.md',
  bob.capabilities = ['sprint_planning', 'task_tracking', 'team_coordination', 'progress_monitoring', 'blocker_resolution'],
  bob.integration_points = ['Notion', 'Slack', 'GitHub'],
  bob.created_date = datetime(),
  bob.status = 'active';

MERGE (bob)-[:SPECIALIZES_IN]->(project);
MERGE (bob)-[:INTEGRATES_WITH]->(notion);
MERGE (bob)-[:INTEGRATES_WITH]->(slack);
MERGE (bob)-[:INTEGRATES_WITH]->(github);
MERGE (bob)-[:HAS_MEMORY_IN]->(global_brain);

MERGE (bob_brain:Brain {name: 'Bob Brain', group_id: 'global-coding-skills'})
ON CREATE SET
  bob_brain.scope = 'agent_specific',
  bob_brain.created_date = datetime();
MERGE (bob)-[:HAS_MEMORY_IN]->(bob_brain);

// ============================================================================
// AGENT 7: ALLURA - UX Expert
// ============================================================================

MERGE (allura:AIAgent {name: 'Allura'})
ON CREATE SET
  allura.role = 'UX Expert',
  allura.file_reference = 'ux-expert.md',
  allura.capabilities = ['ux_design', 'usability_review', 'interface_design', 'user_research', 'accessibility_audit'],
  allura.integration_points = ['Notion', 'Slack'],
  allura.created_date = datetime(),
  allura.status = 'active';

MERGE (allura)-[:SPECIALIZES_IN]->(ux);
MERGE (allura)-[:INTEGRATES_WITH]->(notion);
MERGE (allura)-[:INTEGRATES_WITH]->(slack);
MERGE (allura)-[:HAS_MEMORY_IN]->(global_brain);

MERGE (allura_brain:Brain {name: 'Allura Brain', group_id: 'global-coding-skills'})
ON CREATE SET
  allura_brain.scope = 'agent_specific',
  allura_brain.created_date = datetime();
MERGE (allura)-[:HAS_MEMORY_IN]->(allura_brain);

// ============================================================================
// AGENT 8: BMAD MASTER - Master Coordinator
// ============================================================================

MERGE (master:AIAgent {name: 'BMad Master'})
ON CREATE SET
  master.role = 'Master',
  master.file_reference = 'master.md',
  master.capabilities = ['project_oversight', 'strategic_planning', 'quality_gate_review', 'cross_team_coordination'],
  master.integration_points = ['Notion', 'Slack', 'GitHub'],
  master.created_date = datetime(),
  master.status = 'active';

MERGE (master)-[:SPECIALIZES_IN]->(project);
MERGE (master)-[:SPECIALIZES_IN]->(product);
MERGE (master)-[:INTEGRATES_WITH]->(notion);
MERGE (master)-[:INTEGRATES_WITH]->(slack);
MERGE (master)-[:INTEGRATES_WITH]->(github);
MERGE (master)-[:HAS_MEMORY_IN]->(global_brain);

MERGE (master_brain:Brain {name: 'Master Brain', group_id: 'global-coding-skills'})
ON CREATE SET
  master_brain.scope = 'agent_specific',
  master_brain.created_date = datetime();
MERGE (master)-[:HAS_MEMORY_IN]->(master_brain);

// ============================================================================
// AGENT 9: BMAD ORCHESTRATOR - Workflow Orchestrator
// ============================================================================

MERGE (orchestrator:AIAgent {name: 'BMad Orchestrator'})
ON CREATE SET
  orchestrator.role = 'Orchestrator',
  orchestrator.file_reference = 'orchestrator.md',
  orchestrator.capabilities = ['workflow_coordination', 'agent_assignment', 'task_routing', 'process_automation'],
  orchestrator.integration_points = ['Neo4j', 'GitHub', 'Notion', 'Slack'],
  orchestrator.created_date = datetime(),
  orchestrator.status = 'active';

MERGE (orchestrator)-[:SPECIALIZES_IN]->(project);
MERGE (orchestrator)-[:INTEGRATES_WITH]->(neo4j);
MERGE (orchestrator)-[:INTEGRATES_WITH]->(github);
MERGE (orchestrator)-[:INTEGRATES_WITH]->(notion);
MERGE (orchestrator)-[:INTEGRATES_WITH]->(slack);
MERGE (orchestrator)-[:HAS_MEMORY_IN]->(global_brain);

MERGE (orchestrator_brain:Brain {name: 'Orchestrator Brain', group_id: 'global-coding-skills'})
ON CREATE SET
  orchestrator_brain.scope = 'agent_specific',
  orchestrator_brain.created_date = datetime();
MERGE (orchestrator)-[:HAS_MEMORY_IN]->(orchestrator_brain);

// ============================================================================
// AGENT COLLABORATION RELATIONSHIPS
// ============================================================================

// Orchestrator coordinates all agents
MERGE (orchestrator)-[:COORDINATES]->(jay);
MERGE (orchestrator)-[:COORDINATES]->(winston);
MERGE (orchestrator)-[:COORDINATES]->(brooks);
MERGE (orchestrator)-[:COORDINATES]->(dutch);
MERGE (orchestrator)-[:COORDINATES]->(troy);
MERGE (orchestrator)-[:COORDINATES]->(bob);
MERGE (orchestrator)-[:COORDINATES]->(allura);

// Master oversees all agents
MERGE (master)-[:OVERSEES]->(jay);
MERGE (master)-[:OVERSEES]->(winston);
MERGE (master)-[:OVERSEES]->(brooks);
MERGE (master)-[:OVERSEES]->(dutch);
MERGE (master)-[:OVERSEES]->(troy);
MERGE (master)-[:OVERSEES]->(bob);
MERGE (master)-[:OVERSEES]->(allura);
MERGE (master)-[:OVERSEES]->(orchestrator);

// Planning phase collaborations
MERGE (jay)-[:COLLABORATES_WITH]->(dutch);
MERGE (dutch)-[:COLLABORATES_WITH]->(winston);
MERGE (winston)-[:COLLABORATES_WITH]->(brooks);

// Development phase collaborations
MERGE (brooks)-[:COLLABORATES_WITH]->(troy);
MERGE (troy)-[:COLLABORATES_WITH]->(allura);

// Coordination collaborations
MERGE (bob)-[:TRACKS]->(jay);
MERGE (bob)-[:TRACKS]->(winston);
MERGE (bob)-[:TRACKS]->(brooks);
MERGE (bob)-[:TRACKS]->(dutch);
MERGE (bob)-[:TRACKS]->(troy);
MERGE (bob)-[:TRACKS]->(allura);

// ============================================================================
// VALIDATION QUERY
// ============================================================================
// Run this to verify all agents were created:
// MATCH (a:AIAgent) RETURN a.name, a.role, a.capabilities, a.status ORDER BY a.name
// Expected: 9 agents with unique names and roles

// ============================================================================
// END OF AGENT INITIALIZATION
// ============================================================================