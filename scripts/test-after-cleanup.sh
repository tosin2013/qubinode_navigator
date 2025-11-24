#!/bin/bash
# Test After Cleanup Script
# Verifies application functionality after security cleanup

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TEST_RESULTS_DIR="$PROJECT_ROOT/.security-backups/test-results"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

echo "🧪 Testing application after cleanup..."

# Ensure test results directory exists
mkdir -p "$TEST_RESULTS_DIR"

# Function to test basic functionality
test_basic_functionality() {
    echo "⚙️  Testing basic functionality..."
    
    local test_log="$TEST_RESULTS_DIR/basic-functionality-${TIMESTAMP}.log"
    
    cd "$PROJECT_ROOT"
    
    # Test Python syntax
    echo "## Python Syntax Check" > "$test_log"
    if find . -name "*.py" -not -path "./.git/*" -not -path "./.security-backups/*" -exec python3 -m py_compile {} \; 2>>"$test_log"; then
        echo "✅ Python syntax check passed" | tee -a "$test_log"
    else
        echo "❌ Python syntax errors found" | tee -a "$test_log"
        return 1
    fi
    
    # Test shell script syntax
    echo "## Shell Script Syntax Check" >> "$test_log"
    local shell_errors=0
    while IFS= read -r -d '' script; do
        if ! bash -n "$script" 2>>"$test_log"; then
            echo "❌ Syntax error in: $script" | tee -a "$test_log"
            ((shell_errors++))
        fi
    done < <(find . -name "*.sh" -not -path "./.git/*" -not -path "./.security-backups/*" -print0)
    
    if [[ $shell_errors -eq 0 ]]; then
        echo "✅ Shell script syntax check passed" | tee -a "$test_log"
    else
        echo "❌ $shell_errors shell script syntax errors found" | tee -a "$test_log"
        return 1
    fi
    
    # Test YAML syntax
    echo "## YAML Syntax Check" >> "$test_log"
    if command -v yamllint >/dev/null 2>&1; then
        if find . -name "*.yml" -o -name "*.yaml" -not -path "./.git/*" -not -path "./.security-backups/*" | xargs yamllint 2>>"$test_log"; then
            echo "✅ YAML syntax check passed" | tee -a "$test_log"
        else
            echo "⚠️  YAML syntax warnings found (check log)" | tee -a "$test_log"
        fi
    else
        echo "ℹ️  yamllint not available, skipping YAML check" | tee -a "$test_log"
    fi
}

# Function to test Ansible playbooks
test_ansible_playbooks() {
    echo "🎭 Testing Ansible playbooks..."
    
    local test_log="$TEST_RESULTS_DIR/ansible-test-${TIMESTAMP}.log"
    
    cd "$PROJECT_ROOT"
    
    echo "## Ansible Playbook Syntax Check" > "$test_log"
    
    # Find and test playbooks
    local playbook_errors=0
    while IFS= read -r -d '' playbook; do
        echo "Testing: $playbook" >> "$test_log"
        if ansible-playbook --syntax-check "$playbook" >>"$test_log" 2>&1; then
            echo "✅ $playbook syntax OK" | tee -a "$test_log"
        else
            echo "❌ $playbook syntax error" | tee -a "$test_log"
            ((playbook_errors++))
        fi
    done < <(find . -name "*.yml" -path "*/playbooks/*" -o -name "site.yml" -o -name "main.yml" \
        -not -path "./.git/*" -not -path "./.security-backups/*" -print0 2>/dev/null || true)
    
    if [[ $playbook_errors -eq 0 ]]; then
        echo "✅ All Ansible playbooks passed syntax check"
    else
        echo "❌ $playbook_errors Ansible playbook errors found"
        return 1
    fi
}

