# Issues Found in qubinode_kvmhost_setup_collection v0.10.4

**Upstream Repository**: https://github.com/Qubinode/qubinode_kvmhost_setup_collection  
**Collection**: `tosin2013.qubinode_kvmhost_setup_collection:0.10.4`  
**Tested On**: CentOS Stream 10 (Coughlan)  
**Date**: November 18, 2025

---

## Issue 1: 🐛 HIGH PRIORITY - Broken Conditional Syntax in gpg_verification.yml

### Summary
Deployment fails with "Conditionals must have a boolean result" error in GPG verification task.

### Location
- **File**: `roles/kvmhost_setup/tasks/gpg_verification.yml`
- **Line**: 129

### Error Message
```
[ERROR]: Task failed: Conditional result (True) was derived from value of type 'str' at 
'/root/.ansible/collections/ansible_collections/tosin2013/qubinode_kvmhost_setup_collection/roles/kvmhost_setup/tasks/gpg_verification.yml:129:7'. 
Conditionals must have a boolean result.

Task failed.
Origin: /root/.ansible/collections/ansible_collections/tosin2013/qubinode_kvmhost_setup_collection/roles/kvmhost_setup/tasks/gpg_verification.yml:125:3

125 - name: Skip EPEL GPG verification in container environments
      ^ column 3
```

### Problem Code
```yaml
- name: Skip EPEL GPG verification in container environments
  ansible.builtin.debug:
    msg: Skipping EPEL GPG verification - container environment detected or EPEL not configured
  when:
    - ansible_virtualization_type | default('') in ['container', 'docker', 'podman'] or "'epel' not in
          ^ column 7
```

### Root Cause
The conditional expression on line 129 is incomplete. The `or` statement has no right-hand side operand.

### Impact
- Prevents deployment from completing
- Affects all users on CentOS Stream 10+
- Requires workaround setting `ALLOW_BROKEN_CONDITIONALS=true`

### Suggested Fix
Complete the conditional expression. Example:
```yaml
when:
  - ansible_virtualization_type | default('') in ['container', 'docker', 'podman'] or 
    'epel' not in ansible_facts.packages | default({})
```

### Workaround
Add to `ansible.cfg`:
```ini
[defaults]
ALLOW_BROKEN_CONDITIONALS = true
```

---

## Issue 2: 🐛 MEDIUM PRIORITY - Missing Handler (Case Sensitivity)

### Summary
Tasks attempt to notify `restart libvirtd` (lowercase) but only `Restart libvirtd` (capital R) handler exists.

### Location
- **File**: `roles/kvmhost_setup/handlers/main.yml`

### Error Message
```
[ERROR]: The requested handler 'restart libvirtd' was not found in either the main handlers list nor in the listening handlers list
```

### Problem
Handler names in Ansible are case-sensitive. The handlers file defines:
```yaml
- name: Restart libvirtd    # Capital R
  ansible.builtin.systemd:
    name: libvirtd
    state: restarted
  become: true
```

But tasks call:
```yaml
notify: restart libvirtd    # lowercase r
```

### Impact
- Prevents performance optimization tasks from completing
- Libvirtd service doesn't restart when configuration changes

### Suggested Fix
**Option 1** (Recommended): Standardize to lowercase
```yaml
- name: restart libvirtd
  ansible.builtin.systemd:
    name: libvirtd
    state: restarted
  become: true
```

**Option 2**: Update all `notify` calls to use capital R

### Workaround Applied
Added lowercase handler to `handlers/main.yml`:
```yaml
- name: restart libvirtd
  ansible.builtin.systemd:
    name: libvirtd
    state: restarted
  become: true
```

---

## Issue 3: 📦 MEDIUM PRIORITY - Missing Python Dependency (passlib)

### Summary
Collection uses Ansible's `password_hash` filter without documenting or ensuring `passlib` is installed.

### Location
- **File**: `roles/kvmhost_setup/tasks/configure_remote_user.yml`
- **Line**: 9

### Error Message
```
[ERROR]: Task failed: Finalization of task args for 'ansible.builtin.user' failed: 
Error while resolving value for 'password': The filter plugin 'ansible.builtin.password_hash' failed: 
Unable to encrypt nor hash, passlib must be installed: No module named 'passlib'
```

### Problem Code
```yaml
- name: Set remote user password if not already set
  ansible.builtin.user:
    name: "{{ xrdp_remote_user }}"
    password: "{{ xrdp_remote_user_password | password_hash('sha512') }}"
```

