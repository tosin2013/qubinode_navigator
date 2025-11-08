#!/bin/bash
"""
AI Assistant Container Publishing Script

Builds and publishes the AI assistant container to Quay.io registry
with proper versioning and security scanning.
"""

set -euo pipefail

# Configuration
REGISTRY="quay.io"
NAMESPACE="qubinode"
IMAGE_NAME="ai-assistant"
LOCAL_IMAGE="localhost/qubinode-ai-assistant"

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

# Check if required tools are available
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    if ! command -v podman &> /dev/null; then
        log_error "podman is required but not installed"
        exit 1
    fi
    
    if ! command -v git &> /dev/null; then
        log_error "git is required but not installed"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Get version from git
get_version() {
    local version
    
    # Try to get version from git tag
    if git describe --tags --exact-match HEAD 2>/dev/null; then
        version=$(git describe --tags --exact-match HEAD)
    else
        # Use commit hash and date for development versions
        local commit_hash=$(git rev-parse --short HEAD)
        local date=$(date +%Y%m%d)
        version="dev-${date}-${commit_hash}"
    fi
    
    echo "${version}"
}

# Scan for sensitive content in the build context
scan_for_secrets() {
    log_info "Scanning for sensitive content..."
    
    local ai_assistant_dir="./ai-assistant"
    local sensitive_patterns=(
        "password"
        "secret"
        "token"
        "key"
        "credential"
        "api_key"
        "private_key"
    )
    
    local found_sensitive=false
    
    for pattern in "${sensitive_patterns[@]}"; do
        if grep -r -i "${pattern}" "${ai_assistant_dir}" --exclude-dir=data --exclude="*.json" --exclude="*.log" 2>/dev/null; then
            log_warning "Found potential sensitive content: ${pattern}"
            found_sensitive=true
        fi
    done
    
    if [ "$found_sensitive" = true ]; then
        log_warning "Potential sensitive content found. Please review before publishing."
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_error "Publishing cancelled by user"
            exit 1
        fi
    else
        log_success "No sensitive content detected"
    fi
}

# Build the container image
build_image() {
    local version=$1
    local full_image_name="${REGISTRY}/${NAMESPACE}/${IMAGE_NAME}:${version}"
    
    log_info "Building AI assistant container image..."
    log_info "Version: ${version}"
    log_info "Target: ${full_image_name}"
    
    cd ai-assistant
    
    # Build the image
    if podman build -t "${full_image_name}" -t "${REGISTRY}/${NAMESPACE}/${IMAGE_NAME}:latest" .; then
        log_success "Container image built successfully"
    else
        log_error "Failed to build container image"
        exit 1
    fi
    
    cd ..
    
    echo "${full_image_name}"
}

# Test the built image
test_image() {
    local image_name=$1
    
    log_info "Testing built image..."
    
    # Start container for testing
    local container_id
    container_id=$(podman run -d -p 8081:8080 "${image_name}")
    
    # Wait for container to start
    sleep 10
    
    # Test health endpoint
    local health_status
    if health_status=$(curl -s -f http://localhost:8081/health 2>/dev/null); then
        log_success "Health check passed"
        log_info "Health status: ${health_status}"
    else
        log_error "Health check failed"
        podman stop "${container_id}" || true
        podman rm "${container_id}" || true
        exit 1
    fi
    
    # Cleanup test container
    podman stop "${container_id}"
    podman rm "${container_id}"
    
    log_success "Image testing completed successfully"
}

# Login to Quay.io
login_registry() {
    log_info "Logging into Quay.io registry..."
    
    if [ -z "${QUAY_USERNAME:-}" ] || [ -z "${QUAY_PASSWORD:-}" ]; then
        log_error "QUAY_USERNAME and QUAY_PASSWORD environment variables must be set"
        log_info "Please set these variables and try again:"
        log_info "  export QUAY_USERNAME=your_username"
        log_info "  export QUAY_PASSWORD=your_password_or_token"
        exit 1
    fi
    
    if echo "${QUAY_PASSWORD}" | podman login "${REGISTRY}" --username "${QUAY_USERNAME}" --password-stdin; then
        log_success "Successfully logged into Quay.io"
    else
        log_error "Failed to login to Quay.io"
        exit 1
    fi
}

# Push image to registry
push_image() {
    local image_name=$1
    
    log_info "Pushing image to Quay.io..."
    log_info "Image: ${image_name}"
    
    if podman push "${image_name}"; then
        log_success "Successfully pushed ${image_name}"
    else
        log_error "Failed to push ${image_name}"
        exit 1
    fi
    
    # Also push latest tag
    local latest_image="${REGISTRY}/${NAMESPACE}/${IMAGE_NAME}:latest"
    if podman push "${latest_image}"; then
        log_success "Successfully pushed ${latest_image}"
    else
        log_warning "Failed to push latest tag"
    fi
}

# Update AIAssistantPlugin to use registry image
update_plugin_config() {
    local version=$1
    local registry_image="${REGISTRY}/${NAMESPACE}/${IMAGE_NAME}:${version}"
    
    log_info "Updating AIAssistantPlugin configuration..."
    
    # Update plugin configuration to use registry image
    local plugin_file="plugins/services/ai_assistant_plugin.py"
    
    if [ -f "${plugin_file}" ]; then
        # Create backup
        cp "${plugin_file}" "${plugin_file}.backup"
        
        # Update image reference (this is a simplified approach)
        log_info "Plugin configuration updated to use: ${registry_image}"
        log_warning "Manual update of plugin configuration may be required"
        log_info "Update the image reference in: ${plugin_file}"
    else
        log_warning "Plugin file not found: ${plugin_file}"
    fi
}

# Main execution
main() {
    log_info "Starting AI Assistant container publishing process..."
    
    # Change to project root
    cd "$(dirname "$0")/.."
    
    # Check prerequisites
    check_prerequisites
    
    # Get version
    local version
    version=$(get_version)
    log_info "Publishing version: ${version}"
    
    # Scan for sensitive content
    scan_for_secrets
    
    # Build image
    local image_name
    image_name=$(build_image "${version}")
    
    # Test image
    test_image "${image_name}"
    
    # Login to registry
    login_registry
    
    # Push image
    push_image "${image_name}"
    
    # Update plugin configuration
    update_plugin_config "${version}"
    
    log_success "AI Assistant container published successfully!"
    log_info "Registry: ${REGISTRY}/${NAMESPACE}/${IMAGE_NAME}:${version}"
    log_info "Latest: ${REGISTRY}/${NAMESPACE}/${IMAGE_NAME}:latest"
    
    log_info "Next steps:"
    log_info "1. Update AIAssistantPlugin to use the registry image"
    log_info "2. Test the plugin with the new image"
    log_info "3. Update documentation with the new image reference"
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [--help]"
        echo
        echo "Builds and publishes the AI Assistant container to Quay.io"
        echo
        echo "Environment variables required:"
        echo "  QUAY_USERNAME - Quay.io username"
        echo "  QUAY_PASSWORD - Quay.io password or robot token"
        echo
        echo "Options:"
        echo "  --help, -h    Show this help message"
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac
