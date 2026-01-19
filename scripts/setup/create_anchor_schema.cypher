// Neo4j Schema for Anchor Nodes
// This script creates constraints and indexes for efficient anchor node queries

// Anchor Node ID constraint (unique identifier)
CREATE CONSTRAINT anchor_node_id IF NOT EXISTS
FOR (n:AnchorNode) REQUIRE n.id IS UNIQUE;

// Index on anchor node type for filtering by type
CREATE INDEX anchor_node_type IF NOT EXISTS
FOR (n:AnchorNode) ON (n.type);

// Index on Notion ID for fast lookups from Notion
CREATE INDEX anchor_node_notion_id IF NOT EXISTS
FOR (n:AnchorNode) ON (n.notion_id);

// Index on title for text search
CREATE INDEX anchor_node_title IF NOT EXISTS
FOR (n:AnchorNode) ON (n.title);

// Relationship types used:
// :HAS_TEAMSPACE - Hub -> Teamspace
// :HAS_DATABASE - Hub -> Database
// :HAS_AGENT - Hub -> Agent
// :HAS_TAG - Hub -> TagCategory
// :HAS_CATEGORY - Hub -> KnowledgeCategory
// :BELONGS_TO - Any anchor -> Hub (reverse relationship)
// :TAGGED_WITH - Agent/Teamspace -> TagCategory
// :MANAGED_BY - Teamspace -> Agent
// :HAS_CATEGORY - Database -> KnowledgeCategory
// :CONTAINS - Database -> Agent (for AI Agents Registry)

// Note: Neo4j doesn't require explicit relationship type creation
// Relationships are created when nodes are connected



