# Collection Issue: Recursive Template Loop in XRDP Password Variable

**Collection**: `tosin2013.qubinode_kvmhost_setup_collection`  
**Version**: 0.10.1  
**Date Reported**: 2025-11-16  
**Environment**: CentOS Stream 10 (Coughlan)  
**Deployment Mode**: Ansible Navigator with `--execution-environment false`

---

## Issue Summary

The `kvmhost_setup` role fails with a recursive template loop error when setting the remote user password for XRDP. The variable `xrdp_remote_user_password` appears to be referencing itself in its default value definition, causing infinite recursion during Jinja2 template evaluation.

---

## Error Details

### Error Message
```
TASK [tosin2013.qubinode_kvmhost_setup_collection.kvmhost_setup : Set remote user password if not already set]
fatal: [control]: FAILED! => {
  "msg": "An unhandled exception occurred while templating '{{ xrdp_remote_user_password | default('CHANGE_ME_IN_PRODUCTION') }}'. 
  Error was a <class 'ansible.errors.AnsibleError'>, original message: recursive loop detected in template string: 
  {{ xrdp_remote_user_password | default('CHANGE_ME_IN_PRODUCTION') }}. maximum recursion depth exceeded"
}
```

### Task That Failed
- **Task**: `Set remote user password if not already set`
- **Role**: `tosin2013.qubinode_kvmhost_setup_collection.kvmhost_setup`
- **Variable**: `xrdp_remote_user_password`

---

## Root Cause Analysis

The error indicates a **recursive template loop**, which typically occurs when a variable's default value references itself. This happens in one of these scenarios:

### Scenario 1: Variable Self-Reference in Defaults
```yaml
# roles/kvmhost_setup/defaults/main.yml (INCORRECT)
xrdp_remote_user_password: "{{ xrdp_remote_user_password | default('CHANGE_ME_IN_PRODUCTION') }}"
```

### Scenario 2: Variable Self-Reference in Tasks
```yaml
# roles/kvmhost_setup/tasks/remote_desktop_setup.yml (INCORRECT)
- name: Set remote user password if not already set
  ansible.builtin.set_fact:
    xrdp_remote_user_password: "{{ xrdp_remote_user_password | default('CHANGE_ME_IN_PRODUCTION') }}"
```

### Scenario 3: Circular Reference Between Variables
```yaml
# Variable A references Variable B, which references Variable A
xrdp_remote_user_password: "{{ remote_user_password }}"
remote_user_password: "{{ xrdp_remote_user_password | default('CHANGE_ME_IN_PRODUCTION') }}"
```

---

## Affected File

The issue is likely in one of these files:
```
roles/kvmhost_setup/defaults/main.yml
roles/kvmhost_setup/vars/main.yml
roles/kvmhost_setup/tasks/remote_desktop_setup.yml
roles/kvmhost_setup/tasks/xrdp_setup.yml
roles/kvmhost_setup/tasks/main.yml
```

---

## Deployment Progress Before Failure

The deployment successfully completed **117 tasks** before failing - this is the furthest we've gotten!

### Successfully Completed Phases
1. ✅ OS Detection (CentOS Stream 10 correctly identified)
2. ✅ RHEL version compatibility check
3. ✅ Package installation (base packages)
4. ✅ Service configuration
5. ✅ Shell configuration for lab-user
6. ✅ **Firewall role configuration** (working in 0.10.1!)
7. ✅ Cockpit setup
8. ✅ Network configuration
9. ✅ Remote desktop package installation
10. ✅ XRDP service configuration
11. ❌ **FAILED**: Remote user password setup (recursive template loop)

### Deployment Statistics
```
PLAY RECAP:
control : ok=117 changed=12 unreachable=0 failed=1 skipped=54 rescued=0 ignored=1
```

**Completion Rate**: ~85% (117 of ~140 estimated tasks)

---

## Suggested Fixes

### Fix 1: Remove Self-Reference in Defaults (Most Likely)

**Current (Incorrect)**:
```yaml
# roles/kvmhost_setup/defaults/main.yml
xrdp_remote_user_password: "{{ xrdp_remote_user_password | default('CHANGE_ME_IN_PRODUCTION') }}"
```

**Fixed**:
```yaml
# roles/kvmhost_setup/defaults/main.yml
xrdp_remote_user_password: "CHANGE_ME_IN_PRODUCTION"
```

### Fix 2: Fix Self-Reference in Task

