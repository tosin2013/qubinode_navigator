# Configuration File Sync Guide for Airflow Containers

This guide explains how to make configuration files in user home directories accessible inside Airflow containers.

## Problem

When deploying OpenShift or other infrastructure via Airflow DAGs, configuration files located in user directories (e.g., `/home/vpcuser/openshift-agent-install/`) are not accessible inside Airflow containers because:

1. Volume mounts in `docker-compose.yml` only mount `/root`
1. Configuration files in `/home/username/` are not visible to containers
1. DAGs fail with errors like:

```
[ERROR] Environment file not found: /home/vpcuser/openshift-agent-install/examples/jfrog-disconnected-vlan/env/passthrough.env
```

## Solution

Use the `config-sync.sh` tool to generate a `docker-compose.override.yml` that adds volume mounts for your configuration directories.

## Quick Start

```bash
# 1. Discover configuration directories
./airflow/scripts/config-sync.sh discover

# 2. Edit volume-mounts.yml to add your directories
vim airflow/config/volume-mounts.yml

# 3. Generate the override file
./airflow/scripts/config-sync.sh generate

# 4. Restart Airflow to apply
cd airflow && podman-compose down && podman-compose up -d
```

## Configuration File

Edit `airflow/config/volume-mounts.yml` to define your volume mounts:

```yaml
# Default mounts (common directories)
default_mounts:
  - source: "${HOME}/openshift-agent-install"
    target: "/opt/openshift-agent-install"
    mode: "ro"
    description: "OpenShift agent install configs"

# Add your custom mounts here
custom_mounts:
  - source: "/home/vpcuser/cluster-configs"
    target: "/opt/cluster-configs"
    mode: "ro"
    description: "My cluster configurations"
```

## Commands

### Discover

Find configuration directories on your system:

```bash
./airflow/scripts/config-sync.sh discover
```

Output:

```
[INFO] Discovering configuration directories...
  ✓ Found: /home/vpcuser/openshift-agent-install
  ✓ Found: /home/vpcuser/.generated
  ✓ Found (by cluster.yml): /home/vpcuser/cluster-configs
```

### Generate

Create `docker-compose.override.yml` from your configuration:

```bash
./airflow/scripts/config-sync.sh generate
```

Output:

```
[INFO] Generating docker-compose.override.yml...
[OK] Mount: /home/vpcuser/openshift-agent-install -> /opt/openshift-agent-install (ro)
[OK] Mount: /home/vpcuser/.generated -> /opt/generated (rw)
[OK] Generated docker-compose.override.yml with 2 mounts
```

### Validate

Check that all volume mounts are working:

```bash
./airflow/scripts/config-sync.sh validate
```

## Using in DAGs

### Check Config Files Exist

Add a validation task at the start of your DAG:

```python
from dag_helpers import get_config_check_command

validate_configs = BashOperator(
    task_id='validate_configs',
    bash_command=get_config_check_command([
        "/opt/openshift-agent-install/examples/cluster.yml",
        "/opt/openshift-agent-install/examples/env/passthrough.env",
    ]),
    dag=dag,
)

# Run validation before deployment
validate_configs >> deploy_task
```

### Find Config Files

Use the helper to search multiple locations:

```python
from dag_helpers import get_config_file_path, get_openshift_agent_install_dir

# Get base directory
agent_dir = get_openshift_agent_install_dir()

# Find specific file (searches multiple locations)
try:
    env_file = get_config_file_path("examples/jfrog-disconnected-vlan/env/passthrough.env")
    print(f"Found: {env_file}")
except FileNotFoundError as e:
    print(f"Config not found: {e}")
```

## Environment Variables

| Variable                      | Description                           |
| ----------------------------- | ------------------------------------- |
| `OPENSHIFT_AGENT_INSTALL_DIR` | Override OpenShift agent install path |

## Path Mappings

| Host Path                   | Container Path                 | Purpose             |
| --------------------------- | ------------------------------ | ------------------- |
| `~/openshift-agent-install` | `/opt/openshift-agent-install` | OpenShift configs   |
| `~/.generated`              | `/opt/generated`               | Generated inventory |
| `~/kcli-pipelines`          | `/opt/kcli-pipelines`          | Deployment scripts  |

## Example: OpenShift JFrog Deployment

```python
from datetime import datetime
from airflow import DAG
from airflow.operators.bash import BashOperator
from dag_helpers import get_config_check_command, get_ssh_user

SSH_USER = get_ssh_user()

dag = DAG(
    'ocp_jfrog_deployment',
    start_date=datetime(2025, 1, 1),
    schedule=None,
)

# Validate configs are accessible
validate = BashOperator(
    task_id='validate_configs',
    bash_command=get_config_check_command([
        "/opt/openshift-agent-install/examples/jfrog-disconnected-vlan/cluster.yml",
        "/opt/openshift-agent-install/examples/jfrog-disconnected-vlan/env/passthrough.env",
    ]),
    dag=dag,
)

# Deploy using the config
deploy = BashOperator(
    task_id='deploy_cluster',
    bash_command=f"""
    ssh -o StrictHostKeyChecking=no {SSH_USER}@localhost \
        "cd /opt/openshift-agent-install && ./deploy.sh"
    """,
    dag=dag,
)

validate >> deploy
```

## Troubleshooting

### Config File Not Found in Container

1. Check if the file exists on host:

   ```bash
   ls -la ~/openshift-agent-install/examples/
   ```

1. Run discover to find config directories:

   ```bash
   ./airflow/scripts/config-sync.sh discover
   ```

1. Generate and apply volume mounts:

   ```bash
   ./airflow/scripts/config-sync.sh generate
   cd airflow && podman-compose down && podman-compose up -d
   ```

### Override File Not Applied

Ensure `docker-compose.override.yml` exists:

```bash
ls -la airflow/docker-compose.override.yml
```

Restart containers to pick up changes:

```bash
cd airflow && podman-compose down && podman-compose up -d
```

### Permission Denied

If configs need write access, change mode from `ro` to `rw`:

```yaml
custom_mounts:
  - source: "/home/vpcuser/generated-assets"
    target: "/opt/generated-assets"
    mode: "rw"  # Read-write access
```

## Related Documentation

- [DAG User Configuration](./DAG-USER-CONFIGURATION.md)
- [Vault Password Setup](./VAULT-PASSWORD-SETUP.md)
- [Issue #124](https://github.com/Qubinode/qubinode_navigator/issues/124)
