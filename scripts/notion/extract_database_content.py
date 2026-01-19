"""
Extract full content from Notion databases.

This script uses Notion MCP tools to query databases and extract
all entries with all their properties for RAG content extraction.
"""

import json
import os
import sys
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid

# Database IDs from anchor nodes
DATABASES = {
    "AI Agents Registry": "62baeeb2-8b17-436d-a92b-314128fb93cb",
    "Master Knowledge Base": "e5d3db1e-1290-4d33-bd1f-71f93cc36655",
    "Prompt Database": "2a11d9be-65b3-8055-909b-fc277d4f47ed",
    "Agent activation prompt": "2c11d9be-65b3-80f8-868c-c1b5d896342b"
}


def extract_property_value(property_obj: Dict) -> Any:
    """
    Extract value from a Notion property object.
    
    Handles different property types:
    - title, rich_text: Extract plain text
    - select, multi_select: Extract names
    - number: Extract number value
    - date: Extract date range
    - checkbox: Extract boolean
    - url, email, phone_number: Extract string
    - relation: Extract related page IDs
    - etc.
    """
    prop_type = property_obj.get("type")
    
    if prop_type == "title" or prop_type == "rich_text":
        rich_text = property_obj.get(prop_type, [])
        return "".join([t.get("plain_text", "") for t in rich_text])
    
    elif prop_type == "select":
        select_obj = property_obj.get("select")
        return select_obj.get("name") if select_obj else None
    
    elif prop_type == "multi_select":
        multi_select = property_obj.get("multi_select", [])
        return [item.get("name") for item in multi_select]
    
    elif prop_type == "number":
        return property_obj.get("number")
    
    elif prop_type == "checkbox":
        return property_obj.get("checkbox", False)
    
    elif prop_type == "date":
        date_obj = property_obj.get("date")
        if date_obj:
            return {
                "start": date_obj.get("start"),
                "end": date_obj.get("end")
            }
        return None
    
    elif prop_type in ["url", "email", "phone_number"]:
        return property_obj.get(prop_type)
    
    elif prop_type == "relation":
        relation = property_obj.get("relation", [])
        return [item.get("id") for item in relation]
    
    elif prop_type == "created_time":
        return property_obj.get("created_time")
    
    elif prop_type == "last_edited_time":
        return property_obj.get("last_edited_time")
    
    elif prop_type == "created_by":
        created_by = property_obj.get("created_by")
        return created_by.get("id") if created_by else None
    
    elif prop_type == "last_edited_by":
        last_edited_by = property_obj.get("last_edited_by")
        return last_edited_by.get("id") if last_edited_by else None
    
    else:
        # For unknown types, return the raw object
        return property_obj


def structure_database_entry(entry: Dict, database_name: str, database_id: str) -> Dict:
    """
    Structure a Notion database entry as a ContentSource.
    
    Args:
        entry: Notion page object from database query
        database_name: Name of the database
        database_id: Notion database ID
        
    Returns:
        Structured ContentSource dictionary
    """
    properties = entry.get("properties", {})
    
    # Extract all property values
    all_properties = {}
    for prop_name, prop_obj in properties.items():
        all_properties[prop_name] = extract_property_value(prop_obj)
    
    # Try to find title property (usually "Name" or first title property)
    title = None
    for prop_name, prop_obj in properties.items():
        if prop_obj.get("type") == "title":
            title = extract_property_value(prop_obj)
            break
    
    if not title:
        # Fallback to first property or page ID
        title = list(all_properties.keys())[0] if all_properties else entry.get("id", "Untitled")
    
    # Build full text content from all properties
    content_parts = []
    for prop_name, prop_value in all_properties.items():
        if prop_value:
            if isinstance(prop_value, str):
                content_parts.append(f"{prop_name}: {prop_value}")
            elif isinstance(prop_value, list):
                content_parts.append(f"{prop_name}: {', '.join(str(v) for v in prop_value)}")
            elif isinstance(prop_value, dict):
                content_parts.append(f"{prop_name}: {json.dumps(prop_value)}")
            else:
                content_parts.append(f"{prop_name}: {str(prop_value)}")
    
    full_content = "\n\n".join(content_parts)
    
    return {
        "id": str(uuid.uuid4()),
        "notion_id": entry.get("id"),
        "source_type": "database_entry",
        "title": title,
        "url": entry.get("url"),
        "database_name": database_name,
        "database_id": database_id,
        "all_properties": all_properties,
        "full_content": full_content,
        "created_at": entry.get("created_time"),
        "updated_at": entry.get("last_edited_time"),
        "metadata": {
            "database_name": database_name,
            "database_id": database_id,
            "extracted_at": datetime.utcnow().isoformat()
        }
    }


def extract_database_entries_mcp(database_id: str, database_name: str) -> List[Dict]:
    """
    Extract all entries from a Notion database using MCP.
    
    Note: This function is designed to be called from Cursor with MCP tools.
    The actual MCP calls will be made by the AI assistant.
    
    Args:
        database_id: Notion database ID
        database_name: Name of the database
        
    Returns:
        List of structured ContentSource dictionaries
    """
    # This function will be called with MCP results
    # For now, return empty list - will be populated by MCP calls
    return []


def process_mcp_database_results(mcp_results: Dict, database_name: str, database_id: str) -> List[Dict]:
    """
    Process MCP query-data-source results and structure as ContentSources.
    
    Args:
        mcp_results: Results from Notion MCP query-data-source tool
        database_name: Name of the database
        database_id: Notion database ID
        
    Returns:
        List of structured ContentSource dictionaries
    """
    content_sources = []
    
    # Extract results from MCP response
    results = mcp_results.get("results", [])
    
    for entry in results:
        try:
            structured = structure_database_entry(entry, database_name, database_id)
            content_sources.append(structured)
        except Exception as e:
            print(f"Error processing entry {entry.get('id', 'unknown')}: {e}")
            continue
    
    return content_sources


def main():
    """
    Main function - extracts database content.
    
    This script is designed to be orchestrated by the AI assistant
    which will make the actual MCP calls and pass results here.
    """
    print("Database content extraction script")
    print("This script processes MCP results to extract database entries.")
    print("The AI assistant will call Notion MCP tools and pass results here.")


if __name__ == "__main__":
    main()