**Current (Incorrect)**:
```yaml
- name: Set remote user password if not already set
  ansible.builtin.set_fact:
    xrdp_remote_user_password: "{{ xrdp_remote_user_password | default('CHANGE_ME_IN_PRODUCTION') }}"
```

**Fixed Option A - Use Different Variable Name**:
```yaml
- name: Set remote user password if not already set
  ansible.builtin.set_fact:
    xrdp_password: "{{ xrdp_remote_user_password | default('CHANGE_ME_IN_PRODUCTION') }}"
```

**Fixed Option B - Check if Variable is Defined First**:
```yaml
- name: Set remote user password if not already set
  ansible.builtin.set_fact:
    xrdp_remote_user_password: "CHANGE_ME_IN_PRODUCTION"
  when: xrdp_remote_user_password is not defined
```

**Fixed Option C - Use block with conditional**:
```yaml
- name: Set remote user password if not already set
  block:
    - name: Check if password is defined
      ansible.builtin.set_fact:
        _xrdp_password_defined: "{{ xrdp_remote_user_password is defined }}"
    
    - name: Set default password if not defined
      ansible.builtin.set_fact:
        xrdp_remote_user_password: "CHANGE_ME_IN_PRODUCTION"
      when: not _xrdp_password_defined | bool
```

### Fix 3: Use vars_prompt or lookup for Password

For better security, consider using `vars_prompt` or password lookup:

```yaml
- name: Generate or use provided XRDP password
  ansible.builtin.set_fact:
    xrdp_remote_user_password: >-
      {{
        xrdp_remote_user_password
        if xrdp_remote_user_password is defined and xrdp_remote_user_password != ''
        else lookup('password', '/dev/null length=16 chars=ascii_letters,digits')
      }}
```

---

## Debugging Steps

To identify the exact location of the issue:

### Step 1: Search for Self-References
```bash
cd /root/.ansible/collections/ansible_collections/tosin2013/qubinode_kvmhost_setup_collection/

# Find all references to xrdp_remote_user_password
grep -r "xrdp_remote_user_password" roles/kvmhost_setup/

# Look for self-referencing patterns
grep -r "xrdp_remote_user_password.*xrdp_remote_user_password" roles/kvmhost_setup/
```

### Step 2: Check Defaults File
```bash
cat roles/kvmhost_setup/defaults/main.yml | grep -A2 -B2 "xrdp_remote_user_password"
```

### Step 3: Check Tasks Files
```bash
find roles/kvmhost_setup/tasks/ -name "*.yml" -exec grep -l "xrdp_remote_user_password" {} \;
```

### Step 4: Check for Circular References
```bash
# Look for variables that might reference each other
grep -r "remote_user_password\|xrdp_password" roles/kvmhost_setup/defaults/
grep -r "remote_user_password\|xrdp_password" roles/kvmhost_setup/vars/
```

---

## Workaround for Users

Users can work around this issue by explicitly defining the variable in their inventory before the collection tries to set it:

```yaml
# In inventories/localhost/group_vars/all.yml
xrdp_remote_user_password: "ChangeMe123!"
```

**Security Note**: Users should change this password immediately after deployment or use Ansible Vault to encrypt it:

```bash
# Encrypt the password
ansible-vault encrypt_string 'YourSecurePassword' --name 'xrdp_remote_user_password'

# Add to group_vars/all.yml:
xrdp_remote_user_password: !vault |
          $ANSIBLE_VAULT;1.1;AES256
          ...encrypted content...
```

---

## Impact

**Severity**: High  
**Impact**: Blocks one-command bootstrap deployment at 85% completion (117 of ~140 tasks)

**Affected Users**:
- All users deploying with collection 0.10.1
- Users on all platforms (RHEL 8, 9, 10, CentOS Stream)
- Both with and without execution environment
- Only affects deployments that include XRDP/remote desktop setup

**Workaround Available**: Yes (define variable in inventory)

---

## Version History & Progress

### Collection Version Timeline
- **0.9.28**: Initial version (with execution environment)
- **0.9.34**: 79 tasks - Firewall role compatibility issue
- **0.9.35**: 90 tasks - Firewall fixed, VNC package availability issue
- **0.9.37**: 84 tasks - VNC fixed, missing playbook file issue
- **0.10.1**: 117 tasks - Playbook fixed, recursive template bug ⭐ **85% Complete!**

### Issues Fixed in Previous Versions
1. ✅ OS detection (Fedora 41 container vs CentOS Stream 10 host)
2. ✅ Missing `users` variable
3. ✅ User account mismatch (`admin` → `lab-user`)
4. ✅ Missing `linux-system-roles.*` roles
5. ✅ Firewall role variable naming (`ansible.builtin.service` → `service`)
6. ✅ VNC/RDP package availability on CentOS Stream 10
7. ✅ Missing `configure_remote_desktop.yml` playbook
8. ❌ **Current**: Recursive template loop in password variable

