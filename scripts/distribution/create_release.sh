#!/bin/bash
# BMAD Distribution Release Creator
# Builds all packages and optionally creates GitHub release

set -e

VERSION=${1:-$(git describe --tags --always)}

echo "🚀 Creating BMAD Distribution Release v${VERSION}"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 not found"
    exit 1
fi

# Build all packages
echo "Building all packages..."
python3 scripts/distribution/build_release.py --version "$VERSION" --package all

echo ""
echo "✅ Release v${VERSION} created!"
echo "📦 Packages available in: dist/releases-${VERSION}/"
echo ""

# List created packages
echo "Created packages:"
ls -lh dist/releases-${VERSION}/*.tar.gz | awk '{print "  - " $9 " (" $5 ")"}'

echo ""

# Optionally create GitHub release
if command -v gh &> /dev/null; then
    echo "GitHub CLI detected."
    read -p "Create GitHub release? (y/N) " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "📤 Creating GitHub release v${VERSION}..."
        
        # Create release notes
        RELEASE_NOTES="dist/releases-${VERSION}/RELEASE_NOTES.md"
        cat > "$RELEASE_NOTES" << EOF
# BMAD v${VERSION}

## Distribution Packages

This release includes 5 distribution packages:

- **bmad-agents**: 9 BMAD AI agents with Neo4j schemas
- **bmad-workflows**: Custom workflow system and templates
- **bmad-containers**: Docker-based infrastructure stack
- **bmad-predictions**: ML prediction system for pattern effectiveness
- **bmad-complete**: Complete BMAD system (all-in-one)

## Installation

See individual package README files for installation instructions.

## Verification

All packages include SHA256 checksums for integrity verification:

\`\`\`bash
sha256sum -c <package>.tar.gz.sha256
\`\`\`

## Documentation

- Main README: https://github.com/Charitablebusinessronin/neoronin/blob/main/README.md
- Prediction System: https://github.com/Charitablebusinessronin/neoronin/blob/main/_bmad-output/predictions/README.md

## Release Manifest

See \`RELEASE_MANIFEST.json\` for complete package details.
EOF
        
        gh release create "v${VERSION}" \
            dist/releases-${VERSION}/*.tar.gz \
            dist/releases-${VERSION}/*.sha256 \
            dist/releases-${VERSION}/RELEASE_MANIFEST.json \
            --title "BMAD v${VERSION}" \
            --notes-file "$RELEASE_NOTES" \
            --draft
        
        echo "✅ GitHub release created as DRAFT"
        echo "Review at: https://github.com/Charitablebusinessronin/neoronin/releases"
    fi
else
    echo "📌 To create GitHub release, install GitHub CLI: https://cli.github.com/"
fi

echo ""
echo "🎉 Distribution complete!"
