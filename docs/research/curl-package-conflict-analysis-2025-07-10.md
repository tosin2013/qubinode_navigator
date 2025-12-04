# curl/curl-minimal Package Conflict Analysis and Multi-Platform Testing Strategy

**Date**: 2025-07-10
**Category**: package-management
**Status**: Active Research
**Priority**: Critical - Blocking RHEL 9 Deployments
**Repository**: https://github.com/Qubinode/qubinode_kvmhost_setup_collection.git

## Executive Summary

Critical package conflict discovered in `qubinode_kvmhost_setup_collection` preventing deployments on RHEL 9 systems. The collection attempts to install `curl` package which conflicts with pre-installed `curl-minimal` in RHEL 9 minimal installations.

## Research Questions

### Primary Research Question

**How can we resolve the curl/curl-minimal package conflict in the qubinode_kvmhost_setup_collection for RHEL 9+ systems and implement comprehensive multi-platform testing to prevent similar issues across RHEL 9/10 and CentOS 9/10?**

### Critical Sub-Questions

1. **Comprehensive Package Conflict Analysis**

   - What is the exact mechanism causing the curl/curl-minimal conflict?
   - Which RHEL/CentOS versions are affected by this issue?
   - Are there other similar package conflicts in the current package list?
   - What packages in `required_rpm_packages` have minimal vs full variants?
   - How do package conflicts differ between minimal and full RHEL installations?
   - What are the functional differences between curl and curl-minimal?
   - Are there other conflicting package pairs we should investigate (e.g., systemd-minimal)?

1. **Complete Package List Analysis**

   - Which packages in the 40+ item `required_rpm_packages` list are RHEL 9/10 compatible?
   - What packages have been deprecated or renamed between RHEL 8 and RHEL 9?
   - Are there packages that require different installation methods in RHEL 9/10?
   - Which packages are available in different repositories (BaseOS vs AppStream)?
   - What packages require EPEL and how does EPEL availability differ across versions?
   - Are there packages that conflict with default RHEL 9/10 minimal installations?

1. **RHEL 9/10 GitHub Actions Testing Strategy**

   - How can we implement RHEL 9 testing in GitHub Actions without Red Hat subscriptions?
   - What is the best approach for RHEL 10 testing when it becomes available?
   - Can we use UBI (Universal Base Images) for package testing?
   - How do we handle subscription-manager requirements in CI/CD?
   - What testing matrix should cover RHEL 9.0, 9.1, 9.2, 9.3+ versions?
   - How can we test both minimal and full RHEL installations?
   - What is the strategy for testing CentOS Stream 9/10 as RHEL alternatives?

1. **Multi-Platform CI/CD Architecture**

   - How do we structure GitHub Actions workflows for multi-OS testing?
   - What container strategy works best for RHEL testing (podman vs docker)?
   - How can we implement parallel testing across RHEL 8/9/10 and CentOS 8/9/10?
   - What is the approach for testing with different subscription states?
   - How do we handle package repository differences across versions?
   - What caching strategy optimizes CI/CD performance for package testing?

1. **Solution Implementation Strategy**

   - How can we implement conditional package installation logic for all packages?
   - What is the best approach for detecting package conflicts before installation?
   - Should we create version-specific package lists or dynamic detection?
   - How do we handle packages that require different names across RHEL versions?
   - What is the strategy for graceful fallbacks when packages are unavailable?
   - How can we implement smart package resolution for minimal vs full installations?

1. **Upstream Coordination and Contribution**

   - What changes are needed in the qubinode_kvmhost_setup_collection repository?
   - How do we coordinate fixes with the upstream maintainers?
   - What is the process for testing and validating upstream changes?
   - How do we ensure our fixes align with upstream development practices?
   - What documentation updates are needed for multi-platform support?
   - How do we contribute testing infrastructure back to the upstream project?

1. **Backward Compatibility and Migration**

   - How do we maintain compatibility with existing RHEL 8 deployments?
   - What is the migration path for users on different RHEL versions?
   - How do we ensure the fix doesn't break existing installations?
   - What versioning strategy supports multiple RHEL versions simultaneously?
   - How do we handle deprecated packages gracefully across versions?
   - What rollback strategy exists if new package logic fails?

## Technical Analysis

### Root Cause Investigation

**Repository Analysis Results**:

- **Cloned Repository**: `/tmp/qubinode_kvmhost_setup_collection_research`
- **Conflict Source**: `inventories/test/group_vars/all.yml` line 85
- **Package List Variable**: `required_rpm_packages`
- **Problematic Entry**: `curl` (conflicts with `curl-minimal`)

**Error Details**:

