# BMAD Distribution Guide

Complete guide for building, packaging, and distributing BMAD system components.

## Overview

The BMAD distribution system creates five types of downloadable packages:

| Package | Size | Contents | Use Case |
|---------|------|----------|----------|
| **bmad-agents** | ~2 MB | 9 AI agents + Neo4j schemas | Add agents to existing Neo4j |
| **bmad-workflows** | ~5 MB | Workflow system + templates | Extend existing BMAD |
| **bmad-containers** | ~800 MB | Docker stack + infrastructure | Deploy complete infrastructure |
| **bmad-predictions** | ~50 MB | ML models + prediction engine | Add forecasting to existing system |
| **bmad-complete** | ~850 MB | Everything | Full system deployment |

## Quick Start

### Build All Packages

```bash
python scripts/distribution/build_release.py --package all
```

Output will be in `dist/releases-<version>/`

### Build Specific Package

```bash
# Build only agent bundle
python scripts/distribution/build_release.py --package agents

# Build only prediction system
python scripts/distribution/build_release.py --package predictions
```

### Create GitHub Release

```bash
bash scripts/distribution/create_release.sh v1.0.0
```

## Distribution Builder

### Command-Line Options

```bash
python scripts/distribution/build_release.py [OPTIONS]

Options:
  --version VERSION    Release version (default: git tag/commit)
  --package TYPE       Package type: agents, workflows, containers,
                       predictions, complete, or all
  -h, --help          Show help message
```

### Package Types

#### 1. Agent Bundle (`bmad-agents`)

**Contents:**
- 9 agent JSON configurations (Jay, Winston, Brooks, Dutch, Troy, Bob, Allura, Master, Orchestrator)
- Neo4j schema files
- Agent initialization Cypher script
- Installation script (`install.sh`)
- README with setup instructions

**Installation:**
```bash
tar -xzf bmad-agents-v1.0.0.tar.gz
cd bmad-agents-v1.0.0
./install.sh bolt://localhost:7687 neo4j your_password
```

**Verification:**
```cypher
MATCH (a:AIAgent)
RETURN a.name, a.role, a.color
ORDER BY a.name;
```

Expected: 9 agents with roles and colors.

#### 2. Workflow Package (`bmad-workflows`)

**Contents:**
- `_bmad/` workflow system
- Workflow templates
- Planning artifacts
- Installation script
- README

**Installation:**
```bash
tar -xzf bmad-workflows-v1.0.0.tar.gz
cd bmad-workflows-v1.0.0
./install.sh /path/to/your/project
```

**Usage:**
```bash
bmad run technical-architecture-workflow --input PRD.md
```

#### 3. Container Stack (`bmad-containers`)

**Contents:**
- `docker-compose.yml`
- Docker build contexts (`docker/`)
- Infrastructure scripts (`scripts/`)
- Source code (`src/`)
- Deployment guide
- Deployment script (`deploy.sh`)

**Installation:**
```bash
tar -xzf bmad-containers-v1.0.0.tar.gz
cd bmad-containers-v1.0.0

# Configure environment
cp .env.example .env
edit .env  # Set your passwords

# Deploy
./deploy.sh
```

**Verification:**
```bash
docker ps  # Should show neo4j and backup-scheduler
curl http://localhost:7474  # Neo4j Browser
```

#### 4. Prediction System (`bmad-predictions`)

**Contents:**
- Prediction system documentation
- Trained ML models (if available)
- Prediction source code
- JSON schemas
- `requirements.txt`
- Installation script

**Installation:**
```bash
tar -xzf bmad-predictions-v1.0.0.tar.gz
cd bmad-predictions-v1.0.0

# Install dependencies
pip install -r requirements.txt

# Run installation
./install.sh
```

**Usage:**
```bash
# Train models
python src/predictions/train_models.py

# Generate predictions
python src/predictions/predict.py --model pattern_effectiveness
```

#### 5. Complete Bundle (`bmad-complete`)

**Contents:**
- Entire repository (filtered)
- All agents, workflows, containers, and predictions
- Comprehensive README
- Quick-start script
- Uninstall script

**Installation:**
```bash
tar -xzf bmad-complete-v1.0.0.tar.gz
cd bmad-complete-v1.0.0

# One-command deployment
./quickstart.sh
```

This will:
1. Deploy Docker container stack
2. Initialize Neo4j with BMAD schema
3. Install agents
4. Set up workflows
5. Configure prediction system

## Package Verification

### SHA256 Checksums

All packages include SHA256 checksums for integrity verification:

```bash
# Verify package integrity
sha256sum -c bmad-agents-v1.0.0.tar.gz.sha256

# Expected output:
# bmad-agents-v1.0.0.tar.gz: OK
```

### Release Manifest

Each release includes `RELEASE_MANIFEST.json` with package metadata:

```json
{
  "version": "v1.0.0",
  "build_date": "2026-01-26T08:30:00Z",
  "packages": {
    "agents": {
      "filename": "bmad-agents-v1.0.0.tar.gz",
      "size_bytes": 2048576,
      "sha256": "abc123..."
    }
  }
}
```

## GitHub Release Workflow

### Manual Release

1. **Build packages:**
   ```bash
   bash scripts/distribution/create_release.sh v1.0.0
   ```

2. **Confirm GitHub release creation** when prompted

3. **Review draft release** at: https://github.com/Charitablebusinessronin/neoronin/releases

4. **Publish release** after review

### Automated Release (CI/CD)

See `.github/workflows/build-release.yml` for automated release pipeline (Phase 4).

## Distribution Structure

```
dist/
└── releases-v1.0.0/
    ├── bmad-agents-v1.0.0/
    │   ├── agents/
    │   │   ├── jay.json
    │   │   ├── winston.json
    │   │   └── ... (7 more)
    │   ├── schemas/
    │   ├── scripts/
    │   │   └── init_agents.cypher
    │   ├── install.sh
    │   └── README.md
    ├── bmad-agents-v1.0.0.tar.gz
    ├── bmad-agents-v1.0.0.tar.gz.sha256
    ├── bmad-workflows-v1.0.0.tar.gz
    ├── bmad-workflows-v1.0.0.tar.gz.sha256
    ├── bmad-containers-v1.0.0.tar.gz
    ├── bmad-containers-v1.0.0.tar.gz.sha256
    ├── bmad-predictions-v1.0.0.tar.gz
    ├── bmad-predictions-v1.0.0.tar.gz.sha256
    ├── bmad-complete-v1.0.0.tar.gz
    ├── bmad-complete-v1.0.0.tar.gz.sha256
    └── RELEASE_MANIFEST.json
```

## Advanced Usage

### Custom Version Tagging

```bash
# Use semantic versioning
python scripts/distribution/build_release.py --version v1.2.3

# Use date-based versioning
python scripts/distribution/build_release.py --version $(date +%Y.%m.%d)

# Use custom tag
python scripts/distribution/build_release.py --version alpha-2026-01-26
```

### Filtering Package Contents

Edit `build_release.py` to customize exclusion patterns:

```python
exclude_patterns = [
    ".git",
    "dist",
    "__pycache__",
    "*.pyc",
    ".env",
    "venv",
    ".venv",
    "node_modules",
    "*.egg-info",
    "your_custom_exclusion"
]
```

### Docker Image Export

The container stack package can optionally include Docker images:

```bash
# Export Docker images for offline deployment
docker save neo4j:5.13.0-community -o images/neo4j-5.13.0.tar
docker save grap-backup-scheduler:latest -o images/backup-scheduler.tar

# Include in container package
python scripts/distribution/build_release.py --package containers
```

## Distribution Best Practices

### Version Naming Conventions

- **Major releases**: `v1.0.0`, `v2.0.0` (breaking changes)
- **Minor releases**: `v1.1.0`, `v1.2.0` (new features)
- **Patch releases**: `v1.0.1`, `v1.0.2` (bug fixes)
- **Dev builds**: `dev-20260126`, `alpha-v1.0.0`

### Release Checklist

- [ ] Update version in `__init__.py` files
- [ ] Update CHANGELOG.md with release notes
- [ ] Test all packages in clean environment
- [ ] Verify checksums
- [ ] Review README files in each package
- [ ] Test installation scripts
- [ ] Create GitHub release as draft
- [ ] Review and publish release

### Security Considerations

1. **Never include secrets** in distribution packages:
   - Remove `.env` files
   - Exclude API keys and passwords
   - Filter out private configurations

2. **Verify package integrity:**
   - Always check SHA256 checksums
   - Use HTTPS for downloads
   - Verify GitHub release signatures

3. **Installation security:**
   - Review installation scripts before execution
   - Use principle of least privilege
   - Validate input parameters

## Troubleshooting

### Build Fails with "git not found"

**Solution:** Install Git or specify version manually:
```bash
python scripts/distribution/build_release.py --version v1.0.0
```

### Package Too Large

**Solution:** Exclude unnecessary files by editing `exclude_patterns` in `build_release.py`.

### Missing Dependencies

**Solution:** Install required Python packages:
```bash
pip install -r requirements.txt
```

### GitHub Release Fails

**Solution:** Install and authenticate GitHub CLI:
```bash
# Install gh CLI
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo tee /usr/share/keyrings/githubcli-archive-keyring.gpg

# Authenticate
gh auth login
```

## Support

For issues or questions:
- **GitHub Issues**: https://github.com/Charitablebusinessronin/neoronin/issues
- **Documentation**: `_bmad-output/docs/`
- **Architecture**: `_bmad-output/docs/architecture/component_map.md`

---

**Version:** 1.0.0  
**Last Updated:** 2026-01-26  
**Maintainer:** Winston (Architect)
