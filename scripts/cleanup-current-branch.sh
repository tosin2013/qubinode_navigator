#!/bin/bash
# Current Branch Cleanup Script
# Removes/relocates AI-generated notes and sensitive content from active branches

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DEV_NOTES_DIR="$PROJECT_ROOT/.dev-notes"
INTERNAL_DOCS_DIR="$PROJECT_ROOT/docs/internal"
BACKUP_DIR="$PROJECT_ROOT/.security-backups/cleanup-backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

echo "🧹 Starting current branch cleanup..."

# Ensure directories exist
mkdir -p "$DEV_NOTES_DIR" "$INTERNAL_DOCS_DIR" "$BACKUP_DIR"

# Function to create cleanup backup
create_cleanup_backup() {
    echo "💾 Creating cleanup backup..."
    
    local backup_file="$BACKUP_DIR/pre-cleanup-backup-${TIMESTAMP}.tar.gz"
    
    cd "$PROJECT_ROOT"
    tar --exclude='.git' --exclude='.security-backups' \
        -czf "$backup_file" .
    
    echo "✅ Cleanup backup created: $backup_file"
}

# Function to move developer notes to hidden directory
move_developer_notes() {
    echo "📝 Moving developer notes to .dev-notes/..."
    
    local moved_count=0
    
    # Find and move standalone note files
    while IFS= read -r -d '' file; do
        if [[ -f "$file" ]]; then
            local relative_path="${file#$PROJECT_ROOT/}"
            local target_dir="$DEV_NOTES_DIR/$(dirname "$relative_path")"
            
            mkdir -p "$target_dir"
            mv "$file" "$target_dir/"
            echo "  Moved: $relative_path → .dev-notes/$relative_path"
            ((moved_count++))
        fi
    done < <(find "$PROJECT_ROOT" -maxdepth 2 -type f \( \
        -name "NOTES.md" -o \
        -name "TODO.md" -o \
        -name "*.notes" -o \
        -name "*.todo" -o \
        -name "IMPLEMENTATION-PLAN.md" -o \
        -name "DEVELOPMENT-NOTES.md" \
        \) -not -path "*/.git/*" -not -path "*/.security-backups/*" -not -path "*/.dev-notes/*" -print0 2>/dev/null || true)
    
    echo "✅ Moved $moved_count developer note files"
}

# Function to clean AI-generated comments from code files
clean_ai_comments() {
    echo "🤖 Cleaning AI-generated comments from code files..."
    
    local cleaned_count=0
    
    # Find Python files with AI comments
    while IFS= read -r -d '' file; do
        if [[ -f "$file" ]]; then
            local temp_file=$(mktemp)
            local changes_made=false
            
            # Remove long TODO/FIXME comments (likely AI-generated)
            if sed -E '/^[[:space:]]*#[[:space:]]*(TODO|FIXME|HACK|XXX|NOTE):.{30,}/d' "$file" > "$temp_file"; then
                if ! cmp -s "$file" "$temp_file"; then
                    changes_made=true
                fi
            fi
            
            # Remove debug/temporary comments
            if sed -E '/^[[:space:]]*#[[:space:]]*(DEBUG|TEMP|REMOVE|DELETE|CLEANUP):/d' "$temp_file" > "${temp_file}.2"; then
                mv "${temp_file}.2" "$temp_file"
                if ! cmp -s "$file" "$temp_file"; then
                    changes_made=true
                fi
            fi
            
            if [[ "$changes_made" == true ]]; then
                cp "$file" "$BACKUP_DIR/$(basename "$file").backup-${TIMESTAMP}"
                mv "$temp_file" "$file"
                echo "  Cleaned: ${file#$PROJECT_ROOT/}"
                ((cleaned_count++))
            else
                rm -f "$temp_file"
            fi
        fi
    done < <(find "$PROJECT_ROOT" -type f -name "*.py" \
        -not -path "*/.git/*" -not -path "*/.security-backups/*" -not -path "*/.dev-notes/*" -print0 2>/dev/null || true)
    
    # Clean shell scripts
    while IFS= read -r -d '' file; do
        if [[ -f "$file" ]]; then
            local temp_file=$(mktemp)
            local changes_made=false
            
            # Remove AI-generated comments from shell scripts
            if sed -E '/^[[:space:]]*#[[:space:]]*(TODO|FIXME|DEBUG|TEMP):.{20,}/d' "$file" > "$temp_file"; then
                if ! cmp -s "$file" "$temp_file"; then
                    cp "$file" "$BACKUP_DIR/$(basename "$file").backup-${TIMESTAMP}"
                    mv "$temp_file" "$file"
                    echo "  Cleaned: ${file#$PROJECT_ROOT/}"
                    ((cleaned_count++))
                    changes_made=true
                fi
            fi
            
            if [[ "$changes_made" != true ]]; then
                rm -f "$temp_file"
            fi
        fi
    done < <(find "$PROJECT_ROOT" -type f -name "*.sh" \
        -not -path "*/.git/*" -not -path "*/.security-backups/*" -not -path "*/.dev-notes/*" -print0 2>/dev/null || true)
    
    echo "✅ Cleaned $cleaned_count code files"
}

