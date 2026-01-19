# PLANNING.md - Grap Infrastructure

## High-Level Vision
To provide a production-ready, durable, and governed memory layer for AI agents, utilizing **Neo4j** as the sole knowledge graph.

## Architecture
- **Graph Tier**: Neo4j 5.13.0 (Community) with APOC.
- **Governance Tier**: Backup Scheduler (Durability), Health Checker (Consistency), Write Log (Audit).

## Tech Stack
- **Persistence**: Docker Named Volumes
- **Language**: Python 3.9+ (Tooling), Cypher (Queries)
- **Orchestration**: Docker Compose

## Current Objectives (Cleanup Phase)
1. **Purge Technical Debt**: Remove Mem0 and Qdrant containers and config.
2. **Consolidate Documentation**: Ensure `README.md` and `docker-compose.yml` reflect the "Neo4j Only" stack.
3. **Validate Durability**: Ensure `grap-backup-scheduler` reliably captures the standalone graph using APOC exports.

## Constraints
- Keep all files under 500 lines.
- Validate structure like data.
- Maintain Conceptual Integrity at all costs.
