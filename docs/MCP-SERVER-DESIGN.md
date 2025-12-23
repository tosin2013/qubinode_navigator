______________________________________________________________________

## nav_exclude: true

# MCP Server Integration for Qubinode Navigator

## Overview

Add Model Context Protocol (MCP) server capability to expose Qubinode Navigator tools to external LLMs.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    External LLM Clients                      │
│              (Claude Desktop, OpenAI, etc.)                  │
└────────────────────────┬────────────────────────────────────┘
                         │ MCP Protocol (stdio/HTTP)
                         │
        ┌────────────────┴────────────────┐
        │                                 │
┌───────▼─────────┐             ┌────────▼──────────┐
│  AI Assistant   │             │  Airflow MCP      │
│  MCP Server     │             │  Server Plugin    │
│  Port: 8081     │             │  Port: 8889       │
└────────┬────────┘             └────────┬──────────┘
         │                               │
         │                               │
┌────────▼────────┐             ┌────────▼──────────┐
│  RAG System     │             │  Airflow Core     │
│  Document Store │             │  kcli/virsh       │
│  AI Chat        │             │  DAG Management   │
└─────────────────┘             └───────────────────┘
```

## Features to Expose

### AI Assistant MCP Tools:

1. **query_documents**

   - Search RAG document store
   - Get relevant context

1. **chat_with_context**

   - Send messages with project context
   - Get AI responses

1. **get_project_status**

   - Current deployment state
   - Service health

### Airflow MCP Tools:

1. **list_dags**

   - Get available workflows
   - DAG status and schedules

1. **trigger_dag**

   - Start workflow execution
   - Specify parameters

1. **get_dag_status**

   - Check DAG run status
   - Task completion

1. **get_task_logs**

   - Retrieve execution logs
   - Debug information

1. **create_vm**

   - Provision VM via kcli
   - Specify resources

1. **delete_vm**

   - Remove VM
   - Cleanup resources

1. **list_vms**

   - Get VM inventory
   - VM states

1. **get_vm_info**

   - Detailed VM information
   - Resource usage

## Implementation Plan

### Phase 1: AI Assistant MCP Server

**File:** `ai-assistant/mcp_server.py`

```python
from mcp.server import Server, Tool
from mcp.types import TextContent
import httpx

class QuibinodeAIMCPServer(Server):
    """MCP Server for AI Assistant"""

    def __init__(self):
        super().__init__("qubinode-ai-assistant")
        self.register_tools()

    def register_tools(self):
        @self.tool()
        async def query_documents(query: str) -> TextContent:
            """Search RAG document store"""
            # Implementation
            pass

        @self.tool()
        async def chat_with_context(message: str, context: dict) -> TextContent:
            """Chat with AI Assistant"""
            # Implementation
            pass
```

**Configuration:**

```yaml
# ai-assistant/config.yml
mcp_server:
  enabled: true
  port: 8081
  host: 0.0.0.0
  auth:
    enabled: true
    api_key: ${MCP_API_KEY}
  cors:
    enabled: true
    allowed_origins:
      - http://localhost:*
```

### Phase 2: Airflow MCP Server Plugin

**File:** `airflow/plugins/qubinode/mcp_server_plugin.py`

```python
from airflow.plugins_manager import AirflowPlugin
from mcp.server import Server, Tool
from airflow.api.common.experimental.trigger_dag import trigger_dag

class AirflowMCPServer(Server):
    """MCP Server for Airflow"""

    def __init__(self):
        super().__init__("qubinode-airflow")
        self.register_tools()

    def register_tools(self):
        @self.tool()
        async def trigger_dag(dag_id: str, conf: dict = None) -> TextContent:
            """Trigger an Airflow DAG"""
            # Implementation
            pass

        @self.tool()
        async def list_dags() -> TextContent:
            """List available DAGs"""
            # Implementation
            pass

        @self.tool()
        async def create_vm(
            name: str,
            image: str = "centos10stream",
            memory: int = 2048,
            cpus: int = 2,
            disk_size: int = 10
        ) -> TextContent:
            """Create a VM using kcli"""
            # Implementation
            pass

class QuibinodeMCPPlugin(AirflowPlugin):
    name = "qubinode_mcp_server"
    # Plugin implementation
