#!/bin/bash
# =============================================================================
# Qubinode Airflow Deployment Script
# Integrates with AI Assistant and deploys on same Podman network
# =============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AI_ASSISTANT_CONTAINER="qubinode-ai-assistant"
AIRFLOW_NETWORK="airflow_default"
ENABLE_AIRFLOW="${ENABLE_AIRFLOW:-true}"

deploy_airflow() {
    if [[ "$ENABLE_AIRFLOW" != "true" ]]; then
        log_info "Airflow deployment disabled"
        return 0
    fi

    log_info "🚀 Starting Airflow deployment..."
    
    # Check prerequisites
    if ! command -v podman &> /dev/null; then
        log_error "Podman is required but not installed"
        return 1
    fi
    
    if ! command -v podman-compose &> /dev/null; then
        log_info "Installing podman-compose..."
        pip3 install podman-compose || {
            log_error "Failed to install podman-compose"
            return 1
        }
    fi
    
    # Change to airflow directory
    cd "$SCRIPT_DIR" || return 1
    
    # Enable Airflow in configuration
    log_info "Enabling Airflow in configuration..."
    if [[ -f config/airflow.env ]]; then
        sed -i 's/ENABLE_AIRFLOW=false/ENABLE_AIRFLOW=true/' config/airflow.env
    fi
    
    # Build custom image with kcli + virsh
    log_info "Building custom Airflow image with kcli and virsh..."
    podman build -t qubinode-airflow:2.10.4-python3.12 -f Dockerfile . || {
        log_error "Failed to build Airflow image"
        return 1
    }
    log_success "Custom Airflow image built"
    
    # Start Airflow services
    log_info "Starting Airflow services..."
    
    # Check if MCP server should be enabled
    local mcp_profile=""
    if [[ "${AIRFLOW_MCP_ENABLED:-false}" == "true" ]]; then
        log_info "MCP server enabled, starting with --profile mcp"
        mcp_profile="--profile mcp"
    fi
    
    podman-compose ${mcp_profile} up -d || {
        log_error "Failed to start Airflow services"
        return 1
    }
    
    # Wait for services to be healthy
    log_info "Waiting for Airflow to be ready..."
    for i in {1..60}; do
        if curl -s http://localhost:8888/health &> /dev/null; then
            log_success "Airflow webserver is ready!"
            break
        fi
        sleep 2
    done
    
    # Connect AI Assistant to Airflow network if it's running
    if podman ps --format "{{.Names}}" | grep -q "^${AI_ASSISTANT_CONTAINER}$"; then
        log_info "Connecting AI Assistant to Airflow network..."
        podman network connect ${AIRFLOW_NETWORK} ${AI_ASSISTANT_CONTAINER} 2>/dev/null || {
            log_warning "AI Assistant already connected to Airflow network"
        }
        log_success "AI Assistant connected to Airflow network"
    else
        log_warning "AI Assistant not running - chat plugin will not work"
        log_info "Restart AI Assistant after Airflow is running to enable chat"
    fi
    
    # Verify DAGs are loaded
    log_info "Verifying DAGs..."
    sleep 10
    local dag_count=$(podman exec airflow_airflow-scheduler_1 airflow dags list 2>/dev/null | grep -c "example" || echo "0")
    log_success "Found $dag_count example DAGs"
    
    # Test kcli and virsh connectivity
    log_info "Testing kcli connectivity..."
    if podman exec airflow_airflow-scheduler_1 kcli list vm &> /dev/null; then
        log_success "✅ kcli is working"
    else
        log_warning "⚠️  kcli may not be working properly"
    fi
    
    log_info "Testing virsh connectivity..."
    if podman exec airflow_airflow-scheduler_1 virsh list --all &> /dev/null; then
        log_success "✅ virsh is working"
    else
        log_warning "⚠️  virsh may not be working properly"
    fi
    
    # Display access information
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║              Airflow Deployment Complete!                   ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${GREEN}✅ Airflow UI:${NC}          http://localhost:8888"
    echo -e "${GREEN}   Username:${NC}           admin"
    echo -e "${GREEN}   Password:${NC}           admin"
    echo ""
    echo -e "${GREEN}✅ AI Assistant:${NC}        http://localhost:8080"
    echo -e "${GREEN}✅ AI Chat in Airflow:${NC}  http://localhost:8888/ai-assistant"
    echo ""
    echo -e "${CYAN}📚 Available Tools:${NC}"
    echo -e "   • kcli - VM provisioning"
    echo -e "   • virsh - Libvirt management"
    echo -e "   • Airflow DAGs - Workflow orchestration"
    echo ""
    echo -e "${CYAN}📖 Example DAGs:${NC}"
    echo -e "   • example_kcli_vm_provisioning"
    echo -e "   • example_kcli_virsh_combined"
    echo ""
    echo -e "${CYAN}🔗 Documentation:${NC}"
    echo -e "   • airflow/README.md"
    echo -e "   • airflow/TOOLS-AVAILABLE.md"
    echo ""
    
    return 0
}

stop_airflow() {
    log_info "Stopping Airflow services..."
    cd "$SCRIPT_DIR" || return 1
    podman-compose down || {
        log_error "Failed to stop Airflow services"
        return 1
    }
    log_success "Airflow services stopped"
}

status_airflow() {
    log_info "Checking Airflow status..."
    
    echo ""
    echo -e "${CYAN}Container Status:${NC}"
    podman ps --filter "label=io.podman.compose.project=airflow" \
        --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    
    echo ""
    echo -e "${CYAN}Health Checks:${NC}"
    
    # Check Airflow webserver
    if curl -s http://localhost:8888/health &> /dev/null; then
        echo -e "  ${GREEN}✅ Airflow Webserver${NC} - http://localhost:8888"
    else
        echo -e "  ${RED}❌ Airflow Webserver${NC} - Not responding"
    fi
    
    # Check AI Assistant
    if curl -s http://localhost:8080/health &> /dev/null; then
        echo -e "  ${GREEN}✅ AI Assistant${NC} - http://localhost:8080"
    else
        echo -e "  ${YELLOW}⚠️  AI Assistant${NC} - Not running"
    fi
    
    # Check network connectivity
    if podman network inspect ${AIRFLOW_NETWORK} &> /dev/null; then
        local containers=$(podman network inspect ${AIRFLOW_NETWORK} --format '{{range .Containers}}{{.Name}} {{end}}')
        echo ""
        echo -e "${CYAN}Network ${AIRFLOW_NETWORK}:${NC}"
        echo -e "  Containers: $containers"
    fi
    
    echo ""
}

# Main script logic
case "${1:-deploy}" in
    deploy)
        deploy_airflow
        ;;
    stop)
        stop_airflow
        ;;
    status)
        status_airflow
        ;;
    restart)
        stop_airflow
        sleep 2
        deploy_airflow
        ;;
    *)
        echo "Usage: $0 {deploy|stop|status|restart}"
        exit 1
        ;;
esac
