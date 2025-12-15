# Vault Password Setup for Airflow DAGs

This document explains how to configure vault passwords for Airflow DAGs that use Ansible with encrypted variables.

## Problem

When deploying components via kcli-pipelines (e.g., vyos-router, step-ca-server), the deployment scripts expect a `.vault_password` file. Without this file, deployments fail with:

```
ERROR! The vault password file /opt/kcli-pipelines/vyos-router/.vault_password was not found
```

## Solution

The DAG helpers provide functions to automatically ensure vault password files exist before running Ansible commands.

## Configuration Options

### Option 1: Set Airflow Variable (Recommended)

Set a global vault password via Airflow Variable:

```bash
# Via CLI
airflow variables set VAULT_PASSWORD 'your-secure-password'

# Via Airflow UI
# Admin → Variables → Add
# Key: VAULT_PASSWORD
# Value: your-secure-password
```

### Option 2: Create File Manually

Create the vault password file on the host:

```bash
# Create file with secure permissions
echo 'your-secure-password' > ~/.vault_password
chmod 600 ~/.vault_password
```

### Option 3: Environment Variable

Set the vault password file location via environment:

```bash
export QUBINODE_VAULT_PASSWORD_FILE=/path/to/custom/vault_password
```

## Using Vault Password Helpers in DAGs

### 1. Ensure Vault Password Exists

Add a task at the start of your DAG to ensure the vault password file exists:

```python
from dag_helpers import get_ensure_vault_password_command

ensure_vault = BashOperator(
    task_id='ensure_vault_password',
    bash_command=get_ensure_vault_password_command(),
    dag=dag,
)

# Add dependency
ensure_vault >> your_ansible_task
```

### 2. Setup kcli-pipelines Components

For DAGs that call kcli-pipelines deploy scripts, setup symlinks:

```python
from dag_helpers import get_kcli_pipelines_vault_setup_command

setup_vault = BashOperator(
    task_id='setup_kcli_vault',
    bash_command=get_kcli_pipelines_vault_setup_command(['vyos-router']),
    dag=dag,
)

# Add dependencies
ensure_vault >> setup_vault >> deploy_task
```

### 3. Check Vault Password (Validation Only)

For validation tasks that should fail early if vault password is missing:

```python
from dag_helpers import get_vault_password_check_command

validate_vault = BashOperator(
    task_id='validate_vault',
    bash_command=get_vault_password_check_command(),
    dag=dag,
)
```

## Environment Variables

| Variable                       | Default               | Description                           |
| ------------------------------ | --------------------- | ------------------------------------- |
| `QUBINODE_VAULT_PASSWORD_FILE` | `~/.vault_password`   | Path to vault password file           |
| `KCLI_PIPELINES_DIR`           | `/opt/kcli-pipelines` | Path to kcli-pipelines directory      |
| `VAULT_PASSWORD`               | (Airflow Variable)    | Vault password stored in Airflow      |
| `QUBINODE_DEV_MODE`            | `false`               | If true, creates placeholder password |

## Helper Functions Reference

### `get_ensure_vault_password_command()`

Generates bash command to ensure vault password file exists.

**Arguments:**

- `vault_password_file`: Path to vault password file (default: uses `get_vault_password_file()`)
- `default_password_var`: Airflow Variable name for default password (default: `"VAULT_PASSWORD"`)
- `create_if_missing`: Whether to create file if missing (default: `True`)

**Returns:** Bash command string

### `get_kcli_pipelines_vault_setup_command()`

Generates bash command to setup vault password symlinks for kcli-pipelines components.

**Arguments:**

- `components`: List of component names (default: all known components)
- `vault_password_file`: Source vault password file
- `pipelines_dir`: kcli-pipelines directory

**Returns:** Bash command string that creates symlinks

### `get_vault_password_check_command()`

Generates bash command to check if vault password file exists.

**Arguments:**

- `vault_password_file`: Path to check
- `fail_if_missing`: Whether to exit with error if missing (default: `True`)

**Returns:** Bash command string for validation

## Example: Complete DAG with Vault Setup

```python
from datetime import datetime
from airflow import DAG
from airflow.operators.bash import BashOperator
from dag_helpers import (
    get_ensure_vault_password_command,
    get_kcli_pipelines_vault_setup_command,
    get_ssh_user,
)

SSH_USER = get_ssh_user()

dag = DAG(
    'vyos_with_vault_setup',
    start_date=datetime(2025, 1, 1),
    schedule=None,
    catchup=False,
)

# Task 1: Ensure vault password exists
ensure_vault = BashOperator(
    task_id='ensure_vault_password',
    bash_command=get_ensure_vault_password_command(),
    dag=dag,
)

# Task 2: Setup symlinks for kcli-pipelines
setup_kcli_vault = BashOperator(
    task_id='setup_kcli_vault',
    bash_command=get_kcli_pipelines_vault_setup_command(['vyos-router']),
    dag=dag,
)

# Task 3: Deploy VyOS (now vault password is available)
deploy_vyos = BashOperator(
    task_id='deploy_vyos',
    bash_command=f"""
    ssh -o StrictHostKeyChecking=no {SSH_USER}@localhost \
        "cd /opt/kcli-pipelines/vyos-router && ./deploy.sh"
    """,
    dag=dag,
)

# Define dependencies
ensure_vault >> setup_kcli_vault >> deploy_vyos
```

## Troubleshooting

### Error: Vault password file not found

1. Check if the Airflow Variable is set:

   ```bash
   airflow variables get VAULT_PASSWORD
   ```

1. Create the file manually:

   ```bash
   echo 'your-password' > ~/.vault_password
   chmod 600 ~/.vault_password
   ```

1. Verify the symlinks for kcli-pipelines:

   ```bash
   ls -la /opt/kcli-pipelines/*/. vault_password
   ```

### Error: Permission denied

Ensure the vault password file has correct permissions:

```bash
chmod 600 ~/.vault_password
```

### Development Mode

For testing, you can enable development mode to create placeholder passwords:

```bash
export QUBINODE_DEV_MODE=true
```

**Warning:** Do not use development mode in production.

## Related Documentation

- [DAG User Configuration](./DAG-USER-CONFIGURATION.md) - User-configurable paths
- [Migration Guide](./MIGRATION-GUIDE-ROOT-TO-NONROOT.md) - Non-root user setup
- [Issue #123](https://github.com/Qubinode/qubinode_navigator/issues/123) - Original issue
