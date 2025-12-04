#!/bin/bash
# Download Granite-4.0-Micro model for Qubinode AI Assistant
# Based on ADR-0027: CPU-Based AI Deployment Assistant Architecture

set -euo pipefail

# Configuration
MODEL_URL="https://huggingface.co/ibm-granite/granite-4.0-micro-GGUF/resolve/main/granite-4.0-micro-Q4_K_M.gguf"
MODEL_DIR="/root/qubinode_navigator/ai-assistant/models"
MODEL_FILE="granite-4.0-micro.gguf"
MODEL_PATH="${MODEL_DIR}/${MODEL_FILE}"

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

# Create models directory
create_model_dir() {
    log_info "Creating models directory..."
    mkdir -p "${MODEL_DIR}"
    log_success "Models directory ready: ${MODEL_DIR}"
}

# Download model
download_model() {
    log_info "Downloading Granite-4.0-Micro model (Q4_K_M quantization)..."
    log_info "Source: ${MODEL_URL}"
    log_info "Destination: ${MODEL_PATH}"

    if [[ -f "${MODEL_PATH}" ]]; then
        log_warning "Model file already exists. Checking size..."
        local file_size=$(stat -c%s "${MODEL_PATH}" 2>/dev/null || echo "0")
        if [[ ${file_size} -gt 1000000 ]]; then  # > 1MB
            log_success "Model file exists and appears valid (${file_size} bytes)"
            return 0
        else
            log_warning "Model file exists but appears incomplete. Re-downloading..."
            rm -f "${MODEL_PATH}"
        fi
    fi

    # Download with wget for progress and resume capability
    if wget --progress=bar:force:noscroll \
           --timeout=30 \
           --tries=3 \
           --continue \
           -O "${MODEL_PATH}" \
           "${MODEL_URL}"; then
        log_success "Model downloaded successfully"

        # Verify download
        local file_size=$(stat -c%s "${MODEL_PATH}")
        log_info "Downloaded model size: ${file_size} bytes ($(( file_size / 1024 / 1024 )) MB)"

        if [[ ${file_size} -lt 1000000 ]]; then  # < 1MB
            log_error "Downloaded file appears too small. Download may have failed."
            return 1
        fi

    else
        log_error "Model download failed"
        return 1
    fi
}

# Verify model file
verify_model() {
    log_info "Verifying model file..."

    if [[ ! -f "${MODEL_PATH}" ]]; then
        log_error "Model file not found: ${MODEL_PATH}"
        return 1
    fi

    # Check if it's a GGUF file (basic check)
    if file "${MODEL_PATH}" | grep -q "data"; then
        log_success "Model file appears to be valid binary data"
    else
        log_warning "Model file format could not be verified"
    fi

    # Check file size
    local file_size=$(stat -c%s "${MODEL_PATH}")
    local file_size_mb=$(( file_size / 1024 / 1024 ))

    log_info "Model file size: ${file_size_mb} MB"

    if [[ ${file_size_mb} -lt 100 ]]; then
        log_warning "Model file seems small for a 4B parameter model"
    elif [[ ${file_size_mb} -gt 5000 ]]; then
        log_warning "Model file seems large - check if correct quantization"
    else
        log_success "Model file size appears reasonable"
    fi
}

# Set permissions
set_permissions() {
    log_info "Setting appropriate permissions..."
    chmod 644 "${MODEL_PATH}"
    log_success "Permissions set"
}

# Main execution
main() {
    log_info "Starting Granite-4.0-Micro model download..."

    create_model_dir
    download_model
    verify_model
    set_permissions

    log_success "Model download completed successfully!"
    log_info "Model location: ${MODEL_PATH}"
    log_info "You can now run the AI assistant container with the real model"
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Download Granite-4.0-Micro model for Qubinode AI Assistant"
        echo ""
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --force        Force re-download even if file exists"
        echo ""
        echo "Model Details:"
        echo "  Model: IBM Granite-4.0-Micro"
        echo "  Quantization: Q4_K_M (good balance of quality/size)"
        echo "  Size: ~2-3GB"
        echo "  License: Apache 2.0"
        echo ""
        exit 0
        ;;
    --force)
        log_info "Force mode enabled - will re-download existing files"
        rm -f "${MODEL_PATH}"
        ;;
esac

# Run main function
main
