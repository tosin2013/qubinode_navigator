______________________________________________________________________

## layout: default title: ADR-0002 Multi-Cloud Inventory Strategy parent: Infrastructure & Deployment grand_parent: Architectural Decision Records nav_order: 2

# ADR-0002: Multi-Cloud Inventory Strategy with Environment-Specific Configurations

## Status

Accepted

## Context

Qubinode Navigator needed to support deployment across multiple cloud providers (Equinix Metal, Hetzner) and different operating system versions (RHEL 8/9, Rocky Linux) while maintaining consistent automation workflows. Each cloud provider has unique networking requirements, API endpoints, authentication methods, and resource provisioning patterns. Additionally, different OS versions require specific package repositories, kernel modules, and configuration approaches. The project required a strategy to manage these variations without duplicating automation logic or creating brittle, provider-specific code paths.

## Decision

Implement a multi-cloud inventory strategy using separate, environment-specific inventory directories for each deployment target. Each inventory contains provider-specific configurations in group_vars, custom host definitions, and environment validation scripts. The structure follows the pattern: `inventories/{environment}/` containing hosts, group_vars/, and check_env.py for validation. This approach isolates provider-specific configurations while maintaining shared playbook logic and role definitions.

## Consequences

### Positive Consequences

- Enables deployment across multiple cloud providers without code duplication
- Provides clear separation of environment-specific configurations
- Allows independent evolution of provider integrations
- Simplifies testing and validation per environment
- Enables parallel development for different cloud providers
- Facilitates environment-specific optimizations and customizations

### Negative Consequences

- Increases configuration maintenance overhead across multiple inventories
- Potential for configuration drift between environments
- Requires discipline to keep shared logic in roles rather than inventories
- May lead to duplication of similar configurations across providers
- Complexity in managing inventory-specific variables and their relationships

## Alternatives Considered

1. **Single unified inventory with conditional logic** - Rejected due to complexity and maintainability issues
1. **Provider-specific playbooks with separate workflows** - Would duplicate automation logic
1. **Dynamic inventory scripts** - Runtime generation adds complexity and debugging difficulty
1. **Terraform or cloud-specific IaC tools** - Ansible chosen for consistency with existing automation
1. **Ansible Tower/AWX with dynamic inventory** - Too heavyweight for the project's needs

## Evidence Supporting This Decision

- Directory structure shows separate inventories: `equinix/`, `hetzner/`, `hetzner-bridge/`, `rhel8-equinix/`, `rhel9-equinix/`
- Each inventory contains provider-specific group_vars and hosts files
- Environment validation scripts (`check_env.py`) exist in each inventory
- Setup scripts dynamically select inventory based on deployment target
- Ansible navigator configurations reference inventory-specific paths
- `load-variables.py` script updates inventory-specific configuration files

## Implementation Details

### Inventory Structure

```
inventories/
├── equinix/               # Equinix Metal cloud
│   ├── hosts
│   ├── group_vars/
│   └── check_env.py
├── hetzner/               # Hetzner cloud
│   ├── hosts
│   ├── group_vars/
│   └── check_env.py
├── hetzner-bridge/        # Hetzner with bridge networking
├── rhel8-equinix/         # RHEL 8 on Equinix
├── rhel9-equinix/         # RHEL 9 on Equinix
└── sample/                # Template inventory
```

### Dynamic Inventory Selection

```bash
# From setup.sh
export INVENTORY="localhost"  # Default
# Scripts dynamically update based on target environment
```

### Environment Validation

Each inventory includes `check_env.py` for validating provider-specific requirements and credentials.

## Related Decisions

- ADR-0001: Container-First Execution Model with Ansible Navigator
- ADR-0003: Dynamic Configuration Management (planned)
- ADR-0004: Security Architecture with Ansible Vault (planned)

## Date

2025-01-09

## Stakeholders

- DevOps Team
- Infrastructure Team
- Cloud Operations Team
- Project Maintainers
