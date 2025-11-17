# CentOS Stream 10 OS Detection Issue in qubinode_kvmhost_setup_collection

## Issue Summary
The `qubinode_kvmhost_setup_collection` Ansible collection incorrectly detects CentOS Stream 10 as "Fedora 41" instead of recognizing it as a supported RHEL-based distribution, causing deployment failures.

## Environment Details
- **OS**: CentOS Stream 10 (Coughlan)
- **Ansible Collection**: qubinode_kvmhost_setup_collection
- **Ansible Navigator**: Using containerized execution
- **Deployment Script**: deploy-qubinode.sh (terminal-based one-shot deployment)

## Error Details

### Error Message
```
fatal: [control]: FAILED! => {
    "changed": false,
    "msg": "Unsupported operating system: Fedora 41\nThis role supports RHEL/CentOS/CentOS Stream/Rocky/AlmaLinux versions 8, 9, and 10 only.\n"
}
```

### Expected Behavior
CentOS Stream 10 should be detected as a supported CentOS Stream distribution and proceed with the deployment.

### Actual Behavior
CentOS Stream 10 is incorrectly identified as "Fedora 41" and rejected as unsupported.

## Root Cause Analysis

### OS Detection Information
CentOS Stream 10 `/etc/os-release` contains:
```bash
NAME="CentOS Stream"
VERSION="10 (Coughlan)"
ID="centos"
ID_LIKE="rhel fedora"
VERSION_ID="10"
PLATFORM_ID="platform:el10"
PRETTY_NAME="CentOS Stream 10 (Coughlan)"
ANSI_COLOR="0;31"
LOGO="fedora-logo-icon"
CPE_NAME="cpe:/o:centos:centos:10"
```

### Problem
The issue appears to be that Ansible's `ansible_distribution` fact is detecting "Fedora" due to the `ID_LIKE="rhel fedora"` field, rather than using the primary `ID="centos"` field.

### Ansible Facts Detection
When running on CentOS Stream 10, Ansible reports:
- `ansible_distribution`: "Fedora" (incorrect)
- `ansible_distribution_version`: "41" (incorrect)
- Should be: `ansible_distribution`: "CentOS" and `ansible_distribution_version`: "10"

## Impact
- **Deployment Failure**: Complete deployment failure on CentOS Stream 10 systems
- **Platform Support**: Prevents adoption of modern CentOS Stream 10 infrastructure
- **User Experience**: Breaks the one-shot deployment promise for CentOS Stream 10 users

## Suggested Fix

### Option 1: Enhanced OS Detection Logic
Update the OS detection logic in the collection to check multiple fields:

```yaml
# In roles/kvmhost_setup/tasks/rhel_version_detection.yml
- name: Detect CentOS Stream 10 specifically
  set_fact:
    ansible_distribution: "CentOS"
    ansible_distribution_major_version: "10"
  when:
    - ansible_os_family == "RedHat"
    - ansible_distribution_file_variety == "RedHat"
    - (ansible_distribution == "Fedora" and 
       (ansible_cmdline.ostree is defined or 
        '/etc/os-release' | ansible.builtin.file | regex_search('ID="centos"')))
```

### Option 2: Use More Reliable Detection
Instead of relying solely on `ansible_distribution`, use a combination of facts:

```yaml
- name: Read OS release file
  slurp:
    src: /etc/os-release
  register: os_release_content

- name: Parse OS information
  set_fact:
    os_id: "{{ (os_release_content.content | b64decode | regex_search('ID=(.+)', '\\1'))[0] | regex_replace('\"', '') }}"
    os_version_id: "{{ (os_release_content.content | b64decode | regex_search('VERSION_ID=(.+)', '\\1'))[0] | regex_replace('\"', '') }}"

- name: Set CentOS Stream 10 facts
  set_fact:
    kvmhost_is_centos10: true
    ansible_distribution: "CentOS"
    ansible_distribution_major_version: "10"
  when:
    - os_id == "centos"
    - os_version_id == "10"
```

### Option 3: Update Supported OS List
If the collection already has logic for CentOS Stream but the detection is failing, update the supported OS patterns to include the Fedora detection case:

```yaml
- name: Set CentOS Stream 10 support
  set_fact:
    kvmhost_is_centos10: true
  when:
    - (ansible_distribution == "CentOS" and ansible_distribution_major_version == "10") or
      (ansible_distribution == "Fedora" and ansible_distribution_version == "41" and 
       ansible_cmdline.ostree is defined)
```

## Files Likely Needing Updates
Based on typical Ansible collection structure:
- `roles/kvmhost_setup/tasks/rhel_version_detection.yml`
- `roles/kvmhost_setup/tasks/main.yml`
- `roles/kvmhost_setup/vars/main.yml` (if OS-specific variables are defined)

## Testing Verification
After the fix, the following should work on CentOS Stream 10:
1. OS detection should identify CentOS Stream 10 correctly
2. Package installation should use `dnf` with appropriate repositories
3. Service management should work with `systemd`
4. Firewall configuration should work with `firewalld`

## Additional Context
- This issue is part of implementing **ADR-0026: RHEL 10/CentOS 10 Platform Support Strategy**
- CentOS Stream 10 is based on RHEL 10 and should be treated as an Enterprise Linux distribution
- The deployment uses a **terminal-based one-shot deployment architecture** (ADR-0033)
- This affects the broader **Qubinode Navigator modernization** for next-generation enterprise Linux

## Reproduction Steps
1. Install CentOS Stream 10 (Coughlan)
2. Clone qubinode_navigator repository
3. Run `./deploy-qubinode.sh`
4. Observe failure during Ansible collection execution

## Priority
**High** - This blocks CentOS Stream 10 adoption and breaks the modern platform support strategy.

## Contact
This issue was identified during implementation of the Qubinode Navigator terminal-based deployment architecture. The deployment script includes AI Assistant integration for troubleshooting, but this requires collection-level fixes.

---
*Generated by: Qubinode Navigator deployment testing*  
*Date: 2025-11-11*  
*Architecture: Terminal-Based One-Shot Deployment (ADR-0033)*
