#!/bin/bash

# Setup and verification script for Graphiti MCP server
# Usage: ./scripts/setup/setup-graphiti-mcp.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
CONTAINER_NAME="grap-graphiti-mcp"
NEO4J_CONTAINER="grap-neo4j"
ENV_FILE=".env"

echo "=========================================="
echo "Graphiti MCP Server Setup & Verification"
echo "=========================================="
echo ""

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
    else
        echo -e "${RED}✗${NC} $2"
    fi
}

# Function to print warning
print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Step 1: Check prerequisites
echo "Step 1: Checking prerequisites..."
echo "-----------------------------------"

# Check Docker
if command -v docker &> /dev/null; then
    print_status 0 "Docker is installed"
else
    print_status 1 "Docker is not installed"
    exit 1
fi

# Check Docker Compose
if command -v docker-compose &> /dev/null || docker compose version &> /dev/null; then
    print_status 0 "Docker Compose is available"
else
    print_status 1 "Docker Compose is not available"
    exit 1
fi

# Check .env file exists
if [ -f "$ENV_FILE" ]; then
    print_status 0 ".env file exists"
else
    print_warning ".env file not found. Copying from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        print_status 0 "Created .env from .env.example"
        print_warning "Please edit .env and add your OPENAI_API_KEY"
    else
        print_status 1 ".env.example not found"
        exit 1
    fi
fi

echo ""

# Step 2: Verify environment configuration
echo "Step 2: Verifying environment configuration..."
echo "-----------------------------------"

# Check OpenAI API key
if grep -q "OPENAI_API_KEY=" "$ENV_FILE" && ! grep -q "OPENAI_API_KEY=your_openai_api_key_here" "$ENV_FILE" && ! grep -q "^#.*OPENAI_API_KEY" "$ENV_FILE"; then
    API_KEY=$(grep "^OPENAI_API_KEY=" "$ENV_FILE" | cut -d '=' -f2- | tr -d '"' | tr -d "'")
    if [ -n "$API_KEY" ] && [ "$API_KEY" != "sk-" ]; then
        print_status 0 "OPENAI_API_KEY is configured"
    else
        print_warning "OPENAI_API_KEY appears to be a placeholder. Please set a valid key in .env"
    fi
else
    print_warning "OPENAI_API_KEY not found or is a placeholder in .env"
    print_warning "Add: OPENAI_API_KEY=sk-your-actual-key-here"
fi

# Check Neo4j configuration
if grep -q "NEO4J_USER=" "$ENV_FILE"; then
    print_status 0 "NEO4J_USER is configured"
else
    print_warning "NEO4J_USER not found in .env (using default: neo4j)"
fi

if grep -q "NEO4J_PASSWORD=" "$ENV_FILE"; then
    print_status 0 "NEO4J_PASSWORD is configured"
else
    print_warning "NEO4J_PASSWORD not found in .env (using default: changeme)"
fi

echo ""

# Step 3: Check Neo4j service
echo "Step 3: Verifying Neo4j service..."
echo "-----------------------------------"

if docker ps --format '{{.Names}}' | grep -q "^${NEO4J_CONTAINER}$"; then
    print_status 0 "Neo4j container is running"
    
    # Test Neo4j connectivity
    if docker exec "$NEO4J_CONTAINER" cypher-shell -u neo4j -p changeme "RETURN 1" &> /dev/null; then
        print_status 0 "Neo4j is accessible and responding"
    else
        print_warning "Neo4j container is running but not responding to queries"
        print_warning "Check Neo4j logs: docker logs $NEO4J_CONTAINER"
    fi
else
    print_status 1 "Neo4j container is not running"
    print_warning "Start Neo4j first: docker-compose up -d neo4j"
    exit 1
fi

echo ""

# Step 4: Build Graphiti MCP container
echo "Step 4: Building Graphiti MCP container..."
echo "-----------------------------------"

if docker-compose build graphiti-mcp 2>&1 | tee /tmp/graphiti-build.log; then
    print_status 0 "Graphiti MCP container built successfully"
else
    print_status 1 "Graphiti MCP container build failed"
    echo "Build logs saved to /tmp/graphiti-build.log"
    exit 1
fi

echo ""

# Step 5: Start Graphiti MCP service
echo "Step 5: Starting Graphiti MCP service..."
echo "-----------------------------------"

