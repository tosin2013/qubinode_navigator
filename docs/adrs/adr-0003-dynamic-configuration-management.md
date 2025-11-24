---
layout: default
title: ADR-0003 Dynamic Configuration Management
parent: Configuration & Automation
grand_parent: Architectural Decision Records
nav_order: 3
---

# ADR-0003: Dynamic Configuration Management with Python

## Status
Accepted

## Context
Qubinode Navigator needed to automatically discover and configure network interfaces, storage devices, and system parameters across diverse hardware configurations and cloud environments. Manual configuration would be error-prone and time-consuming, especially when deploying across different cloud providers with varying network topologies, storage options, and system capabilities. The project required an intelligent configuration system that could adapt to different environments while maintaining consistency and reliability.

## Decision
Implement dynamic configuration management using Python scripts that automatically discover system resources and generate environment-specific Ansible inventory configurations. The primary tool is `load-variables.py`, which performs network interface discovery, storage device detection, and system parameter configuration, then updates the appropriate inventory files with discovered values.

## Consequences

### Positive Consequences
- Eliminates manual configuration errors and reduces deployment time
- Automatically adapts to different hardware and cloud configurations
- Provides consistent configuration discovery across all supported environments
- Reduces the barrier to entry for new deployments
- Enables automated validation of system requirements
- Facilitates rapid environment provisioning and scaling

### Negative Consequences  
- Adds Python dependency and complexity to the deployment process
- Requires error handling for edge cases in hardware/network detection
- May fail in unusual or unsupported hardware configurations
- Debugging configuration issues requires Python knowledge
- Potential for incorrect auto-detection in complex network setups

## Alternatives Considered

1. **Manual configuration files** - Rejected due to error-prone nature and maintenance overhead
2. **Ansible facts gathering only** - Insufficient for complex network and storage configuration
3. **Shell script-based discovery** - Python chosen for better data manipulation and YAML handling
4. **Cloud-provider specific tools** - Would create vendor lock-in and inconsistency
5. **Configuration management databases** - Too complex for the project's requirements

## Evidence Supporting This Decision

- `load-variables.py` performs comprehensive system discovery and configuration
- Network interface detection using `netifaces` library for cross-platform compatibility
- Storage device discovery with `psutil` for system resource information
- Dynamic YAML file updates for inventory configuration
- Interactive prompts with validation for critical parameters
- Integration with multiple inventory environments

## Implementation Details

### Network Discovery
```python
# From load-variables.py
def get_interface_ips(configure_bridge=None, interface=None):
    addrs = netifaces.ifaddresses(interface)
    ip = addrs[netifaces.AF_INET][0]['addr']
    netmask = addrs[netifaces.AF_INET][0]['netmask']
    macaddr = addrs[netifaces.AF_LINK][0]['addr']
```

### Storage Configuration
```python
def select_disk(disks=None):
    # Automatic disk detection and selection
    # Updates inventory with storage configuration
    inventory['kvm_host_libvirt_extra_disk'] = disks
```

### Dynamic Inventory Updates
```python
def update_inventory(username=None, domain_name=None, dnf_forwarder=None):
    inventory_path = 'inventories/'+str(inventory_env)+'/group_vars/all.yml'
    with open(inventory_path, 'r') as f:
        inventory = yaml.safe_load(f)
    # Update with discovered values
```

### Key Dependencies
- `netifaces`: Cross-platform network interface information
- `psutil`: System and process utilities
- `fire`: Command-line interface generation
- `requests`: HTTP library for API interactions

### Configuration Flow
1. **System Detection**: Discover network interfaces, storage devices, system capabilities
2. **User Interaction**: Prompt for environment-specific parameters with validation
3. **Inventory Update**: Generate and update YAML configuration files
4. **Validation**: Verify configuration consistency and completeness

## Integration Points

- Called by `setup.sh` during initial environment setup
- Supports both interactive and automated (CI/CD) modes
- Updates multiple inventory files based on environment selection
- Integrates with Ansible variable hierarchy

## Related Decisions
- ADR-0001: Container-First Execution Model with Ansible Navigator
- ADR-0002: Multi-Cloud Inventory Strategy with Environment-Specific Configurations
- ADR-0004: Security Architecture with Ansible Vault (planned)

## Date
2025-01-09

## Stakeholders
- DevOps Team
- Infrastructure Team
- System Administrators
- Project Maintainers
