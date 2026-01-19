"""
Extract full content from Notion pages.

This script uses Notion MCP tools to retrieve full page content
including all blocks recursively for RAG content extraction.
"""

import json
import os
import sys
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid


def extract_text_from_block(block: Dict) -> str:
    """
    Extract plain text content from a Notion block.
    
    Handles various block types:
    - paragraph, heading_1-3, bulleted_list_item, numbered_list_item
    - quote, callout, code, to_do
    - etc.
    """
    block_type = block.get("type")
    
    if block_type in ["paragraph", "heading_1", "heading_2", "heading_3", 
                      "bulleted_list_item", "numbered_list_item", "quote", 
                      "callout", "to_do"]:
        rich_text = block.get(block_type, {}).get("rich_text", [])
        return "".join([t.get("plain_text", "") for t in rich_text])
    
    elif block_type == "code":
        code_obj = block.get("code", {})
        language = code_obj.get("language", "")
        code_text = "".join([t.get("plain_text", "") for t in code_obj.get("rich_text", [])])
        return f"```{language}\n{code_text}\n```"
    
    elif block_type == "divider":
        return "---"
    
    elif block_type == "table":
        # Tables are complex - return placeholder for now
        return "[Table content]"
    
    elif block_type == "child_database":
        db_info = block.get("child_database", {})
        return f"[Database: {db_info.get('title', 'Untitled')}]"
    
    elif block_type == "child_page":
        page_info = block.get("child_page", {})
        return f"[Page: {page_info.get('title', 'Untitled')}]"
    
    else:
        # For unknown types, try to extract any text
        return ""


def get_all_blocks_recursive(block_id: str, mcp_get_blocks_func) -> List[Dict]:
    """
    Recursively get all blocks from a page.
    
    Args:
        block_id: Notion page/block ID
        mcp_get_blocks_func: Function to call MCP get-block-children
        
    Returns:
        List of all blocks (flattened)
    """
    all_blocks = []
    
    # Get direct children
    try:
        result = mcp_get_blocks_func(block_id, page_size=100)
        blocks = result.get("results", [])
        all_blocks.extend(blocks)
        
        # Check for pagination
        while result.get("has_more"):
            next_cursor = result.get("next_cursor")
            result = mcp_get_blocks_func(block_id, page_size=100, start_cursor=next_cursor)
            blocks = result.get("results", [])
            all_blocks.extend(blocks)
        
        # Recursively get children of blocks that have children
        for block in blocks:
            if block.get("has_children"):
                child_blocks = get_all_blocks_recursive(block.get("id"), mcp_get_blocks_func)
                all_blocks.extend(child_blocks)
    
    except Exception as e:
        print(f"Error getting blocks for {block_id}: {e}")
    
    return all_blocks


def extract_page_content(page_id: str, page_data: Dict, all_blocks: List[Dict]) -> Dict:
    """
    Extract and structure full page content as ContentSource.
    
    Args:
        page_id: Notion page ID
        page_data: Page metadata from retrieve-a-page
        all_blocks: All blocks from the page (recursive)
        
    Returns:
        Structured ContentSource dictionary
    """
    # Extract page title
    title_prop = page_data.get("properties", {}).get("title", {})
    title = "".join([t.get("plain_text", "") for t in title_prop.get("title", [])]) if title_prop.get("title") else "Untitled"
    
    # Extract text content from all blocks
    content_parts = []
    block_metadata = []
    
    for i, block in enumerate(all_blocks):
        block_type = block.get("type")
        block_text = extract_text_from_block(block)
        
        if block_text.strip():
            content_parts.append(block_text)
            block_metadata.append({
                "index": i,
                "type": block_type,
                "id": block.get("id"),
                "has_children": block.get("has_children", False)
            })
    
    full_content = "\n\n".join(content_parts)
    
    return {
        "id": str(uuid.uuid4()),
        "notion_id": page_id,
        "source_type": "page",
        "title": title,
        "url": page_data.get("url"),
        "full_content": full_content,
        "block_count": len(all_blocks),
        "created_at": page_data.get("created_time"),
        "updated_at": page_data.get("last_edited_time"),
        "metadata": {
            "block_metadata": block_metadata,
            "extracted_at": datetime.utcnow().isoformat(),
            "page_properties": page_data.get("properties", {})
        }
    }


def extract_teamspace_pages(teamspace_ids: Dict[str, str]) -> List[Dict]:
    """
    Extract content from all teamspace pages.
    
    Args:
        teamspace_ids: Dictionary mapping teamspace names to Notion page IDs
        
    Returns:
        List of structured ContentSource dictionaries
    """
    # This function will be called with MCP results
    # For now, return empty list - will be populated by MCP calls
    return []


def process_mcp_page_results(page_id: str, page_data: Dict, blocks_data: List[Dict]) -> Dict:
    """
    Process MCP page retrieval results and structure as ContentSource.
    
    Args:
        page_id: Notion page ID
        page_data: Results from retrieve-a-page MCP tool
        blocks_data: Results from get-block-children MCP tool (recursive)
        
    Returns:
        Structured ContentSource dictionary
    """
    return extract_page_content(page_id, page_data, blocks_data)


def main():
    """
    Main function - extracts page content.
    
    This script is designed to be orchestrated by the AI assistant
    which will make the actual MCP calls and pass results here.
    """
    print("Page content extraction script")
    print("This script processes MCP results to extract page content.")
    print("The AI assistant will call Notion MCP tools and pass results here.")


if __name__ == "__main__":
    main()



