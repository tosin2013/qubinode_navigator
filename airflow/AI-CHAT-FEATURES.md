# AI Chat Features

## Overview

The Qubinode AI Assistant integrated into Airflow has enhanced capabilities for system interaction and beautiful response rendering.

## ✨ Key Features

### 1. 📝 Markdown Rendering

All AI responses are beautifully rendered using **Markdown** for improved readability.

**Supported Markdown Features:**

- **Bold** and *italic* text
- `Inline code` with syntax highlighting
- ```language
  Multi-line code blocks with syntax highlighting
  ```
- Bullet and numbered lists
- Tables
- Blockquotes
- Links

**Example AI Response:**

````markdown
## Creating a VM with kcli

Here's how to create a VM:

```bash
kcli create vm myvm --image centos-stream-10 --memory 2048 --cpus 2
````

**Parameters:**

| Parameter  | Description      | Example            |
| ---------- | ---------------- | ------------------ |
| `--image`  | Cloud image name | `centos-stream-10` |
| `--memory` | RAM in MB        | `2048`             |
| `--cpus`   | Number of CPUs   | `2`                |

> **Note**: Make sure libvirtd is running before creating VMs.

````

### 2. 🔐 Safe Command Execution

The AI has context about commands that can be safely executed on the system as the **non-root airflow user**.

**Security Features:**
- ✅ Runs as `airflow` user (not root)
- ✅ Whitelist of safe read-only commands
- ✅ No shell injection (uses `shell=False`)
- ✅ 30-second timeout
- ✅ Only read-only operations allowed

**Allowed Commands:**

#### Airflow Commands
```bash
airflow dags list
airflow dags show <dag_id>
airflow tasks list <dag_id>
airflow pools list
airflow connections list
````

#### kcli Commands

```bash
kcli list vm
kcli list image
kcli list network
kcli info vm <vm_name>
kcli info host
```

#### virsh Commands

```bash
virsh list --all
virsh dominfo <vm>
virsh net-list --all
virsh pool-list --all
virsh nodeinfo
virsh version
virsh capabilities
```

#### System Commands

```bash
ls /opt/airflow/dags
cat /opt/airflow/dags/example.py
df -h
free -h
uptime
date
```

**Blocked Commands:**

- ❌ Any `rm` commands
- ❌ Write operations (`mv`, `cp` to system locations)
- ❌ Package management (`apt`, `yum`, `dnf`)
- ❌ Service management (`systemctl`, `service`)
- ❌ User management commands
- ❌ Network configuration changes
- ❌ Any command not in the whitelist

### 3. 🎯 Rich System Context

The AI receives comprehensive context about your environment:

**Environment Details:**

