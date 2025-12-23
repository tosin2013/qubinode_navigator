# MCP Servers - Quick Start Guide ⚡

## ✅ Status: ACTIVE

Your MCP servers are **configured and running**!

______________________________________________________________________

## 🔑 Your API Keys

### AI Assistant (Port 8081):

```
74008c5dde3fca81946c7a5c019ee1e64aef85dbe7a08c2ea9a709bdcfae1e0f
```

### Airflow (Port 8889):

```
65efb281f1ea9dc8498ec563f7bf42af4f8bf8a6b7bb542141902ce462cdb98a
```

______________________________________________________________________

## 🚀 Claude Desktop Setup (Copy & Paste)

**Add this to:** `~/.config/claude/claude_desktop_config.json`

**Replace:** `YOUR_SERVER_IP` with your actual IP address

```json
{
  "mcpServers": {
    "qubinode-airflow": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "http://YOUR_SERVER_IP:8889/sse",
        "--header",
        "X-API-Key:${MCP_API_KEY}"
      ],
      "env": {
        "MCP_API_KEY": "65efb281f1ea9dc8498ec563f7bf42af4f8bf8a6b7bb542141902ce462cdb98a"
      }
    },
    "qubinode-ai": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "http://YOUR_SERVER_IP:8081/sse",
        "--header",
        "X-API-Key:${MCP_API_KEY}"
      ],
      "env": {
        "MCP_API_KEY": "74008c5dde3fca81946c7a5c019ee1e64aef85dbe7a08c2ea9a709bdcfae1e0f"
      }
    }
  }
}
```

______________________________________________________________________

## 🎯 Test These Commands in Claude Desktop

After configuring Claude Desktop, restart it and try:

```
1. "List all available Airflow workflows"
2. "Show me what VMs are currently running"
3. "Create a test VM named demo-vm with 2GB RAM"
4. "What's the status of the example_kcli_vm_provisioning DAG?"
5. "Search the documentation for kcli commands"
```

______________________________________________________________________

## 🛠️ Available Tools (12 Total)

### Via Airflow MCP:

- ✅ list_dags, get_dag_info, get_dag_runs
- ✅ trigger_dag (start workflows)
- ✅ list_vms, get_vm_info
- ✅ create_vm, delete_vm (full access)
- ✅ get_task_logs

### Via AI Assistant MCP:

- ✅ query_documents (RAG search)
- ✅ chat_with_context (AI chat)
- ✅ get_project_status

______________________________________________________________________

## ✅ What's Enabled

```
✅ AI Assistant MCP:     Port 8081
✅ Airflow MCP:          Port 8889
✅ DAG Management:       Enabled
✅ VM Operations:        Enabled
✅ Log Access:           Enabled
⚠️  Write Access:        ENABLED (full control)
```

______________________________________________________________________

## ⚡ Quick Commands

```bash
# Check services
podman ps --filter "name=airflow"

# View MCP config
cat /opt/qubinode_navigator/airflow/.env | grep MCP

# Restart if needed
cd /opt/qubinode_navigator/airflow && podman-compose restart

# View logs
podman logs -f airflow_airflow-webserver_1 | grep MCP
```

______________________________________________________________________

## 📚 Full Documentation

- **Complete Guide:** `airflow/MCP-SERVER-GUIDE.md`
- **Configuration:** `MCP-CONFIGURATION-ACTIVE.md`
- **Architecture:** `docs/MCP-SERVER-DESIGN.md`

______________________________________________________________________

## 🎉 You're All Set!

MCP servers are running and ready for Claude Desktop or other LLM clients to connect!
