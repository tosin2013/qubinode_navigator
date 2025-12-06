# Qubinode Navigator - Apache Airflow Integration

Phase 6 Goal 2: Workflow Orchestration Integration
Based on: **ADR-0036** (Airflow Integration), **ADR-0037** (Git-Based DAG Management)

## 🎯 Overview

This directory contains the Apache Airflow integration for Qubinode Navigator, enabling enterprise-scale workflow orchestration for VM provisioning, infrastructure deployment, and OpenShift/Kubernetes cluster management.

## 📋 Features

- **✅ Optional Feature Flag**: ENABLE_AIRFLOW configuration (disabled by default)
- **✅ kcli Integration**: Custom operators for VM lifecycle management
- **✅ AI Assistant Integration**: AI-powered workflow guidance and recommendations
- **✅ Git-Based DAG Management**: Version-controlled workflow definitions (ADR-0037)
- **✅ Custom Operators**: Qubinode-specific operators for infrastructure automation
- **✅ Community Extensibility**: Plugin system for custom workflows

## 📦 Prerequisites for New Developers

Before starting Airflow, you need to clone the required repositories:

```bash
# 1. Clone qubinode_navigator (if not already done)
git clone https://github.com/Qubinode/qubinode_navigator.git /root/qubinode_navigator

# 2. Clone qubinode-pipelines to the standard location (required for deployment DAGs)
sudo git clone https://github.com/Qubinode/qubinode-pipelines.git /opt/qubinode-pipelines

# 3. (Optional) If you have an existing kcli-pipelines clone, create a symlink instead:
# sudo ln -s /path/to/your/kcli-pipelines /opt/qubinode-pipelines
```

**Why `/opt/qubinode-pipelines`?** This is the standard location defined in ADR-0047. The docker-compose.yml mounts this directory into the Airflow containers for DAG access.

## 🚀 Quick Start

### 1. Enable Airflow

Edit `airflow/config/airflow.env`:

```bash
ENABLE_AIRFLOW=true
```

### 2. Start Airflow Services

**Using Podman** (RHEL ecosystem - recommended):

```bash
cd /root/qubinode_navigator/airflow
podman-compose up -d
```

**Using Docker** (if available):

```bash
cd /root/qubinode_navigator/airflow
docker-compose up -d
```

### 3. Access Airflow UI

- **URL**: http://localhost:8888
- **Username**: admin
- **Password**: admin (change in production!)

**Note**: Airflow runs on port 8888 to avoid conflict with AI Assistant on port 8080

### 4. Run Example DAG

1. Navigate to Airflow UI
1. Find "example_kcli_vm_provisioning" DAG
1. Enable the DAG (toggle switch)
1. Click the play button to trigger manually
1. Monitor execution in Graph or Tree view

## 📁 Directory Structure

```
airflow/
├── config/
│   └── airflow.env              # Airflow configuration with feature flag
├── dags/                         # DAG definitions (workflow files)
│   └── example_kcli_vm_provisioning.py  # Example kcli VM workflow
├── plugins/                      # Custom plugins
│   └── qubinode/                # Qubinode Navigator plugin
│       ├── __init__.py          # Plugin registration
│       ├── operators.py         # Custom operators (VM create, delete, list)
│       ├── sensors.py           # Custom sensors (VM status monitoring)
│       └── hooks.py             # Hooks for kcli and AI Assistant
├── logs/                         # Airflow logs
├── docker-compose.yml           # Docker Compose configuration
└── README.md                    # This file
```

## 🔧 Custom Operators

### KcliVMCreateOperator

Create a VM using kcli:

```python
from qubinode.operators import KcliVMCreateOperator

create_vm = KcliVMCreateOperator(
    task_id='create_centos_vm',
    vm_name='centos-stream-10',
    image='centos-stream-10',
    memory=4096,  # MB
    cpus=2,
    disk_size='20G',
    ai_assistance=True  # Enable AI guidance
)
```

### KcliVMDeleteOperator

Delete a VM:

```python
from qubinode.operators import KcliVMDeleteOperator

delete_vm = KcliVMDeleteOperator(
    task_id='delete_vm',
    vm_name='centos-stream-10',
    force=True
)
```

### KcliVMListOperator

List all VMs:

```python
from qubinode.operators import KcliVMListOperator

list_vms = KcliVMListOperator(
    task_id='list_all_vms'
)
```

