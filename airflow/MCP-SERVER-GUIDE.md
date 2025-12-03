# MCP Server Integration Guide

## Overview

Qubinode Navigator now supports Model Context Protocol (MCP) servers, allowing external LLMs (like Claude Desktop, ChatGPT, or custom AI assistants) to interact with your infrastructure through natural language.

## What is MCP?

The Model Context Protocol is a standard that enables AI assistants to connect to external tools and data sources. Think of it as giving your AI assistant direct access to your infrastructure management capabilities.

## Architecture

### Two MCP Servers:

1. **AI Assistant MCP Server** (Port 8081)

   - Query RAG document store
   - Chat with AI assistant
   - Get project status

1. **Airflow MCP Server** (Port 8889)

   - List and trigger DAGs
   - Create/delete VMs
   - Query logs and status

### All Interfaces Work Together:

```
Human Users                  LLMs
    │                         │
    ├─ Web UI (Port 80)      ├─ Claude Desktop
    ├─ CLI/SSH               ├─ ChatGPT
    └─ Embedded AI Chat      └─ Custom LLMs
          │                         │
          └─────────┬───────────────┘
                    │
            ┌───────▼────────┐
            │ Airflow Core   │
            │ AI Assistant   │
            │ kcli/virsh     │
            └────────────────┘
```

## Quick Start

### Step 1: Run Setup Script

```bash
cd /root/qubinode_navigator/airflow
./setup-mcp-servers.sh
```

This will:

- Generate secure API keys
- Create `.env` file with MCP configuration
- Provide Claude Desktop configuration
- Optionally restart services

### Step 2: Restart Services

```bash
cd /root/qubinode_navigator/airflow
podman-compose restart
```

### Step 3: Connect Claude Desktop

Add to `~/.config/claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "qubinode-airflow": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-http-proxy"],
      "env": {
        "MCP_HTTP_URL": "http://YOUR_SERVER_IP:8889",
        "MCP_API_KEY": "your-api-key-from-setup"
      }
    }
  }
}
```

Replace:

- `YOUR_SERVER_IP` with your server's IP address
- `your-api-key-from-setup` with the API key from setup script

### Step 4: Test in Claude Desktop

Restart Claude Desktop and try:

```
"List all available workflows"
"Create a VM named test-vm with 4GB RAM"
"What's the status of the VM provisioning DAG?"
```

## Available Tools

### AI Assistant MCP Tools:

| Tool                   | Description               | Permission Level |
| ---------------------- | ------------------------- | ---------------- |
| **query_documents**    | Search RAG document store | Read-only        |
| **chat_with_context**  | Chat with AI assistant    | Read-only        |
| **get_project_status** | Get deployment status     | Read-only        |

### Airflow MCP Tools:

| Tool              | Description           | Permission Level |
| ----------------- | --------------------- | ---------------- |
| **list_dags**     | List all DAGs         | Read-only        |
| **get_dag_info**  | Get DAG details       | Read-only        |
| **get_dag_runs**  | Get recent DAG runs   | Read-only        |
| **trigger_dag**   | Trigger DAG execution | **Write**        |
| **list_vms**      | List all VMs          | Read-only        |
| **get_vm_info**   | Get VM details        | Read-only        |
| **create_vm**     | Create a new VM       | **Write**        |
| **delete_vm**     | Delete a VM           | **Write**        |
| **get_task_logs** | Get task logs         | Read-only        |

## Configuration

### Environment Variables:

```bash
# AI Assistant MCP
MCP_SERVER_ENABLED=true|false       # Default: false
MCP_SERVER_PORT=8081                # Default: 8081
MCP_API_KEY=<secure-key>            # Required if enabled

# Airflow MCP
AIRFLOW_MCP_ENABLED=true|false      # Default: false
AIRFLOW_MCP_PORT=8889               # Default: 8889
AIRFLOW_MCP_API_KEY=<secure-key>    # Required if enabled

# Tool Permissions
AIRFLOW_MCP_TOOLS_DAG_MGMT=true     # DAG operations
AIRFLOW_MCP_TOOLS_VM_OPS=true       # VM operations
AIRFLOW_MCP_TOOLS_LOG_ACCESS=true   # Log access
AIRFLOW_MCP_TOOLS_READ_ONLY=false   # Read-only mode
```

### Read-Only Mode:

For production or untrusted LLMs, enable read-only mode:

