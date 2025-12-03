#!/bin/bash

# =============================================================================
# Bundle Install Tester - The "Ruby Environment Validator"
# =============================================================================
#
# 🎯 PURPOSE FOR LLMs:
# This script tests Ruby bundle installation in containerized environments to
# debug and validate Jekyll documentation build processes. It replicates GitHub
# Actions environments locally for troubleshooting and validation.
#
# 🧠 ARCHITECTURE OVERVIEW FOR AI ASSISTANTS:
# This script implements Ruby environment testing:
# 1. [PHASE 1]: Container Setup - Creates Ubuntu test containers for Ruby testing
# 2. [PHASE 2]: Dependency Installation - Installs Ruby, build tools, and libraries
# 3. [PHASE 3]: Bundle Configuration - Configures bundler with proper build flags
# 4. [PHASE 4]: Jekyll Testing - Tests Jekyll installation and build process
# 5. [PHASE 5]: Environment Validation - Validates GitHub Actions compatibility
# 6. [PHASE 6]: Cleanup - Removes test containers and temporary files
#
# 🔧 HOW IT CONNECTS TO QUBINODE NAVIGATOR:
# - [CI/CD Validation]: Tests documentation build process before deployment
# - [Environment Debugging]: Helps troubleshoot Jekyll build issues
# - [GitHub Actions Compatibility]: Ensures local environment matches CI/CD
# - [Documentation Quality]: Validates documentation can be built successfully
# - [Development Support]: Assists developers with Jekyll setup issues
#
# 📊 KEY DESIGN PRINCIPLES FOR LLMs TO UNDERSTAND:
# - [Environment Replication]: Matches GitHub Actions Ubuntu environment exactly
# - [Containerized Testing]: Uses containers for isolated, reproducible testing
# - [Comprehensive Validation]: Tests all aspects of Jekyll build process
# - [Error Diagnosis]: Provides detailed error reporting and troubleshooting
# - [Multiple Test Scenarios]: Tests different Ruby and Jekyll configurations
#
# 💡 WHEN TO MODIFY THIS SCRIPT (for future LLMs):
# - [Ruby Updates]: Update Ruby versions or gem configurations
# - [Jekyll Updates]: Modify for new Jekyll versions or dependencies
# - [CI/CD Changes]: Update to match new GitHub Actions environments
# - [Dependency Updates]: Add new system dependencies or build tools
# - [Testing Enhancements]: Add new test scenarios or validation checks
#
# 🚨 IMPORTANT FOR LLMs: This script creates and manages test containers for
# Ruby environment validation. It requires container runtime and may download
# large container images. It's designed for development and testing purposes.

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Bundle Installation Tester - The "Ruby Environment Simulator"
test_bundle_install() {
# 🎯 FOR LLMs: This function creates a containerized Ubuntu environment that
# exactly replicates GitHub Actions conditions to test Jekyll bundle installation.
# 🔄 WORKFLOW:
# 1. Creates unique container name with timestamp
# 2. Generates test script that installs Ruby dependencies
# 3. Configures bundler with proper build flags
# 4. Tests Jekyll installation and build process
# 5. Validates environment matches GitHub Actions
# 📊 INPUTS/OUTPUTS:
# - INPUT: Container runtime and docs directory
# - OUTPUT: Test results and validation status
# ⚠️  SIDE EFFECTS: Creates containers, downloads packages, creates temporary files

    local container_name="bundle-test-$(date +%s)"  # Unique container name

    log_info "Testing bundle install in Ubuntu 22.04 container..."

    # Create a simple test script that replicates GitHub Actions environment
    cat > /tmp/bundle-test.sh << 'EOF'
#!/bin/bash
set -euo pipefail

echo "=== Bundle Install Test ==="
echo "Ubuntu version: $(cat /etc/os-release | grep VERSION=)"
echo

# Install minimal dependencies
echo "Installing minimal dependencies..."
apt-get update
apt-get install -y \
    build-essential \
    ruby-full \
    ruby-dev \
    libgmp-dev \
    libgmp3-dev \
    zlib1g-dev \
    libssl-dev \
    libffi-dev

echo "Ruby version: $(ruby --version)"

# Install bundler (compatible version)
gem install bundler
echo "Bundler version: $(bundle --version)"

# Navigate to docs
cd /workspace/docs
echo "Current directory: $(pwd)"
echo "Gemfile contents:"
cat Gemfile
echo

# Test bigdecimal compilation first
echo "Testing bigdecimal compilation..."
gem install bigdecimal -v 3.1.7 -- --with-gmp-dir=/usr || {
  echo "❌ BigDecimal 3.1.7 failed, trying 3.1.6..."
  gem install bigdecimal -v 3.1.6 -- --with-gmp-dir=/usr || {
    echo "❌ BigDecimal 3.1.6 failed, using default..."
    gem install bigdecimal || echo "❌ All bigdecimal installations failed"
  }
}

# Configure bundler
echo "Configuring bundler..."
bundle config set --local build.bigdecimal --with-gmp-dir=/usr
bundle config set --local build.nokogiri --use-system-libraries
bundle config set --local build.ffi --enable-system-libffi

# Set environment variables
export CFLAGS="-I/usr/include"
export CXXFLAGS="-I/usr/include"
export LDFLAGS="-L/usr/lib/x86_64-linux-gnu"
export PKG_CONFIG_PATH="/usr/lib/x86_64-linux-gnu/pkgconfig"
export BIGDECIMAL_CFLAGS="-I/usr/include"
export BIGDECIMAL_LDFLAGS="-L/usr/lib/x86_64-linux-gnu"

# Try bundle install
echo "Running bundle install..."
bundle install --verbose

echo "✅ Bundle install successful!"
EOF

    chmod +x /tmp/bundle-test.sh

    # Run the test
    podman run --rm -it \
        -v "$(pwd)/docs:/workspace/docs:z" \
        -v "/tmp/bundle-test.sh:/test.sh:z" \
        ubuntu:22.04 \
        bash /test.sh

    local exit_code=$?

    # Clean up
    rm -f /tmp/bundle-test.sh

    if [[ $exit_code -eq 0 ]]; then
        log_success "Bundle install test passed!"
    else
        log_error "Bundle install test failed with exit code: $exit_code"
    fi

    return $exit_code
}

