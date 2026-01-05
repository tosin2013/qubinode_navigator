# SSH Connection Setup for Airflow DAGs

This guide explains how to configure SSH connections for Airflow DAGs that need to execute commands on the host system.

## Overview

Airflow DAGs use the SSHOperator to execute commands on the host machine (kcli, virsh, ansible-playbook, etc.) from within the Airflow container. This provides:

- ✅ Centralized SSH configuration
- ✅ Connection pooling and reuse
- ✅ Built-in retry logic
- ✅ Better error messages
- ✅ No string concatenation bugs

## Prerequisites

1. SSH server running on host (typically already installed)
1. SSH key-based authentication configured
1. Airflow containers running with host network access (ADR-0043)

## Setup Methods

### Method 1: Using Airflow CLI (Recommended)

From the host machine or inside the Airflow scheduler container:

```bash
# Get your admin user (typically the user running the Airflow deployment)
export ADMIN_USER=${QUBINODE_ADMIN_USER:-$(whoami)}

# Create SSH connection for localhost
airflow connections add 'localhost_ssh' \
    --conn-type 'ssh' \
    --conn-host 'localhost' \
    --conn-login "${ADMIN_USER}" \
    --conn-extra '{"key_file": "/root/.ssh/id_rsa"}'
```

### Method 2: Using Airflow Web UI

