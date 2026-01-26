# Grap Neo4j Durability System

A production-ready Neo4j memory infrastructure for persistent graph-backed AI systems. Implements Constitution Principle VI with automated APOC-based backups, recovery procedures, health monitoring, and comprehensive audit logging.

## Phase 2: BMAD Agent Memory Integration (In Progress)

This project is being extended with **BMAD Agent Memory Integration** - a learning system that enables AI agents to capture, share, and refine knowledge from their work.

### BMAD Architecture Components

| Component | Purpose | Port/Schedule |
|-----------|---------|---------------|
| **EventLoggerMiddleware** | Captures GitHub actions as events (commits, PRs, reviews) | Port 8001 |
| **QueryTemplateLibrary** | Parameterized query templates with mandatory group_id filtering | Library |
| **PatternManager** | Reusable pattern library with LRU cache (100 patterns, 1hr TTL) | Library |
| **InsightGeneratorEngine** | Analyzes outcomes to generate insights with confidence scoring | Daily 2:00 AM |
| **RelevanceScoringService** | Temporal decay for stale insights (90-day half-life) | Daily 2:10 AM |
| **HealthCheckService** | Orphan detection and agent workflow integrity validation | Weekly Sunday 1 AM |
| **PredictionEngine** | ML-powered pattern effectiveness and learning velocity forecasting | Daily 2:15 AM |

### BMAD Agents

9 BMAD agents with persistent learning capabilities:
- **Jay** - Frontend specialist
- **Winston** - Architect
- **Brooks** - Product Manager
- **Dutch** - Security
- **Troy** - DevOps
- **Bob** - Backend specialist
- **Allura** - UX Designer
- **Master** - BMad orchestrator
- **Orchestrator** - Agent coordination

### Multi-Tenant Architecture

Three project groups with scoped knowledge isolation:
- **faith-meats** - Faith-based content platform
- **diff-driven-saas** - SaaS with git diff integration
- **global-coding-skills** - Universal coding patterns (shared across all)

### BMAD Features

- **Event Capture**: GitHub → Event → Solution → Outcome chains
- **Pattern Library**: Reusable solutions tracked with success_rate, usage_count
- **Insight Generation**: Automated pattern detection with confidence scoring
- **Cross-Agent Learning**: Daily knowledge sharing between agents
- **Brain Scoping**: Three-tier knowledge (agent-specific, project-specific, global)
- **Temporal Decay**: Stale insights lose confidence over time
- **ML Predictions**: Pattern effectiveness forecasting, learning velocity tracking

### BMAD Implementation Status

- ✅ **Phase 1 Complete**: Technical Architecture (6 components mapped)
- ✅ **Phase 1 Complete**: Implementation Readiness Check (0 blocking issues)
- ✅ **Phase 2 Complete**: Epics & Stories (5 epics, 16 stories)
- ✅ **Phase 2 Complete**: Prediction System (6 ML models)
- ✅ **Phase 2 Complete**: Distribution System (5 package types)
- ⏳ **Phase 2 In Progress**: Story implementation beginning with Story 1.1

See `_bmad-output/planning-artifacts/epics.md` for complete epic breakdown.

## Features

### 🗄️ Persistent Storage
- Docker named volumes for Neo4j data and backups
- **APOC-based Logical Backups** (Community Edition compatible)
- Automatic schema initialization

### 🔄 Automated Backups
- Sidecar container using `apscheduler`
- `apoc.export.graphml.all` for logical graph dumps
- SHA256 checksum verification
- Configurable retention policy (default: 30 days)

### 🏥 Health Monitoring
- Connectivity checks (5s timeout)
- Orphaned relationship detection
- Fast-fail behavior

### 🐳 Containerization
- **Neo4j 5.13.0 Community**
- **Backup Scheduler Sidecar** (Python 3.9)
- Zero external vector dependencies (No Qdrant/Mem0)

### 🧠 Prediction System
- **Pattern Effectiveness**: Forecast which patterns will succeed (>85% accuracy)
- **Learning Velocity**: Predict weekly insight generation per agent
- **Knowledge Transfer**: Identify optimal cross-agent learning opportunities
- **Performance Degradation**: Detect query latency increases before SLA breach
- **Confidence Scoring**: Pre-compute insight confidence scores
- **Promotion Ranking**: Recommend patterns ready for global promotion

See `_bmad-output/predictions/README.md` for complete documentation.

### 📦 Distribution Packages

BMAD system is available as downloadable packages:

- **bmad-agents** - 9 AI agents with Neo4j schemas
- **bmad-workflows** - Custom workflow system and templates
- **bmad-containers** - Docker-based infrastructure stack
- **bmad-predictions** - ML prediction system
- **bmad-complete** - Complete BMAD system (all-in-one)

#### Building Distribution Packages

```bash
# Build all packages
python scripts/distribution/build_release.py --package all

# Build specific package
python scripts/distribution/build_release.py --package agents

# Create GitHub release
bash scripts/distribution/create_release.sh v1.0.0
```

Packages include:
- Compressed tar.gz archives
- SHA256 checksums for integrity verification
- Installation scripts for each component
- Complete documentation

## Quick Start