## 🎭 Custom Sensors

### KcliVMStatusSensor

Wait for VM to reach a specific status:

```python
from qubinode.sensors import KcliVMStatusSensor

wait_for_vm = KcliVMStatusSensor(
    task_id='wait_for_running',
    vm_name='centos-stream-10',
    expected_status='running',
    timeout=300,
    poke_interval=30
)
```

## 🤖 AI Assistant Integration

The Airflow integration includes hooks to the Qubinode Navigator AI Assistant:

```python
from qubinode.hooks import QuibinodeAIAssistantHook

ai_hook = QuibinodeAIAssistantHook()

# Get guidance for a task
guidance = ai_hook.get_kcli_guidance("create a VM for OpenShift")

# Analyze workflow results
analysis = ai_hook.analyze_workflow_results(workflow_results)
```

## 📝 Creating Custom DAGs

1. Create a new Python file in `airflow/dags/`
1. Define your workflow using Airflow operators
1. Use Qubinode custom operators for infrastructure tasks
1. Airflow will auto-discover and load your DAG

Example template:

```python
from datetime import datetime, timedelta
from airflow import DAG
from qubinode.operators import KcliVMCreateOperator

default_args = {
    'owner': 'qubinode',
    'start_date': datetime(2025, 11, 19),
    'retries': 1,
}

dag = DAG(
    'my_custom_workflow',
    default_args=default_args,
    schedule_interval=None,  # Manual trigger
    tags=['qubinode', 'custom'],
)

create_vm = KcliVMCreateOperator(
    task_id='create_vm',
    vm_name='my-vm',
    dag=dag,
)
```

## 🔐 Security Considerations

### Production Deployment Checklist

- [ ] Change `AIRFLOW__WEBSERVER__SECRET_KEY` in `airflow.env`
- [ ] Change `POSTGRES_PASSWORD` in `airflow.env`
- [ ] Change default admin password (admin/admin)
- [ ] Enable HTTPS for Airflow UI
- [ ] Configure proper authentication backend
- [ ] Set up RBAC with appropriate roles
- [ ] Enable audit logging
- [ ] Scan custom plugins for security issues

## 🔄 Cross-Repository DAG Architecture (ADR-0047)

Qubinode uses a **two-repository pattern** for DAG management:

| Repository           | DAG Type        | Location                        | Purpose                          |
| -------------------- | --------------- | ------------------------------- | -------------------------------- |
| `qubinode_navigator` | Platform DAGs   | `airflow/dags/`                 | dag_factory, rag\_\*, smoke_test |
| `qubinode-pipelines` | Deployment DAGs | `/opt/qubinode-pipelines/dags/` | Infrastructure, OCP, networking  |

### Production Layout

```
/opt/qubinode-pipelines/          # Volume mounted from qubinode-pipelines repo
├── dags/
│   ├── infrastructure/           # FreeIPA, VyOS, Step-CA, etc.
│   ├── ocp/                      # OpenShift deployment DAGs
│   ├── networking/               # Network configuration DAGs
│   ├── storage/                  # Storage provisioning DAGs
│   └── security/                 # Security automation DAGs
└── scripts/                      # Deployment scripts called by DAGs
```

### CI/CD Cross-Repository Testing

The `airflow-validate.yml` workflow validates DAGs from **both repositories** together:

```bash
# Trigger CI manually with specific qubinode-pipelines branch
gh workflow run airflow-validate.yml -f pipelines_ref=develop

# Or use GitHub Actions UI:
# Actions → Airflow Validation → Run workflow → Enter branch/tag/SHA
```

**Workflow inputs:**

- `pipelines_ref`: Branch, tag, or SHA of qubinode-pipelines to test against (default: `main`)

This ensures DAG changes in either repository don't break the integrated system.

### Related ADRs

- **ADR-0045**: DAG Development Standards (quote style, naming, ASCII markers)
- **ADR-0046**: DAG Validation Pipeline and Host-Based Execution
- **ADR-0047**: qubinode-pipelines Integration Pattern
- **ADR-0061**: Multi-Repository Architecture

## 🔄 Git-Based DAG Management (ADR-0037)

### Enable Git-Sync

Edit `airflow/config/airflow.env`:

```bash
GIT_SYNC_ENABLED=true
GIT_SYNC_REPO=https://github.com/yourorg/airflow-dags
GIT_SYNC_BRANCH=main
```

