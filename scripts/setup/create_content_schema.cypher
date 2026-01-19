// Neo4j Schema for Content Chunks and Sources
// This script creates constraints and indexes for efficient content chunk queries

// ContentSource Node Constraints
CREATE CONSTRAINT content_source_id IF NOT EXISTS
FOR (n:ContentSource) REQUIRE n.id IS UNIQUE;

CREATE INDEX content_source_notion_id IF NOT EXISTS
FOR (n:ContentSource) ON (n.notion_id);

CREATE INDEX content_source_type IF NOT EXISTS
FOR (n:ContentSource) ON (n.source_type);

// ContentChunk Node Constraints
CREATE CONSTRAINT content_chunk_id IF NOT EXISTS
FOR (n:ContentChunk) REQUIRE n.id IS UNIQUE;

CREATE INDEX content_chunk_source IF NOT EXISTS
FOR (n:ContentChunk) ON (n.notion_source_id);

CREATE INDEX content_chunk_type IF NOT EXISTS
FOR (n:ContentChunk) ON (n.content_type);

CREATE INDEX content_chunk_index IF NOT EXISTS
FOR (n:ContentChunk) ON (n.chunk_index);

// Full-text index for semantic search
CREATE FULLTEXT INDEX content_chunk_text IF NOT EXISTS
FOR (n:ContentChunk) ON EACH [n.content];

// Relationship types used:
// :HAS_CONTENT - AnchorNode → ContentSource
// :CONTAINS_CHUNK - ContentSource → ContentChunk
// :NEXT_CHUNK - ContentChunk → ContentChunk (sequential)
// :PARENT_CHUNK - ContentChunk → ContentChunk (hierarchical)
// :RELATED_TO - ContentChunk → ContentChunk (semantic)
// :FROM_ANCHOR - ContentChunk → AnchorNode (direct link)

// Note: Neo4j doesn't require explicit relationship type creation
// Relationships are created when nodes are connected



