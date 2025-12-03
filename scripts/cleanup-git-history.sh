#!/bin/bash
# Git History Cleanup Script using BFG Repo-Cleaner
# Removes secrets and sensitive content from Git history

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_ROOT/.security-backups/history-cleanup"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

echo "🗂️  Starting Git history cleanup..."

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

# Function to create comprehensive backup before history cleanup
create_history_backup() {
    echo "💾 Creating comprehensive backup before history cleanup..."

    local backup_bundle="$BACKUP_DIR/pre-history-cleanup-${TIMESTAMP}.bundle"
    local backup_refs="$BACKUP_DIR/refs-backup-${TIMESTAMP}.txt"

    cd "$PROJECT_ROOT"

    # Create Git bundle with all refs
    git bundle create "$backup_bundle" --all

    # Backup all refs for reference
    git for-each-ref --format="%(refname) %(objectname) %(objecttype)" > "$backup_refs"

    # Create repository statistics
    cat > "$BACKUP_DIR/repo-stats-${TIMESTAMP}.txt" << EOF
# Repository Statistics Before History Cleanup
Generated: $(date)

## Repository Size
$(du -sh .git)

## Commit Count
Total commits: $(git rev-list --all --count)

## Branch Information
$(git branch -a)

## Tag Information
$(git tag -l)

## Large Files in History
$(git rev-list --objects --all | git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | awk '/^blob/ {print $3, $4}' | sort -nr | head -20)

## Recent Commits
$(git log --oneline -20)
EOF

    echo "✅ History backup created: $backup_bundle"
}

# Function to prepare secrets file for BFG
prepare_secrets_file() {
    echo "🔍 Preparing secrets file for BFG cleanup..."

    local secrets_file="$BACKUP_DIR/secrets-to-remove-${TIMESTAMP}.txt"
    local patterns_file="$BACKUP_DIR/file-patterns-to-remove-${TIMESTAMP}.txt"

    # Create secrets file from Gitleaks scan if available
    local latest_gitleaks_scan=$(find "$PROJECT_ROOT/.security-backups/scan-results" -name "gitleaks-scan-*.json" -type f | sort | tail -1)

    if [[ -f "$latest_gitleaks_scan" ]]; then
        echo "📄 Using Gitleaks scan results: $latest_gitleaks_scan"

        # Extract secrets from Gitleaks JSON
        jq -r '.[] | .Match' "$latest_gitleaks_scan" 2>/dev/null | grep -v '^$' > "$secrets_file" || touch "$secrets_file"

        echo "✅ Extracted $(wc -l < "$secrets_file") secrets for removal"
    else
        echo "⚠️  No Gitleaks scan found. Creating manual secrets file..."

        # Create template secrets file
        cat > "$secrets_file" << 'EOF'
# Add actual secrets found in your repository (one per line)
# Examples (replace with real secrets):
# actual_password_123
# sk-1234567890abcdef
# AKIA1234567890ABCDEF
EOF

        echo "📝 Created template secrets file: $secrets_file"
        echo "   Edit this file to add actual secrets before running BFG"
    fi

    # Create file patterns to remove
    cat > "$patterns_file" << 'EOF'
*.key
*.pem
*.crt
*_rsa
*.p12
*.pfx
*.env
vault.*
*.vault_password
*.backup
*secret*
*credential*
EOF

    echo "✅ Created file patterns: $patterns_file"
    echo "📁 Review and edit files in: $BACKUP_DIR"
}

