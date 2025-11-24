#!/bin/bash
# =============================================================================
# MCP Server Setup Script
# Generates API keys and configures MCP servers for Qubinode Navigator
# =============================================================================

set -euo pipefail

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${CYAN}"
cat << 'EOF'
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║       MCP Server Configuration for Qubinode Navigator          ║
║                                                                ║
║     Enables external LLMs to interact with:                    ║
║     • AI Assistant (RAG queries, chat)                         ║
║     • Airflow (DAG management, VM operations)                  ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# Check if .env exists
ENV_FILE="${SCRIPT_DIR}/.env"

if [ -f "$ENV_FILE" ]; then
    echo -e "${YELLOW}Warning: .env file already exists${NC}"
    echo -e "${YELLOW}This script will append MCP configuration${NC}"
    read -p "Continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 1
    fi
fi

echo -e "${BLUE}Step 1: Generating API Keys...${NC}"

# Generate secure API keys
AI_MCP_KEY=$(openssl rand -hex 32)
AIRFLOW_MCP_KEY=$(openssl rand -hex 32)

echo -e "${GREEN}✓ API keys generated${NC}"

echo -e "${BLUE}Step 2: Configuration Options...${NC}"

# Ask user for configuration
read -p "Enable AI Assistant MCP server? (Y/n): " -n 1 -r AI_ENABLED
echo
AI_ENABLED=${AI_ENABLED:-Y}

read -p "Enable Airflow MCP server? (Y/n): " -n 1 -r AIRFLOW_ENABLED
echo
AIRFLOW_ENABLED=${AIRFLOW_ENABLED:-Y}

if [[ $AIRFLOW_ENABLED =~ ^[Yy]$ ]]; then
    read -p "Enable read-only mode (safe for production)? (y/N): " -n 1 -r READ_ONLY
    echo
    READ_ONLY=${READ_ONLY:-N}
else
    READ_ONLY="N"
fi

echo -e "${BLUE}Step 3: Writing configuration...${NC}"

# Create or append to .env
cat >> "$ENV_FILE" << EOF

# =============================================================================
# MCP Server Configuration
# Generated on $(date)
# =============================================================================

# AI Assistant MCP Server
MCP_SERVER_ENABLED=$([[ $AI_ENABLED =~ ^[Yy]$ ]] && echo "true" || echo "false")
MCP_SERVER_PORT=8081
MCP_API_KEY=${AI_MCP_KEY}
AI_SERVICE_URL=http://localhost:8080

# Airflow MCP Server
AIRFLOW_MCP_ENABLED=$([[ $AIRFLOW_ENABLED =~ ^[Yy]$ ]] && echo "true" || echo "false")
AIRFLOW_MCP_PORT=8889
AIRFLOW_MCP_API_KEY=${AIRFLOW_MCP_KEY}

# Tool Permissions
AIRFLOW_MCP_TOOLS_DAG_MGMT=true
AIRFLOW_MCP_TOOLS_VM_OPS=true
AIRFLOW_MCP_TOOLS_LOG_ACCESS=true
AIRFLOW_MCP_TOOLS_READ_ONLY=$([[ $READ_ONLY =~ ^[Yy]$ ]] && echo "true" || echo "false")
EOF

echo -e "${GREEN}✓ Configuration saved to ${ENV_FILE}${NC}"

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              MCP Servers Configuration Complete!               ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Display configuration summary
echo -e "${CYAN}📊 Configuration Summary:${NC}"
echo ""

if [[ $AI_ENABLED =~ ^[Yy]$ ]]; then
    echo -e "${GREEN}✓ AI Assistant MCP Server: ENABLED${NC}"
    echo -e "  Port: 8081"
    echo -e "  API Key: ${AI_MCP_KEY}"
    echo ""
else
    echo -e "  AI Assistant MCP Server: Disabled"
    echo ""
fi

if [[ $AIRFLOW_ENABLED =~ ^[Yy]$ ]]; then
    echo -e "${GREEN}✓ Airflow MCP Server: ENABLED${NC}"
    echo -e "  Port: 8889"
    echo -e "  API Key: ${AIRFLOW_MCP_KEY}"
    if [[ $READ_ONLY =~ ^[Yy]$ ]]; then
        echo -e "  Mode: ${YELLOW}READ-ONLY${NC} (safe)"
    else
        echo -e "  Mode: ${RED}READ-WRITE${NC} (full access)"
    fi
    echo ""
else
    echo -e "  Airflow MCP Server: Disabled"
    echo ""
fi

echo -e "${CYAN}📝 Claude Desktop Configuration:${NC}"
echo ""
echo "Add to ~/.config/claude/claude_desktop_config.json:"
echo ""
cat << CLAUDE_EOF
{
  "mcpServers": {
CLAUDE_EOF

if [[ $AI_ENABLED =~ ^[Yy]$ ]]; then
cat << CLAUDE_EOF
    "qubinode-ai": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-http-proxy"],
      "env": {
        "MCP_HTTP_URL": "http://YOUR_SERVER_IP:8081",
        "MCP_API_KEY": "${AI_MCP_KEY}"
      }
    }$([[ $AIRFLOW_ENABLED =~ ^[Yy]$ ]] && echo "," || echo "")
CLAUDE_EOF
fi

if [[ $AIRFLOW_ENABLED =~ ^[Yy]$ ]]; then
cat << CLAUDE_EOF
    "qubinode-airflow": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-http-proxy"],
      "env": {
        "MCP_HTTP_URL": "http://YOUR_SERVER_IP:8889",
        "MCP_API_KEY": "${AIRFLOW_MCP_KEY}"
      }
    }
CLAUDE_EOF
fi

cat << CLAUDE_EOF
  }
}
CLAUDE_EOF

echo ""
echo -e "${YELLOW}⚠️  Security Reminders:${NC}"
echo "  • Keep API keys secure and never commit to git"
echo "  • Use firewall rules to restrict access"
echo "  • Monitor MCP access logs regularly"
if [[ ! $READ_ONLY =~ ^[Yy]$ ]] && [[ $AIRFLOW_ENABLED =~ ^[Yy]$ ]]; then
    echo -e "  • ${RED}READ-WRITE mode enabled - LLMs can create/delete VMs!${NC}"
fi
echo ""

echo -e "${CYAN}🚀 Next Steps:${NC}"
echo "  1. Restart Airflow services:"
echo "     cd ${SCRIPT_DIR} && podman-compose restart"
echo ""
echo "  2. Test MCP connection:"
echo "     python3 ${SCRIPT_DIR}/../ai-assistant/mcp_server.py"
echo ""
echo "  3. Configure Claude Desktop with the config above"
echo ""

# Ask if they want to restart services now
read -p "Restart Airflow services now? (y/N): " -n 1 -r RESTART
echo
if [[ $RESTART =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}Restarting services...${NC}"
    cd "$SCRIPT_DIR"
    podman-compose restart
    echo -e "${GREEN}✓ Services restarted${NC}"
fi

echo ""
echo -e "${GREEN}Setup complete! 🎉${NC}"
