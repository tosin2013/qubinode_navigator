#!/bin/bash
# Qubinode Navigator - AI Tools Setup Script
# Copies AI assistant configurations to your project directory
#
# Usage:
#   ./scripts/setup-ai-tools.sh [target-directory] [options]
#
# Options:
#   --all         Install all AI tool configs (default)
#   --claude      Install Claude Code commands only
#   --gemini      Install Gemini CLI commands only
#   --cursor      Install Cursor rules only
#   --windsurf    Install Windsurf rules only
#   --symlink     Create symlinks instead of copying (for auto-updates)
#   --help        Show this help message

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
QUBINODE_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default options
INSTALL_ALL=true
INSTALL_CLAUDE=false
INSTALL_GEMINI=false
INSTALL_CURSOR=false
INSTALL_WINDSURF=false
USE_SYMLINKS=false
TARGET_DIR=""

show_help() {
    cat << 'EOF'
Qubinode Navigator - AI Tools Setup Script

This script installs AI assistant configurations (custom commands and rules)
to your project directory, enabling AI tools to understand Qubinode Navigator.

USAGE:
    ./scripts/setup-ai-tools.sh [target-directory] [options]

ARGUMENTS:
    target-directory    Directory to install configs to (default: current directory)

OPTIONS:
    --all               Install all AI tool configs (default)
    --claude            Install Claude Code commands only
    --gemini            Install Gemini CLI commands only
    --cursor            Install Cursor rules only
    --windsurf          Install Windsurf rules only
    --symlink           Create symlinks instead of copying
                        (configs auto-update when qubinode_navigator is updated)
    --help              Show this help message

EXAMPLES:
    # Install all configs to current directory
    ./scripts/setup-ai-tools.sh

    # Install to a specific project
    ./scripts/setup-ai-tools.sh /path/to/my-project

    # Install only Claude Code commands
    ./scripts/setup-ai-tools.sh --claude

    # Create symlinks for auto-updates
    ./scripts/setup-ai-tools.sh ~/my-project --symlink

SUPPORTED AI TOOLS:
    - Claude Code    (.claude/commands/)     - Slash commands for Claude
    - Gemini CLI     (.gemini/commands/)     - Custom commands for Gemini
    - Cursor         (.cursor/rules/)        - Context rules for Cursor
    - Windsurf       (.windsurf/rules/)      - Context rules for Windsurf

After installation, you can use commands like:
    Claude Code:  /dag-list, /vm-info, /diagnose
    Gemini CLI:   /dag:list, /vm:info, /diagnose

EOF
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

install_config() {
    local source_dir="$1"
    local target_dir="$2"
    local name="$3"

    if [[ ! -d "$source_dir" ]]; then
        log_warn "Source directory not found: $source_dir"
        return 1
    fi

    if [[ "$USE_SYMLINKS" == "true" ]]; then
        # Create parent directory if needed
        mkdir -p "$(dirname "$target_dir")"

        # Remove existing directory/symlink
        if [[ -e "$target_dir" || -L "$target_dir" ]]; then
            rm -rf "$target_dir"
        fi

        # Create symlink
        ln -s "$source_dir" "$target_dir"
        log_success "$name: Created symlink $target_dir -> $source_dir"
    else
        # Copy files
        mkdir -p "$target_dir"
        cp -r "$source_dir"/* "$target_dir/"
        log_success "$name: Copied to $target_dir"
    fi
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --all)
            INSTALL_ALL=true
            shift
            ;;
        --claude)
            INSTALL_ALL=false
            INSTALL_CLAUDE=true
            shift
            ;;
        --gemini)
            INSTALL_ALL=false
            INSTALL_GEMINI=true
            shift
            ;;
        --cursor)
            INSTALL_ALL=false
            INSTALL_CURSOR=true
            shift
            ;;
        --windsurf)
            INSTALL_ALL=false
            INSTALL_WINDSURF=true
            shift
            ;;
        --symlink)
            USE_SYMLINKS=true
            shift
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        -*)
            log_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
        *)
            TARGET_DIR="$1"
            shift
            ;;
    esac
done

# Set default target directory
if [[ -z "$TARGET_DIR" ]]; then
    TARGET_DIR="$(pwd)"
fi

# Validate target directory
if [[ ! -d "$TARGET_DIR" ]]; then
    log_error "Target directory does not exist: $TARGET_DIR"
    exit 1
fi

# Convert to absolute path
TARGET_DIR="$(cd "$TARGET_DIR" && pwd)"

echo ""
echo "========================================"
echo "  Qubinode Navigator AI Tools Setup"
echo "========================================"
echo ""
log_info "Source: $QUBINODE_ROOT"
log_info "Target: $TARGET_DIR"
log_info "Mode: $(if [[ "$USE_SYMLINKS" == "true" ]]; then echo "Symlinks"; else echo "Copy"; fi)"
echo ""

# Install selected configs
if [[ "$INSTALL_ALL" == "true" ]] || [[ "$INSTALL_CLAUDE" == "true" ]]; then
    install_config \
        "$QUBINODE_ROOT/.claude/commands" \
        "$TARGET_DIR/.claude/commands" \
        "Claude Code"
fi

if [[ "$INSTALL_ALL" == "true" ]] || [[ "$INSTALL_GEMINI" == "true" ]]; then
    install_config \
        "$QUBINODE_ROOT/.gemini/commands" \
        "$TARGET_DIR/.gemini/commands" \
        "Gemini CLI"
fi

if [[ "$INSTALL_ALL" == "true" ]] || [[ "$INSTALL_CURSOR" == "true" ]]; then
    install_config \
        "$QUBINODE_ROOT/.cursor/rules" \
        "$TARGET_DIR/.cursor/rules" \
        "Cursor"
fi

if [[ "$INSTALL_ALL" == "true" ]] || [[ "$INSTALL_WINDSURF" == "true" ]]; then
    install_config \
        "$QUBINODE_ROOT/.windsurf/rules" \
        "$TARGET_DIR/.windsurf/rules" \
        "Windsurf"
fi

echo ""
echo "========================================"
log_success "Installation complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo "  1. cd $TARGET_DIR"
echo "  2. Open your preferred AI tool:"
echo "     - Claude Code: claude"
echo "     - Gemini CLI:  gemini"
echo "     - Cursor:      Open folder in Cursor"
echo "     - Windsurf:    Open folder in Windsurf"
echo ""
echo "Available commands:"
echo "  Claude Code: /dag-list, /vm-info, /infra-status, /diagnose"
echo "  Gemini CLI:  /dag:list, /vm:info, /infra:status, /diagnose"
echo ""
