# AGENTS.md - AI Coding Agent Instructions for Qubinode Navigator

> **Purpose**: This file provides comprehensive context and instructions for AI coding agents (Claude Code, Cursor, GitHub Copilot, etc.) to effectively work with the Qubinode Navigator infrastructure automation platform.

---

## Quick Context

**What is Qubinode Navigator?**
An infrastructure automation platform for deploying OpenShift, VMs, and supporting services on KVM hypervisors. It combines:
- **Airflow** for workflow orchestration (DAGs)
- **AI Assistant** (llama.cpp + IBM Granite) for intelligent automation
- **MCP Servers** for LLM tool integration
- **Plugin Architecture** for extensible deployments

**Primary Use Cases:**
1. Deploy OpenShift clusters (SNO, Compact, Standard)
2. Provision VMs with kcli
3. Deploy supporting infrastructure (FreeIPA, Step-CA, VyOS, Keycloak)
4. Automate certificate and DNS management
5. Enable AI-assisted infrastructure operations

---

## Environment Detection

When starting a session, **automatically detect** the current environment by checking:

```bash
# 1. Check if running on a Qubinode host
if [ -f "/root/qubinode_navigator/.env" ]; then
    echo "Running on Qubinode host"
    source /root/qubinode_navigator/.env
fi

# 2. Detect OS
cat /etc/os-release | grep -E "^(ID|VERSION_ID)="

# 3. Check deployment status
systemctl is-active libvirtd          # KVM available
podman ps 2>/dev/null | grep airflow  # Airflow deployed
curl -s localhost:8080/health         # AI Assistant running
curl -s localhost:8889/health         # MCP Server running
```

**Expected Environments:**
| Environment | Indicators | Key Paths |
|-------------|------------|-----------|
| **Development Host** | Has `.env`, libvirtd running | `/root/qubinode_navigator/` |
| **Remote/SSH** | No local `.env`, SSH connection | Clone repo first |
| **Container** | Running inside Airflow container | `/opt/airflow/`, SSH to host for kcli |
| **CI/CD** | GitHub Actions context vars | Use test fixtures |

---

## Project Structure

```
qubinode_navigator/
├── AGENTS.md                 # THIS FILE - AI agent instructions
├── QUICKSTART.md             # Human quick start guide
├── README.md                 # Project overview
├── .env.example              # Environment template (COPY TO .env)
├── .mcp-server-context.md    # MCP server state (auto-generated)
│
├── airflow/                  # Airflow orchestration
│   ├── dags/                 # 31 workflow DAGs
│   │   ├── ocp_agent_deployment.py      # OpenShift deployment
│   │   ├── freeipa_deployment.py        # FreeIPA identity
│   │   ├── example_kcli_vm_provisioning.py # VM operations
│   │   └── infrastructure_health_check.py  # System monitoring
│   ├── plugins/qubinode/     # Custom Airflow operators
│   │   ├── operators.py      # KcliVMCreate/Delete/List
│   │   └── sensors.py        # VM status sensors
│   ├── scripts/              # MCP servers + utilities
│   │   ├── mcp_server_fastmcp.py  # PRIMARY MCP server (20+ tools)
│   │   ├── mcp_http_server.py     # HTTP/SSE transport
│   │   └── test-kcli-*.sh         # Test scripts
│   ├── docker-compose.yml    # Airflow container stack
│   └── deploy-airflow.sh     # Airflow deployment script
│
├── ai-assistant/             # AI Assistant service
│   ├── src/
│   │   ├── main.py           # FastAPI server
│   │   └── ai_service.py     # llama.cpp inference
│   ├── mcp_server_fastmcp.py # AI-focused MCP tools
│   └── scripts/build.sh      # Container build
│
├── plugins/                  # Extensible plugin system
│   ├── os/                   # RHEL9, RHEL10, Rocky, CentOS
│   ├── cloud/                # Hetzner, Equinix
│   ├── environments/         # Deployment targets
│   └── services/             # AI Assistant, Vault
│
├── config/
│   └── plugins.yml           # Plugin configuration
│
├── scripts/development/
│   ├── deploy-qubinode.sh    # Main deployment orchestrator
│   └── deploy-qubinode-with-airflow.sh  # Full stack deployment
│
├── docs/
│   └── adrs/                 # Architecture Decision Records (54 ADRs)
│
└── .claude/                  # Claude Code settings
    └── settings.local.json   # Permissions
```

---

## Installation & Deployment

### Prerequisites Check
Before any deployment, run pre-flight validation:

```bash
./scripts/preflight-check.sh --fix
```

This checks: CPU virtualization, podman, libvirtd, disk space, network.

### Deployment Options

