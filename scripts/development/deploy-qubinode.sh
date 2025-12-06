#!/bin/bash
# =============================================================================
# Qubinode Navigator One-Shot Deployment Script
# =============================================================================
#
# 🎯 PURPOSE: Deploy complete Qubinode Navigator solution on modern RHEL-based machines
# 🖥️  SUPPORTED: RHEL 9/10, CentOS Stream 9/10, Rocky Linux 9, AlmaLinux 9
# 🤖 AI HELP: Integrated AI Assistant for troubleshooting and guidance
# 🔗 INTEGRATION: Uses existing setup.sh and rhel9-linux-hypervisor.sh architecture
# 📜 ADR: Based on ADR-0001 One-Shot Deployment Script Consolidation
#
# USAGE:
#   1. Configure environment variables in .env file or export them
#   2. Run: ./deploy-qubinode.sh
#   3. If issues occur, the AI Assistant will be available for help
#
# =============================================================================

set -euo pipefail

# Script metadata
SCRIPT_VERSION="1.0.0"
SCRIPT_NAME="Qubinode Navigator One-Shot Deployment"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
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

log_step() {
    echo -e "${PURPLE}[STEP]${NC} $1"
}

log_ai() {
    echo -e "${CYAN}[AI ASSISTANT]${NC} $1"
}

# =============================================================================
# CONFIGURATION SECTION
# =============================================================================

# Load environment variables from .env file if it exists
if [[ -f "$SCRIPT_DIR/.env" ]]; then
    log_info "Loading configuration from .env file..."
    set -a  # Automatically export all variables
    source "$SCRIPT_DIR/.env"
    set +a
fi

# Required Environment Variables (with defaults)
export QUBINODE_DOMAIN="${QUBINODE_DOMAIN:-example.com}"
export QUBINODE_ADMIN_USER="${QUBINODE_ADMIN_USER:-admin}"
export QUBINODE_CLUSTER_NAME="${QUBINODE_CLUSTER_NAME:-qubinode}"
export QUBINODE_DEPLOYMENT_MODE="${QUBINODE_DEPLOYMENT_MODE:-production}"

# Integration with existing Qubinode Navigator architecture
export GIT_REPO="https://github.com/Qubinode/qubinode_navigator.git"
export CICD_PIPELINE="${CICD_PIPELINE:-false}"
export INVENTORY="${INVENTORY:-localhost}"
export USE_HASHICORP_VAULT="${USE_HASHICORP_VAULT:-false}"
export USE_HASHICORP_CLOUD="${USE_HASHICORP_CLOUD:-false}"
export SSH_USER="${SSH_USER:-lab-user}"
export ANSIBLE_SAFE_VERSION="0.0.14"

# Optional Environment Variables
export QUBINODE_ENABLE_AI_ASSISTANT="${QUBINODE_ENABLE_AI_ASSISTANT:-true}"

# AI Assistant Configuration
export AI_ASSISTANT_PORT="${AI_ASSISTANT_PORT:-8080}"
export AI_ASSISTANT_VERSION="${AI_ASSISTANT_VERSION:-latest}"

# Airflow Orchestration Configuration (Optional Feature)
export QUBINODE_ENABLE_AIRFLOW="${QUBINODE_ENABLE_AIRFLOW:-false}"
export AIRFLOW_PORT="${AIRFLOW_PORT:-8888}"
export AIRFLOW_VERSION="${AIRFLOW_VERSION:-2.10.4-python3.12}"
export AIRFLOW_NETWORK="${AIRFLOW_NETWORK:-airflow_default}"
export QUBINODE_ENABLE_NGINX_PROXY="${QUBINODE_ENABLE_NGINX_PROXY:-false}"
export NGINX_PORT="${NGINX_PORT:-80}"

# ADR-0050: Host AI Services Configuration (Hybrid Architecture)
# These services run on the host for better performance and smaller containers
export QUBINODE_ENABLE_AI_SERVICES="${QUBINODE_ENABLE_AI_SERVICES:-false}"
export EMBEDDING_SERVICE_PORT="${EMBEDDING_SERVICE_PORT:-8891}"
export LITELLM_PROXY_PORT="${LITELLM_PROXY_PORT:-4000}"

# Internal variables
DEPLOYMENT_LOG="/tmp/qubinode-deployment-$(date +%Y%m%d-%H%M%S).log"
AI_ASSISTANT_CONTAINER=""
DEPLOYMENT_FAILED=false

# Set working directory - use the parent directory of where the script is located
# This ensures the script works correctly whether run directly or via sudo
# If the script is at /path/to/qubinode_navigator/scripts/development/deploy-qubinode.sh,
# SCRIPT_DIR is /path/to/qubinode_navigator/scripts/development
# MY_DIR should be /path/to (three levels of dirname: scripts -> qubinode_navigator -> parent)
MY_DIR="$(dirname "$(dirname "$(dirname "$SCRIPT_DIR")")")"

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

show_banner() {
    echo -e "${CYAN}"
    cat << 'EOF'
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║     ██████  ██    ██ ██████  ██ ███    ██  ██████  ██████     ║
    ║    ██    ██ ██    ██ ██   ██ ██ ████   ██ ██    ██ ██   ██    ║
    ║    ██    ██ ██    ██ ██████  ██ ██ ██  ██ ██    ██ ██   ██    ║
    ║    ██ ▄▄ ██ ██    ██ ██   ██ ██ ██  ██ ██ ██    ██ ██   ██    ║
    ║     ██████   ██████  ██████  ██ ██   ████  ██████  ██████     ║
    ║        ▀▀                                                     ║
    ║                                                               ║
    ║              NAVIGATOR ONE-SHOT DEPLOYMENT                    ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
    echo -e "${BLUE}Version: ${SCRIPT_VERSION}${NC}"
    echo -e "${BLUE}Target: RHEL-based systems (RHEL, CentOS, Rocky Linux)${NC}"
    echo -e "${BLUE}Mode: ${QUBINODE_DEPLOYMENT_MODE}${NC}"
    echo ""
}

# OS Detection Engine - Refactored from setup.sh with modern OS support
get_rhel_version() {
    log_info "Detecting operating system..."

    if [[ ! -f /etc/redhat-release ]]; then
        log_error "This script requires a RHEL-based operating system"
        return 1
    fi

    local os_info=$(cat /etc/redhat-release)
    log_info "Detected OS: $os_info"

    # Modern RHEL-based OS detection (removes RHEL 8, adds RHEL 10/CentOS 10)
    if [[ $os_info =~ "Red Hat Enterprise Linux release 10" ]]; then
        export BASE_OS="RHEL10"
        export OS_TYPE="rhel"
        export OS_VERSION="10"
    elif [[ $os_info =~ "Red Hat Enterprise Linux release 9" ]]; then
        export BASE_OS="RHEL9"
        export OS_TYPE="rhel"
        export OS_VERSION="9"
    elif [[ $os_info =~ "CentOS Stream release 10" ]]; then
        export BASE_OS="CENTOS10"
        export OS_TYPE="centos"
        export OS_VERSION="10"
    elif [[ $os_info =~ "CentOS Stream release 9" ]]; then
        export BASE_OS="CENTOS9"
        export OS_TYPE="centos"
        export OS_VERSION="9"
    elif [[ $os_info =~ "Rocky Linux release 9" ]]; then
        export BASE_OS="ROCKY9"
        export OS_TYPE="rocky"
        export OS_VERSION="9"
    elif [[ $os_info =~ "AlmaLinux release 9" ]]; then
        export BASE_OS="ALMA9"
        export OS_TYPE="alma"
        export OS_VERSION="9"
    elif [[ $os_info =~ "Red Hat Enterprise Linux release 8" ]]; then
        log_error "RHEL 8 is no longer supported. Please upgrade to RHEL 9 or 10."
        log_error "Migration guide: https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/9/html/upgrading_from_rhel_8_to_rhel_9/index"
        ask_ai_for_help "rhel8_unsupported" "RHEL 8 detected but no longer supported. Need upgrade guidance."
        return 1
    else
        log_error "Unsupported operating system: $os_info"
        log_error "Supported OS versions:"
        log_error "  - RHEL 9.x or 10.x"
        log_error "  - CentOS Stream 9 or 10"
        log_error "  - Rocky Linux 9.x"
        log_error "  - AlmaLinux 9.x"
        ask_ai_for_help "unsupported_os" "Unsupported OS detected: $os_info"
        return 1
    fi

    log_success "OS Detection: $BASE_OS (Type: $OS_TYPE, Version: $OS_VERSION)"
    return 0
}

