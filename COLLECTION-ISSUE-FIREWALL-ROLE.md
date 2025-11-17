# Collection Issue: Firewall Role Compatibility Problem

**Collection**: `tosin2013.qubinode_kvmhost_setup_collection`  
**Version**: 0.9.34  
**Date Reported**: 2025-11-14  
**Environment**: CentOS Stream 10 (Coughlan)  
**Deployment Mode**: Ansible Navigator with `--execution-environment false`

---

## Issue Summary

The `kvmhost_setup` role fails when calling the `linux-system-roles.firewall` role due to incorrect variable naming in the firewall configuration task.

---

## Error Details

### Error Message
```
TASK [fedora.linux_system_roles.firewall : Configure firewall]
failed: [control] (item={'ansible.builtin.service': 'cockpit', 'state': 'enabled'}) => {
  "ansible_loop_var": "item",
  "changed": false,
  "item": {
    "ansible.builtin.service": "cockpit",
    "state": "enabled"
  },
  "msg": "One of service, port, source_port, forward_port, masquerade, rich_rule, source, interface, icmp_block, icmp_block_inversion, target, zone, set_default_zone, ipset or firewalld_conf needs to be set"
}
```

### Task That Failed
- **Task**: `Configure firewall` in `fedora.linux_system_roles.firewall` role
- **Location**: Called from `tosin2013.qubinode_kvmhost_setup_collection.kvmhost_setup` role
- **Iteration**: Processing cockpit firewall service configuration

---

## Root Cause Analysis

The collection is passing firewall configuration with the key `ansible.builtin.service` instead of just `service`:

**Current (Incorrect)**:
```yaml
item:
  ansible.builtin.service: 'cockpit'
  state: 'enabled'
```

**Expected (Correct)**:
```yaml
item:
  service: 'cockpit'
  state: 'enabled'
```

The `linux-system-roles.firewall` role expects the parameter name to be `service`, not `ansible.builtin.service`.

---

## Affected File

Based on the collection structure, the issue is likely in:
```
roles/kvmhost_setup/tasks/cockpit_setup.yml
```

Or in the variables/defaults that define firewall services:
```
roles/kvmhost_setup/defaults/main.yml
roles/kvmhost_setup/vars/main.yml
```

---

## Reproduction Steps

1. Install collection version 0.9.34:
   ```bash
   ansible-galaxy collection install tosin2013.qubinode_kvmhost_setup_collection:0.9.34
   ```

2. Install required roles:
   ```bash
   ansible-galaxy role install linux-system-roles.cockpit linux-system-roles.network linux-system-roles.firewall
   ```

3. Run deployment with execution environment disabled:
   ```bash
   ansible-navigator run ansible-navigator/setup_kvmhost.yml \
     --execution-environment false \
     -m stdout
   ```

4. Observe failure at firewall configuration task (task ~79 of deployment)

---

## Environment Context

### System Information
- **OS**: CentOS Stream 10 (Coughlan)
- **Kernel**: (as detected by Ansible)
- **Ansible Navigator**: Running without execution environment container
- **Python**: python3 (CentOS Stream 10 default)

### Installed Roles
- `linux-system-roles.cockpit`: 1.7.1
- `linux-system-roles.network`: 1.17.6
- `linux-system-roles.firewall`: 1.11.2

### Collection Dependencies
From `ansible-builder/requirements.yml`:
```yaml
collections:
  - name: tosin2013.qubinode_kvmhost_setup_collection
    version: "==0.9.34"
  - name: fedora.linux_system_roles
    version: ">=1.20.0"
```

---

## Deployment Progress Before Failure

The deployment successfully completed **79 tasks** before failing:

### Successfully Completed Phases
1. ✅ OS Detection (CentOS Stream 10 correctly identified)
2. ✅ RHEL version compatibility check
3. ✅ Package installation
4. ✅ Service configuration
5. ✅ Shell configuration for lab-user
6. ✅ Firewall role installation and setup
7. ❌ **FAILED**: Firewall service configuration for cockpit

---

## Suggested Fix

### Option 1: Fix Variable Naming (Recommended)

Locate where firewall services are defined (likely in `defaults/main.yml` or the cockpit setup task) and change:

```yaml
# INCORRECT
firewall_services:
  - ansible.builtin.service: cockpit
    state: enabled

# CORRECT
firewall_services:
  - service: cockpit
    state: enabled
```

### Option 2: Update Firewall Role Call

If the variable structure is intentional, update how the firewall role is called to properly map the variables.

---

## Workaround for Users

Until this is fixed in the collection, users can disable cockpit setup:

```yaml
# In inventory group_vars/all.yml
enable_cockpit: false
```

Then manually install and configure cockpit after deployment:
```bash
dnf install -y cockpit cockpit-machines
systemctl enable --now cockpit.socket
firewall-cmd --permanent --add-service=cockpit
firewall-cmd --reload
```

---

## Additional Context

### Previous Deployment Fixes Applied
1. **OS Detection Issue**: Added `--execution-environment false` to run on CentOS Stream 10 host instead of Fedora 41 container
2. **Missing Variables**: Added `users: [lab-user]` to inventory
3. **User Account**: Changed `admin_user` from `admin` to `lab-user` (actual system user)
4. **Missing Roles**: Added automatic installation of `linux-system-roles.*` roles in deployment script

### Collection Version History
- **0.9.28**: Last known working version (with execution environment)
- **0.9.31**: First version tested without execution environment
- **0.9.34**: Current version with firewall role compatibility issue

---

## Impact

**Severity**: High  
**Impact**: Blocks one-command bootstrap deployment on CentOS Stream 10 when running without execution environment

**Affected Users**:
- Users deploying on CentOS Stream 10
- Users running without Ansible Navigator execution environment
- Users requiring cockpit web console

---

## Testing Recommendations

1. Test firewall role integration with `linux-system-roles.firewall` versions 1.10.x and 1.11.x
2. Verify variable naming matches firewall role expectations
3. Add integration tests for cockpit setup with firewall configuration
4. Test both with and without execution environment containers

---

## Contact

**Reporter**: Deployment automation testing  
**Collection Repository**: https://galaxy.ansible.com/tosin2013/qubinode_kvmhost_setup_collection  
**Related Issue**: Firewall role variable naming incompatibility

---

## Logs

Full deployment log available upon request. Key excerpt:

```
PLAY RECAP *************************************************************
control : ok=79 changed=4 unreachable=0 failed=1 skipped=44 rescued=0 ignored=1
```

**Last Successful Task**: `fedora.linux_system_roles.firewall : Enable and start firewalld service`  
**Failed Task**: `fedora.linux_system_roles.firewall : Configure firewall`
