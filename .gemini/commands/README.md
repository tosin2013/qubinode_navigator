# Qubinode Navigator - Gemini CLI Custom Commands

Custom commands for managing Qubinode Navigator infrastructure using [Gemini CLI](https://geminicli.com/).

## Installation

These commands are automatically available when you run Gemini CLI from the qubinode_navigator directory:

```bash
cd ${QUBINODE_HOME:-$HOME/qubinode_navigator}
gemini
```

## Path Configuration

Commands use `${QUBINODE_HOME:-$HOME/qubinode_navigator}` for flexible path resolution:

```bash
# If installed in non-standard location, set QUBINODE_HOME
export QUBINODE_HOME=/custom/path/qubinode_navigator

# Default: Uses $HOME/qubinode_navigator (works for both root and regular users)
```

## Available Commands

### DAG Management (`/dag:*`)

| Command                        | Description                              |
| ------------------------------ | ---------------------------------------- |
| `/dag:list`                    | List all Airflow DAGs with status        |
| `/dag:info <dag_id>`           | Get detailed information about a DAG     |
| `/dag:trigger <dag_id>`        | Trigger a DAG execution                  |
| `/dag:validate`                | Validate DAG syntax and check for errors |
| `/dag:scaffold <requirements>` | Generate a new DAG from template         |

**Examples:**

```
/dag:list
/dag:info ocp_initial_deployment
/dag:trigger rag_document_ingestion
/dag:validate
/dag:scaffold "deploy FreeIPA server with DNS"
```

### VM Management (`/vm:*`)

| Command                  | Description                             |
| ------------------------ | --------------------------------------- |
| `/vm:list`               | List all virtual machines               |
| `/vm:info <vm_name>`     | Get VM details (CPU, memory, IP)        |
| `/vm:create <specs>`     | Create a new virtual machine            |
| `/vm:delete <vm_name>`   | Delete a virtual machine                |
| `/vm:preflight <config>` | Run preflight checks before VM creation |

**Examples:**

```
/vm:list
/vm:info freeipa-server
/vm:create centos-stream-10 with 4GB RAM and 2 CPUs
/vm:preflight ocp-bootstrap
```

### Infrastructure (`/infra:*`)

| Command                          | Description                             |
| -------------------------------- | --------------------------------------- |
| `/infra:cert-request <hostname>` | Request a TLS certificate               |
| `/infra:cert-list`               | List all managed certificates           |
| `/infra:dns-add <hostname> <ip>` | Add a DNS record                        |
| `/infra:dns-check <hostname>`    | Check DNS resolution                    |
| `/infra:status`                  | Check all infrastructure service status |

**Examples:**

```
/infra:cert-request api.example.com
/infra:cert-list
/infra:dns-add myvm.lab.local 192.168.122.50
/infra:dns-check freeipa.lab.local
/infra:status
```

### RAG Knowledge Base (`/rag:*`)

| Command                   | Description                    |
| ------------------------- | ------------------------------ |
| `/rag:query <question>`   | Query the knowledge base       |
| `/rag:ingest <file_path>` | Ingest a document              |
| `/rag:stats`              | Show knowledge base statistics |

**Examples:**

```
/rag:query how do I deploy OpenShift disconnected
/rag:ingest docs/new-procedure.md
/rag:stats
```

### Diagnostics

| Command                 | Description                           |
| ----------------------- | ------------------------------------- |
| `/diagnose <problem>`   | AI-powered issue diagnosis            |
| `/troubleshoot <issue>` | Interactive troubleshooting assistant |

**Examples:**

```
/diagnose DAG not appearing in Airflow UI
/troubleshoot VM won't start after reboot
```

### System Operations (`/system:*`)

| Command                  | Description                          |
| ------------------------ | ------------------------------------ |
| `/system:deploy`         | Deploy or redeploy the stack         |
| `/system:logs <service>` | View service logs                    |
| `/system:health`         | Run comprehensive health checks      |
| `/system:backup`         | Backup configuration and data        |
| `/system:adr <topic>`    | Search Architecture Decision Records |

**Examples:**

```
/system:deploy
/system:logs airflow-scheduler
/system:health
/system:backup
/system:adr DAG development standards
```

## Command Features

All commands leverage Gemini CLI's powerful features:

- **Shell execution** (`!{...}`): Runs commands and injects output
- **File injection** (`@{...}`): Reads file/directory content for context
- **Arguments** (`{{args}}`): User input is shell-escaped for safety

## Architecture Reference

These commands integrate with:

| Component    | Port | Purpose               |
| ------------ | ---- | --------------------- |
| Airflow UI   | 8888 | DAG management        |
| MCP Server   | 8889 | Tool API              |
| AI Assistant | 8080 | Chat and diagnostics  |
| PostgreSQL   | 5432 | Metadata and vectors  |
| Marquez      | 5001 | Lineage tracking      |
| Marquez Web  | 3000 | Lineage visualization |

## Related Documentation

- [ADR-0045](../docs/adrs/adr-0045-dag-development-standards.md): DAG Development Standards
- [ADR-0047](../docs/adrs/adr-0047-kcli-pipelines-integration.md): Pipeline Integration
- [Airflow README](../airflow/README.md): Airflow setup guide

## Extending Commands

To add new commands:

1. Create a `.toml` file in `.gemini/commands/`
1. Use subdirectories for namespacing (e.g., `dag/list.toml` → `/dag:list`)
1. Include `description` and `prompt` fields
1. Use `!{...}` for shell commands, `@{...}` for file content

Example:

```toml
description = "My custom command"
prompt = """You are helping with a specific task.

Run this command:
!{echo "Hello from {{args}}"}

Review this file:
@{path/to/relevant/file.md}
"""
```

## Claude Code Integration

These Gemini CLI commands can be ported to Claude Code custom slash commands.
See `.claude/commands/` for the Claude Code equivalents (coming soon).
