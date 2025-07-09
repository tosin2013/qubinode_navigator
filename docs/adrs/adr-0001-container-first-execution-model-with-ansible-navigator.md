# ADR-0001: Container-First Execution Model with Ansible Navigator

## Status
Accepted

## Context
Qubinode Navigator needed a consistent and reproducible way to execute Ansible playbooks across different host systems, operating systems, and environments. Traditional Ansible execution suffered from 'works on my machine' problems due to varying Python versions, Ansible versions, system dependencies, and collection availability across different deployment targets (RHEL 8/9, Rocky Linux, Fedora, cloud providers like Equinix and Hetzner). The project required a solution that would ensure identical execution environments regardless of the underlying host system while maintaining security and performance.

## Decision
Adopt a container-first execution model using ansible-navigator with standardized execution environments built via ansible-builder. All Ansible playbooks are executed within Podman containers using pre-built images (quay.io/qubinode/qubinode-installer) that contain all necessary dependencies, collections, and tools. The execution environment is defined declaratively in execution-environment.yml and includes Python dependencies, Ansible collections, and system packages required for infrastructure automation.

## Consequences

### Positive Consequences
- Eliminates environment inconsistencies and dependency conflicts across different host systems
- Provides reproducible deployments with identical execution environments
- Simplifies dependency management through containerized packaging
- Enables version pinning of Ansible and collections for stability
- Improves security through container isolation
- Facilitates CI/CD integration with consistent execution contexts

### Negative Consequences  
- Adds complexity in container image management and building
- Requires Podman/container runtime on all target systems
- Increases initial setup time for building execution environments
- May have performance overhead compared to native execution
- Requires understanding of container concepts for troubleshooting

## Alternatives Considered

1. **Native Ansible execution with manual dependency management** - Rejected due to inconsistency across environments
2. **Virtual environments with pip-based dependency isolation** - Insufficient for system-level dependencies
3. **Docker-based execution environments** - Podman chosen for better security and rootless operation
4. **Ansible AWX/Tower for centralized execution** - Too heavyweight for the project's needs
5. **Configuration management tools like Puppet or Chef** - Ansible better suited for infrastructure automation

## Evidence Supporting This Decision

- ansible-navigator configuration files show containerized execution: `container-engine: podman`, `enabled: true`
- ansible-builder directory contains execution-environment.yml defining container dependencies
- Makefile includes build commands for creating standardized container images
- Multiple inventory configurations reference the same container image for consistency
- Setup scripts automatically configure ansible-navigator with container settings
- Project supports multiple OS targets (RHEL 8/9, Rocky, Fedora) requiring consistent execution

## Implementation Details

### Execution Environment Configuration
```yaml
# ansible-builder/execution-environment.yml
version: 1
ansible_config: 'ansible.cfg'
dependencies:
  galaxy: requirements.yml
  python: requirements.txt
  system: bindep.txt
```

### Ansible Navigator Configuration
```yaml
# ~/.ansible-navigator.yml
ansible-navigator:
  execution-environment:
    container-engine: podman
    enabled: true
    image: quay.io/qubinode/qubinode-installer:0.8.0
    pull:
      policy: missing
```

## Related Decisions
- ADR-0002: Multi-Cloud Inventory Strategy (planned)
- ADR-0003: Security Architecture with Ansible Vault (planned)

## Date
2025-01-09

## Stakeholders
- DevOps Team
- Infrastructure Team
- QA Team
- Project Maintainers
