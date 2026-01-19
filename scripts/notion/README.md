# Notion Anchor Nodes Sync

This directory contains scripts for extracting organizational anchor nodes from Ronin's Notion Hub and syncing them to Neo4j and Graphiti memory.

## Overview

Anchor nodes are high-level entry points in the knowledge graph that enable efficient graph traversal and RAG retrieval. They represent:

- **Hub**: The root Notion Hub page
- **Teamspaces**: Project workspaces (Faith Meats, Patriot Awning, Difference Driven)
- **Databases**: Central command databases (AI Agents Registry, Master Knowledge Base, etc.)
- **Agents**: AI agents (Troy Davis, Steven, Tommy Oliver, etc.)
- **Tag Categories**: Tag groupings (Technical, Programming, AI/ML, etc.)
- **Knowledge Categories**: Knowledge base categories (Archon Project, AI Learning Notes, etc.)

## Quick Start

Run the complete sync workflow:

```bash
python scripts/notion/sync_all.py
```

This will:
1. Extract anchor nodes from Notion Hub
2. Create Neo4j schema
3. Create anchor nodes in Neo4j
4. Create relationships between nodes
5. Sync to Graphiti memory

## Scripts

### `extract_anchor_nodes.py`

Extracts anchor node data from Notion Hub page structure.

**Output**: `notion_anchor_nodes.json`

**Usage**:
```bash
python scripts/notion/extract_anchor_nodes.py
```

### `create_anchor_nodes.py`

Creates anchor nodes in Neo4j from extracted JSON data.

**Prerequisites**: 
- `notion_anchor_nodes.json` must exist
- Neo4j must be running and accessible

**Usage**:
```bash
python scripts/notion/create_anchor_nodes.py
```

### `create_anchor_relationships.py`

Creates relationships between anchor nodes.

**Prerequisites**:
- Anchor nodes must exist in Neo4j
- `notion_anchor_nodes.json` must exist

**Usage**:
```bash
python scripts/notion/create_anchor_relationships.py
```

### `sync_to_graphiti.py`

Syncs anchor nodes to Graphiti memory as facts and episodes.

**Prerequisites**:
- Anchor nodes must exist in Neo4j
- `notion_anchor_nodes.json` must exist

**Usage**:
```bash
python scripts/notion/sync_to_graphiti.py
```

### `query_anchors.py`

Utility functions for querying anchor nodes.

**Usage**:
```bash
# Run as script for example queries
python scripts/notion/query_anchors.py

# Or import in Python code
from scripts.notion.query_anchors import AnchorNodeQuerier, get_all_teamspaces

# Get all teamspaces
teamspaces = get_all_teamspaces()

# Use querier class
with AnchorNodeQuerier() as querier:
    agents = querier.get_all_agents()
    hub = querier.get_hub_node()
    related = querier.get_related_anchors(hub["id"], "HAS_TEAMSPACE")
```

## Neo4j Schema

Anchor nodes use the `AnchorNode` label with the following properties:

- `id`: UUID (unique identifier)
- `notion_id`: Notion page/database ID
- `title`: Display name
- `type`: Node type (Hub, Teamspace, Database, Agent, TagCategory, KnowledgeCategory)
- `url`: Notion URL
- `description`: Optional description
- `tags`: Array of tag strings
- `created_at`: Timestamp
- `updated_at`: Timestamp
- `metadata`: JSON object for type-specific data

### Relationship Types

- `HAS_TEAMSPACE`: Hub → Teamspace
- `HAS_DATABASE`: Hub → Database
- `HAS_AGENT`: Hub → Agent
- `HAS_TAG`: Hub → TagCategory
- `HAS_CATEGORY`: Hub → KnowledgeCategory
- `BELONGS_TO`: Any anchor → Hub (reverse)
- `TAGGED_WITH`: Agent/Teamspace → TagCategory
- `MANAGED_BY`: Teamspace → Agent
- `HAS_CATEGORY`: Database → KnowledgeCategory
- `HAS_GRAPHITI_FACT`: AnchorNode → Fact (Graphiti integration)

## Graphiti Integration

Anchor nodes are synced to Graphiti memory with:

- **Group ID**: `difference-driven` (configurable via `GRAPHITI_GROUP_ID` env var)
- **Facts**: One fact per anchor node, linked via `HAS_GRAPHITI_FACT` relationship
- **Episodes**: One episode created for the sync operation

## Environment Variables

Required environment variables (in `.env` or environment):

- `NEO4J_URI`: Neo4j connection URI (default: `bolt://neo4j:7687`)
- `NEO4J_USER`: Neo4j username (default: `neo4j`)
- `NEO4J_PASSWORD`: Neo4j password (default: `changeme`)
- `GRAPHITI_GROUP_ID`: Graphiti memory group ID (default: `difference-driven`)

## Example Queries

### Get all teamspaces
```python
from scripts.notion.query_anchors import get_all_teamspaces

teamspaces = get_all_teamspaces()
for ts in teamspaces:
    print(f"{ts['title']}: {ts.get('description', '')}")
```

### Find anchor by Notion ID
```python
from scripts.notion.query_anchors import get_anchor_by_notion_id

anchor = get_anchor_by_notion_id("2661d9be-65b3-81df-8977-e88482d03583")
if anchor:
    print(f"Found: {anchor['title']}")
```

### Get related anchors
```python
from scripts.notion.query_anchors import AnchorNodeQuerier

with AnchorNodeQuerier() as querier:
    hub = querier.get_hub_node()
    if hub:
        teamspaces = querier.get_related_anchors(hub["id"], "HAS_TEAMSPACE")
        print(f"Hub has {len(teamspaces)} teamspaces")
```

### Search anchors by title
```python
from scripts.notion.query_anchors import AnchorNodeQuerier

with AnchorNodeQuerier() as querier:
    results = querier.search_anchors_by_title("Faith")
    for result in results:
        print(f"{result['title']} ({result['type']})")
```

## Troubleshooting

### "notion_anchor_nodes.json not found"

Run `extract_anchor_nodes.py` first to generate the JSON file.

### "Neo4j connection failed"

Verify Neo4j is running:
```bash
docker ps | grep neo4j
docker logs grap-neo4j
```

Check connection settings in `.env` file.

### "Schema initialization failed"

The schema is created automatically. If it fails, you can manually run:
```bash
docker exec grap-neo4j cypher-shell -u neo4j -p changeme < scripts/setup/create_anchor_schema.cypher
```

### "Graphiti facts not created"

Verify Graphiti MCP server is running:
```bash
docker ps | grep graphiti-mcp
docker logs grap-graphiti-mcp
```

Check that `GRAPHITI_GROUP_ID` is set correctly.

## Architecture

The anchor node system enables efficient RAG retrieval:

1. **Entry Point**: Start at an anchor node (e.g., "Difference Driven" teamspace)
2. **1-Hop Expansion**: Get related anchors (agents, databases, tags)
3. **2-Hop Context**: Get content linked to those anchors
4. **Graphiti Facts**: Query Graphiti memory facts linked to anchors

This structure allows AI agents to quickly navigate the knowledge graph and retrieve relevant context for queries.



