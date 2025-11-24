#!/bin/bash
# Comprehensive Security Scanning Script
# Detects secrets, AI-generated notes, and sensitive information

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SCAN_DIR="$PROJECT_ROOT/.security-backups/scan-results"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

echo "🔍 Starting comprehensive security scan..."

# Ensure scan directory exists
mkdir -p "$SCAN_DIR"

# Function to run Gitleaks scan
run_gitleaks_scan() {
    echo "🔒 Running Gitleaks security scan..."
    
    local output_file="$SCAN_DIR/gitleaks-scan-${TIMESTAMP}.json"
    local report_file="$SCAN_DIR/gitleaks-report-${TIMESTAMP}.txt"
    
    cd "$PROJECT_ROOT"
    
    # Run Gitleaks with detailed output
    if gitleaks detect --config .gitleaks.toml --report-format json --report-path "$output_file" --verbose; then
        echo "✅ Gitleaks scan completed - No secrets detected"
        echo "No secrets found" > "$report_file"
    else
        echo "⚠️  Gitleaks scan completed - Issues detected"
        
        # Generate human-readable report
        echo "# Gitleaks Security Scan Report" > "$report_file"
        echo "Generated: $(date)" >> "$report_file"
        echo "" >> "$report_file"
        
        if [[ -f "$output_file" ]]; then
            echo "## Summary" >> "$report_file"
            local secret_count=$(jq length "$output_file" 2>/dev/null || echo "0")
            echo "Total issues found: $secret_count" >> "$report_file"
            echo "" >> "$report_file"
            
            echo "## Detailed Findings" >> "$report_file"
            jq -r '.[] | "### \(.RuleID): \(.Description)\n- File: \(.File)\n- Line: \(.StartLine)\n- Match: \(.Match)\n"' "$output_file" >> "$report_file" 2>/dev/null || echo "Error parsing JSON results" >> "$report_file"
        fi
    fi
    
    echo "📄 Gitleaks report saved: $report_file"
}

# Function to scan for AI-generated content
scan_ai_content() {
    echo "🤖 Scanning for AI-generated developer notes..."
    
    local ai_report="$SCAN_DIR/ai-content-scan-${TIMESTAMP}.txt"
    
    echo "# AI-Generated Content Scan Report" > "$ai_report"
    echo "Generated: $(date)" >> "$ai_report"
    echo "" >> "$ai_report"
    
    cd "$PROJECT_ROOT"
    
    # Scan for TODO/FIXME comments with detailed implementation
    echo "## Long TODO/FIXME Comments (Potential AI-generated)" >> "$ai_report"
    grep -rn --include="*.py" --include="*.sh" --include="*.yml" --include="*.yaml" --include="*.md" \
        -E "(TODO|FIXME|HACK|XXX|NOTE):.{30,}" . >> "$ai_report" 2>/dev/null || echo "None found" >> "$ai_report"
    echo "" >> "$ai_report"
    
    # Scan for implementation notes
    echo "## Implementation Notes" >> "$ai_report"
    grep -rn --include="*.py" --include="*.sh" --include="*.yml" --include="*.yaml" --include="*.md" \
        -iE "(implementation note|ai note|claude note|assistant note)" . >> "$ai_report" 2>/dev/null || echo "None found" >> "$ai_report"
    echo "" >> "$ai_report"
    
    # Scan for debug/temporary comments
    echo "## Debug/Temporary Comments" >> "$ai_report"
    grep -rn --include="*.py" --include="*.sh" --include="*.yml" --include="*.yaml" \
        -iE "(DEBUG|TEMP|REMOVE|DELETE|CLEANUP):" . >> "$ai_report" 2>/dev/null || echo "None found" >> "$ai_report"
    echo "" >> "$ai_report"
    
    # Scan for internal architecture details
    echo "## Internal Architecture Details" >> "$ai_report"
    grep -rn --include="*.md" --include="*.py" --include="*.sh" \
        -iE "(internal implementation|private method|internal use only|not for production)" . >> "$ai_report" 2>/dev/null || echo "None found" >> "$ai_report"
    
    echo "📄 AI content report saved: $ai_report"
}

