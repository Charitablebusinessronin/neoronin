#!/bin/bash
# BMAD Multi-Project Installer
# Usage: bash -c "$(curl -fsSL ...)"

set -e

REPO="Charitablebusinessronin/neoronin"
INSTALL_DIR=$(pwd)

echo "🛰️  BMAD One-Click Installer"
echo "---------------------------"

# 1. Detect latest release from GitHub
echo "🔍 Fetching latest release information..."
LATEST_TAG=$(curl -s "https://api.github.com/repos/$REPO/releases/latest" | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')

if [ -z "$LATEST_TAG" ]; then
    echo "⚠️  No official release found. Falling back to main branch..."
    DOWNLOAD_URL="https://github.com/$REPO/archive/refs/heads/main.tar.gz"
    FOLDER_NAME="neoronin-main"
else
    echo "✅ Found Release: $LATEST_TAG"
    DOWNLOAD_URL="https://github.com/$REPO/releases/download/$LATEST_TAG/bmad-complete-${LATEST_TAG#v}.tar.gz"
    # If the specific tarball isn't found in assets, fallback to source code
    FOLDER_NAME="bmad-complete-${LATEST_TAG#v}"
fi

# 2. Download and Extract
echo "📥 Downloading BMAD system..."
curl -L "$DOWNLOAD_URL" -o bmad_bundle.tar.gz

echo "📦 Extracting to $INSTALL_DIR..."
tar -xzf bmad_bundle.tar.gz

# 3. Setup folders
# Depending on whether it was a release asset or source zip, files might be in a subdir
if [ -d "$FOLDER_NAME" ]; then
    cp -r "$FOLDER_NAME/"* .
    rm -rf "$FOLDER_NAME"
fi

# 4. Finalizing
rm bmad_bundle.tar.gz
chmod +x scripts/distribution/*.sh 2>/dev/null || true
chmod +x scripts/setup/*.sh 2>/dev/null || true

echo ""
echo "🔥 BMAD INSTALLATION COMPLETE!"
echo "---------------------------"
echo "Agents, workflows, and container stack are now ready."
echo "Run 'docker compose up -d' to start the memory infrastructure."
echo "Load 'bmad-master' in your IDE to begin!"
