# ADR-0044: User-Configurable Airflow Volume Mounts

## Status
Proposed

## Date
2025-11-27

## Context and Problem Statement

The current Airflow deployment requires modifying `docker-compose.yml` to add volume mounts for external repositories such as:
- `freeipa-workshop-deployer` - Ansible playbooks for FreeIPA installation
- `kcli-pipelines` - VM deployment scripts and DAGs
- `qubinode_navigator` - Vault credentials and inventory files

This approach is not user-friendly because:
1. Requires container rebuilds after each change
2. Core configuration gets modified, complicating upgrades
3. Users must understand docker-compose syntax
4. DAGs fail when required paths are not mounted (e.g., vault.yml not accessible)

DAGs need access to host paths for:
- `vault.yml` - Encrypted credentials (freeipa_server_admin_password, rhsm credentials)
- Ansible playbooks and collections
- SSH keys for VM access
- Inventory files for Ansible
- Generated files (e.g., `~/.generated/` for dynamic inventories)

## Decision Drivers

* Users need to mount host directories without modifying core configuration
* Upgrades to `docker-compose.yml` should not overwrite user customizations
* Configuration must support environment variable expansion for dynamic paths
* Security: Prevent arbitrary mounts to sensitive host paths
* Simplicity: Easy for users to add new mounts

## Considered Options

### Option 1: Hardcode All Mounts in docker-compose.yml
- **Pros**: Simple, no additional configuration
- **Cons**: Inflexible, requires rebuild for changes, bloats compose file

### Option 2: Use Docker Named Volumes
- **Pros**: Portable, managed by Docker
- **Cons**: Doesn't work for existing host directories, complex data migration

### Option 3: Run Airflow Directly on Host
- **Pros**: Full host access, no mount issues
- **Cons**: Loses container isolation, harder to manage dependencies

### Option 4: User-Configurable Mount System (Recommended)
- **Pros**: Flexible, upgrade-safe, user-friendly
- **Cons**: Requires documentation, potential security considerations

## Decision Outcome

**Chosen Option**: Implement a user-configurable volume mount system with:

### 1. Environment File for Custom Mounts (`airflow/.env.local`)
```bash
# User-defined volume mounts (one per line, format: host_path:container_path[:options])
AIRFLOW_EXTRA_VOLUMES="
/root/freeipa-workshop-deployer:/opt/freeipa-workshop-deployer
/root/kcli-pipelines:/opt/kcli-pipelines:ro
/root/qubinode_navigator:/opt/qubinode_navigator:ro
/root/.ssh:/root/.ssh:ro
"
```

### 2. Standard Mounts Directory (`airflow/mounts/`)
```
airflow/mounts/
├── README.md           # Documentation
├── freeipa/            # Symlink to /root/freeipa-workshop-deployer
├── kcli-pipelines/     # Symlink to /root/kcli-pipelines
└── qubinode/           # Symlink to /root/qubinode_navigator
```

### 3. Docker Compose Integration
```yaml
# In docker-compose.yml
volumes:
  # Core mounts (always present)
  - ${AIRFLOW_PROJ_DIR:-.}/dags:/opt/airflow/dags
  - ${AIRFLOW_PROJ_DIR:-.}/logs:/opt/airflow/logs
  # User-configurable mounts directory
  - ${AIRFLOW_PROJ_DIR:-.}/mounts:/opt/airflow/mounts
  # Additional mounts from .env.local (parsed by wrapper script)
```

### 4. Wrapper Script for Mount Expansion
Create `airflow/start-airflow.sh` that:
1. Reads `.env.local` for custom mounts
2. Generates a temporary docker-compose override file
3. Starts services with the override

## Implementation

### Phase 1: Immediate Fix (Current)
Add standard mounts to `docker-compose.yml`:
```yaml
# Mount qubinode_navigator for vault.yml and inventory access
- /root/qubinode_navigator:/opt/qubinode_navigator:ro
# Mount freeipa-workshop-deployer for Ansible playbooks
- /root/freeipa-workshop-deployer:/opt/freeipa-workshop-deployer
# Mount kcli-pipelines for scripts
- /root/kcli-pipelines:/opt/kcli-pipelines:ro
# Mount SSH keys for Ansible
- /root/.ssh:/root/.ssh:ro
# Mount home directory for .generated inventory
- /root:/root
```

### Phase 2: User-Configurable System
1. Create `airflow/mounts/` directory structure
2. Implement `.env.local` parsing in deploy script
3. Document mount configuration format
4. Add validation for security-sensitive paths

## Consequences

### Positive
- Users can add custom mounts without modifying docker-compose.yml
- Core configuration upgrades don't overwrite user customizations
- Supports environment variable expansion for dynamic paths
- DAGs can access required host resources (vault, playbooks, SSH keys)

### Negative
- Requires documentation for mount configuration format
- Potential security risks with arbitrary mounts (mitigated by validation)
- Slightly more complex deployment process

## Security Considerations

1. **Read-only mounts** for sensitive directories (SSH keys, credentials)
2. **Validation script** to warn about potentially dangerous mounts
3. **Documentation** of safe mount practices
4. **Default deny** for mounts outside approved directories

## Related ADRs

- ADR-0036: Airflow Integration Architecture
- ADR-0037: Git-Based DAG Repository Management
- ADR-0043: Airflow Container Host Network Access

## References

- Docker Compose volumes documentation
- Podman volume mount syntax
- FreeIPA deployment requirements from freeipa-workshop-deployer
