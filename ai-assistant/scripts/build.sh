#!/bin/bash
# Build script for Qubinode AI Assistant container
# Based on ADR-0027: CPU-Based AI Deployment Assistant Architecture

set -euo pipefail

# Configuration
CONTAINER_NAME="qubinode-ai-assistant"
CONTAINER_TAG="latest"
REGISTRY="localhost"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
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

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if podman is available
    if ! command -v podman &> /dev/null; then
        log_error "Podman is not installed or not in PATH"
        exit 1
    fi
    
    # Check if we're in the right directory
    if [[ ! -f "Dockerfile" ]]; then
        log_error "Dockerfile not found. Please run this script from the ai-assistant directory."
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Build the container
build_container() {
    log_info "Building Qubinode AI Assistant container..."
    
    # Build with podman
    if podman build \
        --tag "${REGISTRY}/${CONTAINER_NAME}:${CONTAINER_TAG}" \
        --tag "${REGISTRY}/${CONTAINER_NAME}:$(date +%Y%m%d)" \
        --file Dockerfile \
        --format docker \
        .; then
        log_success "Container built successfully"
    else
        log_error "Container build failed"
        exit 1
    fi
}

# Test the container
test_container() {
    log_info "Testing container..."
    
    # Run a quick test to ensure the container starts
    if podman run --rm \
        --name "${CONTAINER_NAME}-test" \
        "${REGISTRY}/${CONTAINER_NAME}:${CONTAINER_TAG}" \
        python3 -c "import sys; print('Python test passed'); sys.exit(0)"; then
        log_success "Container test passed"
    else
        log_warning "Container test failed - this might be expected if dependencies are missing"
    fi
}

# Show container information
show_info() {
    log_info "Container information:"
    echo "  Name: ${CONTAINER_NAME}"
    echo "  Tag: ${CONTAINER_TAG}"
    echo "  Full name: ${REGISTRY}/${CONTAINER_NAME}:${CONTAINER_TAG}"
    
    # Show image size
    if podman images "${REGISTRY}/${CONTAINER_NAME}:${CONTAINER_TAG}" --format "table {{.Repository}}:{{.Tag}} {{.Size}}" | tail -n +2; then
        log_success "Container ready for use"
    fi
}

# Main execution
main() {
    log_info "Starting Qubinode AI Assistant container build..."
    
    check_prerequisites
    build_container
    test_container
    show_info
    
    log_success "Build process completed!"
    
    echo ""
    log_info "Next steps:"
    echo "  1. Run the container: podman run -d -p 8080:8080 ${REGISTRY}/${CONTAINER_NAME}:${CONTAINER_TAG}"
    echo "  2. Test the API: curl http://localhost:8080/health"
    echo "  3. Use the CLI: ./scripts/qubinode-ai --health"
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Build the Qubinode AI Assistant container"
        echo ""
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --no-test      Skip container testing"
        echo ""
        exit 0
        ;;
    --no-test)
        NO_TEST=true
        ;;
esac

# Run main function
main
