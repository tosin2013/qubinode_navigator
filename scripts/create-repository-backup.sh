#!/bin/bash
# Repository Backup Script for DevSecOps Operations
# Creates comprehensive backups before security cleanup operations

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_ROOT/.security-backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

echo "🔒 Creating comprehensive repository backup..."

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"/{git-bundles,file-backups,scan-results}

# Function to create Git bundle backup
create_git_bundle() {
    echo "📦 Creating Git bundle backup..."

    local bundle_file="$BACKUP_DIR/git-bundles/repo-backup-${TIMESTAMP}.bundle"

    cd "$PROJECT_ROOT"
    git bundle create "$bundle_file" --all

    if [[ -f "$bundle_file" ]]; then
        echo "✅ Git bundle created: $bundle_file"
        echo "   Size: $(du -h "$bundle_file" | cut -f1)"
    else
        echo "❌ Failed to create Git bundle"
        exit 1
    fi
}

# Function to create file system backup
create_filesystem_backup() {
    echo "📁 Creating filesystem backup..."

    local backup_archive="$BACKUP_DIR/file-backups/filesystem-backup-${TIMESTAMP}.tar.gz"

    cd "$PROJECT_ROOT"

    # Create exclusion list for large/unnecessary files
    cat > /tmp/backup-exclude.txt << 'EOF'
.git
node_modules
__pycache__
*.pyc
*.pyo
.pytest_cache
*.log
*.tmp
*.cache
.security-backups
ai-assistant/models
ai-assistant/data/rag-docs
ai-assistant/data/vector-db
EOF

    tar --exclude-from=/tmp/backup-exclude.txt \
        -czf "$backup_archive" \
        --exclude-vcs \
        .

    rm /tmp/backup-exclude.txt

    if [[ -f "$backup_archive" ]]; then
        echo "✅ Filesystem backup created: $backup_archive"
        echo "   Size: $(du -h "$backup_archive" | cut -f1)"
    else
        echo "❌ Failed to create filesystem backup"
        exit 1
    fi
}

# Function to backup sensitive files separately
backup_sensitive_files() {
    echo "🔐 Backing up sensitive files..."

    local sensitive_backup="$BACKUP_DIR/file-backups/sensitive-files-${TIMESTAMP}.tar.gz"
    local sensitive_files=()

    # Find potential sensitive files
    while IFS= read -r -d '' file; do
        sensitive_files+=("$file")
    done < <(find "$PROJECT_ROOT" -type f \( \
        -name "*.env*" -o \
        -name "*.key" -o \
        -name "*.pem" -o \
        -name "*.crt" -o \
        -name "*secret*" -o \
        -name "*credential*" -o \
        -name "vault.*" -o \
        -name "*.vault_password" \
        \) -print0 2>/dev/null || true)

    if [[ ${#sensitive_files[@]} -gt 0 ]]; then
        tar -czf "$sensitive_backup" "${sensitive_files[@]}" 2>/dev/null || true
        echo "✅ Sensitive files backup created: $sensitive_backup"
        echo "   Files backed up: ${#sensitive_files[@]}"

        # List backed up files
        echo "   Sensitive files found:"
        printf '     %s\n' "${sensitive_files[@]}"
    else
        echo "ℹ️  No sensitive files found to backup"
    fi
}

# Function to create backup verification
create_backup_verification() {
    echo "🔍 Creating backup verification..."

    local verification_file="$BACKUP_DIR/backup-verification-${TIMESTAMP}.txt"

    cat > "$verification_file" << EOF
# Repository Backup Verification Report
# Generated: $(date)
# Project: $(basename "$PROJECT_ROOT")
# Git Repository: $(git remote get-url origin 2>/dev/null || echo "No remote origin")

## Backup Details
- Timestamp: $TIMESTAMP
- Git Bundle: git-bundles/repo-backup-${TIMESTAMP}.bundle
- Filesystem: file-backups/filesystem-backup-${TIMESTAMP}.tar.gz
- Sensitive Files: file-backups/sensitive-files-${TIMESTAMP}.tar.gz

## Git Status at Backup Time
$(git status --porcelain)

## Git Log (Last 10 commits)
$(git log --oneline -10)

## Repository Statistics
- Total commits: $(git rev-list --all --count)
- Branches: $(git branch -a | wc -l)
- Tags: $(git tag | wc -l)
- Total files: $(find "$PROJECT_ROOT" -type f | wc -l)

## Backup File Sizes
$(ls -lh "$BACKUP_DIR"/*/${TIMESTAMP}* 2>/dev/null || echo "No backup files found")

## Recovery Instructions
To restore from Git bundle:
  git clone repo-backup-${TIMESTAMP}.bundle restored-repo

To restore filesystem:
  tar -xzf filesystem-backup-${TIMESTAMP}.tar.gz

## Verification Checksums
EOF

    # Add checksums for verification
    echo "## File Checksums" >> "$verification_file"
    find "$BACKUP_DIR" -name "*${TIMESTAMP}*" -type f -exec sha256sum {} \; >> "$verification_file"

    echo "✅ Verification report created: $verification_file"
}

# Function to test backup integrity
test_backup_integrity() {
    echo "🧪 Testing backup integrity..."

    local bundle_file="$BACKUP_DIR/git-bundles/repo-backup-${TIMESTAMP}.bundle"
    local filesystem_backup="$BACKUP_DIR/file-backups/filesystem-backup-${TIMESTAMP}.tar.gz"

    # Test Git bundle
    if [[ -f "$bundle_file" ]]; then
        if git bundle verify "$bundle_file" >/dev/null 2>&1; then
            echo "✅ Git bundle integrity verified"
        else
            echo "❌ Git bundle integrity check failed"
            exit 1
        fi
    fi

    # Test filesystem backup
    if [[ -f "$filesystem_backup" ]]; then
        if tar -tzf "$filesystem_backup" >/dev/null 2>&1; then
            echo "✅ Filesystem backup integrity verified"
        else
            echo "❌ Filesystem backup integrity check failed"
            exit 1
        fi
    fi
}

# Main backup process
main() {
    echo "🚀 Starting comprehensive repository backup..."
    echo "   Project: $(basename "$PROJECT_ROOT")"
    echo "   Timestamp: $TIMESTAMP"
    echo ""

    # Ensure we're in a Git repository
    if ! git rev-parse --git-dir >/dev/null 2>&1; then
        echo "❌ Not in a Git repository"
        exit 1
    fi

    create_git_bundle
    create_filesystem_backup
    backup_sensitive_files
    create_backup_verification
    test_backup_integrity

    echo ""
    echo "🎉 Backup complete!"
    echo ""
    echo "Backup location: $BACKUP_DIR"
    echo "Backup timestamp: $TIMESTAMP"
    echo ""
    echo "⚠️  Store backups in a secure location before proceeding with cleanup operations!"
    echo ""
    echo "Next steps:"
    echo "1. Copy backups to secure external location"
    echo "2. Run security scan: ./scripts/security-scan.sh"
    echo "3. Review scan results before cleanup"
}

main "$@"
