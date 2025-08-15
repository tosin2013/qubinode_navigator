#!/bin/bash

# =============================================================================
# Jekyll Local Development Server - The "Documentation Lab Technician"
# =============================================================================
#
# 🎯 PURPOSE FOR LLMs:
# This script provides a containerized Jekyll development environment for local
# documentation development and testing. It implements container-first development
# practices using Podman to ensure consistent, isolated development environments.
#
# 🧠 ARCHITECTURE OVERVIEW FOR AI ASSISTANTS:
# This script implements containerized Jekyll development:
# 1. [PHASE 1]: Environment Validation - Checks Podman installation and docs directory
# 2. [PHASE 2]: Container Management - Stops existing containers and cleans up
# 3. [PHASE 3]: Image Building - Creates Jekyll container image with dependencies
# 4. [PHASE 4]: Container Deployment - Runs Jekyll server with live reload
# 5. [PHASE 5]: Service Management - Provides start/stop/restart/logs commands
# 6. [PHASE 6]: Development Support - Opens browser and provides status information
#
# 🔧 HOW IT CONNECTS TO QUBINODE NAVIGATOR:
# - [Documentation Development]: Enables local development of project documentation
# - [Container-First Approach]: Implements ADR-0001 container-first execution model
# - [Development Workflow]: Supports documentation contributors and maintainers
# - [CI/CD Integration]: Can be used in automated documentation testing
# - [Quality Assurance]: Provides local testing before documentation deployment
#
# 📊 KEY DESIGN PRINCIPLES FOR LLMs TO UNDERSTAND:
# - [Container-Native]: Uses Podman containers for isolated development environment
# - [Live Reload]: Provides real-time preview of documentation changes
# - [Port Management]: Handles Jekyll and LiveReload port configuration
# - [User-Friendly]: Provides simple commands for common development tasks
# - [Cross-Platform]: Works on any system with Podman support
#
# 💡 WHEN TO MODIFY THIS SCRIPT (for future LLMs):
# - [Jekyll Updates]: Update Jekyll version or Ruby version in container
# - [Port Configuration]: Modify ports if conflicts arise with other services
# - [Container Features]: Add new development tools or features to container
# - [Platform Support]: Add support for Docker or other container runtimes
# - [Development Workflow]: Enhance development experience with new features
#
# 🚨 IMPORTANT FOR LLMs: This script creates and manages containers for development
# purposes. It requires Podman and modifies container state. It's designed for
# development environments and should not be used in production.

set -euo pipefail

# 🔧 CONFIGURATION CONSTANTS FOR LLMs:
CONTAINER_NAME="qubinode-jekyll-dev"  # Container name for Jekyll development server
JEKYLL_PORT="4000"                    # Standard Jekyll development server port
LIVERELOAD_PORT="35729"               # LiveReload port for automatic browser refresh
DOCS_DIR="$(pwd)/docs"                # Documentation source directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"  # Script location
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"  # Project root directory

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

# Container Runtime Validator - The "Environment Checker"
check_podman() {
# 🎯 FOR LLMs: This function validates that Podman container runtime is available
# for Jekyll container deployment, providing installation guidance if missing.
# 🔄 WORKFLOW:
# 1. Checks if podman command is available in PATH
# 2. Provides OS-specific installation instructions if missing
# 3. Reports Podman version if available
# 📊 INPUTS/OUTPUTS:
# - INPUT: System PATH and available commands
# - OUTPUT: Podman version confirmation or installation instructions
# ⚠️  SIDE EFFECTS: Exits script if Podman is not available

    if ! command -v podman &> /dev/null; then
        log_error "Podman is not installed. Please install podman first."
        log_info "On RHEL/CentOS: sudo dnf install podman"
        log_info "On Ubuntu: sudo apt install podman"
        exit 1
    fi
    log_success "Podman is available: $(podman --version)"
}

# Documentation Directory Validator - The "Content Locator"
check_docs_dir() {
# 🎯 FOR LLMs: This function validates that the documentation directory exists
# and is accessible for Jekyll processing.
# 🔄 WORKFLOW:
# 1. Checks if docs directory exists at expected location
# 2. Provides guidance on correct script execution location
# 3. Confirms directory availability for Jekyll processing
# 📊 INPUTS/OUTPUTS:
# - INPUT: DOCS_DIR path and filesystem state
# - OUTPUT: Directory confirmation or error guidance
# ⚠️  SIDE EFFECTS: Exits script if docs directory is not found

    if [[ ! -d "$DOCS_DIR" ]]; then
        log_error "Docs directory not found: $DOCS_DIR"
        log_info "Please run this script from the project root directory"
        exit 1
    fi
    log_success "Docs directory found: $DOCS_DIR"
}

# Function to stop existing container
stop_existing_container() {
    if podman ps -a --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
        log_info "Stopping existing container: $CONTAINER_NAME"
        podman stop "$CONTAINER_NAME" || true
        podman rm "$CONTAINER_NAME" || true
        log_success "Existing container removed"
    fi
}

# Function to check if ports are available
check_ports() {
    local ports=("$JEKYLL_PORT" "$LIVERELOAD_PORT")
    for port in "${ports[@]}"; do
        if ss -tuln | grep -q ":${port} "; then
            log_warning "Port $port is already in use"
            log_info "You may need to stop other services or change the port"
        else
            log_success "Port $port is available"
        fi
    done
}