```
TASK [tosin2013.qubinode_kvmhost_setup_collection.kvmhost_setup : Ensure required packages are installed]
failed: [control] (item=curl) => {
  "msg": "Depsolve Error occurred: Problem: problem with installed package curl-minimal-7.76.1-31.el9.x86_64
  - package curl-minimal-7.76.1-31.el9.x86_64 from @System conflicts with curl provided by curl-7.76.1-31.el9.x86_64"
}
```

**Package Analysis**:

- **RHEL 9 Minimal**: Ships with `curl-minimal` by default
- **Full curl Package**: Provides additional features but conflicts with minimal version
- **Mutual Exclusivity**: Cannot have both packages installed simultaneously
- **Impact**: Blocks entire KVM host setup process

### Complete Package List Analysis

**Current required_rpm_packages (40+ packages)**:

```yaml
required_rpm_packages:
  - virt-install              # Virtualization - Core
  - libvirt-daemon-config-network  # Virtualization - Networking
  - libvirt-daemon-kvm        # Virtualization - KVM
  - libguestfs-tools          # Virtualization - Guest tools
  - libvirt-client            # Virtualization - Client
  - qemu-kvm                  # Virtualization - QEMU
  - nfs-utils                 # Storage - NFS
  - libvirt-daemon           # Virtualization - Daemon
  - virt-top                  # Virtualization - Monitoring
  - tuned                     # Performance - Tuning
  - openssh-server           # Network - SSH
  - wget                      # Network - Download
  - git                       # Development - Version control
  - net-tools                 # Network - Legacy tools
  - bind-utils               # Network - DNS tools
  - yum-utils                # Package - YUM utilities (RHEL 8 name)
  - iptables-services        # Network - Firewall
  - bash-completion          # Shell - Completion
  - kexec-tools              # System - Kernel tools
  - sos                      # System - Support tools
  - psacct                   # System - Process accounting
  - vim                      # Editor - Text editor
  - device-mapper-event-libs # Storage - Device mapper
  - device-mapper-libs       # Storage - Device mapper
  - httpd-tools              # Web - Apache tools
  - tmux                     # Terminal - Multiplexer
  - python3-dns             # Python - DNS library
  - python3-lxml            # Python - XML library
  - cockpit-machines        # Management - Web console
  - bc                      # Utilities - Calculator
  - nmap                    # Network - Scanner
  - ncurses-devel          # Development - Terminal library
  - curl                   # Network - HTTP client ⚠️ CONFLICT
```

**Potential RHEL 9/10 Compatibility Issues**:

1. **curl vs curl-minimal** ⚠️ - Confirmed conflict
1. **yum-utils vs dnf-utils** ⚠️ - Package renamed in RHEL 9
1. **iptables-services** ⚠️ - May conflict with firewalld default
1. **net-tools** ⚠️ - Deprecated in favor of iproute2
1. **python3-* packages*\* ⚠️ - May have different names/availability

**Packages Requiring Investigation**:

- **Development packages**: ncurses-devel, python3-\* libraries
- **Legacy networking**: net-tools, iptables-services vs firewalld
- **Package managers**: yum-utils (RHEL 8) vs dnf-utils (RHEL 9+)
- **Container tools**: podman, container-selinux compatibility
- **Virtualization stack**: libvirt versions and dependencies

### Affected Systems

**Confirmed Affected**:

- RHEL 9 minimal installations
- Likely affects CentOS 9 minimal installations

**Potentially Affected**:

- RHEL 10 (when released)
- CentOS 10 (when released)
- Any minimal installation variants

**Not Affected**:

- RHEL 8 systems (different package structure)
- Full RHEL installations that don't include curl-minimal

## RHEL 9/10 GitHub Actions Testing Strategy

### Testing Matrix Design

**Target Platforms**:

```yaml
strategy:
  matrix:
    os:
      - rhel-9.0-minimal
      - rhel-9.1-minimal
      - rhel-9.2-minimal
      - rhel-9.3-minimal
      - rhel-9-full
      - centos-stream-9
      - rhel-10-beta (when available)
      - centos-stream-10 (when available)
    ansible_version:
      - "2.14"
      - "2.15"
      - "2.16"
    python_version:
      - "3.9"
      - "3.11"
```

**Container Strategy**:

```yaml
# Use Red Hat Universal Base Images (UBI) for testing
container:
  image: registry.access.redhat.com/ubi9/ubi:latest
  options: --privileged --systemd=true
  volumes:
    - /sys/fs/cgroup:/sys/fs/cgroup:ro
```

**Subscription Management Strategy**:

```yaml
# For RHEL testing without subscriptions
- name: Enable free repositories for testing
  shell: |
    dnf config-manager --enable ubi-9-baseos-rpms
    dnf config-manager --enable ubi-9-appstream-rpms

# Alternative: Use CentOS Stream as RHEL proxy
- name: Test on CentOS Stream 9 as RHEL 9 equivalent
  uses: actions/setup-python@v4
  with:
    python-version: '3.11'
```

