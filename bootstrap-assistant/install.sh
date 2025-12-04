#!/bin/bash
# Qubinode Navigator Bootstrap Assistant Installer
# Usage: curl -sSL https://get.qubinode.io | bash

set -e

BOOTSTRAP_VERSION="v1.0.0"
INSTALL_DIR="/opt/qubinode-bootstrap"
GITHUB_REPO="Qubinode/qubinode_navigator"
BOOTSTRAP_URL="https://raw.githubusercontent.com/${GITHUB_REPO}/main/bootstrap-assistant"

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

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_error "This script should not be run as root"
        log_info "Please run as a regular user with sudo privileges"
        exit 1
    fi
}

# Check system requirements
check_requirements() {
    log_info "Checking system requirements..."

    # Check Python 3.8+
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is required but not installed"
        exit 1
    fi

    python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
        log_error "Python 3.8+ is required (found: $python_version)"
        exit 1
    fi

    log_success "Python $python_version detected"

    # Check required tools
    local required_tools=("curl" "git" "sudo")
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            log_error "$tool is required but not installed"
            exit 1
        fi
    done

    log_success "All required tools found"
}

# Install Python dependencies
install_dependencies() {
    log_info "Installing Python dependencies..."

    # Create virtual environment
    python3 -m venv "$INSTALL_DIR/venv"
    source "$INSTALL_DIR/venv/bin/activate"

    # Upgrade pip
    pip install --upgrade pip

    # Install required packages
    pip install psutil requests aiofiles

    log_success "Dependencies installed"
}

# Download bootstrap assistant
download_bootstrap() {
    log_info "Downloading Qubinode Navigator Bootstrap Assistant..."

    # Create installation directory
    sudo mkdir -p "$INSTALL_DIR"
    sudo chown "$USER:$USER" "$INSTALL_DIR"

    # Download bootstrap script
    curl -sSL "${BOOTSTRAP_URL}/bootstrap.py" -o "$INSTALL_DIR/bootstrap.py"
    chmod +x "$INSTALL_DIR/bootstrap.py"

    # Download requirements if available
    if curl -sSL "${BOOTSTRAP_URL}/requirements.txt" -o "$INSTALL_DIR/requirements.txt" 2>/dev/null; then
        log_info "Installing additional requirements..."
        source "$INSTALL_DIR/venv/bin/activate"
        pip install -r "$INSTALL_DIR/requirements.txt"
    fi

    log_success "Bootstrap assistant downloaded"
}

# Create launcher script
create_launcher() {
    log_info "Creating launcher script..."

    cat > "$INSTALL_DIR/qubinode-bootstrap" << 'EOF'
#!/bin/bash
# Qubinode Navigator Bootstrap Assistant Launcher

INSTALL_DIR="/opt/qubinode-bootstrap"

# Activate virtual environment
source "$INSTALL_DIR/venv/bin/activate"

# Run bootstrap assistant
python3 "$INSTALL_DIR/bootstrap.py" "$@"
EOF

    chmod +x "$INSTALL_DIR/qubinode-bootstrap"

    # Create system-wide symlink
    sudo ln -sf "$INSTALL_DIR/qubinode-bootstrap" /usr/local/bin/qubinode-bootstrap

    log_success "Launcher created at /usr/local/bin/qubinode-bootstrap"
}

# Display completion message
show_completion() {
    echo ""
    echo "🎉 Qubinode Navigator Bootstrap Assistant installed successfully!"
    echo ""
    echo "📋 Next steps:"
    echo "  1. Run: qubinode-bootstrap"
    echo "  2. Follow the AI-guided setup process"
    echo "  3. Enjoy your automated infrastructure deployment!"
    echo ""
    echo "📚 Documentation: https://docs.qubinode.io"
    echo "🐛 Issues: https://github.com/${GITHUB_REPO}/issues"
    echo ""
    echo "💡 Pro tip: The AI assistant will analyze your system and provide"
    echo "   personalized recommendations for optimal performance."
    echo ""
}

# Main installation function
main() {
    echo "🚀 Qubinode Navigator Bootstrap Assistant Installer"
    echo "=================================================="
    echo ""

    check_root
    check_requirements
    download_bootstrap
    install_dependencies
    create_launcher
    show_completion
}

# Handle script interruption
trap 'log_error "Installation interrupted"; exit 1' INT TERM

# Run main function
main "$@"