# Deployment Target Detection - Based on research of existing patterns
detect_deployment_target() {
    log_info "Detecting deployment target and configuration..."

    # Check for existing deployment configurations
    if [[ -f "$SCRIPT_DIR/notouch.env" ]]; then
        log_info "Found existing notouch.env configuration"
        source "$SCRIPT_DIR/notouch.env" || {
            log_warning "Failed to source notouch.env, continuing..."
        }
    fi

    # Detect deployment target based on environment or domain
    local deployment_target="unknown"

    if [[ "$QUBINODE_DOMAIN" =~ "hetzner" || "$QUBINODE_DOMAIN" =~ "qubinodelab.io" || "$INVENTORY" == "hetzner" ]]; then
        deployment_target="hetzner"
        export DEPLOYMENT_TARGET="hetzner"
        export INVENTORY="${INVENTORY:-hetzner}"
        export FORWARDER="${FORWARDER:-1.1.1.1}"
        export INTERFACE="${INTERFACE:-bond0}"
        log_info "Detected Hetzner Cloud deployment target"
    elif [[ "$QUBINODE_DOMAIN" =~ "opentlc.com" || "$QUBINODE_DOMAIN" =~ "redhat.com" || "$INVENTORY" == "rhel9-equinix" ]]; then
        deployment_target="equinix"
        export DEPLOYMENT_TARGET="equinix"
        export INVENTORY="${INVENTORY:-rhel9-equinix}"
        # Auto-detect forwarder from /etc/resolv.conf for Equinix
        export FORWARDER="${FORWARDER:-$(awk '/^nameserver/ {print $2}' /etc/resolv.conf | head -1)}"
        export INTERFACE="${INTERFACE:-bond0}"
        log_info "Detected Red Hat Demo System (Equinix) deployment target"
    elif [[ "$QUBINODE_DOMAIN" =~ "dev.local" || "$INVENTORY" == "localhost" ]]; then
        deployment_target="local"
        export DEPLOYMENT_TARGET="local"
        export INVENTORY="${INVENTORY:-localhost}"
        export FORWARDER="${FORWARDER:-8.8.8.8}"
        export INTERFACE="${INTERFACE:-$(ip route | grep default | awk '{print $5}' | head -1)}"
        log_info "Detected local development deployment target"
    else
        deployment_target="custom"
        export DEPLOYMENT_TARGET="custom"
        export INVENTORY="${INVENTORY:-localhost}"
        export FORWARDER="${FORWARDER:-8.8.8.8}"
        export INTERFACE="${INTERFACE:-$(ip route | grep default | awk '{print $5}' | head -1)}"
        log_info "Using custom deployment configuration"
    fi

    # Set deployment-specific defaults
    export CICD_PIPELINE="${CICD_PIPELINE:-true}"
    export ENV_USERNAME="${ENV_USERNAME:-$SSH_USER}"
    export KVM_VERSION="${KVM_VERSION:-latest}"
    export CICD_ENVIORNMENT="${CICD_ENVIORNMENT:-gitlab}"
    export ACTIVE_BRIDGE="${ACTIVE_BRIDGE:-false}"
    export USE_ROUTE53="${USE_ROUTE53:-false}"
    export DISK="${DISK:-skip}"  # Default to skip disk selection for automated deployment

    log_success "Deployment target: $deployment_target (Inventory: $INVENTORY)"
    log_info "Network configuration: Interface=$INTERFACE, Forwarder=$FORWARDER"

    return 0
}

check_prerequisites() {
    log_step "Checking prerequisites..."

    # Check if running as root
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        return 1
    fi

    # Check system resources
    local mem_gb=$(free -g | awk '/^Mem:/{print $2}')
    local disk_gb=$(df / | awk 'NR==2{print int($4/1024/1024)}')

    log_info "System Resources:"
    log_info "  Memory: ${mem_gb}GB"
    log_info "  Disk Space: ${disk_gb}GB available"

    if [[ $mem_gb -lt 8 ]]; then
        log_warning "Minimum 8GB RAM recommended (found ${mem_gb}GB)"
    fi

    if [[ $disk_gb -lt 50 ]]; then
        log_warning "Minimum 50GB disk space recommended (found ${disk_gb}GB available)"
    fi

    # Check network connectivity
    if ! ping -c 1 8.8.8.8 &> /dev/null; then
        log_error "No internet connectivity detected"
        return 1
    fi

    log_success "Prerequisites check completed"
    return 0
}

validate_configuration() {
    log_step "Validating configuration..."

    # Check required variables
    local required_vars=(
        "QUBINODE_DOMAIN"
        "QUBINODE_ADMIN_USER"
        "QUBINODE_CLUSTER_NAME"
    )

    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            log_error "Required environment variable $var is not set"
            return 1
        fi
    done

    # Validate domain format
    if [[ ! $QUBINODE_DOMAIN =~ ^[a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9]*\.[a-zA-Z]{2,}$ ]]; then
        log_error "Invalid domain format: $QUBINODE_DOMAIN"
        return 1
    fi

    log_success "Configuration validation completed"
    return 0
}

# =============================================================================
# AI ASSISTANT INTEGRATION
# =============================================================================

start_ai_assistant() {
    if [[ "$QUBINODE_ENABLE_AI_ASSISTANT" != "true" ]]; then
        log_info "AI Assistant disabled, skipping..."
        return 0
    fi

    log_step "Starting AI Assistant for troubleshooting support..."

    # Check if podman is available
    if ! command -v podman &> /dev/null; then
        log_info "Podman not found, installing for AI Assistant..."
        if ! dnf install -y podman; then
            log_warning "Failed to install podman, AI Assistant will not be available"
            return 1
        fi
        log_success "Podman installed successfully"
    fi

    # Check if AI Assistant container is already running
    if podman ps --format "{{.Names}}" | grep -q "^qubinode-ai-assistant$"; then
        log_info "AI Assistant container is already running"
        # Verify it's accessible
        if curl -s http://localhost:${AI_ASSISTANT_PORT}/health &> /dev/null; then
            log_success "AI Assistant is ready at http://localhost:${AI_ASSISTANT_PORT}"
            AI_ASSISTANT_CONTAINER="qubinode-ai-assistant"
            log_ai "I'm already running and ready to help with deployment issues!"
            return 0
        else
            log_warning "AI Assistant container exists but not responding, restarting..."
            podman stop qubinode-ai-assistant &> /dev/null || true
            podman rm qubinode-ai-assistant &> /dev/null || true
        fi
    fi

    # Pull and start AI Assistant container
    log_info "Pulling AI Assistant container..."
    if podman pull quay.io/takinosh/qubinode-ai-assistant:${AI_ASSISTANT_VERSION}; then
        log_info "Starting AI Assistant container..."
        AI_ASSISTANT_CONTAINER=$(podman run -d \
            --name qubinode-ai-assistant \
            -p ${AI_ASSISTANT_PORT}:8080 \
            -e DEPLOYMENT_MODE=${QUBINODE_DEPLOYMENT_MODE} \
            -e LOG_LEVEL=INFO \
            quay.io/takinosh/qubinode-ai-assistant:${AI_ASSISTANT_VERSION})

        # Wait for AI Assistant to be ready
        log_info "Waiting for AI Assistant to be ready..."
        for i in {1..30}; do
            if curl -s http://localhost:${AI_ASSISTANT_PORT}/health &> /dev/null; then
                log_success "AI Assistant is ready at http://localhost:${AI_ASSISTANT_PORT}"
                log_ai "You can ask me for help if you encounter any issues during deployment!"
                return 0
            fi
            sleep 2
        done

        log_warning "AI Assistant started but health check failed"
        return 1
    else
        log_warning "Failed to pull AI Assistant container, continuing without AI support"
        return 1
    fi
}

ask_ai_for_help() {
    local error_context="$1"
    local error_message="$2"

    if [[ -z "$AI_ASSISTANT_CONTAINER" ]]; then
        log_warning "AI Assistant not available for troubleshooting"
        return 1
    fi

    log_ai "Analyzing error and providing troubleshooting guidance..."

    # Prepare context for AI Assistant
    local context_data=$(cat << EOF
{
    "deployment_context": {
        "os_type": "$OS_TYPE",
        "os_version": "$OS_VERSION",
        "deployment_mode": "$QUBINODE_DEPLOYMENT_MODE",
        "cluster_name": "$QUBINODE_CLUSTER_NAME",
        "domain": "$QUBINODE_DOMAIN"
    },
    "error_context": "$error_context",
    "error_message": "$error_message",
    "system_info": {
        "memory_gb": $(free -g | awk '/^Mem:/{print $2}'),
        "disk_space_gb": $(df / | awk 'NR==2{print int($4/1024/1024)}'),
        "timestamp": "$(date -Iseconds)"
    }
}
EOF
    )

    # Query AI Assistant for help
    # Properly escape the context data for JSON
    local escaped_context=$(echo "$context_data" | jq -R -s .)
    local ai_response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "{\"message\": \"I encountered an error during Qubinode deployment. Context: $escaped_context\", \"max_tokens\": 500}" \
        http://localhost:${AI_ASSISTANT_PORT}/chat 2>/dev/null)

    if [[ $? -eq 0 ]] && [[ -n "$ai_response" ]]; then
        echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${CYAN}║                    AI ASSISTANT GUIDANCE                     ║${NC}"
        echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
        echo "$ai_response" | jq -r '.text // .message // .' 2>/dev/null || echo "$ai_response"
        echo ""
        echo -e "${CYAN}For more help, visit: http://localhost:${AI_ASSISTANT_PORT}${NC}"
        return 0
    else
        log_warning "Could not get AI assistance at this time"
        return 1
    fi
}

