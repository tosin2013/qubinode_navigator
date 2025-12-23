#!/bin/bash
# FastMCP Production Deployment Script
# Deploys both Airflow and AI Assistant MCP servers

set -e

# QUBINODE_HOME Setup
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -n "${QUBINODE_HOME:-}" ]]; then
    : # Already set
elif [[ -d "$SCRIPT_DIR/airflow" ]]; then
    QUBINODE_HOME="$SCRIPT_DIR"
else
    QUBINODE_HOME="/opt/qubinode_navigator"
fi
export QUBINODE_HOME

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  FastMCP Production Deployment                            ║${NC}"
echo -e "${BLUE}║  Qubinode Navigator MCP Servers                           ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check prerequisites
echo -e "${YELLOW}[1/6]${NC} Checking prerequisites..."
command -v podman-compose >/dev/null 2>&1 || { echo -e "${RED}✗${NC} podman-compose not found!"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo -e "${RED}✗${NC} python3 not found!"; exit 1; }
command -v curl >/dev/null 2>&1 || { echo -e "${RED}✗${NC} curl not found!"; exit 1; }
echo -e "${GREEN}✓${NC} Prerequisites satisfied"
echo ""

# Backup existing configuration
echo -e "${YELLOW}[2/6]${NC} Creating backup..."
BACKUP_DIR="/tmp/mcp-backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp ${QUBINODE_HOME}/airflow/.env "$BACKUP_DIR/" 2>/dev/null || echo "No .env to backup"
cp ${QUBINODE_HOME}/airflow/docker-compose.yml "$BACKUP_DIR/"
echo -e "${GREEN}✓${NC} Backup created: $BACKUP_DIR"
echo ""

# Configure environment
echo -e "${YELLOW}[3/6]${NC} Configuring environment..."
cd ${QUBINODE_HOME}/airflow

# Ensure MCP is enabled
if ! grep -q "AIRFLOW_MCP_ENABLED" .env 2>/dev/null; then
    echo "AIRFLOW_MCP_ENABLED=true" >> .env
    echo "AIRFLOW_MCP_PORT=8889" >> .env
    echo "AIRFLOW_MCP_API_KEY=65efb281f1ea9dc8498ec563f7bf42af4f8bf8a6b7bb542141902ce462cdb98a" >> .env
    echo -e "${GREEN}✓${NC} Added MCP configuration to .env"
else
    echo -e "${GREEN}✓${NC} MCP configuration already exists"
fi
echo ""

# Rebuild Docker images
echo -e "${YELLOW}[4/6]${NC} Rebuilding Docker images with FastMCP..."
echo "This may take 5-10 minutes..."
podman-compose build --no-cache airflow-webserver 2>&1 | grep -E "(Step|Successfully)" || true
echo -e "${GREEN}✓${NC} Docker images rebuilt"
echo ""

# Deploy services
echo -e "${YELLOW}[5/6]${NC} Deploying MCP services..."

# Stop old services
echo "Stopping existing services..."
podman-compose --profile mcp down 2>/dev/null || true
sleep 2

# Start with MCP profile
echo "Starting services with MCP profile..."
podman-compose --profile mcp up -d

# Wait for services to be healthy
echo "Waiting for services to start..."
for i in {1..30}; do
    if podman-compose ps | grep -q "airflow-mcp-server.*Up"; then
        echo -e "${GREEN}✓${NC} Airflow MCP server is up"
        break
    fi
    echo -n "."
    sleep 2
done
echo ""
echo ""

# Verify deployment
echo -e "${YELLOW}[6/6]${NC} Verifying deployment..."
echo ""

# Check Airflow MCP
echo -n "Testing Airflow MCP (port 8889): "
if curl -sf http://localhost:8889/sse >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Online${NC}"
else
    echo -e "${RED}✗ Offline${NC}"
    echo "Check logs: podman-compose logs airflow-mcp-server"
fi

# Check AI Assistant MCP (if running)
echo -n "Testing AI Assistant MCP (port 8081): "
if curl -sf http://localhost:8081/sse >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Online${NC}"
else
    echo -e "${YELLOW}⚠ Not running (start manually if needed)${NC}"
fi

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Deployment Complete!                                     ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Show service status
echo -e "${GREEN}Running Services:${NC}"
podman-compose ps
echo ""

# Show useful commands
echo -e "${YELLOW}Useful Commands:${NC}"
echo "  View logs:       podman-compose logs -f airflow-mcp-server"
echo "  Restart:         podman-compose restart airflow-mcp-server"
echo "  Stop:            podman-compose --profile mcp down"
echo "  Test:            ansible-playbook tests/mcp/test_mcp_suite.yml"
echo ""

# Show MCP endpoints
echo -e "${YELLOW}MCP Endpoints:${NC}"
echo "  Airflow MCP:     http://localhost:8889/sse"
echo "  AI Assistant:    http://localhost:8081/sse (if running)"
echo ""

# Show client configuration
echo -e "${YELLOW}Client Configuration:${NC}"
echo "  Copy ${QUBINODE_HOME}/mcp-client-config-example.json"
echo "  To: ~/.config/claude/claude_desktop_config.json"
echo "  Or: /root/.codeium/windsurf/mcp_config.json"
echo ""

echo -e "${GREEN}✅ FastMCP deployment complete!${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "  1. Configure your MCP client (Claude/Windsurf)"
echo "  2. Test connection: ansible-playbook tests/mcp/test_mcp_suite.yml"
echo "  3. Monitor logs: podman-compose logs -f airflow-mcp-server"
echo "  4. Review docs: ${QUBINODE_HOME}/FASTMCP-QUICK-START.md"
echo ""
