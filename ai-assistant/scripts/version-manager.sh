#!/bin/bash
# AI Assistant Container Version Management Script
# Implements semantic versioning strategy for container releases

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AI_ASSISTANT_DIR="$(dirname "$SCRIPT_DIR")"
VERSION_FILE="$AI_ASSISTANT_DIR/VERSION"
CHANGELOG_FILE="$AI_ASSISTANT_DIR/CHANGELOG.md"

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

# Get current version
get_current_version() {
    if [[ -f "$VERSION_FILE" ]]; then
        cat "$VERSION_FILE"
    else
        echo "0.0.0"
    fi
}

# Parse semantic version
parse_version() {
    local version="$1"
    if [[ $version =~ ^([0-9]+)\.([0-9]+)\.([0-9]+)(-([a-zA-Z0-9.-]+))?(\+([a-zA-Z0-9.-]+))?$ ]]; then
        MAJOR="${BASH_REMATCH[1]}"
        MINOR="${BASH_REMATCH[2]}"
        PATCH="${BASH_REMATCH[3]}"
        PRERELEASE="${BASH_REMATCH[5]}"
        BUILD="${BASH_REMATCH[7]}"
        return 0
    else
        log_error "Invalid semantic version format: $version"
        return 1
    fi
}

# Increment version
increment_version() {
    local version="$1"
    local increment_type="$2"

    if ! parse_version "$version"; then
        return 1
    fi

    case "$increment_type" in
        major)
            MAJOR=$((MAJOR + 1))
            MINOR=0
            PATCH=0
            PRERELEASE=""
            BUILD=""
            ;;
        minor)
            MINOR=$((MINOR + 1))
            PATCH=0
            PRERELEASE=""
            BUILD=""
            ;;
        patch)
            PATCH=$((PATCH + 1))
            PRERELEASE=""
            BUILD=""
            ;;
        prerelease)
            if [[ -z "$PRERELEASE" ]]; then
                PRERELEASE="alpha.1"
            else
                # Increment prerelease number
                if [[ $PRERELEASE =~ ^([a-zA-Z]+)\.([0-9]+)$ ]]; then
                    local pre_type="${BASH_REMATCH[1]}"
                    local pre_num="${BASH_REMATCH[2]}"
                    PRERELEASE="$pre_type.$((pre_num + 1))"
                else
                    PRERELEASE="$PRERELEASE.1"
                fi
            fi
            ;;
        *)
            log_error "Invalid increment type: $increment_type (use: major, minor, patch, prerelease)"
            return 1
            ;;
    esac

    local new_version="$MAJOR.$MINOR.$PATCH"
    if [[ -n "$PRERELEASE" ]]; then
        new_version="$new_version-$PRERELEASE"
    fi
    if [[ -n "$BUILD" ]]; then
        new_version="$new_version+$BUILD"
    fi

    echo "$new_version"
}

# Set version
set_version() {
    local version="$1"

    if ! parse_version "$version"; then
        return 1
    fi

    echo "$version" > "$VERSION_FILE"
    log_success "Version set to $version"
}

# Generate container tags
generate_container_tags() {
    local version="$1"
    local registry="${2:-localhost}"
    local image_name="${3:-qubinode-ai-assistant}"

    if ! parse_version "$version"; then
        return 1
    fi

    local tags=()

    # Full version tag
    tags+=("$registry/$image_name:$version")

    # Major.Minor tag (for patch updates)
    tags+=("$registry/$image_name:$MAJOR.$MINOR")

    # Major tag (for minor/patch updates)
    tags+=("$registry/$image_name:$MAJOR")

    # Latest tag (only for non-prerelease versions)
    if [[ -z "$PRERELEASE" ]]; then
        tags+=("$registry/$image_name:latest")
    fi

    # Date tag for tracking
    tags+=("$registry/$image_name:$(date +%Y%m%d)")

    printf '%s\n' "${tags[@]}"
}

# Generate build metadata
generate_build_metadata() {
    local version="$1"
    local build_info=""

    # Add git commit hash if available
    if command -v git &> /dev/null && git rev-parse --git-dir > /dev/null 2>&1; then
        local git_hash=$(git rev-parse --short HEAD)
        build_info="git.$git_hash"
    fi

    # Add build timestamp
    local timestamp=$(date +%Y%m%d%H%M%S)
    if [[ -n "$build_info" ]]; then
        build_info="$build_info.build.$timestamp"
    else
        build_info="build.$timestamp"
    fi

    # Parse version and add build metadata
    if parse_version "$version"; then
        local versioned_build="$MAJOR.$MINOR.$PATCH"
        if [[ -n "$PRERELEASE" ]]; then
            versioned_build="$versioned_build-$PRERELEASE"
        fi
        versioned_build="$versioned_build+$build_info"
        echo "$versioned_build"
    else
        echo "$version+$build_info"
    fi
}

