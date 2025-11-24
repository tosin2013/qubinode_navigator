#!/bin/bash
# Build script for Qubinode AI Assistant container
# Based on ADR-0027: CPU-Based AI Deployment Assistant Architecture

set -euo pipefail

# Configuration
CONTAINER_NAME="qubinode-ai-assistant"
REGISTRY="localhost"

# Version management
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION_MANAGER="$SCRIPT_DIR/version-manager.sh"

# Get current version
if [[ -f "$VERSION_MANAGER" ]]; then
    CONTAINER_VERSION=$("$VERSION_MANAGER" current | grep "Current version:" | cut -d' ' -f3)
    BUILD_VERSION=$("$VERSION_MANAGER" build-metadata)
else
    CONTAINER_VERSION="latest"
    BUILD_VERSION="latest"
fi

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
    log_info "Version: $CONTAINER_VERSION"
    log_info "Build metadata: $BUILD_VERSION"
    
    # Generate all container tags
    local tags=()
    if [[ -f "$VERSION_MANAGER" ]]; then
        # Use version manager to generate tags
        while IFS= read -r tag; do
            tags+=("--tag" "$tag")
        done < <("$VERSION_MANAGER" tags "$REGISTRY" "$CONTAINER_NAME")
    else
        # Fallback to simple tagging
        tags+=("--tag" "${REGISTRY}/${CONTAINER_NAME}:${CONTAINER_VERSION}")
        tags+=("--tag" "${REGISTRY}/${CONTAINER_NAME}:$(date +%Y%m%d)")
    fi
    
    # Build with podman
    if podman build \
        "${tags[@]}" \
        --label "version=$CONTAINER_VERSION" \
        --label "build-version=$BUILD_VERSION" \
        --label "build-date=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        --label "vcs-ref=$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')" \
        --file Dockerfile \
        --format docker \
        .; then
        log_success "Container built successfully"
        log_info "Tags created:"
        for ((i=1; i<${#tags[@]}; i+=2)); do
            echo "  ${tags[i]}"
        done
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
        "${REGISTRY}/${CONTAINER_NAME}:${CONTAINER_VERSION}" \
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
    echo "  Version: ${CONTAINER_VERSION}"
    echo "  Build Version: ${BUILD_VERSION}"
    echo "  Registry: ${REGISTRY}"
    
    # Show image size for main version tag
    local main_tag="${REGISTRY}/${CONTAINER_NAME}:${CONTAINER_VERSION}"
    if podman images "$main_tag" --format "table {{.Repository}}:{{.Tag}} {{.Size}}" | tail -n +2; then
        log_success "Container ready for use"
    fi
    
    # Show all tags for this image
    log_info "Available tags:"
    podman images "${REGISTRY}/${CONTAINER_NAME}" --format "  {{.Repository}}:{{.Tag}} ({{.Size}})"
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
    echo "  1. Run the container: podman run -d -p 8080:8080 ${REGISTRY}/${CONTAINER_NAME}:${CONTAINER_VERSION}"
    echo "  2. Test the API: curl http://localhost:8080/health"
    echo "  3. Check version: ./scripts/version-manager.sh current"
    echo "  4. Release new version: ./scripts/version-manager.sh release minor 'Description of changes'"
    echo "  5. Push to registry: podman push ${REGISTRY}/${CONTAINER_NAME}:${CONTAINER_VERSION}"
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