This will automatically sync DAGs from your Git repository every 60 seconds.

### Webhook Integration

Set up webhooks in your Git provider to trigger immediate DAG updates on push:

- **GitHub**: Settings → Webhooks → Add webhook
- **GitLab**: Settings → Integrations → Webhooks
- **URL**: http://your-airflow-host:8080/api/v1/dags/sync

## 📊 Lineage & DAG Visualization

Qubinode Navigator includes OpenLineage integration for DAG lineage tracking.

### Access Lineage Services

| Service        | URL                   | Description             |
| -------------- | --------------------- | ----------------------- |
| Marquez API    | http://localhost:5001 | Lineage data API        |
| Marquez Web UI | http://localhost:3000 | Visual lineage explorer |
| Airflow UI     | http://localhost:8888 | DAG management          |

### What You Can Do with Lineage

- **Visualize complete DAG task graphs** - See all dependencies
- **Understand data flow between tasks** - Track inputs and outputs
- **Analyze failure blast radius** - See what tasks are affected by failures
- **Debug task dependency issues** - Identify missing or incorrect dependencies

### Query Lineage via MCP

```python
# Using the MCP server
get_dag_lineage("freeipa_deployment")
```

## 📊 Monitoring

### View DAG Execution

- **Graph View**: Visual representation of task dependencies
- **Tree View**: Historical execution tree
- **Gantt Chart**: Timeline view of task execution
- **Logs**: Detailed logs for each task execution

### Metrics

Airflow exposes metrics at:

- http://localhost:8888/metrics

## 🛠️ Makefile Commands

Common operations are available via make:

```bash
# Service Management
make up                  # Start all services
make up-all              # Start with lineage and MCP server
make down                # Stop all services
make restart             # Restart all services
make status              # Show service status

# DAG Management
make clear-dag-cache     # Clear DAG cache and reload
make validate-dags       # Validate DAG syntax
make lint-dags           # Check for common issues

# Testing
make test-mcp            # Test MCP server
make test-lineage        # Test Marquez/lineage

# Initialization
make init-prereqs        # Initialize vault.yml, clone repos
```

## 🧪 Testing DAGs

Test your DAG before deployment:

```bash
# Validate DAG structure
podman-compose run airflow-cli airflow dags test my_custom_workflow 2025-11-19

# List all DAGs
podman-compose run airflow-cli airflow dags list

# Test a specific task
podman-compose run airflow-cli airflow tasks test my_custom_workflow create_vm 2025-11-19
```

## 🛠️ Troubleshooting

### Common Issues

**Issue**: Airflow UI not accessible
**Solution**: Check if containers are running: `docker-compose ps`

**Issue**: DAG not appearing
**Solution**: Check logs: `docker-compose logs airflow-scheduler`

**Issue**: kcli commands failing
**Solution**: Verify kcli is accessible from Airflow container

**Issue**: AI Assistant connection failed
**Solution**: Verify AI Assistant is running on localhost:8000

### Logs

View logs for debugging:

```bash
# All services
docker-compose logs

# Specific service
docker-compose logs airflow-webserver
docker-compose logs airflow-scheduler

# Follow logs
docker-compose logs -f
```

## 📚 Resources

- **Apache Airflow Documentation**: https://airflow.apache.org/docs/
- **kcli Documentation**: https://kcli.readthedocs.io/
- **ADR-0036**: Apache Airflow Workflow Orchestration Integration
- **ADR-0037**: Git-Based DAG Repository Management
- **Qubinode Navigator Docs**: ../docs/

## 🤝 Contributing

To add custom operators or DAGs:

1. For operators: Add to `airflow/plugins/qubinode/operators.py`
1. For sensors: Add to `airflow/plugins/qubinode/sensors.py`
1. For hooks: Add to `airflow/plugins/qubinode/hooks.py`
1. For DAGs: Add Python file to `airflow/dags/`

Submit contributions via pull request with:

- Comprehensive docstrings
- Example usage in DAG
- Test coverage
- Security validation

## 📞 Support

For issues or questions:

- Check Airflow logs
- Review DAG documentation
- Consult AI Assistant for guidance
- Open GitHub issue for bugs

______________________________________________________________________

**Phase 6 Goal 2 Status**: ✅ Core Integration Complete
**Next Steps**: Create community DAG marketplace, implement advanced features
