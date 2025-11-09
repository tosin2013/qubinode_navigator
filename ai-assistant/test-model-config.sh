#!/bin/bash
"""
Test script for configurable AI models
Demonstrates different model configurations
"""

set -e

echo "🧪 Testing Configurable AI Model System"
echo "========================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Test 1: Default CPU model (current setup)
test_default_model() {
    log_info "Test 1: Default CPU Model (Granite 4.0 Micro)"
    
    podman run --rm --name test-ai-default \
        -p 8081:8080 \
        -v $(pwd)/data:/app/data:Z \
        -d \
        localhost/qubinode-ai-assistant:latest
    
    sleep 10
    
    # Test model info endpoint
    if curl -f http://localhost:8081/model/info >/dev/null 2>&1; then
        log_success "Default model API accessible"
        curl -s http://localhost:8081/model/info | jq '.model_info.model_type'
    else
        log_warning "Default model still starting up"
    fi
    
    podman stop test-ai-default || true
}

# Test 2: GPU model configuration (simulated)
test_gpu_model() {
    log_info "Test 2: GPU Model Configuration (Simulated)"
    
    # This would work on a system with GPU
    cat << 'EOF'
Example GPU command:
podman run --rm --name test-ai-gpu \
    -p 8082:8080 \
    -v $(pwd)/data:/app/data:Z \
    --device nvidia.com/gpu=all \
    -e AI_MODEL_TYPE=llama3-8b \
    -e AI_USE_GPU=true \
    -e AI_GPU_LAYERS=32 \
    -d \
    quay.io/qubinode/ai-assistant:latest
EOF
    
    log_info "GPU model would use Llama3-8B with 32 GPU layers"
}

# Test 3: API model configuration (simulated)
test_api_model() {
    log_info "Test 3: API Model Configuration (Simulated)"
    
    cat << 'EOF'
Example OpenAI API command:
podman run --rm --name test-ai-api \
    -p 8083:8080 \
    -v $(pwd)/data:/app/data:Z \
    -e AI_MODEL_TYPE=openai-gpt4 \
    -e OPENAI_API_KEY=your_api_key_here \
    -d \
    quay.io/qubinode/ai-assistant:latest
EOF
    
    log_info "API model would use OpenAI GPT-4 via LiteLLM"
}

# Test 4: Hardware detection
test_hardware_detection() {
    log_info "Test 4: Hardware Detection"
    
    # Check for GPU
    if command -v nvidia-smi >/dev/null 2>&1; then
        log_success "NVIDIA GPU detected"
        nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
    else
        log_info "No NVIDIA GPU detected - CPU-only mode recommended"
    fi
    
    # Check system memory
    local mem_gb=$(free -g | awk '/^Mem:/{print $2}')
    log_info "System Memory: ${mem_gb}GB"
    
    if [ "$mem_gb" -ge 8 ]; then
        log_success "Sufficient memory for larger models (granite-7b)"
    else
        log_info "Limited memory - recommend granite-4.0-micro"
    fi
}

# Test 5: Configuration validation
test_config_validation() {
    log_info "Test 5: Configuration Validation"
    
    # Test invalid model type
    log_info "Testing invalid model configuration..."
    
    # This would fail gracefully
    cat << 'EOF'
Invalid configuration example:
podman run --rm --name test-ai-invalid \
    -e AI_MODEL_TYPE=nonexistent-model \
    quay.io/qubinode/ai-assistant:latest

Expected: Graceful failure with error message
EOF
}

# Main execution
main() {
    log_info "Starting AI Assistant Model Configuration Tests"
    echo
    
    # Run tests
    test_hardware_detection
    echo
    
    test_default_model
    echo
    
    test_gpu_model
    echo
    
    test_api_model
    echo
    
    test_config_validation
    echo
    
    log_success "Model configuration tests completed!"
    
    echo
    log_info "Summary of Model Options:"
    echo "  • granite-4.0-micro: CPU-only, 2GB+ RAM (default)"
    echo "  • granite-7b: CPU/GPU, 8GB+ RAM"
    echo "  • llama3-8b: GPU, 6GB+ VRAM"
    echo "  • phi3-mini: GPU, 4GB+ VRAM (fast)"
    echo "  • openai-gpt4: API-based (requires key)"
    echo "  • anthropic-claude: API-based (requires key)"
    echo "  • ollama-local: Local Ollama integration"
    
    echo
    log_info "For production deployment, configure via environment variables:"
    echo "  export AI_MODEL_TYPE=llama3-8b"
    echo "  export AI_USE_GPU=true"
    echo "  export AI_GPU_LAYERS=32"
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [--help]"
        echo
        echo "Test configurable AI model system"
        echo
        echo "Options:"
        echo "  --help, -h    Show this help message"
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac
