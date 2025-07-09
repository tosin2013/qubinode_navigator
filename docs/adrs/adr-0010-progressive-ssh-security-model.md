# ADR-0010: Progressive SSH Security Model

## Status
Accepted

## Context
Qubinode Navigator deployments, particularly in cloud environments like Hetzner, face a security challenge during initial setup. Cloud instances often require password-based SSH authentication for initial access and configuration, but production security best practices mandate key-based authentication with password authentication disabled. The project needed a security model that balances initial accessibility for automated setup with long-term security hardening, while ensuring the transition between security states is automated and reliable.

## Decision
Implement a progressive SSH security model that transitions from permissive initial setup to hardened production configuration through automated phases. The model includes functions to enable password authentication during initial setup and configuration deployment, followed by automatic disabling of password authentication and enforcement of key-based authentication once the system is fully configured and operational.

## Consequences

### Positive Consequences
- Enables automated initial setup in cloud environments requiring password authentication
- Provides clear security progression from setup to production state
- Reduces manual intervention required for security hardening
- Ensures consistent security posture across all deployed environments
- Facilitates automated deployment in cloud environments with initial password requirements
- Maintains audit trail of security state transitions
- Supports both cloud and bare-metal deployment scenarios

### Negative Consequences  
- Temporary security exposure during initial setup phase with password authentication enabled
- Complexity in managing security state transitions and ensuring they complete successfully
- Risk of deployment failure leaving systems in permissive security state
- Requires careful coordination between setup phases to avoid security gaps
- Additional testing required to validate security transitions
- Potential for human error if manual intervention is required during transition

## Alternatives Considered

1. **Key-based authentication only** - Rejected due to cloud provider initial setup requirements
2. **Manual security hardening post-deployment** - Rejected due to automation goals and human error risk
3. **Cloud provider-specific key injection** - Limited to specific providers and reduces portability
4. **VPN-based initial access** - Too complex for automated deployment scenarios
5. **Immutable infrastructure with pre-hardened images** - Would require maintaining multiple cloud provider images

## Evidence Supporting This Decision

- `rocky-linux-hetzner.sh` implements progressive SSH security functions
- Cloud environments like Hetzner require password authentication for initial access
- Automated security hardening reduces operational overhead and human error
- Security state transitions are logged and auditable
- Function-based implementation allows selective security state management

## Implementation Details

### Progressive Security Functions
```bash
# Phase 1: Enable password authentication for initial setup
function enable_ssh_password_authentication() {
    echo "Enabling ssh password authentication"
    echo "*************************************"
    sudo sed -i 's/#PasswordAuthentication.*/PasswordAuthentication yes/g' /etc/ssh/sshd_config
    sudo systemctl restart sshd
}

# Phase 3: Disable password authentication for production security
function disable_ssh_password_authentication() {
    echo "Disabling ssh password authentication"
    echo "**************************************"
    sudo sed -i 's/PasswordAuthentication.*/PasswordAuthentication no/g' /etc/ssh/sshd_config
    sudo systemctl restart sshd
}
```

### Security Transition Workflow
1. **Initial State**: Cloud instance with password authentication required
2. **Setup Phase**: Enable password authentication for automated configuration
3. **Configuration Phase**: Deploy SSH keys, users, and system configuration
4. **Hardening Phase**: Disable password authentication, enforce key-based access
5. **Production State**: Secure key-based authentication only

### SSH Configuration Management
```bash
# SSH configuration validation
function validate_ssh_keys() {
    if [ -f ~/.ssh/id_rsa ]; then
        echo "SSH key already exists"
    else
        ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N ""
        cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys
        chmod 600 ~/.ssh/authorized_keys
    fi
}
```

### Security State Verification
- **Pre-hardening checks**: Verify SSH keys are properly deployed
- **Post-hardening validation**: Test key-based authentication functionality
- **Rollback capability**: Ability to re-enable password auth if key auth fails
- **Audit logging**: Log all security state transitions

## Security Phases

### Phase 1: Permissive Setup
- **SSH Password Auth**: Enabled for initial access
- **Purpose**: Allow automated configuration and key deployment
- **Duration**: Minimal - only during active setup
- **Monitoring**: Setup progress tracking

### Phase 2: Configuration Deployment
- **SSH Key Setup**: Deploy and configure SSH keys
- **User Management**: Create and configure service accounts
- **System Configuration**: Deploy system and application configurations
- **Validation**: Verify all configurations are properly deployed

### Phase 3: Security Hardening
- **SSH Password Auth**: Disabled
- **Key-based Auth**: Enforced as only authentication method
- **Validation**: Test key-based authentication functionality
- **Monitoring**: Continuous security posture monitoring

## Risk Mitigation

### Security Exposure Minimization
- **Time-limited**: Password authentication enabled only during active setup
- **Automated**: No manual intervention required for security transitions
- **Validated**: Each phase includes validation before proceeding
- **Audited**: All security state changes are logged

### Failure Recovery
- **Rollback Procedures**: Ability to re-enable password auth if needed
- **Validation Checks**: Verify key-based auth before disabling password auth
- **Emergency Access**: Documented procedures for emergency access
- **Monitoring**: Automated monitoring of security state transitions

## Operational Procedures

### Deployment Workflow
1. **Pre-deployment**: Verify cloud provider requirements
2. **Initial Access**: Use cloud provider credentials for initial access
3. **Setup Execution**: Run progressive security setup functions
4. **Validation**: Verify security hardening completed successfully
5. **Production**: Monitor and maintain hardened security posture

### Monitoring and Alerting
- **Security State Monitoring**: Track SSH authentication configuration
- **Failed Authentication Alerts**: Monitor for authentication failures
- **Configuration Drift Detection**: Detect unauthorized security changes
- **Compliance Reporting**: Regular security posture reporting

## Related Decisions
- ADR-0004: Security Architecture with Ansible Vault and AnsibleSafe
- ADR-0008: OS-Specific Deployment Script Strategy
- ADR-0009: Cloud Provider-Specific Configuration Management

## Date
2025-01-09

## Stakeholders
- Security Team
- Cloud Operations Team
- DevOps Team
- Infrastructure Team
- Compliance Team
- Project Maintainers