# Function to move internal documentation
move_internal_docs() {
    echo "📚 Moving internal documentation..."
    
    local moved_count=0
    
    # Move research and development docs
    if [[ -d "$PROJECT_ROOT/docs/research" ]]; then
        mv "$PROJECT_ROOT/docs/research" "$INTERNAL_DOCS_DIR/"
        echo "  Moved: docs/research → docs/internal/research"
        ((moved_count++))
    fi
    
    if [[ -d "$PROJECT_ROOT/docs/development" ]]; then
        mv "$PROJECT_ROOT/docs/development" "$INTERNAL_DOCS_DIR/"
        echo "  Moved: docs/development → docs/internal/development"
        ((moved_count++))
    fi
    
    # Move specific internal files
    local internal_files=(
        "MISSING-ENV-VARIABLES.md"
        "DNS-CONFIGURATION-GUIDE.md"
        "INTEGRATION_TEST_FIXES.md"
        "TIMEOUT_IMPROVEMENTS.md"
    )
    
    for file in "${internal_files[@]}"; do
        if [[ -f "$PROJECT_ROOT/$file" ]]; then
            mv "$PROJECT_ROOT/$file" "$INTERNAL_DOCS_DIR/"
            echo "  Moved: $file → docs/internal/$file"
            ((moved_count++))
        fi
    done
    
    echo "✅ Moved $moved_count internal documentation files"
}

# Function to remove sensitive files from tracking
remove_sensitive_files() {
    echo "🔒 Removing sensitive files from tracking..."
    
    local removed_count=0
    
    # Files that should not be in version control
    local sensitive_patterns=(
        "*.env"
        "*.key"
        "*.pem"
        "*.crt"
        "*_rsa"
        "*.p12"
        "*.pfx"
        "*.backup*"
        "notouch.env*"
    )
    
    cd "$PROJECT_ROOT"
    
    for pattern in "${sensitive_patterns[@]}"; do
        while IFS= read -r -d '' file; do
            if [[ -f "$file" ]] && git ls-files --error-unmatch "$file" >/dev/null 2>&1; then
                # Backup the file before removing from Git
                cp "$file" "$BACKUP_DIR/$(basename "$file").sensitive-backup-${TIMESTAMP}"
                
                # Remove from Git tracking but keep local file
                git rm --cached "$file" 2>/dev/null || true
                echo "  Removed from Git: ${file#$PROJECT_ROOT/}"
                ((removed_count++))
            fi
        done < <(find "$PROJECT_ROOT" -name "$pattern" -type f \
            -not -path "*/.git/*" -not -path "*/.security-backups/*" -print0 2>/dev/null || true)
    done
    
    echo "✅ Removed $removed_count sensitive files from Git tracking"
}

