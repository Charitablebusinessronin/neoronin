# TASK.md - The Great Consolidation

## Phase 1: The Purge (Accidental Complexity Removal)
- [/] Remove `mem0`, `qdrant`, and `graphiti` from `docker-compose.yml`.
- [ ] Apply changes (`docker compose up -d --remove-orphans`).
- [ ] Verify `neo4j` and `backup-scheduler` constitute the entire running stack.

## Phase 2: Durability & Integrity
- [/] Verify `grap-backup-scheduler` is correctly targeting the `grap-neo4j` container.
- [x] Fix Backup Strategy (Switched to APOC export).
- [ ] Perform manual backup test.
- [/] Verify Neo4j MCP connectivity (Data Modeling, Memory, Cypher).

## Phase 3: Documentation
- [x] Update `README.md` to reflect the single-container architecture.
- [x] Archive `mem0_config.yaml` and other vestigial config files.
