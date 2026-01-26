// AIAgent Constraints
CREATE CONSTRAINT agent_name_unique IF NOT EXISTS FOR (a:AIAgent) REQUIRE a.name IS UNIQUE;

// Work Execution Layer Constraints
CREATE CONSTRAINT project_name_groupid_unique IF NOT EXISTS FOR (p:Project) REQUIRE (p.name, p.group_id) IS UNIQUE;

// Knowledge Layer Constraints
CREATE CONSTRAINT brain_name_groupid_unique IF NOT EXISTS FOR (b:Brain) REQUIRE (b.name, b.group_id) IS UNIQUE;

// Infrastructure Constraints
CREATE CONSTRAINT system_name_unique IF NOT EXISTS FOR (s:System) REQUIRE s.name IS UNIQUE;

// Performance Indexes
CREATE INDEX agent_role IF NOT EXISTS FOR (a:AIAgent) ON (a.role);
CREATE INDEX brain_scope IF NOT EXISTS FOR (b:Brain) ON (b.scope);
CREATE INDEX event_timestamp IF NOT EXISTS FOR (e:Event) ON (e.timestamp);
CREATE INDEX group_id_idx IF NOT EXISTS FOR (n) ON (n.group_id);