```

**Configuration:**

```yaml
# airflow/config/mcp.yml
mcp_server:
  enabled: false  # Opt-in feature
  port: 8889
  host: 0.0.0.0
  auth:
    enabled: true
    api_key: ${AIRFLOW_MCP_API_KEY}
  tools:
    dag_management: true
    vm_operations: true
    log_access: true
```

### Phase 3: Docker/Podman Integration

**Update `docker-compose.yml`:**

```yaml
services:
  airflow-webserver:
    # ... existing config ...
    environment:
      # ... existing env vars ...
      AIRFLOW__MCP__ENABLED: ${AIRFLOW_MCP_ENABLED:-false}
      AIRFLOW__MCP__PORT: ${AIRFLOW_MCP_PORT:-8889}
      AIRFLOW__MCP__API_KEY: ${AIRFLOW_MCP_API_KEY:-}
    ports:
      - "${AIRFLOW_MCP_PORT:-8889}:8889"  # Only if MCP enabled

  qubinode-ai-assistant:
    # ... existing config ...
    environment:
      # ... existing env vars ...
      MCP_SERVER_ENABLED: ${MCP_SERVER_ENABLED:-false}
      MCP_SERVER_PORT: ${MCP_SERVER_PORT:-8081}
      MCP_API_KEY: ${MCP_API_KEY:-}
    ports:
      - "${MCP_SERVER_PORT:-8081}:8081"  # Only if MCP enabled
```

### Phase 4: Nginx Configuration

**Update nginx config for MCP endpoints:**

```nginx
# MCP Server for AI Assistant (optional)
location /mcp/ai/ {
    proxy_pass http://localhost:8081/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;

    # Require authentication
    auth_basic "MCP Access";
    auth_basic_user_file /etc/nginx/.mcp_htpasswd;
}

# MCP Server for Airflow (optional)
location /mcp/airflow/ {
    proxy_pass http://localhost:8889/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;

    # Require authentication
    auth_basic "MCP Access";
    auth_basic_user_file /etc/nginx/.mcp_htpasswd;
}
```

## Security Considerations

### 1. Authentication

- API key required for all MCP connections
- Support for multiple auth methods:
  - API Key (header-based)
  - JWT tokens
  - mTLS (mutual TLS)

### 2. Authorization

- Role-based access control
- Tool-level permissions:
  - read-only (list, query, status)
  - execute (trigger, create, delete)
  - admin (full access)

### 3. Rate Limiting

- Per-client rate limits
- Per-tool rate limits
- Prevent abuse

### 4. Audit Logging

- Log all MCP requests
- Track tool usage
- Security monitoring

## Configuration Flags

### Environment Variables:

```bash
# AI Assistant MCP
export MCP_SERVER_ENABLED=true
export MCP_SERVER_PORT=8081
export MCP_API_KEY="your-secure-api-key"
export MCP_AUTH_METHOD="api_key"  # api_key, jwt, mtls

# Airflow MCP
export AIRFLOW_MCP_ENABLED=true
export AIRFLOW_MCP_PORT=8889
export AIRFLOW_MCP_API_KEY="your-secure-api-key"
export AIRFLOW_MCP_TOOLS="dag_management,vm_operations,log_access"
```

### Config File:

**`config/mcp-servers.yml`:**

```yaml
ai_assistant:
  mcp:
    enabled: false  # Default disabled for security
    port: 8081
    host: 0.0.0.0
    auth:
      method: api_key
      api_key: ${MCP_API_KEY}
    tools:
      - query_documents
      - chat_with_context
      - get_project_status
    rate_limit:
      requests_per_minute: 60

airflow:
  mcp:
    enabled: false  # Default disabled for security
    port: 8889
    host: 0.0.0.0
    auth:
      method: api_key
      api_key: ${AIRFLOW_MCP_API_KEY}
    tools:
      dag_management:
        enabled: true
        permissions: ["read", "execute"]
      vm_operations:
        enabled: true
        permissions: ["read", "execute"]
      log_access:
        enabled: true
        permissions: ["read"]
    rate_limit:
      requests_per_minute: 30
```

## Usage Examples

### Connecting from Claude Desktop

**`claude_desktop_config.json`:**

```json
{
  "mcpServers": {
    "qubinode-ai": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-http-proxy"],
      "env": {
        "MCP_HTTP_URL": "http://YOUR_SERVER_IP:8081",
        "MCP_API_KEY": "your-api-key"
      }
    },
    "qubinode-airflow": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-http-proxy"],
      "env": {
        "MCP_HTTP_URL": "http://YOUR_SERVER_IP:8889",
        "MCP_API_KEY": "your-airflow-api-key"
      }
    }
  }
}
```

### Using MCP Tools

**In Claude Desktop:**

```
User: List all available workflows
Claude: [Calls list_dags tool]

