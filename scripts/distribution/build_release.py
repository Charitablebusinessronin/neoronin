#!/usr/bin/env python3
"""
BMAD Distribution Builder
Creates downloadable packages for agents, workflows, containers, and complete bundles.
"""

import os
import shutil
import tarfile
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict
import subprocess


class BMADDistributionBuilder:
    """Builds distributable packages for BMAD system components."""
    
    def __init__(self, version: str = None):
        self.version = version or self._get_git_version()
        self.build_date = datetime.now().strftime("%Y%m%d")
        self.dist_dir = Path("dist")
        self.dist_dir.mkdir(exist_ok=True)
        
        # Output directories
        self.releases_dir = self.dist_dir / f"releases-{self.version}"
        self.releases_dir.mkdir(exist_ok=True)
        
    def _get_git_version(self) -> str:
        """Get version from git tag or commit."""
        try:
            version = subprocess.check_output(
                ["git", "describe", "--tags", "--always"],
                stderr=subprocess.STDOUT
            ).decode().strip()
            return version
        except:
            return f"dev-{datetime.now().strftime('%Y%m%d')}"
    
    def build_agent_bundle(self) -> Path:
        """
        Package: BMAD Agent Bundle
        Contents: 9 agent definitions + Neo4j schemas
        """
        print(f"📦 Building Agent Bundle v{self.version}...")
        
        bundle_name = f"bmad-agents-{self.version}"
        bundle_dir = self.releases_dir / bundle_name
        bundle_dir.mkdir(exist_ok=True)
        
        # 1. Copy agent definitions
        agents_dir = bundle_dir / "agents"
        agents_dir.mkdir(exist_ok=True)
        
        agent_configs = {
            "jay": {"role": "Frontend Specialist", "color": "blue"},
            "winston": {"role": "Architect", "color": "purple"},
            "brooks": {"role": "Product Manager", "color": "green"},
            "dutch": {"role": "Security Engineer", "color": "red"},
            "troy": {"role": "DevOps Engineer", "color": "orange"},
            "bob": {"role": "Backend Engineer", "color": "navy"},
            "allura": {"role": "UX Designer", "color": "pink"},
            "master": {"role": "BMad Master Orchestrator", "color": "gold"},
            "orchestrator": {"role": "Agent Coordinator", "color": "silver"}
        }
        
        for agent_name, config in agent_configs.items():
            agent_file = agents_dir / f"{agent_name}.json"
            with open(agent_file, "w") as f:
                json.dump({
                    "name": agent_name.capitalize(),
                    "role": config["role"],
                    "color": config["color"],
                    "capabilities": [
                        "event_logging",
                        "pattern_retrieval",
                        "insight_generation",
                        "cross_agent_learning"
                    ],
                    "schema_version": "1.0.0"
                }, f, indent=2)
        
        # 2. Copy Neo4j schemas
        if Path("_bmad-output/schemas").exists():
            self._copy_directory("_bmad-output/schemas", bundle_dir / "schemas")
        
        # 3. Create agent initialization script
        scripts_dir = bundle_dir / "scripts"
        scripts_dir.mkdir(exist_ok=True)
        self._create_agent_init_script(scripts_dir / "init_agents.cypher")
        
        # 4. Create README
        self._create_agent_readme(bundle_dir / "README.md")
        
        # 5. Create installation script
        self._create_agent_installer(bundle_dir / "install.sh")
        
        # 6. Package as tar.gz
        tarball_path = self.releases_dir / f"{bundle_name}.tar.gz"
        self._create_tarball(bundle_dir, tarball_path)
        
        # 7. Generate checksum
        checksum = self._generate_checksum(tarball_path)
        
        print(f"✅ Agent Bundle: {tarball_path.name} ({checksum[:8]})")
        return tarball_path
    
    def build_workflow_package(self) -> Path:
        """
        Package: BMAD Workflow Package
        Contents: Custom workflows + templates + orchestration engine
        """
        print(f"📦 Building Workflow Package v{self.version}...")
        
        package_name = f"bmad-workflows-{self.version}"
        package_dir = self.releases_dir / package_name
        package_dir.mkdir(exist_ok=True)
        
        # 1. Copy BMAD workflow system
        if Path("_bmad").exists():
            self._copy_directory("_bmad", package_dir / "_bmad")
        
        # 2. Copy planning artifacts
        if Path("_bmad-output/planning-artifacts").exists():
            self._copy_directory("_bmad-output/planning-artifacts", package_dir / "planning-artifacts")
        
        # 3. Create README
        self._create_workflow_readme(package_dir / "README.md")
        
        # 4. Create installation script
        self._create_workflow_installer(package_dir / "install.sh")
        
        # 5. Package as tar.gz
        tarball_path = self.releases_dir / f"{package_name}.tar.gz"
        self._create_tarball(package_dir, tarball_path)
        
        checksum = self._generate_checksum(tarball_path)
        print(f"✅ Workflow Package: {tarball_path.name} ({checksum[:8]})")
        return tarball_path
    
    def build_container_stack(self) -> Path:
        """
        Package: Container Stack
        Contents: Docker images + compose files + infrastructure scripts
        """
        print(f"📦 Building Container Stack v{self.version}...")
        
        stack_name = f"bmad-containers-{self.version}"
        stack_dir = self.releases_dir / stack_name
        stack_dir.mkdir(exist_ok=True)
        
        # 1. Copy Docker compose files
        if Path("docker-compose.yml").exists():
            shutil.copy("docker-compose.yml", stack_dir / "docker-compose.yml")
        if Path(".env.example").exists():
            shutil.copy(".env.example", stack_dir / ".env.example")
        
        # 2. Copy Docker build contexts
        if Path("docker").exists():
            self._copy_directory("docker", stack_dir / "docker")
        
        # 3. Copy scripts
        if Path("scripts").exists():
            self._copy_directory("scripts", stack_dir / "scripts")
        
        # 4. Copy source code
        if Path("src").exists():
            self._copy_directory("src", stack_dir / "src")
        
        # 5. Create deployment guide
        self._create_deployment_guide(stack_dir / "DEPLOYMENT.md")
        
        # 6. Create deployment script
        self._create_deployment_script(stack_dir / "deploy.sh")
        
        # 7. Package as tar.gz
        tarball_path = self.releases_dir / f"{stack_name}.tar.gz"
        self._create_tarball(stack_dir, tarball_path)
        
        checksum = self._generate_checksum(tarball_path)
        print(f"✅ Container Stack: {tarball_path.name} ({checksum[:8]})")
        return tarball_path
    
    def build_prediction_system(self) -> Path:
        """
        Package: Prediction System
        Contents: ML models + prediction engine + training scripts
        """
        print(f"📦 Building Prediction System v{self.version}...")
        
        pred_name = f"bmad-predictions-{self.version}"
        pred_dir = self.releases_dir / pred_name
        pred_dir.mkdir(exist_ok=True)
        
        # 1. Copy prediction system
        if Path("_bmad-output/predictions").exists():
            self._copy_directory("_bmad-output/predictions", pred_dir / "predictions")
        
        # 2. Copy prediction source code
        if Path("src/predictions").exists():
            pred_src_dir = pred_dir / "src/predictions"
            pred_src_dir.mkdir(parents=True, exist_ok=True)
            self._copy_directory("src/predictions", pred_src_dir)
        
        # 3. Copy schemas
        if Path("_bmad-output/schemas/predictions").exists():
            self._copy_directory("_bmad-output/schemas/predictions", pred_dir / "schemas")
        
        # 4. Create requirements.txt
        self._create_prediction_requirements(pred_dir / "requirements.txt")
        
        # 5. Create README
        self._create_prediction_readme(pred_dir / "README.md")
        
        # 6. Create installation script
        self._create_prediction_installer(pred_dir / "install.sh")
        
        # 7. Package as tar.gz
        tarball_path = self.releases_dir / f"{pred_name}.tar.gz"
        self._create_tarball(pred_dir, tarball_path)
        
        checksum = self._generate_checksum(tarball_path)
        print(f"✅ Prediction System: {tarball_path.name} ({checksum[:8]})")
        return tarball_path
    
    def build_complete_bundle(self) -> Path:
        """
        Package: Complete BMAD System
        Contents: Everything (agents + workflows + containers + predictions)
        """
        print(f"📦 Building Complete Bundle v{self.version}...")
        
        bundle_name = f"bmad-complete-{self.version}"
        bundle_dir = self.releases_dir / bundle_name
        bundle_dir.mkdir(exist_ok=True)
        
        # Copy entire repository structure (filtered)
        exclude_patterns = [
            ".git",
            "dist",
            "__pycache__",
            "*.pyc",
            ".env",
            "venv",
            ".venv",
            "node_modules",
            "*.egg-info"
        ]
        
        print("  📋 Copying repository files...")
        self._copy_directory_filtered(".", bundle_dir, exclude_patterns)
        
        # Create comprehensive README
        self._create_complete_readme(bundle_dir / "README.md")
        
        # Create quick-start script
        self._create_quickstart_script(bundle_dir / "quickstart.sh")
        
        # Create uninstall script
        self._create_uninstall_script(bundle_dir / "uninstall.sh")
        
        # Package as tar.gz
        tarball_path = self.releases_dir / f"{bundle_name}.tar.gz"
        self._create_tarball(bundle_dir, tarball_path)
        
        checksum = self._generate_checksum(tarball_path)
        print(f"✅ Complete Bundle: {tarball_path.name} ({checksum[:8]})")
        return tarball_path
    
    def build_all(self) -> Dict[str, Path]:
        """Build all distribution packages."""
        print(f"\n🚀 Building BMAD Distribution v{self.version}\n")
        
        packages = {
            "agents": self.build_agent_bundle(),
            "workflows": self.build_workflow_package(),
            "containers": self.build_container_stack(),
            "predictions": self.build_prediction_system(),
            "complete": self.build_complete_bundle()
        }
        
        # Create release manifest
        self._create_release_manifest(packages)
        
        print(f"\n✅ Distribution complete! Files in: {self.releases_dir}\n")
        return packages
    
    # ========== Helper Methods ==========
    
    def _copy_directory(self, src: str, dst: Path):
        """Copy directory recursively."""
        if Path(src).exists():
            shutil.copytree(src, dst, dirs_exist_ok=True)
    
    def _copy_directory_filtered(self, src: str, dst: Path, exclude: List[str]):
        """Copy directory with exclusions."""
        for item in Path(src).rglob("*"):
            if any(pattern in str(item) for pattern in exclude):
                continue
            
            rel_path = item.relative_to(src)
            dst_path = dst / rel_path
            
            if item.is_dir():
                dst_path.mkdir(parents=True, exist_ok=True)
            else:
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dst_path)
    
    def _create_tarball(self, source_dir: Path, output_path: Path):
        """Create compressed tarball."""
        with tarfile.open(output_path, "w:gz") as tar:
            tar.add(source_dir, arcname=source_dir.name)
    
    def _generate_checksum(self, filepath: Path) -> str:
        """Generate SHA256 checksum."""
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        
        checksum = sha256.hexdigest()
        
        # Write checksum file
        checksum_path = filepath.with_suffix(filepath.suffix + ".sha256")
        with open(checksum_path, "w") as f:
            f.write(f"{checksum}  {filepath.name}\n")
        
        return checksum
    
    def _create_agent_init_script(self, filepath: Path):
        """Create Cypher script to initialize agents."""
        cypher_script = '''// BMAD Agent Initialization Script
// Creates 9 AI agents with their roles and capabilities

CREATE CONSTRAINT agent_id_unique IF NOT EXISTS FOR (a:AIAgent) REQUIRE a.id IS UNIQUE;

MERGE (jay:AIAgent {id: "jay"})
SET jay.name = "Jay",
    jay.role = "Frontend Specialist",
    jay.color = "blue",
    jay.created_at = datetime();

MERGE (winston:AIAgent {id: "winston"})
SET winston.name = "Winston",
    winston.role = "Architect",
    winston.color = "purple",
    winston.created_at = datetime();

MERGE (brooks:AIAgent {id: "brooks"})
SET brooks.name = "Brooks",
    brooks.role = "Product Manager",
    brooks.color = "green",
    brooks.created_at = datetime();

MERGE (dutch:AIAgent {id: "dutch"})
SET dutch.name = "Dutch",
    dutch.role = "Security Engineer",
    dutch.color = "red",
    dutch.created_at = datetime();

MERGE (troy:AIAgent {id: "troy"})
SET troy.name = "Troy",
    troy.role = "DevOps Engineer",
    troy.color = "orange",
    troy.created_at = datetime();

MERGE (bob:AIAgent {id: "bob"})
SET bob.name = "Bob",
    bob.role = "Backend Engineer",
    bob.color = "navy",
    bob.created_at = datetime();

MERGE (allura:AIAgent {id: "allura"})
SET allura.name = "Allura",
    allura.role = "UX Designer",
    allura.color = "pink",
    allura.created_at = datetime();

MERGE (master:AIAgent {id: "master"})
SET master.name = "BMad Master",
    master.role = "Master Orchestrator",
    master.color = "gold",
    master.created_at = datetime();

MERGE (orchestrator:AIAgent {id: "orchestrator"})
SET orchestrator.name = "Orchestrator",
    orchestrator.role = "Agent Coordinator",
    orchestrator.color = "silver",
    orchestrator.created_at = datetime();
'''
        with open(filepath, "w") as f:
            f.write(cypher_script)
    
    def _create_agent_readme(self, filepath: Path):
        """Create README for agent bundle."""
        readme = f'''# BMAD Agent Bundle v{self.version}

## Contents

This package contains the complete set of 9 BMAD AI agents with their Neo4j schemas and initialization scripts.

### Agents Included

1. **Jay** - Frontend Specialist (Blue)
2. **Winston** - Architect (Purple)
3. **Brooks** - Product Manager (Green)
4. **Dutch** - Security Engineer (Red)
5. **Troy** - DevOps Engineer (Orange)
6. **Bob** - Backend Engineer (Navy)
7. **Allura** - UX Designer (Pink)
8. **Master** - BMad Master Orchestrator (Gold)
9. **Orchestrator** - Agent Coordinator (Silver)

## Installation

### Quick Install

```bash
# Extract the bundle
tar -xzf bmad-agents-{self.version}.tar.gz
cd bmad-agents-{self.version}

# Run installation script
./install.sh --neo4j-uri bolt://localhost:7687 --neo4j-password your_password
```

## Verification

```cypher
MATCH (a:AIAgent)
RETURN a.name AS Agent, a.role AS Role, a.color AS Color
ORDER BY a.name;
```

**Version:** {self.version}  
**Build Date:** {self.build_date}
'''
        with open(filepath, "w") as f:
            f.write(readme)
    
    def _create_agent_installer(self, filepath: Path):
        """Create bash installation script for agents."""
        installer = '''#!/bin/bash
set -e

NEO4J_URI=${1:-"bolt://localhost:7687"}
NEO4J_USER=${2:-"neo4j"}
NEO4J_PASSWORD=${3}

if [ -z "$NEO4J_PASSWORD" ]; then
    echo "Usage: ./install.sh [NEO4J_URI] [NEO4J_USER] <NEO4J_PASSWORD>"
    exit 1
fi

echo "🚀 Installing BMAD Agents..."
echo "  Neo4j URI: $NEO4J_URI"

cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" < scripts/init_agents.cypher

AGENT_COUNT=$(cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" --format plain "MATCH (a:AIAgent) RETURN count(a)" | tail -n 1)

if [ "$AGENT_COUNT" -eq 9 ]; then
    echo "✅ Success! All 9 agents installed."
else
    echo "⚠️  Warning: Expected 9 agents, found $AGENT_COUNT"
fi
'''
        with open(filepath, "w") as f:
            f.write(installer)
        filepath.chmod(0o755)
    
    def _create_workflow_readme(self, filepath: Path):
        readme = f"# BMAD Workflow Package v{self.version}\n\nCustom workflows and templates for the BMAD system.\n"
        with open(filepath, "w") as f:
            f.write(readme)
    
    def _create_workflow_installer(self, filepath: Path):
        installer = '''#!/bin/bash
set -e
TARGET_DIR=${1:-.}
cp -r _bmad "$TARGET_DIR/_bmad"
echo "✅ Workflows installed!"
'''
        with open(filepath, "w") as f:
            f.write(installer)
        filepath.chmod(0o755)
    
    def _create_deployment_guide(self, filepath: Path):
        guide = f"# BMAD Container Stack Deployment Guide\n\nVersion: {self.version}\n"
        with open(filepath, "w") as f:
            f.write(guide)
    
    def _create_deployment_script(self, filepath: Path):
        script = '''#!/bin/bash
set -e
echo "🚀 Deploying BMAD Container Stack..."
docker-compose up -d
echo "✅ Deployed!"
'''
        with open(filepath, "w") as f:
            f.write(script)
        filepath.chmod(0o755)
    
    def _create_prediction_requirements(self, filepath: Path):
        requirements = '''scikit-learn==1.3.2
statsmodels==0.14.0
torch==2.1.0
pandas==2.1.3
numpy==1.26.2
joblib==1.3.2
shap==0.43.0
neo4j==5.14.0
'''
        with open(filepath, "w") as f:
            f.write(requirements)
    
    def _create_prediction_readme(self, filepath: Path):
        readme = f"# BMAD Prediction System v{self.version}\n\nML-powered forecasting for agent learning patterns.\n"
        with open(filepath, "w") as f:
            f.write(readme)
    
    def _create_prediction_installer(self, filepath: Path):
        installer = '''#!/bin/bash
set -e
echo "🚀 Installing BMAD Prediction System..."
pip install -r requirements.txt
echo "✅ Installed!"
'''
        with open(filepath, "w") as f:
            f.write(installer)
        filepath.chmod(0o755)
    
    def _create_complete_readme(self, filepath: Path):
        readme = f'''# BMAD Complete System v{self.version}

The complete BMAD system with agents, workflows, containers, and predictions.

## Quick Start

```bash
./quickstart.sh
```

**Version:** {self.version}  
**Build Date:** {self.build_date}
'''
        with open(filepath, "w") as f:
            f.write(readme)
    
    def _create_quickstart_script(self, filepath: Path):
        script = '''#!/bin/bash
set -e
echo "🚀 BMAD System Quick Start"
echo "Deploying container stack..."
docker-compose up -d
echo "✅ BMAD System deployed!"
'''
        with open(filepath, "w") as f:
            f.write(script)
        filepath.chmod(0o755)
    
    def _create_uninstall_script(self, filepath: Path):
        script = '''#!/bin/bash
set -e
echo "🗑️  Uninstalling BMAD System..."
docker-compose down
echo "✅ Uninstalled!"
'''
        with open(filepath, "w") as f:
            f.write(script)
        filepath.chmod(0o755)
    
    def _create_release_manifest(self, packages: Dict[str, Path]):
        """Create release manifest JSON."""
        manifest = {
            "version": self.version,
            "build_date": datetime.now().isoformat(),
            "packages": {}
        }
        
        for pkg_type, pkg_path in packages.items():
            checksum_file = pkg_path.with_suffix(pkg_path.suffix + ".sha256")
            if checksum_file.exists():
                with open(checksum_file, "r") as f:
                    checksum = f.read().split()[0]
            else:
                checksum = "unknown"
            
            manifest["packages"][pkg_type] = {
                "filename": pkg_path.name,
                "size_bytes": pkg_path.stat().st_size if pkg_path.exists() else 0,
                "sha256": checksum
            }
        
        manifest_path = self.releases_dir / "RELEASE_MANIFEST.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
        
        print(f"📋 Release manifest: {manifest_path}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Build BMAD distribution packages")
    parser.add_argument("--version", help="Release version (default: git tag)")
    parser.add_argument("--package", choices=["agents", "workflows", "containers", "predictions", "complete", "all"],
                       default="all", help="Package type to build")
    
    args = parser.parse_args()
    
    builder = BMADDistributionBuilder(version=args.version)
    
    if args.package == "all":
        builder.build_all()
    elif args.package == "agents":
        builder.build_agent_bundle()
    elif args.package == "workflows":
        builder.build_workflow_package()
    elif args.package == "containers":
        builder.build_container_stack()
    elif args.package == "predictions":
        builder.build_prediction_system()
    elif args.package == "complete":
        builder.build_complete_bundle()


if __name__ == "__main__":
    main()