**Option 1: Full Stack (Recommended)**
```bash
# Creates: Airflow + PostgreSQL + MCP Server + Marquez Lineage + AI Assistant + Nginx
./deploy-qubinode-with-airflow.sh
```

**Option 2: Airflow via Makefile**
```bash
cd airflow
make install    # Full installation (prereqs + build + start)
make uninstall  # Stop and remove containers/volumes
```

**Option 3: Airflow Manual**
```bash
cd airflow
./deploy-airflow.sh
```

**Option 4: AI Assistant Only**
```bash
cd ai-assistant
./scripts/build.sh
podman run -d --name qubinode-ai -p 8080:8080 localhost/qubinode-ai-assistant:latest
```

### Post-Deployment Verification
```bash
# Check all services
curl -s localhost:8888/health    # Airflow
curl -s localhost:8080/health    # AI Assistant
curl -s localhost:8889/health    # MCP Server
curl -s localhost:5001/api/v1/namespaces  # Marquez Lineage API
kcli list vm                     # KVM/libvirt
```

### Services (All Enabled by Default)
| Service | Port | URL |
|---------|------|-----|
| Airflow UI | 8888 | http://localhost:8888 |
| MCP Server | 8889 | http://localhost:8889 |
| Marquez API | 5001 | http://localhost:5001 |
| Marquez Web | 3000 | http://localhost:3000 |
| AI Assistant | 8080 | http://localhost:8080 |

---

## MCP Tools Reference

### Airflow MCP Server (Port 8889)

**DAG Management:**
| Tool | Purpose | Example |
|------|---------|---------|
| `list_dags()` | List all DAGs | Returns dag_id, schedule, tags |
| `get_dag_info(dag_id)` | DAG details | `get_dag_info("freeipa_deployment")` |
| `trigger_dag(dag_id, conf)` | Execute DAG | `trigger_dag("ocp_agent_deployment", {"cluster_type": "sno"})` |

**VM Operations:**
| Tool | Purpose | Example |
|------|---------|---------|
| `preflight_vm_creation()` | Validate before create | Checks image, memory, libvirt |
| `list_vms()` | List all VMs | Via virsh/kcli |
| `get_vm_info(name)` | VM details | Memory, CPU, state |
| `create_vm(name, image, ...)` | Create VM | Uses kcli |
| `delete_vm(name)` | Delete VM | Cleanup with confirmation |

**RAG & Intelligence:**
| Tool | Purpose | Example |
|------|---------|---------|
| `search_similar_errors(error)` | Find similar issues | Pattern matching in history |
| `manage_rag_documents(op)` | Document lifecycle | ingest, query, delete |

### AI Assistant MCP Server (Port 8081)
| Tool | Purpose |
|------|---------|
| `ask_qubinode(question)` | Learning tool with docs + AI |
| `query_documents(query)` | RAG search |
| `chat_with_context(message)` | Context-aware chat |
| `get_project_status()` | Project health metrics |

### Using MCP Tools

**From Claude Desktop:**
```json
// claude_desktop_config.json
{
  "mcpServers": {
    "qubinode-airflow": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "http://localhost:8889/sse"]
    }
  }
}
```

**Direct HTTP:**
```bash
# List available tools
curl http://localhost:8889/tools

# Call a tool
curl -X POST http://localhost:8889/call \
  -H "Content-Type: application/json" \
  -d '{"tool": "list_vms", "arguments": {}}'
```

---

## DAG Patterns & Best Practices

### Standard DAG Structure (ADR-0045)
```python
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    'owner': 'qubinode',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'retries': 2,
    'retry_delay': timedelta(minutes=3),
}

dag = DAG(
    'my_dag_id',  # snake_case, matches filename
    default_args=default_args,
    description='Brief description',
    schedule=None,  # Manual trigger for deployment DAGs
    catchup=False,
    tags=['qubinode', 'category'],
)

# Use """ double quotes for bash commands (not ''')
task = BashOperator(
    task_id='my_task',
    bash_command="""
    echo "[INFO] Starting task..."
    # Your commands here
    echo "[OK] Task completed"
    """,
    dag=dag,
)
```

### SSH Execution Pattern (ADR-0046)
Run commands on host from Airflow container. Use the helper functions in `dag_helpers.py`:

```python
from dag_helpers import ssh_to_host_command, ssh_to_host_script, get_kcli_command

# Simple command
bash_command = ssh_to_host_command("kcli list vm")

# Multi-line script
bash_command = ssh_to_host_script("""
cd /opt/kcli-pipelines
./deploy.sh
""")

# kcli with automatic SSH wrapping
bash_command = get_kcli_command("info vm freeipa")
```

Or manually:
```python
bash_command="""
ssh -o StrictHostKeyChecking=no root@localhost \
    "cd /opt/kcli-pipelines && ./deploy.sh"
"""
```