# =============================================================================
# AIRFLOW ORCHESTRATION INTEGRATION
# =============================================================================

deploy_airflow_services() {
    if [[ "$QUBINODE_ENABLE_AIRFLOW" != "true" ]]; then
        log_info "Airflow deployment disabled, skipping..."
        return 0
    fi

    log_step "Deploying Apache Airflow for workflow orchestration..."

    # Check if podman is available
    if ! command -v podman &> /dev/null; then
        log_warning "Podman not found, Airflow will not be available"
        return 1
    fi

    # Check if podman-compose is available
    if ! command -v podman-compose &> /dev/null; then
        log_info "Installing podman-compose for Airflow..."
        if ! pip3 install podman-compose; then
            log_warning "Failed to install podman-compose, skipping Airflow deployment"
            return 1
        fi
        log_success "podman-compose installed successfully"
    fi

    # Change to airflow directory - calculate relative to repo root
    # SCRIPT_DIR is /path/to/qubinode_navigator/scripts/development
    # repo_root is /path/to/qubinode_navigator (go up two levels from SCRIPT_DIR)
    local repo_root="$(dirname "$(dirname "$SCRIPT_DIR")")"
    local airflow_dir="$repo_root/airflow"
    if [[ ! -d "$airflow_dir" ]]; then
        log_warning "Airflow directory not found at $airflow_dir, skipping Airflow deployment"
        return 1
    fi
    
    cd "$airflow_dir" || {
        log_warning "Failed to change to airflow directory, skipping Airflow deployment"
        return 1
    }

    # Enable Airflow in configuration
    log_info "Enabling Airflow services..."
    export ENABLE_AIRFLOW="true"

    # Call the dedicated Airflow deployment script
    log_info "Starting Airflow services via deploy-airflow.sh..."
    if bash ./deploy-airflow.sh deploy; then
        log_success "Airflow deployment initiated successfully"

        # Wait for Airflow to be ready
        log_info "Waiting for Airflow webserver to be ready on port ${AIRFLOW_PORT}..."
        for i in {1..60}; do
            if curl -s http://localhost:${AIRFLOW_PORT}/health &> /dev/null; then
                log_success "Airflow webserver is ready at http://localhost:${AIRFLOW_PORT}"

                # Attempt to connect AI Assistant to Airflow network if it's running
                if [[ "$QUBINODE_ENABLE_AI_ASSISTANT" == "true" ]]; then
                    if podman ps --format "{{.Names}}" | grep -q "^qubinode-ai-assistant$"; then
                        log_info "Connecting AI Assistant to Airflow network..."
                        if podman network connect ${AIRFLOW_NETWORK} qubinode-ai-assistant 2>/dev/null; then
                            log_success "AI Assistant connected to Airflow network"
                        else
                            log_warning "AI Assistant already connected or connection failed (non-critical)"
                        fi
                    else
                        log_warning "AI Assistant not running - restart it after Airflow for full integration"
                    fi
                fi

                return 0
            fi
            sleep 2
        done

        log_warning "Airflow webserver health check did not complete in time, but services may still be running"
        return 0
    else
        log_error "Airflow deployment failed"
        ask_ai_for_help "airflow_deploy" "Airflow deployment via deploy-airflow.sh failed"
        return 1
    fi
}

# =============================================================================
# ADR-0050: HOST AI SERVICES (Hybrid Architecture)
# =============================================================================
# These services run on the host (not in containers) to:
# - Reduce container image size from 10.5GB to ~2-3GB
# - Allow GPU access for embedding models
# - Share services across multiple tools

deploy_host_ai_services() {
    if [[ "$QUBINODE_ENABLE_AI_SERVICES" != "true" ]]; then
        log_info "Host AI services disabled, skipping..."
        return 0
    fi

    log_step "Deploying Host AI Services (ADR-0050)..."

    # Check if the install script exists
    local install_script="$SCRIPT_DIR/airflow/host-services/install-host-services.sh"
    if [[ ! -f "$install_script" ]]; then
        log_error "Host services install script not found: $install_script"
        return 1
    fi

    # Run the install script
    log_info "Installing Embedding Service and LiteLLM Proxy..."
    if bash "$install_script"; then
        log_success "Host AI services installed successfully"
    else
        log_error "Host AI services installation failed"
        ask_ai_for_help "ai_services_install" "Host AI services installation failed"
        return 1
    fi

    # Verify services are running
    log_info "Verifying host AI services..."
    local services_ok=true

    # Check Embedding Service
    if systemctl is-active --quiet qubinode-embedding.service; then
        log_success "Embedding Service running on port ${EMBEDDING_SERVICE_PORT}"
    else
        log_warning "Embedding Service not running"
        services_ok=false
    fi

    # Check LiteLLM Proxy
    if systemctl is-active --quiet qubinode-litellm.service; then
        log_success "LiteLLM Proxy running on port ${LITELLM_PROXY_PORT}"
    else
        log_warning "LiteLLM Proxy not running"
        services_ok=false
    fi

    # Health checks
    sleep 5
    if curl -s http://localhost:${EMBEDDING_SERVICE_PORT}/health > /dev/null 2>&1; then
        log_success "Embedding Service health check passed"
    else
        log_warning "Embedding Service health check failed (may still be starting)"
    fi

    if curl -s http://localhost:${LITELLM_PROXY_PORT}/health > /dev/null 2>&1; then
        log_success "LiteLLM Proxy health check passed"
    else
        log_warning "LiteLLM Proxy health check failed (may still be starting)"
    fi

    if [[ "$services_ok" == "true" ]]; then
        log_success "All host AI services deployed successfully"
        return 0
    else
        log_warning "Some host AI services failed to start, but deployment continues"
        return 0  # Non-blocking
    fi
}

setup_nginx_reverse_proxy() {
    if [[ "$QUBINODE_ENABLE_AIRFLOW" != "true" ]]; then
        log_info "Airflow not enabled, skipping nginx reverse proxy setup..."
        return 0
    fi

    log_step "Setting up nginx reverse proxy for unified access..."

    # Install nginx if not present
    if ! command -v nginx &> /dev/null; then
        log_info "Installing nginx..."
        if ! dnf install -y nginx; then
            log_warning "Failed to install nginx, skipping reverse proxy setup"
            return 1
        fi
        log_success "nginx installed successfully"
    fi

    # Create nginx configuration for Airflow and AI Assistant
    log_info "Creating nginx reverse proxy configuration..."
    cat > /etc/nginx/conf.d/qubinode.conf << 'NGINX_CONF'
# Qubinode Navigator - Nginx Reverse Proxy
# Provides unified access to Airflow and AI Assistant

# Upstream definitions
upstream airflow_backend {
    server localhost:8888;
}

upstream ai_assistant_backend {
    server localhost:8080;
}

# HTTP server
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;

    # Airflow UI at root
    location / {
        proxy_pass http://airflow_backend/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support for Airflow live updates
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Timeouts
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # AI Assistant API at /ai/
    location /ai/ {
        proxy_pass http://ai_assistant_backend/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://airflow_backend/health;
        access_log off;
    }
}
NGINX_CONF

    # Test nginx configuration
    log_info "Testing nginx configuration..."
    if ! nginx -t; then
        log_error "nginx configuration test failed"
        return 1
    fi
    log_success "nginx configuration is valid"

    # Enable and start nginx
    log_info "Starting nginx service..."
    if ! systemctl enable nginx; then
        log_warning "Failed to enable nginx for auto-start"
    fi

    if ! systemctl restart nginx; then
        log_error "Failed to start nginx"
        return 1
    fi

    if systemctl is-active --quiet nginx; then
        log_success "nginx reverse proxy is running"
    else
        log_error "nginx failed to start"
        return 1
    fi

    return 0
}

# =============================================================================
# DEPLOYMENT FUNCTIONS
# =============================================================================

