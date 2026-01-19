#!/usr/bin/env python3
"""
Mem0 MCP Server - Provides Model Context Protocol interface for Mem0.
This script bridges Mem0's API to MCP stdio protocol.
"""

import os
import sys
import json
import asyncio
from typing import Any, Dict, List, Optional

# Try to import Mem0 SDK
try:
    from mem0 import Memory
except ImportError:
    print("Error: mem0ai package not installed. Install with: pip install mem0ai", file=sys.stderr)
    sys.exit(1)

# Configuration from environment
MEM0_CONFIG_PATH = os.getenv("MEM0_CONFIG_PATH", "/app/config/mem0_config.yaml")
USER_ID = os.getenv("MEM0_USER_ID", "difference-driven")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Initialize Mem0 client
# Mem0 can be initialized from config file or with direct parameters
memory = None
try:
    import yaml
    if os.path.exists(MEM0_CONFIG_PATH):
        with open(MEM0_CONFIG_PATH, 'r') as f:
            config = yaml.safe_load(f)
        # Initialize with config dict
        memory = Memory.from_config(config)
    else:
        # Fallback: initialize with environment variables
        memory = Memory()
except Exception as e:
    # Don't exit on initialization error - allow script to start and handle errors gracefully
    # This prevents container crashes if Mem0 config is temporarily unavailable
    print(f"Warning: Mem0 initialization failed: {e}", file=sys.stderr)
    print("MCP server will start but memory operations will fail until Mem0 is initialized", file=sys.stderr)

TOOL_DEFS = [
    {
        "name": "mem0.add",
        "description": "Store a memory from a list of chat messages.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "messages": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "role": {"type": "string"},
                            "content": {"type": "string"}
                        },
                        "required": ["role", "content"]
                    },
                    "minItems": 1
                },
                "user_id": {"type": "string"}
            },
            "required": ["messages"]
        }
    },
    {
        "name": "mem0.search",
        "description": "Search stored memories with a query string.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "user_id": {"type": "string"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "mem0.get_all",
        "description": "Fetch all memories for a user.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"}
            }
        }
    }
]


def tool_content(payload: Any) -> Dict[str, Any]:
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
            }
        ]
    }


async def handle_mcp_request(request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Handle MCP protocol requests."""
    method = request.get("method")
    params = request.get("params", {})
    request_id = request.get("id")
    
    # JSON-RPC: if request has no id, it's a notification and we shouldn't respond
    is_notification = request_id is None
    
    try:
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "mem0-mcp",
                        "version": "0.1.1"
                    }
                }
            }

        elif method == "listOfferings":
            # Cursor's MCP client calls this to discover capabilities
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "tools": TOOL_DEFS,
                    "prompts": [],
                    "resources": []
                }
            }

        elif method in ("tools/list", "list_tools"):
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "tools": TOOL_DEFS
                }
            }

        elif method in ("prompts/list", "list_prompts"):
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "prompts": []
                }
            }

        elif method in ("resources/list", "list_resources"):
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "resources": []
                }
            }

        elif method in ("tools/call", "call_tool"):
            # Check if Mem0 is initialized
            if memory is None:
                if is_notification:
                    return None
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32000,
                        "message": "Mem0 not initialized. Check container logs for initialization errors."
                    }
                }
            
            tool_name = params.get("name")
            tool_args = params.get("arguments", {}) or {}

            if tool_name == "mem0.add":
                try:
                    messages = tool_args.get("messages", [])
                    user_id = tool_args.get("user_id", USER_ID)
                    result = memory.add(messages, user_id=user_id)
                    payload = {
                        "success": True,
                        "memory_id": result.get("id") if isinstance(result, dict) else str(result)
                    }
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": tool_content(payload)
                    }
                except Exception as e:
                    if is_notification:
                        return None
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32000,
                            "message": f"Failed to add memory: {str(e)}"
                        }
                    }

            if tool_name == "mem0.search":
                try:
                    query = tool_args.get("query", "")
                    user_id = tool_args.get("user_id", USER_ID)
                    filters = {"user_id": user_id}
                    results = memory.search(query, filters=filters)
                    payload = {
                        "memories": results if isinstance(results, list) else [results]
                    }
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": tool_content(payload)
                    }
                except Exception as e:
                    if is_notification:
                        return None
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32000,
                            "message": f"Failed to search memories: {str(e)}"
                        }
                    }

            if tool_name == "mem0.get_all":
                try:
                    user_id = tool_args.get("user_id", USER_ID)
                    filters = {"user_id": user_id}
                    results = memory.get_all(filters=filters)
                    payload = {
                        "memories": results if isinstance(results, list) else [results]
                    }
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": tool_content(payload)
                    }
                except Exception as e:
                    if is_notification:
                        return None
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32000,
                            "message": f"Failed to get memories: {str(e)}"
                        }
                    }

            # Method not found - but only respond if it's not a notification
            if is_notification:
                return None
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Tool not found: {tool_name}"
                }
            }

        else:
            # Method not found - but only respond if it's not a notification
            if is_notification:
                return None
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }
    
    except Exception as e:
        # Only respond if it's not a notification
        if is_notification:
            return None
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32000,
                "message": str(e)
            }
        }

async def main():
    """Main MCP server loop - reads from stdin, writes to stdout."""
    # Read requests from stdin
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        
        try:
            request = json.loads(line)
            response = await handle_mcp_request(request)
            # Only print response if we got one (not a notification)
            if response is not None:
                print(json.dumps(response), flush=True)
        except json.JSONDecodeError as e:
            # Parse errors don't have request IDs, so we can't respond properly
            # Just skip invalid JSON
            continue
        except Exception as e:
            # For unexpected errors, try to extract request ID if possible
            try:
                request = json.loads(line)
                request_id = request.get("id")
                if request_id is not None:
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32000,
                            "message": f"Internal error: {e}"
                        }
                    }
                    print(json.dumps(error_response), flush=True)
            except:
                # Can't parse request, skip it
                continue

if __name__ == "__main__":
    asyncio.run(main())
