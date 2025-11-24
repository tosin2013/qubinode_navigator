#!/bin/bash
# Startup script for Airflow MCP HTTP Server
# Runs as a background service in the Airflow container

set -e

# Load environment variables
if [ -f /opt/airflow/.env ]; then
    source /opt/airflow/.env
fi

# Check if MCP is enabled
MCP_ENABLED=$(echo "${AIRFLOW_MCP_ENABLED:-false}" | tr '[:upper:]' '[:lower:]')

if [ "$MCP_ENABLED" != "true" ]; then
    echo "Airflow MCP Server is disabled (AIRFLOW_MCP_ENABLED=$MCP_ENABLED)"
    exit 0
fi

echo "============================================================"
echo "Starting Airflow MCP HTTP Server"
echo "Port: ${AIRFLOW_MCP_PORT:-8889}"
echo "============================================================"

# Set Python path to include plugins
export PYTHONPATH="/opt/airflow/plugins:${PYTHONPATH:-}"

# Create log directory
mkdir -p /opt/airflow/logs/mcp

# Change to plugins directory for proper imports
cd /opt/airflow/plugins

# Start MCP HTTP server
exec python3 -m qubinode.mcp_http_server \
    >> /opt/airflow/logs/mcp/server.log 2>&1