# Function to run BFG Repo-Cleaner
run_bfg_cleanup() {
    echo "🧹 Running BFG Repo-Cleaner..."

    local secrets_file="$BACKUP_DIR/secrets-to-remove-${TIMESTAMP}.txt"
    local patterns_file="$BACKUP_DIR/file-patterns-to-remove-${TIMESTAMP}.txt"
    local bfg_log="$BACKUP_DIR/bfg-cleanup-${TIMESTAMP}.log"

    cd "$PROJECT_ROOT"

    # Check if BFG is available
    if ! command -v bfg >/dev/null 2>&1; then
        echo "❌ BFG Repo-Cleaner not found. Run: ./scripts/setup-security-tools.sh"
        exit 1
    fi

    # Check if secrets file has content (not just comments)
    if ! grep -v '^#' "$secrets_file" | grep -v '^$' >/dev/null 2>&1; then
        echo "⚠️  No secrets specified in: $secrets_file"
        echo "   Edit the file to add actual secrets, then re-run this script"
        return 1
    fi

    echo "🚀 Starting BFG cleanup process..." | tee "$bfg_log"

    # Remove secrets by content
    echo "Removing secrets by content..." | tee -a "$bfg_log"
    if bfg --replace-text "$secrets_file" --no-blob-protection . >>"$bfg_log" 2>&1; then
        echo "✅ Secrets removal completed" | tee -a "$bfg_log"
    else
        echo "❌ Secrets removal failed (check log)" | tee -a "$bfg_log"
        return 1
    fi

    # Remove files by pattern
    echo "Removing sensitive files by pattern..." | tee -a "$bfg_log"
    while IFS= read -r pattern; do
        if [[ -n "$pattern" && ! "$pattern" =~ ^# ]]; then
            echo "  Removing files matching: $pattern" | tee -a "$bfg_log"
            if bfg --delete-files "$pattern" --no-blob-protection . >>"$bfg_log" 2>&1; then
                echo "    ✅ Pattern $pattern processed" | tee -a "$bfg_log"
            else
                echo "    ⚠️  Pattern $pattern failed" | tee -a "$bfg_log"
            fi
        fi
    done < "$patterns_file"

    echo "✅ BFG cleanup completed. Check log: $bfg_log"
}

# Function to clean up Git repository after BFG
cleanup_git_repository() {
    echo "🧽 Cleaning up Git repository after BFG..."

    local cleanup_log="$BACKUP_DIR/git-cleanup-${TIMESTAMP}.log"

    cd "$PROJECT_ROOT"

    echo "Git repository cleanup started: $(date)" > "$cleanup_log"

    # Expire reflog entries
    echo "Expiring reflog entries..." | tee -a "$cleanup_log"
    git reflog expire --expire=now --all >>"$cleanup_log" 2>&1

    # Garbage collect with aggressive pruning
    echo "Running aggressive garbage collection..." | tee -a "$cleanup_log"
    git gc --prune=now --aggressive >>"$cleanup_log" 2>&1

    # Clean up BFG backup refs
    echo "Cleaning up BFG backup refs..." | tee -a "$cleanup_log"
    git for-each-ref --format="delete %(refname)" refs/original/ | git update-ref --stdin >>"$cleanup_log" 2>&1 || true

    # Final garbage collection
    echo "Final garbage collection..." | tee -a "$cleanup_log"
    git gc --prune=now >>"$cleanup_log" 2>&1

    echo "✅ Git repository cleanup completed"
}

# Function to verify cleanup results
verify_cleanup_results() {
    echo "🔍 Verifying cleanup results..."

    local verification_log="$BACKUP_DIR/cleanup-verification-${TIMESTAMP}.txt"

    cd "$PROJECT_ROOT"

    cat > "$verification_log" << EOF
# Git History Cleanup Verification Report
Generated: $(date)

## Repository Size After Cleanup
$(du -sh .git)

## Commit Count After Cleanup
Total commits: $(git rev-list --all --count)

## Remaining Large Files
$(git rev-list --objects --all | git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | awk '/^blob/ {print $3, $4}' | sort -nr | head -10)

## Git Status
$(git status --porcelain)

## Recent Commits (should be unchanged)
$(git log --oneline -10)
EOF

    # Run Gitleaks scan to verify secrets removal
    echo "## Post-Cleanup Security Scan" >> "$verification_log"
    if command -v gitleaks >/dev/null 2>&1 && [[ -f ".gitleaks.toml" ]]; then
        if gitleaks detect --config .gitleaks.toml --no-git >>"$verification_log" 2>&1; then
            echo "✅ No secrets detected after cleanup" | tee -a "$verification_log"
        else
            echo "⚠️  Some issues still detected (review log)" | tee -a "$verification_log"
        fi
    fi

    echo "✅ Verification completed: $verification_log"
}

# Function to generate force push instructions
generate_force_push_instructions() {
    echo "📋 Generating force push instructions..."

    local instructions_file="$BACKUP_DIR/force-push-instructions-${TIMESTAMP}.txt"

    cat > "$instructions_file" << EOF
# Force Push Instructions - CRITICAL SAFETY INFORMATION

## ⚠️  DANGER: DESTRUCTIVE OPERATION ⚠️

The Git history cleanup has modified the repository history. To apply these changes
to remote repositories, you MUST perform a force push. This is a destructive operation
that will rewrite history on the remote repository.

## Prerequisites Before Force Push

1. ✅ Ensure all team members have committed and pushed their work
2. ✅ Notify all team members about the upcoming history rewrite
3. ✅ Verify cleanup results with: git log --oneline -20
4. ✅ Test application functionality after cleanup
5. ✅ Have backups of the original repository

## Force Push Commands

### For GitHub/GitLab (main branch)
git push --force-with-lease origin main

### For all branches and tags
git push --force-with-lease --all origin
git push --force-with-lease --tags origin

### Alternative: Delete and re-push (safer for some workflows)
# Delete remote branch
git push origin --delete main
# Push clean branch
git push origin main

## Team Recovery Instructions

After force push, all team members must:

1. Backup their local work:
   git stash
   git branch backup-$(date +%Y%m%d)

2. Reset their local repository:
   git fetch origin
   git reset --hard origin/main

3. Restore their work:
   git stash pop
   # Or merge from backup branch

## Verification After Force Push

1. Clone fresh repository to verify cleanup
2. Run security scan: ./scripts/security-scan.sh
3. Test application functionality
4. Verify no secrets in history: git log --all --full-history --grep="password"

## Rollback Procedure (Emergency Only)

If issues are discovered after force push:

1. Restore from backup bundle:
   git clone pre-history-cleanup-${TIMESTAMP}.bundle restored-repo

2. Force push the original history:
   cd restored-repo
   git remote add origin <your-repo-url>
   git push --force-with-lease --all origin

## Current Repository State

- Backup bundle: $BACKUP_DIR/pre-history-cleanup-${TIMESTAMP}.bundle
- Cleanup log: $BACKUP_DIR/bfg-cleanup-${TIMESTAMP}.log
- Verification: $BACKUP_DIR/cleanup-verification-${TIMESTAMP}.txt

## Next Steps

1. Review all logs and verification reports
2. Test application thoroughly
3. Coordinate with team for force push timing
4. Execute force push during low-activity period
5. Monitor for issues after push
6. Setup pre-commit hooks to prevent future secrets

Generated: $(date)
EOF

    echo "✅ Force push instructions: $instructions_file"
    echo ""
    echo "🚨 CRITICAL: Read the instructions file before proceeding with force push!"
}

# Function to check history cleanup prerequisites
check_history_prerequisites() {
    echo "🔧 Checking history cleanup prerequisites..."

    # Check if we're in a Git repository
    if ! git rev-parse --git-dir >/dev/null 2>&1; then
        echo "❌ Not in a Git repository"
        exit 1
    fi

    # Check if BFG is available
    if ! command -v bfg >/dev/null 2>&1; then
        echo "❌ BFG Repo-Cleaner not found"
        echo "   Install with: ./scripts/setup-security-tools.sh"
        exit 1
    fi

    # Check for uncommitted changes
    if ! git diff-index --quiet HEAD -- 2>/dev/null; then
        echo "❌ You have uncommitted changes"
        echo "   Commit or stash changes before history cleanup"
        exit 1
    fi

    # Check if we have a remote
    if ! git remote >/dev/null 2>&1; then
        echo "⚠️  No remote repository configured"
        echo "   History cleanup will only affect local repository"
    fi

    # Warn about destructive operation
    echo ""
    echo "🚨 WARNING: Git history cleanup is a DESTRUCTIVE operation!"
    echo "   - It will rewrite Git history permanently"
    echo "   - All team members will need to re-clone or reset their repositories"
    echo "   - This operation cannot be easily undone"
    echo ""
    read -p "Do you want to continue? Type 'YES' to proceed: " -r
    if [[ "$REPLY" != "YES" ]]; then
        echo "❌ History cleanup cancelled"
        exit 1
    fi

    echo "✅ Prerequisites check passed"
}

# Main history cleanup process
main() {
    echo "🚀 Starting Git history cleanup..."
    echo "   Project: $(basename "$PROJECT_ROOT")"
    echo "   Timestamp: $TIMESTAMP"
    echo ""

    check_history_prerequisites

    create_history_backup
    prepare_secrets_file

    echo ""
    echo "📝 IMPORTANT: Review and edit the secrets file before continuing!"
    echo "   Secrets file: $BACKUP_DIR/secrets-to-remove-${TIMESTAMP}.txt"
    echo "   Patterns file: $BACKUP_DIR/file-patterns-to-remove-${TIMESTAMP}.txt"
    echo ""
    read -p "Press Enter after reviewing/editing the files, or Ctrl+C to cancel..."

    run_bfg_cleanup
    cleanup_git_repository
    verify_cleanup_results
    generate_force_push_instructions

    echo ""
    echo "🎉 Git history cleanup complete!"
    echo ""
    echo "📁 Cleanup results: $BACKUP_DIR"
    echo "📋 Force push instructions: $BACKUP_DIR/force-push-instructions-${TIMESTAMP}.txt"
    echo ""
    echo "🚨 CRITICAL NEXT STEPS:"
    echo "1. Review all cleanup logs and verification reports"
    echo "2. Test application functionality thoroughly"
    echo "3. Read force push instructions carefully"
    echo "4. Coordinate with team before force pushing"
    echo "5. Execute force push during low-activity period"
}

# Handle command line arguments
case "${1:-cleanup}" in
    "cleanup")
        main
        ;;
    "prepare-only")
        check_history_prerequisites
        create_history_backup
        prepare_secrets_file
        echo "✅ Preparation complete. Edit secrets file and run 'cleanup' to proceed."
        ;;
    "verify-only")
        verify_cleanup_results
        ;;
    "help")
        echo "Usage: $0 [cleanup|prepare-only|verify-only|help]"
        echo "  cleanup      - Full Git history cleanup process (default)"
        echo "  prepare-only - Only create backups and prepare secrets file"
        echo "  verify-only  - Only verify cleanup results"
        echo "  help         - Show this help message"
        ;;
    *)
        echo "❌ Unknown option: $1"
        echo "Run: $0 help"
        exit 1
        ;;
esac