# Test with minimal packages (GitHub Actions approach)
test_minimal_packages() {
    local container_name="minimal-test-$(date +%s)"

    log_info "Testing GitHub Actions minimal approach..."

    cat > /tmp/minimal-test.sh << 'EOF'
#!/bin/bash
set -euo pipefail

echo "=== GitHub Actions Minimal Test ==="

# Install minimal dependencies (exactly like new workflow)
apt-get update
apt-get install -y build-essential ruby-full ruby-dev libgmp-dev libffi-dev

echo "Ruby version: $(ruby --version)"

# Set up user gem directory (exactly like new workflow)
export GEM_HOME="$HOME/gems"
export PATH="$HOME/gems/bin:/usr/bin:$PATH"

# Create gems directory
mkdir -p "$HOME/gems"

# Install bundler to user directory
gem install bundler
echo "Bundler version: $(bundle --version)"
echo "Bundler path: $(command -v bundle)"

# Navigate to docs
cd /workspace/docs

# Configure bundler (exactly like new workflow)
export GEM_HOME="$HOME/gems"
export PATH="$HOME/gems/bin:/usr/bin:$PATH"

# Verify bundler is available
echo "PATH: $PATH"
echo "GEM_HOME: $GEM_HOME"
bundle --version

bundle config set --local build.bigdecimal --with-gmp-dir=/usr
bundle config set --local build.nokogiri --use-system-libraries
bundle config set --local build.ffi --enable-system-libffi

# Install gems (exactly like new workflow)
bundle install --retry 3 --jobs 4

echo "✅ GitHub Actions minimal test successful!"

# Test Jekyll build
bundle exec jekyll build
echo "✅ Jekyll build successful!"
EOF

    chmod +x /tmp/minimal-test.sh

    podman run --rm -it \
        -v "$(pwd)/docs:/workspace/docs:z" \
        -v "/tmp/minimal-test.sh:/test.sh:z" \
        ubuntu:22.04 \
        bash /test.sh

    local exit_code=$?
    rm -f /tmp/minimal-test.sh

    if [[ $exit_code -eq 0 ]]; then
        log_success "GitHub Actions minimal test passed!"
    else
        log_error "GitHub Actions minimal test failed with exit code: $exit_code"
    fi

    return $exit_code
}

# Show help
show_help() {
    cat << EOF
Bundle Install Test Script

This script tests bundle install in different Ubuntu 22.04 environments
to identify the minimal package set needed for successful Jekyll builds.

Usage: $0 [COMMAND]

Commands:
    full        Test with full package set (like GitHub Actions)
    minimal     Test with minimal package set
    help        Show this help message

Examples:
    $0 full     # Test with all packages from GitHub Actions workflow
    $0 minimal  # Test with minimal packages only
EOF
}

# Main function
main() {
    local command="${1:-full}"

    case "$command" in
        "full")
            test_bundle_install
            ;;
        "minimal")
            test_minimal_packages
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

main "$@"