# Function to create Dockerfile for Jekyll
create_dockerfile() {
    local dockerfile_path="$PROJECT_ROOT/Dockerfile.jekyll"
    
    cat > "$dockerfile_path" << 'EOF'
FROM docker.io/library/ruby:3.1.4-alpine

# Install dependencies for native gem compilation
RUN apk add --no-cache \
    build-base \
    linux-headers \
    git \
    nodejs \
    npm \
    tzdata

# Set working directory
WORKDIR /site

# Copy Gemfile and Gemfile.lock
COPY docs/Gemfile* ./

# Install bundler
RUN gem install bundler

# Expose ports
EXPOSE 4000 35729

# Create entrypoint script
RUN echo '#!/bin/sh' > /entrypoint.sh && \
    echo 'cd /site' >> /entrypoint.sh && \
    echo 'bundle config set --local deployment false' >> /entrypoint.sh && \
    echo 'bundle install' >> /entrypoint.sh && \
    echo 'bundle exec jekyll serve --host 0.0.0.0 --port 4000 --livereload --livereload-port 35729 --force_polling' >> /entrypoint.sh && \
    chmod +x /entrypoint.sh

# Default command
CMD ["/entrypoint.sh"]
EOF

    log_success "Dockerfile created: $dockerfile_path"
}

# Function to build Jekyll container image
build_image() {
    local image_name="qubinode-jekyll:latest"
    
    log_info "Building Jekyll container image..."
    
    if ! podman build -t "$image_name" -f "$PROJECT_ROOT/Dockerfile.jekyll" "$PROJECT_ROOT"; then
        log_error "Failed to build Jekyll container image"
        exit 1
    fi
    
    log_success "Jekyll container image built: $image_name"
}

# Function to run Jekyll container
run_jekyll_container() {
    local image_name="qubinode-jekyll:latest"
    
    log_info "Starting Jekyll development server in container..."
    log_info "Container name: $CONTAINER_NAME"
    log_info "Jekyll URL: http://localhost:$JEKYLL_PORT"
    log_info "LiveReload: http://localhost:$LIVERELOAD_PORT"
    
    # Run container with volume mount and port forwarding
    podman run -d \
        --name "$CONTAINER_NAME" \
        --rm \
        -p "${JEKYLL_PORT}:4000" \
        -p "${LIVERELOAD_PORT}:35729" \
        -v "$DOCS_DIR:/site:Z" \
        "$image_name"
    
    if [[ $? -eq 0 ]]; then
        log_success "Jekyll container started successfully!"
        log_info "Access your site at: http://localhost:$JEKYLL_PORT"
        log_info "LiveReload is available on port: $LIVERELOAD_PORT"
    else
        log_error "Failed to start Jekyll container"
        exit 1
    fi
}

# Function to show container logs
show_logs() {
    log_info "Showing Jekyll container logs (Ctrl+C to exit)..."
    podman logs -f "$CONTAINER_NAME"
}

# Function to stop Jekyll container
stop_jekyll() {
    if podman ps --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
        log_info "Stopping Jekyll container..."
        podman stop "$CONTAINER_NAME"
        log_success "Jekyll container stopped"
    else
        log_warning "Jekyll container is not running"
    fi
}

# Function to show container status
show_status() {
    log_info "Jekyll container status:"
    if podman ps --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
        podman ps --filter "name=$CONTAINER_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        log_success "Jekyll is running at: http://localhost:$JEKYLL_PORT"
    else
        log_warning "Jekyll container is not running"
    fi
}

# Function to open browser
open_browser() {
    local url="http://localhost:$JEKYLL_PORT"
    log_info "Opening browser to: $url"
    
    if command -v xdg-open &> /dev/null; then
        xdg-open "$url"
    elif command -v open &> /dev/null; then
        open "$url"
    else
        log_warning "Could not open browser automatically"
        log_info "Please open: $url"
    fi
}

# Function to show help
show_help() {
    cat << EOF
Jekyll Local Development Server with Podman

Usage: $0 [COMMAND]

Commands:
    start       Start Jekyll development server (default)
    stop        Stop Jekyll development server
    restart     Restart Jekyll development server
    logs        Show Jekyll container logs
    status      Show container status
    build       Build Jekyll container image
    open        Open browser to Jekyll site
    clean       Stop container and remove image
    help        Show this help message

Examples:
    $0              # Start Jekyll server
    $0 start        # Start Jekyll server
    $0 logs         # Show logs
    $0 stop         # Stop server
    $0 restart      # Restart server

The Jekyll site will be available at: http://localhost:$JEKYLL_PORT
LiveReload will be available at: http://localhost:$LIVERELOAD_PORT
EOF
}

# Function to clean up
cleanup() {
    log_info "Cleaning up Jekyll container and image..."
    podman stop "$CONTAINER_NAME" 2>/dev/null || true
    podman rm "$CONTAINER_NAME" 2>/dev/null || true
    podman rmi "qubinode-jekyll:latest" 2>/dev/null || true
    rm -f "$PROJECT_ROOT/Dockerfile.jekyll"
    log_success "Cleanup completed"
}

# Main function
main() {
    local command="${1:-start}"
    
    case "$command" in
        "start")
            log_info "Starting Jekyll development server..."
            check_podman
            check_docs_dir
            check_ports
            stop_existing_container
            create_dockerfile
            build_image
            run_jekyll_container
            sleep 3
            show_status
            log_info "Use '$0 logs' to see real-time logs"
            log_info "Use '$0 stop' to stop the server"
            ;;
        "stop")
            stop_jekyll
            ;;
        "restart")
            log_info "Restarting Jekyll development server..."
            stop_jekyll
            sleep 2
            main start
            ;;
        "logs")
            show_logs
            ;;
        "status")
            show_status
            ;;
        "build")
            check_podman
            check_docs_dir
            create_dockerfile
            build_image
            ;;
        "open")
            open_browser
            ;;
        "clean")
            cleanup
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            log_error "Unknown command: $command"
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
