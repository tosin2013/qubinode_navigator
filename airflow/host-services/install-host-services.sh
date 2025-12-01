#!/bin/bash
# =============================================================================
# Qubinode Host Services Installer
# ADR-0050: Hybrid Host-Container Architecture
# =============================================================================
#
# This script installs the host-side AI services:
# - Embedding Service (sentence-transformers) on port 8891
# - LiteLLM Proxy on port 4000
#
# Usage: ./install-host-services.sh [--skip-embedding] [--skip-litellm]
#
# =============================================================================

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Parse arguments
SKIP_EMBEDDING=false
SKIP_LITELLM=false

for arg in "$@"; do
    case $arg in
        --skip-embedding)
            SKIP_EMBEDDING=true
            ;;
        --skip-litellm)
            SKIP_LITELLM=true
            ;;
        --help)
            echo "Usage: $0 [--skip-embedding] [--skip-litellm]"
            exit 0
            ;;
    esac
done

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    log_error "This script must be run as root"
    exit 1
fi

# =============================================================================
# Create directories
# =============================================================================
log_info "Creating directories..."
mkdir -p /opt/qubinode/{services,config,models}
mkdir -p /etc/qubinode
mkdir -p /var/log/litellm

# =============================================================================
# Install Embedding Service
# =============================================================================
if [[ "$SKIP_EMBEDDING" == "false" ]]; then
    log_info "Installing Embedding Service..."

    # Install Python dependencies
    log_info "Installing Python dependencies for embedding service..."
    pip3 install --quiet sentence-transformers fastapi uvicorn pydantic

    # Copy service files
    cp "${SCRIPT_DIR}/embedding_service.py" /opt/qubinode/services/
    chmod +x /opt/qubinode/services/embedding_service.py

    # Pre-download embedding model
    log_info "Pre-downloading embedding model (all-MiniLM-L6-v2)..."
    TRANSFORMERS_CACHE=/opt/qubinode/models python3 -c "
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2', cache_folder='/opt/qubinode/models')
print(f'Model loaded: {model.get_sentence_embedding_dimension()} dimensions')
"

    # Install systemd service
    cp "${SCRIPT_DIR}/qubinode-embedding.service" /etc/systemd/system/
    systemctl daemon-reload
    systemctl enable qubinode-embedding.service

    log_success "Embedding Service installed"
else
    log_warning "Skipping Embedding Service installation"
fi

# =============================================================================
# Install LiteLLM Proxy
# =============================================================================
if [[ "$SKIP_LITELLM" == "false" ]]; then
    log_info "Installing LiteLLM Proxy..."

    # Install LiteLLM
    log_info "Installing LiteLLM..."
    pip3 install --quiet litellm

    # Copy config
    cp "${SCRIPT_DIR}/litellm_config.yaml" /opt/qubinode/config/

    # Create environment file if it doesn't exist
    if [[ ! -f /etc/qubinode/litellm.env ]]; then
        log_info "Creating LiteLLM environment file..."
        MASTER_KEY=$(openssl rand -hex 32)
        cat > /etc/qubinode/litellm.env << EOF
# LiteLLM API Keys
# Add your API keys here for external model access

# Master key for LiteLLM API authentication
LITELLM_MASTER_KEY=${MASTER_KEY}

# External API keys (optional)
# ANTHROPIC_API_KEY=your-key-here
# OPENAI_API_KEY=your-key-here
EOF
        chmod 600 /etc/qubinode/litellm.env
        log_info "Generated LiteLLM master key: ${MASTER_KEY}"
    else
        log_info "LiteLLM environment file already exists, preserving..."
    fi

    # Install systemd service
    cp "${SCRIPT_DIR}/qubinode-litellm.service" /etc/systemd/system/
    systemctl daemon-reload
    systemctl enable qubinode-litellm.service

    log_success "LiteLLM Proxy installed"
else
    log_warning "Skipping LiteLLM Proxy installation"
fi

# =============================================================================
# Start services
# =============================================================================
log_info "Starting services..."

if [[ "$SKIP_EMBEDDING" == "false" ]]; then
    systemctl start qubinode-embedding.service
    sleep 3
    if systemctl is-active --quiet qubinode-embedding.service; then
        log_success "Embedding Service started (http://localhost:8891)"
    else
        log_error "Embedding Service failed to start"
        journalctl -u qubinode-embedding.service -n 20 --no-pager
    fi
fi

if [[ "$SKIP_LITELLM" == "false" ]]; then
    systemctl start qubinode-litellm.service
    sleep 3
    if systemctl is-active --quiet qubinode-litellm.service; then
        log_success "LiteLLM Proxy started (http://localhost:4000)"
    else
        log_error "LiteLLM Proxy failed to start"
        journalctl -u qubinode-litellm.service -n 20 --no-pager
    fi
fi

# =============================================================================
# Verify services
# =============================================================================
log_info "Verifying services..."

if [[ "$SKIP_EMBEDDING" == "false" ]]; then
    if curl -s http://localhost:8891/health > /dev/null 2>&1; then
        log_success "Embedding Service health check passed"
    else
        log_warning "Embedding Service health check failed (may still be starting)"
    fi
fi

if [[ "$SKIP_LITELLM" == "false" ]]; then
    if curl -s http://localhost:4000/health > /dev/null 2>&1; then
        log_success "LiteLLM Proxy health check passed"
    else
        log_warning "LiteLLM Proxy health check failed (may still be starting)"
    fi
fi

# =============================================================================
# Summary
# =============================================================================
echo ""
log_success "Installation complete!"
echo ""
echo "Services:"
[[ "$SKIP_EMBEDDING" == "false" ]] && echo "  - Embedding Service: http://localhost:8891"
[[ "$SKIP_LITELLM" == "false" ]] && echo "  - LiteLLM Proxy:     http://localhost:4000"
echo ""
echo "Management commands:"
echo "  systemctl status qubinode-embedding.service"
echo "  systemctl status qubinode-litellm.service"
echo "  journalctl -u qubinode-embedding.service -f"
echo "  journalctl -u qubinode-litellm.service -f"
echo ""
if [[ "$SKIP_LITELLM" == "false" ]]; then
    echo "LiteLLM Master Key (save this):"
    grep LITELLM_MASTER_KEY /etc/qubinode/litellm.env | cut -d= -f2
fi