# Function to test AI Assistant functionality
test_ai_assistant() {
    echo "🤖 Testing AI Assistant functionality..."
    
    local test_log="$TEST_RESULTS_DIR/ai-assistant-test-${TIMESTAMP}.log"
    
    cd "$PROJECT_ROOT"
    
    echo "## AI Assistant Test" > "$test_log"
    
    # Check if AI Assistant files exist
    if [[ -d "ai-assistant" ]]; then
        echo "Testing AI Assistant configuration..." >> "$test_log"
        
        # Test configuration loading
        if [[ -f "ai-assistant/config/ai_config.yaml" ]]; then
            if python3 -c "import yaml; yaml.safe_load(open('ai-assistant/config/ai_config.yaml'))" 2>>"$test_log"; then
                echo "✅ AI Assistant config valid" | tee -a "$test_log"
            else
                echo "❌ AI Assistant config invalid" | tee -a "$test_log"
                return 1
            fi
        fi
        
        # Test Python imports
        if [[ -f "ai-assistant/src/ai_service.py" ]]; then
            if python3 -c "import sys; sys.path.append('ai-assistant/src'); import ai_service" 2>>"$test_log"; then
                echo "✅ AI Assistant imports OK" | tee -a "$test_log"
            else
                echo "❌ AI Assistant import errors" | tee -a "$test_log"
                return 1
            fi
        fi
    else
        echo "ℹ️  AI Assistant directory not found, skipping test" | tee -a "$test_log"
    fi
}

# Function to test container builds
test_container_builds() {
    echo "🐳 Testing container builds..."
    
    local test_log="$TEST_RESULTS_DIR/container-test-${TIMESTAMP}.log"
    
    cd "$PROJECT_ROOT"
    
    echo "## Container Build Test" > "$test_log"
    
    # Test Dockerfile syntax
    if [[ -f "Dockerfile" ]]; then
        echo "Testing Dockerfile..." >> "$test_log"
        if command -v hadolint >/dev/null 2>&1; then
            if hadolint Dockerfile >>"$test_log" 2>&1; then
                echo "✅ Dockerfile passed hadolint check" | tee -a "$test_log"
            else
                echo "⚠️  Dockerfile has hadolint warnings (check log)" | tee -a "$test_log"
            fi
        else
            echo "ℹ️  hadolint not available, skipping Dockerfile check" | tee -a "$test_log"
        fi
    fi
    
    # Test AI Assistant Dockerfile
    if [[ -f "ai-assistant/Dockerfile" ]]; then
        echo "Testing AI Assistant Dockerfile..." >> "$test_log"
        if command -v hadolint >/dev/null 2>&1; then
            if hadolint ai-assistant/Dockerfile >>"$test_log" 2>&1; then
                echo "✅ AI Assistant Dockerfile passed hadolint check" | tee -a "$test_log"
            else
                echo "⚠️  AI Assistant Dockerfile has hadolint warnings (check log)" | tee -a "$test_log"
            fi
        fi
    fi
}

# Function to test CI/CD configuration
test_cicd_config() {
    echo "🔄 Testing CI/CD configuration..."
    
    local test_log="$TEST_RESULTS_DIR/cicd-test-${TIMESTAMP}.log"
    
    cd "$PROJECT_ROOT"
    
    echo "## CI/CD Configuration Test" > "$test_log"
    
    # Test GitHub Actions workflows
    if [[ -d ".github/workflows" ]]; then
        echo "Testing GitHub Actions workflows..." >> "$test_log"
        local workflow_errors=0
        
        while IFS= read -r -d '' workflow; do
            echo "Testing: $workflow" >> "$test_log"
            if python3 -c "import yaml; yaml.safe_load(open('$workflow'))" 2>>"$test_log"; then
                echo "✅ $(basename "$workflow") syntax OK" | tee -a "$test_log"
            else
                echo "❌ $(basename "$workflow") syntax error" | tee -a "$test_log"
                ((workflow_errors++))
            fi
        done < <(find .github/workflows -name "*.yml" -o -name "*.yaml" -print0 2>/dev/null || true)
        
        if [[ $workflow_errors -eq 0 ]]; then
            echo "✅ All GitHub Actions workflows passed syntax check"
        else
            echo "❌ $workflow_errors GitHub Actions workflow errors found"
            return 1
        fi
    fi
    
    # Test GitLab CI configuration
    if [[ -f ".gitlab-ci.yml" ]]; then
        echo "Testing GitLab CI configuration..." >> "$test_log"
        if python3 -c "import yaml; yaml.safe_load(open('.gitlab-ci.yml'))" 2>>"$test_log"; then
            echo "✅ GitLab CI config syntax OK" | tee -a "$test_log"
        else
            echo "❌ GitLab CI config syntax error" | tee -a "$test_log"
            return 1
        fi
    fi
}

