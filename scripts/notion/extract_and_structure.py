"""
Extract and structure anchor nodes from Notion MCP results.

This script processes the MCP results we retrieved and creates
structured anchor node JSON ready for Neo4j import.
"""

import json
import sys
from process_mcp_results import structure_anchor_nodes

# MCP results from Hub page retrieval
HUB_PAGE_DATA = {
    "object": "page",
    "id": "2661d9be-65b3-81df-8977-e88482d03583",
    "created_time": "2025-09-06T12:32:00.000Z",
    "last_edited_time": "2025-12-27T12:58:00.000Z",
    "url": "https://www.notion.so/Ronin-s-Notion-Hub-Master-Directory-Command-Center-2661d9be65b381df8977e88482d03583",
    "properties": {
        "title": {
            "id": "title",
            "type": "title",
            "title": [
                {
                    "type": "text",
                    "text": {"content": "🏛️ Ronin's Notion Hub - Master Directory & Command Center"},
                    "plain_text": "🏛️ Ronin's Notion Hub - Master Directory & Command Center"
                }
            ]
        }
    }
}

# MCP results from block children retrieval
BLOCKS_DATA = [
    {"object": "block", "id": "4a0e2649-eb95-46d4-8f51-7c3501f21926", "type": "callout"},
    {"object": "block", "id": "476f5931-4c8f-4d29-b45d-cee0463df0ec", "type": "divider"},
    {"object": "block", "id": "0d0c3950-48bf-48c8-9966-d590a6a66861", "type": "heading_3"},
    {"object": "block", "id": "277df34d-7eac-4414-9848-a8bcc0609133", "type": "table"},
    {"object": "block", "id": "ace985da-6df8-4929-889d-9e75fa874da3", "type": "divider"},
    {"object": "block", "id": "715e278f-5fab-4329-8b21-211325a176f2", "type": "heading_3", "heading_3": {"rich_text": [{"plain_text": "Workspace Map (Top-Level)"}]}},
    {"object": "block", "id": "e19af69a-f81a-4853-acf5-5f570e7ef8b1", "type": "heading_3", "heading_3": {"rich_text": [{"plain_text": "Project team spaces"}]}},
    {
        "object": "block",
        "id": "12c250ea-8e14-4fc7-a9f0-8fa6feb501a0",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [
                {"type": "text", "text": {"content": "Faith Meats"}, "plain_text": "Faith Meats", "annotations": {"bold": True}},
                {"type": "text", "text": {"content": " — Premium halal beef jerky; Shopify Hydrogen migration."}, "plain_text": " — Premium halal beef jerky; Shopify Hydrogen migration."}
            ]
        }
    },
    {
        "object": "block",
        "id": "3c283c3d-12e5-4662-9649-677849161b6b",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [
                {"type": "text", "text": {"content": "Patriot Awning"}, "plain_text": "Patriot Awning", "annotations": {"bold": True}},
                {"type": "text", "text": {"content": " — Commercial/residential awning company; Astro + Tailwind rebuild."}, "plain_text": " — Commercial/residential awning company; Astro + Tailwind rebuild."}
            ]
        }
    },
    {
        "object": "block",
        "id": "9aa8bdf1-5bae-459e-a30c-b4d31c7aaeb0",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [
                {"type": "text", "text": {"content": "Difference Driven"}, "plain_text": "Difference Driven", "annotations": {"bold": True}},
                {"type": "text", "text": {"content": " — Nonprofit community platform; Payload CMS website development."}, "plain_text": " — Nonprofit community platform; Payload CMS website development."}
            ]
        }
    },
    {"object": "block", "id": "f0961c7c-5464-4627-9cc7-c1222aaee95d", "type": "heading_3", "heading_3": {"rich_text": [{"plain_text": "Central command databases"}]}},
    {
        "object": "block",
        "id": "495894e8-06a4-4501-b1a0-05ce274b4d64",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [
                {"type": "text", "text": {"content": "AI Agents Registry"}, "plain_text": "AI Agents Registry", "annotations": {"bold": True}},
                {"type": "text", "text": {"content": " — agent tracking and management."}, "plain_text": " — agent tracking and management."}
            ]
        }
    },
    {
        "object": "block",
        "id": "5b14e4d9-2868-4eb5-990d-5a7721b72e06",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [
                {"type": "text", "text": {"content": "Master Knowledge Base"}, "plain_text": "Master Knowledge Base", "annotations": {"bold": True}},
                {"type": "text", "text": {"content": " — centralized documentation."}, "plain_text": " — centralized documentation."}
            ]
        }
    },
    {
        "object": "block",
        "id": "60e78978-bb00-402b-9903-79b5cb1b7e9c",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [
                {"type": "text", "text": {"content": "Master Calendar & Events"}, "plain_text": "Master Calendar & Events", "annotations": {"bold": True}},
                {"type": "text", "text": {"content": " — cross-project scheduling."}, "plain_text": " — cross-project scheduling."}
            ]
        }
    },
    {"object": "block", "id": "cece84e6-02a7-4dc5-aa8e-aba0f480edec", "type": "heading_3", "heading_3": {"rich_text": [{"plain_text": "Active AI agents (high-level)"}]}},
    {
        "object": "block",
        "id": "35c167e7-753e-4c2b-bcf4-ab8aec86467e",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [
                {"type": "text", "text": {"content": "Troy Davis — General Coding Agent (Spec-Kit SDD workflows across projects)"}, "plain_text": "Troy Davis — General Coding Agent (Spec-Kit SDD workflows across projects)"}
            ]
        }
    },
    {
        "object": "block",
        "id": "ed230872-d65f-40fb-93a8-997e9d0c84c7",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [
                {"type": "text", "text": {"content": "Steven — DD Product Manager (SpecKit oversight, constitution compliance, spec/plan reviews)"}, "plain_text": "Steven — DD Product Manager (SpecKit oversight, constitution compliance, spec/plan reviews)"}
            ]
        }
    },
    {
        "object": "block",
        "id": "8bc5eb8f-3250-4c0e-a9f5-3cd53c694c6e",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [
                {"type": "text", "text": {"content": "Tommy Oliver — Agent Builder & Workflow Architect (BMAD-compliant agent/workflow design)"}, "plain_text": "Tommy Oliver — Agent Builder & Workflow Architect (BMAD-compliant agent/workflow design)"}
            ]
        }
    },
    {
        "object": "block",
        "id": "247f526f-30db-417b-bd00-5fa1a7ee87ae",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [
                {"type": "text", "text": {"content": "Ari Khalid — Investigative Researcher (primary-source hunting, decision-ready briefs)"}, "plain_text": "Ari Khalid — Investigative Researcher (primary-source hunting, decision-ready briefs)"}
            ]
        }
    },
    {"object": "block", "id": "5c1b8066-d0b2-44b2-a486-4448762f5663", "type": "heading_3", "heading_3": {"rich_text": [{"plain_text": "BMAD agent team (available in AI Agents Registry)"}]}},
    {
        "object": "block",
        "id": "ea8dfecf-dfed-4e4f-a757-87fc116b8a0b",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [
                {"type": "text", "text": {"content": "John — Product Manager (PRD creation, epics & stories)"}, "plain_text": "John — Product Manager (PRD creation, epics & stories)"}
            ]
        }
    },
    {
        "object": "block",
        "id": "312aac82-737b-4099-9fbb-f4178b2ff62a",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [
                {"type": "text", "text": {"content": "Troy — Developer Agent (code implementation)"}, "plain_text": "Troy — Developer Agent (code implementation)"}
            ]
        }
    },
    {
        "object": "block",
        "id": "a387d038-32f2-4a91-9e21-7d193ee33104",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [
                {"type": "text", "text": {"content": "Sally — UX Designer (design collaboration)"}, "plain_text": "Sally — UX Designer (design collaboration)"}
            ]
        }
    },
    {
        "object": "block",
        "id": "bb76b78d-6353-4386-9da7-e15d8b06ed09",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [
                {"type": "text", "text": {"content": "BMad Builder — agent/workflow creation and maintenance"}, "plain_text": "BMad Builder — agent/workflow creation and maintenance"}
            ]
        }
    },
    {"object": "block", "id": "64793101-53e6-4994-b6e4-0a427d0364fb", "type": "heading_3", "heading_3": {"rich_text": [{"plain_text": "Content categories (knowledge base)"}]}},
    {
        "object": "block",
        "id": "f283ed8b-9d98-4bac-8dcd-d36492556128",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [
                {"type": "text", "text": {"content": "Archon Project"}, "plain_text": "Archon Project"}
            ]
        }
    },
    {
        "object": "block",
        "id": "3b846b82-e188-4e1b-ad89-2f38c94cec22",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [
                {"type": "text", "text": {"content": "AI Learning Notes"}, "plain_text": "AI Learning Notes"}
            ]
        }
    },
    {
        "object": "block",
        "id": "1c926ced-ce23-4f8c-bfab-d7e6286b9f78",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [
                {"type": "text", "text": {"content": "RAG"}, "plain_text": "RAG"}
            ]
        }
    },
    {
        "object": "block",
        "id": "90331381-9198-4550-aa78-744515f99bac",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [
                {"type": "text", "text": {"content": "Coding & Development"}, "plain_text": "Coding & Development"}
            ]
        }
    },
    {
        "object": "block",
        "id": "3684b4e9-40fc-450b-b9c7-347851d55a39",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [
                {"type": "text", "text": {"content": "Faith Meats"}, "plain_text": "Faith Meats"}
            ]
        }
    },
    {
        "object": "block",
        "id": "876878ba-09cb-430d-9e38-af832ee86b86",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [
                {"type": "text", "text": {"content": "Project Management"}, "plain_text": "Project Management"}
            ]
        }
    },
    {
        "object": "block",
        "id": "662f532d-cf81-4b21-898b-db7ad99c1da2",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [
                {"type": "text", "text": {"content": "Research & Discovery"}, "plain_text": "Research & Discovery"}
            ]
        }
    },
    {
        "object": "block",
        "id": "ab0a9c86-815a-442e-a93b-d892e8819a1a",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [
                {"type": "text", "text": {"content": "Team Knowledge"}, "plain_text": "Team Knowledge"}
            ]
        }
    },
    {"object": "block", "id": "07343e66-a8e6-439d-a5e8-221bbac34ce5", "type": "heading_3", "heading_3": {"rich_text": [{"plain_text": "Smart tags"}]}},
    {
        "object": "block",
        "id": "c75f8e74-863d-4037-acd9-f560fe743250",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [
                {"type": "text", "text": {"content": "Technical: Vercel, Docker, API, Database, Authentication, Infrastructure"}, "plain_text": "Technical: Vercel, Docker, API, Database, Authentication, Infrastructure"}
            ]
        }
    },
    {
        "object": "block",
        "id": "9dc0039d-ae19-43c7-84d5-7633039fd0d7",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [
                {"type": "text", "text": {"content": "Programming: Python, JavaScript, TypeScript, React, Next.js"}, "plain_text": "Programming: Python, JavaScript, TypeScript, React, Next.js"}
            ]
        }
    },
    {
        "object": "block",
        "id": "cf8f1ad5-c2f0-4ea3-9ecc-a06f1d9a35fd",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [
                {"type": "text", "text": {"content": "AI/ML: LLM, RAG, Embeddings, Vector Search, Claude, Archon"}, "plain_text": "AI/ML: LLM, RAG, Embeddings, Vector Search, Claude, Archon"}
            ]
        }
    },
    {
        "object": "block",
        "id": "c0009a11-4baa-4c9d-8aa8-c4d34ce4e23a",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [
                {"type": "text", "text": {"content": "Business: Sales, CRM, Pricing, Healthcare, Halal Food"}, "plain_text": "Business: Sales, CRM, Pricing, Healthcare, Halal Food"}
            ]
        }
    },
    {
        "object": "block",
        "id": "ca61c77c-3145-4119-a345-7a3f95dc5dce",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [
                {"type": "text", "text": {"content": "Projects: Faith Meats, Snug Kisses, Dam Restoration, Difference Driven"}, "plain_text": "Projects: Faith Meats, Snug Kisses, Dam Restoration, Difference Driven"}
            ]
        }
    },
    {
        "object": "block",
        "id": "8a1e5a59-3f6d-4bc1-9b26-99d778888024",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [
                {"type": "text", "text": {"content": "Content: Documentation, Guide, Tutorial, Template, Reference"}, "plain_text": "Content: Documentation, Guide, Tutorial, Template, Reference"}
            ]
        }
    },
    {
        "object": "block",
        "id": "2d682602-f310-42a1-a3e1-c5cb8a176a9d",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [
                {"type": "text", "text": {"content": "Status: Urgent, Completed, In Progress, Needs Review"}, "plain_text": "Status: Urgent, Completed, In Progress, Needs Review"}
            ]
        }
    },
    {
        "object": "block",
        "id": "a32c673e-92c5-4f9c-80d3-cb25f6ffd959",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [
                {"type": "text", "text": {"content": "Access: Public, Internal, Example, Backup"}, "plain_text": "Access: Public, Internal, Example, Backup"}
            ]
        }
    },
    {
        "object": "block",
        "id": "e5d3db1e-1290-4d33-bd1f-71f93cc36655",
        "type": "child_database",
        "child_database": {"title": "Master Knowledge Base"}
    },
    {
        "object": "block",
        "id": "62baeeb2-8b17-436d-a92b-314128fb93cb",
        "type": "child_database",
        "child_database": {"title": "AI Agents Registry"}
    },
    {
        "object": "block",
        "id": "2a11d9be-65b3-8055-909b-fc277d4f47ed",
        "type": "child_database",
        "child_database": {"title": "Prompt Database"}
    },
    {
        "object": "block",
        "id": "2c11d9be-65b3-80f8-868c-c1b5d896342b",
        "type": "child_database",
        "child_database": {"title": "Agent activation prompt"}
    }
]


def main():
    """Process MCP results and create anchor nodes JSON."""
    print("Processing MCP results and structuring anchor nodes...")
    
    # Structure anchor nodes from MCP data
    anchor_nodes = structure_anchor_nodes(
        hub_page=HUB_PAGE_DATA,
        blocks=BLOCKS_DATA,
        agents_from_registry=None  # We'll add this later if needed
    )
    
    # Save to JSON file
    output_file = "notion_anchor_nodes.json"
    with open(output_file, "w") as f:
        json.dump(anchor_nodes, f, indent=2)
    
    print(f"Created {len(anchor_nodes)} anchor nodes")
    print(f"Saved to {output_file}")
    
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



