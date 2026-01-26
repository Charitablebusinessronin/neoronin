// ============================================================================
// BMAD Project Group Initialization
// Creates Project nodes with group_id for multi-tenant isolation
// ============================================================================

// Faith Meats Project
MERGE (faith_meats:Project {name: 'Faith Meats', group_id: 'faith-meats'})
ON CREATE SET
  faith_meats.description = 'E-commerce platform for faith-based meat products',
  faith_meats.scope = 'project_specific',
  faith_meats.status = 'active',
  faith_meats.created_date = datetime();

// Create Project-specific Brain
MERGE (faith_meats_brain:Brain {name: 'Faith Meats Brain', group_id: 'faith-meats'})
ON CREATE SET
  faith_meats_brain.scope = 'project_specific',
  faith_meats_brain.memory_retention_days = 90;

// Diff-Driven SaaS Project
MERGE (diff_saas:Project {name: 'Diff-Driven SaaS', group_id: 'diff-driven-saas'})
ON CREATE SET
  diff_saas.description = 'SaaS platform for difference-driven development tools',
  diff_saas.scope = 'project_specific',
  diff_saas.status = 'active',
  diff_saas.created_date = datetime();

// Create Project-specific Brain
MERGE (diff_saas_brain:Brain {name: 'Diff-Driven SaaS Brain', group_id: 'diff-driven-saas'})
ON CREATE SET
  diff_saas_brain.scope = 'project_specific',
  diff_saas_brain.memory_retention_days = 90;

// Global Coding Skills (cross-project)
MERGE (global_skills:Project {name: 'Global Coding Skills', group_id: 'global-coding-skills'})
ON CREATE SET
  global_skills.description = 'Cross-project universal patterns and best practices',
  global_skills.scope = 'global',
  global_skills.status = 'active',
  global_skills.created_date = datetime();

// Link project brains to existing global brain (using MATCH instead of MERGE)
MATCH (global_brain:Brain {name: 'BMAD Global Brain', group_id: 'global-coding-skills'})
MATCH (faith_meats_brain:Brain {name: 'Faith Meats Brain', group_id: 'faith-meats'})
MATCH (diff_saas_brain:Brain {name: 'Diff-Driven SaaS Brain', group_id: 'diff-driven-saas'})
MERGE (faith_meats_brain)-[:PART_OF]->(global_brain)
MERGE (diff_saas_brain)-[:PART_OF]->(global_brain);

// ============================================================================
// VALIDATION QUERY
// ============================================================================
// Run this to verify all project groups:
// MATCH (p:Project) RETURN p.name, p.group_id, p.scope ORDER BY p.group_id
// Expected: 3 projects with unique group_ids

// ============================================================================
// END OF PROJECT GROUPS INIT
// ============================================================================