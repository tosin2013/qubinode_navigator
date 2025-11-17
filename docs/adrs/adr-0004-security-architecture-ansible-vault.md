---
layout: default
title: ADR-0004 Security Architecture
parent: Security & Operations
grand_parent: Architectural Decision Records
nav_order: 1
---

# ADR-0004: Security Architecture with Ansible Vault and AnsibleSafe

## Status
Accepted

## Context
Qubinode Navigator handles sensitive information including cloud provider API keys, SSH private keys, database passwords, and other credentials required for infrastructure automation. This sensitive data must be stored securely, managed consistently across different environments, and accessed safely during automated deployments. The project needed a security architecture that would protect credentials at rest and in transit while maintaining usability for both interactive and CI/CD deployments.

## Decision
Implement a dual-layer security architecture combining Ansible Vault for encryption with AnsibleSafe for enhanced credential management. All sensitive variables are stored in encrypted `vault.yml` files within each inventory's `group_vars/control/` directory. AnsibleSafe provides additional security features including secure credential input, validation, and automated vault file management.

## Consequences

### Positive Consequences
- Provides strong encryption for sensitive data at rest using AES-256
- Enables secure credential management across multiple environments
- Supports both interactive and automated deployment scenarios
- Integrates seamlessly with existing Ansible workflows
- Allows granular access control per environment/inventory
- Facilitates secure CI/CD pipeline integration
- Provides audit trail for credential access and modifications

### Negative Consequences  
- Adds complexity to credential management workflows
- Requires secure distribution and management of vault passwords
- May impact deployment performance due to encryption/decryption overhead
- Requires team training on secure credential handling practices
- Potential for lockout if vault passwords are lost or corrupted
- Additional dependency on AnsibleSafe tool and its maintenance

## Alternatives Considered

1. **Plain text credentials in version control** - Rejected due to obvious security risks
2. **Environment variables only** - Insufficient for complex multi-environment scenarios
3. **External secret management systems (HashiCorp Vault, AWS Secrets Manager)** - Too complex for current requirements
4. **Ansible Vault alone** - Enhanced with AnsibleSafe for better usability and security
5. **Encrypted configuration files with custom tooling** - Ansible Vault chosen for ecosystem integration

## Evidence Supporting This Decision

- Vault files present in each inventory: `group_vars/control/vault.yml`
- AnsibleSafe integration in setup scripts: `/usr/local/bin/ansiblesafe`
- Vault password file management: `~/.vault_password`
- Secure credential input workflows in setup processes
- Environment-specific vault configurations
- CI/CD integration with automated vault handling

## Implementation Details

### Vault File Structure
```yaml
# inventories/{environment}/group_vars/control/vault.yml
vault_api_key: !vault |
  $ANSIBLE_VAULT;1.1;AES256
  [encrypted content]
vault_ssh_private_key: !vault |
  $ANSIBLE_VAULT;1.1;AES256
  [encrypted content]
```

### AnsibleSafe Integration
```bash
# From qubinode_navigator.sh
if [ ! -f /usr/local/bin/ansiblesafe ]; then
    curl -OL https://github.com/tosin2013/ansiblesafe/releases/download/v${ANSIBLE_SAFE_VERSION}/ansiblesafe-v${ANSIBLE_SAFE_VERSION}-linux-amd64.tar.gz
    tar -zxvf ansiblesafe-v${ANSIBLE_SAFE_VERSION}-linux-amd64.tar.gz
    sudo mv ansiblesafe-linux-amd64 /usr/local/bin/ansiblesafe
fi
```

### Vault Management Workflow
```bash
# Interactive mode
/usr/local/bin/ansiblesafe -f /root/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml

# CI/CD mode
/usr/local/bin/ansiblesafe -f /root/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml -o 1
```

### Security Features
- **Encryption**: AES-256 encryption for all sensitive data
- **Access Control**: Environment-specific vault files with separate passwords
- **Validation**: AnsibleSafe provides input validation and secure prompting
- **Automation Support**: Supports both interactive and non-interactive modes
- **Version Control Safe**: Encrypted files can be safely committed to repositories

### HashiCorp Vault Integration (Optional)
```bash
# Optional HashiCorp Vault support
if [ -z "$USE_HASHICORP_VAULT" ]; then
  export USE_HASHICORP_VAULT="false"
else
    if [[ -z "$VAULT_ADDRESS" && -z "$VAULT_TOKEN" && -z ${SECRET_PATH} ]]; then
      echo "VAULT environment variables are not set"
      exit 1
    fi
fi
```

### Credential Lifecycle Management
1. **Creation**: AnsibleSafe prompts for secure credential input
2. **Storage**: Credentials encrypted and stored in environment-specific vault files
3. **Access**: Ansible automatically decrypts during playbook execution
4. **Rotation**: Manual process using AnsibleSafe to update vault files
5. **Audit**: Git history provides audit trail of vault file changes

## Security Best Practices Implemented

- **Principle of Least Privilege**: Environment-specific vault files limit credential scope
- **Defense in Depth**: Multiple layers of security (encryption + access control)
- **Secure by Default**: All sensitive data encrypted by default
- **Separation of Concerns**: Credentials separated from configuration logic
- **Audit Trail**: Version control provides change tracking

## Related Decisions
- ADR-0001: Container-First Execution Model with Ansible Navigator
- ADR-0002: Multi-Cloud Inventory Strategy with Environment-Specific Configurations
- ADR-0003: Dynamic Configuration Management with Python

## Date
2025-01-09

## Stakeholders
- Security Team
- DevOps Team
- Infrastructure Team
- Compliance Team
- Project Maintainers