# Package Installation Manager - Refactored from setup.sh
configure_os() {
    local base_os="$1"
    log_step "Configuring OS packages for $base_os..."

    # Update system first
    log_info "Updating system packages..."
    sudo dnf update -y || {
        log_error "Failed to update system packages"
        ask_ai_for_help "package_update" "dnf update failed for $base_os"
        return 1
    }

    # Install packages based on OS type
    case "$base_os" in
        "RHEL10")
            log_info "Installing RHEL 10 packages..."
            sudo dnf install -y git vim unzip wget bind-utils python3 python3-pip python3-devel tar util-linux-user gcc podman ansible-core make sshpass || {
                log_error "Failed to install RHEL 10 packages"
                ask_ai_for_help "rhel10_packages" "Package installation failed for $base_os"
                return 1
            }
            log_info "Using Python 3.12 (default in RHEL 10)"
            ;;
        "RHEL9")
            log_info "Installing RHEL 9 packages..."
            sudo dnf install -y git vim unzip wget bind-utils python3.11 python3.11-pip python3.11-devel tar util-linux-user gcc podman ansible-core make sshpass || {
                log_error "Failed to install RHEL 9 packages"
                ask_ai_for_help "rhel9_packages" "Package installation failed for $base_os"
                return 1
            }
            # Set Python 3.11 as default for ansible-navigator compatibility
            sudo alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
            sudo alternatives --install /usr/bin/pip3 pip3 /usr/bin/pip3.11 1
            ;;
        "CENTOS10")
            log_info "Installing CentOS Stream 10 packages..."
            sudo dnf install -y git vim unzip wget bind-utils python3 python3-pip python3-devel tar util-linux-user gcc podman ansible-core make sshpass || {
                log_error "Failed to install CentOS Stream 10 packages"
                ask_ai_for_help "centos10_packages" "Package installation failed for $base_os"
                return 1
            }
            log_info "Using Python 3.12 (default in CentOS Stream 10)"
            ;;
        "CENTOS9")
            log_info "Installing CentOS Stream 9 packages..."
            sudo dnf install -y git vim unzip wget bind-utils python3.11 python3.11-pip python3.11-devel tar util-linux-user gcc podman ansible-core make sshpass || {
                log_error "Failed to install CentOS Stream 9 packages"
                ask_ai_for_help "centos9_packages" "Package installation failed for $base_os"
                return 1
            }
            # Set Python 3.11 as default for ansible-navigator compatibility
            sudo alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
            sudo alternatives --install /usr/bin/pip3 pip3 /usr/bin/pip3.11 1
            ;;
        "ROCKY9"|"ALMA9")
            log_info "Installing Rocky/Alma Linux packages..."
            sudo dnf install -y git vim unzip wget bind-utils python3-pip tar util-linux-user gcc python3-devel podman ansible-core make sshpass || {
                log_error "Failed to install Rocky/Alma packages"
                ask_ai_for_help "rocky_alma_packages" "Package installation failed for $base_os"
                return 1
            }
            ;;
        *)
            log_error "Unsupported OS for package configuration: $base_os"
            return 1
            ;;
    esac

    log_success "OS packages configured successfully for $base_os"
    return 0
}

# Enhanced package installation with development tools
install_packages() {
    log_step "Installing additional packages and development tools..."

    # Core packages required for containerized Ansible execution
    local core_packages=(
        "openssl-devel"
        "bzip2-devel"
        "libffi-devel"
        "wget"
        "vim"
        "podman"
        "ncurses-devel"
        "sqlite-devel"
        "firewalld"
        "make"
        "gcc"
        "git"
        "unzip"
        "sshpass"
        "lvm2"
        "python3"
        "python3-pip"
        "cockpit-leapp"
    )

    log_info "Installing core packages..."
    for package in "${core_packages[@]}"; do
        if rpm -q "$package" >/dev/null 2>&1; then
            log_info "Package $package already installed"
        else
            log_info "Installing package $package"
            sudo dnf install "$package" -y || {
                log_warning "Failed to install $package, continuing..."
            }
        fi
    done

    # Install Development Tools group
    if dnf group info "Development Tools" >/dev/null 2>&1; then
        log_info "Development Tools group already installed"
    else
        log_info "Installing Development Tools group..."
        sudo dnf groupinstall "Development Tools" -y || {
            log_warning "Failed to install Development Tools group"
        }
    fi

    log_success "Package installation completed"
    return 0
}

# SSH Configuration - Refactored from setup.sh
configure_ssh() {
    log_step "Configuring SSH..."

    if [[ -f ~/.ssh/id_rsa ]]; then
        log_info "SSH key already exists"
    else
        log_info "Generating SSH key..."
        local ip_address=$(hostname -I | awk '{print $1}')
        ssh-keygen -f ~/.ssh/id_rsa -t rsa -N '' || {
            log_error "Failed to generate SSH key"
            ask_ai_for_help "ssh_keygen" "ssh-keygen failed"
            return 1
        }

        # Configure SSH key for local access
        if [[ "$CICD_PIPELINE" == "true" ]]; then
            if [[ "$EUID" -eq 0 ]]; then
                sshpass -p "$SSH_PASSWORD" ssh-copy-id -o StrictHostKeyChecking=no "$SSH_USER@${ip_address}" || {
                    log_warning "Failed to copy SSH key automatically"
                }
            else
                sshpass -p "$SSH_PASSWORD" ssh-copy-id -o StrictHostKeyChecking=no "$USER@${ip_address}" || {
                    log_warning "Failed to copy SSH key automatically"
                }
                sudo ssh-keygen -f /root/.ssh/id_rsa -t rsa -N '' || true
            fi
        else
            if [[ "$EUID" -eq 0 ]]; then
                log_info "Please manually copy SSH key to target user if needed"
                log_info "Command: ssh-copy-id $SSH_USER@${ip_address}"
            else
                ssh-copy-id "$USER@${ip_address}" || {
                    log_warning "Failed to copy SSH key, you may need to do this manually"
                }
                sudo ssh-keygen -f /root/.ssh/id_rsa -t rsa -N '' || true
            fi
        fi
    fi

    log_success "SSH configuration completed"
    return 0
}

# Firewall Configuration - Refactored from setup.sh
configure_firewalld() {
    log_step "Configuring firewalld..."

    if systemctl is-active --quiet firewalld; then
        log_info "firewalld is already active"
    else
        log_info "Starting firewalld..."
        sudo systemctl start firewalld || {
            log_error "Failed to start firewalld"
            ask_ai_for_help "firewalld_start" "systemctl start firewalld failed"
            return 1
        }
        sudo systemctl enable firewalld || {
            log_warning "Failed to enable firewalld"
        }
    fi

    # If Airflow is enabled, configure firewall for nginx proxy
    if [[ "$QUBINODE_ENABLE_AIRFLOW" == "true" ]]; then
        log_info "Configuring firewall for Airflow deployment..."

        # Close direct access to Airflow and AI Assistant ports (nginx will proxy them)
        log_info "Closing direct access to internal service ports..."
        firewall-cmd --permanent --remove-port=8888/tcp 2>/dev/null || log_info "Port 8888 already closed or not open"
        firewall-cmd --permanent --remove-port=8080/tcp 2>/dev/null || log_info "Port 8080 already closed or not open"

        # Open HTTP/HTTPS for nginx reverse proxy
        log_info "Opening HTTP/HTTPS ports for nginx..."
        firewall-cmd --permanent --add-service=http || log_warning "HTTP service already added"
        firewall-cmd --permanent --add-service=https || log_warning "HTTPS service already added"

        # Reload firewall rules
        log_info "Reloading firewall rules..."
        if firewall-cmd --reload; then
            log_success "Firewall rules updated for Airflow deployment"
        else
            log_warning "Failed to reload firewall, continuing anyway..."
        fi
    fi

    log_success "Firewall configuration completed"
    return 0
}

