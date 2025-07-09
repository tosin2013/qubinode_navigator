# ADR-0009: Cloud Provider-Specific Configuration Management

## Status
Accepted

## Context
Qubinode Navigator needed to support deployment across multiple cloud providers, each with unique networking models, authentication mechanisms, storage options, and operational requirements. Hetzner Cloud requires specific SSH authentication workflows, user management patterns, and network configurations that differ significantly from bare-metal RHEL deployments or other cloud providers like Equinix Metal. The project required a strategy to handle cloud provider-specific requirements while maintaining consistent automation workflows and avoiding vendor lock-in.

## Decision
Implement cloud provider-specific configuration management through dedicated deployment scripts and inventory configurations. Each cloud provider receives a specialized script (e.g., `rocky-linux-hetzner.sh`) that encapsulates provider-specific networking, authentication, user management, and service configurations. Cloud-specific logic is isolated within these scripts while maintaining integration with the core Qubinode Navigator automation framework.

## Consequences

### Positive Consequences
- Enables optimal integration with each cloud provider's native services and APIs
- Provides clear separation between cloud-specific logic and core automation
- Allows independent optimization for each cloud provider's unique characteristics
- Facilitates testing and validation specific to each cloud environment
- Enables cloud provider-specific security and compliance configurations
- Reduces complexity in shared automation code by isolating provider-specific logic
- Supports multi-cloud deployment strategies without vendor lock-in

### Negative Consequences  
- Increases maintenance overhead with multiple cloud-specific configurations
- Potential for configuration drift between different cloud provider implementations
- Requires expertise in multiple cloud providers and their specific requirements
- May lead to duplication of similar functionality across cloud-specific scripts
- Complexity in ensuring feature parity across different cloud targets
- Additional testing requirements for each cloud provider integration

## Alternatives Considered

1. **Single unified script with cloud provider detection** - Rejected due to complexity and maintainability issues
2. **Cloud-agnostic configuration with runtime detection** - Would lose cloud-specific optimizations
3. **Terraform or cloud-specific infrastructure-as-code tools** - Inconsistent with Ansible-based approach
4. **Container-based deployment abstracting cloud differences** - Would lose native cloud integration benefits
5. **Multi-cloud abstraction layer** - Too complex and would reduce cloud-specific capabilities

## Evidence Supporting This Decision

- `rocky-linux-hetzner.sh` sets `INVENTORY="hetzner"` by default for Hetzner-specific configurations
- Cloud-specific SSH authentication workflows in Hetzner script
- Provider-specific user management with `check_for_lab_user()` function
- Hetzner-specific networking and storage optimizations
- Different inventory structures for cloud vs. bare-metal deployments
- Cloud provider-specific environment variable configurations

## Implementation Details

### Hetzner Cloud Specific Configuration
```bash
# Hetzner-specific inventory and pipeline settings
export CICD_PIPELINE="false"
export INVENTORY="hetzner"

# Hetzner-specific user management
function check_for_lab_user() {
    if id "lab-user" &>/dev/null; then
        echo "User lab-user exists"
    else
        curl -OL https://gist.githubusercontent.com/tosin2013/385054f345ff7129df6167631156fa2a/raw/b67866c8d0ec220c393ea83d2c7056f33c472e65/configure-sudo-user.sh
        chmod +x configure-sudo-user.sh
        ./configure-sudo-user.sh lab-user
    fi
}
```

### Progressive SSH Security for Cloud Environments
```bash
# Enable SSH password authentication for initial setup
function enable_ssh_password_authentication() {
    sudo sed -i 's/#PasswordAuthentication.*/PasswordAuthentication yes/g' /etc/ssh/sshd_config
    sudo systemctl restart sshd
}

# Disable SSH password authentication after setup
function disable_ssh_password_authentication() {
    sudo sed -i 's/PasswordAuthentication.*/PasswordAuthentication no/g' /etc/ssh/sshd_config
    sudo systemctl restart sshd
}
```

### Cloud Provider Integration Patterns
- **Inventory Mapping**: Cloud-specific inventory configurations
- **Authentication**: Provider-specific authentication and credential management
- **Networking**: Cloud-native networking and security group configurations
- **Storage**: Provider-specific storage and backup configurations
- **Monitoring**: Cloud provider monitoring and alerting integration

### Supported Cloud Providers
- **Hetzner Cloud**: Rocky Linux optimized with Hetzner-specific configurations
- **Equinix Metal**: RHEL 8/9 support with bare-metal optimizations
- **Localhost/Bare-metal**: Direct hardware deployment configurations
- **Extensible**: Framework supports additional cloud provider integrations

## Cloud Provider Characteristics

### Hetzner Cloud Optimizations
- **OS Choice**: Rocky Linux for cost-effectiveness and compatibility
- **Authentication**: Progressive SSH security model
- **User Management**: Automated lab-user provisioning
- **Networking**: Cloud-native networking configurations
- **Cost Optimization**: Streamlined package sets and configurations

### Bare-Metal/RHEL Optimizations
- **Enterprise Features**: Full RHEL enterprise capabilities
- **Hardware Integration**: Direct hardware management and optimization
- **Security**: Enterprise-grade security configurations
- **Performance**: Native hardware performance optimization

## Operational Benefits

- **Cloud Native**: Leverages each cloud provider's native capabilities
- **Cost Optimization**: Provider-specific cost optimization strategies
- **Security**: Cloud provider-specific security and compliance features
- **Performance**: Optimized for each cloud provider's infrastructure
- **Scalability**: Native cloud scaling and auto-scaling capabilities
- **Monitoring**: Integrated with cloud provider monitoring and alerting

## Integration Points

- **Inventory Management**: Cloud-specific inventory configurations
- **Credential Management**: Provider-specific credential and secret management
- **Networking**: Cloud provider networking and security integration
- **Storage**: Provider-specific storage and backup solutions
- **Monitoring**: Cloud provider monitoring and observability integration

## Related Decisions
- ADR-0002: Multi-Cloud Inventory Strategy with Environment-Specific Configurations
- ADR-0004: Security Architecture with Ansible Vault and AnsibleSafe
- ADR-0008: OS-Specific Deployment Script Strategy
- ADR-0010: Progressive SSH Security Model (planned)

## Date
2025-01-09

## Stakeholders
- Cloud Operations Team
- DevOps Team
- Infrastructure Team
- Security Team
- Project Maintainers