User: Create a VM named test-vm with 4GB RAM
Claude: [Calls create_vm tool with parameters]

User: What's the status of the example_kcli_vm_provisioning DAG?
Claude: [Calls get_dag_status tool]
```

## Benefits

### For Users:

1. **Natural Language Control:** Manage VMs and workflows conversationally
1. **Multi-Client Support:** Use any MCP-compatible LLM
1. **Automation:** Chain operations via AI reasoning
1. **Observability:** Query status and logs naturally

### For Developers:

1. **Standardized API:** MCP protocol is vendor-neutral
1. **Tool Discovery:** LLMs automatically discover capabilities
1. **Type Safety:** Schema-based tool definitions
1. **Extensible:** Easy to add new tools

## Deployment

### Enable MCP Servers:

```bash
cd /opt/qubinode_navigator

# Generate API keys
export MCP_API_KEY=$(openssl rand -hex 32)
export AIRFLOW_MCP_API_KEY=$(openssl rand -hex 32)

# Save to .env file
cat >> airflow/.env << EOF
# MCP Server Configuration
MCP_SERVER_ENABLED=true
MCP_SERVER_PORT=8081
MCP_API_KEY=${MCP_API_KEY}

AIRFLOW_MCP_ENABLED=true
AIRFLOW_MCP_PORT=8889
AIRFLOW_MCP_API_KEY=${AIRFLOW_MCP_API_KEY}
EOF

# Update deployment
./deploy-qubinode-with-airflow.sh
```

### Open Firewall Ports:

```bash
# Only if exposing externally (not recommended without VPN)
firewall-cmd --permanent --add-port=8081/tcp
firewall-cmd --permanent --add-port=8889/tcp
firewall-cmd --reload
```

### Update Nginx:

```bash
# Add MCP proxy configuration
vim /etc/nginx/conf.d/airflow.conf
# Add location blocks for /mcp/ai/ and /mcp/airflow/
nginx -t && systemctl reload nginx
```

## Testing

### Test MCP Server Health:

```bash
# AI Assistant MCP
curl -H "X-API-Key: $MCP_API_KEY" \
  http://localhost:8081/health

# Airflow MCP
curl -H "X-API-Key: $AIRFLOW_MCP_API_KEY" \
  http://localhost:8889/health
```

### Test Tool Discovery:

```bash
# List available tools
curl -H "X-API-Key: $MCP_API_KEY" \
  http://localhost:8081/tools

curl -H "X-API-Key: $AIRFLOW_MCP_API_KEY" \
  http://localhost:8889/tools
```

### Test Tool Execution:

```bash
# Trigger a DAG
curl -X POST \
  -H "X-API-Key: $AIRFLOW_MCP_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"dag_id": "example_kcli_vm_provisioning"}' \
  http://localhost:8889/tools/trigger_dag
```

## Documentation

Files to create:

- `docs/MCP-SERVER-SETUP.md` - Setup guide
- `docs/MCP-TOOLS-REFERENCE.md` - Tool catalog
- `docs/MCP-SECURITY.md` - Security best practices
- `examples/mcp-client-config.json` - Client examples

## Next Steps

1. **Phase 1:** Implement AI Assistant MCP server (Week 1)
1. **Phase 2:** Implement Airflow MCP server plugin (Week 2)
1. **Phase 3:** Add authentication and security (Week 3)
1. **Phase 4:** Documentation and examples (Week 4)
1. **Phase 5:** Testing and hardening (Week 5)

## Future Enhancements

1. **WebSocket Support:** Real-time updates for long-running operations
1. **GraphQL Interface:** Alternative to MCP for web clients
1. **Custom Tool Builder:** UI for creating new MCP tools
1. **Tool Marketplace:** Share community tools
1. **Monitoring Dashboard:** MCP usage analytics

______________________________________________________________________

**Status:** Design Phase
**Feature Flag:** `MCP_SERVER_ENABLED` (default: false)
**Security:** Opt-in, authentication required
**Impact:** Enables LLM-powered automation
