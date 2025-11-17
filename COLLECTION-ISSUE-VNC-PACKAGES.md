# Collection Issue: VNC/RDP Packages Not Available on CentOS Stream 10

**Collection**: `tosin2013.qubinode_kvmhost_setup_collection`  
**Version**: 0.9.35  
**Date Reported**: 2025-11-14  
**Environment**: CentOS Stream 10 (Coughlan)  
**Deployment Mode**: Ansible Navigator with `--execution-environment false`

---

## Issue Summary

The `kvmhost_setup` role fails when attempting to install `tigervnc-server` and `xrdp` packages on CentOS Stream 10, as these packages are not yet available in the CentOS Stream 10 repositories.

---

## Error Details

### Error Message
```
TASK [tosin2013.qubinode_kvmhost_setup_collection.kvmhost_setup : Install tigervnc-server and xrdp packages]
fatal: [control]: FAILED! => {
  "changed": false,
  "failures": [
    "No package tigervnc-server available.",
    "No package xrdp available."
  ],
  "msg": "Failed to install some of the specified packages",
  "rc": 1,
  "results": []
}
```

### Task That Failed
- **Task**: `Install tigervnc-server and xrdp packages`
- **Role**: `tosin2013.qubinode_kvmhost_setup_collection.kvmhost_setup`
- **Packages**: `tigervnc-server`, `xrdp`

---

## Root Cause Analysis

CentOS Stream 10 is a next-generation development platform that is still building out its package ecosystem. The VNC and RDP packages (`tigervnc-server` and `xrdp`) are not yet available in the official repositories.

### Package Availability Check
```bash
$ dnf search tigervnc xrdp
Last metadata expiration check: 0:02:23 ago on Fri 14 Nov 2025 04:48:40 PM CET.
No matches found.
```

### Available Repositories
```
repo id                                                    repo name
appstream                                                  CentOS Stream 10 - AppStream
baseos                                                     CentOS Stream 10 - BaseOS
epel                                                       Extra Packages for Enterprise Linux 10 - x86_64
extras-common                                              CentOS Stream 10 - Extras packages
```

---

## Affected File

The issue is likely in one of these files:
```
roles/kvmhost_setup/tasks/vnc_setup.yml
roles/kvmhost_setup/tasks/remote_access.yml
roles/kvmhost_setup/tasks/main.yml
```

Or in the package list variables:
```
roles/kvmhost_setup/defaults/main.yml
roles/kvmhost_setup/vars/main.yml
roles/kvmhost_setup/vars/CentOS-10.yml (if exists)
```

---

## Deployment Progress Before Failure

The deployment successfully completed **90 tasks** before failing (up from 79 with the firewall fix):

### Successfully Completed Phases
1. ✅ OS Detection (CentOS Stream 10 correctly identified)
2. ✅ RHEL version compatibility check
3. ✅ Package installation (base packages)
4. ✅ Service configuration
5. ✅ Shell configuration for lab-user
6. ✅ **Firewall role configuration** (fixed in 0.9.35!)
7. ✅ Cockpit setup
8. ✅ Network configuration
9. ❌ **FAILED**: VNC/RDP package installation

---

## Suggested Fixes

### Option 1: Add CentOS Stream 10 Conditional (Recommended)

Add OS version detection to skip VNC/RDP installation on CentOS Stream 10:

```yaml
- name: Install tigervnc-server and xrdp packages
  ansible.builtin.dnf:
    name:
      - tigervnc-server
      - xrdp
    state: present
  when:
    - enable_vnc | default(true) | bool
    - not (kvmhost_is_centos_stream and kvmhost_os_major_version|int >= 10)
```

### Option 2: Add enable_vnc Variable Control

Allow users to disable VNC/RDP installation via variable:

```yaml
- name: Install tigervnc-server and xrdp packages
  ansible.builtin.dnf:
    name:
      - tigervnc-server
      - xrdp
    state: present
  when: enable_vnc | default(true) | bool
```

### Option 3: Use Alternative Packages for CentOS Stream 10

If alternative packages become available, use conditional package selection:

```yaml
- name: Set VNC package names based on OS version
  ansible.builtin.set_fact:
    vnc_packages: >-
      {{
        ['tigervnc-server', 'xrdp']
        if not (kvmhost_is_centos_stream and kvmhost_os_major_version|int >= 10)
        else ['alternative-vnc-package']
      }}

- name: Install VNC packages
  ansible.builtin.dnf:
    name: "{{ vnc_packages }}"
    state: present
  when:
    - enable_vnc | default(true) | bool
    - vnc_packages | length > 0
```

### Option 4: Make Task Non-Fatal with Warning

Allow deployment to continue with a warning:

