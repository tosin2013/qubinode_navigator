#!/bin/bash
"""
Pre-commit Security Check Script

Validates that no sensitive content is being committed to the repository.
Can be used as a git pre-commit hook or run manually before commits.
"""

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "[INFO] $1"
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

# Check for sensitive file patterns
check_sensitive_files() {
    log_info "Checking for sensitive files..."
    
    local sensitive_files=()
    
    # Check staged files for sensitive patterns
    while IFS= read -r -d '' file; do
        if [[ "$file" =~ \.(key|pem|crt|p12|pfx)$ ]] || \
           [[ "$file" =~ (notouch\.env|\.env|vault\.|.*_rsa|.*_rsa\.pub)$ ]] || \
           [[ "$file" =~ (IMPLEMENTATION-PLAN\.md|TODO\.md|NOTES\.md)$ ]]; then
            sensitive_files+=("$file")
        fi
    done < <(git diff --cached --name-only -z 2>/dev/null || true)
    
    if [ ${#sensitive_files[@]} -gt 0 ]; then
        log_error "Sensitive files detected in commit:"
        for file in "${sensitive_files[@]}"; do
            echo "  - $file"
        done
        return 1
    fi
    
    log_success "No sensitive files detected"
    return 0
}

# Check for sensitive content patterns
check_sensitive_content() {
    log_info "Checking for sensitive content patterns..."
    
    local sensitive_patterns=(
        "password\s*[:=]\s*['\"][a-zA-Z0-9!@#$%^&*]{8,}['\"]"
        "secret\s*[:=]\s*['\"][a-zA-Z0-9!@#$%^&*]{16,}['\"]"
        "token\s*[:=]\s*['\"][a-zA-Z0-9_-]{20,}['\"]"
        "api_key\s*[:=]\s*['\"][a-zA-Z0-9_-]{16,}['\"]"
        "-----BEGIN [A-Z ]*PRIVATE KEY-----"
        "ssh-rsa [A-Za-z0-9+/]{100,}"
        "AKIA[0-9A-Z]{16}"  # AWS Access Key
        "ghp_[0-9a-zA-Z]{36}"  # GitHub Personal Access Token
    )
    
    local found_sensitive=false
    
    # Check staged files for sensitive content (excluding test files and test data)
    for pattern in "${sensitive_patterns[@]}"; do
        if git diff --cached | grep -v "test_" | grep -v "/tests/" | grep -v "f\.write" | grep -v "example" | grep -E -i "$pattern" >/dev/null 2>&1; then
            log_warning "Potential sensitive content found matching pattern: $pattern"
            found_sensitive=true
        fi
    done
    
    if [ "$found_sensitive" = true ]; then
        log_error "Sensitive content patterns detected in staged changes"
        log_info "Please review the changes and remove any sensitive information"
        return 1
    fi
    
    log_success "No sensitive content patterns detected"
    return 0
}

# Check for large files that might contain models or data
check_large_files() {
    log_info "Checking for large files..."
    
    local large_files=()
    local max_size=$((10 * 1024 * 1024))  # 10MB
    
    while IFS= read -r -d '' file; do
        if [ -f "$file" ]; then
            local file_size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null || echo 0)
            if [ "$file_size" -gt "$max_size" ]; then
                large_files+=("$file ($(numfmt --to=iec $file_size))")
            fi
        fi
    done < <(git diff --cached --name-only -z 2>/dev/null || true)
    
    if [ ${#large_files[@]} -gt 0 ]; then
        log_warning "Large files detected in commit:"
        for file in "${large_files[@]}"; do
            echo "  - $file"
        done
        log_info "Consider using Git LFS for large files or excluding them"
        
        # Don't fail for large files, just warn
        return 0
    fi
    
    log_success "No large files detected"
    return 0
}

# Validate .gitignore coverage
validate_gitignore() {
    log_info "Validating .gitignore coverage..."
    
    local required_patterns=(
        "*.key"
        "*.pem"
        "*.crt"
        ".env"
        "notouch.env"
        "vault.*"
        "docs/IMPLEMENTATION-PLAN.md"
        "ai-assistant/models/*.gguf"
        "ai-assistant/data/rag-docs/*.json"
    )
    
    local missing_patterns=()
    
    for pattern in "${required_patterns[@]}"; do
        if ! grep -q "^${pattern}$" .gitignore 2>/dev/null; then
            missing_patterns+=("$pattern")
        fi
    done
    
    if [ ${#missing_patterns[@]} -gt 0 ]; then
        log_warning "Missing .gitignore patterns:"
        for pattern in "${missing_patterns[@]}"; do
            echo "  - $pattern"
        done
        log_info "Consider adding these patterns to .gitignore"
    else
        log_success ".gitignore coverage looks good"
    fi
    
    return 0
}

# Main execution
main() {
    log_info "Running pre-commit security checks..."
    
    local exit_code=0
    
    # Run all checks
    check_sensitive_files || exit_code=1
    check_sensitive_content || exit_code=1
    check_large_files || exit_code=1
    validate_gitignore || exit_code=1
    
    if [ $exit_code -eq 0 ]; then
        log_success "All security checks passed!"
        log_info "Safe to commit"
    else
        log_error "Security checks failed!"
        log_info "Please fix the issues above before committing"
    fi
    
    return $exit_code
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [--help]"
        echo
        echo "Runs pre-commit security checks to prevent sensitive data from being committed"
        echo
        echo "Options:"
        echo "  --help, -h    Show this help message"
        echo
        echo "To install as a git pre-commit hook:"
        echo "  ln -sf ../../scripts/pre-commit-security-check.sh .git/hooks/pre-commit"
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac
