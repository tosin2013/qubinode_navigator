#!/bin/bash
# Startup script for AI Assistant with MCP Server
# Starts both the main AI Assistant and the MCP HTTP server

set -e

echo "============================================================"
echo "Starting Qubinode AI Assistant with MCP Server Support"
echo "============================================================"

# Activate virtual environment if it exists
if [ -d "/app/venv" ]; then
    source /app/venv/bin/activate
fi

# Function to start MCP HTTP server in background
start_mcp_server() {
    if [ "${MCP_SERVER_ENABLED:-false}" == "true" ]; then
        echo "Starting MCP HTTP Server on port ${MCP_SERVER_PORT:-8081}..."
        python3 /app/mcp_http_server.py &
        MCP_PID=$!
        echo "MCP Server started with PID: $MCP_PID"
        
        # Wait a moment for server to start
        sleep 2
        
        # Verify it's running
        if kill -0 $MCP_PID 2>/dev/null; then
            echo "✓ MCP Server is running"
        else
            echo "✗ MCP Server failed to start"
        fi
    else
        echo "MCP Server is disabled (MCP_SERVER_ENABLED=false)"
    fi
}

# Function to cleanup on exit
cleanup() {
    echo "Shutting down..."
    if [ ! -z "$MCP_PID" ]; then
        echo "Stopping MCP Server (PID: $MCP_PID)..."
        kill $MCP_PID 2>/dev/null || true
    fi
}

trap cleanup EXIT INT TERM

# Start MCP server in background
start_mcp_server

# Start main AI Assistant (foreground process)
echo "Starting AI Assistant main application..."
exec python3 /app/src/main.py