# Repository Manager - Refactored from setup.sh
get_qubinode_navigator() {
    local target_dir="$1"
    log_step "Setting up Qubinode Navigator repository..."

    if [[ -d "$target_dir/qubinode_navigator" ]]; then
        log_info "Qubinode Navigator already exists, updating..."
        git -C "$target_dir/qubinode_navigator" pull || {
            log_warning "Failed to update repository, continuing with current version"
        }
    else
        log_info "Cloning Qubinode Navigator repository..."
        cd "$target_dir" || return 1
        git clone "$GIT_REPO" || {
            log_error "Failed to clone Qubinode Navigator repository"
            ask_ai_for_help "git_clone" "Failed to clone $GIT_REPO"
            return 1
        }

        # Create system-wide symlink
        sudo ln -sf "$target_dir/qubinode_navigator" /opt/qubinode_navigator || {
            log_warning "Failed to create system symlink"
        }
    fi

    # Set proper permissions
    chmod +x "$target_dir/qubinode_navigator"/*.sh 2>/dev/null || true
    chmod +x "$target_dir/qubinode_navigator/ai-assistant/scripts/"*.sh 2>/dev/null || true

    log_success "Qubinode Navigator repository setup completed"
    return 0
}

configure_environment() {
    log_step "Configuring Qubinode environment..."

    # Create/update environment configuration in current directory
    local env_file="$SCRIPT_DIR/.env"

    # Backup existing .env if it exists
    if [[ -f "$env_file" ]]; then
        cp "$env_file" "${env_file}.backup.$(date +%Y%m%d-%H%M%S)"
        log_info "Backed up existing .env file"
    fi

    # Create comprehensive environment configuration
    log_info "Creating environment configuration..."
    cat > "$env_file" << EOF
# Qubinode Navigator Configuration
# Generated by one-shot deployment script on $(date)

# =============================================================================
# BASIC CONFIGURATION
# =============================================================================
QUBINODE_DOMAIN=${QUBINODE_DOMAIN}
QUBINODE_ADMIN_USER=${QUBINODE_ADMIN_USER}
QUBINODE_CLUSTER_NAME=${QUBINODE_CLUSTER_NAME}
QUBINODE_DEPLOYMENT_MODE=${QUBINODE_DEPLOYMENT_MODE}

# =============================================================================
# QUBINODE NAVIGATOR INTEGRATION
# =============================================================================
GIT_REPO=${GIT_REPO}
CICD_PIPELINE=${CICD_PIPELINE}
INVENTORY=${INVENTORY}
USE_HASHICORP_VAULT=${USE_HASHICORP_VAULT}
SSH_USER=${SSH_USER}

# =============================================================================
# RESOURCE CONFIGURATION
# =============================================================================
QUBINODE_STORAGE_SIZE=${QUBINODE_STORAGE_SIZE}
QUBINODE_WORKER_NODES=${QUBINODE_WORKER_NODES}

# =============================================================================
# FEATURE FLAGS
# =============================================================================
QUBINODE_ENABLE_AI_ASSISTANT=${QUBINODE_ENABLE_AI_ASSISTANT}
QUBINODE_ENABLE_MONITORING=${QUBINODE_ENABLE_MONITORING}
QUBINODE_ENABLE_LOGGING=${QUBINODE_ENABLE_LOGGING}

# =============================================================================
# AI ASSISTANT CONFIGURATION
# =============================================================================
AI_ASSISTANT_PORT=${AI_ASSISTANT_PORT}
AI_ASSISTANT_VERSION=${AI_ASSISTANT_VERSION}

# =============================================================================
# SYSTEM INFORMATION
# =============================================================================
OS_TYPE=${OS_TYPE}
OS_VERSION=${OS_VERSION}
BASE_OS=${BASE_OS}
DEPLOYMENT_TIMESTAMP=$(date -Iseconds)
DEPLOYMENT_LOG=${DEPLOYMENT_LOG}
EOF

    log_success "Environment configuration created at $env_file"
    return 0
}

# Deployment orchestration using existing architecture
deploy_qubinode_infrastructure() {
    local my_dir="$1"
    log_step "Deploying Qubinode infrastructure using existing architecture..."

    # Change to the qubinode directory
    cd "$my_dir/qubinode_navigator" || {
        log_error "Failed to change to qubinode_navigator directory"
        return 1
    }

    log_info "Working directory: $(pwd)"
    log_info "Deployment mode: $QUBINODE_DEPLOYMENT_MODE"
    log_info "Target OS: $BASE_OS"

    # Determine the appropriate deployment approach
    if [[ "$BASE_OS" == "ROCKY8" ]]; then
        log_error "Rocky Linux 8 should use the rocky-linux-hypervisor.sh script"
        log_error "This script focuses on modern RHEL-based systems (9+)"
        return 1
    fi

    # Use the existing setup.sh workflow but with our environment
    log_info "Executing Qubinode Navigator setup workflow..."
    log_info "This process includes:"
    log_info "  1. OS configuration and package installation"
    log_info "  2. SSH and firewall configuration"
    log_info "  3. Ansible Navigator setup"
    log_info "  4. Vault configuration"
    log_info "  5. Inventory generation"
    log_info "  6. KVM host deployment"
    log_info "  7. Bash aliases and kcli setup"

    # Execute the setup workflow step by step
    configure_os "$BASE_OS" || return 1
    install_packages || return 1
    configure_ssh || return 1
    configure_firewalld || return 1

    # Create notouch.env for compatibility with existing scripts
    create_notouch_env || return 1

    # Configure ansible navigator (from setup.sh)
    configure_navigator "$my_dir" || return 1

    # Configure vault (from setup.sh)
    configure_vault "$my_dir" || return 1

    # Generate inventory (from setup.sh)
    generate_inventory "$my_dir" || return 1

    # Test inventory (from setup.sh)
    test_inventory "$my_dir" || return 1

    # Deploy KVM host (from setup.sh)
    deploy_kvmhost || return 1

    # Configure bash aliases (from setup.sh)
    configure_bash_aliases || return 1

    # Setup kcli base (from setup.sh)
    setup_kcli_base || return 1

    log_success "Qubinode infrastructure deployment completed successfully!"
    return 0
}

# =============================================================================
# FUNCTIONS FROM SETUP.SH (Referenced but not yet implemented)
# =============================================================================

# Ansible Navigator Configurator - From setup.sh
configure_navigator() {
    local target_dir="$1"
    log_step "Configuring ansible navigator..."

    if [[ -d "$target_dir/qubinode_navigator" ]]; then
        cd "$target_dir/qubinode_navigator" || return 1

        if ! command -v ansible-navigator &> /dev/null; then
            log_info "Installing ansible-navigator..."
            make install-ansible-navigator || {
                log_error "Failed to install ansible-navigator"
                ask_ai_for_help "ansible_navigator_install" "make install-ansible-navigator failed"
                return 1
            }

            make copy-navigator || {
                log_warning "Failed to copy navigator configuration"
            }

            # Update navigator configuration for current user
            if [[ "$EUID" -eq 0 ]]; then
                sed -i "s|/home/admin/qubinode_navigator/inventories/localhost|/root/qubinode_navigator/inventories/${INVENTORY}|g" ~/.ansible-navigator.yml
            else
                sed -i "s|/home/admin/qubinode_navigator/inventories/localhost|/home/$USER/qubinode_navigator/inventories/${INVENTORY}|g" ~/.ansible-navigator.yml
            fi
        fi

        # Install Python requirements
        sudo pip3 install -r requirements.txt || {
            log_warning "Failed to install Python requirements"
        }

        # Install passlib for Ansible password_hash filter
        log_info "Ensuring passlib is installed for password hashing..."
        sudo pip3 install passlib || {
            log_warning "Failed to install passlib, password operations may fail"
        }

        # Load variables
        log_info "Loading variables..."

        # Auto-detect /tmp/config.yml and use non-interactive mode
        if [[ -f "/tmp/config.yml" ]]; then
            log_info "Found existing /tmp/config.yml, using automated configuration"
            # Use CI/CD mode with environment variables when config file exists
            export CICD_PIPELINE="true"

            # Set reasonable defaults for CI/CD mode when config file exists
            export ENV_USERNAME="${ENV_USERNAME:-$SSH_USER}"
            export DOMAIN="${DOMAIN:-$QUBINODE_DOMAIN}"
            export FORWARDER="${FORWARDER:-8.8.8.8}"
            export ACTIVE_BRIDGE="${ACTIVE_BRIDGE:-false}"
            export INTERFACE="${INTERFACE:-$(ip route | grep default | awk '{print $5}' | head -1)}"
            export DISK="${DISK:-skip}"

            # Use appropriate inventory - force to hetzner when config file exists
            # (Override the default localhost set earlier in the script)
            export INVENTORY="hetzner"

            log_info "Using configuration: Domain=$DOMAIN, User=$ENV_USERNAME, Interface=$INTERFACE"
        fi

        if [[ "$CICD_PIPELINE" == "false" ]]; then
            python3 "$target_dir/qubinode_navigator/load-variables.py" || {
                log_error "Failed to load variables"
                ask_ai_for_help "load_variables" "python3 load-variables.py failed"
                return 1
            }
        else
            if [[ -z "$ENV_USERNAME" || -z "$DOMAIN" || -z "$FORWARDER" || -z "$ACTIVE_BRIDGE" || -z "$INTERFACE" || -z "$DISK" ]]; then
                log_error "Required environment variables not set for CI/CD mode"
                return 1
            fi
            python3 "$target_dir/qubinode_navigator/load-variables.py" --username "$ENV_USERNAME" --domain "$DOMAIN" --forwarder "$FORWARDER" --bridge "$ACTIVE_BRIDGE" --interface "$INTERFACE" --disk "$DISK" || {
                log_error "Failed to load variables with parameters"
                return 1
            }
        fi
    else
        log_error "Qubinode Navigator directory not found"
        return 1
    fi

    log_success "Ansible Navigator configuration completed"
    return 0
}

# Vault Configuration - From setup.sh
configure_vault() {
    local target_dir="$1"
    log_step "Configuring ansible vault..."

    if [[ -d "$target_dir/qubinode_navigator" ]]; then
        cd "$target_dir/qubinode_navigator" || return 1

        # Install ansible-core if not present
        if ! command -v ansible-vault &> /dev/null; then
            sudo dnf install ansible-core -y || {
                log_error "Failed to install ansible-core"
                return 1
            }
        fi

        # Install ansiblesafe if not present
        if ! command -v ansiblesafe &> /dev/null; then
            log_info "Installing ansiblesafe..."
            curl -OL "https://github.com/tosin2013/ansiblesafe/releases/download/v0.0.12/ansiblesafe-v0.0.14-linux-amd64.tar.gz" || {
                log_error "Failed to download ansiblesafe"
                return 1
            }
            tar -zxvf "ansiblesafe-v0.0.14-linux-amd64.tar.gz"
            chmod +x ansiblesafe-linux-amd64
            sudo mv ansiblesafe-linux-amd64 /usr/local/bin/ansiblesafe
        fi

        # Configure Ansible Vault
        log_info "Configuring Ansible Vault password file..."
        if [[ ! -f ~/qubinode_navigator/ansible_vault_setup.sh ]]; then
            curl -OL https://gist.githubusercontent.com/tosin2013/022841d90216df8617244ab6d6aceaf8/raw/92400b9e459351d204feb67b985c08df6477d7fa/ansible_vault_setup.sh
            chmod +x ansible_vault_setup.sh
        fi

        rm -f ~/.vault_password
        sudo rm -rf /root/.vault_password

        if [[ "$USE_HASHICORP_VAULT" == "true" ]]; then
            echo "$SSH_PASSWORD" > ~/.vault_password
            sudo cp ~/.vault_password /root/.vault_password
            bash ./ansible_vault_setup.sh
        elif [[ "$QUBINODE_DEPLOYMENT_MODE" == "development" ]]; then
            log_info "Setting up vault password file for development mode..."
            # For development mode, create a default vault password file
            echo "defaultpassword" > ~/.vault_password
            chmod 600 ~/.vault_password
            sudo cp ~/.vault_password /root/.vault_password
            sudo chmod 600 /root/.vault_password
            log_success "Development vault password file created"
        else
            log_info "Setting up vault interactively..."
            bash ./ansible_vault_setup.sh
        fi
    else
        log_error "Qubinode Navigator directory not found"
        return 1
    fi

    log_success "Vault configuration completed"
    return 0
}

# Inventory Generation - From setup.sh
generate_inventory() {
    local target_dir="$1"
    log_step "Generating inventory..."

    if [[ -d "$target_dir/qubinode_navigator" ]]; then
        cd "$target_dir/qubinode_navigator" || return 1

        # Create inventory directory structure
        if [[ ! -d "inventories/${INVENTORY}" ]]; then
            mkdir -p "inventories/${INVENTORY}"
            mkdir -p "inventories/${INVENTORY}/group_vars/control"
        fi

        # Update bash aliases
        sed -i "s|export CURRENT_INVENTORY=\"localhost\"|export CURRENT_INVENTORY=\"${INVENTORY}\"|g" bash-aliases/functions.sh

        # Set up control host
        local control_host=$(hostname -I | awk '{print $1}')
        local control_user

        if [[ "$EUID" -eq 0 ]]; then
            control_user="$SSH_USER"
        else
            control_user="$USER"
        fi

        # Generate hosts file
        echo "[control]" > "inventories/${INVENTORY}/hosts"
        echo "control ansible_host=${control_host} ansible_user=${control_user}" >> "inventories/${INVENTORY}/hosts"

        # Create vault.yml if it doesn't exist
        local vault_file="inventories/${INVENTORY}/group_vars/control/vault.yml"
        if [[ ! -f "$vault_file" ]]; then
            log_info "Creating vault.yml with default credentials..."

            # Get password from environment or use default
            local vault_password="${SSH_PASSWORD:-COmp123\$%}"

            # Create unencrypted vault file first
            cat > "$vault_file" << VAULTEOF
---
# Ansible Vault - Sensitive Credentials
# Encrypted with ansible-vault

# FreeIPA Configuration
freeipa_server_admin_password: "${vault_password}"

# Red Hat Subscription Manager (leave empty for CentOS/community)
rhsm_org: ""
rhsm_activationkey: ""
rhsm_username: ""
rhsm_password: ""

# OpenShift Pull Secret (optional)
openshift_pull_secret: ""
VAULTEOF

            # Encrypt the vault file
            if [[ -f "$HOME/.vault_password" ]]; then
                ansible-vault encrypt "$vault_file" --vault-password-file "$HOME/.vault_password" --encrypt-vault-id default 2>/dev/null || \
                ansible-vault encrypt "$vault_file" --vault-password-file "$HOME/.vault_password" 2>/dev/null || \
                log_warning "Could not encrypt vault.yml - please encrypt manually"
                log_success "vault.yml created and encrypted"
            else
                log_warning "vault.yml created but not encrypted - .vault_password not found"
            fi
        else
            log_info "vault.yml already exists"
        fi

        log_success "Inventory generated for ${INVENTORY}"
    else
        log_error "Qubinode Navigator directory not found"
        return 1
    fi

    return 0
}

# Test Inventory - From setup.sh
test_inventory() {
    local target_dir="$1"
    log_step "Testing inventory..."

    if [[ -d "$target_dir/qubinode_navigator" ]]; then
        cd "$target_dir/qubinode_navigator" || return 1

        local ansible_navigator_cmd
        if ! command -v ansible-navigator &> /dev/null; then
            ansible_navigator_cmd=$(whereis ansible-navigator | awk '{print $2}')
        else
            ansible_navigator_cmd="ansible-navigator"
        fi

        $ansible_navigator_cmd inventory --list -i "inventories/${INVENTORY}" -m stdout --vault-password-file "$HOME/.vault_password" || {
            log_error "Inventory test failed"
            ask_ai_for_help "inventory_test" "ansible-navigator inventory test failed"
            return 1
        }

        log_success "Inventory test completed successfully"
    else
        log_error "Qubinode Navigator directory not found"
        return 1
    fi

    return 0
}

# Deploy KVM Host - From setup.sh
deploy_kvmhost() {
    log_step "Deploying KVM Host..."

    # Set up SSH agent
    eval $(ssh-agent)
    ssh-add ~/.ssh/id_rsa || {
        log_error "Failed to add SSH key to agent"
        return 1
    }

    cd "$HOME/qubinode_navigator" || {
        log_error "Failed to change to qubinode_navigator directory"
        return 1
    }

    # Install required Ansible collections and roles when running without execution environment
    log_info "Installing required Ansible collections..."
    ansible-galaxy collection install -r "$HOME/qubinode_navigator/ansible-builder/requirements.yml" --force || {
        log_warning "Failed to install some Ansible collections, continuing anyway..."
    }

    log_info "Installing required Ansible roles..."
    ansible-galaxy role install linux-system-roles.cockpit linux-system-roles.network linux-system-roles.firewall --force || {
        log_warning "Failed to install some Ansible roles, continuing anyway..."
    }

    local ansible_navigator_cmd
    if ! command -v ansible-navigator &> /dev/null; then
        ansible_navigator_cmd=$(whereis ansible-navigator | awk '{print $2}')
    else
        ansible_navigator_cmd="ansible-navigator"
    fi

    $ansible_navigator_cmd run "$HOME/qubinode_navigator/ansible-navigator/setup_kvmhost.yml" \
        --vault-password-file "$HOME/.vault_password" \
        --execution-environment false \
        -m stdout || {
        log_error "KVM host deployment failed"
        ask_ai_for_help "kvmhost_deploy" "ansible-navigator run setup_kvmhost.yml failed"
        return 1
    }

    log_success "KVM host deployment completed"
    return 0
}

# Configure Bash Aliases - From setup.sh
configure_bash_aliases() {
    log_step "Configuring bash aliases..."

    if [[ "$(pwd)" != "/root/qubinode_navigator" ]]; then
        cd /root/qubinode_navigator || {
            log_error "Failed to change to /root/qubinode_navigator"
            return 1
        }
    fi

    # Source the function and alias definitions
    source bash-aliases/functions.sh || {
        log_warning "Failed to source functions.sh"
    }

    source bash-aliases/aliases.sh || {
        log_warning "Failed to source aliases.sh"
    }

    # Apply bash aliases
    if [[ -f ~/.bash_aliases ]]; then
        source ~/.bash_aliases
    fi

    # Ensure .bash_aliases is sourced from .bashrc
    if ! grep -qF "source ~/.bash_aliases" ~/.bashrc; then
        echo "source ~/.bash_aliases" >> ~/.bashrc
    fi

    log_success "Bash aliases configuration completed"
    return 0
}

# Setup Kcli Base - From setup.sh
setup_kcli_base() {
    log_step "Setting up kcli base..."

    if [[ "$(pwd)" != "/root/qubinode_navigator" ]]; then
        cd /root/qubinode_navigator || {
            log_error "Failed to change to /root/qubinode_navigator"
            return 1
        }
    fi

    # Source bash aliases to get kcli functions
    source ~/.bash_aliases || {
        log_warning "Failed to source bash aliases"
    }

    # Setup kcli
    qubinode_setup_kcli || {
        log_warning "Failed to setup kcli"
    }

    # Configure kcli images
    kcli_configure_images || {
        log_warning "Failed to configure kcli images"
    }

    log_success "Kcli base setup completed"
    return 0
}

# Create notouch.env for compatibility with existing deployment scripts
create_notouch_env() {
    log_step "Creating notouch.env for compatibility with existing scripts..."

    local notouch_file="$SCRIPT_DIR/notouch.env"

    # Backup existing notouch.env if it exists
    if [[ -f "$notouch_file" ]]; then
        cp "$notouch_file" "${notouch_file}.backup.$(date +%Y%m%d-%H%M%S)"
        log_info "Backed up existing notouch.env"
    fi

    # Create notouch.env based on deployment target and current configuration
    log_info "Creating notouch.env for deployment target: $DEPLOYMENT_TARGET"

    cat > "$notouch_file" << EOF
# Qubinode Navigator Environment Configuration
# Generated by deploy-qubinode.sh on $(date)
# Deployment Target: $DEPLOYMENT_TARGET

export SSH_USER=$SSH_USER
export CICD_PIPELINE=$CICD_PIPELINE
export ENV_USERNAME=$ENV_USERNAME
export KVM_VERSION=$KVM_VERSION
export CICD_ENVIORNMENT=$CICD_ENVIORNMENT
export DOMAIN=$QUBINODE_DOMAIN
export USE_HASHICORP_VAULT=$USE_HASHICORP_VAULT
export USE_HASHICORP_CLOUD=$USE_HASHICORP_CLOUD
export FORWARDER=$FORWARDER
export ACTIVE_BRIDGE=$ACTIVE_BRIDGE
export INTERFACE=$INTERFACE
export USE_ROUTE53=$USE_ROUTE53
export GIT_REPO=$GIT_REPO
export INVENTORY=$INVENTORY
EOF

    # Add SSH_PASSWORD if it's set
    if [[ -n "${SSH_PASSWORD:-}" ]]; then
        echo "export SSH_PASSWORD='$SSH_PASSWORD'" >> "$notouch_file"
    fi

    # Add HashiCorp Cloud configuration if enabled
    if [[ "$USE_HASHICORP_CLOUD" == "true" ]]; then
        cat >> "$notouch_file" << EOF
export HCP_CLIENT_ID=\${HCP_CLIENT_ID:-}
export HCP_CLIENT_SECRET=\${HCP_CLIENT_SECRET:-}
export HCP_ORG_ID=\${HCP_ORG_ID:-}
export HCP_PROJECT_ID=\${HCP_PROJECT_ID:-}
export APP_NAME=\${APP_NAME:-qubinode}
EOF
    fi

    # Add deployment-target specific configuration
    case "$DEPLOYMENT_TARGET" in
        "hetzner")
            cat >> "$notouch_file" << EOF
# Hetzner Cloud specific configuration
export ZONE_NAME=$QUBINODE_DOMAIN
export EMAIL=\${EMAIL:-admin@$QUBINODE_DOMAIN}
export GUID=\${GUID:-hetzner-$(date +%s)}
EOF
            ;;
        "equinix")
            cat >> "$notouch_file" << EOF
# Red Hat Demo System (Equinix) specific configuration
export ZONE_NAME=$QUBINODE_DOMAIN
export EMAIL=\${EMAIL:-admin@$QUBINODE_DOMAIN}
export GUID=\${GUID:-equinix-$(date +%s)}
EOF
            ;;
        "local")
            cat >> "$notouch_file" << EOF
# Local development specific configuration
export ZONE_NAME=$QUBINODE_DOMAIN
export EMAIL=\${EMAIL:-admin@$QUBINODE_DOMAIN}
export GUID=\${GUID:-local-$(date +%s)}
EOF
            ;;
    esac

    # Make notouch.env executable
    chmod +x "$notouch_file"

    log_success "Created notouch.env for compatibility with existing deployment scripts"
    log_info "notouch.env location: $notouch_file"

    return 0
}

# Fix DNS configuration in inventory files - Auto-update CHANGEME values
fix_dns_configuration() {
    log_step "Fixing DNS configuration in inventory files..."

    local inventory_dir="$SCRIPT_DIR/inventories/$INVENTORY"
    local all_vars_file="$inventory_dir/group_vars/all.yml"
    local kvm_host_file="$inventory_dir/group_vars/control/kvm_host.yml"

    # Auto-detect current DNS servers from system
    local current_dns_servers=($(awk '/^nameserver/ {print $2}' /etc/resolv.conf))
    local primary_dns="${current_dns_servers[0]:-8.8.8.8}"
    local secondary_dns="${current_dns_servers[1]:-$FORWARDER}"

    # Use detected forwarder if available, otherwise use secondary DNS
    local dns_forwarder="${FORWARDER:-$secondary_dns}"

    log_info "Auto-detected DNS configuration:"
    log_info "  Primary DNS: $primary_dns"
    log_info "  DNS Forwarder: $dns_forwarder"
    log_info "  Domain: $QUBINODE_DOMAIN"

    # Function to update DNS in a YAML file
    update_dns_in_file() {
        local yaml_file="$1"

        if [[ ! -f "$yaml_file" ]]; then
            log_warning "File not found: $yaml_file"
            return 1
        fi

        # Create backup
        local backup_file="${yaml_file}.backup.$(date +%Y%m%d-%H%M%S)"
        cp "$yaml_file" "$backup_file"
        log_info "Created backup: $backup_file"

        # Update DNS configuration using sed
        sed -i "s/dns_forwarder: \"CHANGEME\"/dns_forwarder: \"$dns_forwarder\"/" "$yaml_file"
        sed -i "s/dns_forwarder: CHANGEME/dns_forwarder: \"$dns_forwarder\"/" "$yaml_file"
        sed -i "s/primary_dns_server: \"8.8.8.8\"/primary_dns_server: \"$primary_dns\"/" "$yaml_file"
        sed -i "s/kvm_host_dns_server: \"8.8.8.8\"/kvm_host_dns_server: \"$primary_dns\"/" "$yaml_file"
        sed -i "s/kvm_host_domain: \"lab.local\"/kvm_host_domain: \"$QUBINODE_DOMAIN\"/" "$yaml_file"

        # Update search domains
        sed -i "s/- \"lab.local\"/- \"$QUBINODE_DOMAIN\"/" "$yaml_file"
        sed -i "s/- lab.local/- \"$QUBINODE_DOMAIN\"/" "$yaml_file"

        log_success "Updated DNS configuration in: $yaml_file"
    }

    # Update main inventory file
    if [[ -f "$all_vars_file" ]]; then
        update_dns_in_file "$all_vars_file"
    else
        log_error "Main inventory file not found: $all_vars_file"
        return 1
    fi

    # Update control host configuration if it exists
    if [[ -f "$kvm_host_file" ]]; then
        update_dns_in_file "$kvm_host_file"
    fi

    # Validate the changes
    if grep -q "CHANGEME" "$all_vars_file"; then
        log_warning "Some CHANGEME values may still exist in inventory files"
        log_info "Remaining CHANGEME entries:"
        grep -n "CHANGEME" "$all_vars_file" || true
    else
        log_success "All CHANGEME values have been replaced with auto-detected DNS configuration"
    fi

    log_success "DNS configuration fix completed"
    return 0
}

verify_deployment() {
    log_step "Verifying deployment..."

    # Check libvirt
    if ! virsh list &> /dev/null; then
        log_error "libvirt verification failed"
        return 1
    fi

    # Check for running VMs (if any were created)
    local vm_count=$(virsh list --all | grep -c "running\|shut off" || echo "0")
    log_info "Virtual machines found: $vm_count"

    # Check AI Assistant if enabled
    if [[ "$QUBINODE_ENABLE_AI_ASSISTANT" == "true" ]] && [[ -n "$AI_ASSISTANT_CONTAINER" ]]; then
        if curl -s http://localhost:${AI_ASSISTANT_PORT}/health &> /dev/null; then
            log_success "AI Assistant is running and accessible"
        else
            log_warning "AI Assistant is not responding"
        fi
    fi

    log_success "Deployment verification completed"
    return 0
}

# =============================================================================
# ERROR HANDLING AND CLEANUP
# =============================================================================

cleanup_on_error() {
    log_error "Deployment failed, performing cleanup..."
    DEPLOYMENT_FAILED=true

    # Stop AI Assistant container if it was started
    if [[ -n "$AI_ASSISTANT_CONTAINER" ]]; then
        log_info "Stopping AI Assistant container..."
        podman stop qubinode-ai-assistant &> /dev/null || true
        podman rm qubinode-ai-assistant &> /dev/null || true
    fi

    # Show deployment log location
    if [[ -f "$DEPLOYMENT_LOG" ]]; then
        log_info "Deployment log available at: $DEPLOYMENT_LOG"
    fi
}

show_completion_summary() {
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                   DEPLOYMENT COMPLETED                       ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}Deployment Summary:${NC}"
    echo -e "  • Cluster Name: ${QUBINODE_CLUSTER_NAME}"
    echo -e "  • Domain: ${QUBINODE_DOMAIN}"
    echo -e "  • Admin User: ${QUBINODE_ADMIN_USER}"
    echo -e "  • OS: ${OS_TYPE} ${OS_VERSION}"
    echo -e "  • Mode: ${QUBINODE_DEPLOYMENT_MODE}"
    echo -e "  • DNS: Auto-configured from system settings"
    echo ""

    if [[ "$QUBINODE_ENABLE_AI_ASSISTANT" == "true" ]] && [[ -n "$AI_ASSISTANT_CONTAINER" ]]; then
        echo -e "${CYAN}AI Assistant Available:${NC}"
        echo -e "  • URL: http://localhost:${AI_ASSISTANT_PORT}"
        echo -e "  • Health: http://localhost:${AI_ASSISTANT_PORT}/health"
        echo -e "  • Ask for help with: deployment issues, troubleshooting, best practices"
        echo ""
    fi

    if [[ "$QUBINODE_ENABLE_AIRFLOW" == "true" ]]; then
        echo -e "${CYAN}Apache Airflow Orchestration:${NC}"
        echo -e "  • Airflow Web UI: http://localhost:${AIRFLOW_PORT}"
        echo -e "  • Username: admin"
        echo -e "  • Password: admin"
        echo -e "  • Documentation: airflow/README.md"
        echo ""

        if systemctl is-active --quiet nginx; then
            echo -e "${CYAN}Nginx Reverse Proxy (Web UIs):${NC}"
            echo -e "  • Status: Running on port 80"
            echo -e "  • Airflow UI (proxied): http://localhost/ → localhost:${AIRFLOW_PORT}"
            if [[ "$QUBINODE_ENABLE_AI_ASSISTANT" == "true" ]]; then
                echo -e "  • AI Assistant API (proxied): http://localhost/ai/ → localhost:${AI_ASSISTANT_PORT}"
            fi
            echo ""
        fi

        echo -e "${CYAN}MCP Servers (Direct Access for LLMs):${NC}"
        echo -e "  • Airflow MCP: http://localhost:8889/sse"
        echo -e "    └─ Tools: DAG management (3), VM operations (5), Status (1)"
        if [[ "$QUBINODE_ENABLE_AI_ASSISTANT" == "true" ]] && [[ -n "$AI_ASSISTANT_CONTAINER" ]]; then
            echo -e "  • AI Assistant MCP: http://localhost:8081"
            echo -e "    └─ Tools: Chat, query documents, RAG integration"
        fi
        echo ""

        echo -e "${CYAN}📖 Architecture & Documentation:${NC}"
        echo -e "  • Main: airflow/README.md"
        echo -e "  • MCP Servers: docs/MCP-SERVER-ARCHITECTURE.md"
        echo -e "  • Tools: airflow/TOOLS-AVAILABLE.md"
        echo ""
    fi

    echo -e "${BLUE}Next Steps:${NC}"
    echo -e "  1. Review deployment log: ${DEPLOYMENT_LOG}"
    echo -e "  2. Check running VMs: virsh list --all"
    echo -e "  3. Access Qubinode Navigator: /opt/qubinode-navigator"

    if [[ "$QUBINODE_ENABLE_AIRFLOW" == "true" ]]; then
        echo -e "  4. Access Airflow UI (port 80 via nginx or port ${AIRFLOW_PORT} direct)"
        echo -e "  5. Connect MCP servers to Claude Desktop for AI-powered automation"
        echo -e "     └─ Airflow MCP: http://localhost:8889/sse"
        if [[ "$QUBINODE_ENABLE_AI_ASSISTANT" == "true" ]]; then
            echo -e "     └─ AI Assistant MCP: http://localhost:8081"
        fi
    fi

    if [[ "$QUBINODE_ENABLE_AI_ASSISTANT" == "true" ]]; then
        echo -e "  • Ask AI Assistant for guidance: http://localhost:${AI_ASSISTANT_PORT}/chat"
    fi

    echo ""
    log_success "Qubinode Navigator deployment completed successfully!"
}

show_failure_summary() {
    echo ""
    echo -e "${RED}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║                   DEPLOYMENT FAILED                          ║${NC}"
    echo -e "${RED}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}Troubleshooting Resources:${NC}"
    echo -e "  • Deployment log: ${DEPLOYMENT_LOG}"

    if [[ "$QUBINODE_ENABLE_AI_ASSISTANT" == "true" ]] && [[ -n "$AI_ASSISTANT_CONTAINER" ]]; then
        echo -e "  • AI Assistant: http://localhost:${AI_ASSISTANT_PORT}"
        echo -e "  • Ask AI for help with the specific error you encountered"
    fi

    echo -e "  • Check system resources: free -h && df -h"
    echo -e "  • Verify network connectivity: ping 8.8.8.8"
    echo -e "  • Check virtualization: grep -E '(vmx|svm)' /proc/cpuinfo"
    echo ""
    echo -e "${YELLOW}Common Solutions:${NC}"
    echo -e "  • Ensure you have sufficient resources (8GB+ RAM, 50GB+ disk)"
    echo -e "  • Enable virtualization in BIOS/UEFI"
    echo -e "  • Check internet connectivity"
    echo -e "  • Run as root user"
    echo ""
}

# =============================================================================
# MAIN EXECUTION
# =============================================================================

main() {
    # Set up error handling
    trap cleanup_on_error ERR

    # Show banner
    show_banner

    # Start deployment log
    log_info "Starting Qubinode Navigator deployment..."
    log_info "Deployment log: $DEPLOYMENT_LOG"
    echo "Qubinode Navigator Deployment Log - $(date)" > "$DEPLOYMENT_LOG"

    # Execute deployment steps following ADR-0001 architecture
    get_rhel_version || exit 1
    check_prerequisites || exit 1
    validate_configuration || exit 1
    detect_deployment_target || exit 1  # New: Detect deployment target based on research
    start_ai_assistant  # Non-blocking, continues even if AI Assistant fails
    deploy_host_ai_services  # ADR-0050: Host AI services for hybrid architecture
    deploy_airflow_services  # Non-blocking, continues even if Airflow fails
    get_qubinode_navigator "$MY_DIR" || exit 1
    fix_dns_configuration || exit 1  # Auto-fix DNS configuration in inventory files
    # configure_environment || exit 1  # Commented out - users should configure .env manually to avoid overwriting
    deploy_qubinode_infrastructure "$MY_DIR" || exit 1
    setup_nginx_reverse_proxy  # Non-blocking, only active if Airflow is enabled
    verify_deployment || exit 1

    # Show completion summary
    show_completion_summary
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Deploy Qubinode Navigator on RHEL-based systems"
        echo ""
        echo "Environment Variables:"
        echo "  QUBINODE_DOMAIN              - Domain name (required)"
        echo "  QUBINODE_ADMIN_USER          - Admin username (required)"
        echo "  QUBINODE_CLUSTER_NAME        - Cluster name (required)"
        echo "  QUBINODE_DEPLOYMENT_MODE     - Deployment mode (default: production)"
        echo "  QUBINODE_ENABLE_AI_ASSISTANT - Enable AI Assistant (default: true)"
        echo "  QUBINODE_ENABLE_AIRFLOW      - Enable Airflow orchestration (default: false)"
        echo "  QUBINODE_ENABLE_AI_SERVICES  - Enable host AI services (default: false, ADR-0050)"
        echo "  QUBINODE_ENABLE_NGINX_PROXY  - Enable nginx reverse proxy (auto-enabled with Airflow)"
        echo "  AI_ASSISTANT_PORT            - AI Assistant port (default: 8080)"
        echo "  AIRFLOW_PORT                 - Airflow webserver port (default: 8888)"
        echo "  EMBEDDING_SERVICE_PORT       - Embedding service port (default: 8891)"
        echo "  LITELLM_PROXY_PORT           - LiteLLM proxy port (default: 4000)"
        echo ""
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --version, -v  Show version information"
        echo ""
        echo "Examples:"
        echo "  # Basic deployment with AI Assistant only"
        echo "  export QUBINODE_DOMAIN=example.com"
        echo "  export QUBINODE_ADMIN_USER=admin"
        echo "  export QUBINODE_CLUSTER_NAME=mycluster"
        echo "  ./deploy-qubinode.sh"
        echo ""
        echo "  # Deployment with Airflow orchestration"
        echo "  export QUBINODE_DOMAIN=example.com"
        echo "  export QUBINODE_ADMIN_USER=admin"
        echo "  export QUBINODE_CLUSTER_NAME=mycluster"
        echo "  export QUBINODE_ENABLE_AIRFLOW=true"
        echo "  ./deploy-qubinode.sh"
        echo ""
        echo "  # Full deployment with Airflow + Host AI Services (ADR-0050)"
        echo "  export QUBINODE_DOMAIN=example.com"
        echo "  export QUBINODE_ADMIN_USER=admin"
        echo "  export QUBINODE_CLUSTER_NAME=mycluster"
        echo "  export QUBINODE_ENABLE_AIRFLOW=true"
        echo "  export QUBINODE_ENABLE_AI_SERVICES=true"
        echo "  ./deploy-qubinode.sh"
        echo ""
        echo "  # Using .env file"
        echo "  cat > .env << EOF"
        echo "  QUBINODE_DOMAIN=example.com"
        echo "  QUBINODE_ADMIN_USER=admin"
        echo "  QUBINODE_CLUSTER_NAME=mycluster"
        echo "  QUBINODE_ENABLE_AIRFLOW=true"
        echo "  EOF"
        echo "  ./deploy-qubinode.sh"
        exit 0
        ;;
    --version|-v)
        echo "Qubinode Navigator One-Shot Deployment v${SCRIPT_VERSION}"
        exit 0
        ;;
    "")
        # No arguments, proceed with deployment
        main
        ;;
    *)
        log_error "Unknown option: $1"
        echo "Use --help for usage information"
        exit 1
        ;;
esac

# Handle script exit
if [[ "$DEPLOYMENT_FAILED" == "true" ]]; then
    show_failure_summary
    exit 1
fi
