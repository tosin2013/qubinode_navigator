# ADR-0008: OS-Specific Deployment Script Strategy

## Status
Accepted

## Context
Qubinode Navigator needed to support deployment across different Linux distributions with varying package managers, system configurations, and cloud provider integrations. Each operating system has unique package repositories, service management approaches, kernel modules, and configuration file locations. RHEL 9 requires enterprise-grade features and subscription management, while Rocky Linux offers community-driven alternatives with different optimization needs. The project required a strategy to handle these OS-specific differences while maintaining consistent functionality and avoiding code duplication in core automation logic.

## Decision
Implement OS-specific deployment scripts that encapsulate distribution-specific logic, package management, and configuration approaches. Create dedicated scripts for each major OS target: `rhel9-linux-hypervisor.sh` for RHEL 9 enterprise environments and `rocky-linux-hetzner.sh` for Rocky Linux cloud deployments. Each script contains OS-optimized package lists, service configurations, and environment-specific setup procedures while sharing common architectural patterns and function structures.

## Consequences

### Positive Consequences
- Enables optimal configuration for each operating system with native package managers and repositories
- Provides clear separation between OS-specific logic and shared automation code
- Allows independent evolution and optimization of deployment procedures per OS
- Facilitates testing and validation specific to each distribution
- Enables cloud provider optimizations within OS-specific contexts
- Reduces complexity in shared automation code by removing conditional OS logic

### Negative Consequences  
- Increases maintenance overhead with multiple deployment scripts to maintain
- Potential for configuration drift between different OS implementations
- Requires expertise in multiple Linux distributions and their specific requirements
- May lead to duplication of similar functionality across scripts
- Complexity in ensuring feature parity across different OS targets

## Alternatives Considered

1. **Single unified deployment script with extensive conditional logic** - Rejected due to complexity and maintainability issues
2. **OS detection with dynamic package list generation at runtime** - Would add runtime complexity and debugging difficulty
3. **Ansible-only approach using distribution-specific variables** - Insufficient for complex OS-specific setup procedures
4. **Container-based deployment abstracting OS differences** - Would lose OS-specific optimizations and native integration
5. **Configuration management tools like Puppet or Chef** - Too heavyweight and inconsistent with existing Ansible-based approach

## Evidence Supporting This Decision

- `rhel9-linux-hypervisor.sh` contains 759 lines with 21 RHEL 9-specific functions
- `rocky-linux-hetzner.sh` contains 435 lines with 19 Rocky Linux-specific functions
- Different package installation commands: `dnf` for RHEL 9, `yum/dnf` for Rocky Linux
- OS-specific service management and firewall configurations
- Cloud provider-specific optimizations in `rocky-linux-hetzner.sh` for Hetzner
- Consistent function naming and error handling patterns across both scripts

## Implementation Details

### RHEL 9 Script (`rhel9-linux-hypervisor.sh`)
```bash
# RHEL 9 specific package installation
function install_packages() {
    sudo dnf install bzip2-devel libffi-devel wget vim podman \
        ncurses-devel sqlite-devel firewalld make gcc git unzip \
        sshpass lvm2 python3 python3-pip java-11-openjdk-devel \
        ansible-core perl-Digest-SHA -y
}
```

### Rocky Linux Script (`rocky-linux-hetzner.sh`)
```bash
# Rocky Linux with Hetzner-specific optimizations
export INVENTORY="hetzner"  # Cloud provider specific
function check_for_lab_user() {
    # Hetzner-specific user management
}
```

### Common Patterns
- **Function-based architecture**: Both scripts use modular function approach
- **Error handling**: Consistent exit-on-failure patterns
- **Logging**: Standardized output formatting
- **Configuration management**: Similar vault and inventory setup

### OS-Specific Optimizations

#### RHEL 9 Enterprise Features
- Enterprise package repositories and subscription management
- Advanced security configurations
- Enterprise-grade monitoring and logging
- Comprehensive hypervisor setup with 21 specialized functions

#### Rocky Linux Cloud Optimizations
- Cloud provider-specific networking configurations
- Streamlined package set for cloud environments
- Hetzner-specific SSH and user management
- Optimized for cloud deployment scenarios

## Operational Benefits

- **Maintenance**: Clear ownership and responsibility per OS
- **Testing**: OS-specific testing strategies and validation
- **Performance**: Native package managers and optimized configurations
- **Security**: OS-specific security hardening and compliance
- **Scalability**: Independent scaling and optimization per distribution

## Related Decisions
- ADR-0001: Container-First Execution Model with Ansible Navigator
- ADR-0002: Multi-Cloud Inventory Strategy with Environment-Specific Configurations
- ADR-0003: Dynamic Configuration Management with Python
- ADR-0005: KVM/Libvirt Virtualization Platform Choice

## Date
2025-01-09

## Stakeholders
- DevOps Team
- Infrastructure Team
- System Administrators
- Cloud Operations Team
- Project Maintainers