if docker-compose up -d graphiti-mcp; then
    print_status 0 "Graphiti MCP service started"
    
    # Wait a moment for service to initialize
    sleep 3
    
    # Check if container is running
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        print_status 0 "Graphiti MCP container is running"
    else
        print_status 1 "Graphiti MCP container failed to start"
        echo "Check logs: docker logs $CONTAINER_NAME"
        exit 1
    fi
else
    print_status 1 "Failed to start Graphiti MCP service"
    exit 1
fi

echo ""

# Step 6: Verify Graphiti MCP service health
echo "Step 6: Verifying Graphiti MCP service health..."
echo "-----------------------------------"

# Check container logs for errors
if docker logs "$CONTAINER_NAME" 2>&1 | grep -i "error\|exception\|traceback" > /dev/null; then
    print_warning "Errors found in Graphiti MCP logs"
    echo "Recent logs:"
    docker logs "$CONTAINER_NAME" --tail 20
else
    print_status 0 "No errors in Graphiti MCP logs"
fi

# Test Neo4j connectivity from Graphiti container
if docker exec "$CONTAINER_NAME" python -c "
from neo4j import GraphDatabase
try:
    driver = GraphDatabase.driver('bolt://neo4j:7687', auth=('neo4j', 'changeme'))
    with driver.session() as session:
        session.run('RETURN 1')
    driver.close()
    exit(0)
except Exception as e:
    print(f'Error: {e}')
    exit(1)
" 2>&1; then
    print_status 0 "Graphiti MCP can connect to Neo4j"
else
    print_warning "Graphiti MCP cannot connect to Neo4j"
    print_warning "Check network configuration and Neo4j credentials"
fi

# Check if uv is available
if docker exec "$CONTAINER_NAME" uv --version &> /dev/null; then
    print_status 0 "uv package manager is available"
else
    print_warning "uv package manager not found (may cause issues)"
fi

echo ""

# Step 7: Test MCP server execution
echo "Step 7: Testing MCP server execution..."
echo "-----------------------------------"

# Test that the MCP server can start (timeout after 5 seconds)
if timeout 5 docker exec -i "$CONTAINER_NAME" sh -c "cd /app/graphiti/mcp_server && uv run python main.py --help" &> /dev/null || \
   docker exec "$CONTAINER_NAME" test -f /app/graphiti/mcp_server/main.py; then
    print_status 0 "Graphiti MCP server script is available"
else
    print_warning "Cannot verify Graphiti MCP server script"
    print_warning "Check Dockerfile installation steps"
fi

echo ""

# Step 8: Summary and next steps
echo "=========================================="
echo "Setup Summary"
echo "=========================================="
echo ""

# Container status
if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo -e "${GREEN}✓${NC} Graphiti MCP container: RUNNING"
    CONTAINER_ID=$(docker ps --format '{{.ID}}' --filter "name=${CONTAINER_NAME}")
    echo "  Container ID: $CONTAINER_ID"
else
    echo -e "${RED}✗${NC} Graphiti MCP container: NOT RUNNING"
fi

echo ""
echo "Next Steps:"
echo "-----------"
echo "1. Configure Cursor IDE:"
echo "   - Open Cursor Settings > Features > Model Context Protocol"
echo "   - Add server with command: docker exec -i $CONTAINER_NAME sh -c 'cd /app/graphiti/mcp_server && uv run python main.py --database-provider neo4j --transport stdio'"
echo "   - See docs/MCP_SETUP.md for detailed instructions"
echo ""
echo "2. Test the connection:"
echo "   - Restart Cursor IDE"
echo "   - Try using Graphiti MCP tools in a chat session"
echo ""
echo "3. Monitor the service:"
echo "   - View logs: docker logs -f $CONTAINER_NAME"
echo "   - Check status: docker ps | grep $CONTAINER_NAME"
echo ""
echo "4. Verify memory operations:"
echo "   - Add a test fact via MCP tools"
echo "   - Query Neo4j: docker exec $NEO4J_CONTAINER cypher-shell -u neo4j -p changeme"
echo "   - Run: MATCH (f:Fact) RETURN f LIMIT 5;"
echo ""
echo "For detailed documentation, see:"
echo "  - docs/MCP_SETUP.md (comprehensive guide)"
echo "  - docs/OPERATOR_GUIDE.md (operational procedures)"
echo "  - README.md (project overview)"
echo ""

# Final status
if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo -e "${GREEN}Setup completed successfully!${NC}"
    exit 0
else
    echo -e "${RED}Setup completed with warnings. Please review the output above.${NC}"
    exit 1
fi