# Validate version
validate_version() {
    local version="$1"

    if ! parse_version "$version"; then
        return 1
    fi

    log_success "Version $version is valid"
    echo "  Major: $MAJOR"
    echo "  Minor: $MINOR"
    echo "  Patch: $PATCH"
    if [[ -n "$PRERELEASE" ]]; then
        echo "  Prerelease: $PRERELEASE"
    fi
    if [[ -n "$BUILD" ]]; then
        echo "  Build: $BUILD"
    fi
}

# Create changelog entry
create_changelog_entry() {
    local version="$1"
    local changes="${2:-Minor improvements and bug fixes}"

    local date=$(date +%Y-%m-%d)
    local entry="## [$version] - $date

### Added
- $changes

### Changed
- Updated container version to $version

### Fixed
- Various bug fixes and improvements

"

    if [[ -f "$CHANGELOG_FILE" ]]; then
        # Insert after the header
        local temp_file=$(mktemp)
        head -n 3 "$CHANGELOG_FILE" > "$temp_file"
        echo "$entry" >> "$temp_file"
        tail -n +4 "$CHANGELOG_FILE" >> "$temp_file"
        mv "$temp_file" "$CHANGELOG_FILE"
    else
        # Create new changelog
        cat > "$CHANGELOG_FILE" << EOF
# Changelog

All notable changes to the Qubinode AI Assistant container will be documented in this file.

$entry
EOF
    fi

    log_success "Changelog entry created for version $version"
}

# Show usage
show_usage() {
    cat << EOF
AI Assistant Container Version Management

Usage: $0 <command> [options]

Commands:
    current                     Show current version
    increment <type>            Increment version (major|minor|patch|prerelease)
    set <version>              Set specific version
    validate <version>         Validate version format
    tags [registry] [image]    Generate container tags for current version
    build-metadata             Generate version with build metadata
    changelog <changes>        Create changelog entry for current version
    release <type> [changes]   Full release workflow (increment + changelog)

Examples:
    $0 current
    $0 increment minor
    $0 set 2.1.0
    $0 validate 1.0.0-alpha.1
    $0 tags quay.io/takinosh qubinode-ai-assistant
    $0 build-metadata
    $0 changelog "Added new AI model support"
    $0 release minor "Improved deployment strategy"

Version Format:
    MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]

    Examples:
    - 1.0.0 (stable release)
    - 1.0.0-alpha.1 (prerelease)
    - 1.0.0+build.20241111 (with build metadata)
EOF
}

# Main command processing
main() {
    case "${1:-}" in
        current)
            local current_version=$(get_current_version)
            echo "Current version: $current_version"
            validate_version "$current_version"
            ;;
        increment)
            if [[ -z "${2:-}" ]]; then
                log_error "Increment type required (major|minor|patch|prerelease)"
                exit 1
            fi
            local current_version=$(get_current_version)
            local new_version=$(increment_version "$current_version" "$2")
            if [[ $? -eq 0 ]]; then
                set_version "$new_version"
                echo "Version incremented: $current_version → $new_version"
            fi
            ;;
        set)
            if [[ -z "${2:-}" ]]; then
                log_error "Version required"
                exit 1
            fi
            set_version "$2"
            ;;
        validate)
            if [[ -z "${2:-}" ]]; then
                log_error "Version required"
                exit 1
            fi
            validate_version "$2"
            ;;
        tags)
            local current_version=$(get_current_version)
            local registry="${2:-localhost}"
            local image_name="${3:-qubinode-ai-assistant}"
            generate_container_tags "$current_version" "$registry" "$image_name"
            ;;
        build-metadata)
            local current_version=$(get_current_version)
            generate_build_metadata "$current_version"
            ;;
        changelog)
            local current_version=$(get_current_version)
            local changes="${2:-Minor improvements and bug fixes}"
            create_changelog_entry "$current_version" "$changes"
            ;;
        release)
            if [[ -z "${2:-}" ]]; then
                log_error "Release type required (major|minor|patch)"
                exit 1
            fi
            local current_version=$(get_current_version)
            local new_version=$(increment_version "$current_version" "$2")
            if [[ $? -eq 0 ]]; then
                set_version "$new_version"
                local changes="${3:-Release $new_version with improvements and bug fixes}"
                create_changelog_entry "$new_version" "$changes"
                log_success "Release $new_version completed!"
                echo "Next steps:"
                echo "  1. Review CHANGELOG.md"
                echo "  2. Commit changes: git add VERSION CHANGELOG.md && git commit -m 'Release $new_version'"
                echo "  3. Create git tag: git tag -a v$new_version -m 'Release $new_version'"
                echo "  4. Build container: ./scripts/build.sh"
                echo "  5. Push to registry"
            fi
            ;;
        --help|-h|help)
            show_usage
            ;;
        "")
            show_usage
            exit 1
            ;;
        *)
            log_error "Unknown command: $1"
            show_usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
