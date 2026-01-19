#!/usr/bin/env python3
"""
Extract Notion content, chunk it, and store in Neo4j memory for RAG.
Uses Notion MCP API and Neo4j memory MCP tools.
"""

import json
import re
from typing import List, Dict, Any

def extract_text_from_blocks(blocks: List[Dict]) -> str:
    """Extract plain text from Notion blocks."""
    text_parts = []
    
    for block in blocks:
        block_type = block.get('type')
        
        if block_type == 'paragraph':
            rich_text = block.get('paragraph', {}).get('rich_text', [])
            text = ''.join([rt.get('plain_text', '') for rt in rich_text])
            if text.strip():
                text_parts.append(text)
        
        elif block_type in ['heading_1', 'heading_2', 'heading_3']:
            rich_text = block.get(block_type, {}).get('rich_text', [])
            text = ''.join([rt.get('plain_text', '') for rt in rich_text])
            if text.strip():
                prefix = '#' * (1 if block_type == 'heading_1' else 2 if block_type == 'heading_2' else 3)
                text_parts.append(f"{prefix} {text}")
        
        elif block_type == 'bulleted_list_item':
            rich_text = block.get('bulleted_list_item', {}).get('rich_text', [])
            text = ''.join([rt.get('plain_text', '') for rt in rich_text])
            if text.strip():
                text_parts.append(f"- {text}")
        
        elif block_type == 'numbered_list_item':
            rich_text = block.get('numbered_list_item', {}).get('rich_text', [])
            text = ''.join([rt.get('plain_text', '') for rt in rich_text])
            if text.strip():
                text_parts.append(f"1. {text}")
        
        elif block_type == 'callout':
            rich_text = block.get('callout', {}).get('rich_text', [])
            text = ''.join([rt.get('plain_text', '') for rt in rich_text])
            if text.strip():
                text_parts.append(f"💡 {text}")
        
        elif block_type == 'quote':
            rich_text = block.get('quote', {}).get('rich_text', [])
            text = ''.join([rt.get('plain_text', '') for rt in rich_text])
            if text.strip():
                text_parts.append(f"> {text}")
        
        elif block_type == 'code':
            rich_text = block.get('code', {}).get('rich_text', [])
            text = ''.join([rt.get('plain_text', '') for rt in rich_text])
            if text.strip():
                language = block.get('code', {}).get('language', '')
                text_parts.append(f"```{language}\n{text}\n```")
        
        # Recursively process child blocks
        if block.get('has_children'):
            # Note: This would require additional API calls to get children
            # For now, we'll skip nested content
            pass
    
    return '\n\n'.join(text_parts)


def chunk_text(text: str, max_chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    Split text into chunks with overlap.
    
    Args:
        text: Text to chunk
        max_chunk_size: Maximum characters per chunk
        overlap: Number of characters to overlap between chunks
    
    Returns:
        List of text chunks
    """
    if len(text) <= max_chunk_size:
        return [text]
    
    chunks = []
    # Try to split on paragraph boundaries first
    paragraphs = text.split('\n\n')
    
    current_chunk = []
    current_size = 0
    
    for para in paragraphs:
        para_size = len(para)
        
        if current_size + para_size <= max_chunk_size:
            current_chunk.append(para)
            current_size += para_size + 2  # +2 for \n\n
        else:
            if current_chunk:
                chunks.append('\n\n'.join(current_chunk))
            
            # Start new chunk with overlap
            if overlap > 0 and chunks:
                # Take last part of previous chunk for overlap
                prev_chunk = chunks[-1]
                overlap_text = prev_chunk[-overlap:] if len(prev_chunk) > overlap else prev_chunk
                current_chunk = [overlap_text, para]
                current_size = len(overlap_text) + para_size + 2
            else:
                current_chunk = [para]
                current_size = para_size
    
    if current_chunk:
        chunks.append('\n\n'.join(current_chunk))
    
    return chunks


def create_metadata(page: Dict, chunk_index: int, total_chunks: int) -> Dict[str, Any]:
    """Create metadata for a chunk."""
    page_id = page.get('id', '')
    page_title = ''
    
    # Extract title from properties
    if 'properties' in page:
        title_prop = page['properties'].get('title', {})
        if isinstance(title_prop, dict) and 'title' in title_prop:
            title_array = title_prop['title']
            if isinstance(title_array, list) and len(title_array) > 0:
                page_title = title_array[0].get('plain_text', '')
    
    # Fallback to URL if no title
    if not page_title:
        url = page.get('url', '')
        page_title = url.split('/')[-1] if url else 'Untitled'
    
    return {
        'source': 'notion',
        'page_id': page_id,
        'page_title': page_title,
        'page_url': page.get('url', ''),
        'chunk_index': chunk_index,
        'total_chunks': total_chunks,
        'created_time': page.get('created_time', ''),
        'last_edited_time': page.get('last_edited_time', '')
    }


if __name__ == '__main__':
    print("Notion to Neo4j RAG chunking utility")
    print("This script provides functions for chunking Notion content.")
    print("Use the MCP tools to actually store the chunks in Neo4j.")