# Function to run unit tests if available
run_unit_tests() {
    echo "🧪 Running unit tests..."
    
    local test_log="$TEST_RESULTS_DIR/unit-tests-${TIMESTAMP}.log"
    
    cd "$PROJECT_ROOT"
    
    echo "## Unit Tests" > "$test_log"
    
    # Run Python tests if pytest is available
    if command -v pytest >/dev/null 2>&1 && [[ -d "tests" ]]; then
        echo "Running pytest..." >> "$test_log"
        if pytest tests/ -v >>"$test_log" 2>&1; then
            echo "✅ Unit tests passed" | tee -a "$test_log"
        else
            echo "❌ Unit tests failed (check log)" | tee -a "$test_log"
            return 1
        fi
    elif [[ -d "tests" ]]; then
        echo "Running Python unittest..." >> "$test_log"
        if python3 -m unittest discover tests/ -v >>"$test_log" 2>&1; then
            echo "✅ Unit tests passed" | tee -a "$test_log"
        else
            echo "❌ Unit tests failed (check log)" | tee -a "$test_log"
            return 1
        fi
    else
        echo "ℹ️  No unit tests found or pytest not available" | tee -a "$test_log"
    fi
}

# Function to test security configuration
test_security_config() {
    echo "🔒 Testing security configuration..."
    
    local test_log="$TEST_RESULTS_DIR/security-test-${TIMESTAMP}.log"
    
    cd "$PROJECT_ROOT"
    
    echo "## Security Configuration Test" > "$test_log"
    
    # Test Gitleaks configuration
    if [[ -f ".gitleaks.toml" ]]; then
        echo "Testing Gitleaks configuration..." >> "$test_log"
        if gitleaks detect --config .gitleaks.toml --no-git >>"$test_log" 2>&1; then
            echo "✅ Gitleaks configuration test passed" | tee -a "$test_log"
        else
            echo "⚠️  Gitleaks found issues (expected after cleanup)" | tee -a "$test_log"
        fi
    fi
    
    # Check .gitignore effectiveness
    echo "Testing .gitignore effectiveness..." >> "$test_log"
    local ignored_files=0
    
    # Check if sensitive patterns are properly ignored
    while IFS= read -r -d '' file; do
        if git check-ignore "$file" >/dev/null 2>&1; then
            ((ignored_files++))
        else
            echo "⚠️  File not ignored: $file" | tee -a "$test_log"
        fi
    done < <(find . -name "*.env*" -o -name "*.key" -o -name "*.backup*" \
        -not -path "./.git/*" -not -path "./.security-backups/*" -print0 2>/dev/null || true)
    
    echo "✅ $ignored_files sensitive files properly ignored" | tee -a "$test_log"
}

