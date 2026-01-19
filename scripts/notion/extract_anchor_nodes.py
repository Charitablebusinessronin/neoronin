"""
Extract anchor nodes from Ronin's Notion Hub Master Directory.

This script connects to Notion via MCP and extracts all organizational
entities (teamspaces, databases, agents, tags, categories) to create
anchor nodes in Neo4j for efficient graph traversal.
"""

import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid


# Hub page ID from the Notion URL
HUB_PAGE_ID = "2661d9be-65b3-81df-8977-e88482d03583"

# Database IDs from the Hub page
AI_AGENTS_REGISTRY_DB_ID = "62baeeb2-8b17-436d-a92b-314128fb93cb"
MASTER_KNOWLEDGE_BASE_DB_ID = "e5d3db1e-1290-4d33-bd1f-71f93cc36655"


def extract_hub_structure(notion_blocks: List[Dict]) -> Dict[str, Any]:
    """
    Extract organizational structure from Hub page blocks.
    
    Args:
        notion_blocks: List of block objects from Notion API
        
    Returns:
        Dictionary containing extracted entities organized by type
    """
    structure = {
        "teamspaces": [],
        "databases": [],
        "agents": [],
        "tag_categories": [],
        "knowledge_categories": [],
        "metadata": {}
    }
    
    # Known teamspaces from Hub page
    teamspaces_data = [
        {
            "title": "Faith Meats",
            "description": "Premium halal beef jerky; Shopify Hydrogen migration",
            "notion_id": "21a1d9be-65b3-8016-b46e-f83c24dad63a"  # From quick links
        },
        {
            "title": "Patriot Awning",
            "description": "Commercial/residential awning company; Astro + Tailwind rebuild",
            "notion_id": "2871d9be-65b3-80ef-abe9-de57c2d3c731"  # From quick links
        },
        {
            "title": "Difference Driven",
            "description": "Nonprofit community platform; Payload CMS website development",
            "notion_id": "2741d9be-65b3-80ee-a136-d85e0f5c2e8a"  # From quick links
        }
    ]
    
    # Known databases from Hub page
    databases_data = [
        {
            "title": "AI Agents Registry",
            "description": "Agent tracking and management",
            "notion_id": AI_AGENTS_REGISTRY_DB_ID
        },
        {
            "title": "Master Knowledge Base",
            "description": "Centralized documentation",
            "notion_id": MASTER_KNOWLEDGE_BASE_DB_ID
        },
        {
            "title": "Master Calendar & Events",
            "description": "Cross-project scheduling",
            "notion_id": None  # Not found in blocks, may need to query
        },
        {
            "title": "Prompt Database",
            "description": "Prompt templates and definitions",
            "notion_id": "2a11d9be-65b3-8055-909b-fc277d4f47ed"  # From blocks
        },
        {
            "title": "Agent activation prompt",
            "description": "Agent activation prompts",
            "notion_id": "2c11d9be-65b3-80f8-868c-c1b5d896342b"  # From blocks
        }
    ]
    
    # Known active agents from Hub page
    active_agents_data = [
        {
            "title": "Troy Davis",
            "description": "General Coding Agent (Spec-Kit SDD workflows across projects)",
            "type": "active"
        },
        {
            "title": "Steven",
            "description": "DD Product Manager (SpecKit oversight, constitution compliance, spec/plan reviews)",
            "type": "active"
        },
        {
            "title": "Tommy Oliver",
            "description": "Agent Builder & Workflow Architect (BMAD-compliant agent/workflow design)",
            "type": "active"
        },
        {
            "title": "Ari Khalid",
            "description": "Investigative Researcher (primary-source hunting, decision-ready briefs)",
            "type": "active"
        }
    ]
    
    # BMAD team agents
    bmad_agents_data = [
        {
            "title": "John",
            "description": "Product Manager (PRD creation, epics & stories)",
            "type": "bmad"
        },
        {
            "title": "Troy",
            "description": "Developer Agent (code implementation)",
            "type": "bmad"
        },
        {
            "title": "Sally",
            "description": "UX Designer (design collaboration)",
            "type": "bmad"
        },
        {
            "title": "BMad Builder",
            "description": "Agent/workflow creation and maintenance",
            "type": "bmad"
        }
    ]
    
    # Tag categories from Hub page
    tag_categories_data = [
        {"title": "Technical", "tags": ["Vercel", "Docker", "API", "Database", "Authentication", "Infrastructure"]},
        {"title": "Programming", "tags": ["Python", "JavaScript", "TypeScript", "React", "Next.js"]},
        {"title": "AI/ML", "tags": ["LLM", "RAG", "Embeddings", "Vector Search", "Claude", "Archon"]},
        {"title": "Business", "tags": ["Sales", "CRM", "Pricing", "Healthcare", "Halal Food"]},
        {"title": "Projects", "tags": ["Faith Meats", "Snug Kisses", "Dam Restoration", "Difference Driven"]},
        {"title": "Content", "tags": ["Documentation", "Guide", "Tutorial", "Template", "Reference"]},
        {"title": "Status", "tags": ["Urgent", "Completed", "In Progress", "Needs Review"]},
        {"title": "Access", "tags": ["Public", "Internal", "Example", "Backup"]}
    ]
    
    # Knowledge base categories from Hub page
    knowledge_categories_data = [
        {"title": "Archon Project"},
        {"title": "AI Learning Notes"},
        {"title": "RAG"},
        {"title": "Coding & Development"},
        {"title": "Faith Meats"},
        {"title": "Project Management"},
        {"title": "Research & Discovery"},
        {"title": "Team Knowledge"}
    ]
    
    structure["teamspaces"] = teamspaces_data
    structure["databases"] = databases_data
    structure["agents"] = active_agents_data + bmad_agents_data
    structure["tag_categories"] = tag_categories_data
    structure["knowledge_categories"] = knowledge_categories_data
    
    # Extract metadata from Hub page
    structure["metadata"] = {
        "hub_page_id": HUB_PAGE_ID,
        "hub_title": "Ronin's Notion Hub - Master Directory & Command Center",
        "hub_url": f"https://www.notion.so/Ronin-s-Notion-Hub-Master-Directory-Command-Center-{HUB_PAGE_ID.replace('-', '')}",
        "extracted_at": datetime.utcnow().isoformat(),
        "description": "Operational hub for Sabir Asheed's Notion workspace"
    }
    
    return structure


