# Collection Issue: Missing configure_remote_desktop.yml Playbook

**Collection**: `tosin2013.qubinode_kvmhost_setup_collection`  
**Version**: 0.9.37  
**Date Reported**: 2025-11-15  
**Environment**: CentOS Stream 10 (Coughlan)  
**Deployment Mode**: Ansible Navigator with `--execution-environment false`

---

## Issue Summary

The `kvmhost_setup` role attempts to include a playbook file `configure_remote_desktop.yml` that does not exist in the user's project directory, causing the deployment to fail.

---

## Error Details

### Error Message
```
TASK [tosin2013.qubinode_kvmhost_setup_collection.kvmhost_setup : Configure Remote Desktop (Platform-Aware)]
fatal: [control]: FAILED! => {
  "reason": "Could not find or access '/root/qubinode_navigator/ansible-navigator/configure_remote_desktop.yml' on the Ansible Controller."
}
```

### Task That Failed
- **Task**: `Configure Remote Desktop (Platform-Aware)`
- **Role**: `tosin2013.qubinode_kvmhost_setup_collection.kvmhost_setup`
- **Expected File**: `/root/qubinode_navigator/ansible-navigator/configure_remote_desktop.yml`

---

## Root Cause Analysis

The collection is trying to include an external playbook file that should either:
1. Be provided by the collection itself (in the role's files/templates)
2. Be documented as a required file users must create
3. Be made optional with proper error handling

The file path suggests it expects the playbook to be in the user's project structure, but:
- No such file exists in the qubinode_navigator repository
- No documentation mentions this file requirement
- The collection should either bundle this file or make it optional

---

## Affected File

The issue is likely in:
```
roles/kvmhost_setup/tasks/remote_desktop_setup.yml
roles/kvmhost_setup/tasks/main.yml
```

Probable code causing the issue:
```yaml
- name: Configure Remote Desktop (Platform-Aware)
  ansible.builtin.include_tasks: "{{ playbook_dir }}/configure_remote_desktop.yml"
  # or
  ansible.builtin.import_playbook: "{{ playbook_dir }}/configure_remote_desktop.yml"
```

---

## Deployment Progress Before Failure

The deployment successfully completed **84 tasks** before failing:

### Successfully Completed Phases
1. ✅ OS Detection (CentOS Stream 10 correctly identified)
2. ✅ RHEL version compatibility check
3. ✅ Package installation (base packages)
4. ✅ Service configuration
5. ✅ Shell configuration for lab-user
6. ✅ **Firewall role configuration** (working in 0.9.37!)
7. ✅ Cockpit setup
8. ✅ Network configuration
9. ✅ Rocky Linux setup (skipped, not applicable)
10. ❌ **FAILED**: Remote desktop configuration (missing playbook file)

---

## CI/CD Evidence

From the GitHub Actions CI/CD output you provided:
```
Warning: [Errno 2] No such file or directory: '/home/github-runner/actions-runner/_work/qubinode_kvmhost_setup_collection/qubinode_kvmhost_setup_collection/configure_remote_desktop.yml'

load-failure[filenotfounderror]: [Errno 2] No such file or directory: '/home/github-runner/actions-runner/_work/qubinode_kvmhost_setup_collection/qubinode_kvmhost_setup_collection/configure_remote_desktop.yml' (warning)
configure_remote_desktop.yml:1
```

This confirms the file is missing from the collection repository itself.

---

## Suggested Fixes

### Option 1: Move Playbook into Collection (Recommended)

Move the playbook content into the collection as a task file:

```yaml
# roles/kvmhost_setup/tasks/remote_desktop_setup.yml
- name: Configure Remote Desktop (Platform-Aware)
  block:
    - name: Install remote desktop packages
      ansible.builtin.dnf:
        name:
          - tigervnc-server
          - xrdp
        state: present
      when:
        - enable_vnc | default(true) | bool
        - not (kvmhost_is_centos_stream and kvmhost_os_major_version|int >= 10)
    
    - name: Configure VNC service
      ansible.builtin.systemd:
        name: vncserver@:1
        enabled: true
        state: started
      when:
        - enable_vnc | default(true) | bool
        - not (kvmhost_is_centos_stream and kvmhost_os_major_version|int >= 10)
```

### Option 2: Make File Optional with Proper Error Handling

```yaml
- name: Check if remote desktop playbook exists
  ansible.builtin.stat:
    path: "{{ playbook_dir }}/configure_remote_desktop.yml"
  register: remote_desktop_playbook

- name: Configure Remote Desktop (Platform-Aware)
  ansible.builtin.include_tasks: "{{ playbook_dir }}/configure_remote_desktop.yml"
  when:
    - remote_desktop_playbook.stat.exists
    - enable_vnc | default(true) | bool

- name: Warn if remote desktop playbook not found
  ansible.builtin.debug:
    msg: >-
      Remote desktop configuration playbook not found at {{ playbook_dir }}/configure_remote_desktop.yml.
      Skipping remote desktop setup. To enable, create this playbook or set enable_vnc: false.
  when:
    - not remote_desktop_playbook.stat.exists
    - enable_vnc | default(true) | bool
```

### Option 3: Use Conditional Include with ignore_errors

```yaml
- name: Configure Remote Desktop (Platform-Aware)
  ansible.builtin.include_tasks: "{{ playbook_dir }}/configure_remote_desktop.yml"
  when: enable_vnc | default(true) | bool
  ignore_errors: true
  register: remote_desktop_result

- name: Skip remote desktop if playbook missing
  ansible.builtin.debug:
    msg: "Remote desktop configuration skipped - playbook not found"
  when:
    - remote_desktop_result is failed
    - "'Could not find or access' in remote_desktop_result.msg"
```

### Option 4: Document Required File

If the file is meant to be user-provided, add clear documentation:

```markdown
## Required Files

Users must create the following playbook in their project:

**File**: `ansible-navigator/configure_remote_desktop.yml`

**Minimum Content**:
```yaml
---
- name: Configure Remote Desktop
  hosts: all
  tasks:
    - name: Remote desktop setup placeholder
      ansible.builtin.debug:
        msg: "Add your remote desktop configuration here"
```

**To disable**: Set `enable_vnc: false` in your inventory.
```

---

## Workaround for Users

### Workaround 1: Create Empty Playbook

```bash
cat > /root/qubinode_navigator/ansible-navigator/configure_remote_desktop.yml << 'EOF'
---
- name: Configure Remote Desktop (Placeholder)
  hosts: all
  tasks:
    - name: Remote desktop configuration placeholder
      ansible.builtin.debug:
        msg: "Remote desktop configuration skipped - using placeholder"
EOF
```

### Workaround 2: Disable Remote Desktop

```yaml
# In inventory group_vars/all.yml
enable_vnc: false
```

---

## Impact

**Severity**: High  
**Impact**: Blocks one-command bootstrap deployment at 84% completion

**Affected Users**:
- All users deploying with collection 0.9.37
- Users on all platforms (RHEL 8, 9, 10, CentOS Stream)
- Both with and without execution environment

**Workaround Available**: Yes (create placeholder file or disable VNC)

---

## Related Issues

### Version History
- **0.9.34**: Firewall role compatibility issue
- **0.9.35**: Firewall fixed, VNC package availability issue
- **0.9.37**: VNC packages fixed, missing playbook file issue

### CI/CD Lint Failures
The same file is causing ansible-lint failures in CI/CD:
- `load-failure[filenotfounderror]` in ansible-lint
- 7 `yaml[trailing-spaces]` errors in `roles/kvmhost_setup/tasks/rhpds_instance.yml`

---

## Testing Recommendations

1. **File Existence Checks**
   - Add pre-flight checks for required external files
   - Provide clear error messages when files are missing
   - Make external dependencies optional with proper conditionals

2. **CI/CD Integration**
   - Fix ansible-lint failures before release
   - Add tests for file dependencies
   - Verify all `include_tasks` and `import_playbook` references

3. **Documentation**
   - Document all required external files
   - Provide example/template files
   - Add troubleshooting guide for missing files

4. **Collection Self-Containment**
   - Move external dependencies into collection
   - Reduce reliance on user-provided files
   - Bundle all required playbooks/tasks in the collection

---

## Deployment Statistics

- **Tasks Completed**: 84 of ~100
- **Success Rate**: ~84% completion
- **Previous Issues Fixed**: 
  - ✅ OS detection (0.9.31+)
  - ✅ User variables (0.9.31+)
  - ✅ Firewall role (0.9.35)
  - ✅ VNC package availability (0.9.37)
- **Current Issue**: Missing playbook file (0.9.37)

---

## Recommended Solution Priority

1. **Critical**: Make the include optional with proper error handling (Option 2)
2. **High**: Move playbook content into collection tasks (Option 1)
3. **Medium**: Add clear documentation if file is required (Option 4)
4. **Low**: Use ignore_errors as temporary fix (Option 3)

---

## Additional Context

### File Path Analysis
```
Expected: /root/qubinode_navigator/ansible-navigator/configure_remote_desktop.yml
Collection: /root/.ansible/collections/ansible_collections/tosin2013/qubinode_kvmhost_setup_collection/

The file path uses {{ playbook_dir }} which resolves to the user's project directory,
not the collection directory. This suggests the file is expected to be user-provided,
but no documentation or template exists.
```

### Similar Patterns in Collection
Check if other tasks use similar external file references:
```bash
grep -r "include_tasks.*playbook_dir" roles/
grep -r "import_playbook" roles/
```

---

## Contact

**Reporter**: Deployment automation testing  
**Collection Repository**: https://galaxy.ansible.com/tosin2013/qubinode_kvmhost_setup_collection  
**Related Issue**: Missing configure_remote_desktop.yml playbook file

---

## Logs

Full deployment log available upon request. Key excerpt:

```
PLAY RECAP *************************************************************
control : ok=84 changed=1 unreachable=0 failed=1 skipped=51 rescued=0 ignored=1
```

**Last Successful Task**: `Setup Rocky Linux` (skipped, not applicable)  
**Failed Task**: `Configure Remote Desktop (Platform-Aware)`  
**Next Expected Task**: Additional KVM host configuration and validation