```yaml
- name: Install tigervnc-server and xrdp packages
  ansible.builtin.dnf:
    name:
      - tigervnc-server
      - xrdp
    state: present
  when: enable_vnc | default(true) | bool
  failed_when: false
  register: vnc_install_result

- name: Warn if VNC packages unavailable
  ansible.builtin.debug:
    msg: >-
      WARNING: VNC/RDP packages are not available on {{ ansible_distribution }} {{ ansible_distribution_version }}.
      Remote desktop access will not be configured.
  when:
    - vnc_install_result is defined
    - vnc_install_result.failed | default(false)
```

---

## Workaround for Users

Until this is fixed in the collection, users can disable VNC/RDP installation:

```yaml
# In inventory group_vars/all.yml
enable_vnc: false
```

Or manually install alternative remote access solutions after deployment:

```bash
# Alternative: Use Cockpit for web-based management (already installed)
systemctl enable --now cockpit.socket

# Alternative: Use SSH X11 forwarding
# Edit /etc/ssh/sshd_config:
# X11Forwarding yes
systemctl restart sshd
```

---

## CentOS Stream 10 Context

### About CentOS Stream 10
- **Release**: Next-generation development platform (Coughlan)
- **Status**: Active development, package ecosystem still growing
- **Relationship**: Development preview of RHEL 10
- **Timeline**: Some packages may not be available until closer to RHEL 10 GA

### Package Availability Timeline
- **Current**: Many RHEL 8/9 packages not yet available
- **Expected**: Package availability will improve as CentOS Stream 10 matures
- **Recommendation**: Add conditional logic for CentOS Stream 10 compatibility

---

## Testing Recommendations

1. **Add CentOS Stream 10 to CI/CD Testing**
   - Test package availability across all supported OS versions
   - Add matrix testing for RHEL 8, 9, 10 and CentOS Stream 8, 9, 10

2. **Package Availability Checks**
   - Add pre-flight checks for package availability
   - Provide clear error messages when packages are unavailable
   - Suggest alternatives when primary packages are missing

3. **Version-Specific Package Lists**
   - Create OS version-specific package lists
   - Use conditional package selection based on OS version
   - Document package differences between OS versions

4. **Graceful Degradation**
   - Allow deployment to continue when optional packages are unavailable
   - Log warnings instead of failing for non-critical packages
   - Provide post-deployment instructions for manual installation

---

## Impact

**Severity**: Medium  
**Impact**: Blocks one-command bootstrap deployment on CentOS Stream 10 when VNC/RDP is required

**Affected Users**:
- Users deploying on CentOS Stream 10
- Users requiring remote desktop access (VNC/RDP)
- Early adopters testing RHEL 10 compatibility

**Workaround Available**: Yes (disable VNC or use alternative remote access)

---

## Related Issues

### Previously Fixed in 0.9.35
- ✅ Firewall role compatibility issue (fixed)
- ✅ Variable naming for firewall service configuration (fixed)

### Current Issue
- ❌ VNC/RDP package availability on CentOS Stream 10

---

## Additional Context

### Collection Version History
- **0.9.28**: Last version tested with execution environment
- **0.9.34**: Firewall role compatibility issue
- **0.9.35**: Firewall role fixed, VNC package availability issue discovered

### Deployment Statistics
- **Tasks Completed**: 90 of ~100
- **Success Rate**: ~90% completion before VNC package failure
- **Previous Failures Fixed**: 3 (OS detection, user variables, firewall role)

---

## Recommended Solution Priority

1. **High Priority**: Add `enable_vnc` variable control (Option 2)
2. **High Priority**: Add CentOS Stream 10 conditional skip (Option 1)
3. **Medium Priority**: Add graceful degradation with warnings (Option 4)
4. **Low Priority**: Research alternative packages for CentOS Stream 10 (Option 3)

---

## Testing Checklist

- [ ] Test on RHEL 8 (packages should be available)
- [ ] Test on RHEL 9 (packages should be available)
- [ ] Test on CentOS Stream 8 (packages should be available)
- [ ] Test on CentOS Stream 9 (packages should be available)
- [ ] Test on CentOS Stream 10 (packages currently unavailable)
- [ ] Test with `enable_vnc: false` on all platforms
- [ ] Test with `enable_vnc: true` on platforms with package availability
- [ ] Verify deployment continues successfully when VNC is disabled
- [ ] Verify appropriate warnings are logged when packages unavailable

---

## Contact

**Reporter**: Deployment automation testing  
**Collection Repository**: https://galaxy.ansible.com/tosin2013/qubinode_kvmhost_setup_collection  
**Related Issue**: VNC/RDP package availability on CentOS Stream 10

---

## Logs

Full deployment log available upon request. Key excerpt:

```
PLAY RECAP *************************************************************
control : ok=90 changed=4 unreachable=0 failed=1 skipped=54 rescued=0 ignored=1
```

**Last Successful Task**: `Update package cache for Rocky/Alma Linux` (skipped, not applicable)  
**Failed Task**: `Install tigervnc-server and xrdp packages`  
**Next Expected Task**: Additional KVM host configuration tasks
