"""
Process Notion MCP results and structure anchor nodes.

This script processes the results from Notion MCP tool calls
and structures them into anchor node format for Neo4j.
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Any


def extract_teamspaces_from_blocks(blocks: List[Dict]) -> List[Dict]:
    """Extract teamspace information from Hub page blocks."""
    teamspaces = []
    
    # Known teamspaces from the blocks we retrieved
    teamspace_data = [
        {
            "title": "Faith Meats",
            "description": "Premium halal beef jerky; Shopify Hydrogen migration",
            "notion_id": "21a1d9be-65b3-8016-b46e-f83c24dad63a"
        },
        {
            "title": "Patriot Awning",
            "description": "Commercial/residential awning company; Astro + Tailwind rebuild",
            "notion_id": "2871d9be-65b3-80ef-abe9-de57c2d3c731"
        },
        {
            "title": "Difference Driven",
            "description": "Nonprofit community platform; Payload CMS website development",
            "notion_id": "2741d9be-65b3-80ee-a136-d85e0f5c2e8a"
        }
    ]
    
    # Also check blocks for teamspace mentions
    for block in blocks:
        if block.get("type") == "bulleted_list_item":
            rich_text = block.get("bulleted_list_item", {}).get("rich_text", [])
            text_content = "".join([t.get("plain_text", "") for t in rich_text])
            
            # Check if this is a teamspace entry
            for ts in teamspace_data:
                if ts["title"] in text_content and "—" in text_content:
                    # Extract description if not already set
                    if "—" in text_content:
                        parts = text_content.split("—")
                        if len(parts) >= 2:
                            ts["description"] = parts[1].strip()
                    
                    # Extract notion_id from mentions
                    for text_obj in rich_text:
                        if text_obj.get("type") == "mention":
                            mention = text_obj.get("mention", {})
                            if mention.get("type") == "page":
                                ts["notion_id"] = mention["page"]["id"]
    
    return teamspace_data


def extract_databases_from_blocks(blocks: List[Dict]) -> List[Dict]:
    """Extract database information from Hub page blocks."""
    databases = []
    
    for block in blocks:
        if block.get("type") == "child_database":
            db_info = block.get("child_database", {})
            databases.append({
                "title": db_info.get("title", "Unknown Database"),
                "notion_id": block.get("id"),
                "description": ""
            })
        
        # Also check bulleted list items for database descriptions
        elif block.get("type") == "bulleted_list_item":
            rich_text = block.get("bulleted_list_item", {}).get("rich_text", [])
            text_content = "".join([t.get("plain_text", "") for t in rich_text])
            
            # Known databases with descriptions
            known_dbs = {
                "AI Agents Registry": "agent tracking and management",
                "Master Knowledge Base": "centralized documentation",
                "Master Calendar & Events": "cross-project scheduling"
            }
            
            for db_name, desc in known_dbs.items():
                if db_name in text_content and "—" in text_content:
                    # Find matching database by title
                    for db in databases:
                        if db["title"] == db_name:
                            db["description"] = desc
                            break
    
    return databases


def extract_agents_from_blocks(blocks: List[Dict]) -> List[Dict]:
    """Extract agent information from Hub page blocks."""
    agents = []
    agent_section_started = False
    
    for block in blocks:
        # Detect agent sections
        if block.get("type") == "heading_3":
            heading_text = "".join([
                t.get("plain_text", "") 
                for t in block.get("heading_3", {}).get("rich_text", [])
            ])
            if "AI agent" in heading_text.lower() or "agent" in heading_text.lower():
                agent_section_started = True
            else:
                agent_section_started = False
        
        # Extract agents from bulleted lists in agent sections
        if agent_section_started and block.get("type") == "bulleted_list_item":
            rich_text = block.get("bulleted_list_item", {}).get("rich_text", [])
            text_content = "".join([t.get("plain_text", "") for t in rich_text])
            
            if "—" in text_content:
                parts = text_content.split("—")
                if len(parts) >= 2:
                    title = parts[0].strip().replace("**", "")
                    description = parts[1].strip()
                    
                    # Determine agent type
                    agent_type = "active"
                    if "BMAD" in text_content or title in ["John", "Troy", "Sally", "BMad Builder"]:
                        agent_type = "bmad"
                    
                    agents.append({
                        "title": title,
                        "description": description,
                        "type": agent_type,
                        "notion_id": None  # Will be filled from Agents Registry
                    })
    
    return agents


def extract_tag_categories_from_blocks(blocks: List[Dict]) -> List[Dict]:
    """Extract tag category information from Hub page blocks."""
    tag_categories = []
    in_tag_section = False
    
    for block in blocks:
        if block.get("type") == "heading_3":
            heading_text = "".join([
                t.get("plain_text", "") 
                for t in block.get("heading_3", {}).get("rich_text", [])
            ])
            if "Smart tags" in heading_text:
                in_tag_section = True
            else:
                in_tag_section = False
        
        if in_tag_section and block.get("type") == "bulleted_list_item":
            rich_text = block.get("bulleted_list_item", {}).get("rich_text", [])
            text_content = "".join([t.get("plain_text", "") for t in rich_text])
            
            if ":" in text_content:
                parts = text_content.split(":", 1)
                if len(parts) == 2:
                    category_title = parts[0].strip()
                    tags_str = parts[1].strip()
                    tags = [t.strip() for t in tags_str.split(",")]
                    
                    tag_categories.append({
                        "title": category_title,
                        "tags": tags
                    })
    
    return tag_categories


def extract_knowledge_categories_from_blocks(blocks: List[Dict]) -> List[Dict]:
    """Extract knowledge base category information from Hub page blocks."""
    kb_categories = []
    in_kb_section = False
    
    for block in blocks:
        if block.get("type") == "heading_3":
            heading_text = "".join([
                t.get("plain_text", "") 
                for t in block.get("heading_3", {}).get("rich_text", [])
            ])
            if "Content categories" in heading_text or "knowledge base" in heading_text.lower():
                in_kb_section = True
            else:
                in_kb_section = False
        
        if in_kb_section and block.get("type") == "bulleted_list_item":
            rich_text = block.get("bulleted_list_item", {}).get("rich_text", [])
            text_content = "".join([t.get("plain_text", "") for t in rich_text])
            
            if text_content.strip():
                kb_categories.append({
                    "title": text_content.strip()
                })
    
    return kb_categories


def structure_anchor_nodes(
    hub_page: Dict,
    blocks: List[Dict],
    agents_from_registry: List[Dict] = None
) -> List[Dict]:
    """
    Structure all extracted data into anchor node format.
    
    Args:
        hub_page: Hub page data from MCP
        blocks: Hub page blocks from MCP
        agents_from_registry: Optional agents from Agents Registry database
        
    Returns:
        List of anchor node dictionaries
    """
    anchor_nodes = []
    
    # Extract data from blocks
    teamspaces = extract_teamspaces_from_blocks(blocks)
    databases = extract_databases_from_blocks(blocks)
    agents = extract_agents_from_blocks(blocks)
    tag_categories = extract_tag_categories_from_blocks(blocks)
    kb_categories = extract_knowledge_categories_from_blocks(blocks)
    
    # Get Hub page title
    hub_title = "".join([
        t.get("plain_text", "") 
        for t in hub_page.get("properties", {}).get("title", {}).get("title", [])
    ]) or "Ronin's Notion Hub - Master Directory & Command Center"
    
    # Create Hub anchor
    hub_anchor = {
        "id": str(uuid.uuid4()),
        "notion_id": hub_page.get("id"),
        "title": hub_title,
        "type": "Hub",
        "url": hub_page.get("url"),
        "description": "Operational hub for Sabir Asheed's Notion workspace",
        "tags": [],
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "metadata": {
            "extracted_at": datetime.utcnow().isoformat()
        }
    }
    anchor_nodes.append(hub_anchor)
    
    # Create Teamspace anchors
    for teamspace in teamspaces:
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
    for database in databases:
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
    
    # Create Agent anchors from Hub page
    for agent in agents:
        anchor = {
            "id": str(uuid.uuid4()),
            "notion_id": agent.get("notion_id"),
            "title": agent["title"],
            "type": "Agent",
            "url": f"https://www.notion.so/{agent.get('notion_id', '').replace('-', '')}" if agent.get("notion_id") else None,
            "description": agent.get("description", ""),
            "tags": [agent.get("type", "active").title()],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "metadata": {
                "agent_type": agent.get("type", "active")
            }
        }
        anchor_nodes.append(anchor)
    
    # Add agents from registry if provided
    if agents_from_registry:
        for agent_page in agents_from_registry:
            # Extract agent properties from Notion page
            props = agent_page.get("properties", {})
            name_prop = props.get("Name", {})
            title = "".join([t.get("plain_text", "") for t in name_prop.get("title", [])])
            
            if title:
                # Check if we already have this agent
                existing = any(a["title"] == title for a in anchor_nodes if a["type"] == "Agent")
                if not existing:
                    primary_function = props.get("Primary Function", {}).get("rich_text", [{}])[0].get("plain_text", "")
                    agent_type_prop = props.get("Agent Type", {}).get("select", {})
                    agent_type = agent_type_prop.get("name", "project_management") if agent_type_prop else "project_management"
                    
                    anchor = {
                        "id": str(uuid.uuid4()),
                        "notion_id": agent_page.get("id"),
                        "title": title,
                        "type": "Agent",
                        "url": agent_page.get("url"),
                        "description": primary_function or "",
                        "tags": [agent_type.title()],
                        "created_at": datetime.utcnow().isoformat(),
                        "updated_at": datetime.utcnow().isoformat(),
                        "metadata": {
                            "agent_type": agent_type,
                            "platform": props.get("Platform", {}).get("select", {}).get("name"),
                            "integration_points": [ip.get("name") for ip in props.get("Integration Points", {}).get("multi_select", [])]
                        }
                    }
                    anchor_nodes.append(anchor)
    
    # Create Tag Category anchors
    for tag_cat in tag_categories:
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
    for kb_cat in kb_categories:
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
    """Main function - this would be called with MCP results."""
    print("This script processes MCP results.")
    print("In Cursor, call this after retrieving Hub page and blocks via MCP.")


if __name__ == "__main__":
    main()



