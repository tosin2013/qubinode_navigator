---
layout: default
title: ADR-0005 KVM/Libvirt Virtualization
parent: Infrastructure & Deployment
grand_parent: Architectural Decision Records
nav_order: 5
---

# ADR-0005: KVM/Libvirt Virtualization Platform Choice

## Status
Accepted

## Context
Qubinode Navigator required a virtualization platform to create and manage virtual machines for development, testing, and production workloads across different environments. The platform needed to support multiple operating systems (RHEL 8/9, Rocky Linux, Fedora), provide good performance on bare-metal and cloud instances, integrate well with Ansible automation, and offer enterprise-grade features for storage, networking, and resource management. The solution needed to be cost-effective, well-supported, and suitable for both single-node and distributed deployments.

## Decision
Adopt KVM (Kernel-based Virtual Machine) with libvirt as the primary virtualization platform, enhanced with kcli for simplified VM lifecycle management. KVM provides hardware-accelerated virtualization on Linux systems, libvirt offers a consistent API for VM management, and kcli provides user-friendly tooling for common virtualization tasks.

## Consequences

### Positive Consequences
- Excellent performance through hardware-accelerated virtualization
- Native Linux integration with minimal overhead
- Strong ecosystem support and enterprise adoption
- Cost-effective solution with no licensing fees
- Comprehensive networking and storage options
- Good integration with Ansible and automation tools
- Supports live migration and advanced VM features
- Active development and long-term support from Red Hat/community

### Negative Consequences  
- Linux-only solution, limiting cross-platform compatibility
- Steeper learning curve compared to desktop virtualization solutions
- Requires hardware virtualization support (Intel VT-x/AMD-V)
- More complex networking configuration for advanced scenarios
- Limited GUI management tools compared to commercial alternatives
- Requires root privileges for many operations

## Alternatives Considered

1. **VMware vSphere/ESXi** - Rejected due to licensing costs and vendor lock-in
2. **Proxmox VE** - Good option but adds additional management layer complexity
3. **Docker/Podman containers** - Insufficient for full OS virtualization requirements
4. **OpenStack** - Too complex and resource-intensive for the project's needs
5. **Xen Hypervisor** - Less integrated with Red Hat ecosystem
6. **VirtualBox** - Not suitable for production/server environments

## Evidence Supporting This Decision

- Extensive KVM host setup automation in `setup.sh` and `qubinode_navigator.sh`
- Libvirt storage configuration and management
- Integration with kcli for VM lifecycle management
- Support for bridge networking and storage pools
- Ansible playbooks for KVM host deployment
- Hardware compatibility checks and optimization

## Implementation Details

### KVM Host Setup
```bash
# From setup.sh - KVM host deployment
function deploy_kvmhost() {
    echo "Deploying KVM Host"
    cd "$HOME"/qubinode_navigator
    sudo -E /usr/local/bin/ansible-navigator run ansible-navigator/setup_kvmhost.yml \
        --extra-vars "admin_user=lab-user" --penv GUID \
        --vault-password-file "$HOME"/.vault_password -m stdout
}
```

### Storage Configuration
```python
# From load-variables.py - Dynamic storage setup
inventory['create_libvirt_storage'] = True
inventory['create_lvm'] = True
inventory['kvm_host_libvirt_extra_disk'] = disks
```

### Networking Setup
```python
# Network bridge configuration
inventory['configure_bridge'] = configure_bridge
inventory['kvm_host_interface'] = interface
inventory['kvm_host_ip'] = ip
```

### Kcli Integration
```bash
# From setup.sh - Kcli setup for VM management
function setup_kcli_base() {
    echo "Configuring Kcli"
    source ~/.bash_aliases
    qubinode_setup_kcli
    kcli_configure_images
}
```

### Key Features Utilized
- **Hardware Acceleration**: Native KVM support for Intel VT-x/AMD-V
- **Storage Management**: LVM-based storage pools with libvirt integration
- **Network Management**: Bridge networking for VM connectivity
- **Resource Management**: CPU, memory, and disk allocation controls
- **Snapshot Support**: VM state management and backup capabilities
- **Live Migration**: VM mobility between hosts (when configured)

### Integration Points
- **Ansible Automation**: Playbooks for KVM host setup and VM management
- **Storage Integration**: LVM and filesystem-based storage pools
- **Network Integration**: Bridge networking with host network interfaces
- **Monitoring**: Integration with system monitoring and alerting
- **Backup**: VM snapshot and backup automation

### Performance Optimizations
- Hardware virtualization acceleration enabled
- Optimized storage configurations with LVM
- Network bridge setup for minimal overhead
- CPU and memory tuning for virtualization workloads

### Security Considerations
- Isolated VM environments with proper resource limits
- Network segmentation through bridge configurations
- Storage encryption support where required
- Access control through libvirt permissions

## Operational Benefits

- **Standardization**: Consistent virtualization platform across all environments
- **Automation**: Full lifecycle management through Ansible
- **Scalability**: Supports both single-node and distributed deployments
- **Cost Efficiency**: No licensing costs for virtualization platform
- **Performance**: Near-native performance for virtualized workloads
- **Flexibility**: Supports various guest operating systems and configurations

## Related Decisions
- ADR-0001: Container-First Execution Model with Ansible Navigator
- ADR-0002: Multi-Cloud Inventory Strategy with Environment-Specific Configurations
- ADR-0003: Dynamic Configuration Management with Python
- ADR-0004: Security Architecture with Ansible Vault and AnsibleSafe

## Date
2025-01-09

## Stakeholders
- Infrastructure Team
- DevOps Team
- System Administrators
- Development Teams
- Project Maintainers