# Function to scan for large files
scan_large_files() {
    echo "📏 Scanning for large files..."
    
    local large_files_report="$SCAN_DIR/large-files-scan-${TIMESTAMP}.txt"
    
    echo "# Large Files Scan Report" > "$large_files_report"
    echo "Generated: $(date)" >> "$large_files_report"
    echo "" >> "$large_files_report"
    
    cd "$PROJECT_ROOT"
    
    # Find files larger than 10MB
    echo "## Files larger than 10MB" >> "$large_files_report"
    find . -type f -size +10M -not -path "./.git/*" -not -path "./.security-backups/*" \
        -exec ls -lh {} \; >> "$large_files_report" 2>/dev/null || echo "None found" >> "$large_files_report"
    echo "" >> "$large_files_report"
    
    # Find files larger than 1MB
    echo "## Files larger than 1MB" >> "$large_files_report"
    find . -type f -size +1M -not -path "./.git/*" -not -path "./.security-backups/*" \
        -exec ls -lh {} \; >> "$large_files_report" 2>/dev/null || echo "None found" >> "$large_files_report"
    
    echo "📄 Large files report saved: $large_files_report"
}

# Function to scan for sensitive file patterns
scan_sensitive_patterns() {
    echo "🔐 Scanning for sensitive file patterns..."
    
    local sensitive_report="$SCAN_DIR/sensitive-patterns-${TIMESTAMP}.txt"
    
    echo "# Sensitive Patterns Scan Report" > "$sensitive_report"
    echo "Generated: $(date)" >> "$sensitive_report"
    echo "" >> "$sensitive_report"
    
    cd "$PROJECT_ROOT"
    
    # Find potential credential files
    echo "## Potential Credential Files" >> "$sensitive_report"
    find . -type f \( -name "*.env*" -o -name "*.key" -o -name "*.pem" -o -name "*.crt" -o -name "*secret*" -o -name "*credential*" \) \
        -not -path "./.git/*" -not -path "./.security-backups/*" >> "$sensitive_report" 2>/dev/null || echo "None found" >> "$sensitive_report"
    echo "" >> "$sensitive_report"
    
    # Find backup files
    echo "## Backup Files" >> "$sensitive_report"
    find . -type f \( -name "*.backup*" -o -name "*.bak" -o -name "*~" \) \
        -not -path "./.git/*" -not -path "./.security-backups/*" >> "$sensitive_report" 2>/dev/null || echo "None found" >> "$sensitive_report"
    echo "" >> "$sensitive_report"
    
    # Find configuration files with potential secrets
    echo "## Configuration Files (Review for secrets)" >> "$sensitive_report"
    find . -type f \( -name "config.*" -o -name "*.conf" -o -name "*.cfg" \) \
        -not -path "./.git/*" -not -path "./.security-backups/*" >> "$sensitive_report" 2>/dev/null || echo "None found" >> "$sensitive_report"
    
    echo "📄 Sensitive patterns report saved: $sensitive_report"
}