**Package Testing Workflow**:

```yaml
name: Multi-Platform Package Testing

on:
  pull_request:
    paths:
      - 'roles/kvmhost_setup/defaults/main.yml'
      - 'inventories/*/group_vars/all.yml'
  schedule:
    - cron: '0 2 * * 1'  # Weekly testing

jobs:
  package-compatibility-test:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        rhel_version: [8, 9, 10]
        installation_type: [minimal, full]

    steps:
      - name: Test package installation
        run: |
          # Test each package individually
          for package in $(cat required_packages.txt); do
            echo "Testing package: $package"
            dnf info $package || echo "Package $package not available"
          done
```

### Testing Scenarios

**Scenario 1: Package Conflict Detection**

```yaml
- name: Test curl/curl-minimal conflict
  block:
    - name: Attempt to install curl on minimal system
      dnf:
        name: curl
        state: present
      register: curl_install
      ignore_errors: true

    - name: Verify conflict detection
      assert:
        that: curl_install.failed
        fail_msg: "Expected curl installation to fail on minimal system"
```

**Scenario 2: Cross-Version Compatibility**

```yaml
- name: Test package availability across RHEL versions
  include_tasks: test_package_availability.yml
  vars:
    test_packages: "{{ required_rpm_packages }}"
    rhel_version: "{{ ansible_distribution_major_version }}"
```

**Scenario 3: Repository Requirements**

```yaml
- name: Test EPEL dependency packages
  block:
    - name: Install EPEL
      dnf:
        name: epel-release
        state: present

    - name: Test EPEL-dependent packages
      dnf:
        name: "{{ epel_packages }}"
        state: present
```

## Proposed Solutions

### Solution 1: Comprehensive Package Compatibility Matrix

```yaml
# Version-specific package mappings
package_mappings:
  rhel8:
    http_client: curl
    package_utils: yum-utils
    firewall: iptables-services
  rhel9:
    http_client: curl-minimal
    package_utils: dnf-utils
    firewall: firewalld
  rhel10:
    http_client: curl-minimal
    package_utils: dnf-utils
    firewall: firewalld

- name: Install version-appropriate packages
  dnf:
    name: "{% raw %}{{ package_mappings[ansible_distribution + ansible_distribution_major_version][item.key] }}{% endraw %}"
    state: present
  loop: "{% raw %}{{ required_package_categories | dict2items }}{% endraw %}"
```

### Solution 2: Smart Package Detection with Fallbacks

```yaml
- name: Detect available packages
  ansible.builtin.shell: |
    if dnf list available curl-minimal &>/dev/null; then
      echo "curl-minimal"
    elif dnf list available curl &>/dev/null; then
      echo "curl"
    else
      echo "none"
    fi
  register: available_curl_package

- name: Install detected package
  dnf:
    name: "{{ available_curl_package.stdout }}"
    state: present
  when: available_curl_package.stdout != "none"
```

### Solution 3: Pre-installation Conflict Detection

```yaml
- name: Check for package conflicts before installation
  ansible.builtin.shell: |
    dnf install --assumeno {{ item }} 2>&1 | grep -i conflict || echo "no_conflict"
  register: conflict_check
  loop: "{{ required_rpm_packages }}"

- name: Filter out conflicting packages
  set_fact:
    safe_packages: "{% raw %}{{ required_rpm_packages | difference(conflicting_packages) }}{% endraw %}"
  vars:
    conflicting_packages: "{% raw %}{{ conflict_check.results | selectattr('stdout', 'search', 'conflict') | map(attribute='item') | list }}{% endraw %}"
```

## Research Methodology

### Phase 1: Repository Analysis ✅

- [x] Clone qubinode_kvmhost_setup_collection repository
- [x] Identify exact source of curl package requirement
- [x] Analyze package installation logic
- [x] Document current package list structure

### Phase 2: Comprehensive Package Analysis (In Progress)

- [ ] Analyze all 40+ packages in required_rpm_packages list
- [ ] Identify RHEL 8 vs RHEL 9/10 package name changes
- [ ] Document package conflicts and dependencies
- [ ] Test package availability across RHEL/CentOS versions
- [ ] Create package compatibility matrix
- [ ] Investigate EPEL requirements and availability

### Phase 3: Solution Development (Planned)

- [ ] Develop conditional package installation logic for all packages
- [ ] Implement smart package detection with fallbacks
- [ ] Create version-specific package mappings
- [ ] Test solutions in isolated RHEL 9/10 environments
- [ ] Validate backward compatibility with RHEL 8
- [ ] Create comprehensive test cases for all scenarios

