#!/bin/bash
# Rebuild AI Assistant container with llama.cpp fix
# This script rebuilds the container to fix the missing llama.cpp server issue

set -e

echo "🔧 Rebuilding AI Assistant container with llama.cpp fix..."

# Navigate to AI Assistant directory
cd "$(dirname "$0")"

# Stop any running containers
echo "📦 Stopping existing AI Assistant containers..."
docker stop qubinode-ai-assistant 2>/dev/null || true
docker rm qubinode-ai-assistant 2>/dev/null || true

# Remove old image to force rebuild
echo "🗑️  Removing old container image..."
docker rmi qubinode-ai-assistant:latest 2>/dev/null || true

# Build new container
echo "🏗️  Building new container with llama.cpp fix..."
docker build -t qubinode-ai-assistant:latest .

# Verify the build was successful
if [ $? -eq 0 ]; then
    echo "✅ Container rebuilt successfully!"
    echo ""
    echo "🚀 To start the AI Assistant:"
    echo "   docker run -d --name qubinode-ai-assistant -p 8080:8080 qubinode-ai-assistant:latest"
    echo ""
    echo "📋 To check logs:"
    echo "   docker logs -f qubinode-ai-assistant"
else
    echo "❌ Container build failed!"
    exit 1
fi
