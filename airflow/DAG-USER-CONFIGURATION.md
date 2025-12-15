# DAG User Configuration Guide

## Overview

As of this update, all Airflow DAGs in `qubinode_navigator` are now **user-portable** and no longer hardcoded to use the `root` user. This allows DAGs to run successfully under any user account (e.g., `cloud-user`, `vpcuser`, etc.).

## Environment Variables

Configure the following environment variables to customize DAG behavior for your user context:

### `QUBINODE_SSH_USER`

**Purpose:** Specifies the SSH user for connecting to the host system from Airflow containers.

**Default:** Current user from `$USER` environment variable, falls back to `root` if not set.

**Example:**

```bash
export QUBINODE_SSH_USER=vpcuser
```

### `QUBINODE_SSH_KEY_PATH`

**Purpose:** Path to the SSH private key used for host authentication.

**Default:** `~/.ssh/id_rsa` (expands to current user's home directory)

**Example:**

```bash
export QUBINODE_SSH_KEY_PATH=/home/vpcuser/.ssh/id_rsa
```

### `QUBINODE_INVENTORY_DIR`

**Purpose:** Directory where Ansible inventory files are generated and stored.

**Default:** `~/.generated` (expands to current user's home directory)

**Example:**

```bash
export QUBINODE_INVENTORY_DIR=/home/vpcuser/.generated
```

### `QUBINODE_VAULT_PASSWORD_FILE`

**Purpose:** Path to the Ansible Vault password file.

**Default:** `~/.vault_password` (expands to current user's home directory)

**Example:**

```bash
export QUBINODE_VAULT_PASSWORD_FILE=/home/vpcuser/.vault_password
```

### `QUBINODE_PULL_SECRET_PATH`

**Purpose:** Path to the OpenShift pull secret JSON file.

**Default:** `~/pull-secret.json` (expands to current user's home directory)

**Example:**

```bash
export QUBINODE_PULL_SECRET_PATH=/home/vpcuser/pull-secret.json
```

## Configuration Methods

### Method 1: Environment Variables (Recommended)

Set environment variables in your shell or systemd service file:

```bash
# In ~/.bashrc or ~/.bash_profile
export QUBINODE_SSH_USER=vpcuser
export QUBINODE_SSH_KEY_PATH=/home/vpcuser/.ssh/id_rsa
export QUBINODE_INVENTORY_DIR=/home/vpcuser/.generated
```

### Method 2: Airflow Environment Configuration

Add to `airflow/config/airflow.env`:

```ini
QUBINODE_SSH_USER=vpcuser
QUBINODE_SSH_KEY_PATH=/home/vpcuser/.ssh/id_rsa
QUBINODE_INVENTORY_DIR=/home/vpcuser/.generated
```

### Method 3: Docker/Podman Compose

Add to `docker-compose.yml` or `podman-compose.yml`:

```yaml
services:
  airflow-webserver:
    environment:
      - QUBINODE_SSH_USER=vpcuser
      - QUBINODE_SSH_KEY_PATH=/home/vpcuser/.ssh/id_rsa
      - QUBINODE_INVENTORY_DIR=/home/vpcuser/.generated
```

## Usage Examples

### Running as Non-Root User

```bash
# Set your user context
export QUBINODE_SSH_USER=vpcuser
export QUBINODE_SSH_KEY_PATH=/home/vpcuser/.ssh/id_rsa

# Start Airflow
cd airflow
podman-compose up -d

# Trigger a DAG
airflow dags trigger freeipa_deployment
```

### Multiple User Contexts

Different users can run the same DAGs with different configurations:

**User 1 (vpcuser):**

```bash
export QUBINODE_SSH_USER=vpcuser
export QUBINODE_INVENTORY_DIR=/home/vpcuser/.generated
```

**User 2 (cloud-user):**

```bash
export QUBINODE_SSH_USER=cloud-user
export QUBINODE_INVENTORY_DIR=/home/cloud-user/.generated
```

## SSH Key Setup

Ensure your SSH keys are properly configured:

```bash
# Generate SSH key if needed
ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa

# Copy public key to localhost for host access
ssh-copy-id -i ~/.ssh/id_rsa.pub localhost

# Test SSH connection
ssh -o StrictHostKeyChecking=no localhost "echo 'SSH works!'"
```

## Troubleshooting

### Issue: DAG fails with "Permission denied (publickey)"

**Solution:** Check that your SSH user and key path are correct:

```bash
echo $QUBINODE_SSH_USER
ls -la $QUBINODE_SSH_KEY_PATH
ssh -i $QUBINODE_SSH_KEY_PATH $QUBINODE_SSH_USER@localhost "echo test"
```

### Issue: Cannot write to inventory directory

**Solution:** Ensure the inventory directory exists and is writable:

```bash
mkdir -p $QUBINODE_INVENTORY_DIR
chmod 755 $QUBINODE_INVENTORY_DIR
ls -ld $QUBINODE_INVENTORY_DIR
```

### Issue: DAGs still reference root user

**Solution:** Clear Airflow cache and restart services:

```bash
cd airflow
podman-compose down
podman-compose up -d
```

## Migration from Hardcoded Root

If you were previously running DAGs as root and want to migrate to a non-root user:

1. **Copy SSH keys:**

   ```bash
   sudo cp -r /root/.ssh /home/vpcuser/
   sudo chown -R vpcuser:vpcuser /home/vpcuser/.ssh
   ```

1. **Copy generated files:**

   ```bash
   sudo cp -r /root/.generated /home/vpcuser/
   sudo chown -R vpcuser:vpcuser /home/vpcuser/.generated
   ```

1. **Set environment variables:**

   ```bash
   export QUBINODE_SSH_USER=vpcuser
   export QUBINODE_SSH_KEY_PATH=/home/vpcuser/.ssh/id_rsa
   export QUBINODE_INVENTORY_DIR=/home/vpcuser/.generated
   ```

1. **Restart Airflow:**

   ```bash
   cd airflow
   podman-compose restart
   ```

## Technical Details

### Helper Functions

The following helper functions in `dag_helpers.py` provide the user configuration:

- `get_ssh_user()` - Returns configured SSH user
- `get_ssh_key_path()` - Returns SSH key path
- `get_inventory_dir()` - Returns inventory directory path
- `get_vault_password_file()` - Returns vault password file path
- `get_pull_secret_path()` - Returns pull secret path

### DAGs Updated

All DAGs that perform SSH operations or file I/O have been updated to use these helper functions:

- `freeipa_deployment.py`
- `vyos_router_deployment.py`
- `step_ca_deployment.py`
- `step_ca_operations.py`
- `dns_management.py`
- `registry_deployment.py`
- And 10 more DAG files

### Backward Compatibility

The defaults maintain backward compatibility with root user deployments:

- If no environment variables are set and `$USER` is `root`, behavior is identical to previous versions
- Existing deployments continue to work without configuration changes

## Related Documentation

- [ADR-0046: DAG Validation Pipeline and Host-Based Execution](../docs/adrs/)
- [Airflow Deployment Guide](./README.md)
- [SSH Configuration Guide](./FIREWALL-SETUP.md)

## Support

For issues or questions, please open an issue in the GitHub repository with the tag `airflow` and `dags`.