### Phase 4: RHEL 9/10 GitHub Actions Implementation (Planned)

- [ ] Design comprehensive testing matrix (RHEL 8/9/10, CentOS 8/9/10)
- [ ] Implement UBI-based container testing strategy
- [ ] Create subscription-free testing approach
- [ ] Develop parallel testing workflows
- [ ] Implement package conflict detection automation
- [ ] Create performance-optimized CI/CD with caching

### Phase 5: Upstream Coordination (Planned)

- [ ] Fork repository for development
- [ ] Implement and test fixes across all target platforms
- [ ] Create comprehensive documentation for multi-platform support
- [ ] Submit pull request to upstream with testing evidence
- [ ] Coordinate with maintainers for review and merge
- [ ] Contribute GitHub Actions testing infrastructure

### Phase 6: Integration and Monitoring (Planned)

- [ ] Update Qubinode Navigator to use fixed collection
- [ ] Implement monitoring for package conflicts
- [ ] Create automated regression testing
- [ ] Establish continuous compatibility monitoring
- [ ] Document migration procedures for different RHEL versions

## Success Criteria

### Immediate Goals (Next 2 weeks)

- [ ] Resolve curl package conflict for RHEL 9 deployments
- [ ] Analyze all 40+ packages for RHEL 9/10 compatibility issues
- [ ] Identify and document all package name changes between RHEL versions
- [ ] Create initial package compatibility matrix
- [ ] Implement and test conditional package installation logic
- [ ] Maintain backward compatibility with RHEL 8

### Short-term Goals (Next month)

- [ ] Implement comprehensive GitHub Actions testing for RHEL 9/10
- [ ] Create UBI-based testing strategy for subscription-free CI/CD
- [ ] Develop automated package conflict detection
- [ ] Test solutions across minimal and full RHEL installations
- [ ] Fork and fix upstream qubinode_kvmhost_setup_collection
- [ ] Submit upstream pull request with comprehensive testing

### Long-term Goals (Next quarter)

- [ ] Establish comprehensive multi-platform testing (RHEL 8/9/10, CentOS 8/9/10)
- [ ] Create sustainable dependency management approach for all packages
- [ ] Implement continuous compatibility monitoring
- [ ] Prevent similar package conflicts through automated detection
- [ ] Contribute testing infrastructure back to upstream repository
- [ ] Document best practices for multi-RHEL version support
- [ ] Create migration guides for users across RHEL versions

## Risk Assessment

### High Risk

- **Breaking Changes**: Solution could break existing RHEL 8 deployments
- **Upstream Coordination**: Delays in upstream acceptance of fixes
- **Testing Complexity**: Difficulty testing across multiple RHEL/CentOS versions

### Medium Risk

- **Feature Limitations**: curl-minimal may lack features needed by some components
- **CI/CD Complexity**: Red Hat subscription requirements in GitHub Actions
- **Maintenance Overhead**: Ongoing maintenance of conditional logic

### Low Risk

- **Performance Impact**: Minimal performance difference between curl variants
- **Documentation**: Need to update documentation for new logic

## Next Steps

### Immediate Actions (Next 24 hours)

1. **Develop Fix**: Implement conditional package installation logic
1. **Local Testing**: Test fix in current RHEL 9 environment
1. **Validation**: Ensure fix resolves deployment issue

### Short-term Actions (Next Week)

1. **Fork Repository**: Create development fork of qubinode_kvmhost_setup_collection
1. **Implement Solution**: Apply fix to forked repository
1. **Comprehensive Testing**: Test across available RHEL/CentOS versions
1. **Documentation**: Update README and documentation

### Medium-term Actions (Next Month)

1. **Upstream Contribution**: Submit pull request to upstream repository
1. **GitHub Actions**: Implement multi-platform testing strategy
1. **Integration**: Update Qubinode Navigator to use fixed collection
1. **Monitoring**: Establish monitoring for similar package conflicts

## Resources and References

### Repository Links

- **Upstream**: https://github.com/Qubinode/qubinode_kvmhost_setup_collection.git
- **Research Clone**: `/tmp/qubinode_kvmhost_setup_collection_research`
- **Conflict File**: `inventories/test/group_vars/all.yml:85`

### Documentation

- **RHEL 9 Package Management**: Red Hat documentation on curl vs curl-minimal
- **Ansible Package Management**: Best practices for conditional package installation
- **GitHub Actions**: Multi-platform testing strategies

### Stakeholders

- **Upstream Maintainers**: Qubinode/qubinode_kvmhost_setup_collection
- **Qubinode Navigator Team**: Integration and testing
- **End Users**: RHEL 9 deployment users

______________________________________________________________________

**Research Status**: Active
**Last Updated**: 2025-07-10
**Next Review**: 2025-07-11