### Root Cause
The `password_hash` Jinja2 filter requires the `passlib` Python library, which is not included in the collection dependencies or documented in requirements.

### Impact
- Fails during remote user configuration
- Prevents RDP/XRDP setup from completing
- Affects all deployments that configure user passwords

### Suggested Fix
**Option 1**: Add to collection dependencies in `galaxy.yml` or `requirements.txt`

**Option 2**: Document in README:
```markdown
## Requirements
- Python 3.6+
- passlib: `pip3 install passlib`
```

**Option 3**: Add pre-task check:
```yaml
- name: Ensure passlib is installed
  ansible.builtin.pip:
    name: passlib
    state: present
```

### Workaround
Install manually before running playbook:
```bash
pip3 install passlib
```

---

## Issue 4: ⚠️ LOW PRIORITY - Multiple Deprecation Warnings

### Summary
Collection uses deprecated `ansible_*` variable format that will break in Ansible 2.24.

### Affected Files
Multiple files across the collection show warnings like:
```
[DEPRECATION WARNING]: INJECT_FACTS_AS_VARS default to `True` is deprecated, 
top-level facts will not be auto injected after the change. 
This feature will be removed from ansible-core version 2.24.
```

### Example Locations
- `roles/kvmhost_setup/tasks/rhel_version_detection.yml:281`
- `roles/kvmhost_setup/tasks/performance_optimization.yml:44`
- `roles/kvmhost_setup/tasks/performance_optimization.yml:65`
- `roles/kvmhost_setup/tasks/setup_gnome_remote_desktop.yml:242`

### Problem Pattern
Current (deprecated):
```yaml
- kvmhost_os_major_version|int >= 8
- ansible_os_family == "RedHat"
- ansible_virtualization_type | default('') in ['container', 'docker', 'podman']
```

### Impact
- Will break when Ansible 2.24 is released
- Currently just warnings, but requires eventual migration

### Suggested Fix
Update all references to use `ansible_facts` dictionary:
```yaml
- ansible_facts['kvmhost_os_major_version']|int >= 8
- ansible_facts['os_family'] == "RedHat"
- ansible_facts['virtualization_type'] | default('') in ['container', 'docker', 'podman']
```

### Timeline
Ansible 2.24 release timeline: TBD (currently warnings only)

---

## Testing Environment

### System Information
- **OS**: CentOS Stream release 10 (Coughlan)
- **Kernel**: Linux 6.12.x
- **Hardware**: 
  - 2x SAMSUNG MZVL2512HCJQ NVMe drives (476.9GB each)
  - RAID1 configuration (md0, md1, md2)
- **Memory**: 64GB
- **Ansible**: 2.16.14
- **Python**: 3.12.11

### Deployment Configuration
- **Method**: localhost deployment with `ansible_connection=local`
- **User**: root
- **Mode**: CICD_PIPELINE=true (non-interactive)
- **Collection Version**: tosin2013.qubinode_kvmhost_setup_collection:0.10.4

### Test Results
✅ **Success after applying workarounds**:
- 120+ tasks completed successfully
- All roles executed: kvmhost_setup, performance optimization, RDP configuration
- Issues only appeared with upstream collection bugs

---

## Recommended Actions for Maintainers

### High Priority (Blocking Issues)
1. ✅ Fix broken conditional in `gpg_verification.yml` line 129
2. ✅ Fix handler case mismatch in `handlers/main.yml`

### Medium Priority (Affects User Experience)
3. ✅ Add passlib to dependencies or documentation
4. ✅ Test collection on CentOS Stream 10 / RHEL 10

### Low Priority (Future Compatibility)
5. ⬜ Migrate all `ansible_*` variables to `ansible_facts["*"]` format
6. ⬜ Update CI/CD pipeline to test against latest Ansible versions

---

## Fixes Applied Locally (Workarounds)

### File: `/root/.ansible/collections/.../handlers/main.yml`
Added lowercase handler:
```yaml
- name: restart libvirtd
  ansible.builtin.systemd:
    name: libvirtd
    state: restarted
  become: true
```

### File: `ansible.cfg`
Added workaround:
```ini
ALLOW_BROKEN_CONDITIONALS = true
```

### File: `deploy-qubinode.sh`
Added auto-installation:
```bash
sudo pip3 install passlib
```

---

## Contact

**Reported By**: Community Testing on CentOS Stream 10  
**Repository**: https://github.com/tosin2013/qubinode_navigator  
**Date**: November 18, 2025

For questions or additional information about these issues, please refer to the deployment logs and testing environment details above.