### Prerequisites
- Docker & Docker Compose 3.8+
- 4GB+ RAM

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Charitablebusinessronin/neoronin.git
   cd neoronin
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   ```

3. **Start services**:
   ```bash
   docker compose up -d
   ```

4. **Verify startup**:
   ```bash
   # Check services
   docker ps

   # Verify backup capability
   docker exec grap-backup-scheduler python -c "from scripts.backup.neo4j_backup import BackupManager; from neo4j import GraphDatabase; import os; driver = GraphDatabase.driver(os.environ['NEO4J_URI'], auth=(os.environ['NEO4J_USER'], os.environ['NEO4J_PASSWORD'])); bm = BackupManager(driver, os.environ['BACKUP_DIR']); print(bm.create_backup())"
   ```

## Architecture

### Service Architecture

```
┌─────────────────────────────────────────────┐
│          Neo4j Database (5.13.0)            │
│  - Community Edition                        │
│  - APOC Plugin Enabled                      │
│  - BMAD Schema: Event, Solution, Outcome   │
│  - BMAD Schema: Pattern, Insight, AIAgent   │
│  - Volume: grap-neo4j-data (/data)          │
│  - Volume: grap-backups (/import)           │
└────────────┬────────────────────────────────┘
             │
             │ Bolt (7687)
             │
    ┌────────▼────────┐
    │  Backup Sidecar │
    │ (Python 3.9)    │
    │  - Scheduler    │
    │  - Logic Checks │
    │  - Volume:      │
    │    grap-backups │
└───────┤                │
        └────────────────┘

┌─────────────────────────────────────────────┐
│          BMAD Learning Layer                │
│                                             │
│  ┌────────────────────┐  ┌──────────────┐  │
│  │ EventLoggerMiddleware│ │PatternManager│  │
│  │ (Port 8001)         │ │(LRU Cache)   │  │
│  │ - GitHub MCP Hook  │ │- 100 patterns │  │
│  │ - Queue on Failure │ │- 1hr TTL      │  │
│  └────────────────────┘  └──────────────┘  │
│                                             │
│  ┌────────────────────┐  ┌──────────────┐  │
│  │InsightGenerator    │ │RelevanceScore │  │
│  │(Daily 2:00 AM)     │ │(Daily 2:10AM)│  │
│  │ - Pattern Detect   │ │- 90-day decay│  │
│  │ - Confidence Score │ │- Usage boost  │  │
│  └────────────────────┘  └──────────────┘  │
│                                             │
│  ┌────────────────────┐  ┌──────────────┐  │
│  │PredictionEngine    │ │HealthCheckSvc │  │
│  │(Daily 2:15 AM)     │ │(Weekly 1 AM) │  │
│  │ - ML Forecasting   │ │- Orphan det. │  │
│  │ - Pattern Promo    │ │- Schema check│  │
│  └────────────────────┘  └──────────────┘  │
└─────────────────────────────────────────────┘
```

**Note**: We purposely avoid `neo4j-admin` backups to maintain compatibility with standard Docker volumes and Community Edition limitations. We use `apoc.export.graphml.all` to dump the graph structure and data to the shared volume.

## Configuration

### Environment Variables (.env)

| Variable | Default | Description |
|----------|---------|-------------|
| `NEO4J_AUTH` | `neo4j/Kamina2025*` | Database credentials |
| `BACKUP_SCHEDULE` | `0 2 * * *` | Cron schedule (2 AM daily) |
| `BACKUP_RETENTION_DAYS` | `30` | Backup retention period |

## Project Structure

```
Grap/
├── docker/
│   ├── neo4j/              # Database image config
│   └── backup-sidecar/     # Python scheduler logic
├── scripts/
│   ├── backup/             # BackupManager logic (APOC based)
│   ├── health/             # Health check scripts
│   └── distribution/       # Release packaging system
├── src/                    # Shared library code
│   ├── event_logger.py     # EventLoggerMiddleware
│   ├── query_templates.py  # QueryTemplateLibrary
│   ├── pattern_manager.py  # PatternManager
│   ├── insight_generator.py # InsightGeneratorEngine
│   ├── relevance_scoring.py # RelevanceScoringService
│   ├── health_check.py     # HealthCheckService
│   └── predictions/        # ML prediction system
├── _bmad-output/
│   ├── docs/               # PRD, Architecture docs
│   ├── planning-artifacts/ # Epics, readiness reports
│   ├── implementation-artifacts/ # Story files, sprint status
│   ├── predictions/        # Prediction models and forecasts
│   └── schemas/            # BMAD Cypher schema scripts
├── _bmad/                  # BMAD workflow system
│   ├── bmm/                # Workflow definitions
│   └── core/               # Core execution engine
├── dist/                   # Distribution packages output
├── docker-compose.yml      # Service definition
├── PLANNING.md             # Project planning status
└── README.md               # This file
```

## Troubleshooting

### Backup Fails with "FileNotFound"
Ensure the `grap-backups` volume is correctly mounted to `/var/lib/neo4j/import` in the Neo4j container. APOC security settings restrict file writing to this directory.

### Backup Fails with "Export not enabled"
Check `docker-compose.yml` for `NEO4J_apoc_export_file_enabled: "true"`.

### Prediction System Dependencies
Install ML dependencies for prediction system:
```bash
pip install -r _bmad-output/predictions/requirements.txt
```

## Documentation

- **Architecture**: `_bmad-output/docs/architecture/component_map.md`
- **Planning**: `_bmad-output/planning-artifacts/`
- **Prediction System**: `_bmad-output/predictions/README.md`
- **Distribution Guide**: Build packages with `scripts/distribution/build_release.py`

## License

MIT License - See LICENSE file for details.