### Log Prefixes
| Prefix | Meaning |
|--------|---------|
| `[OK]` | Success |
| `[ERROR]` | Failure |
| `[WARN]` | Warning |
| `[INFO]` | Informational |
| `[SKIP]` | Skipped |

### Common Mistakes to Avoid
1. **Unicode in bash**: Use `[OK]` not `✅`
2. **String concatenation**: Use f-strings or environment vars, not `''' + var + '''`
3. **Missing PATH**: Add `export PATH="/home/airflow/.local/bin:$PATH"` for kcli
4. **Direct ansible execution**: Use SSH to host, not container ansible

---

## Component Deployment Workflows

### Deploy OpenShift (SNO)
```bash
# Via Airflow UI
1. Navigate to: http://localhost:8888
2. Find: ocp_agent_deployment
3. Trigger with conf: {"cluster_type": "sno", "ocp_version": "4.14"}
4. Monitor Graph view

# Via MCP
trigger_dag("ocp_agent_deployment", {"cluster_type": "sno"})
```

### Deploy FreeIPA
```bash
# Prerequisites: DNS delegation, RHEL VM
trigger_dag("freeipa_deployment", {
    "action": "create",
    "domain": "example.com",
    "realm": "EXAMPLE.COM"
})
```

### Create VM
```bash
# Pre-flight first
preflight_vm_creation()

# Then create
create_vm(
    name="my-vm",
    image="centos10stream",
    memory=4096,
    cpus=2,
    disk_size="20G"
)

# Or via DAG
trigger_dag("example_kcli_vm_provisioning", {
    "vm_name": "my-vm",
    "action": "create"
})
```

### Deploy Certificate Authority
```bash
# Step-CA for internal PKI
trigger_dag("stepca_deployment", {
    "ca_hostname": "ca.example.com"
})
```

---

## Airflow Makefile Commands

The Airflow directory includes a Makefile for common operations:

```bash
cd airflow

# Installation
make install      # Full installation (prereqs + build + start)
make uninstall    # Stop and remove containers/volumes
make build        # Build container image only

# Service Management
make up           # Start all services
make down         # Stop all services
make restart      # Restart all services
make status       # Show service status
make logs         # View logs

# DAG Management
make clear-dag-cache              # Clear cache and reload all DAGs
make clear-dag-cache-id DAG_ID=x  # Clear cache for specific DAG
make validate-dags                # Validate DAG syntax
make lint-dags                    # Check ADR-0045/0046 compliance
make list-dags                    # List all DAGs

# Testing
make test-mcp      # Test MCP server
make test-lineage  # Test Marquez lineage
make health        # Check all service health

# Initialization
make init-prereqs  # Initialize vault.yml, clone repos, setup SSH
make init-db       # Initialize Airflow database
```

---

## Lineage & DAG Visualization

OpenLineage/Marquez is enabled by default for DAG lineage tracking.

### Access Lineage
| Service | URL | Purpose |
|---------|-----|---------|
| Marquez Web | http://localhost:3000 | Visual lineage explorer |
| Marquez API | http://localhost:5001 | Lineage data API |

### Use Cases
- **Visualize DAG dependencies** - See complete task graphs
- **Track data flow** - Understand inputs/outputs between tasks
- **Analyze failure impact** - See what tasks are affected by failures
- **Debug dependencies** - Identify missing or incorrect task dependencies

### Query Lineage
```bash
# Via MCP
get_dag_lineage("freeipa_deployment")

# Via API
curl http://localhost:5001/api/v1/namespaces/qubinode/jobs
```

---

## Debugging & Troubleshooting

### Service Health Checks
```bash
# All services status
cd /root/qubinode_navigator/airflow
podman-compose ps

# Logs
podman-compose logs -f airflow-scheduler  # DAG issues
podman-compose logs -f airflow-webserver  # UI issues
podman logs qubinode-ai-assistant         # AI service
```

### Common Issues

**DAG not appearing or showing stale version:**
```bash
# Clear DAG cache and force reload
cd airflow
make clear-dag-cache

# Or for a specific DAG
make clear-dag-cache-id DAG_ID=freeipa_deployment

# Lint DAGs for common issues
make lint-dags

# Check for Python syntax errors
python3 -c "import ast; ast.parse(open('airflow/dags/my_dag.py').read())"

# Check Airflow import
python3 -c "from airflow.models import DagBag; db = DagBag('airflow/dags'); print(db.import_errors)"
```

**VM operations failing:**
```bash
# Verify kcli on host
kcli list vm
kcli list images

# Check libvirtd
systemctl status libvirtd

# Check SSH from container
podman exec -it airflow-scheduler ssh root@localhost "echo OK"
```

