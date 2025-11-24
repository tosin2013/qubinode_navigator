#!/bin/bash
# =============================================================================
# Pre-Deployment Cleanup and Backup Script
# =============================================================================
#
# This script prepares the system for the one-shot deployment by backing up
# important files and cleaning up temporary/conflicting configurations.
#
# USAGE: ./pre-deployment-cleanup.sh
#
# =============================================================================

set -euo pipefail

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

# Create backup directory
BACKUP_DIR="/root/qubinode_navigator_backup_$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"
log_info "Created backup directory: $BACKUP_DIR"

echo "============================================================================="
echo "                    QUBINODE NAVIGATOR PRE-DEPLOYMENT CLEANUP"
echo "============================================================================="
echo ""

# =============================================================================
# BACKUP CRITICAL FILES
# =============================================================================

log_info "🔄 Backing up critical files..."

# 1. Backup environment files
if [[ -f /root/qubinode_navigator/.env ]]; then
    cp /root/qubinode_navigator/.env "$BACKUP_DIR/.env"
    log_success "Backed up existing .env file"
else
    log_info "No existing .env file found"
fi

if [[ -f /root/qubinode_navigator/notouch.env ]]; then
    cp /root/qubinode_navigator/notouch.env "$BACKUP_DIR/notouch.env"
    log_success "Backed up notouch.env file"
fi

# 2. Backup SSH keys (CRITICAL)
if [[ -d ~/.ssh ]]; then
    cp -r ~/.ssh "$BACKUP_DIR/ssh_backup"
    log_success "Backed up SSH keys and configuration"
else
    log_warning "No SSH directory found"
fi

# 3. Backup vault passwords
if [[ -f ~/.vault_password ]]; then
    cp ~/.vault_password "$BACKUP_DIR/vault_password"
    log_success "Backed up vault password"
fi

if [[ -f /root/.vault_password ]]; then
    cp /root/.vault_password "$BACKUP_DIR/root_vault_password"
    log_success "Backed up root vault password"
fi

# 4. Backup inventories
if [[ -d /root/qubinode_navigator/inventories ]]; then
    cp -r /root/qubinode_navigator/inventories "$BACKUP_DIR/inventories"
    log_success "Backed up inventory configurations"
fi

# 5. Backup ansible navigator config
if [[ -f ~/.ansible-navigator.yml ]]; then
    cp ~/.ansible-navigator.yml "$BACKUP_DIR/ansible-navigator.yml"
    log_success "Backed up ansible-navigator configuration"
fi

# 6. Backup bash aliases
if [[ -f ~/.bash_aliases ]]; then
    cp ~/.bash_aliases "$BACKUP_DIR/bash_aliases"
    log_success "Backed up bash aliases"
fi

# =============================================================================
# CLEANUP TEMPORARY/CONFLICTING FILES
# =============================================================================

log_info "🧹 Cleaning up temporary and conflicting files..."

# 1. Remove old deployment logs
log_info "Removing old deployment logs..."
rm -f /tmp/qubinode-deployment-*.log
rm -f /tmp/ansible-*.log
log_success "Cleaned up old deployment logs"

# 2. Remove temporary ansible files
log_info "Removing temporary ansible files..."
rm -f /root/qubinode_navigator/ansible_vault_setup.sh
rm -f /root/qubinode_navigator/ansiblesafe-*.tar.gz
rm -f /root/qubinode_navigator/*.tar.gz
log_success "Cleaned up temporary ansible files"

# 3. Remove ansible navigator config (will be regenerated)
if [[ -f ~/.ansible-navigator.yml ]]; then
    rm -f ~/.ansible-navigator.yml
    log_success "Removed old ansible-navigator configuration (will be regenerated)"
fi

# 4. Clean up old container processes (if any)
log_info "Checking for old AI Assistant containers..."
if podman ps -a | grep -q qubinode-ai-assistant; then
    log_warning "Found existing AI Assistant containers, stopping and removing..."
    podman stop qubinode-ai-assistant 2>/dev/null || true
    podman rm qubinode-ai-assistant 2>/dev/null || true
    log_success "Cleaned up old AI Assistant containers"
fi

# 5. Clean up old SSH agent processes
log_info "Cleaning up SSH agent processes..."
pkill ssh-agent 2>/dev/null || true
log_success "Cleaned up SSH agent processes"

# =============================================================================
# SYSTEM CHECKS
# =============================================================================

log_info "🔍 Performing system readiness checks..."

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    log_error "This script must be run as root"
    exit 1
fi

# Check available disk space
AVAILABLE_SPACE=$(df / | awk 'NR==2{print int($4/1024/1024)}')
if [[ $AVAILABLE_SPACE -lt 10 ]]; then
    log_warning "Low disk space: ${AVAILABLE_SPACE}GB available (recommend 50GB+)"
else
    log_success "Disk space check: ${AVAILABLE_SPACE}GB available"
fi

# Check memory
AVAILABLE_MEMORY=$(free -g | awk '/^Mem:/{print $2}')
if [[ $AVAILABLE_MEMORY -lt 8 ]]; then
    log_warning "Low memory: ${AVAILABLE_MEMORY}GB (recommend 8GB+)"
else
    log_success "Memory check: ${AVAILABLE_MEMORY}GB available"
fi

# Check network connectivity
if ping -c 1 8.8.8.8 &> /dev/null; then
    log_success "Network connectivity check passed"
else
    log_error "Network connectivity check failed"
    exit 1
fi

# =============================================================================
# ENVIRONMENT PREPARATION
# =============================================================================

log_info "📝 Preparing environment configuration..."

# Check if .env.example exists
if [[ ! -f /root/qubinode_navigator/.env.example ]]; then
    log_error ".env.example file not found! Please ensure you have the latest version."
    exit 1
fi

# Create .env from example if it doesn't exist
if [[ ! -f /root/qubinode_navigator/.env ]]; then
    cp /root/qubinode_navigator/.env.example /root/qubinode_navigator/.env
    log_success "Created .env file from .env.example"
    log_warning "⚠️  IMPORTANT: Edit /root/qubinode_navigator/.env with your configuration before running deployment!"
else
    log_info "Existing .env file found (backed up to $BACKUP_DIR)"
    log_warning "⚠️  IMPORTANT: Review and update /root/qubinode_navigator/.env if needed!"
fi

# =============================================================================
# FINAL SUMMARY
# =============================================================================

echo ""
echo "============================================================================="
echo "                           CLEANUP COMPLETED"
echo "============================================================================="
echo ""
log_success "✅ Pre-deployment cleanup completed successfully!"
echo ""
log_info "📁 Backup Location: $BACKUP_DIR"
log_info "📋 Files backed up:"
ls -la "$BACKUP_DIR" | tail -n +2 | while read line; do
    echo "   - $(echo $line | awk '{print $9}')"
done

echo ""
log_info "🚀 Next Steps:"
echo "   1. Review and edit /root/qubinode_navigator/.env with your configuration"
echo "   2. Ensure required variables are set (QUBINODE_DOMAIN, QUBINODE_ADMIN_USER, etc.)"
echo "   3. Run the deployment: ./deploy-qubinode.sh"
echo ""
log_info "🆘 If something goes wrong:"
echo "   - Your backups are in: $BACKUP_DIR"
echo "   - SSH keys backed up to: $BACKUP_DIR/ssh_backup"
echo "   - Original .env backed up to: $BACKUP_DIR/.env"
echo ""
log_warning "⚠️  CRITICAL: Do not delete the backup directory until deployment is successful!"

echo ""
echo "Ready for deployment! 🎉"
