---
layout: default
title: ADR-0001 Container-First Execution Model
parent: Infrastructure & Deployment
grand_parent: Architectural Decision Records
nav_order: 1
---

# ADR-0001: Container-First Execution Model with Ansible Navigator

## Status
Accepted - Updated 2025-07-10 (Security and Compatibility Updates) - Updated 2025-07-10 (Security and Compatibility Updates)

## Context
Qubinode Navigator needed a consistent and reproducible way to execute Ansible playbooks across different host systems, operating systems, and environments. Traditional Ansible execution suffered from 'works on my machine' problems due to varying Python versions, Ansible versions, system dependencies, and collection availability across different deployment targets (RHEL 8/9, Rocky Linux, Fedora, cloud providers like Equinix and Hetzner). The project required a solution that would ensure identical execution environments regardless of the underlying host system while maintaining security and performance.

## Decision
Adopt a container-first execution model using ansible-navigator with standardized execution environments built via ansible-builder. All Ansible playbooks are executed within Podman containers using pre-built images that contain all necessary dependencies, collections, and tools. The execution environment is defined declaratively in execution-environment.yml and includes Python dependencies, Ansible collections, and system packages required for infrastructure automation.

**Updated Requirements (2025-07-10):**
- **Mandatory Security Update**: Use ansible-core 2.18.1+ to address CVE-2024-11079 (arbitrary code execution vulnerability)
- **Base Image Standardization**: Use Red Hat UBI 9 minimal (`registry.access.redhat.com/ubi9/ubi-minimal`) for enterprise compliance and security
- **Python Version Requirements**: Execution environments must use Python 3.11 or 3.12 (RHEL 9.6 default Python 3.9 is incompatible with ansible-navigator v25.5.0+)
- **Tooling Versions**: ansible-navigator v25.5.0, ansible-builder v3.1.0, ansible-core 2.18.1+
- **Version Pinning**: Strict version pinning for all collections and dependencies to ensure reproducible builds

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
# ansible-builder/execution-environment.yml (Updated 2025-07-10)
version: 3
images:
  base_image:
    name: registry.access.redhat.com/ubi9/ubi-minimal:latest

dependencies:
  galaxy: requirements.yml
  python: requirements.txt
  system: bindep.txt

additional_build_steps:
  append_base:
    - RUN $PYCMD -m pip install -U pip>=20.3
  append_final:
    - RUN echo "Qubinode Navigator EE v${EE_VERSION}"
```

### Ansible Navigator Configuration
```yaml
# ~/.ansible-navigator.yml (Updated 2025-07-10)
ansible-navigator:
  execution-environment:
    container-engine: podman
    enabled: true
    image: quay.io/qubinode/qubinode-installer:1.0.0
    pull:
      policy: missing
  ansible:
    inventory:
      entries:
        - inventories/localhost
```

### Security and Compatibility Requirements (Added 2025-07-10)

**Critical Security Update:**
- CVE-2024-11079 in ansible-core versions prior to 2.18.1 enables arbitrary code execution
- All execution environments MUST use ansible-core 2.18.1 or later
- Immediate upgrade required for all production deployments

**Python Compatibility:**
- ansible-navigator v25.5.0+ requires Python 3.10 or later
- RHEL 9.6 default Python 3.9 is incompatible and requires custom EE with Python 3.11/3.12
- All managed nodes must have Python 3.8+ (control nodes require Python 3.11+)

**Base Image Requirements:**
- Use Red Hat UBI 9 minimal for enterprise compliance and security updates
- Provides continuous security patching and enterprise support
- Ensures compatibility with Red Hat subscriptions and support

## Related Decisions
- ADR-0002: Multi-Cloud Inventory Strategy (planned)
- ADR-0003: Security Architecture with Ansible Vault (planned)

## Date
2025-01-09 (Original)
2025-07-10 (Security and Compatibility Updates)

## Stakeholders
- DevOps Team
- Infrastructure Team
- QA Team
- Project Maintainers