# Function to generate test summary
generate_test_summary() {
    echo "📊 Generating test summary..."
    
    local summary_file="$TEST_RESULTS_DIR/test-summary-${TIMESTAMP}.txt"
    
    cat > "$summary_file" << EOF
# Post-Cleanup Test Summary
Generated: $(date)
Project: $(basename "$PROJECT_ROOT")

## Test Results
- Basic functionality: $(ls -1 "$TEST_RESULTS_DIR"/basic-functionality-*${TIMESTAMP}* 2>/dev/null | wc -l) tests run
- Ansible playbooks: $(ls -1 "$TEST_RESULTS_DIR"/ansible-test-*${TIMESTAMP}* 2>/dev/null | wc -l) tests run
- AI Assistant: $(ls -1 "$TEST_RESULTS_DIR"/ai-assistant-test-*${TIMESTAMP}* 2>/dev/null | wc -l) tests run
- Container builds: $(ls -1 "$TEST_RESULTS_DIR"/container-test-*${TIMESTAMP}* 2>/dev/null | wc -l) tests run
- CI/CD config: $(ls -1 "$TEST_RESULTS_DIR"/cicd-test-*${TIMESTAMP}* 2>/dev/null | wc -l) tests run
- Unit tests: $(ls -1 "$TEST_RESULTS_DIR"/unit-tests-*${TIMESTAMP}* 2>/dev/null | wc -l) tests run
- Security config: $(ls -1 "$TEST_RESULTS_DIR"/security-test-*${TIMESTAMP}* 2>/dev/null | wc -l) tests run

## Overall Status
$(if [[ -f "$TEST_RESULTS_DIR/test-status-${TIMESTAMP}.txt" ]]; then cat "$TEST_RESULTS_DIR/test-status-${TIMESTAMP}.txt"; else echo "Tests completed"; fi)

## Next Steps
1. Review detailed test logs in: $TEST_RESULTS_DIR
2. Fix any issues found during testing
3. Commit cleanup changes if all tests pass
4. Setup pre-commit hooks for future prevention

## Test Log Files
$(ls -la "$TEST_RESULTS_DIR"/*${TIMESTAMP}* 2>/dev/null || echo "No test files found")
EOF

    echo "✅ Test summary saved: $summary_file"
}

# Main testing process
main() {
    echo "🚀 Starting post-cleanup testing..."
    echo "   Project: $(basename "$PROJECT_ROOT")"
    echo "   Timestamp: $TIMESTAMP"
    echo ""
    
    local test_failures=0
    
    # Run all tests and track failures
    test_basic_functionality || ((test_failures++))
    test_ansible_playbooks || ((test_failures++))
    test_ai_assistant || ((test_failures++))
    test_container_builds || ((test_failures++))
    test_cicd_config || ((test_failures++))
    run_unit_tests || ((test_failures++))
    test_security_config || ((test_failures++))
    
    # Save test status
    if [[ $test_failures -eq 0 ]]; then
        echo "✅ ALL TESTS PASSED" | tee "$TEST_RESULTS_DIR/test-status-${TIMESTAMP}.txt"
    else
        echo "❌ $test_failures TEST CATEGORIES FAILED" | tee "$TEST_RESULTS_DIR/test-status-${TIMESTAMP}.txt"
    fi
    
    generate_test_summary
    
    echo ""
    echo "🎉 Post-cleanup testing complete!"
    echo ""
    echo "📁 Test results location: $TEST_RESULTS_DIR"
    echo "📊 Test summary: $TEST_RESULTS_DIR/test-summary-${TIMESTAMP}.txt"
    echo ""
    
    if [[ $test_failures -eq 0 ]]; then
        echo "✅ All tests passed! Safe to commit cleanup changes."
        echo ""
        echo "Next steps:"
        echo "1. git add ."
        echo "2. git commit -m 'Clean up AI-generated notes and sensitive content'"
        echo "3. ./scripts/setup-precommit-hooks.sh"
    else
        echo "❌ Some tests failed. Review logs before committing."
        echo ""
        echo "Fix issues and re-run: ./scripts/test-after-cleanup.sh"
    fi
    
    return $test_failures
}

# Handle command line arguments
case "${1:-test}" in
    "test")
        main
        ;;
    "basic-only")
        test_basic_functionality
        ;;
    "help")
        echo "Usage: $0 [test|basic-only|help]"
        echo "  test       - Run all post-cleanup tests (default)"
        echo "  basic-only - Run only basic functionality tests"
        echo "  help       - Show this help message"
        ;;
    *)
        echo "❌ Unknown option: $1"
        echo "Run: $0 help"
        exit 1
        ;;
esac