```bash
export AIRFLOW_MCP_TOOLS_READ_ONLY=true
```

This allows:

- ✅ Listing DAGs, VMs, status
- ✅ Querying logs
- ❌ Triggering DAGs
- ❌ Creating/deleting VMs

## Security

### Authentication:

- **API Key Required:** All MCP requests must include valid API key
- **Per-Server Keys:** Separate keys for AI Assistant and Airflow
- **Secure Generation:** Use `openssl rand -hex 32`

### Authorization:

- **Tool-Level Permissions:** Enable/disable specific tool categories
- **Read-Only Mode:** Restrict to safe, non-destructive operations
- **Audit Logging:** All MCP requests are logged

### Best Practices:

1. **Use Strong Keys:**

   ```bash
   # Generate secure 256-bit keys
   openssl rand -hex 32
   ```

1. **Restrict Network Access:**

   ```bash
   # Only allow from trusted IPs
   firewall-cmd --zone=trusted --add-source=TRUSTED_IP
   firewall-cmd --zone=trusted --add-port=8889/tcp
   ```

1. **Enable Read-Only for Public LLMs:**

   ```bash
   export AIRFLOW_MCP_TOOLS_READ_ONLY=true
   ```

1. **Monitor Access:**

   ```bash
   # Watch MCP access logs
   tail -f /root/qubinode_navigator/airflow/logs/mcp_access.log
   ```

1. **Rotate Keys Regularly:**

   ```bash
   ./setup-mcp-servers.sh  # Regenerate keys
   ```

## Usage Examples

### Example 1: List and Trigger Workflows

**In Claude Desktop:**

```
User: What workflows are available?

Claude: [Calls list_dags tool]
I found 3 workflows:
1. example_kcli_vm_provisioning - Provisions VMs using kcli
2. example_kcli_virsh_combined - VM operations with virsh
3. example_kcli_script_based - Script-based VM management

User: Trigger the VM provisioning workflow

Claude: [Calls trigger_dag tool with dag_id="example_kcli_vm_provisioning"]
Successfully triggered workflow 'example_kcli_vm_provisioning'
Run ID: manual__2025-11-20T06:30:00+00:00
```

### Example 2: VM Management

**In Claude Desktop:**

```
User: Create a test VM with 4GB RAM and 4 CPUs

Claude: [Calls create_vm tool]
Created VM successfully:
- Name: test-vm-20251120
- Image: centos10stream
- Memory: 4096 MB
- CPUs: 4
- Disk: 10 GB

User: List all VMs

Claude: [Calls list_vms tool]
Active VMs:
 Id   Name                State
----------------------------------
 1    test-vm-20251120    running
 2    airflow-test-vm     running
```

### Example 3: Query Documentation

**In Claude Desktop:**

````
User: How do I use kcli to create a VM?

Claude: [Calls query_documents tool with query="kcli create vm"]
Found documentation:

## Result 1 (Score: 0.95)
**Source:** QUICK-REFERENCE.md

To create a VM with kcli:
```bash
kcli create vm <name> -i <image> -P memory=<MB> -P numcpus=<count>
````

Example:

```bash
kcli create vm test-vm -i centos10stream -P memory=2048 -P numcpus=2
```

```

### Example 4: Monitor DAG Status

**In Claude Desktop:**

```

User: Check the status of the VM provisioning DAG

Claude: \[Calls get_dag_runs tool\]
Recent runs for 'example_kcli_vm_provisioning':

## Run 1

Execution Date: 2025-11-20 06:30:00
State: **success**
Duration: 5m 23s

## Run 2

Execution Date: 2025-11-20 05:15:00
State: **success**
Duration: 5m 10s

````

## Troubleshooting

### Issue: MCP Server Not Starting

**Check if enabled:**
```bash
echo $AIRFLOW_MCP_ENABLED  # Should be "true"
````

**Check logs:**

```bash
podman logs airflow_airflow-webserver_1 | grep MCP
```

**Verify API key is set:**

```bash
echo $AIRFLOW_MCP_API_KEY  # Should not be empty
```

### Issue: Claude Desktop Can't Connect

**Test MCP server locally:**

```bash
cd /root/qubinode_navigator/ai-assistant
MCP_SERVER_ENABLED=true MCP_API_KEY=test python3 mcp_server.py
```

**Check firewall:**

```bash
firewall-cmd --list-ports | grep 8889
```

