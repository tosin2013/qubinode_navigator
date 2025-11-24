#!/bin/bash
# Helper script to start Airflow with MCP server support
# Usage: ./start-mcp-services.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}Starting Airflow with MCP Server Support${NC}"
echo -e "${BLUE}============================================================${NC}"

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Warning: .env file not found${NC}"
    echo "Creating default .env from template..."
    cp .env.example .env 2>/dev/null || echo "# Add your configuration here" > .env
fi

# Check if MCP is enabled
source .env 2>/dev/null || true
MCP_ENABLED="${AIRFLOW_MCP_ENABLED:-false}"

if [ "$MCP_ENABLED" == "true" ]; then
    echo -e "${GREEN}✓ MCP Server is enabled${NC}"
    echo "  Port: ${AIRFLOW_MCP_PORT:-8889}"
    echo "  Starting with MCP profile..."
    
    # Start with MCP profile
    podman-compose --profile mcp up -d
else
    echo -e "${YELLOW}⚠ MCP Server is disabled${NC}"
    echo "  To enable: Set AIRFLOW_MCP_ENABLED=true in .env"
    echo "  Starting without MCP..."
    
    # Start without MCP profile
    podman-compose up -d
fi

echo ""
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}Services Started!${NC}"
echo -e "${GREEN}============================================================${NC}"

# Show running containers
echo ""
echo "Running containers:"
podman-compose ps

echo ""
echo "Service URLs:"
echo "  - Airflow UI:      http://localhost:8888"
if [ "$MCP_ENABLED" == "true" ]; then
    echo "  - Airflow MCP:     http://localhost:8889"
    echo "  - MCP Health:      http://localhost:8889/health"
fi

echo ""
echo "View logs with:"
echo "  podman-compose logs -f"
if [ "$MCP_ENABLED" == "true" ]; then
    echo "  podman-compose logs -f airflow-mcp-server"
fi

echo ""
echo -e "${BLUE}Setup complete!${NC}"