# Function to update .gitignore
update_gitignore() {
    echo "📝 Updating .gitignore..."
    
    local gitignore_file="$PROJECT_ROOT/.gitignore"
    local additions_needed=()
    
    # Check if dev-notes directory is ignored
    if ! grep -q "^\.dev-notes/" "$gitignore_file" 2>/dev/null; then
        additions_needed+=(".dev-notes/")
    fi
    
    # Check if internal docs are ignored
    if ! grep -q "^docs/internal/" "$gitignore_file" 2>/dev/null; then
        additions_needed+=("docs/internal/")
    fi
    
    # Add large file patterns
    local large_file_patterns=(
        "*.tar.gz"
        "*.zip"
        "*.iso"
        "*.img"
        "*.dmg"
        "*.exe"
        "*.msi"
        "*.deb"
        "*.rpm"
    )
    
    for pattern in "${large_file_patterns[@]}"; do
        if ! grep -q "^$pattern" "$gitignore_file" 2>/dev/null; then
            additions_needed+=("$pattern")
        fi
    done
    
    if [[ ${#additions_needed[@]} -gt 0 ]]; then
        echo "" >> "$gitignore_file"
        echo "# Added by cleanup script - $(date)" >> "$gitignore_file"
        printf '%s\n' "${additions_needed[@]}" >> "$gitignore_file"
        echo "✅ Added ${#additions_needed[@]} entries to .gitignore"
    else
        echo "✅ .gitignore is up to date"
    fi
}

# Function to create dev-notes README
create_dev_notes_readme() {
    echo "📖 Creating .dev-notes README..."
    
    cat > "$DEV_NOTES_DIR/README.md" << 'EOF'
# Developer Notes

This directory contains internal developer notes, implementation plans, and technical debt documentation that are not intended for end users.

## Contents

- **Implementation Plans**: Detailed technical implementation strategies
- **Development Notes**: Internal development discussions and decisions
- **Technical Debt**: Known issues and improvement opportunities
- **AI-Generated Content**: Detailed comments and notes from AI assistants

## Usage

These files are for internal development use only and are excluded from the main documentation to keep end-user documentation clean and focused.

## Access

This directory is gitignored and not included in releases or public documentation.

## Contributing

When adding content here:
1. Use clear, descriptive filenames
2. Include dates in time-sensitive notes
3. Reference related issues or PRs when applicable
4. Keep sensitive information in separate, encrypted storage
EOF

    echo "✅ Created .dev-notes/README.md"
}

# Function to create internal docs README
create_internal_docs_readme() {
    echo "📖 Creating docs/internal README..."
    
    cat > "$INTERNAL_DOCS_DIR/README.md" << 'EOF'
# Internal Documentation

This directory contains documentation intended for project contributors and maintainers, not end users.

## Contents

- **Architecture**: Internal system architecture and design decisions
- **Development**: Development setup, testing, and contribution guidelines
- **Research**: Research findings and technical investigations
- **Troubleshooting**: Internal troubleshooting guides and known issues

## Audience

This documentation is intended for:
- Project maintainers
- Core contributors
- DevOps engineers
- Security team members

## Structure

```
internal/
├── architecture/     # System design and architecture docs
├── development/      # Development and contribution guides
├── research/         # Research findings and investigations
├── security/         # Security procedures and guidelines
└── troubleshooting/  # Internal troubleshooting guides
```

## Access Control

This directory may contain sensitive information and should be:
- Reviewed before making public
- Excluded from end-user documentation
- Protected in production environments
EOF

    echo "✅ Created docs/internal/README.md"
}

# Function to generate cleanup report
generate_cleanup_report() {
    echo "📊 Generating cleanup report..."
    
    local report_file="$BACKUP_DIR/cleanup-report-${TIMESTAMP}.txt"
    
    cat > "$report_file" << EOF
# Current Branch Cleanup Report
Generated: $(date)
Project: $(basename "$PROJECT_ROOT")

## Summary
- Developer notes moved to .dev-notes/
- Internal documentation moved to docs/internal/
- AI-generated comments cleaned from code files
- Sensitive files removed from Git tracking
- .gitignore updated with new patterns

## Files Modified
$(find "$BACKUP_DIR" -name "*backup-${TIMESTAMP}" -type f | wc -l) files backed up before modification

## Directories Created
- .dev-notes/ (gitignored)
- docs/internal/ (gitignored)

## Git Status After Cleanup
$(cd "$PROJECT_ROOT" && git status --porcelain)

## Next Steps
1. Review changes: git diff
2. Test application functionality
3. Commit changes: git add . && git commit -m "Clean up AI-generated notes and sensitive content"
4. Consider Git history cleanup if needed
5. Setup pre-commit hooks: ./scripts/setup-precommit-hooks.sh

## Backup Location
All original files backed up to: $BACKUP_DIR
EOF

    echo "✅ Cleanup report saved: $report_file"
}

# Function to check cleanup prerequisites
check_cleanup_prerequisites() {
    echo "🔧 Checking cleanup prerequisites..."
    
    # Check if we're in a Git repository
    if ! git rev-parse --git-dir >/dev/null 2>&1; then
        echo "❌ Not in a Git repository"
        exit 1
    fi
    
    # Check for uncommitted changes
    if ! git diff-index --quiet HEAD -- 2>/dev/null; then
        echo "⚠️  Warning: You have uncommitted changes"
        echo "   Consider committing or stashing changes before cleanup"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "❌ Cleanup cancelled"
            exit 1
        fi
    fi
    
    echo "✅ Prerequisites check passed"
}

# Main cleanup process
main() {
    echo "🚀 Starting current branch cleanup..."
    echo "   Project: $(basename "$PROJECT_ROOT")"
    echo "   Timestamp: $TIMESTAMP"
    echo ""
    
    check_cleanup_prerequisites
    
    create_cleanup_backup
    move_developer_notes
    clean_ai_comments
    move_internal_docs
    remove_sensitive_files
    update_gitignore
    create_dev_notes_readme
    create_internal_docs_readme
    generate_cleanup_report
    
    echo ""
    echo "🎉 Current branch cleanup complete!"
    echo ""
    echo "📁 Backup location: $BACKUP_DIR"
    echo "📊 Cleanup report: $BACKUP_DIR/cleanup-report-${TIMESTAMP}.txt"
    echo ""
    echo "⚠️  IMPORTANT: Review changes before committing!"
    echo ""
    echo "Next steps:"
    echo "1. Review changes: git status && git diff"
    echo "2. Test application: ./scripts/test-after-cleanup.sh"
    echo "3. Commit changes: git add . && git commit -m 'Clean up AI-generated notes and sensitive content'"
    echo "4. Setup prevention: ./scripts/setup-precommit-hooks.sh"
}

# Handle command line arguments
case "${1:-cleanup}" in
    "cleanup")
        main
        ;;
    "dry-run")
        echo "🔍 Dry run mode - showing what would be cleaned..."
        check_cleanup_prerequisites
        echo "Would move developer notes, clean AI comments, and update .gitignore"
        echo "Run without arguments to perform actual cleanup"
        ;;
    "help")
        echo "Usage: $0 [cleanup|dry-run|help]"
        echo "  cleanup   - Perform full cleanup (default)"
        echo "  dry-run   - Show what would be cleaned without making changes"
        echo "  help      - Show this help message"
        ;;
    *)
        echo "❌ Unknown option: $1"
        echo "Run: $0 help"
        exit 1
        ;;
esac
