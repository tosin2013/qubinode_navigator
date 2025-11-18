# Deployment Fixes Summary for qubinode_navigator

**Date**: November 18, 2025  
**Status**: ✅ All fixes tested and working on CentOS Stream 10

---

## Changes to Commit to qubinode_navigator Repository

### Modified Files

#### 1. `load-variables.py` (Line 259-267)
**Issue**: AttributeError when user selects "0" (Exit) during disk selection  
**Fix**: Added None check before calling .replace()
```python
if use_root_disk is True or disks is None:
    print('No disk selected.')
    inventory['create_libvirt_storage'] = False
    inventory['create_lvm'] = False
    with open(inventory_path, 'w') as f:
        yaml.dump(inventory, f, default_flow_style=False)
    exit(1)
else:
    disks = disks.replace('/dev/', '')
```
**Status**: ✅ Keep this fix permanently

---

#### 2. `deploy-qubinode.sh` (Line 86-90)
**Issue**: Unbound variable errors (QUBINODE_STORAGE_SIZE, etc.)  
**Fix**: Added default values for environment variables
```bash
export QUBINODE_ENABLE_AI_ASSISTANT="${QUBINODE_ENABLE_AI_ASSISTANT:-true}"
export QUBINODE_STORAGE_SIZE="${QUBINODE_STORAGE_SIZE:-100G}"
export QUBINODE_WORKER_NODES="${QUBINODE_WORKER_NODES:-2}"
export QUBINODE_ENABLE_MONITORING="${QUBINODE_ENABLE_MONITORING:-false}"
export QUBINODE_ENABLE_LOGGING="${QUBINODE_ENABLE_LOGGING:-false}"
```
**Status**: ✅ Keep this fix permanently

---

#### 3. `deploy-qubinode.sh` (Line 1425)
**Issue**: configure_environment() overwrites user's .env file  
**Fix**: Commented out the function call
```bash
# configure_environment || exit 1  # Commented out - users should configure .env manually to avoid overwriting
```
**Status**: ✅ Keep this fix permanently

---

#### 4. `deploy-qubinode.sh` (Line 835-840) - NEW
**Issue**: Missing passlib dependency causes password_hash filter to fail  
**Fix**: Auto-install passlib after Python requirements
```bash
# Install passlib for Ansible password_hash filter
log_info "Ensuring passlib is installed for password hashing..."
sudo pip3 install passlib || {
    log_warning "Failed to install passlib, password operations may fail"
}
```
**Status**: ✅ Keep this fix permanently

---

#### 5. `ansible.cfg` (Line 13-15)
**Issue**: Broken conditional in upstream collection  
**Fix**: Added workaround setting
```ini
# Temporarily allow broken conditionals to work around collection bug
allow_world_readable_tmpfiles = true
ALLOW_BROKEN_CONDITIONALS = true
```
**Status**: ⚠️ TEMPORARY - Remove once upstream collection is fixed

---

#### 6. `inventories/localhost/hosts`
**Issue**: SSH authentication failed with lab-user  
**Fix**: Changed to local connection with root
```ini
[control]
control ansible_connection=local ansible_user=root
```
**Status**: ✅ Keep this - best practice for localhost deployment

---

## Git Commit Commands

```bash
cd /root/qubinode_navigator

# Stage the fixed files
git add load-variables.py
git add deploy-qubinode.sh
git add ansible.cfg
git add inventories/localhost/hosts

# Commit with descriptive message
git commit -m "fix: CentOS Stream 10 deployment issues

- Fixed NoneType error in load-variables.py disk selection
- Added default values for unbound variables in deploy-qubinode.sh
- Prevented .env file from being overwritten
- Auto-install passlib dependency for Ansible password_hash filter
- Configure ansible.cfg to work around upstream collection bug
- Set localhost inventory to use local connection

Tested on CentOS Stream 10 with RAID1 configuration.
See UPSTREAM_ISSUES.md for issues to report to upstream collection.
"

# Push to your repository
git push origin main
```

---

## New Files Created (Documentation)

### 1. `UPSTREAM_ISSUES.md`
Detailed report of issues found in `qubinode_kvmhost_setup_collection` v0.10.4.  
**Action**: Share with upstream maintainers at https://github.com/Qubinode/qubinode_kvmhost_setup_collection/issues

### 2. `DEPLOYMENT_FIXES_SUMMARY.md` (this file)
Summary of changes made to qubinode_navigator for successful deployment.

---

## User Documentation - Required .env Configuration

Create or update `/root/qubinode_navigator/.env`:

```bash
# Basic Configuration
QUBINODE_DOMAIN=example.com
QUBINODE_ADMIN_USER=admin
QUBINODE_CLUSTER_NAME=qubinode
QUBINODE_DEPLOYMENT_MODE=production

# CI/CD Configuration - Required for non-interactive deployment
CICD_PIPELINE=true
ENV_USERNAME=lab-user
DOMAIN=example.com
FORWARDER=1.1.1.1
ACTIVE_BRIDGE=false
INTERFACE=enp0s31f6  # ⚠️ Change to your interface (use: ip a)
DISK=skip            # Or specify disk like /dev/nvme0n1

# SSH Configuration
SSH_PASSWORD=YourSecurePassword
SSH_USER=lab-user

# Feature Flags
QUBINODE_ENABLE_AI_ASSISTANT=true
AI_ASSISTANT_PORT=8080
AI_ASSISTANT_VERSION=latest

# Integration
GIT_REPO=https://github.com/tosin2013/qubinode_navigator.git
INVENTORY=localhost
USE_HASHICORP_VAULT=false
```

**Important**: Users MUST create this file before running `./deploy-qubinode.sh`

---

## Testing Results

### Environment
- ✅ CentOS Stream 10 (Coughlan)
- ✅ 2x NVMe drives in RAID1
- ✅ 64GB RAM
- ✅ Ansible 2.16.14
- ✅ Python 3.12.11

### Deployment Results
- ✅ 120+ Ansible tasks completed successfully
- ✅ Non-interactive deployment working
- ✅ KVM host setup completed
- ✅ Performance optimization applied
- ✅ GNOME Remote Desktop (RDP) configured
- ✅ Firewall rules applied
- ✅ All services started

### Time to Complete
- Full deployment: ~15-20 minutes
- No manual intervention required

---

## Next Steps

1. ✅ Commit and push changes to qubinode_navigator
2. ⬜ Create issues in upstream collection repository using UPSTREAM_ISSUES.md
3. ⬜ Update project README with new .env requirements
4. ⬜ Consider adding a `.env.example` file for users
5. ⬜ Add CI/CD testing for CentOS Stream 10

---

## Notes for Future Releases

### When Upstream Collection is Fixed
Remove the workaround from `ansible.cfg`:
```ini
# Remove these lines when collection v0.10.5+ is released
# ALLOW_BROKEN_CONDITIONALS = true
```

### Permanent Improvements
All other fixes should remain as they improve stability and user experience.

---

## Contact & Support

**Repository**: https://github.com/tosin2013/qubinode_navigator  
**Upstream Collection**: https://github.com/Qubinode/qubinode_kvmhost_setup_collection  
**Issues**: Report to respective repositories  
**Documentation**: See docs/ directory for additional guides
