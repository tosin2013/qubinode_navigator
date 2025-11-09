#!/bin/bash
# Verify llama.cpp installation in the container
# This script checks if llama.cpp server is properly installed and accessible

set -e

echo "🔍 Verifying llama.cpp installation in AI Assistant container..."

# Check if container exists and is running
if ! docker ps | grep -q qubinode-ai-assistant; then
    echo "⚠️  AI Assistant container is not running. Starting verification container..."
    
    # Run a temporary container to check the installation
    echo "🧪 Running verification in temporary container..."
    docker run --rm qubinode-ai-assistant:latest /bin/bash -c "
        echo '📍 Checking llama.cpp server locations:'
        echo '  /usr/local/bin/llama-server:'
        ls -la /usr/local/bin/llama-server 2>/dev/null && echo '    ✅ Found' || echo '    ❌ Not found'
        
        echo '  /app/llama.cpp/server (symlink):'
        ls -la /app/llama.cpp/server 2>/dev/null && echo '    ✅ Found' || echo '    ❌ Not found'
        
        echo ''
        echo '🔧 Testing llama-server executable:'
        /usr/local/bin/llama-server --help 2>/dev/null | head -3 && echo '    ✅ Executable works' || echo '    ❌ Executable failed'
        
        echo ''
        echo '📂 Checking directory structure:'
        ls -la /app/llama.cpp/ 2>/dev/null || echo '    Directory not found'
    "
else
    echo "🔍 Checking running container..."
    docker exec qubinode-ai-assistant /bin/bash -c "
        echo '📍 Checking llama.cpp server locations:'
        echo '  /usr/local/bin/llama-server:'
        ls -la /usr/local/bin/llama-server 2>/dev/null && echo '    ✅ Found' || echo '    ❌ Not found'
        
        echo '  /app/llama.cpp/server (symlink):'
        ls -la /app/llama.cpp/server 2>/dev/null && echo '    ✅ Found' || echo '    ❌ Not found'
        
        echo ''
        echo '🔧 Testing llama-server executable:'
        /usr/local/bin/llama-server --help 2>/dev/null | head -3 && echo '    ✅ Executable works' || echo '    ❌ Executable failed'
    "
fi

echo ""
echo "✅ Verification complete!"