# Function to generate scan summary
generate_scan_summary() {
    echo "📊 Generating scan summary..."
    
    local summary_file="$SCAN_DIR/scan-summary-${TIMESTAMP}.txt"
    
    echo "# Security Scan Summary Report" > "$summary_file"
    echo "Generated: $(date)" >> "$summary_file"
    echo "Project: $(basename "$PROJECT_ROOT")" >> "$summary_file"
    echo "" >> "$summary_file"
    
    echo "## Scan Results" >> "$summary_file"
    echo "- Gitleaks scan: $(ls -1 "$SCAN_DIR"/gitleaks-*${TIMESTAMP}* | wc -l) files generated" >> "$summary_file"
    echo "- AI content scan: $(ls -1 "$SCAN_DIR"/ai-content-*${TIMESTAMP}* | wc -l) files generated" >> "$summary_file"
    echo "- Large files scan: $(ls -1 "$SCAN_DIR"/large-files-*${TIMESTAMP}* | wc -l) files generated" >> "$summary_file"
    echo "- Sensitive patterns scan: $(ls -1 "$SCAN_DIR"/sensitive-patterns-*${TIMESTAMP}* | wc -l) files generated" >> "$summary_file"
    echo "" >> "$summary_file"
    
    echo "## Next Steps" >> "$summary_file"
    echo "1. Review all scan reports in: $SCAN_DIR" >> "$summary_file"
    echo "2. Identify files/content for cleanup" >> "$summary_file"
    echo "3. Run cleanup scripts for current branch" >> "$summary_file"
    echo "4. Consider Git history cleanup if secrets found" >> "$summary_file"
    echo "5. Setup pre-commit hooks to prevent future issues" >> "$summary_file"
    echo "" >> "$summary_file"
    
    echo "## Report Files Generated" >> "$summary_file"
    ls -la "$SCAN_DIR"/*${TIMESTAMP}* >> "$summary_file" 2>/dev/null || echo "No files found" >> "$summary_file"
    
    echo "📄 Scan summary saved: $summary_file"
}

# Function to check scan prerequisites
check_prerequisites() {
    echo "🔧 Checking scan prerequisites..."
    
    # Check if Gitleaks is installed
    if ! command -v gitleaks >/dev/null 2>&1; then
        echo "❌ Gitleaks not found. Run: ./scripts/setup-security-tools.sh"
        exit 1
    fi
    
    # Check if jq is available for JSON parsing
    if ! command -v jq >/dev/null 2>&1; then
        echo "⚠️  jq not found. Installing for JSON parsing..."
        if command -v apt-get >/dev/null 2>&1; then
            sudo apt-get update && sudo apt-get install -y jq
        elif command -v yum >/dev/null 2>&1; then
            sudo yum install -y jq
        else
            echo "❌ Please install jq manually for JSON parsing"
            exit 1
        fi
    fi
    
    # Check if we're in a Git repository
    if ! git rev-parse --git-dir >/dev/null 2>&1; then
        echo "❌ Not in a Git repository"
        exit 1
    fi
    
    # Check if Gitleaks config exists
    if [[ ! -f "$PROJECT_ROOT/.gitleaks.toml" ]]; then
        echo "❌ Gitleaks configuration not found: .gitleaks.toml"
        exit 1
    fi
    
    echo "✅ Prerequisites check passed"
}

# Main scanning process
main() {
    echo "🚀 Starting comprehensive security scan..."
    echo "   Project: $(basename "$PROJECT_ROOT")"
    echo "   Timestamp: $TIMESTAMP"
    echo ""
    
    check_prerequisites
    
    run_gitleaks_scan
    scan_ai_content
    scan_large_files
    scan_sensitive_patterns
    generate_scan_summary
    
    echo ""
    echo "🎉 Security scan complete!"
    echo ""
    echo "📁 Scan results location: $SCAN_DIR"
    echo "📊 Summary report: $SCAN_DIR/scan-summary-${TIMESTAMP}.txt"
    echo ""
    echo "⚠️  IMPORTANT: Review all scan reports before proceeding with cleanup!"
    echo ""
    echo "Next steps:"
    echo "1. Review scan reports: ls -la $SCAN_DIR/*${TIMESTAMP}*"
    echo "2. Plan cleanup strategy based on findings"
    echo "3. Run current branch cleanup: ./scripts/cleanup-current-branch.sh"
}

# Handle command line arguments
case "${1:-scan}" in
    "scan")
        main
        ;;
    "gitleaks-only")
        check_prerequisites
        run_gitleaks_scan
        ;;
    "ai-only")
        scan_ai_content
        ;;
    "help")
        echo "Usage: $0 [scan|gitleaks-only|ai-only|help]"
        echo "  scan        - Run complete security scan (default)"
        echo "  gitleaks-only - Run only Gitleaks scan"
        echo "  ai-only     - Run only AI content scan"
        echo "  help        - Show this help message"
        ;;
    *)
        echo "❌ Unknown option: $1"
        echo "Run: $0 help"
        exit 1
        ;;
esac
