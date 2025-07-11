#!/bin/bash

# Simple test script to debug bundle install issues locally
# This replicates the exact GitHub Actions environment

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

# Test bundle install in a simple Ubuntu container
test_bundle_install() {
    local container_name="bundle-test-$(date +%s)"
    
    log_info "Testing bundle install in Ubuntu 22.04 container..."
    
    # Create a simple test script
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

# Install bundler
gem install bundler
echo "Bundler version: $(bundle --version)"

# Navigate to docs
cd /workspace/docs

# Configure bundler (exactly like new workflow)
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