def query_agents_registry() -> List[Dict[str, Any]]:
    """
    Query AI Agents Registry database for all agent entries.
    
    Note: This would use Notion MCP API in production.
    For now, returns known agents from Hub page analysis.
    
    Returns:
        List of agent dictionaries with full metadata
    """
    # Known agents from previous analysis
    agents = [
        {
            "title": "Frederick P. Brooks Jr.",
            "notion_id": "2cf1d9be-65b3-80d1-9a7e-c9703c22a693",
            "description": "Turing Award-winning computer architect, software engineer",
            "type": "project_management",
            "platform": "GPT-4",
            "integration_points": ["Notion", "Graphiti", "Neo4j"]
        }
    ]
    
    return agents


def structure_anchor_nodes(extracted_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Structure extracted data into anchor node format.
    
    Args:
        extracted_data: Dictionary from extract_hub_structure()
        
    Returns:
        List of anchor node dictionaries ready for Neo4j creation
    """
    anchor_nodes = []
    
    # Create Hub anchor
    hub_anchor = {
        "id": str(uuid.uuid4()),
        "notion_id": extracted_data["metadata"]["hub_page_id"],
        "title": extracted_data["metadata"]["hub_title"],
        "type": "Hub",
        "url": extracted_data["metadata"]["hub_url"],
        "description": extracted_data["metadata"]["description"],
        "tags": [],
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "metadata": {
            "extracted_at": extracted_data["metadata"]["extracted_at"]
        }
    }
    anchor_nodes.append(hub_anchor)
    
    # Create Teamspace anchors
    for teamspace in extracted_data["teamspaces"]:
        anchor = {
            "id": str(uuid.uuid4()),
            "notion_id": teamspace.get("notion_id"),
            "title": teamspace["title"],
            "type": "Teamspace",
            "url": f"https://www.notion.so/{teamspace.get('notion_id', '').replace('-', '')}" if teamspace.get("notion_id") else None,
            "description": teamspace.get("description", ""),
            "tags": ["Projects"],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "metadata": {}
        }
        anchor_nodes.append(anchor)
    
    # Create Database anchors
    for database in extracted_data["databases"]:
        anchor = {
            "id": str(uuid.uuid4()),
            "notion_id": database.get("notion_id"),
            "title": database["title"],
            "type": "Database",
            "url": f"https://www.notion.so/{database.get('notion_id', '').replace('-', '')}" if database.get("notion_id") else None,
            "description": database.get("description", ""),
            "tags": ["Databases"],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "metadata": {}
        }
        anchor_nodes.append(anchor)
    
    # Create Agent anchors
    for agent in extracted_data["agents"]:
        anchor = {
            "id": str(uuid.uuid4()),
            "notion_id": None,  # Will be populated from Agents Registry query
            "title": agent["title"],
            "type": "Agent",
            "url": None,
            "description": agent.get("description", ""),
            "tags": [agent.get("type", "active").title()],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "metadata": {
                "agent_type": agent.get("type", "active")
            }
        }
        anchor_nodes.append(anchor)
    
    # Add agents from registry query
    registry_agents = query_agents_registry()
    for agent in registry_agents:
        anchor = {
            "id": str(uuid.uuid4()),
            "notion_id": agent.get("notion_id"),
            "title": agent["title"],
            "type": "Agent",
            "url": f"https://www.notion.so/{agent.get('notion_id', '').replace('-', '')}" if agent.get("notion_id") else None,
            "description": agent.get("description", ""),
            "tags": [agent.get("type", "project_management").title()],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "metadata": {
                "agent_type": agent.get("type", "project_management"),
                "platform": agent.get("platform"),
                "integration_points": agent.get("integration_points", [])
            }
        }
        anchor_nodes.append(anchor)
    
    # Create Tag Category anchors
    for tag_cat in extracted_data["tag_categories"]:
        anchor = {
            "id": str(uuid.uuid4()),
            "notion_id": None,
            "title": tag_cat["title"],
            "type": "TagCategory",
            "url": None,
            "description": f"Tag category: {', '.join(tag_cat.get('tags', []))}",
            "tags": [],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "metadata": {
                "tags": tag_cat.get("tags", [])
            }
        }
        anchor_nodes.append(anchor)
    
    # Create Knowledge Category anchors
    for kb_cat in extracted_data["knowledge_categories"]:
        anchor = {
            "id": str(uuid.uuid4()),
            "notion_id": None,
            "title": kb_cat["title"],
            "type": "KnowledgeCategory",
            "url": None,
            "description": f"Knowledge base category: {kb_cat['title']}",
            "tags": ["Knowledge Base"],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "metadata": {}
        }
        anchor_nodes.append(anchor)
    
    return anchor_nodes


def main():
    """
    Main extraction function.
    
    This would normally use Notion MCP API, but for now uses
    hardcoded data from Hub page analysis.
    """
    print("Extracting anchor nodes from Notion Hub...")
    
    # In production, this would fetch blocks from Notion API
    # For now, we use the structure we know from the Hub page
    extracted_data = extract_hub_structure([])
    
    # Structure into anchor nodes
    anchor_nodes = structure_anchor_nodes(extracted_data)
    
    # Output results
    output_file = "notion_anchor_nodes.json"
    with open(output_file, "w") as f:
        json.dump(anchor_nodes, f, indent=2)
    
    print(f"Extracted {len(anchor_nodes)} anchor nodes")
    print(f"Results saved to {output_file}")
    
    # Print summary
    by_type = {}
    for node in anchor_nodes:
        node_type = node["type"]
        by_type[node_type] = by_type.get(node_type, 0) + 1
    
    print("\nAnchor nodes by type:")
    for node_type, count in sorted(by_type.items()):
        print(f"  {node_type}: {count}")
    
    return anchor_nodes


if __name__ == "__main__":
    main()