**MCP not responding:**
```bash
# Check if enabled
grep MCP_ENABLED airflow/.env.mcp

# Restart MCP service
cd airflow && ./start-mcp-services.sh

# Test endpoint
curl http://localhost:8889/health
```

---

## Memory & Context Management

### Reference Context Files
When working on this project, reference these files for context:

```markdown
@.mcp-server-context.md   # MCP server state, tools, resources
@QUICKSTART.md            # User deployment guide
@docs/adrs/               # Architecture decisions (54 ADRs)
@config/plugins.yml       # Plugin configuration
```

### ADR Directory Quick Reference
Key ADRs for understanding architecture:

| ADR | Topic |
|-----|-------|
| ADR-0001 | Core architecture decisions |
| ADR-0036 | Airflow integration architecture |
| ADR-0045 | DAG development standards |
| ADR-0046 | Validation pipeline & host execution |
| ADR-0047 | kcli-pipelines integration |
| ADR-0055 | Zero-friction infrastructure services |

### Generate Rules File
For agents that support rules files, generate one based on this project:

```bash
# Generate .cursorrules or similar
cat > .cursorrules << 'EOF'
# Qubinode Navigator Development Rules

## Code Style
- Python: Follow PEP 8, use type hints
- Bash: Use shellcheck, prefer `[[` over `[`
- DAGs: Follow ADR-0045 standards strictly

## Testing
- Test kcli commands with airflow/scripts/test-*.sh first
- Validate DAG syntax before committing
- Use pre-flight checks before VM operations

## Commits
- Prefix: feat|fix|docs|refactor|test
- Reference ADRs when applicable
- Include [OK]/[ERROR] in test outputs

## MCP Integration
- Always use preflight_vm_creation() before create_vm()
- Check dag status with list_dags() before triggering
- Use search_similar_errors() for debugging

## Paths
- DAGs: airflow/dags/
- Operators: airflow/plugins/qubinode/
- Scripts: airflow/scripts/, scripts/development/
- Config: config/, .env
EOF
```

---

## Security Considerations

### Sensitive Files (Never Commit)
- `.env` - Contains credentials
- `config/vault.yml` - Vault tokens
- `*.pem`, `*.key` - Certificates/keys
- `pull-secret.json` - OpenShift pull secrets

### Credential Management
```bash
# Use HashiCorp Vault when available
export USE_HASHICORP_VAULT=true
export VAULT_ADDR="https://vault.example.com"

# Or use .env with restricted permissions
chmod 600 .env
```

### SSH Keys
The deployment script auto-configures SSH for container→host communication:
```bash
# Keys are created at: ~/.ssh/id_rsa
# Auto-added to: ~/.ssh/authorized_keys
# Used by: Airflow container for host commands
```

---

## Extending the Project

### Adding a New DAG
1. Create `airflow/dags/my_new_dag.py`
2. Follow ADR-0045 template
3. Test with: `python3 -c "import ast; ast.parse(...)"`
4. Verify: `airflow dags test my_new_dag 2025-01-01`

### Adding a Plugin
1. Create plugin class in `plugins/` directory
2. Register in `config/plugins.yml`
3. Define dependencies and configuration
4. Implement `check_state()`, `get_desired_state()`, `apply_changes()`

### Adding MCP Tools
1. Edit `airflow/scripts/mcp_server_fastmcp.py`
2. Add function with `@mcp.tool()` decorator
3. Define input schema with Pydantic
4. Restart MCP service

---

## CI/CD Integration

### GitHub Actions
The project includes workflows for:
- Documentation deployment (Jekyll → GitHub Pages)
- MCP server CI validation
- DAG syntax checking
- Container image builds

### PR Guidelines
1. Reference related ADRs
2. Include test results
3. Update AGENTS.md if adding new capabilities
4. Ensure Jekyll build passes for docs changes

---

## Support & Resources

- **Documentation**: `/docs/` directory
- **ADRs**: `/docs/adrs/` - 54 architecture decisions
- **AI Assistant**: `http://localhost:8080/` when deployed
- **Issues**: https://github.com/Qubinode/qubinode_navigator/issues
- **MCP Context**: `.mcp-server-context.md` (auto-updated)

---

## Agent Session Checklist

When starting a new session:

- [ ] Detect environment (host/container/remote)
- [ ] Check service status (Airflow, AI, MCP)
- [ ] Reference `@.mcp-server-context.md` for state
- [ ] Identify relevant ADRs for the task
- [ ] Use pre-flight checks before destructive operations
- [ ] Follow ADR-0045 for any DAG modifications
- [ ] Test changes before committing

---

*Last updated: 2025-12-02*
*Version: 2.0 - Added MCP/Lineage by default, Makefile commands, SSH helpers*
*Compatible with: Claude Code, Cursor, GitHub Copilot, VS Code AI, and 20+ other agents*
