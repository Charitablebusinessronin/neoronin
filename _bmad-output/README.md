# BMad Output Directory Structure (Hybrid Model)

This directory follows the **Option C (Hybrid)** model for artifact organization, preserving both latest state and development history.

## 📁 Directory Map

- **`docs/`**: Living documentation and architectural designs.
    - `BMAD_PRD.md`: The single source of truth for product requirements.
    - `phase_completions/`: Historical snapshots of completed development phases.
- **`code/`**: Source code for BMAD-specific middleware and engines.
- **`schemas/`**: Latest Neo4j Cypher schemas and versioned historical snapshots.
- **`data/`**: Seed patterns, test fixtures, and JSON schemas.
- **`reports/`**: Sprint-level progress reports and audit summaries.
- **`deployment/`**: Scripts and logs for infrastructure automation.
- **`artifacts/`**: Raw output from audits, logs, and surgical repairs.

## 📜 Organizational Rules
1. **Latest Always Wins**: The main directories (`docs/`, `code/`, `schemas/`) always contain the current production-ready artifacts.
2. **Snapshot on Phase End**: Upon completing a phase, copy the final state to the appropriate historical subdirectory (e.g., `docs/phase_completions/` or `schemas/versions/`).
3. **Audit Trail**: Save surgical logs and audit reports to `artifacts/`.

---
*Maintained by BMad Master & Winston (Architect)*
