______________________________________________________________________

## layout: default title: ADR-0024 Vault-Integrated Setup Script parent: Security & Operations grand_parent: Architectural Decision Records nav_order: 0024

# ADR-0024: Vault-Integrated Setup Script to Eliminate /tmp/config.yml Security Risk

## Status

Accepted

## Context

The current Qubinode Navigator setup process creates `/tmp/config.yml` containing sensitive credentials (RHEL passwords, tokens, pull secrets) in plaintext before copying and encrypting it. This creates a security window where sensitive data exists unencrypted on the filesystem.

Security analysis revealed:

- `/tmp/config.yml` contains plaintext RHEL subscription credentials
- Red Hat offline tokens and OpenShift pull secrets exposed
- Automation Hub tokens and admin passwords in clear text
- Files persist in `/tmp` until manual cleanup
- Risk of credential exposure through system monitoring or logs

With HashiCorp Vault now integrated and running locally via Podman, we can eliminate this security risk by having the setup script retrieve secrets directly from vault.

## Decision

Implement a vault-integrated setup script (`vault-integrated-setup.sh`) that eliminates the `/tmp/config.yml` security concern by:

1. **Direct Vault Integration**: Retrieve secrets directly from HashiCorp Vault without intermediate files
1. **Secure File Creation**: Create `vault.yml` directly with proper permissions (600)
1. **Memory Protection**: Clear sensitive environment variables after use
1. **Automatic Cleanup**: Remove any temporary files automatically
1. **Dual Mode Support**: Support both CI/CD and interactive modes with vault integration
1. **Backward Compatibility**: Maintain compatibility with existing ansiblesafe workflow
1. **Podman Integration**: Leverage existing Podman-based vault infrastructure

### Implementation Details

```bash
# Vault-integrated approach (secure)
create_vault_yml_from_vault() {
    # Create secure temporary file
    local temp_vault_yml=$(mktemp --suffix=.yml)
    chmod 600 "${temp_vault_yml}"

    # Retrieve secrets directly from vault
    vault kv get -format=json "kv/ansiblesafe/${INVENTORY}" | \
    jq -r '.data.data | to_entries[] | "\(.key): \(.value)"' >> "${temp_vault_yml}"

    # Move to final location and encrypt
    mv "${temp_vault_yml}" "${vault_yml_path}"
    /usr/local/bin/ansiblesafe -f vault.yml -o 1
}
```

## Consequences

### Positive

- **Security Enhancement**: Eliminates plaintext credential exposure in `/tmp/config.yml`
- **Vault Integration**: Leverages existing Podman-based HashiCorp Vault infrastructure
- **Automatic Cleanup**: Removes sensitive data from memory and temporary files
- **Dual Mode Support**: Works in both CI/CD and interactive environments
- **Backward Compatibility**: Existing workflows continue to function
- **Audit Trail**: All secret access goes through vault with proper logging

### Negative

- **Vault Dependency**: Requires vault to be running for enhanced security mode
- **Complexity**: Adds complexity for simple deployments
- **Setup Requirements**: Need to ensure vault secrets are populated before setup

### Risks

- **Vault Connectivity**: Setup process depends on vault availability
- **Secret Population**: Vault must contain required secrets before setup
- **Fallback Handling**: Need proper fallback when vault is unavailable

## Alternatives Considered

1. **Continue using `/tmp/config.yml`**: Rejected due to security concerns
1. **Encrypt `/tmp/config.yml` immediately**: Still creates plaintext window
1. **Environment variables only**: Difficult to manage complex configurations
1. **File-based encryption**: Adds complexity without eliminating exposure window

## Evidence Supporting Decision

- Security analysis confirms `/tmp/config.yml` contains sensitive data
- Podman-based vault is successfully running and integrated
- Enhanced load-variables.py successfully retrieves secrets from vault
- Current CI/CD pipelines already use vault integration patterns
- Security best practices recommend eliminating plaintext credential files

## Implementation Tasks

- [x] Create vault-integrated-setup.sh script
- [x] Implement secure temporary file handling
- [x] Add automatic cleanup of sensitive data
- [x] Support CI/CD and interactive modes
- [x] Test with existing Podman vault infrastructure
- [ ] Update CI/CD pipelines to use new script
- [ ] Create migration guide for existing deployments
- [ ] Add monitoring for vault connectivity issues

## Related ADRs

- ADR-0023: Enhanced Configuration Management with Template Support and HashiCorp Vault Integration
- ADR-0004: Security Architecture with Ansible Vault

## References

- Security analysis of current setup process
- HashiCorp Vault integration documentation
- Podman-based vault setup guide
- Enhanced load-variables.py implementation
