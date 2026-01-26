// Ensure Systems exist
MERGE (:System {name: 'GitHub', type: 'version_control', version: 'Enterprise'});
MERGE (:System {name: 'Notion', type: 'documentation', version: 'Enterprise'});
MERGE (:System {name: 'Slack', type: 'communication', version: 'Enterprise'});
MERGE (:System {name: 'Neo4j', type: 'database', version: '5.13.0'});

// Core AIAgent Roster
MERGE (jay:AIAgent {name: 'Jay'}) ON CREATE SET jay.role = 'Analyst';
MERGE (winston:AIAgent {name: 'Winston'}) ON CREATE SET winston.role = 'Architect';
MERGE (brooks:AIAgent {name: 'Brooks'}) ON CREATE SET brooks.role = 'Developer';
MERGE (dutch:AIAgent {name: 'Dutch'}) ON CREATE SET dutch.role = 'PM';
MERGE (troy:AIAgent {name: 'Troy'}) ON CREATE SET troy.role = 'TEA';
MERGE (bob:AIAgent {name: 'Bob'}) ON CREATE SET bob.role = 'Scrum Master';
MERGE (allura:AIAgent {name: 'Allura'}) ON CREATE SET allura.role = 'UX Expert';
MERGE (master:AIAgent {name: 'BMad Master'}) ON CREATE SET master.role = 'Master';
MERGE (orchestrator:AIAgent {name: 'BMad Orchestrator'}) ON CREATE SET orchestrator.role = 'Orchestrator';

// Brain Infrastructure
MERGE (global:Brain {name: 'BMAD Global Brain', group_id: 'global-coding-skills'}) ON CREATE SET global.scope = 'global';

// Sample Personal Brain Wiring
MATCH (master:AIAgent {name: 'BMad Master'})
MERGE (master_brain:Brain {name: 'Master Brain', group_id: 'global-coding-skills'}) ON CREATE SET master_brain.scope = 'agent_specific'
MERGE (master)-[:HAS_MEMORY_IN]->(master_brain)
MERGE (master)-[:HAS_MEMORY_IN]->(global);