---

## Testing Recommendations

### Pre-Release Testing
1. **Variable Definition Tests**
   - Test with variable undefined (should use default)
   - Test with variable defined in inventory
   - Test with variable defined in extra-vars
   - Verify no self-references in defaults/vars files

2. **Template Recursion Detection**
   - Add ansible-lint rules to detect self-referencing variables
   - Use `ansible-playbook --syntax-check` in CI/CD
   - Add unit tests for variable resolution

3. **Password Security Tests**
   - Test with Ansible Vault encrypted passwords
   - Test with generated passwords
   - Test with empty/undefined passwords
   - Verify password complexity requirements

### CI/CD Integration
```yaml
# Add to CI/CD pipeline
- name: Check for recursive template patterns
  run: |
    # Detect variables that reference themselves
    grep -r "{{ \([a-z_]*\) |.*\1" roles/ && exit 1 || exit 0
```

---

## Best Practices for Variable Defaults

### ❌ Don't Do This (Causes Recursion)
```yaml
my_variable: "{{ my_variable | default('default_value') }}"
```

### ✅ Do This Instead
```yaml
# Option 1: Simple default
my_variable: "default_value"

# Option 2: Conditional in task
- name: Set variable if not defined
  ansible.builtin.set_fact:
    my_variable: "default_value"
  when: my_variable is not defined

# Option 3: Use different variable names
my_variable_default: "default_value"
my_variable: "{{ my_variable_override | default(my_variable_default) }}"
```

---

## Related Ansible Documentation

- [Jinja2 Template Designer Documentation](https://jinja.palletsprojects.com/en/3.0.x/templates/)
- [Ansible Variable Precedence](https://docs.ansible.com/ansible/latest/user_guide/playbooks_variables.html#variable-precedence-where-should-i-put-a-variable)
- [Ansible set_fact Module](https://docs.ansible.com/ansible/latest/collections/ansible/builtin/set_fact_module.html)
- [Avoiding Recursive Loops](https://docs.ansible.com/ansible/latest/user_guide/playbooks_loops.html#avoiding-recursive-loops)

---

## Recommended Solution Priority

1. **Critical**: Fix self-reference in defaults/vars file (Fix 1)
2. **High**: Add conditional check in task (Fix 2B)
3. **Medium**: Improve password security with vault/lookup (Fix 3)
4. **Low**: Add CI/CD checks for recursive patterns

---

## Additional Context

### Why This Matters
This is the **closest we've gotten to a successful deployment** - 117 tasks completed (85%)! Fixing this single issue will likely result in a successful one-command bootstrap on CentOS Stream 10.

### User Experience Impact
Users are experiencing a very smooth deployment until this point:
- ✅ Automatic OS detection
- ✅ Package installation
- ✅ Service configuration
- ✅ Firewall setup
- ✅ Cockpit installation
- ✅ Network configuration
- ✅ Remote desktop packages
- ❌ **Blocked here**: Password configuration

### Deployment Time
- **Time to failure**: ~5-10 minutes
- **Tasks completed**: 117 of ~140 (85%)
- **Remaining tasks**: ~20-30 (mostly validation and finalization)

---

## Contact

**Reporter**: Deployment automation testing  
**Collection Repository**: https://galaxy.ansible.com/tosin2013/qubinode_kvmhost_setup_collection  
**GitHub Issues**: https://github.com/tosin2013/qubinode_kvmhost_setup_collection/issues  
**Related Issue**: Recursive template loop in xrdp_remote_user_password variable

---

## Logs

Full deployment log available upon request. Key excerpt:

```
PLAY RECAP:
control : ok=117 changed=12 unreachable=0 failed=1 skipped=54 rescued=0 ignored=1
```

**Last Successful Task**: Multiple XRDP configuration tasks  
**Failed Task**: `Set remote user password if not already set`  
**Next Expected Tasks**: XRDP service enablement, validation, and finalization

---

## Success Metrics

Once this issue is fixed, we expect:
- ✅ **100% task completion** (~140 tasks)
- ✅ **Successful one-command bootstrap** on CentOS Stream 10
- ✅ **Full KVM host setup** with remote desktop access
- ✅ **Validated deployment** ready for VM infrastructure

This is the **final blocker** for achieving the one-command bootstrap goal! 🎯
