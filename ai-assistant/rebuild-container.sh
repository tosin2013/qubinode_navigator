#!/bin/bash
# Rebuild AI Assistant container with llama.cpp and Marquez integration
# This script rebuilds the container and provides proper run commands

set -e

echo "============================================================"
echo "Rebuilding AI Assistant Container"
echo "============================================================"

# Navigate to AI Assistant directory
cd "$(dirname "$0")"

# Detect container runtime (podman or docker)
if command -v podman &>/dev/null; then
    CONTAINER_CMD="podman"
elif command -v docker &>/dev/null; then
    CONTAINER_CMD="docker"
else
    echo "[ERROR] No container runtime found (podman or docker)"
    exit 1
fi
echo "[INFO] Using container runtime: $CONTAINER_CMD"

# Stop any running containers
echo "[INFO] Stopping existing AI Assistant containers..."
$CONTAINER_CMD stop qubinode-ai-assistant 2>/dev/null || true
$CONTAINER_CMD rm qubinode-ai-assistant 2>/dev/null || true

# Remove old image to force rebuild
echo "[INFO] Removing old container image..."
$CONTAINER_CMD rmi qubinode-ai-assistant:latest 2>/dev/null || true

# Build new container
echo "[INFO] Building new container..."
$CONTAINER_CMD build -t qubinode-ai-assistant:latest .

# Verify the build was successful
if [ $? -eq 0 ]; then
    echo ""
    echo "[OK] Container rebuilt successfully!"
    echo ""

    # Get host IP for Marquez connection
    HOST_IP=$(ip route get 1 2>/dev/null | awk '{print $7; exit}' || echo "host.containers.internal")

    echo "============================================================"
    echo "To start the AI Assistant with Marquez/OpenLineage support:"
    echo "============================================================"
    echo ""
    echo "$CONTAINER_CMD run -d \\"
    echo "  --name qubinode-ai-assistant \\"
    echo "  -p 8080:8080 \\"
    echo "  -e MARQUEZ_API_URL=\"http://${HOST_IP}:5001\" \\"
    echo "  -e OPENLINEAGE_NAMESPACE=\"qubinode\" \\"
    echo "  qubinode-ai-assistant:latest"
    echo ""
    echo "============================================================"
    echo "Without Marquez (standalone mode):"
    echo "============================================================"
    echo ""
    echo "$CONTAINER_CMD run -d --name qubinode-ai-assistant -p 8080:8080 qubinode-ai-assistant:latest"
    echo ""
    echo "[INFO] To check logs: $CONTAINER_CMD logs -f qubinode-ai-assistant"
else
    echo "[ERROR] Container build failed!"
    exit 1
fi