1. Navigate to **Admin → Connections** in the Airflow UI (http://localhost:8888)

1. Click **+** to add a new connection

1. Fill in the form:

   - **Connection Id**: `localhost_ssh`
   - **Connection Type**: SSH
   - **Host**: `localhost`
   - **Username**: Your admin user (e.g., `root` or your username)
   - **Extra**: `{"key_file": "/root/.ssh/id_rsa"}`

1. Click **Save**

### Method 3: Using Environment Variables

Add to your `docker-compose.yml` or `.env` file:

```yaml
environment:
  AIRFLOW_CONN_LOCALHOST_SSH: 'ssh://root@localhost?key_file=/root/.ssh/id_rsa'
```

Or in `.env`:

```bash
AIRFLOW_CONN_LOCALHOST_SSH='ssh://root@localhost?key_file=/root/.ssh/id_rsa'
```

## Verification

Test the SSH connection:

```bash
# From host
cd /path/to/qubinode_navigator/airflow
docker-compose exec airflow-scheduler airflow connections test localhost_ssh

# Expected output:
# Connection successfully tested
```

Or test manually:

```bash
# From inside the scheduler container
docker-compose exec airflow-scheduler bash
airflow connections get localhost_ssh
ssh -o StrictHostKeyChecking=no localhost 'echo SSH works'
```

## Connection Configuration Options

The SSH connection supports these Extra fields (JSON format):

```json
{
  "key_file": "/root/.ssh/id_rsa",           // SSH private key path
  "timeout": 10,                              // Connection timeout (seconds)
  "compress": true,                           // Enable SSH compression
  "no_host_key_check": true,                  // Skip host key verification
  "allow_host_key_change": false,             // Allow host key changes
  "look_for_keys": true,                      // Search for SSH keys
  "cmd_timeout": 300                          // Command execution timeout
}
```

### Common Configurations

**Using password instead of key:**

```bash
airflow connections add 'localhost_ssh' \
    --conn-type 'ssh' \
    --conn-host 'localhost' \
    --conn-login 'root' \
    --conn-password 'your-password'
```

**Using non-standard SSH port:**

```bash
airflow connections add 'localhost_ssh' \
    --conn-type 'ssh' \
    --conn-host 'localhost' \
    --conn-port '2222' \
    --conn-login 'root' \
    --conn-extra '{"key_file": "/root/.ssh/id_rsa"}'
```

**For remote hosts (not localhost):**

```bash
airflow connections add 'remote_host_ssh' \
    --conn-type 'ssh' \
    --conn-host '192.168.1.100' \
    --conn-login 'admin' \
    --conn-extra '{"key_file": "/root/.ssh/id_rsa"}'
```

## Using in DAGs

### Basic Example

```python
from airflow import DAG
from airflow.providers.ssh.operators.ssh import SSHOperator
from dag_helpers import get_ssh_conn_id

# Create task
list_vms = SSHOperator(
    task_id='list_vms',
    ssh_conn_id=get_ssh_conn_id(),  # Uses 'localhost_ssh' by default
    command='kcli list vm',
    dag=dag,
)
```

### Using Helper Functions

The `dag_helpers.py` module provides convenience functions:

```python
from dag_helpers import create_ssh_operator, create_kcli_ssh_operator

# Generic SSH command
validate = create_ssh_operator(
    task_id='validate_environment',
    command='virsh list --all',
    dag=dag,
    cmd_timeout=30,
)

# kcli-specific command (automatically adds 'kcli' prefix)
create_vm = create_kcli_ssh_operator(
    task_id='create_vm',
    kcli_command='create vm freeipa -i centos9stream',
    dag=dag,
    cmd_timeout=600,
)
```

### Multi-line Commands

```python
validate_env = SSHOperator(
    task_id='validate_environment',
    ssh_conn_id=get_ssh_conn_id(),
    command="""
    echo "Checking kcli..."
    if ! command -v kcli &> /dev/null; then
        echo "[ERROR] kcli not installed"
        exit 1
    fi
    echo "[OK] kcli installed"

    echo "Checking libvirt..."
    virsh list --all
    echo "[OK] libvirt accessible"
    """,
    dag=dag,
)
```

## Troubleshooting

### Connection Test Fails

**Error**: `Connection refused` or `Permission denied`

**Solutions**:

1. Verify SSH service is running on host:

   ```bash
   systemctl status sshd
   ```

1. Check SSH key permissions:

   ```bash
   chmod 600 /root/.ssh/id_rsa
   chmod 644 /root/.ssh/id_rsa.pub
   ```

1. Verify SSH key is authorized:

   ```bash
   cat /root/.ssh/id_rsa.pub >> /root/.ssh/authorized_keys
   chmod 600 /root/.ssh/authorized_keys
   ```

1. Test SSH manually:

   ```bash
   ssh -i /root/.ssh/id_rsa -o StrictHostKeyChecking=no localhost 'echo test'
   ```

### Commands Fail in DAG

**Error**: `Command not found` (e.g., kcli, virsh)

**Solution**: Commands may not be in PATH. Use full paths or add PATH:

```python
command="""
export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"
kcli list vm
"""
```

**Error**: `Connection timeout`

**Solution**: Increase timeout in connection Extra or operator:

```python
SSHOperator(
    task_id='long_running_task',
    ssh_conn_id=get_ssh_conn_id(),
    command='long-running-command',
    cmd_timeout=1800,  # 30 minutes
    dag=dag,
)
```

### Host Key Verification Failed

**Solution**: Disable host key checking in connection Extra:

```json
{
  "key_file": "/root/.ssh/id_rsa",
  "no_host_key_check": true
}
```

## Environment Variable Override

You can override the default SSH connection ID using:

```bash
# In docker-compose.yml or .env
QUBINODE_SSH_CONN_ID=my_custom_ssh_connection
```

This affects `get_ssh_conn_id()` in all DAGs.

## Security Considerations

1. **Key Management**: Store SSH private keys securely, never in git
1. **Connection Secrets**: Use Airflow's secrets backend for production
1. **Least Privilege**: Use dedicated user accounts with minimal permissions
1. **Audit Logging**: Enable SSH audit logging for compliance
1. **Key Rotation**: Regularly rotate SSH keys

## Migrating from Manual SSH

If you have existing DAGs using BashOperator with manual SSH:

**Before (Manual SSH - Buggy)**:

```python
validate = BashOperator(
    task_id="validate",
    bash_command="""
    ssh -o StrictHostKeyChecking=no " + SSH_USER + "@localhost '
        kcli list vm
    '
    """,
)
```

**After (SSHOperator - Clean)**:

```python
validate = SSHOperator(
    task_id="validate",
    ssh_conn_id=get_ssh_conn_id(),
    command="kcli list vm",
)
```

Benefits:

- ✅ No string concatenation bugs
- ✅ Cleaner code
- ✅ Better error handling
- ✅ Connection reuse

## CI/CD Setup

When running Airflow DAGs in CI/CD pipelines (GitHub Actions, GitLab CI, etc.), the `localhost_ssh` connection must be created programmatically after Airflow starts.

### GitHub Actions Example

Add this step after the Airflow scheduler is ready:

```yaml
- name: Create localhost_ssh Airflow connection
  run: |
    # Determine SSH user and key path
    SSH_USER="${QUBINODE_ADMIN_USER:-root}"
    if [ "$SSH_USER" = "root" ]; then
      SSH_HOME="/root"
    else
      SSH_HOME=$(getent passwd "$SSH_USER" | cut -d: -f6 || echo "/home/$SSH_USER")
    fi
    SSH_KEY_PATH="$SSH_HOME/.ssh/id_rsa"

    # Delete existing connection if present (idempotent)
    sudo podman exec $AIRFLOW_SCHEDULER_CONTAINER \
      airflow connections delete localhost_ssh 2>/dev/null || true

    # Create the localhost_ssh connection
    sudo podman exec $AIRFLOW_SCHEDULER_CONTAINER \
      airflow connections add 'localhost_ssh' \
        --conn-type 'ssh' \
        --conn-host 'localhost' \
        --conn-login "$SSH_USER" \
        --conn-extra "{\"key_file\": \"$SSH_KEY_PATH\", \"no_host_key_check\": true}"

    # Verify connection
    sudo podman exec $AIRFLOW_SCHEDULER_CONTAINER \
      airflow connections get localhost_ssh
```

### Prerequisites for CI/CD

Before creating the connection, ensure:

1. **SSH keys are generated** on the CI runner:

   ```bash
   ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N '' -q
   ```

1. **SSH key is authorized** for localhost access:

   ```bash
   cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys
   chmod 600 ~/.ssh/authorized_keys
   ```

1. **SSH service is running** on the CI runner:

   ```bash
   systemctl start sshd
   ```

1. **Airflow scheduler container** can reach localhost:

   - Use `--network host` or ensure proper network configuration
   - Mount the SSH key into the container if needed

### Common CI/CD Errors

**Error**: `The conn_id 'localhost_ssh' isn't defined`

**Cause**: The connection was not created before triggering the DAG.

**Fix**: Add the connection creation step before any DAG triggers.

**Error**: `Permission denied (publickey)`

**Cause**: SSH key not in authorized_keys or wrong permissions.

**Fix**:

```bash
chmod 700 ~/.ssh
chmod 600 ~/.ssh/id_rsa
chmod 600 ~/.ssh/authorized_keys
cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys
```

**Error**: `Connection refused`

**Cause**: SSH service not running on the host.

**Fix**:

```bash
systemctl start sshd
systemctl enable sshd
```

## Related Documentation

- [Airflow SSH Provider Docs](https://airflow.apache.org/docs/apache-airflow-providers-ssh/stable/index.html)
- [SSHOperator API](https://airflow.apache.org/docs/apache-airflow-providers-ssh/stable/_api/airflow/providers/ssh/operators/ssh/index.html)
- ADR-0043: Host Network Access for VM Connectivity
- ADR-0046: SSH Execution Pattern

## Example: Complete DAG

See `airflow/dags/freeipa_deployment.py` for a complete example of SSHOperator usage.