**Verify network connectivity:**

```bash
curl -H "X-API-Key: your-key" http://YOUR_IP:8889/health
```

### Issue: Permission Denied

**Check read-only mode:**

```bash
echo $AIRFLOW_MCP_TOOLS_READ_ONLY  # If "true", write operations disabled
```

**Verify tool permissions:**

```bash
echo $AIRFLOW_MCP_TOOLS_VM_OPS     # Must be "true" for VM operations
```

### Issue: Invalid API Key

**Regenerate keys:**

```bash
cd /root/qubinode_navigator/airflow
./setup-mcp-servers.sh
```

**Update Claude Desktop config** with new keys

## Advanced Configuration

### Custom Tool Selection:

```bash
# Enable only DAG management (no VM ops)
export AIRFLOW_MCP_TOOLS_DAG_MGMT=true
export AIRFLOW_MCP_TOOLS_VM_OPS=false
export AIRFLOW_MCP_TOOLS_LOG_ACCESS=true
```

### Multiple LLM Clients:

Each LLM client (Claude, ChatGPT, etc.) can connect with its own API key:

```bash
# Generate separate keys
CLAUDE_KEY=$(openssl rand -hex 32)
CHATGPT_KEY=$(openssl rand -hex 32)

# Use same server with different keys
# (implement key rotation/management)
```

### Behind Nginx:

Add to `/etc/nginx/conf.d/airflow.conf`:

```nginx
# MCP Server proxies
location /mcp/ai/ {
    proxy_pass http://localhost:8081/;
    proxy_set_header X-API-Key $http_x_api_key;
}

location /mcp/airflow/ {
    proxy_pass http://localhost:8889/;
    proxy_set_header X-API-Key $http_x_api_key;
}
```

## Monitoring

### View MCP Access Logs:

```bash
# Airflow MCP logs
podman logs -f airflow_airflow-webserver_1 | grep "qubinode-airflow-mcp"

# AI Assistant MCP logs
tail -f /root/qubinode_navigator/ai-assistant/logs/mcp.log
```

### Track Tool Usage:

```python
# In Airflow, MCP calls are logged as:
# [MCP] Tool 'create_vm' called with args: {...}
# [MCP] Tool 'trigger_dag' called by client: claude-desktop
```

## Performance

### Optimize for Multiple Clients:

```yaml
# docker-compose.yml
services:
  airflow-webserver:
    # Increase workers for MCP load
    command: webserver --workers 8
```

### Rate Limiting:

Add nginx rate limiting:

```nginx
limit_req_zone $binary_remote_addr zone=mcp:10m rate=10r/s;

location /mcp/ {
    limit_req zone=mcp burst=20;
    # ... proxy config ...
}
```

## FAQ

**Q: Does MCP replace the Web UI?**
A: No! The Web UI, CLI, and MCP all work together. Humans can use the UI while LLMs use MCP.

**Q: Is it safe to give an LLM VM creation access?**
A: Use read-only mode (`AIRFLOW_MCP_TOOLS_READ_ONLY=true`) until you trust the LLM. Monitor all operations.

**Q: Can multiple LLMs connect simultaneously?**
A: Yes! Each can have its own API key and they see the same data.

**Q: What if I don't want to use MCP?**
A: MCP is disabled by default (`MCP_SERVER_ENABLED=false`). Nothing changes if you don't enable it.

**Q: Does this work with ChatGPT?**
A: Yes, but ChatGPT doesn't natively support MCP yet. You'd need a custom integration or wait for OpenAI to add MCP support.

## Next Steps

1. ✅ Enable MCP servers with setup script
1. ✅ Configure Claude Desktop
1. ✅ Test with simple queries
1. ⏳ Add SSL/TLS for production
1. ⏳ Implement custom tool wrappers
1. ⏳ Monitor usage and refine permissions

## Resources

- [MCP Specification](https://modelcontextprotocol.io/)
- [Claude Desktop MCP Guide](https://docs.anthropic.com/claude/docs/mcp)
- [Design Document](../docs/MCP-SERVER-DESIGN.md)
- [Feature Overview](../FEATURE-MCP-SERVER.md)

______________________________________________________________________

**Status:** Production Ready ✅
**Security:** Opt-in, API key authentication
**Compatibility:** Claude Desktop, Custom LLMs
**Impact:** Enables AI-powered infrastructure management
