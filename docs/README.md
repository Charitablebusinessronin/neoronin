# Deprecated: Root `/docs/` Directory

**Status:** ⚠️ **DEPRECATED** - BMAD Architecture Migration (2026-01-26)

## Migration Summary

All BMAD documentation has been migrated to the canonical BMAD output structure:

| Original Path | New Location | Status |
|---------------|--------------|--------|
| `/docs/BMAD_PRD.md` | `_bmad-output/docs/prd/BMAD_PRD.md` | ✅ Migrated |

## New Documentation Structure

```
_bmad-output/
├── docs/
│   ├── prd/                          ← Product Requirements Documents
│   │   └── BMAD_PRD.md
│   ├── architecture/                 ← Architecture documents (when generated)
│   └── implementation/               ← Implementation artifacts
```

## Knowledge Graph Integration

All migrated documentation is now accessible as `(:KnowledgeItem)` nodes in Neo4j:

```cypher
MATCH (k:KnowledgeItem {source: 'prd_bmad_memory_integration'})
RETURN k.title, k.content_type, k.file_path
```

## Retention Policy

This directory is retained only for backward compatibility. New documentation should be created directly in `_bmad-output/docs/` to maintain BMAD architectural consistency.

**Migration Date:** 2026-01-26
**Executed By:** BMad Master
**Reason:** Align with BMAD architecture - load at runtime, never pre-load