- Platform: Apache Airflow 2.10.4
- Deployment: Qubinode Navigator (Podman)
- Hypervisor: KVM/libvirt (qemu:///system)
- Container Runtime: Podman
- Network: airflow_default

**Available Tools:**

- **kcli 99.0** - VM provisioning CLI
- **virsh/libvirt 9.0.0** - Libvirt management
- **QEMU 10.1.0** - Hypervisor
- **Airflow 2.10.4** - Workflow orchestration

**Available Operators:**
The AI knows about all custom operators:

- `KcliVMCreateOperator` - Create VMs
- `KcliVMDeleteOperator` - Delete VMs
- `KcliVMListOperator` - List VMs
- `VirshCommandOperator` - Run virsh commands
- `VirshVMStartOperator` - Start VMs
- `VirshVMStopOperator` - Stop VMs
- `VirshVMInfoOperator` - Get VM info
- `VirshNetworkListOperator` - List networks
- `KcliVMStatusSensor` - Wait for VM status

### 4. 💬 Context-Aware Responses

The AI understands:

- You're working in Airflow UI
- Available custom operators and their parameters
- Example DAGs location and structure
- Documentation paths
- Deployment architecture
- Security constraints (non-root execution)

## Usage Examples

### Example 1: Get Available DAGs

**User:** "Show me all available DAGs"

**AI Response:**

````markdown
# Available DAGs

Let me check the DAGs in your Airflow instance:

```bash
airflow dags list
````

Based on your setup, you should have these example DAGs:

| DAG ID                         | Description            | Location                                            |
| ------------------------------ | ---------------------- | --------------------------------------------------- |
| `example_kcli_vm_provisioning` | Full VM lifecycle demo | `/opt/airflow/dags/example_kcli_vm_provisioning.py` |
| `example_kcli_virsh_combined`  | kcli + virsh combined  | `/opt/airflow/dags/example_kcli_virsh_combined.py`  |

Would you like to see the code for any of these?

````

### Example 2: Create VM DAG

**User:** "Build a DAG that provisions 3 VMs in parallel"

**AI Response:**
```markdown
# Parallel VM Provisioning DAG

Here's a DAG that creates 3 VMs in parallel:

```python
from datetime import datetime
from airflow import DAG
from qubinode.operators import KcliVMCreateOperator

default_args = {
    'owner': 'qubinode',
    'start_date': datetime(2025, 11, 19),
}

dag = DAG(
    'parallel_vm_provisioning',
    default_args=default_args,
    schedule_interval=None,
    catchup=False,
)

# Create 3 VMs in parallel
vm1 = KcliVMCreateOperator(
    task_id='create_vm1',
    vm_name='worker-1',
    image='centos-stream-10',
    memory=2048,
    cpus=2,
    dag=dag,
)

vm2 = KcliVMCreateOperator(
    task_id='create_vm2',
    vm_name='worker-2',
    image='centos-stream-10',
    memory=2048,
    cpus=2,
    dag=dag,
)

vm3 = KcliVMCreateOperator(
    task_id='create_vm3',
    vm_name='worker-3',
    image='centos-stream-10',
    memory=2048,
    cpus=2,
    dag=dag,
)

# Tasks will run in parallel (no dependencies)
````

**Key Points:**

- All 3 `KcliVMCreateOperator` tasks have no dependencies
- They will execute in parallel
- Each VM gets 2GB RAM and 2 CPUs
- Using CentOS Stream 10 image

Save this to `/opt/airflow/dags/parallel_vm_provisioning.py` and it will be picked up automatically!

````

### Example 3: Troubleshooting

**User:** "Help me troubleshoot a failed VM provisioning task"

**AI Response:**
```markdown
# Troubleshooting VM Provisioning

Let's diagnose the issue step by step:

## Step 1: Check System Resources

```bash
free -h
df -h
````

## Step 2: Verify libvirt is running

```bash
virsh nodeinfo
virsh list --all
```

## Step 3: Check available images

```bash
kcli list image
```

## Common Issues:

### 1. Insufficient Resources

> If you see low memory or disk space, free up resources before provisioning.

### 2. libvirt Connection Issues

Check if the socket is accessible:

```bash
ls -la /var/run/libvirt/libvirt-sock
```

### 3. Image Not Found

Make sure the image is downloaded:

```bash
kcli download image centos-stream-10
```

Would you like me to check any specific error message from your task logs?

````

## Technical Implementation

### Backend (Python)
```python
# Safe command execution function
def execute_safe_command(command_parts):
    """Execute safe read-only commands as airflow user"""
    # Whitelist check
    # Security validation
    # Subprocess execution with timeout
    # Return structured result
````

### Frontend (JavaScript + Markdown)

```javascript
// Markdown rendering with marked.js
function addMessage(type, content) {
    if (type === 'assistant') {
        renderedContent = marked.parse(content);
    }
    // Beautiful rendering with syntax highlighting
}
```

### Context Enhancement

```python
context = {
    "environment": {...},
    "tools_available": {...},
    "available_operators": {...},
    "command_execution": {
        "enabled": True,
        "execution_user": "airflow",
        "allowed_commands": SAFE_COMMANDS
    },
    "response_format": {
        "format": "markdown",
        "recommendation": "Use code blocks, tables, lists"
    }
}
```

## Security Considerations

### Command Execution Safety

1. **User Isolation**: Commands run as `airflow` user, not root
1. **Whitelist**: Only explicitly allowed commands can run
1. **No Shell**: `shell=False` prevents injection attacks
1. **Timeout**: 30-second limit prevents hanging
1. **Read-Only**: No write, delete, or modify operations
1. **Audit**: All commands logged

### Markdown Rendering Safety

1. **Sanitization**: marked.js handles XSS prevention
1. **No Script Execution**: No `<script>` tags in rendered content
1. **Safe HTML**: Only markdown-generated HTML

## Future Enhancements

Potential future features:

- [ ] Real-time command execution from chat
- [ ] Command output display in chat
- [ ] DAG file editing assistance
- [ ] Task log viewing
- [ ] Automated troubleshooting workflows
- [ ] Integration with Airflow REST API
- [ ] Custom operator generation
- [ ] DAG testing assistance

## Support

For issues or questions:

- Check logs: `podman logs airflow_airflow-webserver_1`
- View plugin code: `/opt/airflow/plugins/qubinode/ai_chat_plugin.py`
- Documentation: `/opt/airflow/README.md`
- Troubleshooting: `/opt/airflow/TROUBLESHOOTING.md`
