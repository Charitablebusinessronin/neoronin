# BMAD Quick Start Guide

Get up and running with the BMAD system in minutes.

## What is BMAD?

**BMAD** (BMad Master Agent Development) is an AI agent memory and learning system built on Neo4j. It enables 9 specialized AI agents to capture, share, and refine knowledge from their work.

### Key Features

✅ **9 Specialized Agents** - Frontend, Backend, Architect, PM, Security, DevOps, UX, Master, Orchestrator  
✅ **Pattern Library** - Reusable solutions with success tracking  
✅ **ML Predictions** - Forecast pattern effectiveness and learning velocity  
✅ **Multi-Tenant** - Scoped knowledge for different projects  
✅ **Automated Learning** - Daily insight generation and knowledge sharing  

## 5-Minute Quick Start

### Prerequisites

- Docker & Docker Compose
- 4GB+ RAM
- Git

### Installation

```bash
# 1. Clone repository
git clone https://github.com/Charitablebusinessronin/neoronin.git
cd neoronin

# 2. Configure environment
cp .env.example .env
# Edit .env and set NEO4J_PASSWORD

# 3. Start services
docker-compose up -d

# 4. Wait for Neo4j to start (30 seconds)
sleep 30

# 5. Verify installation
curl http://localhost:7474
```

### Access Neo4j Browser

Open http://localhost:7474 in your browser:

- **Username:** `neo4j`
- **Password:** (from your `.env` file)
- **Connection:** `bolt://localhost:7687`

### Verify Agents

Run this in Neo4j Browser:

```cypher
MATCH (a:AIAgent)
RETURN a.name AS Agent, a.role AS Role
ORDER BY a.name;
```

You should see 9 agents.

## What's Next?

### Run Prediction System

```bash
# Install dependencies
pip install -r requirements.txt

# Generate predictions
python src/predictions/predict.py
```

### Build Distribution Packages

```bash
# Build all packages
python scripts/distribution/build_release.py --package all

# Packages will be in dist/releases-<version>/
```

### Explore Documentation

- **Architecture**: `_bmad-output/docs/architecture/component_map.md`
- **Planning**: `_bmad-output/planning-artifacts/epics.md`
- **Predictions**: `_bmad-output/predictions/README.md`
- **Distribution**: `docs/DISTRIBUTION_GUIDE.md`

## Common Tasks

### View Agent Events

```cypher
MATCH (e:Event)-[:TRIGGERED_BY]->(a:AIAgent)
RETURN a.name, e.type, e.timestamp
ORDER BY e.timestamp DESC
LIMIT 10;
```

### Find Successful Patterns

```cypher
MATCH (p:Pattern)
WHERE p.success_rate > 0.8
RETURN p.id, p.name, p.success_rate, p.usage_count
ORDER BY p.success_rate DESC;
```

### Check Agent Learning Velocity

```cypher
MATCH (a:AIAgent)<-[:GENERATED_BY]-(i:Insight)
WHERE i.created_at > datetime() - duration({days: 7})
RETURN a.name AS Agent, count(i) AS InsightsThisWeek
ORDER BY InsightsThisWeek DESC;
```

## Troubleshooting

### Neo4j Won't Start

```bash
# Check logs
docker logs grap-neo4j

# Restart services
docker-compose down
docker-compose up -d
```

### Port Already in Use

Edit `docker-compose.yml` and change ports:

```yaml
ports:
  - "17474:7474"  # Changed from 7474
  - "17687:7687"  # Changed from 7687
```

### Permission Denied

```bash
# Fix volume permissions
sudo chown -R 7474:7474 /var/lib/docker/volumes/grap-neo4j-data/
```

## Support

- **GitHub Issues**: https://github.com/Charitablebusinessronin/neoronin/issues
- **Documentation**: `docs/` directory
- **Main README**: `README.md`

---

**Ready to build something amazing? Start exploring!** 🚀
